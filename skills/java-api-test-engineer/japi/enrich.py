"""Bounded context pack generation for an *external*, opt-in coding agent."""
from __future__ import annotations
from pathlib import Path
from .common import JapiError


def context_bundle(project,catalog,coverage=None,max_sources=12,context_lines=12):
    root=Path(project).resolve();coverage=coverage or {}
    selected=[];seen=set()
    for ep in catalog.get('endpoints',[]):
        source=str(ep.get('source','')).split(':',1)[0]
        if source.endswith('.java') and source not in seen:seen.add(source);selected.append(source)
    for line in coverage.get('uncovered_lines',[]):
        file=line.get('source',''); name=file.rsplit('/',1)[-1]
        for match in root.rglob(name):
            if match.is_file():
                rel=match.relative_to(root).as_posix()
                if rel not in seen:seen.add(rel);selected.append(rel)
                break
    segments=[];skipped=[]
    for name in selected:
        if len(segments)>=max_sources:skipped.append(name);continue
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():skipped.append(name);continue
        lines=path.read_text(encoding='utf-8',errors='replace').splitlines()
        target=[row['line'] for row in coverage.get('uncovered_lines',[]) if name.endswith(row.get('source',''))]
        if target:
            selected_line_nums=set()
            for n in target[:20]:selected_line_nums.update(range(max(1,n-context_lines),min(len(lines),n+context_lines)+1))
        else:selected_line_nums=set(range(1,min(len(lines),min(120,context_lines*8))+1))
        excerpt='\n'.join(f'{i}: {lines[i-1]}' for i in sorted(selected_line_nums))
        segments.append({'source':name,'excerpt':excerpt[:16000],
                         'uncovered_lines':target[:20]})
    return {'purpose':'Propose branch-targeted request cases; DO NOT execute automatically',
      'endpoints':[{'id':x['id'],'source':x.get('source')} for x in catalog.get('endpoints',[])],
      'sources':segments,'skipped':skipped,
      'requirements':['Return candidate requests with source location, preconditions, intended branches and confidence.',
                      'Avoid invented fixture IDs. Ask for known data where required.',
                      'Do not create default null/empty arrays in normal cases.'],
      'status':'awaiting_external_agent'}
