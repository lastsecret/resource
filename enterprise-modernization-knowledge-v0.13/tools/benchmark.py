#!/usr/bin/env python3
"""Score A/B/C experiments against independently adjudicated change IDs.
Run agents externally in clean disposable worktrees. Never infer missing telemetry as zero.
"""
import argparse,json,statistics,sys,math
from pathlib import Path
from safety import output_file
from decision_router import digest

def evaluate(oracle,observations):
    expected=oracle['required_change_ids']; optional=oracle.get('non_change_ids',[])
    if not isinstance(expected,list) or not isinstance(optional,list) or any(not isinstance(x,str) for x in expected+optional) or len(set(expected+optional))!=len(expected+optional) or not expected:raise ValueError('Invalid independent oracle')
    truth=set(expected);known=truth|set(optional);groups={k:[] for k in ('A','B','C')};seen=set();settings=None
    for x in observations['runs']:
        arm=x['arm'];run=x['run_id'];s=x['conditions'];key=(arm,run)
        if arm not in groups or key in seen:raise ValueError('Duplicate or invalid run')
        seen.add(key)
        if not isinstance(s,dict) or any(not isinstance(s.get(k),str) or not s[k] for k in ('source_snapshot','target_version','java_target','model','prompt_revision','runtime_test_revision')):raise ValueError('Missing comparison conditions')
        if settings is None:settings=s
        if settings!=s:raise ValueError('Experiment conditions differ')
        changes=x['proposed_change_ids']
        if not isinstance(changes,list) or any(not isinstance(v,str) for v in changes) or len(set(changes))!=len(changes):raise ValueError('Duplicate or invalid change IDs')
        predictions=set(changes);tp=len(predictions&truth);fp=len(predictions&set(optional));fn=len(truth-predictions);unadjudicated=len(predictions-known)
        stats={k:x.get(k) for k in ('input_tokens','output_tokens','elapsed_seconds','human_interventions','regression_passed','regression_total','evidence_complete','evidence_total')}
        if any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or v<0 or not math.isfinite(v)) for v in stats.values()):raise ValueError('Invalid telemetry')
        for a,b in [('regression_passed','regression_total'),('evidence_complete','evidence_total')]:
            if stats[a] is not None and (stats[b] is None or stats[a]>stats[b]):raise ValueError('Invalid metric pair')
        groups[arm].append({'run_id':run,'tp':tp,'fp_adjudicated':fp,'fn':fn,'unadjudicated':unadjudicated,'precision':tp/(tp+fp) if tp+fp and not unadjudicated else None,'recall':tp/len(truth),'unnecessary_changes':fp if not unadjudicated else None,'regression_pass_rate':stats['regression_passed']/stats['regression_total'] if stats['regression_passed'] is not None and stats['regression_total'] else None,'evidence_completeness':stats['evidence_complete']/stats['evidence_total'] if stats['evidence_complete'] is not None and stats['evidence_total'] else None,**stats})
    summary={}
    for arm,rows in groups.items():
        metrics={}
        for k in ('precision','recall','unnecessary_changes','input_tokens','output_tokens','elapsed_seconds','human_interventions','regression_pass_rate','evidence_completeness'):
            values=[r[k] for r in rows if r[k] is not None];metrics[k]={'median':statistics.median(values) if values else None,'observations':len(values)}
        summary[arm]={'runs':len(rows),'metrics':metrics,'details':rows}
    return {'schema_version':'0.13','oracle_sha256':digest(oracle),'conditions_sha256':digest(settings),'status':'COMPARISON_READY' if min(len(x) for x in groups.values())>=3 and len({len(x) for x in groups.values()})==1 else 'INSUFFICIENT_BALANCED_REPETITIONS','arms':summary,'note':'User-reported metrics and independently adjudicated IDs; not an attestation. Unadjudicated changes suppress precision. No automatic claim of improvement.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--oracle',required=True,type=Path);p.add_argument('--observations',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try:
        result=evaluate(json.loads(a.oracle.read_text()),json.loads(a.observations.read_text()))
        # exclusive write, no arbitrary command execution
        with a.output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
        return 0
    except (OSError,ValueError,TypeError,KeyError) as e:print('BENCHMARK_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
