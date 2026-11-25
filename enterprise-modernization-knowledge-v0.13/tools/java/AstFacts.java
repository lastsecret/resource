import java.io.*;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;
import javax.lang.model.element.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** Read-only javac tree extraction. Never generate classes or run processors. */
public class AstFacts {
  static String enc(String s) { return Base64.getUrlEncoder().withoutPadding().encodeToString(s.getBytes(java.nio.charset.StandardCharsets.UTF_8)); }
  public static void main(String[] args) throws Exception {
    boolean attr = args[0].equals("attribute");
    List<String> names = Files.readAllLines(Path.of(args[1]));
    JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
    if (compiler == null) throw new IllegalStateException("JDK required");
    DiagnosticCollector<JavaFileObject> diag = new DiagnosticCollector<>();
    try (StandardJavaFileManager fm = compiler.getStandardFileManager(diag, null, java.nio.charset.StandardCharsets.UTF_8)) {
      List<String> opts = List.of("-proc:none", "-implicit:none", "-classpath", args[2], "-sourcepath", "", "-encoding", "UTF-8");
      JavacTask task = (JavacTask) compiler.getTask(new StringWriter(), fm, diag, opts, null, fm.getJavaFileObjectsFromStrings(names));
      List<CompilationUnitTree> units = new ArrayList<>();
      task.parse().forEach(units::add);
      boolean parseClean = diag.getDiagnostics().stream().noneMatch(d -> d.getKind()==Diagnostic.Kind.ERROR);
      if (attr) task.analyze();
      boolean clean = diag.getDiagnostics().stream().noneMatch(d -> d.getKind()==Diagnostic.Kind.ERROR);
      Trees trees = Trees.instance(task);
      System.out.println("STATUS\t"+(clean ? (attr ? "ATTRIBUTED" : "PARSED") : "PARTIAL")+"\t"+(parseClean ? "PARSE_CLEAN" : "PARSE_INCOMPLETE"));
      for (CompilationUnitTree u: units) {
        final String file=Path.of(u.getSourceFile().toUri()).toAbsolutePath().normalize().toString();
        new TreePathScanner<Void,Void>() {
          void emit(String kind, Tree t, String s) {
            long pos=trees.getSourcePositions().getStartPosition(u,t);
            if(pos<0 || s.length()>512) return;
            long line=u.getLineMap().getLineNumber(pos);
            String resolved="";
            if(attr && clean) {
              try {
                Element e=trees.getElement(getCurrentPath());
                if(e instanceof TypeElement te) resolved=te.getQualifiedName().toString();
                else if(e!=null && e.getEnclosingElement() instanceof TypeElement te) resolved=te.getQualifiedName()+"#"+e.getSimpleName();
              } catch(RuntimeException ignored) {}
            }
            System.out.println(kind+"\t"+enc(file)+"\t"+line+"\t"+enc(s)+"\t"+enc(resolved));
          }
          void extra(String kind, Tree t, String value, String resolved) {
            long pos=trees.getSourcePositions().getStartPosition(u,t);
            if(pos<0 || value.length()>512 || resolved.length()>512) return;
            System.out.println(kind+"\t"+enc(file)+"\t"+u.getLineMap().getLineNumber(pos)+"\t"+enc(value)+"\t"+enc(resolved));
          }
          String owner() {
            if(!attr) return "";
            try {
              Element e=trees.getElement(getCurrentPath());
              if(e instanceof ExecutableElement ex && ex.getEnclosingElement() instanceof TypeElement te
                 && te.asType().getKind()!=javax.lang.model.type.TypeKind.ERROR && te.getQualifiedName().length()>0)
                return te.getQualifiedName()+"#"+ex.getSimpleName();
            } catch(RuntimeException ignored) {}
            return "";
          }
          @Override public Void visitVariable(VariableTree t, Void p) {
            if(t.getType()!=null) extra("variable_type",t,t.getName()+"#"+t.getType(),"");
            return super.visitVariable(t,p);
          }
          @Override public Void visitMethod(MethodTree t, Void p) {
            if(t.getReturnType()!=null) {
              String cls="";
              for(TreePath tp=getCurrentPath().getParentPath();tp!=null;tp=tp.getParentPath()) if(tp.getLeaf() instanceof ClassTree ct) { cls=ct.getSimpleName().toString(); break; }
              String pkg=u.getPackageName()==null ? "" : u.getPackageName().toString()+".";
              long end=trees.getSourcePositions().getEndPosition(u,t);
              if(!cls.isEmpty() && end>=0) extra("method_info",t,pkg+cls+"#"+t.getName()+"#"+t.getParameters().size()+"#"+u.getLineMap().getLineNumber(end)+"#"+t.getReturnType(),"");
              boolean bean=t.getModifiers().getAnnotations().stream().anyMatch(a -> a.getAnnotationType().toString().equals("Bean") || a.getAnnotationType().toString().equals("org.springframework.context.annotation.Bean"));
              if(bean) {
                String type="";
                if(attr) try { Element e=trees.getElement(getCurrentPath()); if(e instanceof ExecutableElement ex && ex.getReturnType().getKind()!=javax.lang.model.type.TypeKind.ERROR) type=ex.getReturnType().toString(); } catch(RuntimeException ignored) {}
                extra("bean_method",t,t.getReturnType().toString(),type);
                if(t.getBody()!=null) for(StatementTree st:t.getBody().getStatements()) {
                  if(st instanceof ReturnTree rt && rt.getExpression() instanceof MethodInvocationTree mi) extra("bean_factory",t,mi.getMethodSelect().toString()+"#"+mi.getArguments().size(),"");
                }
              }
            }
            return super.visitMethod(t,p);
          }
          @Override public Void visitImport(ImportTree t, Void p) {emit("import",t,t.getQualifiedIdentifier().toString());return super.visitImport(t,p);}
          @Override public Void visitAnnotation(AnnotationTree t, Void p) {emit("annotation",t,t.getAnnotationType().toString());return super.visitAnnotation(t,p);}
          @Override public Void visitMethodInvocation(MethodInvocationTree t, Void p) {emit("call",t,t.getMethodSelect().toString());extra("invocation",t,t.getMethodSelect()+"#"+t.getArguments().size(),owner());
            String m=t.getMethodSelect().toString();
            for(ExpressionTree arg:t.getArguments()) {
              String a=arg.toString();
              if(a.endsWith(".FAIL_ON_NULL_FOR_PRIMITIVES")||a.endsWith(".SORT_PROPERTIES_ALPHABETICALLY")) {
                String sw=m.endsWith(".enable")?"ENABLE":m.endsWith(".disable")?"DISABLE":"UNKNOWN";
                if(!sw.equals("UNKNOWN"))extra("feature_switch",t,a.substring(a.lastIndexOf('.')+1)+"#"+sw,owner());
              }
            }
            return super.visitMethodInvocation(t,p);}
          @Override public Void visitNewClass(NewClassTree t, Void p) {emit("constructor",t,t.getIdentifier().toString());extra("construction",t,t.getIdentifier().toString(),owner());return super.visitNewClass(t,p);}
          @Override public Void visitIdentifier(IdentifierTree t, Void p) {emit("symbol",t,t.getName().toString());return super.visitIdentifier(t,p);}
          @Override public Void visitMemberSelect(MemberSelectTree t, Void p) {emit("symbol",t,t.toString());return super.visitMemberSelect(t,p);}
        }.scan(u,null);
      }
    }
  }
}
