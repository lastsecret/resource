"""Registry of candidate-only detectors. Every catalog rule gets an evaluation."""
from pathlib import Path
import json,re
from safety import files
from inventory import version
from declarative import load_plans,collect
from semantic import TARGETS
ROOT=Path(__file__).resolve().parents[1]

def load_registry():return json.loads((ROOT/'detectors/registry.json').read_text())['rules']
def applies(spec,graph,matched_modules=None):
    if not spec:return 'BOOT_ROUTE_ONLY'
    if not graph:return 'UNKNOWN_COMPONENT_PAIR'
    if spec.get('target_presence_only'):
        targets=[t for t in graph['target']['dependencies'] if t['ga'] in spec['target_ga'] and version(t['version']) is not None]
        if targets:
            if matched_modules is not None:matched_modules.update(t['module'] for t in targets)
            return 'IMPORTED_PAIR_MATCH'
        if all(graph.get(side,{}).get('completeness')=='CAPTURED_DISCOVERED_MODULE_SCOPE' for side in ('source','target')) and graph['source']['module_coordinates']==graph['target']['module_coordinates']:return 'CAPTURED_SCOPE_NOT_APPLICABLE'
        return 'UNKNOWN_OR_NO_PAIR_MATCH'
    # Imported trees do not prove absence; cross-module matching is not permitted.
    pairs=[]; observed_pairs=0
    target_index={}
    for t in graph['target']['dependencies']:
        if t['ga'] in spec['target_ga']:
            target_index.setdefault((t['module'],t['scope'],t['classifier']),[]).append(t)
    for s in graph['source']['dependencies']:
        if s['ga'] not in spec['source_ga']:continue
        for t in target_index.get((s['module'],s['scope'],s['classifier']),[]):
            sv,tv=version(s['version']),version(t['version'])
            if sv is None or tv is None:continue
            observed_pairs+=1
            if spec.get('exact_target') and t['version']!=spec['exact_target']:continue
            cut=version(spec['crosses'])
            if sv<cut<=tv and (not spec.get('source_min') or sv>=version(spec['source_min'])) and (not spec.get('target_max_exclusive') or tv<version(spec['target_max_exclusive'])):
                pairs.append({'module':s['module'],'source_ga':s['ga'],'source_version':s['version'],'target_ga':t['ga'],'target_version':t['version'],'scope':s['scope']})
    if matched_modules is not None:matched_modules.update(p['module'] for p in pairs)
    if pairs:return 'IMPORTED_PAIR_MATCH'
    scoped=all(graph.get(side,{}).get('completeness')=='CAPTURED_DISCOVERED_MODULE_SCOPE' for side in ('source','target')) and graph['source']['module_coordinates']==graph['target']['module_coordinates']
    # Only exclude observed pairs, or a captured scope with no relevant component on either side.
    related=any(d['ga'] in set(spec['source_ga']+spec['target_ga']) for side in ('source','target') for d in graph[side]['dependencies'])
    related_modules={d['module'] for side in ('source','target') for d in graph[side]['dependencies'] if d['ga'] in set(spec['source_ga']+spec['target_ga'])}
    paired_modules={s['module'] for s in graph['source']['dependencies'] if s['ga'] in spec['source_ga'] and version(s['version']) is not None and any(version(t['version']) is not None for t in target_index.get((s['module'],s['scope'],s['classifier']),[]))}
    if scoped and (not related or (observed_pairs and related_modules<=paired_modules)):return 'CAPTURED_SCOPE_NOT_APPLICABLE'
    return 'IMPORTED_PAIR_OUT_OF_SCOPE' if observed_pairs else 'UNKNOWN_OR_NO_PAIR_MATCH'

