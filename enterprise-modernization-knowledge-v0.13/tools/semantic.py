"""Scoped semantic candidates for high-risk families. No source text or symbol values exported.
Resolved owners take precedence; import/variable hints are explicitly weaker than attribution.
Does not prove mapper reachability, effective settings or behavioral compatibility.
"""
from collections import defaultdict
import re
JACK=('com.fasterxml.jackson.','tools.jackson.')
SEC='org.springframework.security.'
TARGETS={'JCK3-POJO-ORDER-002','JCK31-NULLNODE-001','JCK3-MAPPER-TOPOLOGY-003','SEC7-DSL-001','SB41-JACKSON-HANDLER-009','SB4-JACKSON-API-006','JCK3-NULL-PRIMITIVES-001'}

def collect_semantic(root,facts,mods):
    hits=defaultdict(list); scanned=set(); excluded=defaultdict(int)
    methods=defaultdict(list)
    for path,fs in facts.items():
        for k,l,v,r in fs:
            if k!='method_info':continue
            owner,name,arity,end,ret=v.split('#',4)
            if ret.rsplit('.',1)[-1] not in ('ObjectMapper','JsonMapper'):continue
            if not (ret.startswith(JACK) or any(kk=='import' and (vv.startswith(JACK) and (vv.endswith('.'+ret) or vv.endswith('.*'))) for kk,ll,vv,rr in fs)):continue
            features=sorted({vv for kk,ll,vv,rr in fs if kk=='feature_switch' and l<=ll<=int(end)})
            methods[(mods.bind(path)['module_dir'],owner,name,arity)].append({'location':f'{path.relative_to(root).as_posix()}:{l}','feature_hints':[f.replace('#',':') for f in features]})
    for path,fs in facts.items():
        if not fs:continue
        rel=path.relative_to(root).as_posix();scanned.add(rel)
        imports={v for k,l,v,r in fs if k=='import'}
        vars=defaultdict(set)
        for k,l,v,r in fs:
            if k=='variable_type' and '#' in v:
                a,b=v.split('#',1);vars[a].add(b)
        def family_type(t,prefix):
            if t.startswith(prefix):return True
            if '.' in t:return False
            return any(x.startswith(prefix) and (x.endswith('.'+t) or x.endswith('.*')) for x in imports)
        def inferred(receiver,prefix):
            if receiver.startswith(prefix):return True
            if receiver.startswith('this.'):receiver=receiver[5:]
            if receiver in vars:return len(vars[receiver])==1 and family_type(next(iter(vars[receiver])),prefix)
            return family_type(receiver,prefix)
        def emit(rid,line,mode,detail):
            hit={'location':f'{rel}:{line}','detector':'java.semantic','evidence_kind':mode,'symbol_attributed':mode=='JAVAC_RESOLVED_OWNER','semantic_detail':detail,**mods.bind(path)}
            if hit not in hits[rid]:hits[rid].append(hit)
        factories={l:v for k,l,v,r in fs if k=='bean_factory'}
        declared_owners=[v.split('#',1)[0] for k,l,v,r in fs if k=='method_info']
        def factory_link(line):
            if line not in factories:return None
            select,arity=factories[line].rsplit('#',1)
            if '.' not in select:return None
            receiver,name=select.rsplit('.',1)
            # Unique explicit import, qualified class or same-package owner. Not a general call graph.
            candidates={receiver} if '.' in receiver else {x for x in imports if x.endswith('.'+receiver)} | {x.rsplit('.',1)[0]+'.'+receiver for x in declared_owners if '.' in x}
            matches=[m for c in candidates for m in methods.get((mods.bind(path)['module_dir'],c,name,arity),[])]
            return matches[0] if len(matches)==1 else None
        for k,l,v,r in fs:
            if k=='import' and v.startswith(('com.fasterxml.jackson.databind.','org.springframework.boot.jackson.','org.springframework.boot.autoconfigure.jackson.')):
                emit('SB4-JACKSON-API-006',l,'QUALIFIED_IMPORT','JACKSON_API_IMPORT' if v.startswith('com.fasterxml.jackson.') else 'BOOT_JACKSON_API_IMPORT')
            if k=='bean_method' and (r.startswith(JACK) or (not r and any(family_type(v,p) for p in JACK))) and v.rsplit('.',1)[-1] in ('ObjectMapper','JsonMapper'):
                mode='JAVAC_RESOLVED_OWNER' if r else 'AST_IMPORT_TYPE_HINT'
                emit('JCK3-MAPPER-TOPOLOGY-003',l,mode,'MAPPER_BEAN_FACTORY_RETURN' if l in factories else 'MAPPER_BEAN_RETURN_TYPE')
                link=factory_link(l)
                if link:
                    hits['JCK3-MAPPER-TOPOLOGY-003'][-1]['factory_link']={**link,'status':'ONE_HOP_STATIC_CANDIDATE'}
                emit('SB41-JACKSON-HANDLER-009',l,mode,'MAPPER_BEAN_CANDIDATE')
            if k=='construction':
                ok=r.startswith(JACK) if r else any(family_type(v,p) for p in JACK)
                if ok and v.rsplit('.',1)[-1] in ('ObjectMapper','JsonMapper'):
                    for rid in ('JCK3-MAPPER-TOPOLOGY-003','SB41-JACKSON-HANDLER-009'):emit(rid,l,'JAVAC_RESOLVED_OWNER' if r else 'AST_IMPORT_TYPE_HINT','MAPPER_CONSTRUCTOR')
            if k=='annotation' and v.rsplit('.',1)[-1]=='JsonDeserialize' and (r.startswith(JACK) or (not r and any(family_type(v,p) for p in JACK))):emit('SB41-JACKSON-HANDLER-009',l,'JAVAC_RESOLVED_OWNER' if r else 'AST_IMPORT_TYPE_HINT','DESERIALIZER_ANNOTATION')
            if k=='symbol' and v.rsplit('.',1)[-1] in ('FAIL_ON_NULL_FOR_PRIMITIVES','SORT_PROPERTIES_ALPHABETICALLY','JsonPropertyOrder') and (r.startswith(JACK) or (not r and any(x.startswith(JACK) for x in imports))):
                emit('JCK3-NULL-PRIMITIVES-001' if v.endswith('FAIL_ON_NULL_FOR_PRIMITIVES') else 'JCK3-POJO-ORDER-002',l,'JAVAC_RESOLVED_OWNER' if r else 'AST_IMPORT_TYPE_HINT','FEATURE_OR_ANNOTATION')
            if k!='invocation':continue
            method,arity=v.rsplit('#',1); name=method.rsplit('.',1)[-1];receiver=method.rsplit('.',1)[0] if '.' in method else ''
            jack=r.startswith(JACK) if r else any(inferred(receiver,p) for p in JACK)
            sec=r.startswith(SEC) if r else inferred(receiver,SEC)
            mode='JAVAC_RESOLVED_OWNER' if r else 'AST_IMPORT_TYPE_HINT'
            if jack:
                if name in ('writeValueAsString','writeValueAsBytes','writeValue'):
                    digest=any(kk=='invocation' and ll==l and vv.rsplit('#',1)[0].endswith(('.digest','.doFinal','.sign')) for kk,ll,vv,rr in fs)
                    emit('JCK3-POJO-ORDER-002',l,mode,'SERIALIZATION_WITH_SAME_LINE_SINK_HINT' if digest else 'SERIALIZATION_CALL')
                if name in ('readValue','readTree'):emit('JCK3-NULL-PRIMITIVES-001',l,mode,'DESERIALIZATION_CALL')
                if re.fullmatch(r'as(?:Text|Int|Long|Double|Boolean|String)(?:Opt)?',name) and arity=='1':emit('JCK31-NULLNODE-001',l,mode,'DEFAULT_ARGUMENT_NODE_ACCESSOR')
                if name=='builder':
                    for rid in ('JCK3-MAPPER-TOPOLOGY-003','SB41-JACKSON-HANDLER-009'):emit(rid,l,mode,'MAPPER_BUILDER')
            if sec and arity=='0' and name in ('authorizeHttpRequests','authorizeRequests','and','csrf','cors','formLogin','httpBasic','logout','sessionManagement','exceptionHandling','headers','rememberMe','requestCache','securityContext','anonymous','oauth2Login','oauth2Client','oauth2ResourceServer'):
                emit('SEC7-DSL-001',l,mode,'NO_ARGUMENT_SECURITY_DSL')
            # Unresolved chained legacy DSL: preserve .and() hint in a file importing Spring Security.
            if not r and name=='and' and arity=='0' and any(x.startswith(SEC) for x in imports):emit('SEC7-DSL-001',l,'AST_IMPORT_TYPE_HINT','UNRESOLVED_CHAIN_DSL')
    return hits,scanned
