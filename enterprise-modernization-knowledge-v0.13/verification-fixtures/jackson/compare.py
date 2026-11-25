"""Compare observed fixture values. Requires successful Maven runs; missing output blocks."""
import json,sys
from pathlib import Path

def parse(p):
    values={};order={}
    for line in Path(p).read_text(encoding='utf8').splitlines():
        if not line.startswith('PROBE '):continue
        label,rest=line[6:].split(' ',1)
        if rest.startswith('INPUT='):
            input_,result=rest[6:].split(' RESULT=',1);values[(label,input_)]=result
        elif rest.startswith('ORDER='):order[label]=rest[6:]
    if len(values)!=9 or len(order)!=3:raise ValueError('Incomplete probe output')
    return values,order

def outcome(s):return 'ERROR' if s.startswith('ERROR:') else s

def main():
    a,ao=parse(sys.argv[1]);b,bo=parse(sys.argv[2]); rows=[]
    for baseline,target in [('DEFAULT','DEFAULT'),('DEFAULT','LEGACY_FLAGS'),('STRICT_FLAGS','STRICT_FLAGS')]:
        for (label,input_),v in a.items():
            if label!=baseline:continue
            observed=b[(target,input_)];rows.append({'source':baseline,'target':target,'input':input_,'old':v,'new':observed,'semantic_match':outcome(v)==outcome(observed)})
        rows.append({'source':baseline,'target':target,'order_semantic_match':json.loads(ao[baseline])==json.loads(bo[target]),'order_exact_match':ao[baseline]==bo[target]})
    print(json.dumps(rows,indent=2));return 0 if all(r.get('semantic_match',r.get('order_semantic_match',False)) for r in rows if (r['source'],r['target'])!=('DEFAULT','DEFAULT')) else 2
if __name__=='__main__':raise SystemExit(main())
