"""Strict/semantic A-B diff with scoped normalization and multiplicity-preserving unordered arrays."""
from __future__ import annotations
import base64
from copy import deepcopy
import fnmatch
import json
import math
import re
import unicodedata
from .common import JapiError

DEFAULT_POLICY={'mode':'semantic','headers_include':['content-type'],
    'string_case_sensitive':True,'array_order':'preserve','numeric_tolerance':0.0,
    'strict_numeric_type':True,'trim_string':False,'unicode_normalization':'none',
    'null_missing_equal':False,'null_empty_array_equal':False,'ignore_paths':[],
    'path_rules':[]}
MISSING=object()


def validate_policy(raw):
    policy=deepcopy(DEFAULT_POLICY)
    if not isinstance(raw,dict):raise JapiError('Comparison policy must be an object')
    raw=raw.get('comparison',raw)
    extra=set(raw)-set(DEFAULT_POLICY)
    if extra:raise JapiError(f'Unknown comparison keys: {sorted(extra)}')
    policy.update(raw)
    if policy['mode'] not in ('raw_exact','json_exact','semantic','custom'):
        raise JapiError('Comparison mode: raw_exact | json_exact | semantic | custom')
    if policy['array_order'] not in ('preserve','ignore'):raise JapiError('array_order must be preserve or ignore')
    if policy['unicode_normalization'] not in ('none','NFC','NFD','NFKC','NFKD'):
        raise JapiError('Invalid unicode_normalization')
    if policy['numeric_tolerance']<0:raise JapiError('numeric_tolerance cannot be negative')
    if policy['mode']=='raw_exact' and any(policy[x]!=DEFAULT_POLICY[x] for x in ('string_case_sensitive','array_order','numeric_tolerance','trim_string','unicode_normalization','null_missing_equal','null_empty_array_equal','ignore_paths','path_rules','strict_numeric_type')):
        raise JapiError('raw_exact is incompatible with semantic modifiers')
    if policy['mode']=='json_exact' and any(policy[x]!=DEFAULT_POLICY[x] for x in ('string_case_sensitive','array_order','numeric_tolerance','trim_string','unicode_normalization','null_missing_equal','null_empty_array_equal','ignore_paths','path_rules','strict_numeric_type')):
        raise JapiError('json_exact is incompatible with semantic modifiers')
    for r in policy['path_rules']:
        if not isinstance(r,dict) or not r.get('path'):raise JapiError('Each path rule must have path')
        if set(r)-{'path'}-set(DEFAULT_POLICY):raise JapiError('Unknown path-rule key')
    return policy


def path_matches(pattern,path):
    """Limited JSONPath: dot keys, exact [index], [*], and wildcard keys."""
    expr=re.escape(pattern)
    expr=expr.replace(r'\[\*\]',r'\[\d+\]')
    expr=expr.replace(r'\*',r'[^.\[\]]*')
    return bool(re.fullmatch(expr,path))


def effective(policy,path):
    result=policy.copy()
    for rule in policy.get('path_rules',[]):
        if path_matches(rule['path'],path):result.update({k:v for k,v in rule.items() if k!='path'})
    return result


def ignored(policy,path):
    return any(path_matches(p,path) for p in policy.get('ignore_paths',[]))


def string_equal(a,b,policy):
    if policy['trim_string']:a=a.strip();b=b.strip()
    if policy['unicode_normalization']!='none':
        a=unicodedata.normalize(policy['unicode_normalization'],a)
        b=unicodedata.normalize(policy['unicode_normalization'],b)
    if not policy['string_case_sensitive']:a=a.casefold();b=b.casefold()
    return a==b


def equal(a,b,path,policy,depth=0):
    if depth>80:raise JapiError('JSON nesting depth >80 is unsupported')
    if ignored(policy,path):return True
    p=effective(policy,path)
    if a is MISSING or b is MISSING:
        if a is MISSING and b is MISSING:return True
        if p['null_missing_equal'] and (a is None or b is None):return True
        return False
    if p['null_empty_array_equal'] and ((a is None and b==[]) or (b is None and a==[])):
        return True
    if isinstance(a,bool) or isinstance(b,bool):return isinstance(a,bool) and isinstance(b,bool) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        if p['strict_numeric_type'] and type(a) is not type(b):return False
        return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=p['numeric_tolerance']
    if isinstance(a,str) and isinstance(b,str):return string_equal(a,b,p)
    if isinstance(a,dict) and isinstance(b,dict):
        return all(equal(a.get(k,MISSING),b.get(k,MISSING),path+'.'+k,policy,depth+1)
                   for k in sorted(a.keys()|b.keys()))
    if isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b):return False
        if p['array_order']=='preserve':
            return all(equal(x,y,path+f'[{i}]',policy,depth+1) for i,(x,y) in enumerate(zip(a,b)))
        if len(a)>500:raise JapiError('Unordered array >500 items exceeds deterministic matcher limit')
        # Bipartite matching respects duplicates and non-transitive numeric tolerance.
        edges=[]
        for i,x in enumerate(a):
            edges.append([j for j,y in enumerate(b) if equal(x,y,path+f'[{i}]',policy,depth+1)])
        match=[-1]*len(b)
        def assign(i,seen):
            for j in edges[i]:
                if j in seen:continue
                seen.add(j)
                if match[j]==-1 or assign(match[j],seen):match[j]=i;return True
            return False
        return all(assign(i,set()) for i in range(len(a)))
    return type(a) is type(b) and a==b


