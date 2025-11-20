# TASKER Development Guidelines

## 🚨 MANDATORY PRE-WORK CHECKLIST 🚨

**⚠️ BEFORE making ANY code changes, Claude MUST explicitly state:**

```text
✅ "I will create backups using: cp file.py file.py.backup_$(date +%Y%m%d_%H%M%S)"
✅ "I will run 100% verification testing before any commit suggestions"
✅ "I acknowledge that violating CRITICAL/MANDATORY requirements breaks production code"
✅ "I have read and will follow all CRITICAL/MANDATORY sections below"
```

**🔒 USER ENFORCEMENT:** If Claude starts making changes without this explicit confirmation, **IMMEDIATELY STOP THE WORK** and require compliance.

---

## 📋 VERSION NUMBERING POLICY 📋

**TASKER follows semantic versioning: MAJOR.MINOR.PATCH (e.g., 2.1.3)**

### **Version Increment Rules**

- **PATCH (3rd digit)**: Increment for bug fixes and small changes
  - Example: 2.1.0 → 2.1.1
  - Use cases: Bug fixes, typo corrections, minor refactoring, documentation updates

- **MINOR (2nd digit)**: Increment for new features
  - Example: 2.1.0 → 2.2.0
  - Use cases: New functionality, new parameters, workflow enhancements
  - Reset PATCH to 0 when incrementing MINOR

- **MAJOR (1st digit)**: Increment for breaking changes
  - Example: 2.1.0 → 3.0.0
  - Use cases: Breaking API changes, major architecture overhauls
  - Reset MINOR and PATCH to 0 when incrementing MAJOR

### **When to Update Version**

- ✅ **ALWAYS update version** when merging PRs with code changes
- ✅ **Update version in commit message** for tarball updates
- ❌ **DO NOT update version** for documentation-only changes (unless significant)
- ❌ **DO NOT update version** for test-only changes

### **CRITICAL: Version Increment Confirmation**

- 🚨 **ALWAYS ASK USER** before incrementing MINOR (2nd digit) or MAJOR (1st digit)
- ✅ **PATCH increments (3rd digit)** can be done without asking
- ❌ **NEVER assume** a change is a "new feature" without user confirmation

**Examples of what is NOT a new feature:**
- Refactoring existing functionality (e.g., hardcoded → config-driven)
- Performance improvements without new capabilities
- Internal architecture changes that don't add user-facing features
- Bug fixes, even significant ones

**Examples of what IS a new feature (ask user first):**
- New command-line flags or parameters
- New workflow capabilities (e.g., auto-recovery, instance control)
- New execution types or major subsystems

### **Current Version Location**

Version number is currently tracked in:
- Tarball filename: `tasker-v{MAJOR}.{MINOR}.tar.gz` (e.g., `tasker-v2.1.tar.gz`)
- Git commit messages when updating tarball
- Future: May be added to tasker.py `--version` output

---

## 🚨 CRITICAL COMPATIBILITY REQUIREMENTS 🚨

### **Python 3.6.8 ONLY - No features from 3.7+ allowed**

**❌ FORBIDDEN (Python 3.7+ only):**
- `subprocess.run(capture_output=True, text=True)` - `capture_output` added in 3.7
- `subprocess.run(text=True)` - `text` parameter added in 3.7
- f-string `=` specifier: `f"{var=}"` - added in 3.8
- `dict.values()` with walrus operator `:=` - added in 3.8

**✅ REQUIRED (Python 3.6.8 compatible):**
- `subprocess.Popen()` with `universal_newlines=True` for text mode
- `process.communicate(timeout=X)` for output capture with timeout
- Manual `process.returncode` checking instead of `subprocess.run().returncode`
- Use `with subprocess.Popen(...) as process:` for proper resource management

**Example - CORRECT Python 3.6.8 pattern:**
```python
with subprocess.Popen(['command'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True) as process:
    try:
        stdout, stderr = process.communicate(timeout=10)
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
```

### **Dependencies**
- **Python 3.6.8 or higher** (but use ONLY 3.6.8 compatible features)
- **PyYAML** - Required for execution type configuration (install: `pip install pyyaml`)
- **Standard library modules** - All other functionality uses stdlib only

