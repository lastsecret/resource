#!/usr/bin/env python3
"""Stdlib-only static JDK preflight for Enterprise Modernization Knowledge v0.8.

Not a bytecode scanner, resolved dependency analyzer, Maven executor, or regression tester.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
from version_router import route
from config_contract import errors

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
    invalid=errors(cfg)
    if invalid:return {'schema_version':'0.9','status':'BLOCK','resolved_target_java':None,'issues':[{'level':'BLOCK','code':'CONFIG_SCHEMA_INVALID','detail':x} for x in invalid],'runtime_and_regression_tests':'NOT_RUN'}
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
            elif (v < resolved if k=='ci_jdk' else v != resolved):
                add('BLOCK',f'{k.upper()}_MISMATCH',f'{k}={v}, but resolved target Java={resolved}.')
    boot_version = target.get('spring_boot_version')
    selected_route = route(src.get('spring_boot_version'), boot_version)
    if selected_route['status'] != 'CANDIDATES_SELECTED':
        add('REVIEW' if selected_route['status']=='REVIEW_REQUIRED' else 'BLOCK','KNOWLEDGE_SCOPE_UNVERIFIED',f'Unsupported or unsafe Spring Boot version route: {src.get("spring_boot_version")} -> {boot_version}')
    if selected_route.get('issues') and selected_route['status']=='CANDIDATES_SELECTED':
        add('REVIEW','PATCH_KNOWLEDGE_INCOMPLETE','Patch-only delta not verified.')
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
    add('REVIEW','DEPENDENCY_GRAPH_UNVERIFIED','Declared component input is not independently collected dependency evidence. No static config alone may pass.')
    if 'spring-boot-4.0-to-4.1' in selected_route['stages']:
        add('REVIEW','BOOT41_DEPENDENCY_GRAPH_UNVERIFIED','Boot 4.1 may manage jOOQ OSS requiring Java 21; resolve the dependency graph and confirm jOOQ absence/edition.')
    status = 'BLOCK' if any(x['level']=='BLOCK' for x in issues) else ('REVIEW_REQUIRED' if issues else 'PRECHECK_PASS')
    return {'schema_version':'0.9','version_stages':selected_route['stages'],'selected_rule_count':len(selected_route['rule_ids']),'migration_id':cfg.get('migration_id'),'resolved_target_java':resolved,'expected_classfile_major_max':resolved+44 if isinstance(resolved,int) else None,'status':status,'scope':'STATIC_VERSION_ONLY','runtime_and_regression_tests':'NOT_RUN','issues':issues,'notes':['Actual Maven/Gradle dependency graph and CI/Docker configuration must be verified.','PRECHECK_PASS is not proof of successful migration.']}

def main():
    a=argparse.ArgumentParser(description='Evaluate Java target compatibility for one migration config')
    a.add_argument('config',type=pathlib.Path)
    a.add_argument('--matrix',type=pathlib.Path,default=ROOT/'compatibility'/'java-minimums.json')
    ns=a.parse_args()
    result=evaluate(load_json(ns.config),load_json(ns.matrix))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='PRECHECK_PASS' else (2 if result['status']=='REVIEW_REQUIRED' else 3)
if __name__=='__main__':sys.exit(main())
