"""Compare explicit, externally executed fixture observations; never authorizes migration.
Input: {build_fingerprint: SHA256, cases: [{id, outcome: OBSERVED|FAILED|NOT_RUN,
observation: <JSON>}]}. Output exports only case IDs and equality, not values.
The input is user-supplied, not an independently attested test execution.
"""
import argparse,json,re,sys,hashlib
from pathlib import Path
from safety import output_file
from inventory import build_fingerprint

def read(path,project):
    p=Path(path)
    if p.stat().st_size>10_000_000:raise ValueError('Runtime evidence size')
    raw=p.read_bytes();d=json.loads(raw)
    if d.get('build_fingerprint')!=build_fingerprint(project):raise ValueError('Build fingerprint mismatch')
    cases={}
    for x in d.get('cases',[]):
        id=x.get('id')
        if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',id) or id in cases or x.get('outcome') not in ('OBSERVED','FAILED','NOT_RUN'):raise ValueError('Invalid case')
        if x['outcome']=='OBSERVED' and 'observation' not in x:raise ValueError('Missing observation')
        cases[id]=x
    if not cases:raise ValueError('Empty observation set')
    return cases,hashlib.sha256(raw).hexdigest()

def compare(source,target,source_project,target_project):
    a,ah=read(source,source_project);b,bh=read(target,target_project)
    rows=[]
    for id in sorted(a.keys()|b.keys()):
        x=a.get(id,{});y=b.get(id,{})
        if x.get('outcome')!='OBSERVED' or y.get('outcome')!='OBSERVED':status='INCOMPLETE'
        else:status='OBSERVATION_MATCH' if json.dumps(x['observation'],sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(y['observation'],sort_keys=True,separators=(',',':'),allow_nan=False) else 'OBSERVATION_DIFF'
        rows.append({'id':id,'status':status})
    return {'provenance':'USER_IMPORTED_RUNTIME_UNATTESTED','source_sha256':ah,'target_sha256':bh,'cases':rows,'gate':'BLOCKED_PENDING_VERIFIED_EVIDENCE','automatic_patch':False,'note':'Equality is not correctness; fingerprints cover build files only; original execution and case expectations require independent verification.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('source','target','source-project','target-project','output'):p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    try:
        if a.output.resolve().is_relative_to(a.target_project.resolve()):raise ValueError('Output must be outside target')
        r=compare(a.source,a.target,a.source_project,a.target_project);output_file(a.output,a.source_project,json.dumps(r,indent=2)+'\n');return 2
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as e:print('RUNTIME_IMPORT_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
