#!/usr/bin/env python3
"""Validate and append structured agent proposals. Local, immutable-by-convention
snapshots; not an authentication service. Never executes a command or approves patches.
Only exact task IDs and local source/target references are accepted. No raw snippets.
"""
import argparse,json,re,sys,hashlib,collections
from pathlib import Path
from safety import output_dir,files
from decision_router import digest,fingerprint
MAX=10_000_000
TOKEN=re.compile(r'^[A-Za-z0-9_.:-]{1,180}$')
DECISIONS={'NO_CHANGE_CANDIDATE','CHANGE_CANDIDATE','VALIDATION_REQUIRED','REVIEW_REQUIRED'}

def read(p):
    p=Path(p)
    if p.stat().st_size>MAX:raise ValueError('Input exceeds limit')
    return json.loads(p.read_text(encoding='utf8'))

def verify_queue(q,source,target):
    if q.get('schema_version')!='0.13' or q.get('run_id')!=digest(q['identity']) or q.get('task_manifest_sha256')!=digest(q['tasks']):raise ValueError('Queue identity invalid')
    identity=q['identity']
    if identity['source']!=fingerprint(source) or identity['target']!=fingerprint(target):raise ValueError('Project scope changed; rescan')
    catalog=read(Path(__file__).resolve().parents[1]/'catalog.json')['rules']
    if identity['catalog_sha256']!=digest(catalog):raise ValueError('Knowledge catalog changed; rescan')
    tasks={}
    for t in q['tasks']:
        k=t['task_id']
        if k in tasks or k!=digest([q['run_id'],t['rule_id'],t['module']])[:24]:raise ValueError('Invalid or duplicate task')
        tasks[k]=t
    return tasks

def import_results(q,response,source,target=None,previous=None):
    tasks=verify_queue(q,source,target)
    if set(response)!={'schema_version','run_id','results'} or response['schema_version']!='0.13' or response['run_id']!=q['run_id'] or not isinstance(response['results'],list):raise ValueError('Response contract or run mismatch')
    roots={'source':Path(source).resolve(),'target':Path(target).resolve() if target else None}
    # Only discoverable bounded files, excluding symlink and special files.
    allowed={side:{p.relative_to(root).as_posix():p for p in files(root)} if root else {} for side,root in roots.items()}
    existing={}
    if previous:
        if previous.get('run_id')!=q['run_id'] or previous.get('queue_sha256')!=digest(q):raise ValueError('Previous ledger scope mismatch')
        for p in previous['proposals']:
            if p['task_id'] not in tasks or p['task_id'] in existing:raise ValueError('Previous ledger malformed')
            if p.get('state')!='PENDING_HUMAN_AND_EVIDENCE_REVIEW' or p.get('automatic_patch') is not False:raise ValueError('Previous ledger must be pending review')
            existing[p['task_id']]=p
    batch=set()
    for r in response['results']:
        if not {'task_id','decision','evidence_refs','missing_evidence','verification_status','proposed_fix_id'}<=set(r) or set(r)-{'task_id','decision','evidence_refs','missing_evidence','verification_status','proposed_fix_id','analysis_note'}:raise ValueError('Unexpected response field')
        note=r.get('analysis_note','')
        if not isinstance(note,str) or len(note)>12000:raise ValueError('Analysis note limit')
        k=r['task_id']; t=tasks.get(k)
        if not t or k in batch or k in existing:raise ValueError('Unknown/duplicate task; ledger is append-only')
        batch.add(k)
        if r['decision'] not in DECISIONS or r['verification_status'] not in ('NOT_RUN','OBSERVATION_IMPORTED','FAILED'):raise ValueError('Unsupported claim')
        fix=r['proposed_fix_id']
        if fix is not None and (not isinstance(fix,str) or not TOKEN.fullmatch(fix)):raise ValueError('Invalid fix identifier')
        if t['classification']=='VALIDATION_ONLY' and (fix is not None or r['decision']=='CHANGE_CANDIDATE'):raise ValueError('Validation-only cannot propose edits')
        if r['decision']=='CHANGE_CANDIDATE' and not fix:raise ValueError('Change proposal requires fix identifier')
        if r['decision']!='CHANGE_CANDIDATE' and fix is not None:raise ValueError('Fix on non-change proposal')
        if not isinstance(r['missing_evidence'],list) or not all(isinstance(x,str) and TOKEN.fullmatch(x) for x in r['missing_evidence']):raise ValueError('Missing evidence identifiers invalid')
        refs=[]
        if not isinstance(r['evidence_refs'],list) or len(r['evidence_refs'])>100:raise ValueError('Reference limit')
        for e in r['evidence_refs']:
            if set(e)!={'side','path','line'} or e['side'] not in allowed or not isinstance(e['path'],str) or type(e['line']) is not int or e['line']<1:raise ValueError('Invalid reference')
            p=allowed[e['side']].get(e['path'])
            if not p:raise ValueError('Reference outside discovered project scope')
            b=p.read_bytes()
            if e['line']>len(b.splitlines()):raise ValueError('Reference line outside file')
            refs.append({**e,'sha256':hashlib.sha256(b).hexdigest()})
        if r['decision'] in ('NO_CHANGE_CANDIDATE','CHANGE_CANDIDATE') and (not refs or r['missing_evidence']):raise ValueError('Decision proposal requires references and no declared missing evidence')
        existing[k]={**r,'evidence_refs':refs,'rule_id':t['rule_id'],'module':t['module'],'state':'PENDING_HUMAN_AND_EVIDENCE_REVIEW','automatic_patch':False}
    return {'schema_version':'0.13','run_id':q['run_id'],'queue_sha256':digest(q),'previous_ledger_sha256':digest(previous) if previous else None,'proposals':[existing[k] for k in sorted(existing)],'counts':dict(collections.Counter(x['decision'] for x in existing.values())),'remaining_tasks':sorted(set(tasks)-set(existing)),'pending_review_task_ids':sorted(existing),'unresolved_task_ids':sorted(tasks),'gate':'BLOCKED_PENDING_VERIFIED_EVIDENCE','note':'Local ledger may contain private analysis notes; do not upload. Agent assertions and source references are not verification. Human review and independent regression remain required.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('queue','response','source','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--target',type=Path);p.add_argument('--previous',type=Path);a=p.parse_args()
    try:
        if a.target and a.output.resolve().is_relative_to(a.target.resolve()):raise ValueError('Output inside target')
        r=import_results(read(a.queue),read(a.response),a.source,a.target,read(a.previous) if a.previous else None)
        out=output_dir(a.output,a.source);(out/'evidence-ledger.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print('Proposals stored for review:',len(r['proposals']));return 2
    except (OSError,ValueError,KeyError,TypeError,AttributeError,RecursionError) as e:print('EVIDENCE_IMPORT_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
