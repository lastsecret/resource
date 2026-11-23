"""Modular command-line interface. Each stage runs independently, no LLM required."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request
from urllib.error import URLError, HTTPError
from . import __version__
from .common import JapiError, load_document, load_jsonl, save_json, save_jsonl, compact_summary, normalize_url
from .inspect import inspect
from .discover import from_file, catalog_from_openapi
from .static import discover_static
from .cases import generate, quality_summary
from .http_run import execute, parse_headers, run_summary, OPENER
from .diff import compare, validate_policy
from .coverage import dump, report, summarize
from .enrich import context_bundle
from .html_report import render_diff
from .explore import explore


def main_parser():
    parser=argparse.ArgumentParser(prog='japi',description='Java API discovery, deterministic replay and A/B comparison')
    parser.add_argument('--version',action='version',version=__version__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inspect',help='Offline capability detection; never starts services or builds')
    p.add_argument('--project',required=True);p.add_argument('--output',default='out/inspection')
    p=sub.add_parser('discover',help='Select a specific endpoint discovery adapter')
    p.add_argument('--mode',choices=['openapi-file','static-jdk','springdoc-runtime'],required=True)
    p.add_argument('--project');p.add_argument('--openapi');p.add_argument('--docs-url')
    p.add_argument('--allow-remote',action='store_true');p.add_argument('--output',default='out/discovery')
    p=sub.add_parser('generate',help='Freeze deterministic requests (GET by default)')
    p.add_argument('--catalog',required=True);p.add_argument('--methods',default='GET',help='Comma separated HTTP methods')
    p.add_argument('--variants',type=int,default=1);p.add_argument('--fixtures',help='JSON object mapping "METHOD /path:name" to concrete values')
    p.add_argument('--output',default='out/cases')
    p=sub.add_parser('execute',help='Replay frozen HTTP cases; optionally start an instrumented local JAR')
    p.add_argument('--cases',required=True);p.add_argument('--base-url',required=True)
    p.add_argument('--allow-remote',action='store_true');p.add_argument('--allow-mutation',action='store_true')
    p.add_argument('--block-low-confidence',action='store_true');p.add_argument('--header',action='append')
    p.add_argument('--timeout',type=float,default=10);p.add_argument('--max-body-bytes',type=int,default=2000000)
    p.add_argument('--launch-jar',help='Explicitly launch a local Java JAR (not a shell command)')
    p.add_argument('--app-arg',action='append',default=[])
    p.add_argument('--jacoco-agent',help='JaCoCo agent JAR for locally launched JVM')
    p.add_argument('--jacoco-cli',help='JaCoCo CLI JAR to dump execution data after replay')
    p.add_argument('--jacoco-port',type=int,default=6300)
    p.add_argument('--ready-timeout',type=float,default=45)
    p.add_argument('--output',default='out/execution')
    p=sub.add_parser('compare',help='Compare frozen-case response artifacts or replay both targets')
    input_group=p.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--cases');input_group.add_argument('--a-results')
    p.add_argument('--b-results');p.add_argument('--a-url');p.add_argument('--b-url')
    p.add_argument('--rules',help='YAML/JSON comparison policy')
    p.add_argument('--allow-remote',action='store_true');p.add_argument('--allow-mutation',action='store_true')
    p.add_argument('--block-low-confidence',action='store_true');p.add_argument('--header',action='append')
    p.add_argument('--timeout',type=float,default=10);p.add_argument('--max-body-bytes',type=int,default=2000000)
    p.add_argument('--output',default='out/comparison')
    p=sub.add_parser('coverage',help='JaCoCo data collection, XML report and summary')
    cov=p.add_subparsers(dest='coverage_action',required=True)
    c=cov.add_parser('dump',help='Dump an already instrumented localhost JVM')
    c.add_argument('--jacoco-cli',required=True);c.add_argument('--port',type=int,default=6300)
    c.add_argument('--reset',action='store_true');c.add_argument('--exec',default='out/coverage/jacoco.exec')
    c=cov.add_parser('report',help='Build HTML and XML from JaCoCo .exec')
    c.add_argument('--jacoco-cli',required=True);c.add_argument('--exec',required=True)
    c.add_argument('--classes',action='append',required=True);c.add_argument('--sources',action='append')
    c.add_argument('--output',default='out/coverage')
    c=cov.add_parser('summarize',help='Summarize existing JaCoCo XML (no JAR required)')
    c.add_argument('--xml',required=True);c.add_argument('--output',default='out/coverage')
    p=sub.add_parser('explore',help='Optional Schemathesis exploration (GET only by default)')
    p.add_argument('--openapi',required=True);p.add_argument('--base-url',required=True)
    p.add_argument('--allow-remote',action='store_true');p.add_argument('--allow-mutation',action='store_true')
    p.add_argument('--max-time',type=int,default=30);p.add_argument('--max-failures',type=int,default=10)
    p.add_argument('--output',default='out/exploration')
    p=sub.add_parser('enrich',help='Create bounded source context for explicit external agent review')
    p.add_argument('--project',required=True);p.add_argument('--catalog',required=True);p.add_argument('--coverage-xml')
    p.add_argument('--max-sources',type=int,default=12);p.add_argument('--output',default='out/enrich')
    return parser


def output_summary(out,data):
    save_json(Path(out)/'summary.json',data)
    print(compact_summary({'output':str(Path(out).resolve()), **data}))


def launch_java(args,folder):
    normalize_url(args.base_url,allow_remote=False)
    if not Path(args.launch_jar).is_file():raise JapiError('launch-jar does not exist')
    command=['java']
    if args.jacoco_agent:
        if not Path(args.jacoco_agent).is_file():raise JapiError('jacoco-agent JAR does not exist')
        command.append(f'-javaagent:{Path(args.jacoco_agent).resolve()}=output=tcpserver,address=127.0.0.1,port={args.jacoco_port}')
    command+=['-jar',str(Path(args.launch_jar).resolve()),*args.app_arg]
    folder.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':folder.chmod(0o700)
    log=open(folder/'local-app.log','w',encoding='utf-8')
    if os.name!='nt':(folder/'local-app.log').chmod(0o600)
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    start=time.monotonic()
    try:
        while time.monotonic()-start<args.ready_timeout:
            if process.poll() is not None:raise JapiError(f'Launched application exited with {process.returncode}; inspect local-app.log')
            try:
                r=OPENER.open(Request(args.base_url),timeout=1)
                r.close();break
            except HTTPError:
                break  # HTTP 4xx/5xx still means the local HTTP listener is ready
            except Exception:
                time.sleep(0.4)
        else:raise JapiError(f'Local app not ready in {args.ready_timeout}s; inspect local-app.log')
        return process,log
    except Exception:
        process.terminate();process.wait(timeout=5);log.close();raise


def command(args):
    out=Path(getattr(args,'output','out'))
    if args.command=='inspect':
        data=inspect(args.project);save_json(out/'capabilities.json',data)
        output_summary(out,{'recommended':data['recommended'],'candidates':data['candidates'],
                            'openapi_files':data['openapi_files'],'selection_required':True})
        return 0
    if args.command=='discover':
        if args.mode=='openapi-file':
            if not args.openapi:raise JapiError('--openapi required for openapi-file')
            cat=from_file(args.openapi)
        elif args.mode=='static-jdk':
            if not args.project:raise JapiError('--project required for static-jdk')
            cat=discover_static(args.project)
        else:
            if not args.docs_url:raise JapiError('--docs-url required for springdoc-runtime')
            url=normalize_url(args.docs_url,args.allow_remote)
            try:
                with OPENER.open(Request(url,headers={'Accept':'application/json'}),timeout=10) as r:
                    if int(r.headers.get('Content-Length','0'))>8_000_000:raise JapiError('OpenAPI contract exceeds 8MB')
                    content=r.read(8_000_001)
                if len(content)>8_000_000:raise JapiError('OpenAPI contract exceeds 8MB')
                spec=json.loads(content)
            except (ValueError,URLError) as e:raise JapiError(f'Cannot retrieve Springdoc OpenAPI: {e}') from e
            cat=catalog_from_openapi(spec,'springdoc-runtime')
        save_json(out/'endpoints.json',cat)
        save_json(out/'discovery-decision.json',{'selected_mode':args.mode,'source':cat['source'],
                 'limitations':cat.get('warnings',[])})
        output_summary(out,{'endpoints':len(cat['endpoints']),'warnings':len(cat.get('warnings',[])), 'mode':args.mode})
        return 0
    if args.command=='generate':
        cases=generate(load_document(args.catalog),args.methods.split(','),args.variants,
                       load_document(args.fixtures) if args.fixtures else None)
        save_jsonl(out/'cases.jsonl',cases)
        summary=quality_summary(cases)
        save_json(out/'case-quality.json',{'summary':summary,'cases':[
            {'case_id':c['case_id'],'confidence':c['quality_confidence'],'warnings':c['quality_warnings']} for c in cases]})
        output_summary(out,summary)
        return 0
    if args.command=='execute':
        cases=load_jsonl(args.cases);headers=parse_headers(args.header)
        process=log=None
        try:
            if args.launch_jar:process,log=launch_java(args,out)
            results=execute(cases,args.base_url,args.allow_remote,args.allow_mutation,headers,args.timeout,
                            args.max_body_bytes,not args.block_low_confidence)
            save_jsonl(out/'results.jsonl',results)
            summary=run_summary(results)
            if args.jacoco_cli and args.jacoco_agent and process:
                dump(args.jacoco_cli,out/'jacoco.exec',args.jacoco_port)
                summary['jacoco_exec']=str(out/'jacoco.exec')
            output_summary(out,summary)
            return 4 if summary['errors'] else (3 if summary['spec_mismatches'] else 0)
        finally:
            if process:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
                log.close()
    if args.command=='compare':
        policy=validate_policy(load_document(args.rules) if args.rules else {})
        if args.cases:
            if not args.a_url or not args.b_url:raise JapiError('--cases requires both --a-url and --b-url')
            cases=load_jsonl(args.cases);headers=parse_headers(args.header)
            a=execute(cases,args.a_url,args.allow_remote,args.allow_mutation,headers,args.timeout,args.max_body_bytes,not args.block_low_confidence)
            b=execute(cases,args.b_url,args.allow_remote,args.allow_mutation,headers,args.timeout,args.max_body_bytes,not args.block_low_confidence)
            save_jsonl(out/'a-results.jsonl',a);save_jsonl(out/'b-results.jsonl',b)
        else:
            if not args.b_results:raise JapiError('--a-results requires --b-results')
            a=load_jsonl(args.a_results);b=load_jsonl(args.b_results)
        diffs=compare(a,b,policy);save_json(out/'diff.json',diffs)
        render_diff(diffs,out/'diff.html')
        output_summary(out,diffs['summary'])
        return 3 if diffs['summary']['different'] or diffs['summary']['inconclusive'] else 0
    if args.command=='explore':
        if args.max_time<1 or args.max_failures<1:raise JapiError('max-time and max-failures must be positive')
        result=explore(args.openapi,args.base_url,args.output,args.allow_remote,args.allow_mutation,args.max_time,args.max_failures)
        output_summary(out,result)
        return 4 if result['exit_code'] else 0
    if args.command=='coverage':
        if args.coverage_action=='dump':
            dump(args.jacoco_cli,args.exec,args.port,args.reset)
            print(compact_summary({'exec':str(Path(args.exec).resolve()),'status':'dumped'}));return 0
        if args.coverage_action=='report':
            xml=report(args.jacoco_cli,args.exec,args.classes,args.sources,args.output)
            data=summarize(xml);save_json(Path(args.output)/'coverage-summary.json',data)
            print(compact_summary({'xml':str(xml),'counters':data['counters']}));return 0
        data=summarize(args.xml);save_json(out/'coverage-summary.json',data)
        print(compact_summary({'coverage':data['counters'],'uncovered':len(data['uncovered_lines'])}));return 0
    if args.command=='enrich':
        catalog=load_document(args.catalog)
        cov=summarize(args.coverage_xml) if args.coverage_xml else None
        data=context_bundle(args.project,catalog,cov,max_sources=args.max_sources)
        save_json(out/'context-bundle.json',data)
        output_summary(out,{'sources':len(data['sources']),'skipped':len(data['skipped']),
                            'status':data['status']})
        return 0
    raise JapiError('Unsupported command')


def main():
    parser=main_parser()
    args=parser.parse_args()
    try:return command(args)
    except (JapiError,OSError,ValueError) as e:
        print(compact_summary({'error':str(e),'stage':args.command}),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
