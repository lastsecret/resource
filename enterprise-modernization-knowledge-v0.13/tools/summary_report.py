#!/usr/bin/env python3
"""Read-only report adapter for v0.12; exports allowlisted facts, never raw snippets/config values."""
import argparse,collections,json,re,zipfile,hashlib
from pathlib import Path
STATUSES=('DETECTED','NOT_DETECTED','UNKNOWN','NOT_EVALUATED','NOT_APPLICABLE')
TOKEN=re.compile(r'^[A-Za-z0-9_.:+-]{1,180}$')
LOC=re.compile(r'^[A-Za-z0-9_./-]+(?::[0-9]+)?$')
def token(x): return x if isinstance(x,str) and TOKEN.fullmatch(x) else 'UNAVAILABLE'
def loc(x):
    if not isinstance(x,str) or len(x)>350:return None
    x=x.replace('\\','/')
    if not LOC.fullmatch(x) or x.startswith('/') or '..' in x.split('/'):return None
    return x

def read(p):
    if p.stat().st_size>50_000_000:raise ValueError('Input too large')
    return json.loads(p.read_text(encoding='utf8'))
def matches(location,path):return location==path or location.startswith(path+':')
def rule_rows(s,e):
    groups={rid:token(g.get('reason')) for g in e.get('unresolved_groups',[]) for rid in g.get('rule_ids',[])}
    rows=[]
    for r in s.get('evaluations',[]):
        ls=sorted({v for x in r.get('locations',[]) if (v:=loc(x))})
        rows.append({'rule_id':token(r.get('rule_id')),'status':token(r.get('status')),'applicability':token(r.get('applicability')),'detector':token(r.get('detector')),'decision':token(r.get('decision')),'automatic_patch':r.get('automatic_patch') is True,'locations':ls,'location_count':len(r.get('locations',[])),'locations_omitted':len(r.get('locations',[]))-len(ls),'matched_modules':[token(x) for x in r.get('matched_component_modules',[])],'missing_evidence_group':groups.get(r.get('rule_id')),'required_evidence':[token(x) for x in r.get('required_evidence',[])],'attributed_locations':sum(x.get('symbol_attributed') is True for x in r.get('location_evidence',[]))})
        detail=r.get('coverage_detail',{})
        rows[-1].update(semantic_resolution=token(r.get('semantic_resolution')),effective_configuration=token(r.get('effective_configuration')),coverage_detail={'detector_families':[token(x) for x in detail.get('detector_families',[])],'blocking_warning_count':detail.get('blocking_warning_count'),'warning_paths':[v for x in detail.get('warning_paths',[]) if (v:=loc(x))]},location_evidence=[{'location':v,'module':token(x.get('module')),'kind':token(x.get('evidence_kind')),'semantic_detail':token(x.get('semantic_detail')),'attributed':x.get('symbol_attributed') is True,'factory_link':{'location':loc(x.get('factory_link',{}).get('location')),'status':token(x.get('factory_link',{}).get('status')),'feature_hints':[token(y) for y in x.get('factory_link',{}).get('feature_hints',[])]} if x.get('factory_link') else None} for x in r.get('location_evidence',[]) if (v:=loc(x.get('location')))],next_action=groups.get(r.get('rule_id')) or ('INVESTIGATE_CANDIDATE' if r.get('status')=='DETECTED' else 'SKIP_CAPTURED_SCOPE_ONLY' if r.get('status')=='NOT_APPLICABLE' else 'REVIEW_COVERAGE'))
    return rows

def graph_info(s):
    g=s.get('inventory')
    if not g:return None
    focus={'spring-boot','spring-boot-starter-webmvc','spring-boot-starter-undertow','spring-boot-starter-tomcat','jackson-databind','hibernate-core','HikariCP','ojdbc11','mybatis-spring-boot-starter','spring-security-core','spring-security-config','jooq','mybatis','mybatis-spring','spring-core','spring-web','spring-webmvc','tomcat-embed-core','undertow-core'}
    data={}
    for side in ('source','target'):
        x=g.get(side,{})
        rows=[{k:token(d.get(k)) for k in ('ga','version','scope','module','classifier')} for d in x.get('dependencies',[]) if d.get('ga','').split(':')[-1] in focus]
        data[side]={'module_count':x.get('modules'),'dependency_count':len(x.get('dependencies',[])),'provenance':token(x.get('provenance')),'completeness':token(x.get('completeness')),'module_coordinates':[token(y) for y in x.get('module_coordinates',[])],'focused_dependencies':rows,'capture_scope':{'requested_profiles':token(x.get('capture_scope',{}).get('requested_profiles')),'effective_profiles':token(x.get('capture_scope',{}).get('effective_profiles')),'reactor':token(x.get('capture_scope',{}).get('reactor')),'classpath_complete':x.get('capture_scope',{}).get('classpath_complete')},'focused_dependencies_complete':False}
    return data

