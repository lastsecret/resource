#!/usr/bin/env python3
"""Plan/merge Maven module exports; optional explicit execution in trusted worktrees."""
import argparse,json,sys,re,shutil,subprocess,os
from pathlib import Path
from module_index import Modules
from inventory import import_tree,build_fingerprint
from safety import output_dir,output_file
PLUGIN='org.apache.maven.plugins:maven-dependency-plugin:3.8.1'

def plan(project,output,profiles=None):
    root=Path(project).resolve(); mods=Modules(root); out=Path(output).resolve(); entries=[]
    if profiles and not re.fullmatch(r"[A-Za-z0-9_.!,+-]{1,200}",profiles):raise ValueError("Invalid profile list")
    for i,m in enumerate(mods.report()):
        d=m['module_dir']; pom=root/d/'pom.xml'; tree=out/f'module-{i:04d}.json'; cp=out/f'module-{i:04d}.classpath'
        args=['mvn','-o','-B','-N','-f',str(pom)]
        if profiles:args+=['-P'+profiles]
        entries.append({**m,'tree_file':tree.name,'classpath_file':cp.name,'tree_command':args+[PLUGIN+':tree','-DoutputType=json','-DoutputFile='+str(tree)],'classpath_command':args+[PLUGIN+':build-classpath','-Dmdep.outputFile='+str(cp)]})
    return {'status':'PLAN_ONLY','source_build_fingerprint':build_fingerprint(root),'profiles':profiles,'modules':entries,'notes':['Review build extensions, plugins, Maven settings and profiles; run only in approved disposable workspace.','-N isolates module exports; reactor-only artifacts may need approved local installation.','POM discovery is not effective reactor/profile resolution. Missing or ambiguous modules remain unresolved.']}

def merge(project,export_dir,manifest,output):
    root=Path(project).resolve(); folder=Path(export_dir).resolve(); mods=Modules(root); known={m['module_dir']:m['module'] for m in mods.report()}; merged=[]; cp={}; used=set(); failures=[]
    for m in manifest['modules']:
        d=m['module_dir']; name=m['tree_file']; cname=m['classpath_file']
        if d in used or Path(name).name!=name or Path(cname).name!=cname or d not in known:raise ValueError('Invalid module manifest')
        used.add(d); p=folder/name
        if p.is_symlink() or not p.is_file() or not known[d]:failures.append(d);continue
        try:
            checked=import_tree(p); obj=json.loads(p.read_text(encoding='utf8'))
            if not isinstance(obj,dict) or checked['module_coordinates']!=[known[d]]:raise ValueError('Module mismatch')
            merged.append(obj)
            f=folder/cname
            if f.is_file() and not f.is_symlink() and f.stat().st_size<2_000_000:cp[d]=f.read_text(encoding='utf8').strip()
        except (ValueError,OSError,UnicodeError):failures.append(d)
    missing=sorted(set(known)-used); stale=manifest.get('source_build_fingerprint')!=build_fingerprint(root)
    if not merged:raise ValueError('No valid module exports')
    # The output is external and new; never overwrite project files.
    out=output_dir(output,root)
    (out/'tree.json').write_text(json.dumps(merged,indent=2)+'\n',encoding='utf8');(out/'classpath.json').write_text(json.dumps(cp,indent=2)+'\n',encoding='utf8')
    report={'status':'IMPORTED_REVIEW_REQUIRED','missing_modules':missing,'failed_modules':failures,'build_fingerprint_changed':stale,'merged_modules':len(merged),'completeness':'UNKNOWN','automatic_patch':False}
    (out/'inventory-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');return report

def capture(project,output,profiles=None,approved=False):
    """Explicitly opt in to actual Maven execution. Offline is not a sandbox."""
    if not approved:raise ValueError('Approved build execution required')
    executable=shutil.which('mvn')
    if not executable:raise ValueError('Maven unavailable')
    if os.name=='nt':raise ValueError('On Windows, use reviewed plan commands and merge manually')
    root=Path(project).resolve(); m=plan(root,output,profiles);out=output_dir(output,root)
    (out/'plan.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
    results=[]
    for entry in m['modules']:
        row={'module_dir':entry['module_dir']}
        for kind in ('tree','classpath'):
            args=entry[kind+'_command'][:];args[0]=executable
            try:
                p=subprocess.run(args,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180,check=False)
                row[kind]={'status':'EXIT_ZERO' if p.returncode==0 else 'FAILED','exit_code':p.returncode}
            except (OSError,subprocess.TimeoutExpired):row[kind]={'status':'FAILED_OR_TIMEOUT'}
            # Failed exports must not accidentally be merged as successful partial files.
            if row[kind]['status']!='EXIT_ZERO':
                f=out/entry[kind+'_file']
                if f.is_file() and not f.is_symlink():f.unlink()
        results.append(row)
    report={'status':'CAPTURE_REVIEW_REQUIRED','modules':results,'build_fingerprint_changed':build_fingerprint(root)!=m['source_build_fingerprint'],'completeness':'UNKNOWN','automatic_patch':False,'note':'Exit codes record this invocation only; verify exact profiles, reactor, and artifact resolution.'}
    (out/'capture-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');return report

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);a=sub.add_parser('plan');a.add_argument('--project',required=True,type=Path);a.add_argument('--output',required=True,type=Path);a.add_argument('--profiles');b=sub.add_parser('merge');b.add_argument('--project',required=True,type=Path);b.add_argument('--exports',required=True,type=Path);b.add_argument('--output',required=True,type=Path);c=sub.add_parser('capture');c.add_argument('--project',required=True,type=Path);c.add_argument('--output',required=True,type=Path);c.add_argument('--profiles');c.add_argument('--execute-approved-build',action='store_true');args=p.parse_args()
    try:
        if args.command=='plan':
            report=plan(args.project,args.output,args.profiles);out=output_dir(args.output,args.project);(out/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print('PLAN_ONLY');return 0
        if args.command=='capture':
            report=capture(args.project,args.output,args.profiles,args.execute_approved_build);print(report['status']);return 2
        report=merge(args.project,args.exports,json.loads((args.exports/'plan.json').read_text()),args.output);print(report['status']);return 2
    except Exception as e:print('INVENTORY_ERROR: '+type(e).__name__,file=sys.stderr);return 3
if __name__=='__main__':sys.exit(main())
