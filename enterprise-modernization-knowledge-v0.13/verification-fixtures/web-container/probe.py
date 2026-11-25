"""Loopback-only observational HTTP probes. Explicit invocation; not a load test."""
import argparse,http.client,json,sys
CASES=[('health','GET','/probe/health',None),('encoded','GET','/probe/echo?q=a%2Bb%20c',None),('unicode','GET','/probe/echo?q=%E4%B8%AD%E6%96%87',None),('missing_parameter','GET','/probe/echo',None),('body','POST','/probe/body','hello')]
def capture(port):
    result={}
    for label,method,path,body in CASES:
        c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        try:
            c.request(method,path,body,{'Content-Type':'text/plain; charset=utf-8'} if body is not None else {})
            response=c.getresponse();data=response.read(65537)
            if len(data)>65536:raise ValueError('Response too large')
            payload=None
            if response.status==200:
                obj=json.loads(data)
                # Only fixed fixture keys/known values, never export arbitrary response text.
                expected={'health':{'status':'UP'},'encoded':{'q':'a+b c'},'unicode':{'q':'中文'},'body':{'length':5}}[label]
                payload='MATCH' if obj==expected else 'MISMATCH'
            result[label]={'status':response.status,'fixture_payload':payload}
        finally:c.close()
    return result

def compare(a,b):
    expected={'health':200,'encoded':200,'unicode':200,'missing_parameter':400,'body':200}
    rows=[]
    for label,code in expected.items():
        x=a.get(label);y=b.get(label);ok=bool(x and y and x==y and x['status']==code and (code!=200 or x['fixture_payload']=='MATCH'))
        rows.append({'case':label,'observed_match':ok,'source':x,'target':y})
    return rows
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-port',type=int,required=True);p.add_argument('--target-port',type=int,required=True);a=p.parse_args()
    try:
        if a.source_port==a.target_port or not all(1<=x<=65535 for x in (a.source_port,a.target_port)):raise ValueError('Ports must be distinct')
        rows=compare(capture(a.source_port),capture(a.target_port));print(json.dumps({'status':'OBSERVED_FIXTURE_MATCH' if all(r['observed_match'] for r in rows) else 'OBSERVED_DIFFERENCE','cases':rows},ensure_ascii=False,indent=2));sys.exit(0 if all(r['observed_match'] for r in rows) else 2)
    except Exception as e:print(json.dumps({'status':'INCOMPLETE','error_type':type(e).__name__}));sys.exit(3)
