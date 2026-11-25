"""Local Maven module identity; declaration only, not effective POM resolution."""
import re, xml.etree.ElementTree as ET
from pathlib import Path
from safety import files, SAFE_NAME

def pom_root(path):
    raw=path.read_bytes()
    # Reject DTD even with UTF-16 null bytes; only UTF-8 supported.
    text=raw.decode('utf-8-sig')
    if re.search(r'<!\s*(DOCTYPE|ENTITY)',text,re.I):raise ValueError('DTD disabled')
    root=ET.fromstring(text)
    for el in root.iter():el.tag=el.tag.split('}')[-1]
    return root

def coord(root):
    g=root.findtext('groupId') or root.findtext('parent/groupId') or ''
    a=root.findtext('artifactId') or ''
    return g+':'+a if all(SAFE_NAME.fullmatch(x) for x in (g,a)) else None

class Modules:
    def __init__(self,root,paths=None):
        self.root=Path(root).resolve(); self.by_dir={}; self.by_ga={}; self.errors=0
        for p in paths if paths is not None else files(self.root):
            if p.name!='pom.xml':continue
            try:ga=coord(pom_root(p))
            except (OSError,UnicodeError,ValueError,ET.ParseError):ga=None;self.errors+=1
            d=p.parent; self.by_dir[d]=ga
            if ga:self.by_ga.setdefault(ga,[]).append(d)
    def bind(self,path):
        p=Path(path)
        if not p.is_absolute():p=self.root/p
        for d in (p.parent,*p.parent.parents):
            if d in self.by_dir:
                ga=self.by_dir[d]
                return {'module':ga if ga and len(self.by_ga[ga])==1 else None,'module_dir':d.relative_to(self.root).as_posix(),'binding':'DECLARED_POM_COORDINATE' if ga and len(self.by_ga[ga])==1 else 'UNRESOLVED_OR_AMBIGUOUS'}
            if d==self.root:break
        return {'module':None,'module_dir':None,'binding':'UNRESOLVED_OR_AMBIGUOUS'}
    def report(self):
        return [{'module_dir':d.relative_to(self.root).as_posix(),'module':ga if ga and len(self.by_ga[ga])==1 else None,'binding':'DECLARED_POM_COORDINATE' if ga and len(self.by_ga[ga])==1 else 'UNRESOLVED_OR_AMBIGUOUS'} for d,ga in sorted(self.by_dir.items())]
