import json, unittest, yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestJacksonEffectiveRules(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.obj=yaml.safe_load((ROOT/'rules/jackson-2-to-3-effective-config.yaml').read_text())
  cls.rules={r['id']:r for r in cls.obj['rules']}
  cls.cat=json.loads((ROOT/'catalog.json').read_text())
 def test_new_and_old_rule_ids(self):
  self.assertEqual(len(self.cls_rules()),3)
  ids=[r['id'] for r in self.cat['rules']]
  self.assertEqual(len(ids),len(set(ids)))
  self.assertEqual(len(ids),80)
 def cls_rules(self): return self.rules
 def test_defaults_and_no_auto_patch(self):
  self.assertEqual(self.rules['JCK3-NULL-PRIMITIVES-001']['behavior']['library_default_when_no_override'], {'jackson_2':False,'jackson_3':True})
  self.assertEqual(self.rules['JCK3-POJO-ORDER-002']['behavior']['library_default_when_no_override'], {'jackson_2':False,'jackson_3':True})
  for r in self.rules.values():
   self.assertFalse(r['actionable'])
   self.assertFalse(r['migration_evidence_v0_5']['remediation_policy']['automatic_patch'])
 def test_all_mapper_origins_and_properties(self):
  inventory=self.rules['JCK3-MAPPER-TOPOLOGY-003']['investigation']['mapper_discovery']
  text=' '.join(inventory['scan_source_code_and_configuration'])
  for term in ['new JsonMapper','new ObjectMapper','JsonMapper.builder','@Bean','application.properties','application.yml']:
   self.assertIn(term,text)
  for r in self.rules.values():
   self.assertIn('ASSUME_MANUAL_NEW_INHERITS_SPRING_PROPERTIES',r['prohibited'])
 def test_classification_and_sources(self):
  self.assertEqual([r['rule_type'] for r in self.rules.values()],['BEHAVIOR_CHANGE','BEHAVIOR_CHANGE','VALIDATION_ONLY'])
  src={s['id'] for s in yaml.safe_load((ROOT/'sources.yaml').read_text())['sources']}
  for r in self.rules.values():
   self.assertTrue(set(r['sources'])<=src)
 def test_acceptance_coverage(self):
  cases=yaml.safe_load((ROOT/'acceptance-cases.yaml').read_text())['cases']
  names={c['id']:c for c in cases}
  for i in range(1,16):
   c=names[f'T-JCK3-{i:02}']
   self.assertEqual(c['actual_result'],'NOT_RUN')
   self.assertFalse(c['automatic_patch_expected'])
 def test_old_jackson_rules_reference_new(self):
  old=yaml.safe_load((ROOT/'rules/spring-boot-4-common.yaml').read_text())['rules']
  for item in old:
   if item['id'] in ('SB4-JACKSON-MODULE-005','SB4-JACKSON-API-006'):
    self.assertIn('JCK3-MAPPER-TOPOLOGY-003',item['related_rules_v0_6'])
if __name__=='__main__':unittest.main()