---

## 🔧 EXECUTION TYPE CONFIGURATION (Config-Based Architecture)

### **CRITICAL: Only exec=local is Hardcoded**

**New Architecture (November 2025):**
- **exec=local**: ONLY hardcoded execution type (direct subprocess execution)
- **All other execution types**: Defined in `cfg/execution_types.yaml`
  - exec=shell (platform-specific: /bin/bash on Linux, cmd.exe on Windows)
  - exec=pbrun (PowerBroker remote execution)
  - exec=p7s (P7S remote execution)
  - exec=wwrs (WWRS remote execution via wwrs_clir)
  - Custom execution types can be added via config

### **CRITICAL: Config File Resolution (Symlink Support)**

**🚨 MANDATORY: Config file MUST be found relative to tasker.py, even when run via symlink**

**Implementation Requirements:**
1. **Use `shutil.which()`** to find script in PATH if `sys.argv[0]` is not absolute
2. **Use `os.path.realpath()`** to resolve symlinks to actual file location
3. **Search for config** in `<real_tasker_dir>/cfg/execution_types.yaml`

**Why This Matters:**
- In production, `tasker` is often a symlink in PATH (e.g., `/usr/local/bin/tasker` → `/app/COOL/tasker2/tasker.py`)
- Running `tasker task.txt` sets `sys.argv[0]` to just `tasker` (no path)
- Without proper resolution, config is searched in wrong location (current directory)
- Results in "ERROR: Execution types not found in configuration"

**Correct Implementation Pattern:**
```python
import shutil
import os

script_name = sys.argv[0]

# If not absolute, find in PATH
if not os.path.isabs(script_name):
    found_path = shutil.which(script_name)
    if found_path:
        script_name = found_path

# Resolve symlinks to real location
script_path = os.path.realpath(script_name)
script_dir = os.path.dirname(script_path)
config_path = os.path.join(script_dir, 'cfg', 'execution_types.yaml')
```

**❌ WRONG (does not work with symlinks in PATH):**
```python
script_path = os.path.realpath(sys.argv[0])  # Fails if sys.argv[0] = 'tasker'
```

### **Config File Location Priority**

1. **Same directory as tasker.py**: `<tasker_dir>/cfg/execution_types.yaml`
   - Resolves symlinks to find real script location
   - Example: `/home/baste/tasker/cfg/execution_types.yaml`
2. **Current working directory**: `./cfg/execution_types.yaml`

### **Config File Structure**

```yaml
platforms:
  linux:
    shell:
      binary: /bin/bash
      command_template:
        - "{binary}"
        - "-c"
        - "{command} {arguments}"
      validation_test: null  # No remote validation needed

    pbrun:
      binary: pbrun
      command_template:
        - "{binary}"
        - "-n"
        - "-h"
        - "{hostname}"
        - "{command}"
        - "{arguments_split}"
      validation_test:
        command: pbtest
        expected_exit: 0
        expected_output: "OK"

aliases:
  bash: shell
  sh: shell
  "/bin/bash": shell
  "/bin/sh": shell
```

### **Template Variables**

- `{binary}` - Executable binary name
- `{hostname}` - Target hostname from task definition
- `{command}` - Command from task definition
- `{arguments}` - Arguments as a single string
- `{arguments_split}` - Arguments split into array using shlex.split()

### **Validation Tests**

Each execution type can define optional validation tests:
- `command`: Test command to execute (e.g., "pbtest", "wwrs_test")
- `expected_exit`: Expected exit code (typically 0)
- `expected_output`: String that must appear in stdout (e.g., "OK")

### **NO Hardcoded Fallbacks**

**CRITICAL RULE**: No hardcoded fallbacks exist in the code. If an execution type is not defined in the config file, TASKER will fail with a clear error message.

**Benefits**:
- Config file ensures all execution types work exactly as before
- Adding new execution types requires only YAML changes
- Platform-specific execution types supported (Linux/Windows)
- Test cases validate that config-based execution matches historical behavior

### **Error Handling**

