"""Bounded, read-only comparison of captured dependency graphs and local classpath artifacts.
No extraction, no class loading, no automatic patch. Classfile comparison is direct API only.
"""
import collections, json, os, re, struct, zipfile
from pathlib import Path
from inventory import version
from safety import files, SAFE_NAME


def graph_diff(graph):
    if not graph:return {'status':'NOT_RUN_NO_GRAPH','changes':[]}
    def index(side):
        d=collections.defaultdict(set)
        for x in graph[side]['dependencies']:d[(x['module'],x['ga'],x['scope'],x['classifier'])].add(x['version'])
        return d
    a,b=index('source'),index('target'); changes=[]
    for k in sorted(a.keys()|b.keys()):
        if a[k]!=b[k]:changes.append(dict(zip(('module','ga','scope','classifier'),k),source=sorted(a[k]),target=sorted(b[k]),kind='CHANGED' if a[k] and b[k] else 'ADDED' if b[k] else 'REMOVED'))
    return {'status':'COMPARED_CAPTURED_SCOPE' if all(graph[s].get('provenance')=='SCANNER_CAPTURED_LOCAL' for s in ('source','target')) else 'COMPARED_IMPORTED_UNATTESTED','changes':changes[:3000],'total_changes':len(changes),'truncated':len(changes)>3000}


def gaps(graph,specs):
    if not graph:return []
    # Only flag known bounded family intervals. No assertion of full knowledge coverage elsewhere.
    limits={}
    for rid,s in specs.items():
        c=s.get('component') or {}; maximum=version(c.get('target_max_exclusive'))
        if not maximum:continue
        for ga in c.get('target_ga',[]):
            if ga not in limits or maximum>limits[ga][0]:limits[ga]=(maximum,c['target_max_exclusive'])
    out=[]
    for x in graph['target']['dependencies']:
        lim=limits.get(x['ga']);v=version(x['version'])
        if not lim or not v or v<lim[0]:continue
        old=[y for y in graph['source']['dependencies'] if (y['module'],y['ga'],y['scope'],y['classifier'])==(x['module'],x['ga'],x['scope'],x['classifier'])]
        if old and all(y['version']==x['version'] for y in old):continue
        row={'module':x['module'],'ga':x['ga'],'target_version':x['version'],'known_rule_upper_exclusive':lim[1],'code':'KNOWLEDGE_COVERAGE_GAP','decision':'REVIEW_REQUIRED'}
        if row not in out:out.append(row)
    return out


class Jars:
    def __init__(self,cp):
        self.jars=[];self.errors=0;self.names={};self.duplicates=set()
        for item in cp.split(os.pathsep) if cp else []:
            p=Path(item)
            if not p.is_absolute() or p.suffix.lower()!='.jar' or not p.is_file() or p.stat().st_size>250_000_000:
                self.errors+=1;continue
            if len(self.jars)>=400:self.errors+=1;break
            try:
                z=zipfile.ZipFile(p)
                if len(z.infolist())>100000:z.close();self.errors+=1;continue
                self.jars.append(z)
                for info in z.infolist():
                    if info.filename.startswith('org/springframework/boot/') and info.filename.endswith('.class'):
                        if info.filename in self.names:self.duplicates.add(info.filename)
                        self.names[info.filename]=z
            except (OSError,zipfile.BadZipFile):self.errors+=1
    def close(self):
        for z in self.jars:z.close()
    def read(self,z,name):
        info=z.getinfo(name)
        if info.file_size>4_000_000:raise ValueError('entry limit')
        return z.read(info)
    def metadata(self):
        data={};ambiguous=set()
        for z in self.jars:
            for name in ('META-INF/spring-configuration-metadata.json','META-INF/additional-spring-configuration-metadata.json'):
                try: obj=json.loads(self.read(z,name))
                except KeyError:continue
                except (OSError,ValueError,zipfile.BadZipFile):self.errors+=1;continue
                if not isinstance(obj,dict) or not isinstance(obj.get('properties',[]),list):self.errors+=1;continue
                for p in obj.get('properties',[]):
                    if not isinstance(p,dict) or not isinstance(p.get('name'),str) or not SAFE_NAME.fullmatch(p['name']):continue
                    k=p['name']; sig=(p.get('type'),p.get('defaultValue'),p.get('deprecation'))
                    if k in data and data[k]!=sig:ambiguous.add(k)
                    data[k]=sig
        return data,ambiguous
    def class_api(self,name):
        key=name.replace('.','/')+'.class'
        if key in self.duplicates:raise ValueError('duplicate class')
        if key not in self.names:return None
        return class_members(self.read(self.names[key],key))


