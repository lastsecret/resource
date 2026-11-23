"""Integration-focused offline tests. No external Maven repositories or services."""
from __future__ import annotations
import base64
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading

import pytest
from japi.cases import generate,quality_summary,validate_case
from japi.common import JapiError
from japi.diff import compare,validate_policy,path_matches
from japi.discover import catalog_from_openapi
from japi.http_run import execute
from japi.inspect import inspect
from japi.static import discover_static
from japi.coverage import summarize

SPEC={
 'openapi':'3.0.3','info':{'title':'Test','version':'1'},
 'paths':{
  '/api/users/{id}':{'get':{'operationId':'getUser','parameters':[
    {'in':'path','name':'id','required':True,'schema':{'type':'integer','example':1}},
    {'in':'query','name':'verbose','schema':{'type':'boolean'}}],
   'responses':{'200':{'description':'ok','content':{'application/json':{'schema':{'$ref':'#/components/schemas/User'}}}}}}},
  '/api/search':{'post':{'requestBody':{'required':True,'content':{'application/json':{'example':{'filters':[],'customerId':None},'schema':{'type':'object'}}}},
    'responses':{'200':{'description':'OK'}}}}
 },'components':{'schemas':{'User':{'type':'object','properties':{'id':{'type':'integer'}}}}}}


def result(cid,obj,status=200):
    b=json.dumps(obj).encode()
    return {'case_id':cid,'endpoint_id':'GET /x','status':status,'headers':{'content-type':'application/json'},
            'body_b64':base64.b64encode(b).decode(),'quality_confidence':'low','quality_warnings':[{'code':'UNVERIFIED_VALUE'}]}


def test_openapi_and_get_default():
    catalog=catalog_from_openapi(SPEC)
    assert len(catalog['endpoints'])==2
    cases=generate(catalog)
    assert len(cases)==1 and cases[0]['request']['path']=='/api/users/1'
    assert cases[0]['request']['body_present'] is False
    assert cases[0]['quality_confidence']=='low' # unknown query data
    assert quality_summary(cases)['low_confidence']==1


def test_null_empty_warning_and_intent():
    c=generate(catalog_from_openapi(SPEC),methods=['POST'])[0]
    assert {'UNINTENDED_NULL','UNINTENDED_EMPTY_ARRAY'} <= {x['code'] for x in c['quality_warnings']}
    c['quality_warnings']=[]
    c['intentional_special_values']=[{'path':'/request/body/filters','value_kind':'empty_array',
     'reason':'edge case','expected_behavior':'no filter'},
     {'path':'/request/body/customerId','value_kind':'null',
     'reason':'edge case','expected_behavior':'reject missing customer'}]
    assert not validate_case(c)['quality_warnings']


def test_semantic_rules_and_multiset():
    a=[result('1',{'name':'ABC','items':[1,1,2]})]
    b=[result('1',{'items':[2,1,1],'name':'abc'})]
    assert compare(a,b)['summary']['different']==1
    policy={'mode':'custom','string_case_sensitive':False,'path_rules':[{'path':'$.items','array_order':'ignore'}]}
    diff=compare(a,b,policy)
    assert diff['summary']['same']==1 and diff['summary']['suppressed_by_policy']==1
    assert diff['summary']['low_confidence']==1
    b=[result('1',{'items':[2,2,1],'name':'abc'})]
    assert compare(a,b,policy)['summary']['different']==1


def test_mode_raw_vs_json():
    a=[result('1',{'a':1,'b':2})]
    b=[{'case_id':'1','endpoint_id':'GET /x','status':200,
        'headers':{'content-type':'application/json'},
        'body_b64':base64.b64encode(b'{"b":2,"a":1}').decode()}]
    assert compare(a,b,{'mode':'raw_exact'})['summary']['different']==1
    assert compare(a,b,{'mode':'json_exact'})['summary']['same']==1
    with pytest.raises(JapiError):validate_policy({'mode':'raw_exact','string_case_sensitive':False})


