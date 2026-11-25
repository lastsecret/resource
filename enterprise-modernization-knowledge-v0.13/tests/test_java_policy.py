import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from validate_migration import evaluate

def load(name):
    return json.loads((ROOT/'examples'/name).read_text())

MATRIX = json.loads((ROOT/'compatibility'/'java-minimums.json').read_text())

class JavaVersionPolicyTests(unittest.TestCase):
    def test_java17_preserved(self):
        r=evaluate(load('java17-preserve.json'),MATRIX)
        self.assertEqual((r['status'],r['resolved_target_java'],r['expected_classfile_major_max']),('REVIEW_REQUIRED',17,61))
    def test_java21_preserved(self):
        r=evaluate(load('java21-preserve.json'),MATRIX)
        self.assertEqual((r['status'],r['resolved_target_java'],r['expected_classfile_major_max']),('REVIEW_REQUIRED',21,65))
    def test_java11_preserved_blocked(self):
        r=evaluate(load('java11-incompatible.json'),MATRIX)
        self.assertEqual(r['status'],'BLOCK')
        self.assertIn('JDK_BELOW_MINIMUM',[x['code'] for x in r['issues']])
    def test_17_to_21_requires_approval(self):
        r=evaluate(load('java17-to21-unapproved.json'),MATRIX)
        self.assertIn('JAVA_CHANGE_UNAPPROVED',[x['code'] for x in r['issues']])
    def test_17_to_21_approved_precheck_only(self):
        r=evaluate(load('java17-to21-approved.json'),MATRIX)
        self.assertEqual(r['status'],'REVIEW_REQUIRED')
        self.assertEqual(r['runtime_and_regression_tests'],'NOT_RUN')
    def test_tool_jdk_is_not_target_jdk(self):
        c=load('java17-preserve.json')
        self.assertEqual(c['toolchain']['migration_tool_jdk'],21)
        self.assertEqual(evaluate(c,MATRIX)['status'],'REVIEW_REQUIRED')
    def test_compiler_mismatch_is_blocked(self):
        c=load('java17-preserve.json');c['toolchain']['compiler_release']=21
        self.assertIn('COMPILER_RELEASE_MISMATCH',[x['code'] for x in evaluate(c,MATRIX)['issues']])
    def test_unknown_component_requires_review(self):
        c=load('java17-preserve.json');c['components'].append({'id':'internal-starter','version':'1.2.3'})
        self.assertEqual(evaluate(c,MATRIX)['status'],'REVIEW_REQUIRED')
    def test_boot_41_requires_resolved_graph_review(self):
        c=load('java17-preserve.json');c['target']['spring_boot_version']='4.1.2'
        c['components'][0]['version']='4.1.2'
        r=evaluate(c,MATRIX)
        self.assertEqual(r['status'],'REVIEW_REQUIRED')
        self.assertIn('BOOT41_DEPENDENCY_GRAPH_UNVERIFIED',[x['code'] for x in r['issues']])
    def test_target_preserve_cannot_conflict(self):
        c=load('java17-preserve.json');c['target']['java']['feature_version']=21
        self.assertIn('PRESERVE_TARGET_CONFLICT',[x['code'] for x in evaluate(c,MATRIX)['issues']])
    def test_runtime_mismatch_is_blocked(self):
        c=load('java17-preserve.json');c['toolchain']['runtime_jdk']=21
        self.assertIn('RUNTIME_JDK_MISMATCH',[x['code'] for x in evaluate(c,MATRIX)['issues']])
    def test_no_dependency_graph_requires_review(self):
        c=load('java17-preserve.json');c['components']=[]
        self.assertEqual(evaluate(c,MATRIX)['status'],'REVIEW_REQUIRED')
if __name__=='__main__':unittest.main()
