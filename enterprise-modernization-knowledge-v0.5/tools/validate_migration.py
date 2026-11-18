#!/usr/bin/env python3
"""Stdlib-only static JDK preflight for Enterprise Modernization Knowledge v0.4.

Not a bytecode scanner, resolved dependency analyzer, Maven executor, or regression tester.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def major_minor(v):
    m = re.match(r'^(\d+)\.(\d+)(?:\.|$)', str(v))
    return f'{m.group(1)}.{m.group(2)}' if m else None

def evaluate(cfg, matrix):
    issues = []
    def add(level, code, detail):
        issues.append({'level':level, 'code':code, 'detail':detail})
    src = cfg.get('source', {})
    target = cfg.get('target', {})
    source_j = src.get('java', {}).get('feature_version')
    requested = target.get('java', {})
    mode = requested.get('mode', 'preserve')
    if isinstance(source_j, bool) or not isinstance(source_j, int) or source_j < 8:
        add('BLOCK','SOURCE_JAVA_UNKNOWN','Must supply an observed source Java feature version >= 8.')
    if mode == 'preserve':
        resolved = source_j
        if requested.get('feature_version') not in (None,source_j):
            add('BLOCK','PRESERVE_TARGET_CONFLICT','Preserve mode cannot specify a different Java target.')
    elif mode == 'explicit':
        resolved = requested.get('feature_version')
        if isinstance(resolved,bool) or not isinstance(resolved,int) or resolved < 8:
            add('BLOCK','TARGET_JAVA_INVALID','Explicit target Java must be a feature version >= 8.')
        if resolved != source_j and not requested.get('change_approved',False):
            add('BLOCK','JAVA_CHANGE_UNAPPROVED','Any change to Java target requires human approval.')
    else:
        resolved = None
        add('BLOCK','TARGET_MODE_INVALID','Target Java mode must be preserve or explicit.')
    tool = cfg.get('toolchain', {})
    if isinstance(resolved,int):
        for k in ['compiler_release','runtime_jdk','ci_jdk','docker_jdk']:
            v = tool.get(k)
            if v is None:
                add('REVIEW',f'{k.upper()}_UNKNOWN',f'No declared {k}; verify from actual project/environment.')
            elif v != resolved:
                add('BLOCK',f'{k.upper()}_MISMATCH',f'{k}={v}, but resolved target Java={resolved}.')
    boot_version = target.get('spring_boot_version')
    if major_minor(boot_version) != '4.0':
        add('REVIEW','KNOWLEDGE_SCOPE_UNVERIFIED',f'Knowledge Pack primarily covers Spring Boot 4.0.x; got {boot_version!r}.')
    comps = cfg.get('components',[])
    if not isinstance(comps, list):
        comps=[]; add('BLOCK','COMPONENTS_INVALID','components must be a list.')
    comps = list(comps)
    comps.append({'id':'spring-boot','version':boot_version})
    seen = set()
    for comp in comps:
        cid,v = comp.get('id'),comp.get('version')
        if cid=='spring-boot' and v!=boot_version:
            add('BLOCK','BOOT_VERSION_CONFLICT',f'Component spring-boot {v} conflicts with target {boot_version}.')
        pair = (cid,v)
        if pair in seen:continue
        seen.add(pair)
        line=major_minor(v)
        found = next((x for x in matrix['components'] if x['id']==cid and x['version_series']==line), None)
        if not found:
            add('REVIEW','UNKNOWN_COMPONENT_VERSION',f'{cid} {v} has no verified matrix entry.')
        elif isinstance(resolved,int) and resolved<found['java_minimum']:
            add('BLOCK','JDK_BELOW_MINIMUM',f'{cid} {v} requires Java >= {found["java_minimum"]}; target={resolved}.')
    if not cfg.get('components'):
        add('REVIEW','DEPENDENCY_GRAPH_UNVERIFIED','No resolved dependency list supplied.')
    status = 'BLOCK' if any(x['level']=='BLOCK' for x in issues) else ('REVIEW_REQUIRED' if issues else 'PRECHECK_PASS')
    return {'schema_version':'0.4','migration_id':cfg.get('migration_id'),'resolved_target_java':resolved,'expected_classfile_major_max':resolved+44 if isinstance(resolved,int) else None,'status':status,'scope':'STATIC_VERSION_ONLY','runtime_and_regression_tests':'NOT_RUN','issues':issues,'notes':['Actual Maven/Gradle dependency graph and CI/Docker configuration must be verified.','PRECHECK_PASS is not proof of successful migration.']}

def main():
    a=argparse.ArgumentParser(description='Evaluate Java target compatibility for one migration config')
    a.add_argument('config',type=pathlib.Path)
    a.add_argument('--matrix',type=pathlib.Path,default=ROOT/'compatibility'/'java-minimums.json')
    ns=a.parse_args()
    result=evaluate(load_json(ns.config),load_json(ns.matrix))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='PRECHECK_PASS' else (2 if result['status']=='REVIEW_REQUIRED' else 3)
if __name__=='__main__':sys.exit(main())
