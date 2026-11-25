"""Independent small repros of detector contract and remaining limitations (no Maven)."""
import json,tempfile,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from migration_scan import analyze
from declarative import load_plans
from inventory import snapshot
from agent_queue import build
CFG=json.loads((ROOT/'examples/java17-to-boot413.json').read_text())
rows=[]
def record(id,ok,detail,observed=None):rows.append({'id':id,'status':'PASS' if ok else 'RESIDUAL','detail':detail,'observed':observed})
with tempfile.TemporaryDirectory() as td:
 b=Path(td);p=b/'project';p.mkdir()
 for mod in ['a','b']:
  d=p/mod;d.mkdir();(d/'pom.xml').write_text(f'<project><groupId>demo</groupId><artifactId>{mod}</artifactId></project>');(d/'A.java').write_text('class A { void f(){ setMaximumPoolSize(4); } }')
 def node(m,v):return {'groupId':'demo','artifactId':m,'version':'1.0.0','children':[{'groupId':'com.zaxxer','artifactId':'HikariCP','version':v,'scope':'compile','children':[]}]}
 s=b/'s.json';t=b/'t.json';s.write_text(json.dumps([node('a','6.3.0'),node('b','7.0.2')]));t.write_text(json.dumps([node('a','7.0.2'),node('b','7.0.2')]))
 graph=snapshot(s,t,p,p);r=analyze(p,CFG,graph);e={x['rule_id']:x for x in r['evaluations']};x=e['HCP7-LOAD-006']
 record('V10-A01',x['locations']==['a/A.java:1'] and x['matched_component_modules']==['demo:a'],'Known coordinate mismatch excluded.',x['locations'])
 record('V10-A02',not any(x['rule_id']=='HCP7-SCHEMA-001' for x in r['findings']),'7.0.0 regression not applied to 7.0.2.')
 (p/'a'/'application.yml').write_text('spring:\n  datasource:\n    hikari:\n      maximum-pool-size: 12\n      password: FAKE_AUDIT_SENTINEL\n');r=analyze(p,CFG,graph)
 record('V10-A03','FAKE_AUDIT_SENTINEL' not in json.dumps(r) and 'FAKE_AUDIT_SENTINEL' not in json.dumps(build(r)),'Synthetic config secret not exported to scan or handoff.')
 q=build(r);record('V10-A04',len(q['tasks'])==len(r['evaluations']) and q['gate']=='BLOCKED_PENDING_VERIFIED_EVIDENCE','Every selected evaluation has a review task, not automatic sign-off.',len(q['tasks']))
 e={x['rule_id']:x for x in r['evaluations']};missing=[i for i in ['SB4-PROPERTIES-004','SB41-DEPRECATED-001','SB41-DEPENDENCY-BOM-011'] if e[i]['status']=='NOT_EVALUATED'];record('V10-A05',len(missing)==3,'Unsupported precise diffs not represented as completed detection.',missing)
 (p/'a'/'A.java').write_text('class A { void requestMatchers(){} void f(){ requestMatchers(); } }');(p/'b'/'A.java').write_text('class B {}');r=analyze(p,CFG,ast=True,attribute=True);e={x['rule_id']:x for x in r['evaluations']};hits=e['SEC7-MATCHER-003']['location_evidence']
 record('V10-A06',bool(hits) and all(h['evidence_kind']=='JAVAC_AST' for h in hits) and all(h['symbol_attributed'] for h in hits) and e['SEC7-MATCHER-003']['decision']=='REVIEW_REQUIRED','Actual JDK attribution of a same-named local method does NOT establish Security API identity.',hits)
 record('V10-A07',len(load_plans())==100 and len([x for x in load_plans().values() if x.get('match_any')])==62,'All plans load; 62 added declaration-based detectors.')
 record('V10-A08',False,'Known residual: exact framework symbol/receiver checking is not enforced by the simple-name matcher; the same-named local method still produces a candidate. No patch.')
 record('V10-A09',False,'Known residual: actual Maven reactor/profile resolution, target runtime and real Undertow/Tomcat/Jackson executions not performed.','NOT_RUN')
 record('V10-A10',False,'Known residual: effective Spring Environment/Bean provenance and dynamic call graph still not resolved.','UNKNOWN')
 record('V10-A11',False,'Known residual: 35 legacy detectors are not all migrated to AST; precise metadata/API/graph diff engines not implemented; 13 old source claims pending review.')
print(json.dumps(rows,ensure_ascii=False,indent=2))