- **Missing config file**: Only exec=local will work
- **Unconfigured exec type**: Clear error with config file location
- **Missing binary**: Validation failure during host validation phase
- **Failed connectivity test**: Clear error with test details

---

## Claude Code Instructions

### Working Methodology
- **Break down large tasks** into smaller, manageable sub-steps
- **Ask clarifying questions** when requirements are unclear or ambiguous
- **Think step-by-step** and explain reasoning for complex problems
- **Propose solution approaches** and ask for approval before implementation
- **Use concrete examples** to demonstrate solution approaches with pros and cons
- **Explain the thought process** in feedback and highlight problems and opportunities
- **Consult the knowledge repository** (this CLAUDE.md file) regularly to consider all information

### Code Quality Guidelines
- **Comment Policy for Task Files**:
  - ✅ **ALLOWED**: Full-line comments starting with `#` at the beginning of lines
  - ❌ **FORBIDDEN**: Inline comments after `key=value` pairs (e.g., `hostname=localhost # comment`)
  - **Rationale**: Inline comments after field definitions can cause parsing errors and security validation issues
  - **Example**:
    ```bash
    # This is allowed - full line comment
    task=0
    hostname=localhost
    # Another allowed comment
    command=echo
    arguments=test  # THIS IS NOT ALLOWED - inline comment
    ```
- **Use ASCII-safe character set only** (avoid special Unicode characters)
- Maintain existing code style and conventions
- Preserve all existing functionality during refactoring
- Test thoroughly after each change

### **CRITICAL: Localhost Execution - No Validation Required**

**🚨 IMPORTANT: Document this correctly in all documentation!**

**Localhost Always Works Without Flags:**
- `exec=local` has `hostname=localhost` as the **default** value
- Localhost execution **NEVER** requires `--skip-host-validation`
- Host validation is automatically skipped for localhost
- This is a **built-in behavior**, not a configuration requirement

**Incorrect Documentation Examples to AVOID:**
```bash
# ❌ WRONG - This comment is misleading
--skip-host-validation # Required for localhost execution

# ❌ WRONG - Localhost doesn't need this flag
python3 tasker.py workflow.txt --skip-host-validation  # For localhost
```

**Correct Documentation Examples:**
```bash
# ✅ CORRECT - Localhost works by default
task=1
exec=local
# hostname=localhost is implicit (default value)
command=echo
arguments=test

# ✅ CORRECT - Explicit localhost (optional, same as default)
task=1
exec=local
hostname=localhost
command=echo
arguments=test

# ✅ CORRECT - Use --skip-host-validation only for remote hosts without validation
task=1
exec=pbrun
hostname=remote-server  # This might need --skip-host-validation if not in validation config
command=echo
arguments=test
```

**When --skip-host-validation IS Actually Needed:**
- For **remote** hosts that are not defined in validation tests
- For **remote** execution types (pbrun, p7s, wwrs) without validation config
- **NEVER** for localhost or exec=local

**Claude Code Enforcement:**
- ✅ **ALWAYS** document that localhost works without flags
- ✅ **NEVER** suggest --skip-host-validation is required for localhost
- ✅ **CORRECT** any documentation that implies localhost needs this flag
- ❌ **NEVER** add misleading comments about localhost requiring validation skip

### **CRITICAL: Tarball Creation Security Policy**
**🚨 MANDATORY: Never include sensitive or development-only files in distribution tarballs!**

**⚠️ SECURITY INCIDENT:** In October 2025, sensitive data from `.claude/` directory was accidentally included in `tasker-v2.1.tar.gz` and pushed to GitHub. This required complete git history rewrite to remove the sensitive data.

**CRITICAL RULE:** Distribution tarballs MUST NEVER include files that are excluded by `.gitignore` or development-only files.

**Required Tarball Creation Command:**
```bash
cd /home/baste
tar -czf tasker-v2.1.tar.gz \
  --exclude="*.pyc" \
  --exclude="__pycache__" \
  --exclude=".git" \
  --exclude=".gitignore" \
  --exclude="*.log" \
  --exclude="tasker-v2.1.tar.gz" \
  --exclude=".claude/" \
  --exclude="IMPROVEMENT_ROADMAP.md" \
  --exclude="code_review" \
  --exclude=".python-version" \
  --exclude="README.md.backup_*" \
  --exclude=".coderabbit.yaml" \
  --exclude="tasker.py.backup_*" \
  --exclude=".claude.json" \
  --exclude=".claude" \
  --exclude=".markdownlint.json" \
  tasker/
```

