# Undertow / Tomcat HTTP fixture — NOT_RUN against actual containers

Use trusted disposable directories, approved Maven dependencies, and Java 17. In separate terminals, run:

```sh
mvn -o -f undertow/pom.xml spring-boot:run -Dspring-boot.run.arguments="--server.address=127.0.0.1 --server.port=18080"
mvn -o -f tomcat/pom.xml spring-boot:run -Dspring-boot.run.arguments="--server.address=127.0.0.1 --server.port=18081"
python3 probe.py --source-port 18080 --target-port 18081
```

Inspect successful startup logs and actual dependencies first. The probe covers URL decoding, required query parameters, basic body handling and a synthetic health endpoint. It compares JSON semantics only for fixed successful responses and status for the failure case. It does not cover production actuator, response error body contract, connection timeout, worker counts, header/body limits, load, graceful shutdown, or security. Use an approved separate test environment for these. Maven and Java 17 are unavailable in the authoring environment; neither application has been compiled or run here. Probe comparison logic is independently tested with synthetic local results. No production URLs are accepted.
