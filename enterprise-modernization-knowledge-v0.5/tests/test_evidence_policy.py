import unittest, yaml, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestEvidencePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'catalog.json').read_text())
        cls.byid={r['id']:r for r in cls.catalog['rules']}
    def test_validation_cases_have_no_auto_remediation(self):
        self.assertTrue(all(not r['auto_remediation_allowed'] for r in self.catalog['rules'] if r['classification']=='VALIDATION_ONLY'))
    def test_original_rule_count_preserved(self):
        original=[r for r in self.catalog['rules'] if not r['family'].startswith(('hikaricp','oracle-jdbc'))]
        self.assertEqual(len(original),63)
    def test_new_hikari_oracle_scopes(self):
        self.assertEqual(len([r for r in self.catalog['rules'] if r['family']=='hikaricp-6-to-7']),6)
        self.assertEqual(len([r for r in self.catalog['rules'] if r['family']=='oracle-jdbc-23-7-to-23-9']),8)
    def test_regression_limited_to_7_0_0(self):
        self.assertEqual(self.byid['HCP7-SCHEMA-001']['classification'],'REGRESSION')
        rr=yaml.safe_load((ROOT/'rules'/'hikaricp-6-to-7.yaml').read_text())['rules'][0]
        self.assertEqual(rr['migration_evidence_v0_5']['trigger']['exact_affected_target'],'7.0.0')
    def test_unknown_oracle_is_validation_only(self):
        self.assertTrue(all(r['classification']=='VALIDATION_ONLY' for r in self.catalog['rules'] if r['family']=='oracle-jdbc-23-7-to-23-9'))
    def test_sources_and_rule_lists_are_all_stable(self):
        ver=yaml.safe_load((ROOT/'verification-catalog.yaml').read_text())['rule_ids']
        mig=yaml.safe_load((ROOT/'migration-rules.yaml').read_text())['rule_ids']
        self.assertEqual(len(ver)+len(mig),len(self.catalog['rules']))
        self.assertEqual(set(ver)&set(mig),set())
if __name__=='__main__':unittest.main()
