"""Deterministic HTTP replay with bounded response capture and no redirect following."""
from __future__ import annotations
import base64
from copy import deepcopy
from .cases import validate_case
import hashlib
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPHandler, HTTPSHandler, ProxyHandler, HTTPRedirectHandler
from .common import JapiError, normalize_url

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

OPENER = build_opener(ProxyHandler({}), HTTPHandler(), HTTPSHandler(), NoRedirect())
SENSITIVE={'authorization','proxy-authorization','cookie','set-cookie','x-api-key'}


def parse_headers(headers):
    out={}
    for assignment in headers or []:
        if '=' not in assignment:raise JapiError('Header must use NAME=value or NAME=env:VAR')
        name,value=assignment.split('=',1)
        if not name or any(x in name for x in '\r\n:'):
            raise JapiError('Invalid header name')
        if value.startswith('env:'):
            env=value[4:]
            if env not in os.environ:raise JapiError(f'Missing environment variable: {env}')
            value=os.environ[env]
        if '\r' in value or '\n' in value:raise JapiError('Newlines are prohibited in header values')
        out[name]=value
    return out


def redact_headers(headers):
    return {k:('[REDACTED]' if k.lower() in SENSITIVE else v) for k,v in headers.items()}


def request_one(case, base_url, extra_headers=None, timeout=10, max_bytes=2_000_000):
    req=case.get('request',{})
    method=req.get('method','GET').upper()
    path=req.get('path','/')
    if not isinstance(path,str) or not path.startswith('/') or path.startswith('//') or '..' in path.split('/'):
        raise JapiError(f'Unsafe request path in {case.get("case_id")}: {path}')
    query=[]
    for item in req.get('query',[]):
        v=item.get('value','')
        if isinstance(v,list):query.extend((item['name'],x) for x in v)
        else:query.append((item['name'],v))
    url=base_url.rstrip('/')+path
    if query:url+=('?' if '?' not in url else '&')+urlencode(query,doseq=True)
    headers={**req.get('headers',{}),**(extra_headers or {})}
    payload=None
    if req.get('body_present',False):
        payload=json.dumps(req.get('body'),ensure_ascii=False,separators=(',',':')).encode('utf-8')
        headers.setdefault('Content-Type','application/json')
    request=Request(url,data=payload,headers=headers,method=method)
    start=time.perf_counter()
    result={'case_id':case.get('case_id'),'endpoint_id':case.get('endpoint_id'),
        'request_method':method,'request_path':path,'quality_confidence':case.get('quality_confidence','unknown'),
        'quality_warnings':case.get('quality_warnings',[]),'expected_status':case.get('expected_status')}
    try:
        try:
            response=OPENER.open(request,timeout=timeout)
        except HTTPError as e:
            response=e
        with response:
            body=response.read(max_bytes+1)
            truncated=len(body)>max_bytes
            if truncated:body=body[:max_bytes]
            status=response.status if hasattr(response,'status') else response.code
            result.update(status=status,headers={'content-type':response.headers.get('Content-Type','')},
                body_b64=base64.b64encode(body).decode('ascii'), body_sha256=hashlib.sha256(body).hexdigest(),
                body_truncated=truncated,response_size_captured=len(body),
                status_matches_spec=status in case['expected_status'] if case.get('expected_status') else None,
                error='response_body_exceeds_limit' if truncated else None)
    except (URLError, TimeoutError, ConnectionError, OSError) as e:
        result.update(status=None,headers={},body_b64='',body_sha256=None,body_truncated=False,
                      response_size_captured=0,status_matches_spec=None,error=str(e)[:500])
    result['elapsed_ms']=round((time.perf_counter()-start)*1000,2)
    return result


def execute(cases,base_url,allow_remote=False,allow_mutation=False,headers=None,timeout=10,max_bytes=2_000_000,allow_low=True):
    base=normalize_url(base_url,allow_remote=allow_remote)
    if timeout<=0 or max_bytes<1024:raise JapiError('timeout must be >0 and max_bytes >=1024')
    results=[]
    for raw_case in cases:
        c=validate_case(deepcopy(raw_case))
        if c.get('blocked_reason'):
            results.append({'case_id':c.get('case_id'),'endpoint_id':c.get('endpoint_id'),'status':None,
                'error':'blocked: '+c['blocked_reason'],'quality_warnings':c.get('quality_warnings',[]),
                'quality_confidence':c.get('quality_confidence'),'body_b64':'','headers':{}})
            continue
        if not allow_low and c.get('quality_confidence') in ('low','unknown'):
            results.append({'case_id':c.get('case_id'),'endpoint_id':c.get('endpoint_id'),
                'status':None,'error':'blocked: low confidence','quality_warnings':c.get('quality_warnings',[]),'quality_confidence':c.get('quality_confidence'),'body_b64':'','headers':{}})
            continue
        if c['request']['method'].upper() not in ('GET','HEAD','OPTIONS') and not allow_mutation:
            results.append({'case_id':c.get('case_id'),'endpoint_id':c.get('endpoint_id'),
                'status':None,'error':'blocked: requires --allow-mutation','quality_warnings':c.get('quality_warnings',[]),'quality_confidence':c.get('quality_confidence'),'body_b64':'','headers':{}})
            continue
        results.append(request_one(c,base,headers,timeout,max_bytes))
    return results


def run_summary(results):
    return {'total':len(results),'completed':sum(r.get('status') is not None for r in results),
       'errors':sum(bool(r.get('error')) for r in results),
       'spec_mismatches':sum(r.get('status_matches_spec') is False for r in results),
       'low_confidence':sum(r.get('quality_confidence')=='low' for r in results)}
