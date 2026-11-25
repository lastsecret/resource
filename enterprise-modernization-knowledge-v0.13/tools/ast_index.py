"""Optional JDK compiler-tree analysis. No Maven execution, no annotation processors."""
import base64,os,subprocess,tempfile,shutil
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
def decode(s):return base64.urlsafe_b64decode(s+'='*(-len(s)%4)).decode()

def extract(paths,modules,attribute=False,classpaths=None):
    facts=defaultdict(list); statuses={}; parse_statuses={}; groups=defaultdict(list)
    for p in paths:
        if p.suffix=='.java':groups[modules.bind(p)['module_dir']].append(p)
    if not shutil.which('javac') or not shutil.which('java'):return facts,{'status':'JDK_UNAVAILABLE','files':0,'modules':[]}
    with tempfile.TemporaryDirectory(prefix='migration-ast-') as td:
        tmp=Path(td)
        env={k:v for k,v in os.environ.items() if k not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH','JDK_JAVAC_OPTIONS'}}
        def run(cmd,seconds,stdout):return subprocess.run(cmd,cwd=tmp,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=subprocess.DEVNULL,timeout=seconds,check=False)
        try:
            if run(['javac','-proc:none','-d',td,str(ROOT/'tools/java/AstFacts.java')],30,subprocess.DEVNULL).returncode:return facts,{'status':'HELPER_COMPILE_FAILED','files':0,'modules':[]}
        except (OSError,subprocess.TimeoutExpired):return facts,{'status':'HELPER_UNAVAILABLE','files':0,'modules':[]}
        for group,ps in groups.items():
            # Avoid giant command lines and unbounded fact output. Attribution is per module, never across chunks.
            if len(ps)>500 or sum(p.stat().st_size for p in ps)>12_000_000 or any('\n' in str(p) or '\r' in str(p) for p in ps):
                statuses[group]='LIMIT_SKIPPED';continue
            mf=tmp/'files.txt';mf.write_text('\n'.join(str(p) for p in ps),encoding='utf8')
            out=tmp/'facts.tsv'; cp=(classpaths or {}).get(group,'')
            try:
                with out.open('wb') as f:
                    proc=run(['java','-Xmx512m','-cp',td,'AstFacts','attribute' if attribute else 'parse',str(mf),cp or td],45,f)
                if proc.returncode or out.stat().st_size>30_000_000:statuses[group]='FAILED_OR_LIMIT';continue
                with out.open(encoding='utf8') as f:
                    status=f.readline().strip().split('\t'); statuses[group]=status[1];parse_statuses[group]=status[2] if len(status)>2 else 'UNKNOWN'
                    allowed=set(ps)
                    for line in f:
                        k,p,n,s,r=line.rstrip('\n').split('\t');path=Path(decode(p))
                        if path in allowed:facts[path].append((k,int(n),decode(s),decode(r)))
            except (OSError,ValueError,UnicodeError,subprocess.TimeoutExpired):statuses[group]='FAILED_OR_LIMIT'
    return facts,{'status':'COMPLETE_CANDIDATE_SCAN' if all(s in ('PARSED','ATTRIBUTED') for s in statuses.values()) else 'PARTIAL','files':len(facts),'modules':[{'module_dir':g,'status':s,'parse_status':parse_statuses.get(g,'UNKNOWN')} for g,s in sorted(statuses.items(),key=lambda kv:str(kv[0]))]}
