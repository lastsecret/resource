"""Independent v0.9 probes. No real Java builds or network. Emits PASS / RESIDUAL with evidence."""
import json,sys,tempfile,copy,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from migration_scan import analyze
from project_scanner import scan
from inventory import snapshot
from safety import output_dir
from recipe_guard import review
cfg=json.loads((ROOT/'examples/java17-to-boot413.json').read_text())
rows=[]
def record(id,condition,observed,note):rows.append(dict(id=id,status='PASS' if condition else 'RESIDUAL',observed=observed,detail=note))
def tree(path,children,artifact='app'):
 path.write_text(json.dumps({'groupId':'audit','artifactId':artifact,'version':'1.0.0','children':[{'groupId':g,'artifactId':a,'version':v,'scope':'compile','children':[]} for g,a,v in children]}));return path
with tempfile.TemporaryDirectory() as d:
 b=Path(d);p=b/'project';p.mkdir();(p/'application.properties').write_text('spring.datasource.password=FAKE_SECRET\nserver.undertow.accesslog.pattern=FAKE_SECRET\nserver.undertow.accesslog.enabled=true\n');(p/'Dockerfile.dev').write_text('RUN java -Djarmode=layertools -Dpassword=FAKE_SECRET\n');(p/'src').mkdir();(p/'src/A.java').write_text('class A { Object m = new ObjectMapper(); String s="FAKE_SECRET"; }')
 r=analyze(p,cfg);record('R01-no-raw-secrets-in-sample','FAKE_SECRET' not in json.dumps(r), 'no sample sentinel in output' if 'FAKE_SECRET' not in json.dumps(r) else 'sentinel present','Synthetic secret across config, Java and Docker; not a guarantee for arbitrary secret encoding or path names.')
 c=copy.deepcopy(cfg);c['source']['spring_boot_version']='4.0.9';r=analyze(p,c);record('R02-stage-isolation',not r['legacy']['findings'] and not r['legacy']['undertow_to_tomcat'],len(r['legacy']['findings']),'Boot 4.0→4.1 without imported component pair does not publish old migration findings.')
 record('R03-pending-component-coverage','JCK3-MAPPER-TOPOLOGY-003' in r['unrouted_component_rules_pending_inventory'],len(r['unrouted_component_rules_pending_inventory']),'Unselected component rules requiring inventory are explicit.')
 g=snapshot(tree(b/'src.json',[('com.fasterxml.jackson.core','jackson-databind','2.21.8')]),tree(b/'tgt.json',[('tools.jackson.core','jackson-databind','3.1.8')]),p,p);r=analyze(p,c,g);record('R04-cross-route-component',any(x['rule_id']=='JCK3-MAPPER-TOPOLOGY-003' for x in r['findings']),[x['rule_id'] for x in r['findings']],'Component transition independent of Boot delta.')
 record('R05-evidence-fail-closed',r['preflight']['status']=='REVIEW_REQUIRED' and r['migration_gate']=='BLOCKED_PENDING_VERIFIED_EVIDENCE',r['preflight']['status'],'Even imported tree with SHA-256 cannot assert genuine Maven execution or complete profiles.')
 c=copy.deepcopy(cfg);c['target']['java']['change_approved']='yes';r=analyze(p,c);record('R06-invalid-approval',r['preflight']['status']=='BLOCK',r['preflight']['status'],'Schema rejects truthy string approval.')
 try:output_dir(p/'report',p);guard=False
 except ValueError:guard=True
 record('R07-output-path',guard,guard,'Output inside source rejected.')
 d=review('diff --git a/src/test/java/A.java b/src/test/java/A.java\n--- a/src/test/java/A.java\n+++ b/src/test/java/A.java\n@@ -1 +1 @@\n-assertEquals(1,x);\n+assertEquals(2,x);');record('R08-patch-guard','BASELINE_TEST_CHANGE' in [x['code'] for x in d['findings']] and not d['automatic_patch'],d['status'],'Reject automatic sign-off even if only tests change.')
 # Real residual limitations: retain as explicit negative results rather than silently calling them compatible.
 (p/'src/A.java').write_text('// import org.hibernate.annotations.Columns;\nclass A {}');r=analyze(p,cfg);hit=any(x['rule_id']=='HIB73-COLUMNS-001' for x in r['findings']);record('R09-lexical-comment-false-positive',not hit,hit,'Generic textual detector matches comments; still a candidate. Need Java AST or lexical filters per detector.')
 (p/'src/A.java').write_text('class A { Object m = new ObjectMapper(); }');g=snapshot(tree(b/'s2.json',[('com.fasterxml.jackson.core','jackson-databind','2.21.8')],artifact='other-module'),tree(b/'t2.json',[('tools.jackson.core','jackson-databind','3.1.8')],artifact='other-module'),p,p);r=analyze(p,cfg,g);hit=any(x['rule_id']=='JCK3-MAPPER-TOPOLOGY-003' and x['applicability']=='IMPORTED_PAIR_MATCH' for x in r['findings']);record('R10-module-to-file-binding',not hit,hit,'Graph pairs are module-scoped, but source locations are not bound to module inventory. Candidate only; potential false positive across modules.')
 reg=json.loads((ROOT/'detectors/registry.json').read_text())['rules'];missing=[k for k,v in reg.items() if v['detector']=='none'];record('R11-detector-coverage',not missing,{'unimplemented':len(missing),'total':len(reg)},'No detector is honestly NOT_EVALUATED; must not infer compatibility.')
 record('R12-runtime-proof',False,'NOT_RUN','No Maven, target Java17 runtime, real Oracle DB, Spring Context or OpenRewrite execution available. Runtime sign-off not possible.')
print(json.dumps(rows,ensure_ascii=False,indent=2))