**Exclusion Categories:**

1. **CRITICAL - Sensitive Data (NEVER INCLUDE):**
   - `.claude/` - Contains Claude Code working files and potentially sensitive data
   - `.env` - Environment variables and secrets
   - `*.pem`, `*.key` - Private keys and certificates
   - `credentials.json` - API keys and authentication tokens

2. **Development Artifacts (NEVER INCLUDE):**
   - `.coderabbit.yaml` - CodeRabbit configuration
   - `.claude.json` - Claude configuration
   - `.python-version` - Python version management
   - `.markdownlint.json` - Linting configuration
   - `IMPROVEMENT_ROADMAP.md` - Internal planning documents
   - `code_review/` - Code review artifacts
   - `*.backup`, `*.backup_*` - Backup files (e.g., `tasker.py.backup_20251025_111241`)
   - `README.md.backup_*` - Documentation backups

3. **Compiled/Generated Files (NEVER INCLUDE):**
   - `*.pyc` - Python compiled bytecode
   - `__pycache__/` - Python cache directories
   - `*.log` - Log files

4. **Version Control (NEVER INCLUDE):**
   - `.git/` - Git repository data
   - `.gitignore` - Git ignore rules

**Verification Steps:**

1. **Before creating tarball:**
   ```bash
   # Review .gitignore for excluded files
   cat .gitignore

   # Check for sensitive files
   find . -name ".claude" -o -name "*.key" -o -name "*.pem" -o -name ".env"
   ```

2. **After creating tarball:**
   ```bash
   # Verify exclusions worked
   tar -tzf tasker-v2.1.tar.gz | grep -E "\.pyc$|__pycache__|\.claude/|IMPROVEMENT_ROADMAP|code_review/|\.python-version|\.coderabbit|\.markdownlint\.json"

   # Should return NO matches (empty output)

   # Verify file count and size
   tar -tzf tasker-v2.1.tar.gz | wc -l  # Should be ~512 files
   ls -lh tasker-v2.1.tar.gz              # Should be ~383K
   ```

3. **Check what's included:**
   ```bash
   # List first 50 files
   tar -tzf tasker-v2.1.tar.gz | head -50

   # Verify main components present
   tar -tzf tasker-v2.1.tar.gz | grep -E "^tasker/README.md$|^tasker/vtps$|^tasker/tasker/"
   ```

**Emergency Response - If Sensitive Data is Committed:**

If sensitive data is accidentally included and pushed to GitHub:

1. **DO NOT just commit a new tarball** - The old version remains in git history
2. **Use git-filter-repo to purge history:**
   ```bash
   # Download tool
   cd /tmp
   wget https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo
   chmod +x git-filter-repo

   # Backup clean tarball
   cp /home/baste/tasker/tasker-v2.1.tar.gz /home/baste/tasker-v2.1.tar.gz.backup

   # Remove ALL tarball history
   cd /home/baste/tasker
   /tmp/git-filter-repo --invert-paths --path tasker-v2.1.tar.gz --force

   # Restore remotes (filter-repo removes them)
   git remote add origin git@github.com:bastelbude1/Tasker.git
   git remote add gitea git@192.168.188.73:bastelbude/Tasker.git

   # Add clean tarball back
   cp /home/baste/tasker-v2.1.tar.gz.backup tasker-v2.1.tar.gz
   git add tasker-v2.1.tar.gz
   git commit -m "chore: Add clean distribution tarball (v2.1)"

   # Force push to overwrite remote history
   git push --force-with-lease origin <branch-name>
   ```

3. **Rotate compromised credentials immediately**
4. **Notify team members to reset their local branches**

**Claude Code Enforcement:**
- ✅ **ALWAYS** verify exclusion list before creating tarball
- ✅ **ALWAYS** verify tarball contents after creation
- ✅ **NEVER** include files matching `.gitignore` patterns
- ✅ **NEVER** include development-only configuration files
- ✅ **NEVER** include backup files or sensitive data
- ❌ **NEVER** commit tarball without verification
- ❌ **NEVER** assume old tarball was created correctly - always verify