def class_members(data):
    """Parse classfile constant pool and direct public/protected descriptors. No code execution."""
    if data[:4]!=b'\xca\xfe\xba\xbe':raise ValueError('not class')
    i=8
    def u(n):
        nonlocal i
        if i+n>len(data):raise ValueError('truncated class')
        v=int.from_bytes(data[i:i+n],'big');i+=n;return v
    def skip(n):
        nonlocal i
        if i+n>len(data):raise ValueError('truncated class')
        i+=n
    cp={};n=u(2);j=1
    while j<n:
        t=u(1)
        if t==1:
            l=u(2);cp[j]=data[i:i+l].decode('utf8',errors='replace');skip(l)
        elif t in (3,4,9,10,11,12,17,18):skip(4)
        elif t in (5,6):skip(8);j+=1
        elif t in (7,8,16,19,20):skip(2)
        elif t==15:skip(3)
        else:raise ValueError('unsupported constant pool')
        j+=1
    access=u(2);skip(4);skip(u(2)*2)
    result=set()
    for kind in ('FIELD','METHOD'):
        for _ in range(u(2)):
            flags,ni,di,ac=u(2),u(2),u(2),u(2)
            if flags&5 and ni in cp and di in cp:result.add((kind,cp[ni],cp[di],bool(flags&8)))
            for _ in range(ac):skip(2);skip(u(4))
    return (bool(access&1),result)


def compare_artifacts(project,source_cp,target_cp):
    """Compare exact provided classpath manifests; results are candidate evidence only."""
    if not source_cp or not target_cp:return {'status':'NOT_RUN_NO_PAIRED_CLASSPATH','configuration':[],'api':[],'modules':[]}
    from module_index import Modules
    from project_scanner import parse_yaml,parse_properties
    from ast_index import extract
    paths=list(files(project));mods=Modules(project,paths)
    facts,astmeta=extract(paths,mods,True,source_cp)
    imports=collections.defaultdict(lambda:collections.defaultdict(set));refs=collections.defaultdict(lambda:collections.defaultdict(set));keys=collections.defaultdict(lambda:collections.defaultdict(set))
    for p,fs in facts.items():
        md=mods.bind(p)['module_dir'];rel=p.relative_to(Path(project).resolve()).as_posix()
        for kind,line,v,r in fs:
            if kind=='import' and v.startswith('org.springframework.boot.') and not v.endswith('.*'):imports[md][v].add(f'{rel}:{line}')
            if kind=='invocation' and r.startswith('org.springframework.boot.') and '#' in r:
                owner,name=r.rsplit('#',1);refs[md][(owner,name)].add(f'{rel}:{line}');imports[md][owner].add(f'{rel}:{line}')
    for p in paths:
        if p.suffix not in ('.properties','.yml','.yaml'):continue
        md=mods.bind(p)['module_dir'];rel=p.relative_to(Path(project).resolve()).as_posix()
        entries,_=parse_properties(p) if p.suffix=='.properties' else parse_yaml(p)
        for e in entries:
            if SAFE_NAME.fullmatch(e['key']):keys[md][e['key']].add(f'{rel}:{e["line"]}')
    result={'status':'CANDIDATE_COMPARISON','configuration':[],'api':[],'modules':[],'unpaired_classpath_modules':sorted(set(source_cp)^set(target_cp))}
    for md in sorted(set(source_cp)&set(target_cp)):
        a,b=Jars(source_cp[md]),Jars(target_cp[md])
        try:
            am,aa=a.metadata();bm,ba=b.metadata()
            for key,locs in keys[md].items():
                if key not in am or key in aa or key in ba:continue
                if key not in bm:
                    kind='METADATA_UNAVAILABLE_IN_TARGET_CLASSPATH' # no proof of removal/module ownership
                elif am[key]!=bm[key]:
                    old,new=am[key],bm[key]
                    kind='METADATA_DEFAULT_CHANGED' if old[0]==new[0] and old[2]==new[2] else 'METADATA_CHANGED'
                    if isinstance(new[2],dict) and isinstance(new[2].get('replacement'),str):kind='METADATA_REPLACEMENT_HINT' 
                else:continue
                result['configuration'].append({'module_dir':md,'locations':sorted(locs),'kind':kind,'decision':'REVIEW_REQUIRED'})
            for name,locs in imports[md].items():
                try:x,y=a.class_api(name),b.class_api(name)
                except (ValueError,KeyError,OSError,zipfile.BadZipFile):a.errors+=1;continue
                if not x:continue
                if y is None:result['api'].append({'module_dir':md,'locations':sorted(locs),'kind':'CLASS_NOT_FOUND_IN_TARGET_CLASSPATH','decision':'REVIEW_REQUIRED'});continue
                removed=x[1]-y[1]
                for member in {m[1] for m in removed}:
                    found=refs[md].get((name,member),set())
                    if found:result['api'].append({'module_dir':md,'locations':sorted(found),'kind':'DIRECT_API_DESCRIPTOR_CHANGED_OR_REMOVED','decision':'REVIEW_REQUIRED'})
            result['modules'].append({'module_dir':md,'source_jars':len(a.jars),'target_jars':len(b.jars),'errors':a.errors+b.errors,'metadata_source_keys':len(am),'metadata_target_keys':len(bm),'metadata_changed_keys':sum(am[k]!=bm[k] for k in am.keys()&bm.keys() if k not in aa and k not in ba),'metadata_missing_keys':len(am.keys()-bm.keys()),'api_scope':'DIRECT_REFERENCED_BOOT_CLASSES_ONLY'})
        finally:a.close();b.close()
    return result


