import copy,json,sys,tempfile,unittest,shutil,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from declarative import load_plans,collect
from migration_scan import analyze
from inventory import snapshot,import_tree
from maven_inventory import plan,merge
from agent_queue import build
CFG=json.loads((ROOT/'examples/java17-to-boot413.json').read_text())
class Semantic(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.base=Path(self.t.name);self.p=self.base/'src';self.p.mkdir()
 def tearDown(self):self.t.cleanup()
 def put(self,name,text):
  p=self.p/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8');return p
 def pom(self,module,artifact):return self.put(f'{module}/pom.xml',f'<project><groupId>demo</groupId><artifactId>{artifact}</artifactId></project>')
 def tree(self,artifact,dep=None):return {'groupId':'demo','artifactId':artifact,'version':'1.0.0','children':[] if not dep else [{'groupId':dep[0],'artifactId':dep[1],'version':dep[2],'scope':'compile','children':[]}]}
 def graph(self,a,b):
  f=self.base/'a.json';g=self.base/'b.json';f.write_text(json.dumps(a));g.write_text(json.dumps(b));return snapshot(f,g,self.p,self.p)
 def byid(self,r):return {x['rule_id']:x for x in r['evaluations']}
 def test_all_strategies(self):
  plans=load_plans();self.assertEqual(len(plans),100);self.assertEqual(sum(bool(x.get('match_any')) for x in plans.values()),62);self.assertTrue(all(x['candidate_only'] and x['execution_strategy'] for x in plans.values()))
 def test_config_yaml(self):
  self.put('application.yml','spring:\n  datasource:\n    hikari:\n      maximum-pool-size: 8\n      password: FAKE_SECRET\n');r=analyze(self.p,CFG);x=self.byid(r)['HCP7-LOAD-006'];self.assertEqual(x['status'],'DETECTED');self.assertNotIn('FAKE_SECRET',json.dumps(r));self.assertEqual(x['location_evidence'][0]['evidence_kind'],'CONFIG_KEY_NOT_EFFECTIVE')
 def test_xml_mybatis(self):
  self.put('A.xml','<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "https://mybatis.org/dtd/mybatis-3-mapper.dtd"><mapper namespace="A"><select id="a"><if test="a">x</if></select><resultMap id="b" type="c"/></mapper>');r=self.byid(analyze(self.p,CFG));self.assertEqual(r['MYB4-SQL-007']['status'],'DETECTED');self.assertEqual(r['MYB4-RESULT-008']['status'],'DETECTED')
 def test_xml_no_dtd_entity(self):
  self.put('bad.xml','<!DOCTYPE mapper [<!ENTITY x SYSTEM "file:///etc/passwd">]><mapper>&x;</mapper>');r=analyze(self.p,CFG);self.assertGreater(r['declarative_scan']['parse_warnings_or_errors'],0);self.assertNotEqual(self.byid(r)['MYB4-SQL-007']['status'],'DETECTED')
 def test_lexical_comments_and_strings(self):
  self.put('A.java','class A { // @PreAuthorize\n String a="requestMatchers()"; /* HikariDataSource */ }');r=self.byid(analyze(self.p,CFG));self.assertNotEqual(r['SEC7-METHOD-004']['status'],'DETECTED');self.assertNotEqual(r['SEC7-MATCHER-003']['status'],'DETECTED');self.assertNotEqual(r['HCP7-STARTUP-003']['status'],'DETECTED')
 def test_module_binding(self):
  self.pom('a','a');self.pom('b','b');self.put('a/src/main/java/A.java','class A { void x(){ pool.setMaximumPoolSize(2); } }');self.put('b/src/main/java/B.java','class B { void x(){ pool.setMaximumPoolSize(2); } }');g=self.graph([self.tree('a',('com.zaxxer','HikariCP','6.3.0')),self.tree('b',('com.zaxxer','HikariCP','7.0.2'))],[self.tree('a',('com.zaxxer','HikariCP','7.0.2')),self.tree('b',('com.zaxxer','HikariCP','7.0.2'))]);x=self.byid(analyze(self.p,CFG,g))['HCP7-LOAD-006'];self.assertEqual(x['matched_component_modules'],['demo:a']);self.assertEqual(x['locations'],['a/src/main/java/A.java:1']);self.assertEqual(x['location_evidence'][0]['module'],'demo:a')
 def test_duplicate_pom_unbound(self):
  self.pom('a','dup');self.pom('b','dup');self.put('a/A.java','class A { HikariDataSource p; }');x=self.byid(analyze(self.p,CFG))['HCP7-STARTUP-003'];self.assertIsNone(x['location_evidence'][0]['module'])
 def test_duplicate_graph_rejected(self):
  f=self.base/'tree.json';f.write_text(json.dumps([self.tree('a'),self.tree('a')]));self.assertRaises(ValueError,import_tree,f)
 def test_inventory_plan_merge(self):
  self.pom('a','a');self.pom('b','b');out=self.base/'exports';out.mkdir();m=plan(self.p,out,'prod');self.assertEqual(len(m['modules']),2);self.assertIn('-o',m['modules'][0]['tree_command']);self.assertIn('-Pprod',m['modules'][0]['tree_command']);a=m['modules'][0];(out/a['tree_file']).write_text(json.dumps(self.tree('a')));r=merge(self.p,out,m,self.base/'merged');self.assertEqual(r['merged_modules'],1);self.assertEqual(r['failed_modules'],['b']);self.assertEqual(r['completeness'],'UNKNOWN')
 def test_inventory_mismatched_tree(self):
  self.pom('a','a');out=self.base/'exports';out.mkdir();m=plan(self.p,out);(out/m['modules'][0]['tree_file']).write_text(json.dumps(self.tree('wrong')));self.assertRaises(ValueError,merge,self.p,out,m,self.base/'merged')
 def test_agent_queue_no_patch(self):
  self.put('A.java','class A { void f(){ getObject(); } }');r=analyze(self.p,CFG);q=build(r);self.assertEqual(len(q['tasks']),len(r['evaluations']));self.assertTrue(all(not x['automatic_patch'] for x in q['tasks']));self.assertEqual(q['gate'],'BLOCKED_PENDING_VERIFIED_EVIDENCE')
 @unittest.skipUnless(shutil.which('javac') and shutil.which('java'),'JDK required')
 def test_ast_actual_tree(self):
  self.pom('.','app');self.put('A.java','class A { void requestMatchers(){} void f(){ requestMatchers(); } String s="requestMatchers()"; }');r=analyze(self.p,CFG,ast=True);x=self.byid(r)['SEC7-MATCHER-003'];self.assertEqual(r['declarative_scan']['ast']['status'],'COMPLETE_CANDIDATE_SCAN');self.assertEqual(x['status'],'DETECTED');self.assertTrue(all(h['evidence_kind']=='JAVAC_AST' for h in x['location_evidence']));self.assertFalse(x['location_evidence'][0]['symbol_attributed'])
 @unittest.skipUnless(shutil.which('javac') and shutil.which('java'),'JDK required')
 def test_ast_local_attribution(self):
  self.pom('.','app');self.put('A.java','class A { void requestMatchers(){} void f(){ requestMatchers(); } }');r=analyze(self.p,CFG,ast=True,attribute=True);x=self.byid(r)['SEC7-MATCHER-003'];self.assertEqual(r['declarative_scan']['ast']['modules'][0]['status'],'ATTRIBUTED');self.assertEqual(x['status'],'UNKNOWN');self.assertFalse(x['locations']);self.assertEqual(x['decision'],'REVIEW_REQUIRED')
 @unittest.skipUnless(shutil.which('javac') and shutil.which('java'),'JDK required')
 def test_ast_failed_attribution_fallback(self):
  self.put('A.java','class A { MissingType x; void f(){ requestMatchers(); } }');r=analyze(self.p,CFG,ast=True,attribute=True);self.assertEqual(r['declarative_scan']['ast']['status'],'PARTIAL');x=self.byid(r)['SEC7-MATCHER-003'];self.assertEqual(x['location_evidence'][0]['evidence_kind'],'LEXICAL_CANDIDATE');self.assertFalse(x['location_evidence'][0]['symbol_attributed'])
 def test_probe_comparator(self):
  spec=importlib.util.spec_from_file_location('probe',ROOT/'verification-fixtures/web-container/probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);a={k:{'status':400 if k=='missing_parameter' else 200,'fixture_payload':None if k=='missing_parameter' else 'MATCH'} for k,*_ in m.CASES};self.assertTrue(all(x['observed_match'] for x in m.compare(a,a)));b=copy.deepcopy(a);b['encoded']['fixture_payload']='MISMATCH';self.assertFalse(all(x['observed_match'] for x in m.compare(a,b)))
 def test_transitive_imported_dependency_anchor(self):
  self.pom('a','a');g=self.graph([self.tree('a',('org.springdoc','springdoc-openapi-starter-webmvc-ui','2.8.0'))],[self.tree('a',('org.springdoc','springdoc-openapi-starter-webmvc-ui','3.0.0'))]);r=self.byid(analyze(self.p,CFG,g));x=r['ECO4-SPRINGDOC-001'];self.assertEqual(x['status'],'DETECTED');self.assertEqual(x['location_evidence'][0]['evidence_kind'],'IMPORTED_DEPENDENCY_NOT_VERIFIED')
 def test_unknown_module_association_not_attested(self):
  self.put('src/main/java/A.java','class A { HikariDataSource p; }');g=self.graph([self.tree('other',('com.zaxxer','HikariCP','6.3.0'))],[self.tree('other',('com.zaxxer','HikariCP','7.0.2'))]);x=self.byid(analyze(self.p,CFG,g))['HCP7-STARTUP-003'];self.assertEqual(x['location_evidence'][0]['component_module_association'],'NOT_VERIFIED');self.assertEqual(x['decision'],'REVIEW_REQUIRED')
 def test_missing_metadata_detectors_are_not_evaluated(self):
  x=self.byid(analyze(self.p,CFG));self.assertTrue(all(x[r]['status']=='NOT_EVALUATED' for r in ('SB4-PROPERTIES-004','SB41-DEPRECATED-001','SB41-DEPENDENCY-BOM-011')))
 def test_utf16_dtd_rejected(self):
  p=self.p/'pom.xml';p.write_bytes('<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE project [<!ENTITY e "FAKE_SECRET">]><project><dependencies><dependency><artifactId>undertow-&e;</artifactId></dependency></dependencies></project>'.encode('utf-16'));r=analyze(self.p,CFG);self.assertNotIn('FAKE_SECRET',json.dumps(r));self.assertGreater(r['declarative_scan']['parse_warnings_or_errors'],0)
 def test_scope_remains_unproven_for_simple_method_name(self):
  self.put('A.java','class A { void f(){ save(); } }');r=self.byid(analyze(self.p,CFG))['HIB7-API-REMOVAL-008'];self.assertEqual(r['status'],'DETECTED');self.assertEqual(r['decision'],'REVIEW_REQUIRED');self.assertFalse(r['automatic_patch'])
 def test_http_probe_loopback_mock(self):
  import http.server,threading
  spec=importlib.util.spec_from_file_location('probe',ROOT/'verification-fixtures/web-container/probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def send_obj(self,status,obj):
    data=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
   def do_GET(self):
    from urllib.parse import urlsplit,parse_qs
    u=urlsplit(self.path)
    if u.path=='/probe/health':self.send_obj(200,{'status':'UP'})
    else:
     q=parse_qs(u.query);self.send_obj(200,{'q':q['q'][0]}) if 'q' in q else self.send_obj(400,{})
   def do_POST(self):self.send_obj(200,{'length':len(self.rfile.read(int(self.headers['Content-Length'])).decode())})
  servers=[http.server.HTTPServer(('127.0.0.1',0),Handler) for _ in range(2)];threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in servers]
  try:
   for t in threads:t.start()
   self.assertTrue(all(x['observed_match'] for x in m.compare(*(m.capture(s.server_port) for s in servers))))
  finally:
   for s in servers:s.shutdown();s.server_close()
   for t in threads:t.join()
 def test_capture_requires_explicit_approval(self):
  from maven_inventory import capture
  with self.assertRaises(ValueError):capture(self.p,self.base/'capture')
  self.assertFalse((self.base/'capture').exists())
 def test_capture_exec_contract_mock(self):
  import os
  from unittest.mock import patch
  from types import SimpleNamespace
  from maven_inventory import capture
  if os.name=='nt':self.skipTest('explicit capture is POSIX only')
  self.pom('a','a');out=self.base/'capture'
  with patch('maven_inventory.shutil.which',return_value='/approved/mvn'),patch('maven_inventory.subprocess.run',return_value=SimpleNamespace(returncode=0)) as run:
   r=capture(self.p,out,'prod',True)
   self.assertEqual(run.call_count,2);self.assertIn('-o',run.call_args_list[0].args[0]);self.assertEqual(run.call_args_list[0].args[0][0],'/approved/mvn');self.assertEqual(r['completeness'],'UNKNOWN')