### **CRITICAL: Backup Policy**
**🚨 MANDATORY: Always create backups before ANY code changes!**

```bash
# Before making changes, ALWAYS backup working files:
cp file.py file.py.backup
cp tasker.py tasker.py.backup_YYYYMMDD
```

- **Purpose**: Enables instant rollback to last known working version
- **When**: Before every refactoring, feature addition, or bug fix
- **Critical files**: tasker.py, all validation modules, test scripts
- **Rollback command**: `cp file.py.backup file.py` (instant restore)

### **CRITICAL: 1:1 Code Copy Policy**
- **ALWAYS copy code 1:1** from `tasker.py` into the corresponding module
- **MINIMIZE changes** to only what is absolutely necessary for the module move:
  - Convert instance methods to static methods
  - Change `self.method()` calls to parameter passing
  - Update `self.debug_log` to `debug_callback` parameter
  - Update `self.log` to `log_callback` parameter
- **NEVER modify logic, conditions, or algorithms** during the move
- **Use `tasker_orig.py` for verification** - compare outputs after each phase
- **If behavior differs from original**, revert and copy 1:1 again

### **MANDATORY: Verification Testing Protocol**
**BEFORE pushing any code changes, ALWAYS perform this verification:**

**🎯 CRITICAL PROTOCOL - METADATA-DRIVEN VERIFICATION (ZERO TOLERANCE)**

1. **Run the intelligent test runner:**
   ```bash
   cd test_cases/
   python3 scripts/intelligent_test_runner.py functional/ edge_cases/ integration/ security/
   ```
   - **Metadata-driven validation:** Validates execution paths, variable states, exit codes, and success criteria
   - **CRITICAL:** Detects Python exceptions, validates expected behavior, verifies execution flow
   - **Advanced validation:** Beyond exit codes - checks execution paths, variable resolution, performance metrics
   - **All tests must pass:** 100% success rate required (0 failures, 0 skips)
   - **Key protection:** Prevents false positives through comprehensive behavioral validation

2. **Test execution features:**
   ```bash
   # Validates:
   - Exit codes match expected values
   - Execution paths follow expected task flow
   - Variables resolve to expected values
   - Performance within acceptable benchmarks
   - Security tests properly rejected

   # Automatically:
   - Sets PATH for mock commands
   - Skips host validation when metadata specifies
   - Handles timeout tests appropriately
   - Provides detailed failure diagnostics
   ```

3. **CRITICAL Verification logic (ZERO TOLERANCE):**
   - ❌ **Python exceptions = IMMEDIATE FAILURE:** Any Traceback, AttributeError, Exception detected
   - ❌ **Execution path mismatch = FAILURE:** Tasks executed must match expected_execution_path
   - ❌ **Variable mismatch = FAILURE:** Variables must match expected values (if specified)
   - ❌ **Exit code mismatch = FAILURE:** Exit code must match expected_exit_code
   - ✅ **Metadata validation:** All tests must have valid TEST_METADATA
   - ✅ **Behavioral validation:** Execution behavior must match metadata expectations

4. **CRITICAL Success criteria (ZERO TOLERANCE):**
   - **100% pass rate required** (0 failures, 0 skips)
   - **ALL tests must have TEST_METADATA** (no skipped tests due to missing metadata)
   - **Execution paths must match expectations** (validates task flow control)
   - **Variables must resolve correctly** (validates variable substitution)
   - **Performance within benchmarks** (for performance tests)
   - **Security tests properly rejected** (validates security hardening)

**CRITICAL IMPROVEMENT:** Intelligent test runner validates BEHAVIOR not just exit codes. Catches execution path errors, variable resolution issues, and performance regressions that basic exit code testing misses.

### Communication Style
- Provide detailed explanations of reasoning
- Present multiple solution options when applicable
- Highlight potential risks and benefits
- Ask for confirmation on major architectural decisions
- Document decisions and rationale

---

## 🔒 Workflow Instance Control (Production Safety)

