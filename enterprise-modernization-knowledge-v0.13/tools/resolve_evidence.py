#!/usr/bin/env python3
"""Evidence acquisition orchestration. Read-only scan; Maven execution explicitly approved.
Never infer dependency absence from a declaration or partial graph; never auto-approve.
"""
import argparse, collections, json, sys, shutil, os
from pathlib import Path
from migration_scan import analyze
from config_contract import errors
from inventory import snapshot,attest_capture,import_tree
from artifact_diffs import attach
from runtime_evidence import compare as compare_runtime
from maven_inventory import capture, merge, plan
from safety import output_dir
from decision_router import route as route_decisions
from project_scanner import markdown, candidate_properties


def blockers(report):
    groups=collections.defaultdict(list)
    for r in report.get('evaluations',[]):
        if r['status'] not in ('UNKNOWN','NOT_EVALUATED'):continue
        app=r['applicability']; rid=r['rule_id']
        if app=='UNKNOWN_COMPONENT_PAIR':reason='MISSING_COMPONENT_GRAPH'
        elif app=='UNKNOWN_OR_NO_PAIR_MATCH':reason='COMPONENT_PAIR_OR_COMPLETENESS_UNPROVEN'
        elif app=='IMPORTED_PAIR_OUT_OF_SCOPE':reason='IMPORTED_SCOPE_NOT_ATTESTED'
        elif rid=='SB4-PROPERTIES-004':reason='CONFIG_METADATA_DIFF_REQUIRED'
        elif rid=='SB41-DEPRECATED-001':reason='JAR_API_DIFF_REQUIRED'
        elif rid=='SB41-DEPENDENCY-BOM-011':reason='DEPENDENCY_GRAPH_DIFF_REQUIRED'
        else:reason='SCAN_OR_SCOPE_EVIDENCE_REQUIRED'
        groups[reason].append(rid)
    return [{'reason':k,'count':len(v),'rule_ids':sorted(v),'next_action':{
        'MISSING_COMPONENT_GRAPH':'Acquire source and target dependency trees once per approved profile/module scope.',
        'COMPONENT_PAIR_OR_COMPLETENESS_UNPROVEN':'Review captured module/profile coverage, missing or changed artifact coordinates and graph completeness.',
        'IMPORTED_SCOPE_NOT_ATTESTED':'Verify imported graph provenance and scope before excluding rules.',
        'CONFIG_METADATA_DIFF_REQUIRED':'Compare exact source/target Spring configuration metadata; paired artifact evidence or broader comparison required.',
        'JAR_API_DIFF_REQUIRED':'Compare exact source/target public JAR APIs and references; paired artifact evidence or broader comparison required.',
        'DEPENDENCY_GRAPH_DIFF_REQUIRED':'Review resolved per-module graph differences; paired artifact evidence or broader comparison required.',
        'SCAN_OR_SCOPE_EVIDENCE_REQUIRED':'Review scan omissions, active profiles and source locations; capture runtime evidence if required.'}[k]} for k,v in sorted(groups.items())]


def acquire(project, folder, profiles, approved):
    """One acquisition per side; only complete successful exports enter automatic evaluation.
    Captured data remains unverified: -N is not effective reactor resolution.
    """
    if not approved:return {'status':'APPROVAL_REQUIRED'}
    if not shutil.which('mvn'):return {'status':'MAVEN_UNAVAILABLE'}
    if os.name=='nt':return {'status':'WINDOWS_MANUAL_EXPORT_REQUIRED'}
    try:
        result=capture(project,folder/'capture',profiles,True)
        modules=result.get('modules',[])
        if not modules or result['build_fingerprint_changed'] or any(x['tree']['status']!='EXIT_ZERO' for x in modules):
            return {'status':'CAPTURE_INCOMPLETE','module_count':len(modules)}
        manifest=json.loads((folder/'capture'/'plan.json').read_text())
        merged=merge(project,folder/'capture',manifest,folder/'merged')
        if merged['missing_modules'] or merged['failed_modules'] or merged['build_fingerprint_changed']:
            return {'status':'MERGE_INCOMPLETE','module_count':len(modules)}
        side=import_tree(folder/'merged/tree.json')
        attested=attest_capture(side,project,result,merged,manifest,profiles)
        return {'status':'CAPTURED_SCOPED' if attested else 'CAPTURED_UNATTESTED','module_count':len(modules),'inventory_side':side}
    except (OSError,ValueError,KeyError,TypeError):return {'status':'CAPTURE_OR_MERGE_FAILED'}


