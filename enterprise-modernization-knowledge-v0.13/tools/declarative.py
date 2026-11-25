"""Reusable candidate detectors. No raw values, source text or resolved symbols in output."""
import fnmatch,re,xml.etree.ElementTree as ET
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path
import yaml
from module_index import Modules,pom_root
from safety import files
from project_scanner import parse_properties,parse_yaml
from ast_index import extract
from semantic import collect_semantic
ROOT=Path(__file__).resolve().parents[1]
KINDS={'java.symbol','java.call','java.annotation','java.import','java.constructor','dependency.artifact','config.key','xml.mybatis.element','file.name'}

def load_plans():
    plans=yaml.safe_load((ROOT/'detectors/execution-plans.yaml').read_text())['rules']
    for rid,p in plans.items():
        if p['candidate_only'] is not True or p['decision']!='REVIEW_REQUIRED' or not p['execution_strategy']:raise ValueError('Unsafe plan')
        for m in p.get('match_any',[]):
            if m['type'] not in KINDS or not re.fullmatch(r'[A-Za-z0-9_.$*-]{1,180}',m['pattern']):raise ValueError('Invalid matcher')
    return plans

def mask_java(text):
    rx=re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|//[^\n]*|/\*[\s\S]*?\*/')
    return rx.sub(lambda m:re.sub(r'[^\n]',' ',m.group()),text)

def lexical(text):
    text=mask_java(text); newlines=[m.start() for m in re.finditer(r"\n",text)]
    for typ,rx in [('import',r'\bimport\s+(?:static\s+)?([\w.$*]+)'),('annotation',r'@\s*([\w.$]+)'),('constructor',r'\bnew\s+([\w.$]+)\s*\('),('call',r'\b([\w.$]+)\s*\('),('symbol',r'\b([\w$]+(?:\.[\w$]+)*)\b')]:
        for m in re.finditer(rx,text):yield typ,bisect_left(newlines,m.start())+1,m.group(1),''

def match(typ,pat,kind,value,resolved=''):
    if typ!='java.'+kind:return False
    # Qualified patterns never match arbitrary suffixes. Simple names are deliberately candidates only.
    choices=[value,resolved] if resolved else [value]
    if '.' not in pat and kind!='import':choices += [v.rsplit('.',1)[-1].rsplit('#',1)[-1] for v in choices]
    return any(fnmatch.fnmatchcase(v,pat) for v in choices)