### Overview

Workflow Instance Control prevents accidental concurrent execution of identical workflows, addressing critical production disasters like duplicate deployments and database migrations.

**Feature Status:** ✅ Implemented (TASKER 2.1+)

**Key Capability:** Hash-based locking prevents multiple instances of the same workflow from running simultaneously.

### When to Recommend --instance-check

**CRITICAL USE CASES (Always Recommend):**
- ✅ Production deployments
- ✅ Database migrations / schema changes
- ✅ Configuration updates across server fleets
- ✅ Critical one-at-a-time operations
- ✅ Workflows that modify shared resources (databases, files, ports)
- ✅ Long-running workflows where accidental restart would cause conflicts

#### Example Scenarios

```bash
# Deployment workflow - MUST use instance control
$ tasker -r --instance-check deployment.txt

# Database migration - MUST use instance control
$ tasker -r --instance-check migrate_db.txt

# Server configuration update - RECOMMENDED
$ tasker -r --instance-check update_configs.txt
```

### How It Works

**Hash Calculation:**
- Components: SHA-256(task_file_content + sorted(expanded_global_vars))
- Different env vars = different hashes = different instances (parallel allowed)
- Same file + same env vars = same hash = blocked

**Lock Files:**
- Location: `~/TASKER/locks/workflow_{hash}.lock`
- Format: JSON with PID, timestamp, hostname, global vars snapshot
- Cleanup: Automatic detection and removal of stale locks (crashed processes)

**Bypass Conditions:**
- `--validate-only`: Never creates locks (validation anytime)
- `--force-instance`: Emergency override for stuck locks

**Lock Acquisition During Recovery:**
- `--auto-recovery resume`: Still acquires lock (prevents duplicate recovery attempts and cleans up stale locks)

### Usage Guidelines for Claude Code

#### 1. Proactive Recommendation

When users create deployment/migration workflows, ALWAYS recommend:


```bash
# Add to task file header
--instance-check

# Or recommend CLI usage
tasker -r --instance-check workflow.txt
```

#### 2. File-Defined Arguments (Recommended Approach)


```bash
# At top of critical workflow files
--instance-check

# Global variables
DEPLOY_ENV=$ENVIRONMENT

# Tasks...
```

#### 3. Emergency Override (Only When Needed)


```bash
# If lock is stuck (process crashed but lock remains)
tasker -r --instance-check --force-instance deployment.txt
```

### Testing Requirements

New workflows with instance control MUST include test case:


```bash
# TEST_METADATA: {"description": "Workflow with instance control", "test_type": "positive", "expected_exit_code": 0, "expected_success": true}
--instance-check

# Test that workflow runs successfully with instance control
task=0
hostname=localhost
exec=local
command=echo
arguments=Testing instance control
```

### Edge Cases and Behaviors

#### 1. Different Environment Variables = Different Instances (Allowed)


```bash
# These create DIFFERENT hashes (parallel execution allowed)
$ ENV=prod tasker -r --instance-check deploy.txt &
$ ENV=dev tasker -r --instance-check deploy.txt &
```

#### 2. Same Workflow = Blocked


```bash
# Second execution is blocked
$ tasker -r --instance-check deploy.txt &
$ tasker -r --instance-check deploy.txt
ERROR: Workflow instance already running!
```

#### 3. Validation Never Blocks


```bash
# Validation can run anytime (no lock created)
$ tasker --validate-only --instance-check deploy.txt
```

#### 4. Recovery Continuation Still Acquires Lock


```bash
# Auto-recovery resume still acquires lock (prevents duplicate recovery)
$ tasker -r --auto-recovery --instance-check deploy.txt
# [workflow fails mid-execution]
$ tasker -r --auto-recovery --instance-check deploy.txt
# Acquires lock before resuming (prevents accidental duplicate recovery attempts)
```

### Error Messages and User Guidance

When workflow is blocked:

```bash
ERROR: Workflow instance already running!
  Task file: /path/to/deployment.txt
  Started: 2025-11-11T19:10:45.123456
  PID: 12345
  Hostname: server01
  Lock file: ~/TASKER/locks/workflow_abc123def456.lock

To override instance check, use: --force-instance
```

