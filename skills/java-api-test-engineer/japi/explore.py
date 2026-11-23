"""Explicit opt-in Schemathesis process runner; does not produce frozen A/B cases."""
from __future__ import annotations
from pathlib import Path
import os
import shutil
import subprocess
from .common import JapiError, normalize_url


def explore(openapi,base_url,output,allow_remote=False,allow_mutation=False,max_time=30,max_failures=10):
    executable=shutil.which('st') or shutil.which('schemathesis')
    if not executable:raise JapiError("Schemathesis CLI not installed. Install 'schemathesis' and verify the 'st' command")
    if not Path(openapi).is_file():raise JapiError(f'OpenAPI file not found: {openapi}')
    url=normalize_url(base_url,allow_remote)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':out.chmod(0o700)
    command=[executable,'run',str(Path(openapi).resolve()),'--url',url,
       '--phases','examples,fuzzing','--max-time',str(max_time),'--max-failures',str(max_failures),
       '--request-timeout','5','--max-redirects','0','--report','junit,har','--report-dir',str(out)]
    if not allow_mutation:command+=['--include-method','GET']
    try:
        proc=subprocess.run(command,capture_output=True,text=True,timeout=max_time+40,check=False)
    except subprocess.TimeoutExpired as e:
        raise JapiError('Schemathesis process timed out') from e
    # stdout can include sensitive request payloads: persist locally, never echo into an agent context.
    (out/'schemathesis.log').write_text(proc.stdout[-40000:]+'\n'+proc.stderr[-10000:],encoding='utf-8')
    return {'status':'finished','exit_code':proc.returncode,'report_dir':str(out),
      'replayable_for_ab':False,'message':'Exploratory cases are not automatically frozen for A/B replay'}
