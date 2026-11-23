"""Offline JDK compiler AST adapter (parsing only, no symbol resolution)."""
from __future__ import annotations
from pathlib import Path
import json
import shutil
import subprocess
from .common import JapiError

SCALARS = {
 'String': {'type':'string'},'UUID':{'type':'string','format':'uuid'},'LocalDate':{'type':'string','format':'date'},
 'LocalDateTime':{'type':'string','format':'date-time'},'Instant':{'type':'string','format':'date-time'},
 'int':{'type':'integer'},'Integer':{'type':'integer'},'long':{'type':'integer'},'Long':{'type':'integer'},
 'short':{'type':'integer'},'Short':{'type':'integer'},'boolean':{'type':'boolean'},'Boolean':{'type':'boolean'},
 'double':{'type':'number'},'Double':{'type':'number'},'float':{'type':'number'},'Float':{'type':'number'},
 'BigDecimal':{'type':'number'}
}


def type_schema(t, classes, depth=0):
    t=t.removeprefix('java.lang.').strip()
    if t in SCALARS: return dict(SCALARS[t])
    if t.endswith('[]'): return {'type':'array','items':type_schema(t[:-2],classes,depth+1)}
    for prefix in ('List<','Set<','Collection<'):
        if t.startswith(prefix) and t.endswith('>'):
            return {'type':'array','items':type_schema(t[len(prefix):-1],classes,depth+1)}
    if t.startswith('Optional<') and t.endswith('>'): return type_schema(t[9:-1],classes,depth+1)
    if t in classes: return {'$ref':f'#/components/schemas/{t}'}
    if t in ('void','Void'): return {}
    return {'x-java-type-unresolved':t}


def discover_static(project, java_executable='java'):
    java_path=shutil.which(java_executable)
    if not java_path: raise JapiError('JDK 17+ required for static-jdk mode (java not found)')
    scanner=Path(__file__).resolve().parent/'tools'/'ApiAstScanner.java'
    if not scanner.exists(): raise JapiError(f'Missing packaged AST scanner: {scanner}')
    try:
        proc=subprocess.run([java_path,str(scanner),str(Path(project).resolve())],
          capture_output=True,text=True,timeout=180,check=False)
    except subprocess.TimeoutExpired as e:
        raise JapiError('JDK AST scanner exceeded 180 seconds') from e
    if proc.returncode:
        raise JapiError(f'JDK AST scanner failed: {proc.stderr.strip()[-1200:]}')
    try: raw=json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise JapiError(f'JDK AST scanner returned invalid JSON: {proc.stdout[-300:]} {proc.stderr[-300:]}') from e
    classes=raw['classes']
    schemas={n:{'type':'object','properties':{field:type_schema(ty,classes) for field,ty in fields.items()}}
           for n,fields in classes.items()}
    endpoints=[]
    warnings=list(raw['diagnostics'])
    for raw_ep in raw['endpoints']:
        params=[{'name':p['name'],'in':p['in'],'required':p['required'],
                 'schema':type_schema(p['java_type'],classes)} for p in raw_ep['parameters']]
        body={'required':True,'content':{'application/json':{'schema':type_schema(raw_ep['body_type'],classes)}}} if raw_ep['body_type'] else {}
        schema=type_schema(raw_ep['return_type'],classes)
        endpoints.append({'id':f"{raw_ep['method']} {raw_ep['path']}",
            'method':raw_ep['method'],'path':raw_ep['path'],'operation_id':raw_ep['operation_id'],
            'tags':[],'parameters':params,'request_body':body,
            'responses':{'200':{'content':{'application/json':{'schema':schema}}}} if schema else {},
            'source':raw_ep['source'],'confidence':'inferred'})
    warnings.append('JDK AST scanner does not resolve inherited/controller-interface mappings, Lombok, constants, record components, Jackson customizations, or multi-path mappings, mixed HTTP method mappings, or runtime route conditions; review inferred DTO schemas.')
    return {'format_version':1,'source':f'static-jdk:{Path(project).resolve()}',
        'endpoints':endpoints,'components':{'schemas':schemas},'warnings':warnings}
