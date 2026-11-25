#!/usr/bin/env python3
"""Read-only 4.0->4.1 release-note candidate scanner; not an AST/Gradle/Maven resolver.
Use rule location hints only as prompts for a baseline/target comparison.
"""
import argparse,json,re
from pathlib import Path
from version_router import route
from safety import files,output_file
ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','target','build','node_modules','.gradle','.idea','.next','dist'}
SUFFIXES={'.java','.xml','.properties','.yaml','.yml','.gradle','.kts','.sh','.ps1','.bat','.cmd','.dockerfile'}
SPECIAL={'Dockerfile','Makefile','Jenkinsfile'}

def scan(project,source,target):
    project=Path(project).resolve()
    if not project.is_dir():raise ValueError('Project directory does not exist')
    routing=route(source,target)
    rules=json.loads((ROOT/'deltas'/'spring-boot-4.0-to-4.1.json').read_text(encoding='utf8'))['rules']
    selected=set(routing['rule_ids'])
    candidates=[]
    if routing['status']!='CANDIDATES_SELECTED':
        return {'schema_version':'0.8','route':routing,'findings':[],'limitations':['Unsupported route. No inference.']}
    if not selected.intersection({r['id'] for r in rules}):
        return {'schema_version':'0.8','route':routing,'findings':[],'limitations':['No 4.0->4.1 delta selected.']}
    patterns=[(r,re.compile(r['trigger']['static_regex'],re.I)) for r in rules if r['id'] in selected and r['trigger']['static_regex']]
    counts={}
    for file in files(project,counts):
        if file.suffix.lower() not in SUFFIXES and file.name not in SPECIAL and not file.name.lower().startswith(("dockerfile.","jenkinsfile.","makefile.")):continue
        if file.stat().st_size>1_500_000:continue
        try:lines=file.read_text(encoding='utf8').splitlines()
        except (UnicodeError,OSError):counts['unreadable']=counts.get('unreadable',0)+1;continue
        for i,line in enumerate(lines,1):
            if not line.strip() or line.lstrip().startswith(('#','//','*')): continue
            for r,p in patterns:
                if p.search(line):
                    candidates.append({'rule_id':r['id'],'classification':r['classification'], 'location':f'{file.relative_to(project)}:{i}',
                        'confidence':'TEXT_CANDIDATE_ONLY','decision':'REVIEW_REQUIRED',
                        'effective_configuration':'UNKNOWN','source_behavior':'NOT_MEASURED','target_behavior':'NOT_MEASURED','automatic_patch':False})
    return {'schema_version':'0.8','route':routing,'project':str(project),'scanner_scope':'STATIC_TEXT_ONLY',
      'findings':candidates,'scan_counts':counts,'unresolved_rules':[r['id'] for r in rules if r['id'] in selected and r['trigger']['static_regex'] is None],
      'limitations':['No Maven/Gradle resolved dependency graph; Java/Jackson handler origins and JPA runtime bean availability are unverified.','A text match never proves a breaking change or need to patch.','No match is NOT proof that an API or behavior is compatible.','Does not change project files.']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--config',type=Path,required=True);ap.add_argument('--output',type=Path)
    a=ap.parse_args(); cfg=json.loads(a.config.read_text(encoding='utf8'))
    r=scan(a.project,cfg.get('source',{}).get('spring_boot_version'),cfg.get('target',{}).get('spring_boot_version'))
    out=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.output:output_file(a.output,a.project,out)
    print(out,end='')
    return 0 if r['route']['status']=='CANDIDATES_SELECTED' else 2
if __name__=='__main__':raise SystemExit(main())
