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
- **Standard library modules only** - no external dependencies

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

**🎯 CRITICAL PROTOCOL - EXCEPTION-AWARE VERIFICATION (ZERO TOLERANCE)**

1. **Run the comprehensive verification:**
   ```bash
   cd test_cases/
   ./focused_verification.sh
   ```
   - Tests ALL .txt files with `tasker.py` (captures stderr to detect exceptions)
   - **CRITICAL:** Detects Python exceptions (Traceback, AttributeError, etc.) and treats as FAILURE
   - Automatic state file cleanup between tests using `reset_state()` function
   - 60-second timeout per test - **Must achieve 100% success rate with ZERO timeouts AND ZERO exceptions**
   - **Key protection:** Prevents false positives from hidden runtime errors

2. **Test execution requirements:**
   ```bash
   # Essential: Set PATH for mock commands
   PATH="../test_scripts:$PATH"

   # Essential: Skip host validation for testing
   --skip-host-validation

   # Essential: Exclude validation test files designed to fail
   comprehensive_retry_validation_test.txt
   ```

3. **Code review with CodeRabbit (MANDATORY):**
   ```bash
   coderabbit review --prompt-only
   ```
   - **REQUIRED before ANY push to GitHub or Gitea**
   - Performs automated code quality analysis
   - Reviews code changes for best practices, potential issues, and maintainability
   - Must be run on all modified files before git push operations

4. **CRITICAL Verification logic (ZERO TOLERANCE):**
   - ❌ **Python exceptions = IMMEDIATE FAILURE:** Any Traceback, AttributeError, Exception detected in stderr
   - ❌ **Timeouts = IMMEDIATE FAILURE:** Any timeout (exit 124) = immediate failure
   - ✅ **Exit code matching:** `tasker.py` must have valid exit codes (0 for success)
   - ✅ **State consistency:** `reset_state()` ensures each test starts with clean state

5. **CRITICAL Success criteria (ZERO TOLERANCE):**
   - **100% success rate with ZERO timeouts AND ZERO exceptions**
   - **ANY Python exception = VERIFICATION FAILURE** (prevents false positives)
   - All test cases produce functionally identical results
   - **Exception detection:** Captures stderr to detect runtime errors that exit codes miss

**CRITICAL LESSON LEARNED:** Previous verification falsely reported SUCCESS because `> /dev/null 2>&1` hid Python exceptions. The improved verification captures stderr and detects runtime errors, preventing false positives that could break production code.

### Communication Style
- Provide detailed explanations of reasoning
- Present multiple solution options when applicable
- Highlight potential risks and benefits
- Ask for confirmation on major architectural decisions
- Document decisions and rationale

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

### Simplify Retry Configuration
**Current Limitation**: Retry logic requires both `retry_failed=true` AND `retry_count=N` to be set, which is redundant.

**Proposed Enhancement**: Automatically enable retry when `retry_count` is specified:
```bash
# Current (redundant):
retry_failed=true
retry_count=3

# Proposed (simplified):
retry_count=3  # Setting this automatically enables retry
```

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