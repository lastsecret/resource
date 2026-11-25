import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from decision_router import route,scoped,digest
from evidence_store import import_results
from benchmark import evaluate
from run_jackson_fixture import run
from agent_batch import prepare
from unittest.mock import patch
class V13(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);self.src=self.p/'src';self.dst=self.p/'dst';self.src.mkdir();self.dst.mkdir();(self.src/'A.java').write_text('class A {}\n');(self.dst/'A.java').write_text('class A {}\n')
 def tearDown(self):self.t.cleanup()
 def report(self,cert=True):
  def side(deps):return {'provenance':'SCANNER_CAPTURED_LOCAL' if cert else 'USER_IMPORTED_UNATTESTED','completeness':'CAPTURED_DISCOVERED_MODULE_SCOPE' if cert else 'UNKNOWN','module_coordinates':['x:a'],'capture_scope':{'module_count':1},'dependencies':deps}
  return {'inventory':{'source':side([]),'target':side([])},'preflight':{'status':'REVIEW_REQUIRED','resolved_target_java':17,'issues':[{'code':'DEPENDENCY_GRAPH_UNVERIFIED','level':'REVIEW'},{'code':'BOOT41_DEPENDENCY_GRAPH_UNVERIFIED','level':'REVIEW'},{'code':'KEEP_THIS','level':'REVIEW'}]},'evaluations':[],'route':{},'legacy':None}
 def rec(self,rid,status='DETECTED',app='IMPORTED_PAIR_MATCH'):
  return {'rule_id':rid,'status':status,'applicability':app,'locations':['A.java:1'],'location_evidence':[{'location':'A.java:1','module':'x:a'}],'required_evidence':['RUNTIME_BASELINE'],'matched_component_modules':['x:a']}
 def q(self,rid='JCK3-NULL-PRIMITIVES-001'):
  r=self.report();r['evaluations']=[self.rec(rid)];return route(r,self.src,self.dst)
 def response(self,q,decision='CHANGE_CANDIDATE',fix='FIX-01'):
  return {'schema_version':'0.13','run_id':q['run_id'],'results':[{'task_id':q['tasks'][0]['task_id'],'decision':decision,'evidence_refs':[{'side':'source','path':'A.java','line':1}],'missing_evidence':[],'verification_status':'NOT_RUN','proposed_fix_id':fix}]}
 def test_sync_keeps_blockers_and_scope(self):
  r=self.report();r['preflight']['issues'].append({'code':'NO_GO','level':'BLOCK'});q=route(r);codes={x['code'] for x in r['preflight']['issues']};self.assertNotIn('DEPENDENCY_GRAPH_UNVERIFIED',codes);self.assertIn('EFFECTIVE_REACTOR_PROFILE_SCOPE_UNVERIFIED',codes);self.assertIn('KEEP_THIS',codes);self.assertEqual(r['preflight']['status'],'BLOCK');self.assertTrue(q['scope_attested'])
 def test_imported_no_exclusion(self):
  r=self.report(False);r['evaluations']=[self.rec('HCP7-SCHEMA-001','NOT_APPLICABLE','CAPTURED_SCOPE_NOT_APPLICABLE')];q=route(r);self.assertEqual(q['decisions'][0]['route'],'EVIDENCE');self.assertIn('DEPENDENCY_GRAPH_UNVERIFIED',{x['code'] for x in r['preflight']['issues']})
 def test_attested_exclusion(self):
  r=self.report();r['evaluations']=[self.rec('HCP7-SCHEMA-001','NOT_APPLICABLE','CAPTURED_SCOPE_NOT_APPLICABLE')];q=route(r);self.assertEqual(q['decisions'][0]['decision'],'NOT_APPLICABLE');self.assertFalse(q['tasks'])
 def test_inactive_jooq(self):
  r=self.report();r['evaluations']=[self.rec('SB41-JOOQ-JDK-008')];q=route(r);self.assertEqual(q['decisions'][0]['decision'],'NOT_APPLICABLE');self.assertFalse(r['findings']);self.assertFalse(r['evaluations'][0]['locations'])
 def test_jooq_active(self):
  r=self.report();r['inventory']['target']['dependencies']=[{'ga':'org.jooq:jooq','version':'3.21.9','scope':'compile','module':'x:a'}];r['evaluations']=[self.rec('SB41-JOOQ-JDK-008')];q=route(r);self.assertEqual(q['decisions'][0]['decision'],'BLOCK');self.assertFalse(q['tasks'])
 def test_negative_search_not_no_change(self):
  r=self.report();r['evaluations']=[self.rec('JCK3-NULL-PRIMITIVES-001','NOT_DETECTED')];q=route(r);self.assertEqual(q['decisions'][0]['route'],'EVIDENCE');self.assertEqual(q['decisions'][0]['decision'],'REVIEW_REQUIRED')
 def test_runtime_validation_only(self):self.assertEqual(self.q('HCP7-LOAD-006')['tasks'][0]['route'],'RUNTIME')
 def test_provenance_agent(self):self.assertEqual(self.q('JCK3-MAPPER-TOPOLOGY-003')['tasks'][0]['route'],'AGENT')
 def test_ledger_append_and_no_approval(self):
  q=self.q();a=self.response(q);r=import_results(q,a,self.src,self.dst);self.assertEqual(r['proposals'][0]['state'],'PENDING_HUMAN_AND_EVIDENCE_REVIEW');self.assertFalse(r['proposals'][0]['automatic_patch']);self.assertFalse(r['remaining_tasks']);self.assertIn('sha256',r['proposals'][0]['evidence_refs'][0]);self.assertRaises(ValueError,import_results,q,a,self.src,self.dst,r)
 def test_stale_source(self):
  q=self.q();(self.src/'A.java').write_text('class B {}\n');self.assertRaises(ValueError,import_results,q,self.response(q),self.src,self.dst)
 def test_validation_only_reject_patch(self):
  q=self.q('HCP7-LOAD-006');self.assertRaises(ValueError,import_results,q,self.response(q),self.src,self.dst)
 def test_fake_result_and_escape(self):
  q=self.q();a=self.response(q);a['results'][0]['decision']='NO_CHANGE_CONFIRMED';self.assertRaises(ValueError,import_results,q,a,self.src,self.dst);a=self.response(q);a['results'][0]['evidence_refs'][0]['path']='../outside';self.assertRaises(ValueError,import_results,q,a,self.src,self.dst)
 def test_queue_accidental_tamper(self):
  q=self.q();a=self.response(q);q['tasks'][0]['classification']='REGRESSION';self.assertRaises(ValueError,import_results,q,a,self.src,self.dst)
 def test_benchmark_missing_metrics_and_unadjudicated(self):
  c=dict(source_snapshot='x',target_version='4.1.3',java_target='17',model='m',prompt_revision='p',runtime_test_revision='r');runs=[dict(arm=a,run_id='1',conditions=c,proposed_change_ids=['yes','unknown']) for a in 'ABC'];o={'required_change_ids':['yes'],'non_change_ids':['no']};r=evaluate(o,{'runs':runs});self.assertIsNone(r['arms']['A']['details'][0]['precision']);self.assertIsNone(r['arms']['A']['metrics']['input_tokens']['median']);self.assertEqual(r['status'],'INSUFFICIENT_BALANCED_REPETITIONS');runs[1]['conditions']={**c,'model':'different'};self.assertRaises(ValueError,evaluate,o,{'runs':runs})
 def test_batch_excludes_already_submitted_but_not_resolved(self):
  q=self.q();b=prepare(q,self.src,self.dst);self.assertEqual(len(b['tasks']),1);self.assertEqual(b['response_template']['results'][0]['decision'],'REVIEW_REQUIRED');r=import_results(q,self.response(q),self.src,self.dst);self.assertEqual(len(r['unresolved_task_ids']),1);self.assertFalse(prepare(q,self.src,self.dst,r)['tasks'])
 def test_transitive_jooq_no_declaration_still_blocks(self):
  r=self.report();r['inventory']['target']['dependencies']=[{'ga':'org.jooq:jooq','version':'3.21.9','scope':'compile','module':'x:a'}];rec=self.rec('SB41-JOOQ-JDK-008','NOT_DETECTED');rec.update(locations=[],location_evidence=[],matched_component_modules=[]);r['evaluations']=[rec];q=route(r);self.assertEqual(q['decisions'][0]['decision'],'BLOCK')
 def test_candidate_with_unknown_version_routes_to_evidence(self):
  r=self.report(False);r['evaluations']=[self.rec('JCK3-NULL-PRIMITIVES-001','DETECTED','UNKNOWN_COMPONENT_PAIR')];q=route(r);self.assertEqual(q['tasks'][0]['route'],'EVIDENCE')
 def test_no_maven_runtime_explicit_block(self):
  self.assertRaises(ValueError,run,self.p/'a',False)
  with patch('run_jackson_fixture.shutil.which',return_value=None):r=run(self.p/'b',True)
  self.assertEqual(r['runtime_verification'],'NOT_RUN');self.assertEqual(r['reason'],'MAVEN_UNAVAILABLE')
if __name__=='__main__':unittest.main()
