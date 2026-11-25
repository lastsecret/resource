"""Read pre-exported Maven dependency:tree JSON; evidence import, not trusted execution.
No subprocess invocation; provenance and completeness remain subject to review.
"""
import hashlib,json,re
from pathlib import Path
from safety import files, SAFE_NAME
VER=re.compile(r'\d+(?:\.\d+){1,4}(?:\.Final)?$')
def version(v):
    if not isinstance(v,str) or not VER.fullmatch(v):return None
    parts=tuple(map(int,v.removesuffix('.Final').split('.')))
    return parts+(0,)*(5-len(parts))
def sha(data):return hashlib.sha256(data).hexdigest()
def build_fingerprint(root):
    entries=[]
    for p in files(root):
        if p.name in {'pom.xml','build.gradle','build.gradle.kts','settings.gradle','settings.gradle.kts','gradle.properties','libs.versions.toml'}:
            entries.append((p.relative_to(Path(root).resolve()).as_posix(),sha(p.read_bytes())))
    return sha(json.dumps(sorted(entries),separators=(',',':')).encode())
def import_tree(path):
    p=Path(path)
    if p.stat().st_size>20_000_000:raise ValueError("Graph size limit")
    data=p.read_bytes()
    if len(data)>20_000_000:raise ValueError('Graph size limit')
    obj=json.loads(data);roots=obj if isinstance(obj,list) else [obj]; result=[]; budget=100000
    if not roots:raise ValueError('Empty graph')
    def walk(n,module,depth=0):
        nonlocal budget
        budget-=1
        if budget<0 or depth>100:raise ValueError('Graph complexity limit')
        if not isinstance(n,dict):raise ValueError('Invalid graph node')
        g,a,v=(n.get(k) for k in ('groupId','artifactId','version'))
        if not all(isinstance(x,str) and SAFE_NAME.fullmatch(x) for x in (g,a,v)):raise ValueError('Invalid graph coordinates')
        scope=n.get('scope','')
        if scope not in ('','compile','runtime','provided','test','system','import'):raise ValueError('Invalid scope')
        classifier=n.get('classifier','') or ''
        if not isinstance(classifier,str) or (classifier and not SAFE_NAME.fullmatch(classifier)):raise ValueError('Invalid classifier')
        if depth:result.append({'ga':g+':'+a,'version':v,'scope':scope,'module':module,'classifier':classifier})
        children=n.get('children',[])
        if not isinstance(children,list):raise ValueError('Invalid graph children')
        for child in children:walk(child,module,depth+1)
    seen_modules=set()
    for n in roots:
        if not isinstance(n,dict):raise ValueError('Invalid root')
        module=str(n.get('groupId',''))+':'+str(n.get('artifactId',''))
        if module in seen_modules:raise ValueError('Duplicate graph module')
        seen_modules.add(module);walk(n,module)
    return {'sha256':sha(data),'modules':len(roots),'module_coordinates':sorted(seen_modules),'dependencies':result,'provenance':'USER_IMPORTED_UNATTESTED','completeness':'UNKNOWN'}
def snapshot(source_path,target_path,source_project,target_project):
    return {'source':import_tree(source_path),'target':import_tree(target_path),'source_build_fingerprint':build_fingerprint(source_project),'target_build_fingerprint':build_fingerprint(target_project),'status':'IMPORTED_REVIEW_REQUIRED','note':'Hashes detect byte changes, not proof of build execution, complete module/profile coverage, or graph origin.'}


def attest_capture(graph_side,project,capture_result,merge_result,manifest,profiles):
    """Internal acquisition only. Claims observed discovered POM scope, NOT effective reactor completeness."""
    from module_index import Modules
    mods=Modules(project); rows=mods.report(); expected={x['module_dir']:x['module'] for x in rows}
    captured=capture_result.get('modules',[]); planned=manifest.get('modules',[])
    if not expected or mods.errors or None in expected.values() or len(set(expected.values()))!=len(expected):return False
    if len(captured)!=len(expected) or len(planned)!=len(expected):return False
    if {x['module_dir'] for x in captured}!=set(expected) or {x['module_dir']:x['module'] for x in planned}!=expected:return False
    if sorted(expected.values())!=graph_side['module_coordinates'] or manifest.get('profiles')!=profiles:return False
    if any(x['tree'].get('status')!='EXIT_ZERO' or x['tree'].get('exit_code')!=0 for x in captured):return False
    if capture_result.get('build_fingerprint_changed') or merge_result.get('build_fingerprint_changed') or merge_result.get('missing_modules') or merge_result.get('failed_modules'):return False
    if manifest.get('source_build_fingerprint')!=build_fingerprint(project):return False
    graph_side.update(provenance='SCANNER_CAPTURED_LOCAL',completeness='CAPTURED_DISCOVERED_MODULE_SCOPE',capture_scope={'requested_profiles':profiles or 'DEFAULT_REQUEST','module_count':len(expected),'effective_profiles':'NOT_VERIFIED','reactor':'NON_RECURSIVE_PER_DISCOVERED_POM','build_fingerprint':manifest['source_build_fingerprint'],'classpath_complete':all(x.get('classpath',{}).get('status')=='EXIT_ZERO' and x.get('classpath',{}).get('exit_code')==0 for x in captured)})
    return True
