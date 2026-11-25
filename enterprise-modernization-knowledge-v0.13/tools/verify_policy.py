from pathlib import Path
import json, yaml, sys
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
rules = []
seen = set()
for p in sorted((ROOT / 'rules').glob('*.yaml')):
    raw = yaml.safe_load(p.read_text())
    if not raw['schema_version'] == '0.5':
        raise ValueError(p)
    for rule in raw['rules']:
        rid = rule['id']
        if not rid not in seen:
            raise ValueError(rid)
        seen.add(rid)
        if not rule['rule_type'] in {'BREAKING_CHANGE', 'BEHAVIOR_CHANGE', 'REGRESSION', 'VALIDATION_ONLY'}:
            raise ValueError('Policy invariant failed')
        m = rule['migration_evidence_v0_5']
        if not m['classification'] == rule['rule_type']:
            raise ValueError('Policy invariant failed')
        if not m['runtime_validation'] == 'NOT_RUN':
            raise ValueError('Policy invariant failed')
        if not m['remediation_policy']['automatic_patch'] is False:
            raise ValueError('Policy invariant failed')
        if not rule['actionable'] is False:
            raise ValueError('Policy invariant failed')
        if not 'evidence_class' not in rule:
            raise ValueError('Policy invariant failed')
        if rule['rule_type'] == 'VALIDATION_ONLY':
            if not m['remediation_policy']['mode'] == 'VERIFY_ONLY_NO_PATCH':
                raise ValueError('Policy invariant failed')
            if not m['evidence_status'] == 'NO_EXACT_VERSION_DELTA_ESTABLISHED':
                raise ValueError('Policy invariant failed')
        if rule['rule_type'] == 'REGRESSION':
            if not m['trigger']['exact_affected_target'] == '7.0.0':
                raise ValueError('Policy invariant failed')
        rules.append(rule)
catalog = json.loads((ROOT / 'catalog.json').read_text())
new_delta = json.loads((ROOT / 'deltas' / 'spring-boot-4.0-to-4.1.json').read_text())['rules']
for r in new_delta:
    if not r['id'] not in seen:
        raise ValueError(r['id'])
    if not r['classification'] in {'BREAKING_CHANGE', 'BEHAVIOR_CHANGE', 'REGRESSION', 'VALIDATION_ONLY'}:
        raise ValueError('Policy invariant failed')
    if not (r['automatic_patch'] is False and r['runtime_validation'] == 'NOT_RUN'):
        raise ValueError('Policy invariant failed')
    if not r['source']['status'] == 'OFFICIAL_RELEASE_NOTES_CHECKED':
        raise ValueError('Policy invariant failed')
    seen.add(r['id'])
extra=json.loads((ROOT/'deltas/component-deltas-v09.json').read_text())['rules']
for r in extra:
    if r['id'] in seen or r['automatic_patch'] is not False or r['runtime_validation']!='NOT_RUN':raise ValueError('Bad component delta')
    seen.add(r['id'])
if not len(catalog['rules']) == len(rules) + len(new_delta) + len(extra):
    raise ValueError('Policy invariant failed')
if not {r['id'] for r in catalog['rules']} == seen:
    raise ValueError('Policy invariant failed')
source_ids = {s['id'] for s in yaml.safe_load((ROOT / 'sources.yaml').read_text())['sources']}
for r in rules:
    if not all((ref['source_id'] in source_ids for ref in r['migration_evidence_v0_5']['evidence']['references'])):
        raise ValueError(r['id'])
checks = yaml.safe_load((ROOT / 'acceptance-cases.yaml').read_text())
if not len({c['id'] for c in checks['cases']}) == len(checks['cases']):
    raise ValueError('Policy invariant failed')
for c in checks['cases']:
    if not c['actual_result'] == 'NOT_RUN':
        raise ValueError('Policy invariant failed')
    if not c['automatic_patch_expected'] is False:
        raise ValueError('Policy invariant failed')
    if c['rule_ref'] not in (None, 'RUNTIME-JAVA-PARAMETERIZED'):
        if not c['rule_ref'] in seen:
            raise ValueError('Policy invariant failed')
ver = yaml.safe_load((ROOT / 'verification-catalog.yaml').read_text())
mig = yaml.safe_load((ROOT / 'migration-rules.yaml').read_text())
if not set(ver['rule_ids']) == {r['id'] for r in rules if r['rule_type'] == 'VALIDATION_ONLY'} | {r['id'] for r in new_delta+extra if r['classification'] == 'VALIDATION_ONLY'}:
    raise ValueError('Policy invariant failed')
if not set(mig['rule_ids']) == {r['id'] for r in rules if r['rule_type'] != 'VALIDATION_ONLY'} | {r['id'] for r in new_delta+extra if r['classification'] != 'VALIDATION_ONLY'}:
    raise ValueError('Policy invariant failed')
print('PASS:', len(rules) + len(new_delta) + len(extra), 'rules;', len(checks['cases']), 'acceptance cases;', Counter((r['classification'] for r in catalog['rules'])))
# registry, offline summary hashes and classification consistency
import hashlib,re
registry=json.loads((ROOT/'detectors/registry.json').read_text())['rules']
if set(registry)!=seen:raise ValueError('Detector coverage index mismatch')
for rid,d in registry.items():
    if d['detector'] not in ('none','text','legacy','boot41'):raise ValueError(rid)
    if d['detector']=='text':re.compile(d['regex'])
    if d.get('component'):
        from inventory import version
        if not version(d['component']['crosses']):raise ValueError(rid)
for r in extra:
    if r['source_id'] not in source_ids:raise ValueError(r['id'])
for f in json.loads((ROOT/'sources/manifest.json').read_text())['files']:
    if hashlib.sha256((ROOT/'sources'/f['path']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Source summary integrity mismatch')
if any(r['auto_remediation_allowed'] is not False for r in catalog['rules']):raise ValueError('Unexpected auto remediation')

from declarative import load_plans
plans=load_plans()
if set(plans)!=seen:raise ValueError("Execution plan coverage mismatch")
print("PASS: execution plans",len(plans),"candidate detectors",sum(d["detector"]!="none" or bool(plans[r].get("match_any")) for r,d in registry.items()))
