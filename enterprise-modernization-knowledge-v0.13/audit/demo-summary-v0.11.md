# Evidence Resolution v0.11

Initial: {'DETECTED': 10, 'NOT_DETECTED': 31, 'UNKNOWN': 56, 'NOT_EVALUATED': 3}
Final: {'DETECTED': 10, 'NOT_DETECTED': 31, 'UNKNOWN': 56, 'NOT_EVALUATED': 3}

## Actions
- JAVA_AST: COMPLETE_CANDIDATE_SCAN
- ACQUIRE_COMPONENT_PAIR: TARGET_WORKTREE_REQUIRED

## Unresolved evidence
- CONFIG_METADATA_DIFF_REQUIRED: 1 rules. Compare exact source/target Spring configuration metadata; detector not implemented.
- DEPENDENCY_GRAPH_DIFF_REQUIRED: 1 rules. Review resolved per-module graph differences; detector not implemented.
- JAR_API_DIFF_REQUIRED: 1 rules. Compare exact source/target public JAR APIs and references; detector not implemented.
- MISSING_COMPONENT_GRAPH: 56 rules. Acquire source and target dependency trees once per approved profile/module scope.

Gate: BLOCKED_PENDING_VERIFIED_EVIDENCE. No automatic patch. Runtime: NOT_RUN.
