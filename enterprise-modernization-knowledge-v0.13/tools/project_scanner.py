#!/usr/bin/env python3
"""Read-only preflight scanner for Spring Boot 3 -> 4 migration.

Emits candidate findings only. It is not a Spring Environment simulator, Java AST,
Maven dependency resolver, or an automatic migration tool.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from safety import files, output_dir, config_value, SAFE_NAME, SAFE_KEYS

SCHEMA_VERSION = "0.7.0"
UNDERTOW_PREFIX = "server.undertow."
TOMCAT_PREFIX = "server.tomcat."
# Only an exact, documented key with broadly corresponding purpose becomes a
# candidate; no value is applied automatically and an approval remains required.
KEY_MAP = {
    "server.undertow.accesslog.enabled": ("server.tomcat.accesslog.enabled", "SAME_PURPOSE_CANDIDATE", "Both enable access logging; compare actual logging behaviour."),
    "server.undertow.accesslog.rotate": ("server.tomcat.accesslog.rotate", "SAME_PURPOSE_CANDIDATE", "Rotation policies and naming still require review."),
    "server.undertow.accesslog.dir": ("server.tomcat.accesslog.directory", "REVIEW_SEMANTICS", "Tomcat relative paths are interpreted relative to its base directory."),
    "server.undertow.accesslog.pattern": ("server.tomcat.accesslog.pattern", "REVIEW_SEMANTICS", "Pattern syntax is not guaranteed identical; inspect custom tokens."),
    "server.undertow.accesslog.prefix": ("server.tomcat.accesslog.prefix", "REVIEW_SEMANTICS", "Filename prefix and date naming conventions differ."),
    "server.undertow.accesslog.suffix": ("server.tomcat.accesslog.suffix", "REVIEW_SEMANTICS", "Suffix punctuation and file names can change."),
    "server.undertow.url-charset": ("server.tomcat.uri-encoding", "REVIEW_SEMANTICS", "Verify percent decoding/URI character handling."),
}
SPECIAL_REVIEW = {
    "server.undertow.threads.worker": ("server.tomcat.threads.max", "Worker models differ. Never copy worker count directly; load-test and consider virtual threads."),
    "server.undertow.threads.io": (None, "Undertow I/O threads have no direct Tomcat property equivalent."),
    "server.undertow.no-request-timeout": ("server.tomcat.keep-alive-timeout", "Idle-without-request and keep-alive timeouts are not an exact semantic match. Do not auto-copy."),
    "server.undertow.max-http-post-size": ("server.tomcat.max-http-form-post-size", "Undertow HTTP POST size and Tomcat FORM POST size have different scopes."),
    "server.undertow.max-parameters": ("server.tomcat.max-parameter-count", "Query/path parameter semantics differ from Tomcat GET+POST parameter count."),
    "server.undertow.max-cookies": (None, "No equivalent Spring Boot 4 Tomcat property is established; check Tomcat connector customization."),
    "server.undertow.max-headers": (None, "Do not confuse header count with server.max-http-request-header-size (byte size)."),
    "server.undertow.decode-slash": ("server.tomcat.relaxed-path-chars", "Not equivalent: encoded slash handling needs connector/security review."),
    "server.undertow.direct-buffers": (None, "Undertow direct buffer allocation is container-specific."),
    "server.undertow.buffer-size": (None, "Undertow buffer size is container-specific."),
    "server.undertow.options.server.*": (None, "Undertow server option requires manual API/semantics review."),
    "server.undertow.options.socket.*": (None, "XNIO socket option requires manual API/semantics review."),
}
# Defaults below are from published Spring Boot property appendices, not the
# measured runtime effective configuration of any specific application.
DEFAULT_COMPARISONS = [
    dict(source="server.undertow.threads.io", source_default="derived from available processors", target="server.tomcat.threads.max", target_default="200", equivalence="NO_DIRECT_EQUIVALENCE", note="Undertow I/O threads are not Tomcat request workers."),
    dict(source="server.undertow.threads.worker", source_default="8 × effective Undertow I/O thread count", target="server.tomcat.threads.max", target_default="200", equivalence="NOT_EQUAL_BY_COUNT", note="Tomcat worker model; with virtual threads enabled max does not control the same thing."),
    dict(source="server.undertow.max-http-post-size", source_default="2MB", target="server.tomcat.max-http-form-post-size", target_default="2MB", equivalence="DIFFERENT_SCOPE", note="Equal-looking default size does not mean equivalent request-body semantics."),
    dict(source="server.undertow.accesslog.enabled", source_default="false", target="server.tomcat.accesslog.enabled", target_default="false", equivalence="SIMILAR_INTENT", note="Explicit configuration and log output format still need examination."),
    dict(source="server.undertow.accesslog.prefix", source_default="access_log.", target="server.tomcat.accesslog.prefix", target_default="access_log", equivalence="DIFFERENT_DEFAULT", note="File name and rotation may change without explicit settings."),
    dict(source="server.undertow.accesslog.suffix", source_default="log", target="server.tomcat.accesslog.suffix", target_default=".log", equivalence="DIFFERENT_DEFAULT", note="Do not add properties unless filename contract requires it."),
    dict(source="server.undertow.url-charset", source_default="UTF-8", target="server.tomcat.uri-encoding", target_default="UTF-8", equivalence="SIMILAR_INTENT", note="Actual decoded request behavior must still be compared."),
    dict(source="server.undertow.no-request-timeout", source_default="not documented at Spring property level; server runtime dependent", target="server.tomcat.keep-alive-timeout", target_default="derived from connection-timeout unless overridden", equivalence="NOT_DIRECTLY_EQUIVALENT", note="Do not fabricate a numeric timeout from absent config."),
]
SOURCE_URLS = {
    "boot35": "https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html",
    "boot40": "https://docs.spring.io/spring-boot/4.0/appendix/application-properties/index.html",
    "migration": "https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide",
}
EXCLUDED_DIRS = {".git", "target", "build", "node_modules", ".gradle", ".idea", ".mvn", "dist", "out"}
JAVA_PATTERNS = [
    ("MANUAL_OBJECTMAPPER", re.compile(r"\bnew\s+(?:[\w$]+\.)*ObjectMapper\s*\(")),
    ("MANUAL_JSONMAPPER", re.compile(r"\bnew\s+(?:[\w$]+\.)*JsonMapper\s*\(")),
    ("JSONMAPPER_BUILDER", re.compile(r"\bJsonMapper\s*\.\s*builder\s*\(")),
    ("OBJECTMAPPER_BUILDER", re.compile(r"\bObjectMapper\s*\.\s*builder\s*\(")),
    ("UNDERTOW_CUSTOMIZER", re.compile(r"\b(?:UndertowServletWebServerFactory|UndertowBuilderCustomizer|io\.undertow\.|org\.xnio\.)")),
]

def walk_files(root: Path):
    yield from files(root)

def parse_properties(path: Path):
    out=[]
    try:
        lines=path.read_text(encoding="utf-8-sig").splitlines()
    except (UnicodeError, OSError):
        return out, [f"Unable to decode {path}"]
    # Supports common Spring key=value and key:value forms; complex Java
    # .properties escaping and continuation lines are intentionally flagged.
    warnings=[]
    for i, raw in enumerate(lines, 1):
        line=raw.strip()
        if not line or line.startswith(("#", "!")): continue
        if raw.rstrip().endswith("\\"):
            warnings.append(f"{path}:{i}: multiline/escaped .properties entry requires manual check")
        m=re.match(r"^([^=:\s]+)\s*(?:=|:|\s)\s*(.*)$",line)
        if m:
            out.append(dict(key=m.group(1),value=m.group(2).strip(),line=i))
    return out,warnings

def parse_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        return [],[f"PyYAML not installed: cannot inspect {path}; mark YAML coverage as incomplete"]
    try:
        text=path.read_text(encoding="utf-8-sig")
        docs=list(yaml.compose_all(text, Loader=yaml.SafeLoader))
    except Exception as ex:
        return [],[f"Failed YAML parse {path}: content withheld"]
    out=[]; warnings=[]; visited=0
    def flatten(node,prefix,docnum,ancestors=()):
        nonlocal visited
        visited+=1
        if visited>20000 or id(node) in ancestors or len(ancestors)>40 or len(out)>10000:
            raise ValueError("YAML complexity limit")
        ancestors=(*ancestors,id(node))
        if isinstance(node,yaml.MappingNode):
            seen=set()
            for k,v in node.value:
                key=k.value
                if not isinstance(key,str) or not SAFE_NAME.fullmatch(key):continue
                if key in seen: warnings.append(f"{path}:{k.start_mark.line+1}: duplicate YAML key (name withheld)")
                seen.add(key)
                flatten(v, (prefix+"." if prefix else "")+key, docnum,ancestors)
        elif isinstance(node,yaml.ScalarNode):
            out.append(dict(key=prefix,value=node.value,line=node.start_mark.line+1,document=docnum))
        elif isinstance(node,yaml.SequenceNode):
            warnings.append(f"{path}:{node.start_mark.line+1}: array values not interpreted as Spring config")
    for i,doc in enumerate(docs,1):
        if doc is not None:
            try: flatten(doc,"",i)
            except (ValueError,RecursionError):return [],[f"{path}: YAML complexity limit or unsupported structure"]
    if len(docs)>1: warnings.append(f"{path}: multi-document YAML; profile activation/overrides require runtime resolution")
    return out,warnings

def parse_pom(path: Path):
    try:
        raw=path.read_bytes()
        if re.search(br"<!DOCTYPE|<!ENTITY",raw.replace(b"\x00",b""),re.I):return [],[f"{path}: XML declarations not accepted"]
        root=ET.fromstring(raw)
    except (ET.ParseError,OSError) as ex: return [],[f"Failed POM parse {path}: content withheld"]
    ns={"m": "{http://maven.apache.org/POM/4.0.0}"}  # simple namespace-independent tag stripping
    def bare(t): return t.rsplit("}",1)[-1]
    def child_text(el,name):
        for e in el:
            if bare(e.tag)==name: return (e.text or "").strip()
        return ""
    found=[]
    for e in root.iter():
        if bare(e.tag)!="dependency":continue
        a=child_text(e,"artifactId");g=child_text(e,"groupId")
        if SAFE_NAME.fullmatch(a) and (not g or SAFE_NAME.fullmatch(g)) and any(s in a.lower() for s in ("undertow","tomcat","spring-boot-starter-web")):
            found.append({"artifact":f"{g}:{a}","declared_version":(child_text(e,"version") if re.fullmatch(r"[0-9][0-9A-Za-z.\-]{0,50}",child_text(e,"version")) else "BOM/inherited/unknown"), "source":str(path),"note":"POM declaration only; not resolved runtime dependency"})
    return found,[]

def relative(root:Path,path:Path):return path.relative_to(root).as_posix()

def scan(root:Path):
    root=root.resolve()
    if not root.is_dir(): raise ValueError("Project root must be an existing directory")
    config=[]; findings=[]; warnings=[]; dependencies=[]; java_hits=[]; counts={}; redacted=0
    for path in files(root,counts):
        name=path.name.lower()
        if name=="pom.xml":
            deps,ws=parse_pom(path);dependencies+=deps; warnings+=ws
        if path.suffix==".java" and ("src" in path.parts):
            try: text=path.read_text(encoding="utf-8")
            except (UnicodeError,OSError):counts['unreadable']=counts.get('unreadable',0)+1;continue
            # Mask comments and literals while retaining offsets (lexical hints, not AST).
            text=re.sub(r"""//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'""",lambda m:re.sub(r'[^\n]',' ',m.group()),text)
            for typ,pat in JAVA_PATTERNS:
                for m in pat.finditer(text):
                    java_hits.append(dict(type=typ,file=relative(root,path),line=text.count('\n',0,m.start())+1,confidence="TEXT_CANDIDATE_ONLY"))
        if name in ("application.properties","application.yml","application.yaml") or re.match(r"^application-[^/]+\.(properties|yml|yaml)$",name):
            vals,ws=(parse_properties(path) if path.suffix==".properties" else parse_yaml(path))
            warnings+=ws
            for v in vals:
                v["file"]=relative(root,path)
                v["profile_hint"]=name[len("application-"):].rsplit(".",1)[0] if name.startswith("application-") else "default_or_document_conditions"
                v["is_dynamic"]="${" in v["value"] or "#{" in v["value"]
                if not SAFE_NAME.fullmatch(v["key"]) or not (v["key"] in SAFE_KEYS or v["key"] in KEY_MAP or v["key"] in SPECIAL_REVIEW or v["key"].startswith("server.undertow.options.")):
                    redacted+=1;continue
                if v["key"].startswith("server.undertow.options.") and re.search(r"password|token|secret|credential|private.?key",v["key"],re.I):
                    redacted+=1;continue
                v["value"]=config_value(v["key"],v["value"])
                if v["value"]=="[REDACTED]":redacted+=1
                config.append(v)
    has_undertow=any("undertow" in d["artifact"].lower() for d in dependencies) or any(c["key"].startswith(UNDERTOW_PREFIX) for c in config) or any(h["type"]=="UNDERTOW_CUSTOMIZER" for h in java_hits)
    if has_undertow:
        findings.append(dict(rule_id="WEB-UNDERTOW-001",category="BREAKING_CHANGE",decision="REVIEW_REQUIRED",confidence="DECLARATION_OR_STATIC_HINT",message="Undertow usage detected; Boot 4 no longer supports embedded Undertow. Confirm effective container and replace supported starter if applicable.",locations=[d["source"] for d in dependencies if "undertow" in d["artifact"].lower()],automatic_patch=False))
    undertow_configs=[c for c in config if c["key"].startswith(UNDERTOW_PREFIX)]
    target_configs=[c for c in config if c["key"].startswith(TOMCAT_PREFIX)]
    proposals=[]
    for c in undertow_configs:
        k=c["key"];source_location=f"{c['file']}:{c['line']}"
        if k in KEY_MAP:
            t,kind,note=KEY_MAP[k]
            target_existing=[x for x in target_configs if x["key"]==t]
            decision="REVIEW_REQUIRED" if not target_existing else "CONFLICT_REVIEW_REQUIRED"
            proposals.append(dict(source_key=k,source_value=c["value"],source_location=source_location,target_key=t,candidate_value=None if c["value"]=="[REDACTED]" else c["value"],mapping=kind,decision=decision,note=note,automatic_patch=False,existing_target=[f"{x['file']}:{x['line']}={x['value']}" for x in target_existing]))
        else:
            target,note=SPECIAL_REVIEW.get(k,(None,"Undertow-specific option has no verified equivalent; manual assessment required."))
            # Special wildcard matching
            if k.startswith("server.undertow.options."):
                note="Undertow/XNIO option has no documented one-to-one Tomcat mapping; review manually."
            proposals.append(dict(source_key=k,source_value=c["value"],source_location=source_location,target_key=target,candidate_value=None,mapping="NO_SAFE_MAPPING",decision="MANUAL_REVIEW",note=note,automatic_patch=False,existing_target=[f"{x['file']}:{x['line']}={x['value']}" for x in target_configs if x["key"]==target]))
        findings.append(dict(rule_id="WEB-UNDERTOW-005",category="BEHAVIOR_CHANGE",decision=proposals[-1]["decision"],confidence="STATIC_CONFIG_OBSERVED",message=f"Undertow-specific setting {k} will not configure Tomcat; suggested target is a review candidate only",locations=[source_location],automatic_patch=False))
    default_diffs=[]
    default_preservation_candidates=[]
    if has_undertow:
        for d in DEFAULT_COMPARISONS:
            obs=[c for c in undertow_configs if c["key"]==d["source"]]
            dest=[c for c in target_configs if c["key"]==d["target"]]
            default_diffs.append({**d,"source_observation":"EXPLICIT_STATIC_CONFIG" if obs else "NO_STATIC_OVERRIDE_FOUND", "target_observation":"EXPLICIT_STATIC_CONFIG" if dest else "NO_STATIC_OVERRIDE_FOUND", "source_observed":[f"{c['file']}:{c['line']}={c['value']}" for c in obs], "target_observed":[f"{c['file']}:{c['line']}={c['value']}" for c in dest], "effective_status":"NOT_RUNTIME_VERIFIED", "automatic_patch":False})
        # Default preservation is only a conditional review candidate when
        # access logging is explicitly enabled in a statically inspected file.
        # It is never treated as effective runtime configuration.
        explicit_logging=[c for c in undertow_configs if c["key"]=="server.undertow.accesslog.enabled" and c["value"].lower()=="true"]
        if explicit_logging:
            for src,tgt,old_default in [
                ("server.undertow.accesslog.prefix","server.tomcat.accesslog.prefix","access_log."),
                ("server.undertow.accesslog.suffix","server.tomcat.accesslog.suffix","log")]:
                if not any(c["key"]==src for c in undertow_configs) and not any(c["key"]==tgt for c in target_configs):
                    default_preservation_candidates.append(dict(source_key=src,source_default=old_default,target_key=tgt,candidate_value=old_default,decision="REVIEW_ONLY_DEFAULT_ALIGNMENT",note="Only relevant if the source effectively used this default and filename compatibility is contractually required. Explicit access logging found but runtime not verified.",automatic_patch=False))
        findings.append(dict(rule_id="WEB-UNDERTOW-006",category="VALIDATION_ONLY",decision="COMPARE_SOURCE_TARGET_BEHAVIOR",confidence="DOCUMENTED_DEFAULTS_ONLY",message="Compare documented defaults with the measured source/target runtime; do not equate values across servers",locations=sorted(set([d['source'] for d in dependencies if 'undertow' in d['artifact'].lower()]+[f"{c['file']}:{c['line']}" for c in undertow_configs]+[f"{h['file']}:{h['line']}" for h in java_hits if h['type']=='UNDERTOW_CUSTOMIZER'])),automatic_patch=False))
    for h in java_hits:
        if h["type"]=="UNDERTOW_CUSTOMIZER":
            findings.append(dict(rule_id="WEB-UNDERTOW-001",category="BREAKING_CHANGE",decision="MANUAL_JAVA_API_REVIEW",confidence="TEXT_CANDIDATE_ONLY",message="Undertow-specific Java code may require Servlet container API migration",locations=[f"{h['file']}:{h['line']}"],automatic_patch=False))
        else:
            findings.append(dict(rule_id="JCK3-MAPPER-TOPOLOGY-003",category="VALIDATION_ONLY",decision="RESOLVE_MAPPER_ORIGIN_AND_CALLS",confidence="TEXT_CANDIDATE_ONLY",message=f"{h['type']}: check whether Spring properties can reach this mapper",locations=[f"{h['file']}:{h['line']}"],automatic_patch=False))
    warnings += ["Static application files are NOT sufficient to establish effective configuration: environment, profile activation, @Bean customizers, config server, command-line, Kubernetes and JVM options may override.","Maven POM entries are declarations, not a resolved dependency tree. Run Maven with the project's approved repositories for exact artifact versions.","Scanner never edits source files or auto-applies candidate Tomcat properties."]
    return dict(schema_version=SCHEMA_VERSION, generated_at=datetime.now(timezone.utc).isoformat(),project=str(root),scanner_scope="STATIC_READ_ONLY",project_has_undertow_hints=has_undertow, dependencies=dependencies,configuration_observations=config,java_candidates=java_hits, findings=findings,undertow_to_tomcat=proposals,default_comparisons=default_diffs,default_preservation_candidates=default_preservation_candidates,source_references=SOURCE_URLS,warnings=warnings,scan_counts=counts,redacted_or_omitted_config_entries=redacted)