def grade(cases,rows,s,profile):
    by={r['rule_id']:r for r in rows}; graph=s.get('inventory'); out=[]
    codes={i.get('code') for i in s.get('preflight',{}).get('issues',[])}
    for c in cases:
        r=by.get(c['rule_id']); kind=c['kind']; path=c.get('path'); observed=bool(r and path and any((x==path+':'+str(c['line'])) if c.get('line') else matches(x,path) for x in r['locations'])); app=(r or {}).get('applicability','NOT_SELECTED')
        if c.get('profiles') and profile not in c['profiles']:status='NOT_RUN_PROFILE'
        elif c.get('phase')=='graph' and not graph:status='NOT_RUN_NO_GRAPH'
        elif c.get('phase')=='graph' and path and not all('lab.modernization:'+path.split('/')[0] in graph.get(side,{}).get('module_coordinates',[]) for side in ('source','target')):status='NOT_RUN_MODULE_MISSING'
        elif c['id']=='P09' and graph and not any(d.get('module')=='lab.modernization:persistence' and d.get('ga')=='com.oracle.database.jdbc:ojdbc11' and re.match(r'^23\.(?:1[0-9]|[2-9][0-9])(?:\.|$)',d.get('version','')) for d in graph.get('target',{}).get('dependencies',[])):status='NOT_RUN_VERSION_MISMATCH'
        elif kind=='preflight_block':status='MET' if 'IMPORTED_JOOQ_JDK_CONFLICT' in codes else 'GAP'
        elif kind=='no_jooq_block':status='GAP' if 'IMPORTED_JOOQ_JDK_CONFLICT' in codes else 'MET'
        elif kind=='anchor':
            if observed:status='MET'
            elif not r or r['status'] in ('UNKNOWN','NOT_EVALUATED'):status='UNRESOLVED_ANCHOR'
            else:status='GAP'
        elif kind=='semantic_anchor':
            match_evidence=any(matches(x['location'],path) and (not c.get('line') or x['location']==path+':'+str(c['line'])) and x.get('semantic_detail')==c.get('semantic_detail') for x in (r or {}).get('location_evidence',[]))
            status='MET' if match_evidence else 'UNRESOLVED_ANCHOR' if not r or r['status'] in ('UNKNOWN','NOT_EVALUATED') else 'GAP'
        elif kind=='coverage_gap':
            status='MET' if any(x.get('module')==c.get('module') and x.get('ga')==c.get('ga') for x in s.get('knowledge_coverage_gaps',[])) else 'GAP'
        elif kind=='captured_not_applicable':
            status='NOT_RUN_NO_CAPTURE_ATTESTATION' if not graph or any(graph[x].get('provenance')!='SCANNER_CAPTURED_LOCAL' for x in ('source','target')) else 'MET' if (r or {}).get('status')=='NOT_APPLICABLE' else 'GAP'
        elif kind in ('deterministic_decision','preflight_synced'):
            attested=s.get('decision_routing',{}).get('scope_attested') is True
            if not attested:status='NOT_RUN_NO_CAPTURE_ATTESTATION'
            elif kind=='deterministic_decision':status='MET' if (r or {}).get('decision')==c['expected'] else 'GAP'
            else:status='MET' if not codes.intersection({'DEPENDENCY_GRAPH_UNVERIFIED','BOOT41_DEPENDENCY_GRAPH_UNVERIFIED'}) and 'EFFECTIVE_REACTOR_PROFILE_SCOPE_UNVERIFIED' in codes else 'GAP'
        elif kind=='route_contains':
            rr=next((x for x in s.get('evaluations',[]) if x['rule_id']==c['rule_id']),{})
            status='MET' if c['expected'] in rr.get('decision_routes',[]) else 'UNRESOLVED_ANCHOR' if not graph else 'GAP'
        elif kind=='no_location':
            if observed:status='GAP'
            elif app in ('UNKNOWN_COMPONENT_PAIR','UNKNOWN_OR_NO_PAIR_MATCH','NOT_SELECTED') and c['id'] not in ('N01','N02','N03','N04','N05'):status='UNRESOLVED_ANCHOR'
            else:status='MET'
        else:raise ValueError('Unknown expectation')
        out.append({'case_id':c['id'],'rule_id':c['rule_id'],'kind':kind,'path':path,'line':c.get('line'),'result':status,'observed_anchor':observed,'applicability':app,'rule_status':(r or {}).get('status','NOT_SELECTED'),'why':c['why']})
    return out

