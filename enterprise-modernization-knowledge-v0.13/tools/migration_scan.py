#!/usr/bin/env python3
"""Unified candidate-only scan. Imported graph evidence is not independently verified."""
import argparse,json,sys
from pathlib import Path
from version_router import route
from project_scanner import scan as legacy_scan,markdown as legacy_markdown,candidate_properties
from scan_boot41 import scan as boot41_scan
from validate_migration import evaluate,load_json,ROOT
from config_contract import errors
from inventory import snapshot,version
from detectors import evaluate as evaluate_detectors
from safety import output_dir
from decision_router import route as route_decisions

def analyze(project,config,graph=None,ast=False,attribute=False,classpaths=None):
    preflight=evaluate(config,load_json(ROOT/'compatibility'/'java-minimums.json'))
    if errors(config):return {'route':{'status':'BLOCK','stages':[],'rule_ids':[]},'preflight':preflight,'legacy':None,'boot41':None,'evaluations':[]}
    source=config['source']['spring_boot_version'];target=config['target']['spring_boot_version'];routing=route(source,target)
    if routing['status']!='CANDIDATES_SELECTED':return {'route':routing,'preflight':preflight,'legacy':None,'boot41':None,'evaluations':[]}
    old=legacy_scan(Path(project));new=boot41_scan(Path(project),source,target)
    evaluated=evaluate_detectors(project,routing,old,new,graph,ast,attribute,classpaths)
    ids={r['rule_id'] for r in evaluated['evaluations'] if r['applicability'] not in ('IMPORTED_PAIR_OUT_OF_SCOPE','CAPTURED_SCOPE_NOT_APPLICABLE')}
    old['findings']=[f for f in old['findings'] if f['rule_id'] in ids]
    old['scope_notice']='Legacy diagnostics are unbound hints; authoritative module-filtered candidates are in evaluations/findings.'
    if 'WEB-UNDERTOW-005' not in ids:old['undertow_to_tomcat']=[]
    if 'WEB-UNDERTOW-006' not in ids:old['default_comparisons']=[];old['default_preservation_candidates']=[]
    if 'JCK3-MAPPER-TOPOLOGY-003' not in ids:old['java_candidates']=[h for h in old['java_candidates'] if h['type']=='UNDERTOW_CUSTOMIZER' and 'WEB-UNDERTOW-001' in ids]
    # Existing defaults were sourced from Boot 4.0 only. Do not present them as 4.1 verified facts.
    if target.startswith('4.1.'):
        for d in old['default_comparisons']:d['target_default']='UNKNOWN_FOR_EXACT_4.1_TARGET (4.0 reference: '+str(d['target_default'])+')'
        old['default_preservation_candidates']=[]
    def issue(level,code,detail):preflight['issues'].append({'level':level,'code':code,'detail':detail})
    if graph:
        # Imported tree is evidence of content, not attestation. Check known incompatible declarations, never PASS.
        for d in graph['target']['dependencies']:
            v=version(d['version'])
            if d['ga']=='org.jooq:jooq' and v and v>=version('3.20') and d['scope'] in ('compile','runtime','') and (preflight.get('resolved_target_java') or 0)<21:
                issue('BLOCK','IMPORTED_JOOQ_JDK_CONFLICT','Imported OSS jOOQ candidate requires Java 21; verify exact graph and edition.')
    if any(f['rule_id']=='SB41-JOOQ-JDK-008' for f in new['findings']) and not (graph and graph['target'].get('completeness')=='CAPTURED_DISCOVERED_MODULE_SCOPE' and not any(d['ga']=='org.jooq:jooq' for d in graph['target']['dependencies'])):issue('REVIEW','JOOQ_DECLARATION_NEEDS_RESOLUTION','Source hints include jOOQ; resolve target edition, scope and version.')
    preflight['status']='BLOCK' if any(i['level']=='BLOCK' for i in preflight['issues']) else 'REVIEW_REQUIRED'
    return {'schema_version':'0.10','route':routing,'preflight':preflight,'legacy':old,'boot41':new,'inventory':graph,'evaluations':evaluated['evaluations'],'findings':evaluated['findings'],'coverage':evaluated['coverage'],'declarative_scan':evaluated['declarative_scan'],'unrouted_component_rules_pending_inventory':evaluated['unrouted_component_rules_pending_inventory'],'scan_counts':evaluated['scan_counts'],'migration_gate':'BLOCKED_PENDING_VERIFIED_EVIDENCE','automatic_patch':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True,type=Path);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--source-tree',type=Path);p.add_argument('--target-tree',type=Path);p.add_argument('--target-project',type=Path);p.add_argument('--java-ast',action='store_true');p.add_argument('--attribute',action='store_true',help='Attempt attribution using JDK and optional trusted classpath manifest');p.add_argument('--classpath-manifest',type=Path);a=p.parse_args()
    try:
        if any((a.source_tree,a.target_tree,a.target_project)) and not all((a.source_tree,a.target_tree,a.target_project)):raise ValueError('All graph arguments required')
        graph=snapshot(a.source_tree,a.target_tree,a.project,a.target_project) if a.source_tree else None
        if a.classpath_manifest and not a.attribute:raise ValueError('Classpath requires --attribute')
        cp=load_json(a.classpath_manifest) if a.classpath_manifest else None
        if cp is not None and (not isinstance(cp,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in cp.items())):raise ValueError('Classpath manifest invalid')
        r=analyze(a.project,load_json(a.config),graph,a.java_ast or a.attribute,a.attribute,cp)
        if a.target_project and a.output.resolve().is_relative_to(a.target_project.resolve()):raise ValueError('Output must be outside target project')
        out=output_dir(a.output,a.project)
        routed=route_decisions(r,a.project,a.target_project)
        for name in ('agent-queue.json','decision-routing.json'):(out/name).write_text(json.dumps(routed,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        (out/'scan-summary.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        if r['legacy']:
            (out/'undertow-jackson-report.md').write_text(legacy_markdown(r['legacy']),encoding='utf8')
            (out/'tomcat-review-candidates.properties').write_text(candidate_properties(r['legacy']),encoding='utf8')
        body=['# Modernization v0.10 Scanner Summary','',f"- Route: {r['route']['status']}",f"- Java preflight: {r['preflight']['status']}",f"- Evaluation coverage: {r.get('coverage',{})}",'- No automatic changes; verified compatibility not established.','','## Rule evaluations','']
        for x in r.get('evaluations',[]):body.append(f"- {x['rule_id']}: {x['status']} / {x['applicability']}")
        (out/'summary.md').write_text('\n'.join(body)+'\n',encoding='utf8')
        print(f"Preflight={r['preflight']['status']}; reports={out}")
        return 3 if r['preflight']['status']=='BLOCK' else 2
    except Exception as e:print(f'SCAN_ERROR: {type(e).__name__}',file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
