import copy,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from version_router import route
from migration_scan import analyze
from project_scanner import scan,candidate_properties
from scan_boot41 import scan as scan41
from validate_migration import evaluate
from inventory import snapshot,import_tree
from safety import output_dir
from recipe_guard import review
CFG=json.loads((ROOT/'examples/java17-to-boot413.json').read_text())
MATRIX=json.loads((ROOT/'compatibility/java-minimums.json').read_text())
class Hardening(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.p=self.base/'project';self.p.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def put(self,name,text):
  f=self.p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text,encoding='utf8');return f
 def tree(self,name,deps,module='app'):
  p=self.base/name;p.write_text(json.dumps({'groupId':'demo','artifactId':module,'version':'1.0.0','children':[dict(groupId=g,artifactId=a,version=v,scope='compile',children=[]) for g,a,v in deps]}));return p
 def graph(self,src,tgt,target_module='app'):
  return snapshot(self.tree('source.json',src),self.tree('target.json',tgt,target_module),self.p,self.p)
 def test_a01_patch_downgrade(self):self.assertEqual(route('4.1.3','4.1.0')['status'],'BLOCK')
 def test_a02_prerelease(self):self.assertEqual(route('3.5.7','4.1.0-SNAPSHOT')['status'],'REVIEW_REQUIRED')
 def test_a03_route(self):
  self.put('application.properties','server.undertow.accesslog.enabled=true');self.put('src/main/java/A.java','class A { Object m = new ObjectMapper(); }');c=copy.deepcopy(CFG);c['source']['spring_boot_version']='4.0.9';r=analyze(self.p,c)
  self.assertFalse(r['legacy']['findings']);self.assertFalse(r['legacy']['undertow_to_tomcat']);self.assertFalse(r['legacy']['default_comparisons'])
 def test_a04_builder(self):
  self.put('src/main/java/A.java','/* new ObjectMapper() */\nnew com.fasterxml.jackson.databind.ObjectMapper();\nJsonMapper.\nbuilder();\nObjectMapper.builder();\nString s="new JsonMapper()";');hits=scan(self.p)['java_candidates'];self.assertEqual([(h['type'],h['line']) for h in hits],[('MANUAL_OBJECTMAPPER',2),('JSONMAPPER_BUILDER',3),('OBJECTMAPPER_BUILDER',5)])
 def test_a05_redact(self):
  self.put('application.properties','spring.datasource.password=FAKE_TEST_SECRET\nserver.undertow.accesslog.pattern=FAKE_TEST_SECRET\nserver.undertow.accesslog.dir=${LOG:FAKE_TEST_SECRET}\n');self.put('Dockerfile.dev','RUN java -Djarmode=layertools -Dpassword=FAKE_TEST_SECRET');self.put('src/main/java/A.java','class A { Object m = new ObjectMapper(); String secret="FAKE_TEST_SECRET"; }');r=analyze(self.p,CFG);self.assertNotIn('FAKE_TEST_SECRET',json.dumps(r));self.assertNotIn('FAKE_TEST_SECRET',candidate_properties(r['legacy']))
 def test_a06_profiles(self):
  self.put('application.properties','server.undertow.accesslog.enabled=true');self.put('module/application-prod.properties','server.tomcat.accesslog.enabled=false');r=scan(self.p);self.assertEqual(r['undertow_to_tomcat'][0]['decision'],'CONFLICT_REVIEW_REQUIRED')
 def test_a07_unbound(self):
  c=copy.deepcopy(CFG);c['evidence']={'dependency_graph_verified':True};self.put('pom.xml','<project><dependencies><dependency><groupId>org.jooq</groupId><artifactId>jooq</artifactId></dependency></dependencies></project>');r=analyze(self.p,c);self.assertEqual(r['preflight']['status'],'REVIEW_REQUIRED');self.assertTrue(any(i['code']=='JOOQ_DECLARATION_NEEDS_RESOLUTION' for i in r['preflight']['issues']))
 def test_a08_docker(self):
  self.put('Dockerfile.dev','RUN java -Djarmode=layertools -jar app.jar extract');self.assertTrue(any('Dockerfile.dev' in f['location'] for f in scan41(self.p,'3.5.7','4.1.3')['findings']))
 def test_a09_coverage(self):
  self.put('src/main/java/Config.java','import org.springframework.boot.autoconfigure.web.servlet.WebMvcAutoConfiguration;');r=analyze(self.p,CFG);d={x['rule_id']:x for x in r['evaluations']};self.assertTrue(set(r['route']['rule_ids'])<=set(d));self.assertEqual(d['SB4-PACKAGE-002']['status'],'DETECTED');self.assertTrue(any(x['status']=='NOT_EVALUATED' for x in d.values()));self.assertEqual(sum(r['coverage'].values()),len(d))
 def test_a10_symlink(self):
  outside=self.base/'outside';outside.write_text('server.undertow.accesslog.enabled=true');
  try:(self.p/'application.properties').symlink_to(outside)
  except OSError:self.skipTest('symlink unavailable')
  r=scan(self.p);self.assertFalse(r['project_has_undertow_hints']);self.assertEqual(r['scan_counts']['links_skipped'],1)
 def test_new_schema_rejects_string_approval(self):
  c=copy.deepcopy(CFG);c['target']['java']['change_approved']='true';self.assertEqual(evaluate(c,MATRIX)['status'],'BLOCK')
 def test_new_output_reuse_and_project(self):
  with self.assertRaises(ValueError):output_dir(self.p/'new',self.p)
  out=self.base/'out';output_dir(out,self.p)
  with self.assertRaises(FileExistsError):output_dir(out,self.p)
 def test_new_symlink_dir(self):
  d=self.base/'outside';d.mkdir();(d/'application.properties').write_text('server.undertow.accesslog.enabled=true')
  try:(self.p/'linked').symlink_to(d,target_is_directory=True)
  except OSError:self.skipTest('symlink unavailable')
  self.assertFalse(scan(self.p)['project_has_undertow_hints'])
 def test_new_hardlink(self):
  f=self.base/'outside';f.write_text('server.undertow.accesslog.enabled=true')
  try:os.link(f,self.p/'application.properties')
  except OSError:self.skipTest('hardlink unavailable')
  self.assertFalse(scan(self.p)['project_has_undertow_hints'])
 def test_new_yaml_cycle(self):
  self.put('application.yml','a: &x\n  b: *x\n');self.assertTrue(any('complexity' in x for x in scan(self.p)['warnings']))
 def test_new_yaml_error_no_excerpt(self):
  self.put('application.yml','server: [FAKE_YAML_SECRET');self.assertNotIn('FAKE_YAML_SECRET',json.dumps(scan(self.p)))
 def test_new_component_independent_route(self):
  self.put('src/main/java/A.java','class A { Object m = new ObjectMapper(); }');c=copy.deepcopy(CFG);c['source']['spring_boot_version']='4.0.9';g=self.graph([('com.fasterxml.jackson.core','jackson-databind','2.21.0')],[('tools.jackson.core','jackson-databind','3.1.8')]);r=analyze(self.p,c,g);d={x['rule_id']:x for x in r['evaluations']};self.assertEqual(d['JCK3-MAPPER-TOPOLOGY-003']['applicability'],'IMPORTED_PAIR_MATCH');self.assertEqual(d['JCK3-MAPPER-TOPOLOGY-003']['status'],'DETECTED');self.assertEqual(r['preflight']['status'],'REVIEW_REQUIRED')
 def test_new_cross_module_no_pair(self):
  c=copy.deepcopy(CFG);c['source']['spring_boot_version']='4.0.9';g=self.graph([('com.fasterxml.jackson.core','jackson-databind','2.21.0')],[('tools.jackson.core','jackson-databind','3.1.8')],'other');r=analyze(self.p,c,g);self.assertNotIn('JCK3-MAPPER-TOPOLOGY-003',{x['rule_id'] for x in r['evaluations']})
 def test_new_hikari_exact_regression(self):
  self.put('src/main/java/A.java','class A { void x(){ pool.setSchema("a"); } }');src=[('com.zaxxer','HikariCP','6.3.0')];g=self.graph(src,[('com.zaxxer','HikariCP','7.0.2')]);r=analyze(self.p,CFG,g);d={x['rule_id']:x for x in r['evaluations']};self.assertEqual(d['HCP7-SCHEMA-001']['applicability'],'IMPORTED_PAIR_OUT_OF_SCOPE');self.assertNotIn('HCP7-SCHEMA-001',{x['rule_id'] for x in r['findings']});g=self.graph(src,[('com.zaxxer','HikariCP','7.0.0')]);self.assertIn('HCP7-SCHEMA-001',{x['rule_id'] for x in analyze(self.p,CFG,g)['findings']})
 def test_new_imported_jooq(self):
  g=self.graph([],[('org.jooq','jooq','3.21.9')]);r=analyze(self.p,CFG,g);self.assertEqual(r['preflight']['status'],'BLOCK');self.assertEqual(g['target']['completeness'],'UNKNOWN')
 def test_new_component_delta_73(self):
  self.put('src/main/java/A.java','import org.hibernate.annotations.Columns;');g=self.graph([('org.hibernate.orm','hibernate-core','6.6.0.Final')],[('org.hibernate.orm','hibernate-core','7.4.15.Final')]);r=analyze(self.p,CFG,g);self.assertTrue(any(x['rule_id']=='HIB73-COLUMNS-001' and x['applicability']=='IMPORTED_PAIR_MATCH' for x in r['findings']))
 def test_new_invalid_graph(self):
  f=self.base/'bad.json';f.write_text('{"groupId":"x","artifactId":"y","version":"1","children":"bad"}');
  with self.assertRaises(ValueError):import_tree(f)
 def test_new_guard(self):
  diff='diff --git a/pom.xml b/pom.xml\n--- a/pom.xml\n+++ b/pom.xml\n@@ -1 +1 @@\n-<java.version>17</java.version>\n+<java.version>21</java.version>\n';r=review(diff);self.assertEqual(r['status'],'BLOCKED_PENDING_HUMAN_REVIEW');self.assertIn('JAVA_VERSION_CHANGE',{f['code'] for f in r['findings']})
 def test_new_component_detector_masks_java_comments(self):
  self.put('src/main/java/A.java','// import org.hibernate.annotations.Columns;\n/* @Columns */\nclass A {}');r=analyze(self.p,CFG);self.assertNotIn('HIB73-COLUMNS-001',{x['rule_id'] for x in r['findings']})
 def test_new_guard_unsafe_path(self):self.assertIn('UNRECOGNIZED_OR_UNSAFE_PATH',{f['code'] for f in review('diff --git a/../x b/../x\n@@ -1 +1 @@\n-a\n+b')['findings']})
 def test_new_target_defaults_41_unknown(self):
  self.put('application.properties','server.undertow.accesslog.enabled=true');r=analyze(self.p,CFG);self.assertTrue(all('UNKNOWN_FOR_EXACT_4.1_TARGET' in x['target_default'] for x in r['legacy']['default_comparisons']));self.assertFalse(r['legacy']['default_preservation_candidates'])
if __name__=='__main__':unittest.main()