def make(raw,oracle,profile,exit_code=None,unchanged=None,warm=None,ledger=None):
    raw=Path(raw); s=read(raw/'scan-summary.json') if (raw/'scan-summary.json').is_file() else {}; e=read(raw/'evidence-resolution.json') if (raw/'evidence-resolution.json').is_file() else {}
    rows=rule_rows(s,e); counts=dict(collections.Counter(r['status'] for r in rows)); case_rows=grade(read(Path(oracle))['cases'],rows,s,profile) if s and oracle else []
    canary='LAB_CANARY_DO_NOT_EXPORT_9F8D123'; leaked=[]
    for n in ('scan-summary.json','evidence-resolution.json','agent-queue.json','decision-routing.json','summary.md','undertow-jackson-report.md','tomcat-review-candidates.properties'):
        p=raw/n
        if oracle and p.is_file() and canary.encode() in p.read_bytes():leaked.append(n)
    actions=[{'action':token(x.get('action')),'status':token(x.get('status')),'module_count':x.get('module_count')} for x in e.get('actions',[])]
    groups=[{'reason':token(x.get('reason')),'count':x.get('count'),'rule_ids':[token(y) for y in x.get('rule_ids',[])]} for x in e.get('unresolved_groups',[])]
    ast=s.get('declarative_scan',{}).get('ast',{}); meta=s.get('declarative_scan',{})
    capture={}
    for side in ('source','target'):
        p=raw/side/'capture'/'capture-report.json'
        if p.is_file():
            z=read(p);capture[side]=[{'module_dir':loc(x.get('module_dir')),'tree':token(x.get('tree',{}).get('status')),'tree_exit':x.get('tree',{}).get('exit_code'),'classpath':token(x.get('classpath',{}).get('status')),'classpath_exit':x.get('classpath',{}).get('exit_code')} for x in z.get('modules',[])]
    old=s.get('legacy') or {}; container=[]
    for x in old.get('undertow_to_tomcat',[]):
        container.append({'source_key':token(x.get('source_key')),'target_key':token(x.get('target_key')),'source_location':loc(x.get('source_location')),'mapping':token(x.get('mapping')),'decision':token(x.get('decision')),'has_target_conflict':bool(x.get('existing_target')),'automatic_patch':x.get('automatic_patch') is True})
    mapper=[{'type':token(x.get('type')),'file':loc(x.get('file')),'line':x.get('line') if type(x.get('line')) is int else None,'confidence':token(x.get('confidence'))} for x in old.get('java_candidates',[])]
    report={'container_candidates':container,'legacy_mapper_hints':mapper,'schema_version':'2.0','scanner_version':token(e.get('schema_version','0.12')),'profile':profile,'scanner_exit_code':exit_code,'report_status':'AVAILABLE' if s else 'NO_SCAN_OUTPUT','source_target_files_unchanged':unchanged,'cache_warmup':warm,'preflight_status':token(s.get('preflight',{}).get('status')),'preflight_issue_codes':[token(x.get('code')) for x in s.get('preflight',{}).get('issues',[])],'route_status':token(s.get('route',{}).get('status')),'gate':token(s.get('migration_gate',e.get('gate'))),'automatic_patch':s.get('automatic_patch'),'runtime_verification':token(e.get('runtime_verification')),'initial_coverage':{k:e.get('initial_coverage',{}).get(k,0) for k in STATUSES},'reported_final_coverage':{k:e.get('final_coverage',{}).get(k,0) for k in STATUSES},'actual_coverage':{k:counts.get(k,0) for k in STATUSES},'evaluated_count':len(rows),'coverage_consistent':bool(s) and all(counts.get(k,0)==s.get('coverage',{}).get(k,0) for k in STATUSES),'rules_with_attributed_locations':sum(r['attributed_locations']>0 for r in rows),'actions':actions,'capture':capture,'unresolved_groups':groups,'inventory':graph_info(s),'ast_status':token(ast.get('status')),'scan_counts':{token(k):v for k,v in meta.get('scan_counts',{}).items() if type(v) is int},'parse_warning_count':meta.get('parse_warnings_or_errors') if type(meta.get('parse_warnings_or_errors')) is int else len(meta.get('parse_warnings_or_errors',[]) or []),'truncated_rules':[token(x) for x in meta.get('truncated_rules',[])],'canary_check':'EXECUTED' if oracle and s else 'NOT_RUN','canary_leak_files':leaked,'oracle_counts':dict(collections.Counter(x['result'] for x in case_rows)),'oracle_cases':case_rows,'rules':rows,'limitations':['Candidate detection only; MET means the fixture expectation was observed, not migration success.','Local Maven capture is scoped to discovered POMs and requested profile flags; imported graphs remain unattested. No-match is not compatibility.','No raw config values, source snippets, absolute paths, or raw build logs included. File names and component coordinates remain visible; review before sharing.']}

    report['parser_warnings']=[{'path':v,'module':token(x.get('module')),'family':token(x.get('detector_family')),'code':token(x.get('code')),'coverage_blocking':x.get('coverage_blocking') is True} for x in meta.get('warnings',[]) if (v:=loc(x.get('path')))]
    report['knowledge_coverage_gaps']=[{k:token(x.get(k)) for k in ('module','ga','target_version','known_rule_upper_exclusive','code','decision')} for x in s.get('knowledge_coverage_gaps',[])]
    dd=s.get('dependency_diff',{});ad=s.get('artifact_diffs',{})
    report['dependency_diff']={'status':token(dd.get('status')),'total_changes':dd.get('total_changes'),'truncated':dd.get('truncated')}
    report['artifact_diffs']={'status':token(ad.get('status')),'configuration_candidates':len(ad.get('configuration',[])),'api_candidates':len(ad.get('api',[])),'modules':[{'module_dir':loc(x.get('module_dir')),'source_jars':x.get('source_jars'),'target_jars':x.get('target_jars'),'errors':x.get('errors'),'metadata_source_keys':x.get('metadata_source_keys'),'metadata_target_keys':x.get('metadata_target_keys'),'metadata_changed_keys':x.get('metadata_changed_keys'),'metadata_missing_keys':x.get('metadata_missing_keys')} for x in ad.get('modules',[])]}
    rt=s.get('runtime_evidence',{});report['runtime_evidence']={'provenance':token(rt.get('provenance')),'counts':dict(collections.Counter(token(x.get('status')) for x in rt.get('cases',[])))}
    dr=s.get('decision_routing',{});report['decision_routing']={'run_id':token(dr.get('run_id')),'scope_attested':dr.get('scope_attested') is True,'counts':{token(k):v for k,v in dr.get('counts',{}).items() if type(v) is int},'decision_counts':{token(k):v for k,v in dr.get('decision_counts',{}).items() if type(v) is int}}
    q=read(raw/'decision-routing.json') if (raw/'decision-routing.json').is_file() else {}
    report['routed_tasks']=[{k:token(t.get(k)) for k in ('task_id','rule_id','module','route','decision','reason','classification')} for t in q.get('decisions',[])]
    report['shared_task_groups']=len(q.get('shared_evidence_work',[]))
    report['agent_feedback']={'status':'NOT_RUN','submitted_proposals':0,'pending_review':0}
    if ledger:
        l=read(Path(ledger)); qhash=hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        if not q or l.get('run_id')!=q.get('run_id') or l.get('queue_sha256')!=qhash:raise ValueError('Ledger does not match scan queue')
        proposals=l.get('proposals',[]); ids={t['task_id'] for t in q.get('tasks',[])}
        if len({p['task_id'] for p in proposals})!=len(proposals) or any(p.get('task_id') not in ids or p.get('state')!='PENDING_HUMAN_AND_EVIDENCE_REVIEW' or p.get('automatic_patch') is not False for p in proposals):raise ValueError('Invalid pending ledger')
        report['agent_feedback']={'status':'LOCAL_PROPOSALS_PENDING_REVIEW','submitted_proposals':len(proposals),'pending_review':len(proposals),'unanswered_tasks':len(ids)-len(proposals),'decision_counts':dict(collections.Counter(token(p.get('decision')) for p in proposals))}
    report['legacy_mapper_hints']=[] # canonical semantic findings only; legacy diagnostic raw remains local
    report['schema_version']='3.0'
    return report

