// JDK 17+ source-only AST scanner. No project compilation or dependency download.
import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.tools.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

public class ApiAstScanner {
  static String json(Object x) {
    if (x == null) return "null";
    if (x instanceof Number || x instanceof Boolean) return x.toString();
    if (x instanceof String s) {
      StringBuilder b=new StringBuilder("\"");
      for(char c:s.toCharArray()) switch(c){
        case '\"' -> b.append("\\\""); case '\\' -> b.append("\\\\"); case '\n' -> b.append("\\n");
        case '\r' -> b.append("\\r"); case '\t' -> b.append("\\t");
        default -> { if(c<32) b.append(String.format("\\u%04x",(int)c)); else b.append(c); }
      }
      return b.append('"').toString();
    }
    if(x instanceof Map<?,?> m) return "{"+m.entrySet().stream().map(e->json(e.getKey().toString())+":"+json(e.getValue())).collect(Collectors.joining(","))+"}";
    if(x instanceof Iterable<?> a) {
      List<String> o=new ArrayList<>(); for(Object v:a)o.add(json(v));return "["+String.join(",",o)+"]";
    }
    return json(x.toString());
  }
  static Map<String,Object> obj(Object... kv) {
    Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<kv.length;i+=2)m.put((String)kv[i],kv[i+1]);return m;
  }
  static String annName(AnnotationTree a) {
    String x=a.getAnnotationType().toString(); return x.substring(x.lastIndexOf('.')+1);
  }
  static String unquote(String str){
    str=str.trim();return str.length()>=2&&str.startsWith("\"")&&str.endsWith("\"") ? str.substring(1,str.length()-1):str;
  }
  static Map<String,String> annAttrs(AnnotationTree a){
    Map<String,String> r=new LinkedHashMap<>();
    for(ExpressionTree x:a.getArguments()) {
      if(x instanceof AssignmentTree z)r.put(z.getVariable().toString(),z.getExpression().toString());
      else r.put("value",x.toString());
    }
    return r;
  }
  static String annotationValue(AnnotationTree a) {
    Map<String,String> m=annAttrs(a);String x=m.getOrDefault("path",m.getOrDefault("value",""));
    if(x.startsWith("{")) {
      int i=x.indexOf('"'),j=i<0?-1:x.indexOf('"',i+1);
      return i>=0&&j>i?x.substring(i+1,j):"";
    }
    return unquote(x);
  }
  static String joinPath(String a,String b){
    String x="/"+a.replaceAll("^/+|/+$","")+"/"+b.replaceAll("^/+|/+$","");
    x=x.replaceAll("/+","/");return x.length()>1&&x.endsWith("/")?x.substring(0,x.length()-1):x;
  }
  static String schemaType(String t){
    t=t.replace("java.lang.","").trim();
    if(t.equals("String")||t.equals("UUID")||t.equals("LocalDate")||t.equals("LocalDateTime")||t.equals("Instant"))return "string";
    if(t.equals("int")||t.equals("Integer")||t.equals("long")||t.equals("Long")||t.equals("short")||t.equals("Short"))return "integer";
    if(t.equals("double")||t.equals("Double")||t.equals("float")||t.equals("Float")||t.equals("BigDecimal"))return "number";
    if(t.equals("boolean")||t.equals("Boolean"))return "boolean";
    if(t.endsWith("[]")||t.startsWith("List<")||t.startsWith("Set<")||t.startsWith("Collection<"))return "array";
    if(t.startsWith("Map<"))return "object";
    return "unknown";
  }
  static class TypeInfo {
    final CompilationUnitTree unit; final ClassTree tree; final String name; final String source;
    TypeInfo(CompilationUnitTree unit, ClassTree tree, String name, String source) {
      this.unit=unit; this.tree=tree; this.name=name; this.source=source;
    }
  }
  static final Map<String,TypeInfo> types=new LinkedHashMap<>();
  static final List<Object> hierarchyIssues=new ArrayList<>();
  static TypeInfo resolve(String name, TypeInfo owner) {
    if(name.contains("<")) {
      hierarchyIssues.add("Generic controller hierarchy is not resolved: "+owner.name+" -> "+name);
      return null;
    }
    if(types.containsKey(name)) return types.get(name);
    String pkg=owner.unit.getPackageName()==null?"":owner.unit.getPackageName().toString();
    for(ImportTree imp:owner.unit.getImports()) {
      if(imp.isStatic())continue;
      String imported=imp.getQualifiedIdentifier().toString();
      if(imported.endsWith("."+name)&&types.containsKey(imported))return types.get(imported);
    }
    String local=pkg.isEmpty()?name:pkg+"."+name;
    if(types.containsKey(local))return types.get(local);
    List<TypeInfo> candidates=new ArrayList<>();
    for(ImportTree imp:owner.unit.getImports()) {
      String imported=imp.getQualifiedIdentifier().toString();
      if(!imp.isStatic()&&imported.endsWith(".*")) {
        TypeInfo t=types.get(imported.substring(0,imported.length()-1)+name);
        if(t!=null)candidates.add(t);
      }
    }
    if(candidates.size()==1)return candidates.get(0);
    hierarchyIssues.add("Unresolved or ambiguous controller parent: "+owner.name+" -> "+name);
    return null;
  }
  static List<TypeInfo> parents(TypeInfo t) {
    List<Tree> refs=new ArrayList<>();
    if(t.tree.getExtendsClause()!=null)refs.add(t.tree.getExtendsClause());
    refs.addAll(t.tree.getImplementsClause());
    List<TypeInfo> result=new ArrayList<>();
    for(Tree ref:refs){TypeInfo p=resolve(ref.toString(),t);if(p!=null)result.add(p);}
    return result;
  }
  static String signature(MethodTree m, TypeInfo owner) {
    List<String> args=new ArrayList<>();
    for(VariableTree p:m.getParameters()) {
      String type=p.getType().toString().replace("java.lang.","");
      // Canonicalize source types using imports/package, without compiling the project.
      String pkg=owner.unit.getPackageName()==null?"":owner.unit.getPackageName().toString();
      for(ImportTree imp:owner.unit.getImports()) {
        String imported=imp.getQualifiedIdentifier().toString();
        if(!imp.isStatic()&&imported.endsWith("."+type))type=imported;
      }
      if(types.containsKey(pkg+"."+type))type=pkg+"."+type;
      args.add(type);
    }
    return m.getName()+"("+String.join(",",args)+")";
  }
  static class Declaration {
    final MethodTree method; final TypeInfo owner;
    Declaration(MethodTree method,TypeInfo owner){this.method=method;this.owner=owner;}
  }
  static Map<String,List<Declaration>> methods(TypeInfo t,Set<String> visiting) {
    Map<String,List<Declaration>> result=new LinkedHashMap<>();
    if(!visiting.add(t.name))return result;
    for(Tree member:t.tree.getMembers())if(member instanceof MethodTree m && m.getReturnType()!=null
        && !m.getModifiers().getFlags().contains(javax.lang.model.element.Modifier.STATIC)
        && !m.getModifiers().getFlags().contains(javax.lang.model.element.Modifier.PRIVATE))
      result.computeIfAbsent(signature(m,t),k->new ArrayList<>()).add(new Declaration(m,t));
    for(TypeInfo parent:parents(t))for(var e:methods(parent,visiting).entrySet())
      result.computeIfAbsent(e.getKey(),k->new ArrayList<>()).addAll(e.getValue());
    visiting.remove(t.name);
    return result;
  }
  static AnnotationTree mapping(List<? extends AnnotationTree> annotations) {
    for(AnnotationTree a:annotations)if(Set.of("RequestMapping","GetMapping","PostMapping",
        "PutMapping","PatchMapping","DeleteMapping","HeadMapping","OptionsMapping").contains(annName(a)))return a;
    return null;
  }
  static AnnotationTree typeMapping(TypeInfo t,Set<String> visiting) {
    if(!visiting.add(t.name))return null;
    AnnotationTree a=mapping(t.tree.getModifiers().getAnnotations());
    if(a!=null)return a;
    for(TypeInfo parent:parents(t)){a=typeMapping(parent,visiting);if(a!=null)return a;}
    return null;
  }
  static void scanType(TypeInfo t,List<Object> endpoints,Map<String,Object> classes) {
    ClassTree cl=t.tree;
    Map<String,Object> fields=new LinkedHashMap<>();
    for(Tree member:cl.getMembers())if(member instanceof VariableTree field){
      if(field.getModifiers().getFlags().contains(javax.lang.model.element.Modifier.STATIC))continue;
      if(field.getType()!=null)fields.put(field.getName().toString(),field.getType().toString());
    }
    if(!fields.isEmpty())classes.put(cl.getSimpleName().toString(),fields);
    boolean controller=cl.getModifiers().getAnnotations().stream()
        .anyMatch(a->Set.of("RestController","Controller").contains(annName(a)));
    if(!controller||cl.getKind()==Tree.Kind.INTERFACE
        ||cl.getModifiers().getFlags().contains(javax.lang.model.element.Modifier.ABSTRACT))return;
    AnnotationTree baseAnnotation=typeMapping(t,new HashSet<>());
    String base=baseAnnotation==null?"":annotationValue(baseAnnotation);
    for(List<Declaration> chain:methods(t,new HashSet<>()).values()) {
      Declaration implementation=chain.get(0), mapped=null;
      AnnotationTree route=null;
      for(Declaration d:chain){route=mapping(d.method.getModifiers().getAnnotations());if(route!=null){mapped=d;break;}}
      if(route==null)continue;
      String http=null,n=annName(route);
      if(!n.equals("RequestMapping"))http=n.substring(0,n.length()-7).toUpperCase(Locale.ROOT);
      else {
        String value=annAttrs(route).getOrDefault("method","").toUpperCase(Locale.ROOT);
        for(String k:List.of("GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"))if(value.contains(k)){http=k;break;}
      }
      if(http==null)continue;
      MethodTree method=implementation.method;
      List<Object> params=new ArrayList<>();String bodyType=null;
      for(int i=0;i<method.getParameters().size();i++) {
        VariableTree p=method.getParameters().get(i),metadata=p;
        for(Declaration d:chain) {
          VariableTree candidate=d.method.getParameters().get(i);
          if(candidate.getModifiers().getAnnotations().stream().anyMatch(a->Set.of("RequestBody",
              "PathVariable","RequestParam","RequestHeader").contains(annName(a)))){metadata=candidate;break;}
        }
        String location=null,pname=metadata.getName().toString();boolean required=false;
        for(AnnotationTree a:metadata.getModifiers().getAnnotations()) {
          String an=annName(a);
          if(an.equals("RequestBody"))bodyType=p.getType().toString();
          if(an.equals("PathVariable"))location="path";
          if(an.equals("RequestParam"))location="query";
          if(an.equals("RequestHeader"))location="header";
          if(Set.of("PathVariable","RequestParam","RequestHeader").contains(an)) {
            Map<String,String> attrs=annAttrs(a);
            String explicit=unquote(attrs.getOrDefault("name",attrs.getOrDefault("value","")));
            if(!explicit.isBlank())pname=explicit;
            required=location.equals("path")||(!attrs.getOrDefault("required","true").equals("false")&&!attrs.containsKey("defaultValue"));
          }
        }
        if(location!=null)params.add(obj("name",pname,"in",location,"required",required,"java_type",p.getType().toString()));
      }
      String returnType=method.getReturnType().toString();
      if(returnType.startsWith("ResponseEntity<")&&returnType.endsWith(">"))returnType=returnType.substring(15,returnType.length()-1);
      long pos=Trees.instance(JavacTaskHolder.task).getSourcePositions().getStartPosition(mapped.owner.unit,mapped.method);
      long line=mapped.owner.unit.getLineMap().getLineNumber(pos);
      endpoints.add(obj("method",http,"path",joinPath(base,annotationValue(route)),"parameters",params,
          "return_type",returnType,"body_type",bodyType,"source",mapped.owner.source+":"+line,
          "operation_id",method.getName().toString()));
    }
  }
  static class JavacTaskHolder{static JavacTask task;}
  public static void main(String[] args)throws Exception{
    if(args.length!=1){System.err.println("Usage: java ApiAstScanner.java <project>");System.exit(2);}
    Path root=Path.of(args[0]).toAbsolutePath().normalize();
    List<Path> files=new ArrayList<>();
    try(var walk=Files.walk(root)){
      walk.filter(p->p.toString().endsWith(".java") && Files.isRegularFile(p))
       .filter(p->Arrays.stream(root.relativize(p).toString().split("[/\\\\]")).noneMatch(s->Set.of("target","build",".git","vendor","node_modules").contains(s)))
       .limit(3001).forEach(files::add);
    }
    if(files.size()>3000)throw new IllegalArgumentException("More than 3000 Java files; use a narrower module");
    JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
    if(compiler==null)throw new IllegalStateException("Full JDK (javac), not JRE, required");
    DiagnosticCollector<JavaFileObject> diagnostic=new DiagnosticCollector<>();
    List<Object>endpoints=new ArrayList<>();Map<String,Object>classes=new LinkedHashMap<>();
    try(StandardJavaFileManager fm=compiler.getStandardFileManager(diagnostic,null,null)){
      JavacTask task=(JavacTask)compiler.getTask(null,fm,diagnostic,List.of("-proc:none"),null,fm.getJavaFileObjectsFromPaths(files));
      JavacTaskHolder.task=task;
      for(CompilationUnitTree unit:task.parse()){
        Path source=Path.of(unit.getSourceFile().toUri());
        new TreePathScanner<Void,String>() {
          @Override public Void visitClass(ClassTree cl,String parent) {
            String pkg=unit.getPackageName()==null?"":unit.getPackageName().toString();
            String prefix=parent==null?pkg:parent;
            String name=(prefix.isEmpty()?"":prefix+".")+cl.getSimpleName();
            types.put(name,new TypeInfo(unit,cl,name,root.relativize(source).toString()));
            return super.visitClass(cl,name);
          }
        }.scan(unit,null);
      }
      for(TypeInfo t:types.values())scanType(t,endpoints,classes);
    }
    List<Object>issues=new ArrayList<>();
    issues.addAll(new LinkedHashSet<>(hierarchyIssues));
    for(Diagnostic<? extends JavaFileObject> d:diagnostic.getDiagnostics())
      if(d.getKind()==Diagnostic.Kind.ERROR)issues.add(d.getMessage(Locale.ROOT));
    System.out.println(json(obj("endpoints",endpoints,"classes",classes,"diagnostics",issues)));
  }
}