def collect(project,plans,ast=False,attribute=False,classpaths=None,graph=None):
    root=Path(project).resolve();counts={}; paths=list(files(root,counts));mods=Modules(root,paths)
    astfacts,aststatus=extract(paths,mods,attribute,classpaths) if ast else ({},{'status':'NOT_REQUESTED','files':0,'modules':[]})
    ast_complete={x['module_dir'] for x in aststatus['modules'] if x['status'] in ('PARSED','ATTRIBUTED')}
    rules=defaultdict(list)
    for rid,p in plans.items():
        for m in p.get('match_any',[]):rules[m['type']].append((rid,m['pattern']))
    hits=defaultdict(list);seen=defaultdict(set); truncated=set(); parse_errors=0; warnings_detail=[]
    def warning(p,kind,code,blocking=True):
        warnings_detail.append({"path":p.relative_to(root).as_posix(),"module":mods.bind(p)["module"],"detector_family":kind,"code":code,"coverage_blocking":blocking})
    def emit(typ,value,line,path,mode,resolved='',scope=None):
        for rid,pat in rules[typ]:
            matched=match(typ,pat,typ[5:],value,resolved) if typ.startswith('java.') else fnmatch.fnmatchcase(value,pat)
            if not matched:continue
            family_prefixes={'HCP7-':('com.zaxxer.hikari.',),'SEC7-':('org.springframework.security.',),'MYB4-':('org.apache.ibatis.','org.mybatis.','com.baomidou.'),'HIB7-':('org.hibernate.','jakarta.persistence.'),'JCK3-':('com.fasterxml.jackson.','tools.jackson.')}
            owners=next((v for k,v in family_prefixes.items() if rid.startswith(k)),())
            if owners and typ in ('java.call','java.constructor','java.annotation') and resolved and not resolved.startswith(owners):continue
            rel=path.relative_to(root).as_posix();key=(rel,line,typ,mode,scope)
            if key in seen[rid]:continue
            if len(hits[rid])>=200:truncated.add(rid);continue
            seen[rid].add(key);hits[rid].append({'location':f'{rel}:{line}' if line else rel,'detector':typ,'evidence_kind':mode,'symbol_attributed':bool(resolved),'dependency_scope':scope,**mods.bind(path)})
    for p in paths:
        emit('file.name',p.name,None,p,'FILENAME_ONLY')
        try:
            if p.suffix in ('.java','.kt'):
                use_ast=p.suffix=='.java' and mods.bind(p)['module_dir'] in ast_complete
                facts=astfacts.get(p,[]) if use_ast else lexical(p.read_text(encoding='utf8'))
                for k,line,v,r in facts:emit('java.'+k,v,line,p,'JAVAC_AST' if use_ast else 'LEXICAL_CANDIDATE',r)
            elif p.name=='pom.xml':
                tree=pom_root(p)
                for el in tree.iter('dependency'):
                    a=el.findtext('artifactId') or ''
                    emit('dependency.artifact',a,None,p,'POM_DECLARATION_NOT_RESOLVED')
            elif p.suffix in ('.properties','.yml','.yaml'):
                entries,warnings=parse_properties(p) if p.suffix=='.properties' else parse_yaml(p)
                if warnings:
                    parse_errors+=1
                    for w in warnings:
                        advisory="multi-document YAML" in w
                        warning(p,"config","PROFILE_DOCUMENTS" if advisory else "CONFIG_PARSE_OR_UNSUPPORTED",not advisory)
                for e in entries:emit('config.key',e['key'],e['line'],p,'CONFIG_KEY_NOT_EFFECTIVE')
            elif p.suffix=='.xml':
                # MyBatis commonly declares the standard external DTD. Strip only an exact known public DTD,
                # never fetch it; arbitrary DTD/entity declarations are refused.
                raw=p.read_text(encoding='utf-8-sig')
                raw=re.sub(r'<!DOCTYPE\s+mapper\s+PUBLIC\s+"-//mybatis.org//DTD Mapper 3.0//EN"\s+"https?://mybatis.org/dtd/mybatis-3-mapper.dtd"\s*>','',raw,flags=re.I)
                if re.search(r'<!\s*(DOCTYPE|ENTITY)',raw,re.I):parse_errors+=1;warning(p,"xml","DTD_OR_ENTITY_REFUSED");continue
                node=ET.fromstring(raw)
                if node.tag.split('}')[-1]=='mapper':
                    for e in node.iter():emit('xml.mybatis.element',e.tag.split('}')[-1],None,p,'XML_STRUCTURE')
        except (OSError,UnicodeError,ValueError,ET.ParseError,RecursionError):
            parse_errors+=1;warning(p,"dependency" if p.name=="pom.xml" else "xml" if p.suffix==".xml" else "config" if p.suffix in (".properties",".yml",".yaml") else "java","PARSE_OR_READ_FAILED")
    if graph:
        for d in graph.get('source',{}).get('dependencies',[]):
            dirs=mods.by_ga.get(d['module'],[])
            if len(dirs)==1:
                emit('dependency.artifact',d['ga'].split(':',1)[1],None,dirs[0]/'pom.xml','IMPORTED_DEPENDENCY_NOT_VERIFIED',scope=d['scope'])
    parse_clean={x['module_dir'] for x in aststatus['modules'] if x.get('parse_status')=='PARSE_CLEAN'}
    # Report actual parse failure only against the module/files concerned. Partial attribution is not a global parser failure.
    for m in aststatus['modules']:
        if m['status'] not in ('PARSED','ATTRIBUTED'):
            for p in paths:
                if p.suffix=='.java' and mods.bind(p)['module_dir']==m['module_dir']:
                    warning(p,'java','JAVA_ATTRIBUTION_PARTIAL' if m['module_dir'] in parse_clean else 'JAVA_PARSE_INCOMPLETE',m['module_dir'] not in parse_clean)
                    break
    semantic_hits,semantic_paths=collect_semantic(root,{p:fs for p,fs in astfacts.items() if mods.bind(p)['module_dir'] in parse_clean},mods)
    return hits,{'semantic_hits':dict(semantic_hits),'semantic_paths':sorted(semantic_paths),'warnings':warnings_detail,'modules':mods.report(),'ast':aststatus,'scan_counts':counts,'parse_warnings_or_errors':parse_errors,'truncated_rules':sorted(truncated)},mods
