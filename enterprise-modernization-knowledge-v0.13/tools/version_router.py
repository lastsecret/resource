#!/usr/bin/env python3
"""Version-stage rule selector for Spring Boot 3.5/4.0/4.1.
Pure stdlib. This returns CANDIDATES; it never applies source changes.
"""
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def minor(v):
    if not isinstance(v,str): return None
    m=re.fullmatch(r'(\d+)\.(\d+)(?:\.[0-9]+(?:[-+][A-Za-z0-9_.-]+)?)?',v.strip())
    return f'{m.group(1)}.{m.group(2)}' if m else None

def route(source,target,manifest=None):
    manifest=manifest or json.loads((ROOT/'deltas'/'manifest.json').read_text(encoding='utf-8'))
    def release(v):
        if not isinstance(v,str) or not re.fullmatch(r'\d+\.\d+\.\d+',v):return None
        return tuple(map(int,v.split('.')))
    a_full,b_full=release(source),release(target)
    if a_full is None or b_full is None:
        return {'status':'REVIEW_REQUIRED','stages':[],'rule_ids':[],'issues':[{'code':'NON_RELEASE_OR_INCOMPLETE_VERSION'}],'automatic_patch':False}
    if b_full<a_full:
        return {'status':'BLOCK','stages':[],'rule_ids':[],'issues':[{'code':'DOWNGRADE_NOT_SUPPORTED'}],'automatic_patch':False}
    src,tgt=minor(source),minor(target)
    seq=['3.5','4.0','4.1']
    if src not in seq or tgt not in seq or tgt=="3.5":
        return {'status':'REVIEW_REQUIRED','stages':[],'rule_ids':[], 'issues':[{'code':'UNSUPPORTED_VERSION_ROUTE','source':source,'target':target}], 'automatic_patch':False}
    a,b=seq.index(src),seq.index(tgt)
    if b<a:
        return {'status':'BLOCK','stages':[],'rule_ids':[],'issues':[{'code':'DOWNGRADE_NOT_SUPPORTED'}],'automatic_patch':False}
    picked=manifest['stages'][a:b]
    ids=list(dict.fromkeys(r for x in picked for r in x['rule_ids']))
    return {'status':'CANDIDATES_SELECTED','stages':[x['id'] for x in picked], 'rule_ids':ids,'issues':([{'code':'PATCH_LEVEL_KNOWLEDGE_INCOMPLETE'}] if a==b else []), 'automatic_patch':False,
      'notes':['Rules crossing 4.0 do not require an actual 4.0 deploy.','Each finding still requires project usage, effective config and evidence; no automatic edits.']}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True,type=Path);p.add_argument('--output',type=Path); a=p.parse_args()
    cfg=json.loads(a.config.read_text(encoding='utf8'))
    report=route(cfg.get('source',{}).get('spring_boot_version'),cfg.get('target',{}).get('spring_boot_version'))
    s=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        with a.output.open('x',encoding='utf-8') as f:f.write(s)
    print(s,end='')
    return 0 if report['status']=='CANDIDATES_SELECTED' else 2
if __name__=='__main__':raise SystemExit(main())
