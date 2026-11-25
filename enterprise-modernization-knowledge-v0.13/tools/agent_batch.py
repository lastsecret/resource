#!/usr/bin/env python3
"""Prepare a bounded local handoff batch; no external calls and no code edits."""
import argparse,json,sys
from pathlib import Path
from evidence_store import read,verify_queue
from decision_router import digest
from safety import output_dir

def prepare(q,source,target=None,ledger=None,module=None,limit=8,channel='AGENT'):
    tasks=verify_queue(q,source,target)
    if channel not in ('AGENT','EVIDENCE','RUNTIME') or type(limit) is not int or not 1<=limit<=30:raise ValueError('Invalid batch scope')
    done=set()
    if ledger:
        if ledger.get('run_id')!=q['run_id'] or ledger.get('queue_sha256')!=digest(q):raise ValueError('Ledger mismatch')
        done={p['task_id'] for p in ledger['proposals']}
        if not done<=set(tasks):raise ValueError('Unknown ledger task')
    pending=[t for t in q['tasks'] if t['route']==channel and t['task_id'] not in done and (module is None or t['module']==module)]
    pending.sort(key=lambda t:(t['classification']!='BREAKING_CHANGE',str(t['module']),t['rule_id']))
    chosen=pending[:limit];ids={t['task_id'] for t in chosen}
    # only selected tasks, local rule path and locations; no arbitrary source contents
    return {'schema_version':'0.13','run_id':q['run_id'],'queue_sha256':digest(q),'route':channel,'tasks':chosen,'remaining_in_scope':len(pending)-len(chosen),'shared_evidence_work':[dict(g,task_ids=[i for i in g['task_ids'] if i in ids]) for g in q['shared_evidence_work'] if ids.intersection(g['task_ids'])],'response_template':{'schema_version':'0.13','run_id':q['run_id'],'results':[{'task_id':t['task_id'],'decision':'REVIEW_REQUIRED','evidence_refs':[],'missing_evidence':t['missing_evidence'],'verification_status':'NOT_RUN','proposed_fix_id':None,'analysis_note':''} for t in chosen]}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('queue','source','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--target',type=Path);p.add_argument('--ledger',type=Path);p.add_argument('--module');p.add_argument('--limit',type=int,default=8);p.add_argument('--route',choices=('AGENT','EVIDENCE','RUNTIME'),default='AGENT');a=p.parse_args()
    try:
        if a.target and a.output.resolve().is_relative_to(a.target.resolve()):raise ValueError('Output inside target')
        r=prepare(read(a.queue),a.source,a.target,read(a.ledger) if a.ledger else None,a.module,a.limit,a.route);out=output_dir(a.output,a.source)
        (out/'agent-batch.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n');(out/'response-template.json').write_text(json.dumps(r['response_template'],indent=2,ensure_ascii=False)+'\n');print('Batch tasks:',len(r['tasks']));return 0
    except (OSError,ValueError,KeyError,TypeError) as e:print('BATCH_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