def candidate_properties(report):
    lines=["# Generated review candidates only: DO NOT copy/paste without approval.","# Not a patch. Review target profiles, relative paths, semantics and actual runtime behavior.",""]
    for p in report["undertow_to_tomcat"]:
        lines.append(f"# Source: {p['source_location']} {p['source_key']}={p['source_value']}")
        if p["candidate_value"] is not None:
            lines.append(f"# CANDIDATE (NOT APPLIED): {p['target_key']}={p['candidate_value']}")
        else:
            lines.append(f"# NO SAFE AUTOMATIC TRANSLATION: {p['target_key'] or 'manual review'}")
        lines.append(f"# {p['note']}")
        lines.append("")
    if report["default_preservation_candidates"]:
        lines.extend(["", "# CONDITIONAL SOURCE DEFAULT PRESERVATION (NOT APPLIED):"])
        for d in report["default_preservation_candidates"]:
            lines.append(f"# CANDIDATE (NOT APPLIED): {d['target_key']}={d['candidate_value']}")
            lines.append(f"# {d['note']}")
    if not report["undertow_to_tomcat"]:lines.append("# No explicit Undertow properties found; compare default_comparisons in report.json.")
    return "\n".join(lines)+"\n"

def markdown(report):
    lines=["# Migration Scanner Findings", "", f"- Scope: `{report['scanner_scope']}`", f"- Undertow hints: `{report['project_has_undertow_hints']}`",f"- Findings: {len(report['findings'])}", "", "## Explicit Undertow config migration candidates", "", "| Source location | Source key | Target suggestion | Classification |", "|---|---|---|---|"]
    for p in report["undertow_to_tomcat"]:
        lines.append(f"| `{p['source_location']}` | `{p['source_key']}` | `{p['target_key'] or 'none'}` | {p['mapping']} |")
    lines += ["", "## Defaults: review only", "", "| Source default | Target default | Relationship |", "|---|---|---|"]
    for d in report["default_comparisons"]:
        lines.append(f"| `{d['source']}` = {d['source_default']} | `{d['target']}` = {d['target_default']} | {d['equivalence']} |")
    lines += ["", "## Conditional default-preservation proposals (review only)", ""]
    for d in report["default_preservation_candidates"]:
        lines.append(f"- `{d['target_key']}={d['candidate_value']}` — {d['note']}")
    lines += ["", "## Findings", ""]
    for f in report["findings"]:lines.append(f"- **{f['rule_id']}** / {f['decision']}: {f['message']} ({', '.join(f['locations'])})")
    lines += ["", "## Limitations", ""]+[f"- {x}" for x in report["warnings"]]
    return "\n".join(lines)+"\n"

def main():
    ap=argparse.ArgumentParser(description="Read-only Spring Boot migration candidate scanner")
    ap.add_argument("--project",required=True, type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    try:
        result=scan(args.project)
        args.output=output_dir(args.output,args.project)
        (args.output/"findings.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (args.output/"report.md").write_text(markdown(result),encoding="utf-8")
        (args.output/"suggested-tomcat.properties").write_text(candidate_properties(result),encoding="utf-8")
        print(f"Scanned {args.project} | {len(result['findings'])} findings | {len(result['undertow_to_tomcat'])} config candidates | {args.output}")
    except Exception as e:
        print(f"SCAN ERROR: {type(e).__name__}",file=sys.stderr);return 2
    return 0
if __name__=="__main__":sys.exit(main())
