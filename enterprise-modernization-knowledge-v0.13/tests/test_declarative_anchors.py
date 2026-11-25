"""One synthetic positive anchor per newly declared rule, not an impact or runtime test."""
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from declarative import collect,load_plans

class Anchors(unittest.TestCase):pass

def make_test(rid,plan):
 def test(self):
  m=plan['match_any'][0];kind=m['type'];v=m['pattern'].replace('*','Example')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   if kind=='java.call':f=p/'A.java';f.write_text('class A { void f(){ '+v+'(); } }')
   elif kind=='java.annotation':f=p/'A.java';f.write_text('@'+v+' class A {}')
   elif kind=='java.symbol':f=p/'A.java';f.write_text('class A { '+v+' a; }')
   elif kind=='java.import':f=p/'A.java';f.write_text('import '+v+'; class A {}')
   elif kind=='dependency.artifact':f=p/'pom.xml';f.write_text('<project><dependencies><dependency><artifactId>'+v+'</artifactId></dependency></dependencies></project>')
   elif kind=='config.key':f=p/'application.properties';f.write_text(v+'=true')
   elif kind=='xml.mybatis.element':f=p/'A.xml';f.write_text('<mapper><'+v+'/></mapper>')
   elif kind=='file.name':f=p/v;f.write_text('')
   else:raise AssertionError(kind)
   hits,_,_=collect(p,{rid:plan});self.assertTrue(hits[rid],rid);self.assertIn(f.name,hits[rid][0]['location'])
 return test
for rid,plan in load_plans().items():
 if plan.get('match_any'):setattr(Anchors,'test_'+rid.replace('-','_'),make_test(rid,plan))
