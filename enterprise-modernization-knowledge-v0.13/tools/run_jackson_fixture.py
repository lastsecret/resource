#!/usr/bin/env python3
"""Explicitly approved execution of bundled standalone Jackson probes, offline by default.
Only synthetic fixture; not evidence of production mapper behavior. No automatic gate pass.
"""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from safety import output_dir
ROOT=Path(__file__).resolve().parents[1]/'verification-fixtures/jackson'
def run(out,approved=False,online=False):
    if not approved:raise ValueError('Explicit build approval required')
    out=output_dir(out,ROOT);mvn=shutil.which('mvn');result={'schema_version':'0.13','scope':'BUNDLED_SYNTHETIC_JACKSON_FIXTURE','gate':'BLOCKED_PENDING_VERIFIED_EVIDENCE','runtime_verification':'NOT_RUN','runs':{},'comparison':None}
    if not mvn:result['reason']='MAVEN_UNAVAILABLE'
    else:
        # Copy only fixture to disposable external workspace; never modify pack.
        with tempfile.TemporaryDirectory(prefix='modernization-probe-') as temp:
            work=Path(temp)/'fixture';shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('target','__pycache__'))
            for label in ('jackson2','jackson3'):
                command=[mvn,'-B']+([] if online else ['-o'])+['-f',str(work/label/'pom.xml'),'compile','exec:java','-Dexec.mainClass=demo.Probe']
                dest=Path(temp)/(label+'.out')
                try:
                    with dest.open('wb') as f:p=subprocess.run(command,cwd=work,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=240)
                    result['runs'][label]={'exit_code':p.returncode,'status':'EXIT_ZERO' if p.returncode==0 else 'FAILED'}
                except (OSError,subprocess.TimeoutExpired):result['runs'][label]={'status':'FAILED_OR_TIMEOUT'}
            if all(x['status']=='EXIT_ZERO' for x in result['runs'].values()):
                try:
                    p=subprocess.run([sys.executable,str(work/'compare.py'),str(Path(temp)/'jackson2.out'),str(Path(temp)/'jackson3.out')],capture_output=True,timeout=30)
                    rows=json.loads(p.stdout)
                    result['comparison']=[{k:v for k,v in x.items() if k in ('source','target','input','semantic_match','order_semantic_match','order_exact_match')} for x in rows]
                    result['runtime_verification']='SYNTHETIC_OBSERVED' if p.returncode in (0,2) else 'FAILED'
                except (ValueError,OSError,subprocess.TimeoutExpired):result['runtime_verification']='FAILED'
            else:result['runtime_verification']='FAILED'
    (out/'runtime-fixture-report.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--execute-approved-build',action='store_true');p.add_argument('--online',action='store_true');a=p.parse_args()
    try:r=run(a.output,a.execute_approved_build,a.online);print(r['runtime_verification']);return 2 if r['runtime_verification']=='SYNTHETIC_OBSERVED' else 3
    except (OSError,ValueError) as e:print('FIXTURE_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
