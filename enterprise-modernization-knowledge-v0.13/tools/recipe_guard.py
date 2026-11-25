"""Conservative read-only unified-diff review gate. Never applies patches.
Not a full Git parser; unrecognized input is blocked, never approved.
"""
import argparse,json,re,sys
from pathlib import Path,PurePosixPath

def review(diff):
    findings=[];paths=[];current=None;headers=0;changed=0;in_hunk=False
    def add(code,path=None,line=None):
        f={'code':code,'path':path,'line':line}
        if f not in findings:findings.append(f)
    def path_safe(s):
        return s and not s.startswith(('/', '\\')) and not re.search(r'[:\\\x00-\x1f]',s) and '..' not in PurePosixPath(s).parts and not s.startswith('"')
    for no,line in enumerate(diff.splitlines(),1):
        if line.startswith('diff --git '):
            in_hunk=False;headers+=1
            m=re.fullmatch(r'diff --git a/(\S+) b/(\S+)',line)
            current=None
            if not m or not all(path_safe(x) for x in m.groups()):add('UNRECOGNIZED_OR_UNSAFE_PATH',line=no);continue
            before,after=m.groups();current=after;paths.extend([before,after]);
            if before!=after:add('RENAME_REVIEW',current,no)
            for p in (before,after):
                lower=p.lower();parts=PurePosixPath(lower).parts
                if 'test' in parts or 'tests' in parts or 'snapshots' in parts or 'fixtures' in parts or lower.endswith(('.snap','.golden')):add('BASELINE_TEST_CHANGE',p,no)
                if lower.startswith(('.github/','.gitlab/','.circleci/')) or 'dockerfile' in lower or 'jenkinsfile' in lower or lower.endswith(('gitlab-ci.yml','azure-pipelines.yml','docker-compose.yml','compose.yaml','compose.yml')):add('CI_OR_CONTAINER_CHANGE',p,no)
                if 'security' in lower or 'auth' in lower:add('SECURITY_REVIEW',p,no)
                if lower.endswith(('pom.xml','build.gradle','build.gradle.kts','gradle.properties','libs.versions.toml')):add('DEPENDENCY_OR_BUILD_CHANGE',p,no)
            continue
        if line.startswith(('Binary files ','GIT binary patch','new file mode 120000','old mode ','new mode ','rename from ','rename to ','copy from ','copy to ')):add('SPECIAL_DIFF_REVIEW',current,no)
        if line.startswith(('--- ','+++ ')) and not in_hunk:
            raw=line[4:].split('\t')[0]
            expected=('a/' if line.startswith('--- ') else 'b/')
            if raw!='/dev/null' and (not raw.startswith(expected) or not path_safe(raw[2:]) or raw[2:] not in paths):add('INCONSISTENT_FILE_HEADER',current,no)
            continue
        if line.startswith('@@ '):
            if not current:add('HUNK_WITHOUT_VALID_HEADER',line=no)
            in_hunk=True;continue
        if in_hunk and line.startswith(('+','-')):
            changed+=1
            if re.search(r'java\.version|maven\.compiler\.(?:release|source|target)|JavaLanguageVersion|sourceCompatibility|targetCompatibility|JAVA_HOME|jdk[-_: ]?\d+|eclipse-temurin|java-version|<release>\d+',line,re.I):add('JAVA_VERSION_CHANGE',current,no)
            if re.search(r'permitAll|denyAll|csrf|securityMatcher|authorizeHttpRequests|hasRole|hasAuthority',line,re.I):add('AUTHORIZATION_CHANGE',current,no)
            if re.search(r'(?i)hikaricp|ojdbc|jackson|hibernate|spring-boot-dependencies|<version>|\bimplementation\b',line):add('DEPENDENCY_REVIEW',current,no)
    if not headers or not changed:add('EMPTY_OR_UNRECOGNIZED_DIFF')
    return {'status':'BLOCKED_PENDING_HUMAN_REVIEW','automatic_patch':False,'changed_lines_observed':changed,'files':sorted(set(paths)),'findings':findings,'notes':['All patches require human review, even with zero detected risks.','Lexical review only; no proof of effective JDK, authorization or test integrity. Never apply from this tool.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('patch',type=Path);a=p.parse_args()
    if a.patch.stat().st_size>10_000_000:raise SystemExit('Patch too large')
    print(json.dumps(review(a.patch.read_text(encoding='utf8')),indent=2));return 2
if __name__=='__main__':sys.exit(main())
