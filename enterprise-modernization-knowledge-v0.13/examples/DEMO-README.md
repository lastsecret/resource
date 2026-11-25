# Static scanner demonstration

The `springboot3-undertow-demo/` directory is **not a compilable Spring Boot application**. It is a synthetic input fixture for the scanner; it contains representative POM, properties, profile YAML, and Java source.

From the knowledge pack root:

```bash
python3 tools/project_scanner.py \
  --project examples/springboot3-undertow-demo \
  --output /tmp/undertow-scan-output
```

Inspect `findings.json`, `report.md`, and `suggested-tomcat.properties` in the output directory. All proposed target properties remain commented out. **Run-time effective behavior is not established.**
