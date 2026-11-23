"""Deterministic case generation and data-quality validation."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import re
from urllib.parse import quote
from .common import JapiError
from .discover import resolve_local_ref

MISSING = object()


def referenced_catalog(catalog):
    return {'components':catalog.get('components',{})}


def deref_schema(schema, catalog, depth=0):
    if not isinstance(schema,dict):return {}
    if depth>=12: return {'x-unresolved-ref':'maximum recursion depth'}
    if '$ref' in schema:
        resolved=resolve_local_ref(referenced_catalog(catalog),schema['$ref'])
        if resolved==schema:return {'x-unresolved-ref':schema['$ref']}
        return deref_schema(resolved,catalog,depth+1)
    return schema


def value_for(schema, catalog, variant=0, depth=0):
    """(value, provenance). Unknown mandatory values must be visible as warnings."""
    if depth>=8:return MISSING,'unresolved'
    schema=deref_schema(schema,catalog,depth)
    if schema.get('x-unresolved-ref'):return MISSING,'unresolved'
    if 'example' in schema:return deepcopy(schema['example']),'schema_example'
    if 'const' in schema:return deepcopy(schema['const']),'schema_const'
    if 'enum' in schema and schema['enum']:
        return deepcopy(schema['enum'][variant%len(schema['enum'])]),'schema_enum'
    if 'default' in schema:return deepcopy(schema['default']),'schema_default'
    if 'allOf' in schema:
        props={};required=[]
        for child in schema['allOf']:
            ch=deref_schema(child,catalog,depth+1)
            props.update(ch.get('properties',{}));required.extend(ch.get('required',[]))
        return value_for({'type':'object','properties':props,'required':required},catalog,variant,depth+1)
    for combinator in ('oneOf','anyOf'):
        if schema.get(combinator):return value_for(schema[combinator][0],catalog,variant,depth+1)
    t=schema.get('type')
    if isinstance(t,list):t=next((x for x in t if x!='null'), 'null')
    if not t and 'properties' in schema:t='object'
    if t=='object':
        out={}; sources=[]
        for key in schema.get('required',[]):
            s=schema.get('properties',{}).get(key,{})
            value,origin=value_for(s,catalog,variant,depth+1)
            if value is MISSING:return MISSING,'unresolved'
            out[key]=value;sources.append(origin)
        if not out and schema.get('properties'):
            first=next(iter(schema['properties']))
            value,origin=value_for(schema['properties'][first],catalog,variant,depth+1)
            if value is not MISSING:out[first]=value;sources.append(origin)
        return out,'inferred' if not sources or 'inferred' in sources else 'schema_derived'
    if t=='array':
        value,origin=value_for(schema.get('items',{}),catalog,variant,depth+1)
        return ([value] if value is not MISSING else []),('inferred' if value is MISSING else origin)
    if t=='string':
        if schema.get('format')=='date':return '2026-01-15','inferred'
        if schema.get('format')=='date-time':return '2026-01-15T00:00:00Z','inferred'
        if schema.get('format')=='uuid':return '00000000-0000-4000-8000-000000000001','inferred'
        return ('sample' if variant==0 else f'sample-{variant}'),'inferred'
    if t=='integer':return (max(1,int(schema.get('minimum',1)))+variant),'inferred'
    if t=='number':return (max(1,float(schema.get('minimum',1)))+variant),'inferred'
    if t=='boolean':return (variant%2==0),'inferred'
    if t=='null':return None,'inferred'
    return MISSING,'unresolved'


def special_values(value, path, intentional):
    """Explicit field-path intent suppresses a warning only for that exact path and kind."""
    result=[]
    kind='null' if value is None else 'empty_array' if value==[] else None
    if kind and not any(x.get('path')==path and x.get('value_kind')==kind and x.get('reason') and x.get('expected_behavior') for x in intentional):
        code='UNINTENDED_NULL' if kind=='null' else 'UNINTENDED_EMPTY_ARRAY'
        result.append({'code':code,'severity':'warning','path':path,'message':f'{kind} is not declared as an intentional test input'})
    if isinstance(value,dict):
        for k,v in value.items():result.extend(special_values(v,path+'/'+str(k).replace('~','~0').replace('/','~1'),intentional))
    if isinstance(value,list):
        for i,v in enumerate(value):result.extend(special_values(v,path+'/'+str(i),intentional))
    return result


def validate_case(case):
    warnings=list(case.get('quality_warnings',[]))
    intentional=case.get('intentional_special_values',[])
    request=case.get('request',{})
    if request.get('body_present',False):warnings.extend(special_values(request.get('body'),'/request/body',intentional))
    for i,p in enumerate(request.get('query',[])):
        warnings.extend(special_values(p.get('value'),f'/request/query/{i}/value',intentional))
    unique={};
    for w in warnings:unique[(w.get('code'),w.get('path'))]=w
    warnings=list(unique.values())
    case['quality_warnings']=warnings
    if warnings:case['quality_confidence']='low'
    else:case['quality_confidence']=case.get('quality_confidence','unknown')
    return case


def generate(catalog, methods=('GET',), variants=1, fixtures=None):
    if not 1<=variants<=20:raise JapiError('variants must be between 1 and 20')
    methods={m.upper() for m in methods}
    fixtures=fixtures or {}
    result=[]
    for ep in catalog.get('endpoints',[]):
        method=ep['method'].upper()
        if method not in methods:continue
        for index in range(variants):
            warnings=[]; q=[]; path=ep['path']; origins=[]; headers={'Accept':'application/json'}
            for p in ep.get('parameters',[]):
                p=resolve_local_ref(referenced_catalog(catalog),p)
                location=p.get('in');name=p.get('name')
                if not name or location not in ('query','path','header'):continue
                fixture_key=f"{ep['id']}:{name}"
                if fixture_key in fixtures:value,origin=deepcopy(fixtures[fixture_key]),'fixture'
                elif 'example' in p:value,origin=deepcopy(p['example']),'parameter_example'
                elif isinstance(p.get('examples'),dict) and p['examples']:
                    first=next(iter(p['examples'].values()))
                    value,origin=first.get('value',MISSING),'parameter_example'
                else:value,origin=value_for(p.get('schema',{}),catalog,index)
                if value is MISSING:
                    if p.get('required') or location=='path':
                        warnings.append({'code':'REQUIRED_VALUE_UNRESOLVED','severity':'error', 'path':f'{location}/{name}','message':'No safe request value could be generated'})
                    continue
                origins.append(origin)
                if origin=='inferred':warnings.append({'code':'UNVERIFIED_VALUE','severity':'warning','path':f'{location}/{name}','message':'Value is inferred, not a known valid fixture'})
                if location=='path':path=path.replace('{'+name+'}',quote(str(value).lower() if isinstance(value,bool) else str(value),safe=''))
                elif location=='query':q.append({'name':name,'value':value})
                else:
                    if name.lower() not in ('authorization','cookie','proxy-authorization','host'):
                        headers[name]=str(value)
                    else:warnings.append({'code':'AUTH_HEADER_NOT_GENERATED','severity':'warning','path':f'header/{name}','message':'Supply sensitive headers at execution time'})
            unresolved=re.findall(r'\{[^}]+\}',path)
            if unresolved:warnings.append({'code':'PATH_UNRESOLVED','severity':'error','path':path,'message':f'Unresolved path parameters: {unresolved}'})
            body=MISSING
            request_body=ep.get('request_body',{})
            if request_body:
                content=request_body.get('content',{})
                media='application/json' if 'application/json' in content else next(iter(content),None)
                if media:
                    desc=content[media]
                    if 'example' in desc:body,origin=deepcopy(desc['example']),'media_example'
                    elif 'examples' in desc and desc['examples']:
                        first=next(iter(desc['examples'].values()))
                        body,origin=deepcopy(first.get('value',MISSING)),'media_example'
                    else:body,origin=value_for(desc.get('schema',{}),catalog,index)
                    if body is not MISSING:
                        origins.append(origin);headers['Content-Type']=media
                        if origin=='inferred':warnings.append({'code':'UNVERIFIED_BODY','severity':'warning','path':'/request/body','message':'Body generated from type heuristics'})
                    elif request_body.get('required'):
                        warnings.append({'code':'BODY_UNRESOLVED','severity':'error','path':'/request/body','message':'Required body has no constructible schema'})
            statuses=[int(k) for k in ep.get('responses',{}) if str(k).isdigit() and 200<=int(k)<300]
            kind='positive'
            quality='low' if warnings or 'inferred' in origins else 'medium'
            if origins and all(x=='fixture' for x in origins) and statuses:quality='high'
            stable_id=hashlib.sha256(ep['id'].encode('utf-8')).hexdigest()[:12]
            case={'case_id':f'{method.lower()}-{stable_id}-v{index+1:02d}', 'endpoint_id':ep['id'],
                'request':{'method':method,'path':path,'query':q,'headers':headers,'body_present':body is not MISSING},
                'kind':kind,'origin':'deterministic','expected_status':sorted(statuses) or None,
                'intentional_special_values':[], 'quality_confidence':quality,
                'quality_warnings':warnings,'blocked_reason':next((w['code'] for w in warnings if w['severity']=='error'),None)}
            if body is not MISSING:case['request']['body']=body
            result.append(validate_case(case))
    return result


def quality_summary(cases):
    return {'total':len(cases),'low_confidence':sum(c.get('quality_confidence')=='low' for c in cases),
        'blocked':sum(bool(c.get('blocked_reason')) for c in cases),
        'warnings':sum(len(c.get('quality_warnings',[])) for c in cases)}
