import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from project_scanner import scan, candidate_properties, markdown

POM='''<project xmlns="http://maven.apache.org/POM/4.0.0"><dependencies>
 <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-undertow</artifactId></dependency>
</dependencies></project>'''

class ProjectScannerTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def put(self,p,content):
        path=self.root/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf8');return path
    def test_detect_undertow_and_no_unsafe_worker_conversion(self):
        self.put('pom.xml',POM)
        self.put('src/main/resources/application.properties','server.undertow.threads.worker=16\nserver.undertow.accesslog.enabled=true\n')
        r=scan(self.root)
        self.assertTrue(r['project_has_undertow_hints'])
        d={p['source_key']:p for p in r['undertow_to_tomcat']}
        self.assertEqual(d['server.undertow.threads.worker']['mapping'],'NO_SAFE_MAPPING')
        self.assertIsNone(d['server.undertow.threads.worker']['candidate_value'])
        self.assertEqual(d['server.undertow.accesslog.enabled']['target_key'],'server.tomcat.accesslog.enabled')
        self.assertTrue(all(not p['automatic_patch'] for p in r['undertow_to_tomcat']))
        self.assertIn('NOT APPLIED',candidate_properties(r))
        self.assertIn('WEB-UNDERTOW-001',str(r['findings']))
    def test_defaults_without_explicit_config(self):
        self.put('pom.xml',POM)
        r=scan(self.root)
        self.assertEqual(len(r['undertow_to_tomcat']),0)
        d={p['source']:p for p in r['default_comparisons']}
        self.assertEqual(d['server.undertow.threads.worker']['source_observation'],'NO_STATIC_OVERRIDE_FOUND')
        self.assertEqual(d['server.undertow.threads.worker']['target_default'],'200')
        self.assertEqual(d['server.undertow.max-http-post-size']['equivalence'],'DIFFERENT_SCOPE')
        self.assertEqual(d['server.undertow.no-request-timeout']['effective_status'],'NOT_RUNTIME_VERIFIED')
    def test_accesslog_source_default_proposal_is_conditional(self):
        self.put('pom.xml',POM)
        self.put('src/main/resources/application.properties','server.undertow.accesslog.enabled=true\n')
        r=scan(self.root)
        pairs={x['target_key']:x for x in r['default_preservation_candidates']}
        self.assertEqual(pairs['server.tomcat.accesslog.prefix']['candidate_value'],'access_log.')
        self.assertEqual(pairs['server.tomcat.accesslog.suffix']['decision'],'REVIEW_ONLY_DEFAULT_ALIGNMENT')
        self.assertIn('CANDIDATE (NOT APPLIED)',candidate_properties(r))
    def test_existing_target_stays_untouched(self):
        file=self.put('src/main/resources/application.properties','server.undertow.accesslog.enabled=true\nserver.tomcat.accesslog.enabled=false\n')
        original=file.read_bytes()
        r=scan(self.root)
        self.assertEqual(r['undertow_to_tomcat'][0]['decision'],'CONFLICT_REVIEW_REQUIRED')
        self.assertEqual(original,file.read_bytes())
    def test_yaml_profiles_and_locations(self):
        self.put('src/main/resources/application-prod.yml','server:\n  undertow:\n    accesslog:\n      enabled: true\n    threads:\n      worker: 40\n')
        r=scan(self.root)
        self.assertTrue(any(x['profile_hint']=='prod' and x['line']==4 for x in r['configuration_observations']))
        self.assertEqual(len(r['undertow_to_tomcat']),2)
    def test_mappers_and_customizers_are_candidates_only(self):
        self.put('src/main/java/a/Legacy.java','class Legacy { ObjectMapper m=new ObjectMapper(); UndertowBuilderCustomizer x; }')
        r=scan(self.root)
        self.assertTrue(any(x['rule_id']=='JCK3-MAPPER-TOPOLOGY-003' for x in r['findings']))
        self.assertTrue(any(x['decision']=='MANUAL_JAVA_API_REVIEW' for x in r['findings']))
    def test_unknown_options_are_review(self):
        self.put('src/main/resources/application.properties','server.undertow.options.socket.READ_TIMEOUT=2000\n')
        p=scan(self.root)['undertow_to_tomcat'][0]
        self.assertIsNone(p['target_key']);self.assertEqual(p['decision'],'MANUAL_REVIEW')
    def test_no_undertow_no_diff(self):
        self.put('src/main/resources/application.properties','server.port=9090\n')
        r=scan(self.root)
        self.assertFalse(r['project_has_undertow_hints']);self.assertFalse(r['default_comparisons'])
    def test_placeholder_is_not_treated_as_resolved(self):
        self.put('src/main/resources/application.properties','server.undertow.accesslog.dir=${LOG_PATH}\n')
        r=scan(self.root)
        self.assertTrue(any(v['is_dynamic'] for v in r['configuration_observations']))
        self.assertIn('${LOG_PATH}',candidate_properties(r))
    def test_comments_dont_trigger_java_candidates(self):
        self.put('src/main/java/a/A.java','// new ObjectMapper()\nclass A {}\n')
        self.assertFalse(scan(self.root)['java_candidates'])
    def test_markdown_and_json_serializable(self):
        self.put('pom.xml',POM)
        r=scan(self.root)
        json.dumps(r)
        self.assertIn('Defaults: review only',markdown(r))

if __name__=='__main__':unittest.main()
