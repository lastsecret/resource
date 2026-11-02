# Migration plan — approval required
Project: TODO
Current Spring Boot: TODO
Target Spring Boot: TODO
JDK retained: TODO
Pilot module: TODO
Pinned OpenRewrite plugin: TODO
Pinned rewrite-spring: TODO

## Confirmed breaking changes
TODO (link to DELTA_CATALOG)

## Baseline and risk
TODO

## Execution order
- [ ] Preflight
- [ ] Baseline
- [ ] Dependency/delta assessment
- [ ] Approval of plan
- [ ] Pilot dry-run review
- [ ] Approval to apply
- [ ] Pilot apply and compile/test
- [ ] Remaining modules staged
- [ ] Independent behavioral verification
- [ ] Final approval/sign-off

## Rollback
Git worktree/branch revert; restore built/deployed artifact, database backups/migration policy as appropriate.