def attach(report,project,source_cp=None,target_cp=None):
    """Connect artifact comparisons to the three previously unimplemented rule entries."""
    from detectors import load_registry
    from module_index import Modules
    g=report.get('inventory'); delta=graph_diff(g);report['dependency_diff']=delta
    report['knowledge_coverage_gaps']=gaps(g,load_registry())
    try: artifact=compare_artifacts(project,source_cp,target_cp)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,RecursionError):artifact={'status':'COMPARISON_FAILED','configuration':[],'api':[],'modules':[]}
    report['artifact_diffs']=artifact
    mods=Modules(project); byid={r['rule_id']:r for r in report.get('evaluations',[])}
    def update(rid,items,kind,executed,scope_complete=False):
        r=byid.get(rid)
        if not r or not executed:return
        hits=[]
        for x in items:
            for loc in x.get('locations',[]):
                binding=mods.bind(loc.rsplit(':',1)[0] if loc.rsplit(':',1)[-1].isdigit() else loc)
                hit={'location':loc,'detector':kind,'evidence_kind':x.get('kind','CANDIDATE_DIFF'),'symbol_attributed':False,'component_module_association':'NOT_VERIFIED',**binding}
                if hit not in hits:hits.append(hit)
        r['detector']=kind;r['locations']=sorted({x['location'] for x in hits});r['location_evidence']=hits
        r['status']='DETECTED' if hits else 'NOT_DETECTED' if scope_complete else 'UNKNOWN'
        r['execution_strategy']=['ARTIFACT_DIFF_CANDIDATE','REVIEW_REQUIRED']
        r['semantic_resolution']='PARTIAL';r['effective_configuration']='UNKNOWN';r['agent_fallback']='REQUIRED';r['decision']='REVIEW_REQUIRED'
        report['findings']=[f for f in report['findings'] if f['rule_id']!=rid]
        if hits:report['findings'].append({**r,'confidence':'STATIC_CANDIDATE_ONLY'})
    modmap={m['module']:m['module_dir'] for m in mods.report() if m['module']}
    changes=[{'locations':[str(Path(modmap[x['module']])/'pom.xml')],'kind':'DEPENDENCY_'+x['kind']} for x in delta['changes'] if x['module'] in modmap]
    update('SB41-DEPENDENCY-BOM-011',changes,'dependency.graph_diff',bool(g),delta['status']=='COMPARED_CAPTURED_SCOPE' and not delta.get('truncated'))
    executed=artifact['status']=='CANDIDATE_COMPARISON'
    update('SB4-PROPERTIES-004',artifact['configuration'],'config.metadata_diff',executed)
    update('SB41-DEPRECATED-001',artifact['api'],'jar.direct_api_diff',executed)
    report['coverage']={k:sum(x['status']==k for x in report.get('evaluations',[])) for k in ('DETECTED','NOT_DETECTED','UNKNOWN','NOT_EVALUATED','NOT_APPLICABLE')}
    return report