def evaluate(project,route,legacy,boot41,graph=None,ast=False,attribute=False,classpaths=None):
    specs=load_registry(); plans=load_plans(); decl,scanmeta,modules=collect(project,plans,ast,attribute,classpaths,graph); selected=set(route['rule_ids']); all_hits={}
    for f in legacy['findings']+boot41['findings']:all_hits.setdefault(f['rule_id'],[]).append(f)
    result=[]; findings=[]; text_rules=[]; pending=[]
    for rid,spec in specs.items():
        pair_modules=set(); app=applies(spec.get('component'),graph,pair_modules)
        chosen=rid in selected or (app=='IMPORTED_PAIR_MATCH' and not (spec.get('component') or {}).get('requires_boot_route')) or ('spring-boot-4.0-to-4.1' in route['stages'] and rid.startswith(('HIB71-','HIB72-','HIB73-','HIB74-','JCK31-')))
        if not chosen:
            if spec.get('component') and app.startswith('UNKNOWN'):pending.append(rid)
            continue
        det=spec['detector']; hits=all_hits.get(rid,[])
        if det=='none' and plans[rid].get('match_any'):det='declarative'
        if app in ('IMPORTED_PAIR_OUT_OF_SCOPE','CAPTURED_SCOPE_NOT_APPLICABLE'):
            result.append({'rule_id':rid,'detector':det,'applicability':app,'status':'NOT_APPLICABLE' if app=='CAPTURED_SCOPE_NOT_APPLICABLE' else 'UNKNOWN','decision':'REVIEW_REQUIRED','automatic_patch':False,'locations':[],'location_module_binding':'NOT_VERIFIED'});continue
        if det=='text':text_rules.append((rid,re.compile(spec['regex'],re.I),spec['suffixes']));
        rec={'rule_id':rid,'detector':det,'applicability':app,'status':'NOT_EVALUATED','decision':'REVIEW_REQUIRED','automatic_patch':False,'locations':[],'location_module_binding':'NOT_VERIFIED'}
        rec['matched_component_modules']=sorted(pair_modules)
        if det=='declarative':
            rec['locations']=[h['location'] for h in decl.get(rid,[])]
            rec['location_evidence']=decl.get(rid,[])
            rec['status']='DETECTED' if rec['locations'] else 'NOT_DETECTED'
        if det in ('legacy','boot41'):
            rec['locations']=sorted({str(l) for h in hits for l in h.get('locations',[h.get('location')]) if l})
            rec['status']='DETECTED' if hits else 'NOT_DETECTED'
        result.append(rec)
    byid={x['rule_id']:x for x in result};counts={}
    semantic_hits=scanmeta.pop('semantic_hits');semantic_paths=set(scanmeta.pop('semantic_paths'))
    for path in files(project,counts):
        matching=[(rid,rx) for rid,rx,suffix in text_rules if path.suffix.lower() in suffix or path.name.lower() in suffix]
        if not matching:continue
        try:text=path.read_text(encoding='utf8')
        except (OSError,UnicodeError):counts['unreadable']=counts.get('unreadable',0)+1;continue
        if path.suffix.lower() in ('.java','.kt'):
            # Preserve quoted SQL/annotation literals, mask common comments. Not a Java parser.
            token=re.compile('"""[\\s\\S]*?"""|"(?:\\\\.|[^"\\\\])*"|\\x27(?:\\\\.|[^\\x27\\\\])*\\x27|//[^\\n]*|/\\*[\\s\\S]*?\\*/')
            text=token.sub(lambda m:re.sub(r'[^\n]',' ',m.group()) if m.group().startswith(('//','/*')) else m.group(),text)
        for rid,rx in matching:
            for m in rx.finditer(text):
                rec=byid[rid];loc=f'{path.relative_to(Path(project).resolve())}:{text.count(chr(10),0,m.start())+1}'
                if loc not in rec['locations'] and len(rec['locations'])<200:rec['locations'].append(loc)
    for rid,_,_ in text_rules:
        rec=byid[rid];rec['status']='DETECTED' if rec['locations'] else 'NOT_DETECTED'
    incomplete=any(counts.get(k) for k in ('unreadable','links_skipped','size_or_special_skipped')) or any(legacy.get('scan_counts',{}).get(k) or boot41.get('scan_counts',{}).get(k) for k in ('unreadable','links_skipped','size_or_special_skipped'))
    for rec in result:
        rid=rec['rule_id']; plan=plans[rid]; rec['execution_strategy']=plan['execution_strategy'];rec['required_evidence']=plan['required_evidence']
        pairs=set(rec.get('matched_component_modules',[])); raw=rec.get('location_evidence') or [{'location':loc,'detector':rec['detector'],'evidence_kind':'LEGACY_CANDIDATE',**modules.bind(loc.rsplit(':',1)[0] if loc.rsplit(':',1)[-1].isdigit() else loc)} for loc in rec['locations']]
        if rid in TARGETS and rec['applicability'] not in ('IMPORTED_PAIR_OUT_OF_SCOPE','CAPTURED_SCOPE_NOT_APPLICABLE'):
            raw=[x for x in raw if x['location'].rsplit(':',1)[0] not in semantic_paths]+semantic_hits.get(rid,[])
            if raw:rec['status']='DETECTED'
            elif rec['status']=='DETECTED':rec['status']='NOT_DETECTED'
        # Unbound hits remain hypotheses; known different module hits are excluded.
        if pairs:raw=[x for x in raw if x['module'] is None or x['module'] in pairs]
        if rid=='SB4-JACKSON-API-006' and graph:
            # Preserve Boot-specific relocation candidates even in Jackson2 islands.
            jm=set();japp=applies(specs['JCK3-MAPPER-TOPOLOGY-003']['component'],graph,jm)
            known_stable={s['module'] for s in graph['source']['dependencies'] if s['ga']=='com.fasterxml.jackson.core:jackson-databind' and any(t['ga']==s['ga'] and t['module']==s['module'] and t['version']==s['version'] for t in graph['target']['dependencies']) and not any(t['ga']=='tools.jackson.core:jackson-databind' and t['module']==s['module'] for t in graph['target']['dependencies'])}
            raw=[x for x in raw if not (x.get('semantic_detail')=='JACKSON_API_IMPORT' and x['module'] in known_stable and x['module'] not in jm)]
        for hit in raw:
            loc=hit['location']; root_prefix=str(Path(project).resolve())+str(__import__('os').sep)
            if loc.startswith(root_prefix):hit['location']=loc[len(root_prefix):]
            hit['component_module_association']='DECLARED_COORDINATE_MATCH' if pairs and hit['module'] in pairs else 'NOT_VERIFIED'
        rec['location_evidence']=raw;rec['locations']=sorted({x['location'] for x in raw});rec['location_module_binding']='DECLARATION_ONLY' if raw and all(x['module'] for x in raw) else 'NOT_VERIFIED'
        if rec['status']=='DETECTED' and not raw:rec['status']='UNKNOWN'
        families={m['type'].split('.')[0] for m in plan.get('match_any',[])}
        if rec['detector']=='text':families.update(('java','config','xml'))
        if rec['detector'] in ('legacy','boot41'):families.update(('java','config','dependency'))
        scoped_warnings=[w for w in scanmeta['warnings'] if w['coverage_blocking'] and w['detector_family'] in families and (not pairs or w['module'] in pairs or w['module'] is None)]
        rec['coverage_detail']={'detector_families':sorted(families),'blocking_warning_count':len(scoped_warnings),'warning_paths':sorted({w['path'] for w in scoped_warnings}),'scope':'STATIC_DISCOVERED_FILES_ONLY'}
        if rec['status']=='NOT_DETECTED' and (scoped_warnings or rid in scanmeta['truncated_rules']):rec['status']='UNKNOWN'
        if rec['status']=='NOT_DETECTED' and (incomplete or rec['applicability'].startswith('UNKNOWN')):rec['status']='UNKNOWN'
        rec['semantic_resolution']='PARTIAL' if any(x.get('symbol_attributed') for x in raw) else 'UNVERIFIED'
        rec['effective_configuration']='UNKNOWN'
        rec['agent_fallback']='REQUIRED' if rec['status'] in ('UNKNOWN','NOT_EVALUATED','DETECTED') else 'REVIEW_COVERAGE'
        if rec['status']=='DETECTED':findings.append({**rec,'confidence':'STATIC_CANDIDATE_ONLY'})
    return {'declarative_scan':scanmeta,'evaluations':result,'findings':findings,'scan_counts':counts,'unrouted_component_rules_pending_inventory':pending,'coverage':{k:sum(x['status']==k for x in result) for k in ('DETECTED','NOT_DETECTED','UNKNOWN','NOT_EVALUATED','NOT_APPLICABLE')},'scope':'AST, lexical, XML, config and declaration candidates only. NOT_DETECTED is not compatibility; imported graph is not verified; no patch.'}
