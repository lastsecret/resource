"""OpenAPI 3 ingestion into a stable catalog. Runtime docs require explicit URL approval."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from .common import JapiError, load_document

HTTP_METHODS = {'get','post','put','patch','delete','head','options','trace'}


def resolve_local_ref(spec, ref, max_depth=12):
    seen = set()
    node = {'$ref':ref} if isinstance(ref,str) else ref
    while isinstance(node, dict) and '$ref' in node:
        r = node['$ref']
        if not r.startswith('#/') or r in seen or len(seen) >= max_depth:
            return node
        seen.add(r)
        value = spec
        for seg in r[2:].split('/'):
            key = seg.replace('~1','/').replace('~0','~')
            if not isinstance(value,dict) or key not in value:
                return node
            value = value[key]
        node = value
    return node


def catalog_from_openapi(spec, origin='openapi'):
    if not isinstance(spec,dict) or not str(spec.get('openapi','')).startswith('3.'):
        raise JapiError('Only OpenAPI 3.x is supported; supply a valid OpenAPI 3 document')
    endpoints=[]
    warnings=[]
    for path, path_item in sorted(spec.get('paths',{}).items()):
        if not isinstance(path_item,dict):
            warnings.append(f'Unresolved path item: {path}'); continue
        path_obj=resolve_local_ref(spec,path_item)
        inherited=path_obj.get('parameters',[])
        for method, operation in sorted(path_obj.items()):
            if method not in HTTP_METHODS: continue
            if not isinstance(operation,dict): continue
            params = {}
            for p in [*inherited, *operation.get('parameters',[])]:
                p=resolve_local_ref(spec,p)
                if isinstance(p,dict) and p.get('name') and p.get('in'):
                    params[(p['in'],p['name'])]=deepcopy(p)
            request=resolve_local_ref(spec,operation.get('requestBody',{}))
            responses={str(code): deepcopy(resolve_local_ref(spec,v)) for code,v in operation.get('responses',{}).items()}
            endpoints.append({'id':f'{method.upper()} {path}', 'method':method.upper(), 'path':path,
               'operation_id':operation.get('operationId'), 'tags':operation.get('tags',[]),
               'parameters':list(params.values()),'request_body':deepcopy(request),
               'responses':responses,'source':origin,'confidence':'declared'})
    return {'format_version':1,'source':origin,'openapi_version':spec['openapi'],
      'endpoints':endpoints,'components':deepcopy(spec.get('components',{})), 'warnings':warnings}


def from_file(path):
    return catalog_from_openapi(load_document(path),f'openapi-file:{Path(path).resolve()}')
