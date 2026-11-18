from pathlib import Path
import json, yaml, sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
rules=[]; seen=set()
for p in sorted((ROOT/'rules').glob('*.yaml')):
    raw=yaml.safe_load(p.read_text())
    assert raw['schema_version']=='0.5',p
    for rule in raw['rules']:
        rid=rule['id']; assert rid not in seen, rid; seen.add(rid)
        assert rule['rule_type'] in {'BREAKING_CHANGE','BEHAVIOR_CHANGE','REGRESSION','VALIDATION_ONLY'}
        m=rule['migration_evidence_v0_5']
        assert m['classification']==rule['rule_type']
        assert m['runtime_validation']=='NOT_RUN'
        assert m['remediation_policy']['automatic_patch'] is False
        assert rule['actionable'] is False
        assert 'evidence_class' not in rule
        if rule['rule_type']=='VALIDATION_ONLY':
            assert m['remediation_policy']['mode']=='VERIFY_ONLY_NO_PATCH'
            assert m['evidence_status']=='NO_EXACT_VERSION_DELTA_ESTABLISHED'
        if rule['rule_type']=='REGRESSION':
            assert m['trigger']['exact_affected_target']=='7.0.0'
        rules.append(rule)
catalog=json.loads((ROOT/'catalog.json').read_text())
assert len(catalog['rules'])==len(rules)
assert {r['id'] for r in catalog['rules']} == seen
source_ids={s['id'] for s in yaml.safe_load((ROOT/'sources.yaml').read_text())['sources']}
for r in rules:
    assert all(ref['source_id'] in source_ids for ref in r['migration_evidence_v0_5']['evidence']['references']),r['id']
checks=yaml.safe_load((ROOT/'acceptance-cases.yaml').read_text())
assert len({c['id'] for c in checks['cases']})==len(checks['cases'])
for c in checks['cases']:
    assert c['actual_result']=='NOT_RUN'
    assert c['automatic_patch_expected'] is False
    if c['rule_ref'] not in (None,'RUNTIME-JAVA-PARAMETERIZED'): assert c['rule_ref'] in seen
ver=yaml.safe_load((ROOT/'verification-catalog.yaml').read_text())
mig=yaml.safe_load((ROOT/'migration-rules.yaml').read_text())
assert set(ver['rule_ids']) == {r['id'] for r in rules if r['rule_type']=='VALIDATION_ONLY'}
assert set(mig['rule_ids']) == {r['id'] for r in rules if r['rule_type']!='VALIDATION_ONLY'}
print('PASS:',len(rules),'rules;',len(checks['cases']),'acceptance cases;',Counter(r['rule_type'] for r in rules))