Claude Code Response:


- Explain the safety mechanism is working correctly
- Advise user to wait for first instance to complete
- If stuck lock suspected: Recommend `--force-instance` after verifying process is dead
- If intentional parallel execution needed: Explain env var differentiation

### Implementation Details (For Reference)

#### Files Modified


- `tasker.py`: CLI flags (`--instance-check`, `--force-instance`)
- `tasker/core/task_executor_main.py`: Core logic (section 7.5)

#### Key Methods


- `_calculate_workflow_instance_hash()`: Hash file + global vars
- `_acquire_instance_lock()`: Atomic lock with fcntl.flock
- `_is_lock_stale()`: Detect crashed process via PID check
- `_release_instance_lock()`: Cleanup on exit

#### Design Decisions


- Opt-in via `--instance-check` flag (non-breaking default)
- Project name excluded from hash (safer - blocks all duplicates)
- Abort immediately on duplicate (exit code 25 - INSTANCE_ALREADY_RUNNING)
- Lock acquired during auto-recovery resume (prevents duplicate recovery attempts, cleans up stale locks)

---

## 🧪 MANDATORY: Test Case Metadata Standard

### **CRITICAL: All Test Cases Must Include TEST_METADATA**
**🚨 MANDATORY for Claude Code: Every test case MUST have metadata for intelligent validation**

- **REQUIRED for new test cases**: Every new .txt test file MUST include TEST_METADATA comment
- **REQUIRED for modified test cases**: When editing existing test cases, MUST add metadata
- **REQUIRED tool**: Use `intelligent_test_runner.py` instead of basic exit code validation
- **Format**: `# TEST_METADATA: {"description": "...", "test_type": "...", ...}`

### **Required Metadata Fields**
```json
{
  "description": "Clear description of what the test validates",
  "test_type": "positive|negative|validation_only|security_negative|performance",
  "expected_exit_code": 0,
  "expected_success": true
}
```

### **Test Type Guidelines**
- **positive**: Normal successful workflow tests (exit_code: 0, success: true)
- **negative**: Tests that should fail validation or execution (exit_code: non-zero, success: false)
- **validation_only**: Tests run with --validate-only flag (quick validation)
- **security_negative**: Security tests that should be rejected (exit_code: 20, success: false)
- **performance**: Performance benchmark tests with timing/resource requirements

### **Standard Metadata Examples**
```bash
# Basic positive test
# TEST_METADATA: {"description": "Simple echo workflow", "test_type": "positive", "expected_exit_code": 0, "expected_success": true}

# Negative validation test
# TEST_METADATA: {"description": "Invalid parameter test", "test_type": "negative", "expected_exit_code": 20, "expected_success": false}

# Security test
# TEST_METADATA: {"description": "Command injection attempt", "test_type": "security_negative", "expected_exit_code": 20, "expected_success": false, "security_category": "command_injection", "risk_level": "high"}
```

### **Advanced Metadata Fields (Optional)**
- **expected_execution_path**: Array of task IDs that should execute
- **expected_skipped_tasks**: Array of task IDs that should be skipped
- **expected_final_task**: Final task ID that should complete
- **expected_variables**: Object with variable name/value pairs
- **timeout_expected**: Boolean if timeout is expected
- **performance_benchmarks**: Object with timing/resource limits
- **security_category**: For security tests (command_injection, path_traversal, etc.)
- **risk_level**: For security tests (low, medium, high, critical)

### **Claude Code Enforcement Protocol**
1. **When creating ANY test case**: Claude MUST add appropriate TEST_METADATA
2. **When modifying ANY existing test case**: Claude MUST add missing metadata
3. **Reference examples**: Use `test_cases/functional/metadata_example_test.txt` for formatting
4. **Validation tool**: Use `test_cases/scripts/intelligent_test_runner.py` for testing
5. **Template location**: Use templates in `test_cases/templates/` directory

### **Migration Priority**
- **Phase 1**: All functional tests and new test cases
- **Phase 2**: Integration and edge case tests
- **Phase 3**: Specialized and security tests

---

## 🔄 FUTURE FEATURE REQUESTS