def test_path_rules_null_missing_and_numeric():
    a=[result('1',{'items':[{'name':'ABC'}],'optional':None,'n':1.001})]
    b=[result('1',{'items':[{'name':'abc'}],'n':1.002})]
    policy={'mode':'custom','null_missing_equal':True,'numeric_tolerance':0.01,
            'path_rules':[{'path':'$.items[*].name','string_case_sensitive':False}]}
    assert path_matches('$.items[*].name','$.items[0].name')
    assert compare(a,b,policy)['summary']['same']==1
    assert compare(a,b)['summary']['different']==1


def test_incomplete_never_passes():
    a=[result('1',{'v':1})]
    b=[{'case_id':'1','error':'connection failed','body_b64':''}]
    assert compare(a,b)['summary']['inconclusive']==1


def test_inspect_static_jdk(tmp_path):
    project=tmp_path/'project';src=project/'src/main/java/demo';src.mkdir(parents=True)
    (project/'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0"><dependencies>
    <dependency><groupId>org.springdoc</groupId><artifactId>springdoc-openapi-starter-webmvc-ui</artifactId></dependency>
    </dependencies></project>''')
    (src/'UserController.java').write_text('''package demo;
    @RestController @RequestMapping("/api/users")
    public class UserController {
       @GetMapping("/{id}")
       public User get(@PathVariable("id") long id, @RequestParam("detail") boolean detail){return null;}
    }
    class User { private String name; private int age; }
    ''')
    info=inspect(project)
    assert info['recommended']=='static-jdk' and info['springdoc_evidence']
    cat=discover_static(project)
    assert len(cat['endpoints'])==1, cat
    ep=cat['endpoints'][0]
    assert ep['id']=='GET /api/users/{id}'
    assert ep['responses']['200']['content']['application/json']['schema']['$ref']=='#/components/schemas/User'
    assert cat['components']['schemas']['User']['properties']['name']=={'type':'string'}


def test_http_replay_and_compare(tmp_path):
    class Server(BaseHTTPRequestHandler):
        variant='a'
        def do_GET(self):
            result={'name':'ABC','items':[1,2]} if type(self).variant=='a' else {'name':'abc','items':[2,1]}
            body=json.dumps(result).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
        def log_message(self,*a):pass
    def start(variant):
        subclass=type('Handler'+variant,(Server,),{'variant':variant})
        s=ThreadingHTTPServer(('127.0.0.1',0),subclass)
        th=threading.Thread(target=s.serve_forever,daemon=True);th.start();return s
    a=start('a');b=start('b')
    try:
        cases=generate(catalog_from_openapi(SPEC))
        url_a=f'http://127.0.0.1:{a.server_port}'
        url_b=f'http://127.0.0.1:{b.server_port}'
        ar=execute(cases,url_a);br=execute(cases,url_b)
        assert ar[0]['status']==200
        assert compare(ar,br)['summary']['different']==1
        policy={'mode':'custom','string_case_sensitive':False,'path_rules':[{'path':'$.items','array_order':'ignore'}]}
        assert compare(ar,br,policy)['summary']['same']==1
        with pytest.raises(JapiError):execute(cases,'https://example.com')
    finally:a.shutdown();b.shutdown();a.server_close();b.server_close()


def test_coverage_xml(tmp_path):
    xml=tmp_path/'jacoco.xml'
    xml.write_text('''<report name="demo"><package name="demo"><sourcefile name="User.java">
      <line nr="12" mi="0" ci="4" mb="1" cb="1"/>
      </sourcefile><counter type="BRANCH" missed="1" covered="1"/></package>
      <counter type="BRANCH" missed="1" covered="1"/><counter type="LINE" missed="0" covered="1"/>
      </report>''')
    summary=summarize(xml)
    assert summary['counters']['BRANCH']['pct']==50.0
    assert summary['uncovered_lines'][0]['line']==12


def test_cli_independent_stages(tmp_path):
    spec=tmp_path/'openapi.json';spec.write_text(json.dumps(SPEC))
    out=tmp_path/'d'
    run=lambda *args:subprocess.run([sys.executable,'-m','japi',*args],capture_output=True,text=True)
    first=run('discover','--mode','openapi-file','--openapi',str(spec),'--output',str(out))
    assert first.returncode==0,first.stderr
    generated=run('generate','--catalog',str(out/'endpoints.json'),'--output',str(tmp_path/'cases'))
    assert generated.returncode==0,generated.stderr
    assert (tmp_path/'cases/cases.jsonl').exists()


def test_revalidate_loaded_case_at_execution():
    c={'case_id':'manually-authored','endpoint_id':'POST /api/search',
       'request':{'method':'POST','path':'/api/search','headers':{},'query':[],
       'body_present':True,'body':{'tags':[],'client':None}},
       'quality_confidence':'medium','quality_warnings':[]}
    out=execute([c],'http://127.0.0.1:1')
    assert out[0]['error']=='blocked: requires --allow-mutation'
    assert out[0]['quality_confidence']=='low'
    assert len(out[0]['quality_warnings'])==2


def test_ignore_path_and_null_empty_comparison():
    a=[result('1',{'traceId':'abc','items':[],'name':'fixed'})]
    b=[result('1',{'traceId':'xyz','items':None,'name':'fixed'})]
    cfg={'mode':'custom','ignore_paths':['$.traceId'],'null_empty_array_equal':True}
    assert compare(a,b,cfg)['summary']['same']==1
    assert compare(a,b)['summary']['different']==1


def test_html_escapes_untrusted_payload(tmp_path):
    from japi.html_report import render_diff
    a=[result('x',{'payload':'<script>alert(1)</script>'})]
    b=[result('x',{'payload':'not equal'})]
    p=tmp_path/'report.html'
    render_diff(compare(a,b),p)
    text=p.read_text()
    assert '&lt;script&gt;' in text
    assert '<script>alert' not in text


def test_fixture_stable_id_and_auth_suppression():
    catalog=catalog_from_openapi(SPEC)
    user=generate(catalog,fixtures={'GET /api/users/{id}:id':101})[0]
    assert user['request']['path']=='/api/users/101'
    assert user['case_id']==generate(catalog,fixtures={'GET /api/users/{id}:id':101})[0]['case_id']
    assert user['quality_confidence']=='low'  # Optional query is inferred, not verified


def test_inspect_ignores_dependency_management_only(tmp_path):
    project=tmp_path/'p';project.mkdir()
    (project/'pom.xml').write_text('''<project><dependencyManagement><dependencies>
      <dependency><groupId>org.springdoc</groupId><artifactId>springdoc-openapi-starter-webmvc-ui</artifactId></dependency>
      </dependencies></dependencyManagement></project>''')
    assert inspect(project)['springdoc_evidence']==[]


def test_invalid_json_with_json_content_type_is_inconclusive():
    a={'case_id':'bad-json','status':200,'headers':{'content-type':'application/json'},'body_b64':base64.b64encode(b'{oops').decode()}
    assert compare([a],[dict(a)])['summary']['inconclusive']==1


def test_cli_full_replay_and_diff(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            payload={'value':'ALPHA' if self.server.server_port%2==0 else 'alpha'}
            b=json.dumps(payload).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
        def log_message(self,*args):pass
    servers=[]
    for _ in range(2):
        s=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        servers.append(s)
        threading.Thread(target=s.serve_forever,daemon=True).start()
    try:
        specs=tmp_path/'contract.json';specs.write_text(json.dumps(SPEC))
        def run(*args):
            return subprocess.run([sys.executable,'-m','japi',*args],capture_output=True,text=True)
        assert run('discover','--mode','openapi-file','--openapi',str(specs),'--output',str(tmp_path/'d')).returncode==0
        assert run('generate','--catalog',str(tmp_path/'d/endpoints.json'),'--output',str(tmp_path/'g')).returncode==0
        result=run('compare','--cases',str(tmp_path/'g/cases.jsonl'),
            '--a-url',f'http://127.0.0.1:{servers[0].server_port}',
            '--b-url',f'http://127.0.0.1:{servers[1].server_port}',
            '--output',str(tmp_path/'ab'))
        assert result.returncode in (0,3),result.stderr
        assert (tmp_path/'ab/diff.json').exists() and (tmp_path/'ab/diff.html').exists()
        assert json.loads((tmp_path/'ab/diff.json').read_text())['summary']['total']==1
    finally:
        for s in servers:s.shutdown();s.server_close()