def markdown(r):
    def table(head,rows):return ['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in x)+' |' for x in rows]
    b=['# Modernization challenge — summary','',f"Profile: `{r['profile']}` · Scanner exit: `{r['scanner_exit_code']}` · Report: `{r['report_status']}`",f"Preflight: `{r['preflight_status']}` · Gate: `{r['gate']}` · Runtime: `{r['runtime_verification']}`",f"Fixture files unchanged: `{r['source_target_files_unchanged']}` · Synthetic canary leak: `{bool(r['canary_leak_files'])}` · AST: `{r['ast_status']}`",'', '## Coverage','']
    b+=table(['Status','Initial','Final (recounted)'],[(k,r['initial_coverage'][k],r['actual_coverage'][k]) for k in STATUSES]);b+=['',f"Coverage agrees with scanner: {r['coverage_consistent']}; rules with at least one attributed location: {r['rules_with_attributed_locations']}",'','## Evidence acquisition','']
    b+=table(['Action','Status','Modules'],[(x['action'],x['status'],x['module_count']) for x in r['actions']]);b+=['','## Outstanding evidence',''];b+=table(['Reason','Rules'],[(x['reason'],x['count']) for x in r['unresolved_groups']]);b+=['','## Oracle results','',str(r['oracle_counts']),''];b+=table(['Case','Rule','Result','Path'],[(x['case_id'],x['rule_id'],x['result'],(x['path']+(':'+str(x['line']) if x.get('line') else '')) if x['path'] else '—') for x in r['oracle_cases']]);b+=['','## Candidate locations and unresolved rules',''];b+=table(['Rule','State','Applicability','Locations'],[(x['rule_id'],x['status'],x['applicability'],', '.join(x['locations'][:5]) + (' …' if len(x['locations'])>5 else '')) for x in r['rules']]);b+=['','## Parser warnings','']+table(['File','Family','Code','Blocking'],[(x['path'],x['family'],x['code'],x['coverage_blocking']) for x in r.get('parser_warnings',[])])+['','## Knowledge coverage gaps','']+table(['Module','Artifact','Target','Upper bound (exclusive)'],[(x['module'],x['ga'],x['target_version'],x['known_rule_upper_exclusive']) for x in r.get('knowledge_coverage_gaps',[])])+['','## Artifact diff',str(r.get('dependency_diff',{})),str(r.get('artifact_diffs',{})),'','## Boundaries','']+['- '+x for x in r['limitations']];b+=['','## Decision routing',str(r.get('decision_routing',{})),'',f"Shared task groups: {r.get('shared_task_groups',0)}",str(r.get('agent_feedback',{})),'']+table(['Rule','Module','Route','Decision'],[(x['rule_id'],x['module'],x['route'],x['decision']) for x in r.get('routed_tasks',[])]);return '\n'.join(b)+'\n'

def write(r,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    j=out/'summary-report.json';m=out/'summary-report.md';j.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8');m.write_text(markdown(r),encoding='utf8')
    with zipfile.ZipFile(out/'feedback.zip','x',zipfile.ZIP_DEFLATED) as z:
        for p in (j,m):z.write(p,p.name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',required=True,type=Path);p.add_argument('--oracle',type=Path,help='Optional fixture-specific expectations; omit for ordinary reports');p.add_argument('--profile',choices=['default','jooq-risk','hikari-regression'],default='default');p.add_argument('--output',required=True,type=Path);p.add_argument('--ledger',type=Path,help='Optional matching local evidence ledger; only counts exported');a=p.parse_args();write(make(a.raw,a.oracle,a.profile,ledger=a.ledger),a.output)
if __name__=='__main__':main()
