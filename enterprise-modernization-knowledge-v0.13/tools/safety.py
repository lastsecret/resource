"""Bounded local, read-only discovery. No external processes or network."""
import os,re,stat
from pathlib import Path
SKIP={'.git','target','build','node_modules','.gradle','.idea','.mvn','dist','out','.next','.svn','__pycache__'}
MAX_BYTES=1_500_000

def linked(p):
    s=p.lstat()
    return stat.S_ISLNK(s.st_mode) or bool(getattr(s,'st_file_attributes',0)&0x400)

def files(root,counts=None):
    root=Path(root).resolve(strict=True)
    counts=counts if counts is not None else {}
    def bump(k):counts[k]=counts.get(k,0)+1
    for base,dirs,names in os.walk(root,followlinks=False,onerror=lambda _:bump('unreadable')):
        b=Path(base)
        for n in list(dirs):
            try:
                p=b/n
                if linked(p) or not p.resolve().is_relative_to(root):dirs.remove(n);bump('links_skipped')
                elif n in SKIP:dirs.remove(n);bump('excluded_dirs')
            except OSError:dirs.remove(n);bump('unreadable')
        for n in names:
            p=b/n
            try:
                if linked(p) or not p.resolve().is_relative_to(root):bump('links_skipped');continue
                s=p.lstat()
                if not stat.S_ISREG(s.st_mode) or s.st_nlink>1 or s.st_size>MAX_BYTES:bump('size_or_special_skipped');continue
                bump('files_considered');yield p
            except OSError:bump('unreadable')

def output_dir(path,project):
    p=Path(path).absolute(); root=Path(project).resolve()
    # No output in project, no reuse, no existing symlink ancestors.
    for x in [p,*p.parents]:
        if x.exists() or x.is_symlink():
            if linked(x):raise ValueError('Output path uses a link')
    if p.resolve().is_relative_to(root):raise ValueError('Output must be outside project')
    p.mkdir(parents=True,exist_ok=False);return p

def output_file(path,project,text):
    p=Path(path).absolute()
    if p.resolve().is_relative_to(Path(project).resolve()):raise ValueError('Output must be outside project')
    for x in [p,*p.parents]:
        if (x.exists() or x.is_symlink()) and linked(x):raise ValueError('Output path uses a link')
    with p.open('x',encoding='utf8') as f:f.write(text)

# Do not export arbitrary configuration values. Only explicitly typed safe values.
SAFE_KEYS={'server.undertow.accesslog.enabled','server.undertow.accesslog.rotate','server.tomcat.accesslog.enabled','server.tomcat.accesslog.rotate','server.undertow.threads.worker','server.undertow.threads.io','server.tomcat.threads.max','server.tomcat.threads.min-spare','server.undertow.no-request-timeout','server.tomcat.keep-alive-timeout','server.undertow.max-http-post-size','server.tomcat.max-http-form-post-size','server.undertow.max-parameters','server.tomcat.max-parameter-count','server.port','spring.jackson.deserialization.fail-on-null-for-primitives','spring.jackson.mapper.sort-properties-alphabetically','spring.jackson.use-jackson2-defaults','spring.jackson2.deserialization.fail-on-null-for-primitives','spring.jackson2.mapper.sort-properties-alphabetically','spring.data.jpa.repositories.bootstrap-mode'}
SAFE_NAME=re.compile(r'^[A-Za-z0-9_.-]{1,180}$')
def config_value(k,v):
    if k in SAFE_KEYS and re.fullmatch(r'(?:true|false|[+-]?\d{1,12}(?:ms|s|m|h|KB|MB|GB|B)?|default|deferred|lazy)',v,re.I):return v
    # Plain placeholder contains no fallback value; leave symbolic only.
    if k=='server.undertow.accesslog.dir' and re.fullmatch(r'\$\{[A-Z_][A-Z0-9_]{0,63}\}',v):return v
    return '[REDACTED]'
