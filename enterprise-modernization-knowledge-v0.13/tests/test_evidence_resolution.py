import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from resolve_evidence import run,acquire
CFG=json.loads((ROOT/'examples/java17-to-boot413.json').read_text())
class Resolution(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.s=self.root/'source';self.t=self.root/'target'
  for p in [self.s,self.t]:
   p.mkdir();(p/'pom.xml').write_text('<project><groupId>demo</groupId><artifactId>app</artifactId><version>1.0.0</version></project>')
 def tearDown(self):self.tmp.cleanup()
 def trees(self):
  a,b=self.root/'a.json',self.root/'b.json'
  for p,v in [(a,'6.6.0.Final'),(b,'7.4.0.Final')]:p.write_text(json.dumps({'groupId':'demo','artifactId':'app','version':'1.0.0','children':[{'groupId':'org.hibernate.orm','artifactId':'hibernate-core','version':v,'scope':'compile','children':[]}]}))
  return a,b
 def test_group_unknown_once_and_no_maven(self):
  with patch('resolve_evidence.capture') as cap:
   r=run(self.s,CFG,self.root/'out',self.t);cap.assert_not_called()
  groups={x['reason']:x['count'] for x in r['unresolved_groups']};self.assertGreater(groups['MISSING_COMPONENT_GRAPH'],1);self.assertEqual(sum(groups.values()),r['final_coverage']['UNKNOWN']+r['final_coverage']['NOT_EVALUATED']);self.assertEqual([a['status'] for a in r['actions'][-2:]],['APPROVAL_REQUIRED']*2)
 def test_import_reruns_and_reduces_unknown(self):
  a,b=self.trees();r=run(self.s,CFG,self.root/'out',self.t,a,b)
  self.assertLess(r['final_coverage']['UNKNOWN'],r['initial_coverage']['UNKNOWN']);self.assertEqual(r['actions'][-1]['action'],'REEVALUATE_RULES');self.assertEqual(r['gate'],'BLOCKED_PENDING_VERIFIED_EVIDENCE');self.assertFalse(r['automatic_patch']);self.assertEqual(r['runtime_verification'],'NOT_RUN')
 def test_auto_capture_missing_maven(self):
  with patch('resolve_evidence.shutil.which',return_value=None),patch('resolve_evidence.capture') as cap:
   self.assertEqual(acquire(self.s,self.root/'cap',None,True)['status'],'MAVEN_UNAVAILABLE');cap.assert_not_called()
 def test_partial_capture_not_merged(self):
  with patch('resolve_evidence.shutil.which',return_value='/mvn'),patch('resolve_evidence.capture',return_value={'modules':[{'tree':{'status':'FAILED'}}],'build_fingerprint_changed':False}),patch('resolve_evidence.merge') as m:
   self.assertEqual(acquire(self.s,self.root/'cap',None,True)['status'],'CAPTURE_INCOMPLETE');m.assert_not_called()
 def test_capture_success_path_mock(self):
  a,b=self.trees()
  def fake(p,folder,profiles,approved):
   self.assertTrue(approved);m=folder/'merged';m.mkdir();(m/'tree.json').write_bytes((a if p==self.s else b).read_bytes());(m/'classpath.json').write_text('{}');return {'status':'CAPTURED_UNATTESTED','module_count':1}
  with patch('resolve_evidence.acquire',side_effect=fake) as cap:
   r=run(self.s,CFG,self.root/'out',self.t,approved=True,source_profiles='prod',target_profiles='prod');self.assertEqual(cap.call_count,2)
  self.assertLess(r['final_coverage']['UNKNOWN'],r['initial_coverage']['UNKNOWN']);self.assertEqual(r['gate'],'BLOCKED_PENDING_VERIFIED_EVIDENCE')
 def test_no_output_in_target(self):
  with self.assertRaises(ValueError):run(self.s,CFG,self.t/'report',self.t)
 def test_same_worktree_no_execution(self):
  with self.assertRaises(ValueError):run(self.s,CFG,self.root/'out',self.s,approved=True)
 def test_undertow_default_has_location(self):
  r=run(ROOT/'examples/springboot3-undertow-demo',CFG,self.root/'out');report=json.loads((self.root/'out/scan-summary.json').read_text());rule=next(x for x in report['evaluations'] if x['rule_id']=='WEB-UNDERTOW-006');self.assertEqual(rule['status'],'DETECTED');self.assertTrue(rule['locations']);self.assertEqual(rule['decision'],'VALIDATION_REQUIRED');self.assertIn('RUNTIME',rule['decision_routes'])
if __name__=='__main__':unittest.main()
