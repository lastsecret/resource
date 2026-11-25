# Jackson standalone fixture (NOT_RUN)

Run in approved environment with Java 17, Maven and approved artifacts. Set JAVA_HOME to Java 17 first. Maven may execute configured plugins; use disposable workspace. These are standalone manually-created mappers, not Spring auto-configured mappers. The versions are reference target lines from the Boot 4.1.3 coordinate page, not claims about a source project's resolved versions. Replace versions only with exact approved source/target versions.

```sh
mvn -version
mvn -o -f jackson2/pom.xml compile exec:java -Dexec.mainClass=demo.Probe > jackson2.out
mvn -o -f jackson3/pom.xml compile exec:java -Dexec.mainClass=demo.Probe > jackson3.out
python3 compare.py jackson2.out jackson3.out
```

Remove `-o` only if approved private repository permits dependency retrieval. Expected: explicit JSON null into primitive behaves differently by default, legacy flags should preserve the old behavior if the old mapper used defaults; strict flags should preserve error semantics for strict baseline. Boxed null and absent field must be separate. Compare POJO JSON both semantically and byte-order-sensitive when contract demands it. This fixture never edits project code. It has not been compiled or run in the authoring environment (Maven and JDK17 absent). Spring-managed/custom Mapper integration, Tomcat/Undertow, Oracle/Hibernate and authorization matrix remain separate fixtures to implement or run against actual projects.
