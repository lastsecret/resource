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
  static class Scanner extends TreePathScanner<Void,Void>{
    final CompilationUnitTree unit; final Path file; final String root;
    final List<Object> endpoints;final Map<String,Object> classes;
    String base=""; boolean controller=false;
    Scanner(CompilationUnitTree unit,Path file,String root,List<Object> endpoints,Map<String,Object> classes) {
      this.unit=unit;this.file=file;this.root=root;this.endpoints=endpoints;this.classes=classes;
    }
    @Override public Void visitClass(ClassTree cl,Void v){
      String prior=base;boolean priorC=controller;
      List<? extends AnnotationTree> annotations=cl.getModifiers().getAnnotations();
      controller=annotations.stream().anyMatch(a->Set.of("RestController","Controller").contains(annName(a)));
      base="";
      for(AnnotationTree a:annotations) if(annName(a).equals("RequestMapping"))base=annotationValue(a);
      String cls=cl.getSimpleName().toString();
      Map<String,Object> fields=new LinkedHashMap<>();
      for(Tree member:cl.getMembers())if(member instanceof VariableTree field){
        if(field.getModifiers().getFlags().contains(javax.lang.model.element.Modifier.STATIC))continue;
        if(field.getType()!=null)fields.put(field.getName().toString(),field.getType().toString());
      }
      if(!fields.isEmpty())classes.put(cls,fields);
      super.visitClass(cl,v);
      base=prior;controller=priorC;
      return null;
    }
    @Override public Void visitMethod(MethodTree method,Void v){
      String http=null,path="";
      for(AnnotationTree a:method.getModifiers().getAnnotations()){
        String n=annName(a);
        if(n.endsWith("Mapping")&&n.length()>7){
          http=n.substring(0,n.length()-7).toUpperCase(Locale.ROOT);path=annotationValue(a);break;
        }
        if(n.equals("RequestMapping")){
          String m=annAttrs(a).getOrDefault("method","").toUpperCase(Locale.ROOT);
          for(String k:List.of("GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"))if(m.contains(k)){http=k;break;}
          path=annotationValue(a);
        }
      }
      if(controller&&http!=null){
        List<Object> params=new ArrayList<>();String bodyType=null;
        for(VariableTree p:method.getParameters()){
          String location=null,pname=p.getName().toString();
          for(AnnotationTree a:p.getModifiers().getAnnotations()){
            String n=annName(a);
            if(n.equals("RequestBody"))bodyType=p.getType().toString();
            if(n.equals("PathVariable"))location="path";
            if(n.equals("RequestParam"))location="query";
            if(n.equals("RequestHeader"))location="header";
            if(location!=null&&!annotationValue(a).isBlank())pname=annotationValue(a);
          }
          if(location!=null)params.add(obj("name",pname,"in",location,"required",location.equals("path"),"java_type",p.getType().toString()));
        }
        String returnType=method.getReturnType()==null?"void":method.getReturnType().toString();
        if(returnType.startsWith("ResponseEntity<")&&returnType.endsWith(">"))returnType=returnType.substring(15,returnType.length()-1);
        long pos=Trees.instance(JavacTaskHolder.task).getSourcePositions().getStartPosition(unit,method);
        long line=unit.getLineMap().getLineNumber(pos);
        endpoints.add(obj("method",http,"path",joinPath(base,path),"parameters",params,
            "return_type",returnType,"body_type",bodyType,"source",root+":"+line,"operation_id",method.getName().toString()));
      }
      return super.visitMethod(method,v);
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
        new Scanner(unit,source,root.relativize(source).toString(),endpoints,classes).scan(unit,null);
      }
    }
    List<Object>issues=new ArrayList<>();
    for(Diagnostic<? extends JavaFileObject> d:diagnostic.getDiagnostics())
      if(d.getKind()==Diagnostic.Kind.ERROR)issues.add(d.getMessage(Locale.ROOT));
    System.out.println(json(obj("endpoints",endpoints,"classes",classes,"diagnostics",issues)));
  }
}
