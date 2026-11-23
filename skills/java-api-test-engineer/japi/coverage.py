"""JaCoCo CLI wrapper and XML counter summarizer. No Maven project modification."""
from __future__ import annotations
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from .common import JapiError


def run_jacoco(cli_jar, args, timeout=120):
    jar=Path(cli_jar).resolve()
    if not jar.is_file():raise JapiError(f'JaCoCo CLI JAR not found: {jar}')
    try:
        proc=subprocess.run(['java','-jar',str(jar),*map(str,args)],capture_output=True,text=True,timeout=timeout)
    except FileNotFoundError as e:
        raise JapiError('Java runtime not found') from e
    except subprocess.TimeoutExpired as e:
        raise JapiError('JaCoCo CLI timeout') from e
    if proc.returncode:raise JapiError(f'JaCoCo CLI failed: {(proc.stderr+proc.stdout)[-1300:]}')
    return proc.stdout.strip()


def dump(cli_jar, exec_path, port=6300, reset=False):
    path=Path(exec_path);path.parent.mkdir(parents=True,exist_ok=True)
    args=['dump','--address','127.0.0.1','--port',str(port),'--destfile',str(path)]
    if reset:args.append('--reset')
    return run_jacoco(cli_jar,args)


def report(cli_jar, exec_path, classes, sources=None, output='jacoco', html=True):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    xml=out/'jacoco.xml'
    args=['report',str(exec_path)]
    for x in classes:args+=['--classfiles',str(x)]
    for x in sources or []:args+=['--sourcefiles',str(x)]
    args+=['--xml',str(xml)]
    if html:args+=['--html',str(out/'html')]
    run_jacoco(cli_jar,args,timeout=180)
    return xml


def summarize(xml_path):
    try:root=ET.parse(xml_path).getroot()
    except (OSError,ET.ParseError) as e:raise JapiError(f'Invalid JaCoCo XML: {e}') from e
    if root.tag!='report':raise JapiError('Expected JaCoCo <report> XML')
    counters={}
    for node in root.findall('counter'):
        missed=int(node.get('missed','0'));covered=int(node.get('covered','0'))
        total=missed+covered
        counters[node.get('type')]=dict(missed=missed,covered=covered,total=total,
            pct=round(covered*100/total,2) if total else None)
    packages=[]
    for package in root.findall('package'):
        p={'package':package.get('name'),'counters':{}}
        for node in package.findall('counter'):
            covered=int(node.get('covered','0'));missed=int(node.get('missed','0'))
            p['counters'][node.get('type')]=dict(covered=covered,missed=missed)
        packages.append(p)
    uncovered=[]
    for p in root.findall('package'):
        for source in p.findall('sourcefile'):
            for line in source.findall('line'):
                if int(line.get('mb','0'))>0 or int(line.get('mi','0'))>0:
                    uncovered.append({'source':p.get('name')+'/'+source.get('name'),
                        'line':int(line.get('nr','0')), 'missed_branches':int(line.get('mb','0')),
                        'covered_branches':int(line.get('cb','0')),
                        'missed_instructions':int(line.get('mi','0'))})
    return {'counters':counters,'packages':packages,'uncovered_lines':uncovered,
            'limitations':['JaCoCo branch metrics do not cover every Java decision semantics or exception edge.',
                           'Coverage is JVM-wide for the collection interval, not automatically attributable to an individual endpoint.']}
