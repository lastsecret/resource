"""Read-only, offline project capability detection; does not execute Maven or Gradle."""
from __future__ import annotations
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from .common import JapiError

SKIP = {'.git','target','build','node_modules','.gradle','.idea','.venv','dist','vendor'}
SPEC = {'openapi.json','openapi.yaml','openapi.yml','swagger.json','swagger.yaml','swagger.yml'}


def project_files(project):
    root = Path(project).resolve()
    if not root.is_dir():
        raise JapiError(f'Not a project directory: {root}')
    for base, dirs, files in __import__('os').walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith('.'))
        for name in sorted(files):
            p = Path(base, name)
            yield p, p.relative_to(root).as_posix()


def pom_data(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    found = {'springdoc':False,'springfox':False,'swagger_annotations':False,'boot':None,'dependencies':[]}
    try:
        root = ET.fromstring(text)
        ns = {'m':'http://maven.apache.org/POM/4.0.0'} if root.tag.startswith('{') else {}
        def find(element, tag):
            return element.findtext(f'm:{tag}' if ns else tag, namespaces=ns)
        def elements(element, tag):
            return element.findall(f'.//m:{tag}' if ns else f'.//{tag}', ns)
        parent = next(iter(elements(root, 'parent')), None)
        found['boot'] = find(parent, 'version') if parent is not None and find(parent,'artifactId') == 'spring-boot-starter-parent' else None
        dependencies = root.find('m:dependencies' if ns else 'dependencies', ns)
        for dependency in (dependencies.findall('m:dependency' if ns else 'dependency', ns) if dependencies is not None else []):
            artifact = find(dependency, 'artifactId') or ''
            group = find(dependency, 'groupId') or ''
            found['dependencies'].append(f'{group}:{artifact}')
            if group == 'org.springdoc' and 'springdoc-' in artifact: found['springdoc'] = True
            if 'springfox' in artifact: found['springfox'] = True
            if group == 'io.swagger.core.v3': found['swagger_annotations'] = True
            if group == 'org.springframework.boot' and artifact.startswith('spring-boot'):
                found['boot'] = found['boot'] or 'detected (version unresolved)'
    except ET.ParseError:
        found['parse_error'] = 'Malformed XML'
    return found


def inspect(project):
    root = Path(project).resolve()
    out = {'project':str(root),'build_systems':[],'spring_boot':[],'openapi_files':[], 'springdoc_evidence':[], 'swagger_evidence':[], 'spring_controllers':[], 'jax_rs':[], 'gradle_files':[], 'diagnostics':[], 'candidates':[]}
    if not root.is_dir(): raise JapiError(f'Project path is not a directory: {root}')
    for path, rel in project_files(root):
        name = path.name
        if name == 'pom.xml':
            if 'maven' not in out['build_systems']: out['build_systems'].append('maven')
            info = pom_data(path)
            if info.get('boot'): out['spring_boot'].append({'file':rel,'version':info['boot']})
            if info['springdoc']: out['springdoc_evidence'].append({'file':rel,'kind':'maven-dependency'})
            if info['springfox'] or info['swagger_annotations']: out['swagger_evidence'].append({'file':rel,'kind':'maven-dependency'})
            if info.get('parse_error'): out['diagnostics'].append(f'{rel}: {info["parse_error"]}')
        if name in ('build.gradle','build.gradle.kts'):
            if 'gradle' not in out['build_systems']: out['build_systems'].append('gradle')
            out['gradle_files'].append(rel)
            text = path.read_text(encoding='utf-8',errors='replace')
            if 'org.springdoc' in text: out['springdoc_evidence'].append({'file':rel,'kind':'gradle-text-match'})
            if 'springfox' in text or 'io.swagger' in text: out['swagger_evidence'].append({'file':rel,'kind':'gradle-text-match'})
            if 'org.springframework.boot' in text: out['spring_boot'].append({'file':rel,'version':'unresolved'})
        if name.lower() in SPEC or (name.lower().endswith(('.yaml','.yml','.json')) and '/openapi/' in f'/{rel.lower()}'):
            out['openapi_files'].append(rel)
        if path.suffix == '.java':
            text = path.read_text(encoding='utf-8',errors='replace')
            if re.search(r'@(?:RestController|Controller|GetMapping|PostMapping|RequestMapping)\b',text): out['spring_controllers'].append(rel)
            if re.search(r'@(?:Path|GET|POST)\b',text) and ('jakarta.ws.rs' in text or 'javax.ws.rs' in text): out['jax_rs'].append(rel)
    def add(name, ready, desc, needs_app=False):
        out['candidates'].append({'method':name,'available':bool(ready),'requires_app_start':needs_app,'static':not needs_app,'description':desc})
    add('openapi-file',out['openapi_files'],'Use existing contract, may be stale')
    add('static-jdk',out['spring_controllers'],'Offline JDK compiler AST; type resolution may be incomplete')
    add('springdoc-runtime',out['springdoc_evidence'],'Springdoc dependency found; reachability not verified',True)
    out['recommended'] = 'openapi-file' if out['openapi_files'] else 'static-jdk' if out['spring_controllers'] else None
    out['selection_required'] = True
    return out
