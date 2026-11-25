import json,sys,tempfile,unittest,subprocess,shutil,zipfile,os
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from inventory import attest_capture,build_fingerprint
from detectors import applies,load_registry
from artifact_diffs import graph_diff,gaps,compare_artifacts,class_members
from migration_scan import analyze
from runtime_evidence import compare
from maven_inventory import plan
CFG=json.loads((ROOT/'examples/java17-to-boot413.json').read_text())
class V12(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.src=self.p/'src';self.src.mkdir();(self.src/'pom.xml').write_text('<project><groupId>test</groupId><artifactId>app</artifactId></project>')
 def tearDown(self):self.tmp.cleanup()
 def put(self,n,s):
  p=self.src/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s);return p
 def side(self,deps=None,attested=False):return {'module_coordinates':['test:app'],'dependencies':deps or [],'provenance':'SCANNER_CAPTURED_LOCAL' if attested else 'USER_IMPORTED_UNATTESTED','completeness':'CAPTURED_DISCOVERED_MODULE_SCOPE' if attested else 'UNKNOWN'}
 def dep(self,ga,v,module='test:app'):return {'ga':ga,'version':v,'scope':'compile','classifier':'','module':module}
 def test_scoped_capture(self):
  s=self.side();m=plan(self.src,self.p/'out','prod');cap={'modules':[{'module_dir':'.','tree':{'status':'EXIT_ZERO','exit_code':0},'classpath':{'status':'EXIT_ZERO','exit_code':0}}],'build_fingerprint_changed':False};merge={'missing_modules':[],'failed_modules':[],'build_fingerprint_changed':False};self.assertTrue(attest_capture(s,self.src,cap,merge,m,'prod'));self.assertEqual(s['capture_scope']['effective_profiles'],'NOT_VERIFIED');self.assertEqual(s['provenance'],'SCANNER_CAPTURED_LOCAL')
  self.assertFalse(attest_capture(self.side(),self.src,cap,merge,m,'dev'));(self.src/'pom.xml').write_text('<project/>');self.assertFalse(attest_capture(self.side(),self.src,cap,merge,m,'prod'))
 def test_hikari_scoped_vs_imported(self):
  spec=load_registry()['HCP7-SCHEMA-001']['component'];a=[self.dep('com.zaxxer:HikariCP','6.3.0')];b=[self.dep('com.zaxxer:HikariCP','7.0.2')]
  self.assertEqual(applies(spec,{'source':self.side(a),'target':self.side(b)}),'IMPORTED_PAIR_OUT_OF_SCOPE');self.assertEqual(applies(spec,{'source':self.side(a,True),'target':self.side(b,True)}),'CAPTURED_SCOPE_NOT_APPLICABLE')
  self.assertEqual(applies(spec,{'source':self.side(a,True),'target':self.side([self.dep('com.zaxxer:HikariCP','7.0.0')],True)}),'IMPORTED_PAIR_MATCH')
 def test_graph_diff_and_gap(self):
  ga='com.oracle.database.jdbc:ojdbc11';g={'source':self.side([self.dep(ga,'23.7.0.25.01')]),'target':self.side([self.dep(ga,'23.26.4.0.0')])};self.assertEqual(graph_diff(g)['total_changes'],1);self.assertEqual(gaps(g,load_registry())[0]['ga'],ga)
 def test_metadata_and_class_api(self):
  if not shutil.which('javac'):self.skipTest('JDK required')
  self.put('A.java','import org.springframework.boot.Sample; class A { Sample a; }');self.put('application.properties','sample.old=secret\nsample.change=secret2\n')
  paths=[]
  for name,body,props in [('a','public void old(){}',[{'name':'sample.old','type':'java.lang.String'},{'name':'sample.change','defaultValue':'a'}]),('b','',[{'name':'sample.change','defaultValue':'b'}])]:
   d=self.p/name;d.mkdir();f=d/'Sample.java';f.write_text('package org.springframework.boot; public class Sample {'+body+'}');subprocess.run(['javac','-d',str(d),str(f)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);jar=d/'test.jar'
   with zipfile.ZipFile(jar,'w') as z:
    if name=='a':z.write(d/'org/springframework/boot/Sample.class','org/springframework/boot/Sample.class');self.assertIn(('METHOD','old','()V',False),class_members((d/'org/springframework/boot/Sample.class').read_bytes())[1])
    z.writestr('META-INF/spring-configuration-metadata.json',json.dumps({'properties':props}))
   paths.append(str(jar))
  r=compare_artifacts(self.src,{'.':paths[0]},{'.':paths[1]});self.assertEqual(len(r['configuration']),2);self.assertEqual(len(r['api']),1);self.assertNotIn('secret',json.dumps(r))
 def test_runtime_import_values_hidden(self):
  a,b=self.p/'a.json',self.p/'b.json';fp=build_fingerprint(self.src)
  for p,v in [(a,'SECRET_A'),(b,'SECRET_B')]:p.write_text(json.dumps({'build_fingerprint':fp,'cases':[{'id':'x','outcome':'OBSERVED','observation':v}]}))
  r=compare(a,b,self.src,self.src);self.assertEqual(r['cases'][0]['status'],'OBSERVATION_DIFF');self.assertNotIn('SECRET',json.dumps(r));self.assertEqual(r['gate'],'BLOCKED_PENDING_VERIFIED_EVIDENCE')
 def test_advisory_yaml_not_global(self):
  self.put('application.yml','a: b\n---\na: c\n');r=analyze(self.src,CFG);w=r['declarative_scan']['warnings'];self.assertEqual(w[0]['code'],'PROFILE_DOCUMENTS');self.assertFalse(w[0]['coverage_blocking']);self.assertTrue(all(x['coverage_detail']['blocking_warning_count']==0 for x in r['evaluations']))
 def test_bad_yaml_does_not_block_java_only(self):
  self.put('application.yml','bad: [oops');r=analyze(self.src,CFG);self.assertTrue(any(x['coverage_blocking'] for x in r['declarative_scan']['warnings']));self.assertTrue(all(x['coverage_detail']['blocking_warning_count']==0 for x in r['evaluations'] if x['coverage_detail']['detector_families']==['java']))
 @unittest.skipUnless(shutil.which('javac'),'JDK required')
 def test_security_overloads(self):
  self.put('A.java','import org.springframework.security.config.annotation.web.builders.HttpSecurity;\nclass A {void f(HttpSecurity h){\nh.authorizeHttpRequests();\nh.authorizeHttpRequests(x -> x);\n}}');r=analyze(self.src,CFG,ast=True);x=next(x for x in r['evaluations'] if x['rule_id']=='SEC7-DSL-001');self.assertEqual(x['locations'],['A.java:3'])
 @unittest.skipUnless(shutil.which('javac'),'JDK required')
 def test_resolved_lookalike_same_module(self):
  self.put('Fake.java','class Fake { void setMaximumPoolSize(int n){} void f(){setMaximumPoolSize(1);} }');r=analyze(self.src,CFG,ast=True,attribute=True);x=next(x for x in r['evaluations'] if x['rule_id']=='HCP7-LOAD-006');self.assertFalse(x['locations'])
 def test_no_scoped_exclusion_when_modules_differ(self):
  spec=load_registry()['HCP7-SCHEMA-001']['component'];a=self.side([],True);b=self.side([],True);b['module_coordinates']=['test:other'];self.assertEqual(applies(spec,{'source':a,'target':b}),'UNKNOWN_OR_NO_PAIR_MATCH')
if __name__=='__main__':unittest.main()
