import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from migration_scan import analyze
class TestUnifiedScan(unittest.TestCase):
 def test_unified_35_to_41_scanner(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'pom.xml').write_text('<project/>')
   (p/'Dockerfile').write_text('RUN java -Djarmode=layertools -jar app.jar extract')
   cfg=json.loads((ROOT/'examples'/'java17-to-boot413.json').read_text())
   res=analyze(p,cfg)
   self.assertEqual(len(res['route']['rule_ids']),93)
   self.assertEqual(res['preflight']['status'],'REVIEW_REQUIRED')
   self.assertIn('SB41-LAYERTOOLS-002',{x['rule_id'] for x in res['boot41']['findings']})
if __name__=='__main__':unittest.main()