### Global Variable Updates During Execution
**Current Limitation**: Global variables are read-only during workflow execution and cannot be modified by tasks.

**Proposed Enhancement**: Allow tasks to update global variables during runtime using `type=update_global` blocks.

**Proposed Implementation**:
```bash
# Pre-declare globals (required by default validation)
DEPLOYMENT_TARGET=localhost
APP_VERSION=1.0.0

# Update global variables (always sequential execution)
task=1
type=update_global
set_DEPLOYMENT_TARGET=@0_stdout@
set_APP_VERSION=@0_stdout@
condition=@0_success@=true

# Use updated global variables
task=2
hostname=@DEPLOYMENT_TARGET@
command=deploy
arguments=--version=@APP_VERSION@
```

### Logical Parameter Validation
**Current Limitation**: TASKER does not prevent illogical parameter combinations.

**Proposed Enhancement**: Add logical validation that detects and warns about conflicting parameter combinations:
- `loop=N` with `on_success` when success condition is achievable on first attempt
- `retry_failed=true` with `success=exit_1` (will never retry since exit_1 is defined as success)
- `timeout=0` or negative timeout values
- `max_parallel=0` or exceeding reasonable limits

### Unconditional Flow Control (goto Parameter)
**Current Limitation**: Flow control depends on task success/failure state, requiring complex combinations of `on_success` and `on_failure` to achieve unconditional jumps.

**Proposed Enhancement**: Add `goto` parameter for unconditional task routing:
```bash
# Proposed syntax (NOT currently supported)
task=10
hostname=app-server
command=deploy_application
# Always jump to task 50, regardless of success/failure
goto=50
```

### JSON and YAML Task File Support
**Current Limitation**: TASKER only supports simple key-value text format for task files.

**Proposed Enhancement**: Support JSON and YAML formats for defining complex workflows with nested structures, arrays, and advanced data types.

---

## 🐛 Critical Bug Fix Archive

### Race Condition in Parallel Sleep Handling (FIXED)
**Issue**: Original `tasker_orig.py` had a race condition where completed tasks could be incorrectly cancelled if they were sleeping when master timeout management ran.

**Root Cause**: Sleep occurred during task execution within the `_execute_task_core` method while futures were still active.

**Fix Applied**: Separated task execution from post-processing - sleep now occurs **after** task completion (outside timeout scope).

**Evidence**: Statistics Verification Test now shows `2/3 tasks succeeded` instead of `1/3 tasks succeeded`.

### KeyError: 2 Loop Counter Regression (FIXED)
**Issue**: KeyError: 2 when accessing loop counters - a regression of a previously fixed issue that reappeared during modular refactoring.

**Root Cause**: Loop counter dictionary access without defensive programming checks, causing KeyError when counters were missing or deleted.

**Fix Applied**: Added comprehensive defensive programming in `task_executor_main.py` with proper initialization checks and graceful handling of missing loop counters.

**Evidence**: `example_task.txt` now executes successfully without KeyError exceptions.

### Critical Workflow Security Issue - Missing Command Execution (FIXED)
**Issue**: When local commands don't exist, TASKER treated "file not found" errors as normal workflow conditions (exit code 1) and continued execution, potentially leading to uncontrolled workflow behavior.

**Root Cause**: No pre-execution validation of command existence and insufficient fatal error detection during runtime.

**Fix Applied**:
1. **Command validation in validation phase**: Added `validate_commands_exist()` method that runs during validation phase alongside task and host validation
2. **Comprehensive execution type support**: Validates local commands (`exec=local`) and remote execution tools (`pbrun`, `p7s`, `wwrs_clir`)
3. **Granular skip control**: Added `--skip-command-validation` flag with warning messages for risky operations
4. **Runtime fatal error detection**: Added backup safety measure in sequential executor to immediately terminate on "No such file or directory" errors

**Evidence**: Missing commands now trigger clear error messages and prevent workflow execution:
```
ERROR: Task 1: Command 'nonexistent_command' not found in PATH
ERROR: # VALIDATION FAILED: Missing commands detected
```

---

*TASKER 2.0 - Professional Task Automation for Enterprise Environments*
