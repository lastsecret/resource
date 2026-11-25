import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from version_router import route
from scan_boot41 import scan
from validate_migration import evaluate
MATRIX=json.loads((ROOT/'compatibility'/'java-minimums.json').read_text())
CFG=json.loads((ROOT/'examples'/'java17-to-boot413.json').read_text())
class RouteTests(unittest.TestCase):
 def test_35_to_41_is_composed(self):
  r=route('3.5.7','4.1.3')
  self.assertEqual(r['stages'],['spring-boot-3.5-to-4.0','spring-boot-4.0-to-4.1'])
  self.assertEqual(len(r['rule_ids']),93)
 def test_40_to_41_only_delta(self):
  r=route('4.0.9','4.1.3');self.assertEqual(len(r['rule_ids']),11)
 def test_35_to_40_remains_supported(self):
  r=route('3.5.7','4.0.10');self.assertEqual(len(r['rule_ids']),82)
 def test_unsupported_unknown(self):
  self.assertEqual(route('3.5.7','4.2.0')['status'],'REVIEW_REQUIRED')
 def test_downgrade_blocked(self):
  self.assertEqual(route('4.1.3','4.0.9')['status'],'BLOCK')
 def test_java17_requires_dependency_graph_confirmation(self):
  r=evaluate(CFG,MATRIX)
  self.assertEqual(r['status'],'REVIEW_REQUIRED')
  self.assertIn('BOOT41_DEPENDENCY_GRAPH_UNVERIFIED',[x['code'] for x in r['issues']])
 def test_java17_with_verified_components_remains_permitted(self):
  c=copy.deepcopy(CFG);c['evidence']={'dependency_graph_verified':True}
  self.assertEqual(evaluate(c,MATRIX)['status'],'REVIEW_REQUIRED')
 def test_java17_jooq_oss_blocks(self):
  c=json.loads((ROOT/'examples'/'java17-to-boot413-jooq-block.json').read_text())
  r=evaluate(c,MATRIX)
  self.assertIn('JDK_BELOW_MINIMUM',[x['code'] for x in r['issues']])
 def test_scanner_finds_only_candidates_and_does_not_edit(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'pom.xml').write_text('<project><dependencies><dependency><artifactId>jooq</artifactId></dependency></dependencies></project>')
   (p/'Dockerfile').write_text('RUN java -Djarmode=layertools -jar app.jar extract\n')
   (p/'application.properties').write_text('spring.data.jpa.repositories.bootstrap-mode=deferred\n')
   before=[(f,f.read_bytes()) for f in p.iterdir()]
   r=scan(p,'3.5.7','4.1.3')
   found={x['rule_id'] for x in r['findings']}
   self.assertTrue({'SB41-LAYERTOOLS-002','SB41-JPA-DEFERRED-004','SB41-JOOQ-JDK-008'}.issubset(found))
   self.assertTrue(all(not x['automatic_patch'] and x['decision']=='REVIEW_REQUIRED' for x in r['findings']))
   self.assertEqual(before,[(f,f.read_bytes()) for f in p.iterdir()])
 def test_40_to_40_scanner_has_no_41_findings(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'Dockerfile').write_text('RUN java -Djarmode=layertools -jar app.jar extract\n')
   self.assertEqual(scan(p,'4.0.0','4.0.9')['findings'],[])
if __name__=='__main__': unittest.main()
