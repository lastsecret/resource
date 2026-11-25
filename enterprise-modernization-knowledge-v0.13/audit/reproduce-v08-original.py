"""Non-destructive audit probes. Run: python3 reproduce.py /path/to/extracted/pack"""
import copy, json, pathlib, sys, tempfile
root=pathlib.Path(sys.argv[1]).resolve(); sys.path.insert(0,str(root/'tools'))
from version_router import route
from validate_migration import evaluate
from migration_scan import analyze
from project_scanner import scan
from scan_boot41 import scan as scan41
cfg=json.loads((root/'examples/java17-to-boot413.json').read_text()); matrix=json.loads((root/'compatibility/java-minimums.json').read_text())
results=[]
def record(id, observed, expected, defect):
    results.append(dict(id=id,observed=observed,expected=expected,defect_reproduced=defect))
r=route('4.1.3','4.1.0'); record('A01-patch-downgrade',r['status'],'BLOCK or explicit patch-policy review',r['status']=='CANDIDATES_SELECTED')
r=route('3.5.7','4.1.0-SNAPSHOT');record('A02-prerelease',r['status'],'REVIEW unless explicitly permitted',r['status']=='CANDIDATES_SELECTED')
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d); (p/'src/main/java').mkdir(parents=True);(p/'src/main/java/Demo.java').write_text('class Demo { Object m = JsonMapper.builder().build(); }\nclass Other { Object m = ObjectMapper.builder().build(); }')
 (p/'application.properties').write_text('server.undertow.accesslog.enabled=true\nspring.datasource.password=AUDIT_FAKE_PASSWORD\n')
 (p/'application-prod.properties').write_text('server.tomcat.accesslog.enabled=false\n')
 c=copy.deepcopy(cfg);c['source']['spring_boot_version']='4.0.9';r=analyze(p,c);ids=set(r['route']['rule_ids']);extra=sorted({f['rule_id'] for f in r['legacy']['findings']}-ids);record('A03-route-filter',extra,'No out-of-route rule findings (or separate out-of-scope diagnostic)',bool(extra))
 r=scan(p);hits=[h['type'] for h in r['java_candidates']];record('A04-builder-pattern',hits,'One JsonMapper builder match; ObjectMapper pattern must differ',hits.count('JSONMAPPER_BUILDER')==1 and hits.count('OBJECTMAPPER_BUILDER')==1 and len(hits)==2 and r['java_candidates'][0]['line']==r['java_candidates'][1]['line'])
 vals=r['configuration_observations'];record('A05-secret-disclosure',any(v['value']=='AUDIT_FAKE_PASSWORD' for v in vals),'Sensitive values redacted',any(v['value']=='AUDIT_FAKE_PASSWORD' for v in vals))
 proposal=r['undertow_to_tomcat'][0];record('A06-cross-profile-conflict',proposal['existing_target'],'Record existing target in another profile as possible conflict',not proposal['existing_target'])
 (p/'pom.xml').write_text('<project><dependencies><dependency><groupId>org.jooq</groupId><artifactId>jooq</artifactId><version>3.21.9</version></dependency></dependencies></project>')
 c=copy.deepcopy(cfg);c['evidence']={'dependency_graph_verified':True};r=analyze(p,c);observed={'preflight':r['preflight']['status'],'jooq_candidate':any(f['rule_id']=='SB41-JOOQ-JDK-008' for f in r['boot41']['findings'])};record('A07-unbound-evidence',observed,'Require resolved graph evidence or REVIEW on contradiction',observed['preflight']=='PRECHECK_PASS' and observed['jooq_candidate'])
 (p/'Dockerfile.dev').write_text('RUN java -Djarmode=layertools -jar app.jar extract\n');r=scan41(p,'3.5.7','4.1.3');record('A08-dockerfile-variant',any('Dockerfile.dev' in f['location'] for f in r['findings']),'Flag layertools in Dockerfile.dev',not any('Dockerfile.dev' in f['location'] for f in r['findings']))
 (p/'src/main/java/Config.java').write_text('import org.springframework.boot.autoconfigure.web.servlet.WebMvcAutoConfiguration;\nclass Config {}\n');r=analyze(p,c);record('A09-unimplemented-legacy-detectors', any(f['rule_id']=='SB4-PACKAGE-002' for f in r['legacy']['findings']),'Report rule NOT_EVALUATED if unsupported; do not imply coverage',not any(f['rule_id']=='SB4-PACKAGE-002' for f in r['legacy']['findings']))
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'project').mkdir();(p/'outside.properties').write_text('spring.datasource.password=AUDIT_FAKE_EXTERNAL_SECRET\n');
 try:
  (p/'project/application.properties').symlink_to(p/'outside.properties');r=scan(p/'project');found=any(v['value']=='AUDIT_FAKE_EXTERNAL_SECRET' for v in r['configuration_observations']);record('A10-symlink-scope',found,'Do not follow out-of-root links',found)
 except (OSError,NotImplementedError):record('A10-symlink-scope','SKIP','Platform supports symlinks',False)
print(json.dumps(results,ensure_ascii=False,indent=2))