def differences(a,b,path,policy,limit=30):
    if ignored(policy,path) or equal(a,b,path,policy):return []
    p=effective(policy,path)
    if isinstance(a,dict) and isinstance(b,dict):
        out=[]
        for k in sorted(a.keys()|b.keys()):
            out.extend(differences(a.get(k,MISSING),b.get(k,MISSING),path+'.'+k,policy,limit))
            if len(out)>=limit:break
        return out[:limit]
    if isinstance(a,list) and isinstance(b,list) and p['array_order']=='preserve' and len(a)==len(b):
        out=[]
        for i,(x,y) in enumerate(zip(a,b)):
            out.extend(differences(x,y,path+f'[{i}]',policy,limit))
            if len(out)>=limit:break
        return out[:limit]
    def sanitized(v):
        if v is MISSING:return '<missing>'
        text=json.dumps(v,ensure_ascii=False)
        return text[:200]+('…' if len(text)>200 else '')
    return [{'path':path,'a':sanitized(a),'b':sanitized(b)}]


def compare_one(a,b,policy):
    cid=a.get('case_id') or b.get('case_id')
    entry={'case_id':cid,'endpoint_id':a.get('endpoint_id') or b.get('endpoint_id'),
           'quality_confidence':a.get('quality_confidence') or b.get('quality_confidence'),
           'quality_warnings':a.get('quality_warnings') or b.get('quality_warnings',[]),
           'differences':[],'suppressed_by_policy':False}
    if a.get('error') or b.get('error') or a.get('body_truncated') or b.get('body_truncated'):
        entry.update(outcome='inconclusive',differences=[{'path':'$transport','a':a.get('error'),'b':b.get('error')}]);return entry
    if a.get('status')!=b.get('status'):
        entry['differences'].append({'path':'$status','a':a.get('status'),'b':b.get('status')})
    for h in policy['headers_include']:
        av=next((v for k,v in a.get('headers',{}).items() if k.lower()==h.lower()),None)
        bv=next((v for k,v in b.get('headers',{}).items() if k.lower()==h.lower()),None)
        if av!=bv:entry['differences'].append({'path':'$headers.'+h,'a':av,'b':bv})
    aa=base64.b64decode(a.get('body_b64',''),validate=True)
    bb=base64.b64decode(b.get('body_b64',''),validate=True)
    if policy['mode']=='raw_exact':
        if aa!=bb:entry['differences'].append({'path':'$body.raw','a_sha256':a.get('body_sha256'),'b_sha256':b.get('body_sha256')})
    else:
        is_json=('json' in str(a.get('headers',{}).get('content-type','')).lower() or
                 'json' in str(b.get('headers',{}).get('content-type','')).lower())
        try:
            ax=json.loads(aa);bx=json.loads(bb)
        except (ValueError,UnicodeDecodeError):
            if aa!=bb:
                entry['differences'].append({'path':'$body.raw','a_sha256':a.get('body_sha256'),'b_sha256':b.get('body_sha256')})
            entry['body_mode']='raw-fallback' if not is_json else 'invalid-json'
            if is_json:
                entry['differences'].append({'path':'$body','error':'Invalid JSON under JSON Content-Type; cannot perform semantic comparison'})
                entry['outcome']='inconclusive'
                return entry
        else:
            entry['body_mode']='json'
            entry['differences'].extend(differences(ax,bx,'$',policy))
            if not entry['differences'] and policy['mode'] in ('semantic','custom'):
                strict=validate_policy({'mode':'json_exact'})
                entry['suppressed_by_policy']=not equal(ax,bx,'$',strict)
    entry['outcome']='same' if not entry['differences'] else 'different'
    return entry


def compare(a_results,b_results,raw_policy=None):
    policy=validate_policy(raw_policy or {})
    a_ids=[r.get('case_id') for r in a_results];b_ids=[r.get('case_id') for r in b_results]
    if len(set(a_ids))!=len(a_ids) or len(set(b_ids))!=len(b_ids):
        raise JapiError('Duplicate case IDs in execution results')
    a_by={r['case_id']:r for r in a_results};b_by={r['case_id']:r for r in b_results}
    rows=[]
    for cid in sorted(a_by.keys()|b_by.keys()):
        if cid not in a_by or cid not in b_by:
            rows.append({'case_id':cid,'outcome':'inconclusive','differences':[{'path':'$case','a':'present' if cid in a_by else 'missing','b':'present' if cid in b_by else 'missing'}]})
        else:rows.append(compare_one(a_by[cid],b_by[cid],policy))
    summary={'total':len(rows),'same':sum(x['outcome']=='same' for x in rows),
             'different':sum(x['outcome']=='different' for x in rows),
             'inconclusive':sum(x['outcome']=='inconclusive' for x in rows),
             'suppressed_by_policy':sum(x.get('suppressed_by_policy',False) for x in rows),
             'low_confidence':sum(x.get('quality_confidence')=='low' for x in rows)}
    return {'summary':summary,'policy':policy,'cases':rows}