def counts(r):return r.get('coverage',{})

def run(project,config,out,target=None,source_tree=None,target_tree=None,classpath=None,approved=False,source_profiles=None,target_profiles=None,target_classpath=None,runtime_source=None,runtime_target=None):
    project=Path(project).resolve(strict=True); target=Path(target).resolve(strict=True) if target else None
    if not project.is_dir() or (target and not target.is_dir()):raise ValueError('Project directory required')
    if errors(config):raise ValueError('Invalid migration config')
    if bool(source_tree)!=bool(target_tree) or (source_tree and not target):raise ValueError('Both trees and target project required')
    if approved and (not target or target==project or target.is_relative_to(project) or project.is_relative_to(target)):
        raise ValueError('Approved capture requires distinct non-nested source and target worktrees')
    if approved and source_tree:raise ValueError('Choose import or capture, not both')
    if bool(runtime_source)!=bool(runtime_target) or (runtime_source and not target):raise ValueError('Paired runtime observations and target required')
    if target_classpath and (not classpath or not target):raise ValueError('Paired classpath manifests and target required')
    if target and Path(out).resolve().is_relative_to(target):raise ValueError('Output must be outside target')
    out=output_dir(out,project)
    first=analyze(project,config,ast=True)
    actions=[{'action':'JAVA_AST','status':first.get('declarative_scan',{}).get('ast',{}).get('status','NOT_RUN')}]
    graph=None; cp=None; target_cp=None; final=first
    if first['route']['status']=='CANDIDATES_SELECTED' and first['preflight']['status']!='BLOCK':
        if source_tree:
            graph=snapshot(source_tree,target_tree,project,target)
            actions.append({'action':'IMPORT_COMPONENT_PAIR','status':'IMPORTED_UNATTESTED'})
        elif target:
            acquired={}
            for label,p,profile in [('source',project,source_profiles),('target',target,target_profiles)]:
                # Emit safe plan even if capture cannot run. The report must remain outside both projects.
                side=out/label;side.mkdir()
                (side/'plan.json').write_text(json.dumps(plan(p,side/'capture',profile),indent=2)+'\n')
                result=acquire(p,side,profile,approved)
                acquired[label]=result
                actions.append({'action':'CAPTURE_'+label.upper(),'status':result['status'],**{k:v for k,v in result.items() if k not in ('status','inventory_side')}})
            if all(x['status'] in ('CAPTURED_UNATTESTED','CAPTURED_SCOPED') for x in actions[-2:]):
                graph=snapshot(out/'source/merged/tree.json',out/'target/merged/tree.json',project,target)
                for label,rec in acquired.items():
                    if rec.get('inventory_side',{}).get('sha256')==graph[label]['sha256'] and rec['status']=='CAPTURED_SCOPED':graph[label]=rec['inventory_side']
                cp=json.loads((out/'source/merged/classpath.json').read_text())
                if all(graph[side].get('provenance')=='SCANNER_CAPTURED_LOCAL' for side in ('source','target')):
                    target_cp=json.loads((out/'target/merged/classpath.json').read_text())
        else:
            actions.append({'action':'ACQUIRE_COMPONENT_PAIR','status':'TARGET_WORKTREE_REQUIRED'})
            (out/'source-inventory-plan.json').write_text(json.dumps(plan(project,out/'source-export',source_profiles),indent=2)+'\n')
        if classpath:
            cp=json.loads(Path(classpath).read_text(encoding='utf8'))
            if not isinstance(cp,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in cp.items()):raise ValueError('Invalid approved classpath manifest')
        if target_classpath:
            target_cp=json.loads(Path(target_classpath).read_text(encoding='utf8'))
            if not isinstance(target_cp,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in target_cp.items()):raise ValueError('Invalid target classpath manifest')
        if graph or cp:
            final=analyze(project,config,graph,ast=True,attribute=bool(cp),classpaths=cp)
            actions.append({'action':'REEVALUATE_RULES','status':'EXECUTED','attribution':final.get('declarative_scan',{}).get('ast',{}).get('status','NOT_RUN')})
    else:actions.append({'action':'ACQUIRE_COMPONENT_PAIR','status':'BLOCKED_BY_PREFLIGHT_OR_ROUTE'})
    if final.get('evaluations'):
        attach(final,project,cp,target_cp)
        if target_cp:actions.append({'action':'COMPARE_PAIRED_ARTIFACTS','status':final['artifact_diffs']['status']})
    runtime_status='NOT_RUN'
    if runtime_source:
        final['runtime_evidence']=compare_runtime(runtime_source,runtime_target,project,target)
        runtime_status='IMPORTED_UNATTESTED'
        actions.append({'action':'COMPARE_RUNTIME_OBSERVATIONS','status':runtime_status})
    routed=route_decisions(final,project,target)
    res={'schema_version':'0.13','initial_coverage':counts(first),'final_coverage':counts(final),'actions':actions,'unresolved_groups':blockers(final),'gate':'BLOCKED_PENDING_VERIFIED_EVIDENCE','automatic_patch':False,'preflight_status':final['preflight']['status'],'runtime_verification':runtime_status,'note':'Local capture attestation is limited to discovered POMs and requested profile arguments; imports remain unattested. No runtime or effective configuration claim. No repeated action without new evidence.'}
    queue=routed;queue['acquisition_actions']=actions
    res['decision_routing']=final['decision_routing']
    for name,data in [('evidence-resolution.json',res),('scan-summary.json',final),('agent-queue.json',queue),('decision-routing.json',routed)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if final.get('legacy'):
        (out/'undertow-jackson-report.md').write_text(markdown(final['legacy']),encoding='utf8')
        (out/'tomcat-review-candidates.properties').write_text(candidate_properties(final['legacy']),encoding='utf8')
    lines=['# Evidence Resolution v0.13','','Initial: '+str(res['initial_coverage']),'Final: '+str(res['final_coverage']),'','## Actions']+[f"- {x['action']}: {x['status']}" for x in actions]+['','## Unresolved evidence']+[f"- {x['reason']}: {x['count']} rules. {x['next_action']}" for x in res['unresolved_groups']]+['','Gate: BLOCKED_PENDING_VERIFIED_EVIDENCE. No automatic patch. Runtime: '+runtime_status+'.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return res


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('project','config','output'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('target-project','source-tree','target-tree','classpath-manifest','target-classpath-manifest','runtime-source','runtime-target'):p.add_argument('--'+n,type=Path)
    p.add_argument('--execute-approved-build',action='store_true');p.add_argument('--source-profiles');p.add_argument('--target-profiles');a=p.parse_args()
    try:
        r=run(a.project,json.loads(a.config.read_text()),a.output,a.target_project,a.source_tree,a.target_tree,a.classpath_manifest,a.execute_approved_build,a.source_profiles,a.target_profiles,a.target_classpath_manifest,a.runtime_source,a.runtime_target)
        print(json.dumps(r,ensure_ascii=False,indent=2));return 3 if r['preflight_status']=='BLOCK' else 2
    except (OSError,ValueError,KeyError,TypeError) as e:print('RESOLUTION_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
