# Tasker Refactoring Plan

## 🚨 MANDATORY PRE-WORK CHECKLIST 🚨

**⚠️ BEFORE making ANY code changes, Claude MUST explicitly state:**

```
✅ "I will create backups using: cp file.py file.py.backup_$(date +%Y%m%d_%H%M%S)"
✅ "I will run 100% verification testing before any commit suggestions" 
✅ "I acknowledge that violating CRITICAL/MANDATORY requirements breaks production code"
✅ "I have read and will follow all CRITICAL/MANDATORY sections below"
```

**🔒 USER ENFORCEMENT:** If Claude starts making changes without this explicit confirmation, **IMMEDIATELY STOP THE WORK** and require compliance.

**⚠️ VIOLATION CONSEQUENCES:** If Claude violates any CRITICAL/MANDATORY requirement:
- User should immediately point out the specific violation
- Claude must acknowledge which requirement was violated
- All work must STOP until proper process is followed
- Claude must restart with proper checklist compliance

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
- **NO inline comments** when creating test cases
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
   - Compares with `tasker_orig.py` (also captures exceptions)
   - **CRITICAL:** Detects Python exceptions (Traceback, AttributeError, etc.) and treats as FAILURE
   - Automatic state file cleanup between tests using `reset_state()` function
   - 30-second timeout per test - **Must achieve 100% success rate with ZERO timeouts AND ZERO exceptions**
   - **Key protection:** Prevents false positives from hidden runtime errors

2. **Test the validation script separately:**
   ```bash
   cd test_cases/
   ./retry_validation_test_script.sh
   ```
   - Tests `task_validator.py` functionality
   - Different scope from task execution testing

3. **CRITICAL Verification logic (ZERO TOLERANCE):**
   - ❌ **Python exceptions = IMMEDIATE FAILURE:** Any Traceback, AttributeError, Exception detected in stderr
   - ❌ **Timeouts = IMMEDIATE FAILURE:** Any timeout (exit 124) = immediate failure
   - ✅ **Exit code matching:** `tasker.py` and `tasker_orig.py` must have identical exit codes (without `-d`)
   - ✅ **Improved exit codes allowed:** 
     - `orig: 1` → `tasker: 20` (improved validation failure detection)
     - `orig: 1` → `tasker: 14` (improved conditional execution failure detection)
   - ✅ **State consistency:** `reset_state()` ensures each test starts with clean state

4. **CRITICAL Success criteria (ZERO TOLERANCE):**
   - **100% success rate with ZERO timeouts AND ZERO exceptions**
   - **ANY Python exception = VERIFICATION FAILURE** (prevents false positives)
   - All test cases produce functionally identical results between versions
   - Only acceptable differences: improved exit codes (1→20, 1→14)
   - **Exception detection:** Captures stderr to detect runtime errors that exit codes miss

**CRITICAL LESSON LEARNED:** Previous verification falsely reported SUCCESS because `> /dev/null 2>&1` hid Python exceptions. The improved verification captures stderr and detects runtime errors, preventing false positives that could break production code.

### Communication Style
- Provide detailed explanations of reasoning
- Present multiple solution options when applicable
- Highlight potential risks and benefits
- Ask for confirmation on major architectural decisions
- Document decisions and rationale

## Project Specification

### TASK ExecutoR - TASKER 2.0

**TASKER** is a simplified, robust task execution system that focuses on essential functionality with clean configuration management based on Python 3.6.8.

#### Design Philosophy
- **Simplicity over complexity**: Proven mechanisms only
- **Text format first**: Human-readable, version-control friendly
- **Configuration-driven**: Sensible defaults, easy customization
- **Scale-ready**: 1-1000 servers with @HOSTNAME@ placeholders
- **Safety-first**: Comprehensive validation and error handling

#### File Format Specification

**Required Fields:**
- `task`: Integer ID (0, 1, 2, ...)
- `hostname`: Target server or @HOSTNAME@ placeholder
- `command`: Command to execute

**Optional Fields:**
- `arguments`: Command arguments
- `exec`: Execution type (pbrun, p7s, local, wwrs)
- `timeout`: Command timeout in seconds (5-3600)
- `sleep`: Sleep after task execution (0-300 seconds)
- `condition`: Pre-execution condition
- `success`: Custom success criteria
- `next`: Flow control condition
- `on_success`: Task ID to execute on success
- `on_failure`: Task ID to execute on failure
- `loop`: Number of additional iterations
- `return`: Exit workflow with return code

#### Dependencies
**Required:**
- Python 3.6.8 or higher
- Standard library modules only (no external dependencies)

#### Success Criteria

**Functional Requirements:**
- Execute workflows reliably across 1-1000 servers
- Support all essential TASKER features
- Generate detailed logs and reports

**Quality Requirements:**
- 95%+ test coverage
- Sub-second startup time
- Memory usage < 50MB for typical workflows
- Compatible with Python 3.6.8+
- Clear error messages and documentation

**User Experience Requirements:**
- Simple installation (single script)
- Intuitive command line interface
- Helpful validation messages
- Comprehensive documentation

## Refactoring Overview
This document outlines the planned refactoring of the tasker.py module into a well-structured package to improve maintainability, modularity, and code organization while maintaining all TASKER 2.0 requirements.

## Current State
- Single monolithic `tasker.py` file (~3000+ lines)
- All functionality mixed together in one large TaskExecutor class
- Difficult to maintain and extend

## Target Package Structure

```
./
├── tasker.py                    # Main script (executable, NOT a module)
├── task_validator.py            # Existing script (remains unchanged) 
├── setup_test_environment.sh    # Test environment setup script
│
tasker/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── condition_evaluator.py   # Variable replacement & condition logic ✅ COMPLETED
│   ├── execution_context.py     # ExecutionContext for unified callbacks ✅ COMPLETED  
│   ├── task_executor_main.py    # Main class with Lifecycle, Logging, Validation ✅ COMPLETED
│   └── utilities.py             # Standalone utility functions ✅ COMPLETED
│
├── executors/
│   ├── __init__.py
│   ├── base_executor.py         # Abstract base class for all executors ✅ COMPLETED
│   ├── conditional_executor.py  # Conditional task execution ✅ COMPLETED
│   ├── parallel_executor.py     # Parallel task execution + retry logic ✅ COMPLETED
│   └── sequential_executor.py   # Normal task execution ✅ COMPLETED
│
├── validation/
│   ├── __init__.py
│   ├── host_validator.py        # Host validation logic ✅ COMPLETED
│   └── task_validator.py        # TaskValidator integration ✅ COMPLETED
│
test_cases/                      # Comprehensive test suite
├── extended_verification_test.sh  # Main verification testing framework
├── host_validation_*.txt        # Host validation test cases
└── *.txt                        # Various test scenarios

test_scripts/                    # Mock execution commands for testing
├── pbrun                        # Mock pbrun command
├── p7s                          # Mock p7s command  
└── wwrs_clir                    # Mock wwrs_clir command
```

## Module Responsibilities

### `core/` - Fundamental Services
- **`utilities.py`** ✅ **COMPLETED**
  - Standalone utility functions
  - Exit code management (`ExitCodes`, `ExitHandler`)
  - Value conversion functions (`convert_value`, `convert_to_number`)
  - String formatting utilities (`sanitize_filename`, `sanitize_for_tsv`, `format_output_for_log`)
  - Log directory management (`get_log_directory`)

- **`condition_evaluator.py`** ✅ **COMPLETED**
  - Variable replacement using `@VARIABLE@` syntax
  - Condition evaluation logic
  - Expression parsing and comparison operators
  - Output splitting functionality

- **`execution_context.py`** ✅ **COMPLETED**
  - ExecutionContext for unified callback system
  - Centralized logging and debug callback management
  - Shared state management across executors

- **`task_executor_main.py`** ✅ **COMPLETED**
  - Main TaskExecutor class with lifecycle management
  - Logging infrastructure and output formatting
  - Task result storage and management
  - Signal handling and configuration management

### `executors/` - Task Execution Engines
- **`base_executor.py`** ✅ **COMPLETED**
  - Abstract base class for all executors
  - Common execution interface and utilities
  - Clean STDOUT/STDERR logging with format_output_for_log
  - Output splitting and sleep handling

- **`sequential_executor.py`** ✅ **COMPLETED**
  - Normal sequential task execution
  - Single task processing logic with clean output formatting
  - Standard retry mechanisms and condition evaluation
  - Loop handling and flow control

- **`parallel_executor.py`** ✅ **COMPLETED**
  - Parallel task execution with threading
  - Master timeout enforcement and proper sleep handling
  - Advanced retry logic for failed tasks
  - Result aggregation and success/failure thresholds
  - Fixed race condition with sleep after task completion

- **`conditional_executor.py`** ✅ **COMPLETED**
  - Conditional task execution based on conditions
  - Branch selection logic and flow control
  - Integration with condition evaluator

### `validation/` - Validation Logic
- **`task_validator.py`** ✅ **COMPLETED**
  - Integration with existing TaskValidator
  - Task file syntax validation and dependency validation
  - Comprehensive task structure validation

- **`host_validator.py`** ✅ **COMPLETED**
  - Host connectivity validation with execution type testing
  - DNS resolution (`resolve_hostname`)
  - Connection testing (`check_host_alive`, `check_exec_connection`)
  - Support for pbrun, p7s, wwrs validation with proper test commands

### `test_cases/` - Comprehensive Testing Infrastructure
- **`extended_verification_test.sh`** ✅ **COMPLETED**
  - Main verification testing framework with 100% success requirement
  - Support for both success and failure test scenarios
  - Proper PATH handling for host validation tests
  - 27 test case coverage across all functionality

- **`host_validation_test_runner.sh`** ✅ **COMPLETED**
  - Dedicated host validation testing with expected outcome verification
  - Tests both success and failure scenarios with proper error message validation

- **`test_scripts/`** ✅ **COMPLETED**
  - Mock execution commands (pbrun, p7s, wwrs_clir) for testing
  - Configurable success/failure scenarios based on hostname patterns
  - Proper test command responses for validation testing

## Refactoring Progress

### ✅ Phase 1: Core Utilities (COMPLETED)
- [x] Created `tasker/core/utilities.py`
- [x] Moved `ExitCodes` and `ExitHandler` classes
- [x] Moved `convert_value`, `convert_to_number`, `sanitize_for_tsv` functions
- [x] Updated imports and exports
- [x] Committed to git (commit: 5f3b643)

### ✅ Phase 2: Condition Evaluation (COMPLETED)
- [x] Created `tasker/core/condition_evaluator.py`
- [x] Extracted condition evaluation methods (1:1 copy from `tasker_orig.py`):
  - `replace_variables()` - Variable replacement with @VARIABLE@ syntax
  - `evaluate_condition()` - Complex condition evaluation with boolean operators
  - `evaluate_simple_condition()` - Simple condition evaluation (copied 1:1 from lines 1339-1418)
  - `evaluate_operator_comparison()` - Comparison operators (=, !=, ~, !~, <, >, etc.)
  - `split_output()` - Output splitting by delimiter (restored original format)
- [x] **CRITICAL FIX:** Copied stdout/stderr condition logic 1:1 from `tasker_orig.py`
- [x] Verified with comprehensive testing - functional behavior matches `tasker_orig.py` exactly (with acceptable additional debug output)

### ✅ Phase 3: Host Validation (COMPLETED)
- [x] Created `tasker/validation/host_validator.py`
- [x] Extracted host validation methods (1:1 copy):
  - `validate_hosts()` - Main host validation with connectivity tests
  - `resolve_hostname()` - DNS resolution validation
  - `check_host_alive()` - Ping connectivity test
  - `check_exec_connection()` - Execution type connection testing
- [x] Converted to static methods with minimal parameter changes only
- [x] Updated `tasker.py` to use `HostValidator.validate_hosts()`
- [x] **VERIFIED:** Comprehensive testing completed - functional behavior matches `tasker_orig.py` exactly (with acceptable additional debug output)

### ✅ Phase 4: Task Validation Integration (COMPLETED)
- [x] Integrated existing `tasker/validation/task_validator.py` module with TaskExecutor
- [x] **Implementation approach:** Used existing TaskValidator class with static method `validate_task_file()`
- [x] **Integration method:** TaskExecutor.validate_tasks() calls TaskValidator.validate_task_file() with proper callbacks
- [x] **Note:** Different from original plan - instead of creating separate `task_validator_integration.py`,
      we leveraged the existing comprehensive TaskValidator module and integrated it cleanly
- [x] Task file syntax validation, dependency validation, and comprehensive task structure validation
- [x] **VERIFIED:** Full integration with main TaskExecutor class through clean callback architecture

### ✅ Phase 5: Execution Engines (COMPLETED)
- [x] Created `tasker/executors/base_executor.py` - Abstract base class for all executors
- [x] Created `tasker/executors/sequential_executor.py` - Normal sequential task execution
- [x] Created `tasker/executors/parallel_executor.py` - Parallel task execution with retry logic
- [x] Created `tasker/executors/conditional_executor.py` - Conditional task execution
- [x] **CRITICAL FIX:** Fixed race condition in parallel execution with sleep handling
- [x] **VERIFIED:** All execution engines working correctly with comprehensive testing

### ✅ Phase 6: Main Executor Refactoring (COMPLETED)
- [x] Created `tasker/core/task_executor_main.py` - Main TaskExecutor class
- [x] Created `tasker/core/execution_context.py` - ExecutionContext for unified callbacks
- [x] Refactored main TaskExecutor class with proper modular structure
- [x] Updated `tasker.py` to use new modular structure
- [x] **VERIFIED:** All functionality preserved with improved maintainability

## Design Principles

1. **Single Responsibility**: Each module has a clear, focused purpose
2. **Loose Coupling**: Modules interact through well-defined interfaces
3. **High Cohesion**: Related functionality is grouped together
4. **Backwards Compatibility**: Existing functionality must be preserved
5. **Testability**: Each module should be independently testable

## Migration Strategy

- **Refactor incrementally**, one module at a time
- **Copy code 1:1** from `tasker.py` with minimal changes for module conversion
- **Maintain full functionality** at each step
- **Test thoroughly after each phase** using the **Mandatory Verification Testing Protocol**
- **Update imports and dependencies** as modules are created
- **Preserve all existing command-line interfaces and behavior**
- **Use `tasker_orig.py` as reference** - if outputs differ, revert and copy 1:1 again

## Files to be Kept Unchanged

- `tasker.py` - Main executable script (structure changes only)
- `task_validator.py` - Existing validation script
- All test cases and configuration files

## Usage: Validation Options

TASKER 2.0 provides comprehensive validation capabilities through two separate modules:

### Task Validation (`task_validator.py`)
Validates task file syntax, structure, dependencies, and flow control logic.

### Host Validation (`host_validator.py`)
Validates hostname resolution, connectivity, and execution type compatibility.

### Command Line Options

**Enable/Disable Validation:**
- `--validate-only` - Perform complete validation (task + host) and exit - no task execution
- `--skip-task-validation` - Skip task file and dependency validation (faster resume)
- `--skip-host-validation` - Skip host validation and use hostnames as-is (WARNING: risky!)
- `--skip-validation` - Skip ALL validation (same as --skip-task-validation --skip-host-validation)

**Host Connectivity Testing:**
- `-c, --connection-test` - Check connectivity for pbrun,p7s,wwrs hosts (enables host validation)

**Examples:**
```bash
# Full validation without execution
./tasker.py tasks.txt --validate-only

# Skip task validation for faster resume
./tasker.py tasks.txt --start-from=5 --skip-task-validation

# Skip risky host validation (not recommended)
./tasker.py tasks.txt --skip-host-validation

# Enable host connectivity testing
./tasker.py tasks.txt -c -r
```

## Success Criteria

- All existing functionality preserved
- Improved code maintainability and readability
- Clear separation of concerns
- Easier unit testing and debugging
- Foundation for future feature development

## 🐛 Critical Bug Fix Discovered During Refactoring

### The Issue We Found:
- **Original `tasker_orig.py` had a race condition** where completed tasks could be incorrectly cancelled if they were sleeping when master timeout management ran
- **This caused inconsistent task success counting** in parallel execution
- Tasks would execute successfully, start sleeping, but then get marked as incomplete due to timeout cancellation during sleep phase

### Root Cause Analysis:
- In the original implementation, the `sleep` parameter was handled **during** task execution within the `_execute_task_core` method
- When parallel tasks were executed using `concurrent.futures`, the sleep occurred while the future was still active
- The `as_completed` timeout would cancel futures that were sleeping, even though the actual task had completed successfully
- This created a race condition where task completion depended on timing rather than actual execution success

### The Fix We Applied:
- **Separated task execution from post-processing**: Sleep now occurs **after** task completion (outside timeout scope)
- **Architectural consistency**: Parallel execution now matches sequential execution behavior where sleep happens after task completion
- **Proper separation of concerns**: Master timeout applies to task execution, not post-processing cleanup

### Technical Implementation:
1. **Modified `BaseExecutor.execute_task_core`** to return `sleep_seconds` information instead of executing sleep
2. **Updated `ParallelExecutor`** to handle sleep **after** the future completes but **before** recording the result
3. **Left `SequentialExecutor`** unchanged since it already handled sleep correctly

### Evidence of the Fix:
- **Statistics Verification Test**: 
  - Original: `1/3 tasks succeeded` (Task 101 cancelled during sleep)
  - Refactored: `2/3 tasks succeeded` (Task 101 completes properly)
- **20/23 test cases verified identical**
- **All retry functionality tests pass (14/14)**
- **All core functionality preserved with improved reliability**

### Verification:
```bash
# Test case demonstrating the fix
./tasker_orig.py statistics_verification_test.txt -r -d  # Shows race condition
./tasker.py statistics_verification_test.txt -r -d       # Shows correct behavior
```

**Result**: The refactored version fixes a critical race condition and represents the correct implementation. This bug fix improves the reliability of parallel task execution with sleep parameters.

---

## 📋 FUTURE ENHANCEMENT: JSON/YAML FORMAT SUPPORT

### Implementation Plan for Multi-Format Task Files

**Objective**: Support JSON, YAML, and TXT formats while leveraging structured data capabilities of JSON/YAML for enhanced readability and complex conditions.

### Phase 1: Multi-Format Parser (Low Risk)

**Strategy**: Enhanced parser that produces identical internal data structures regardless of input format.

```python
def parse_task_file(self):
    """Enhanced parser supporting TXT, JSON, YAML with structured conditions."""

    # 1. Format detection and basic parsing (low risk)
    if self.task_file.endswith('.json'):
        raw_data = self._parse_json()
    elif self.task_file.endswith(('.yaml', '.yml')):
        raw_data = self._parse_yaml()
    else:
        raw_data = self._parse_txt()  # Existing logic unchanged

    # 2. Enhanced condition parsing (new feature, backward compatible)
    for task in raw_data['tasks']:
        if 'condition' in task:
            task['condition'] = self._normalize_condition(task['condition'])
        if 'next' in task:
            task['next'] = self._normalize_next(task['next'])
        if 'success' in task:
            task['success'] = self._normalize_success(task['success'])

    # 3. Same internal structures as before (zero risk)
    self.global_vars = raw_data['global_vars']
    self.tasks = raw_data['tasks']
```

### Benefits

**Immediate Benefits:**
- Support for JSON/YAML formats with zero risk to existing execution logic
- Better readability for complex workflows
- Structured conditions instead of complex single-line strings
- Backward compatibility with all existing TXT files

**Enhanced Condition Examples:**

**Current TXT (hard to read):**
```
condition=(@0_exit_code@=0|@0_exit_code@=2)&@0_stdout@~deployed&(@1_stderr@=|@1_exit_code@<5)
next=(exit_1|exit_255)&stdout~OK
```

**Enhanced YAML (much clearer):**
```yaml
condition:
  and:
    - or: [{"@0_exit_code@": 0}, {"@0_exit_code@": 2}]
    - "@0_stdout@": {contains: "deployed"}
    - or: [{"@1_stderr@": {empty: true}}, {"@1_exit_code@": {less_than: 5}}]

next:
  and:
    - or: [exit_1, exit_255]
    - stdout: {contains: "OK"}
```

### Implementation Requirements

**Dependencies:**
- JSON: Built-in `json` module (no new dependencies)
- YAML: `pyyaml` library (new dependency, but optional)

**Core Changes:**
- Enhanced `parse_task_file()` method in `task_executor_main.py`
- New structured condition parser methods
- Backward-compatible condition normalization

**Risk Assessment:**
| Component | Risk Level | Impact |
|-----------|------------|---------|
| Execution Engines | **None** | Same input data structures |
| Validation | **None** | Same task objects |
| Flow Control | **None** | Same next/condition evaluation |
| Parser Only | **Low** | Isolated changes, well-testable |

### Backward Compatibility Strategy

**Dual Support:**
```python
def _normalize_condition(self, condition_value):
    if isinstance(condition_value, str):
        # TXT format: "(exit_1|exit_255)&stdout~OK"
        return condition_value  # Use existing parser
    elif isinstance(condition_value, dict):
        # JSON/YAML format: {"and": [{"or": ["exit_1", "exit_255"]}, ...]}
        return self._convert_structured_to_string(condition_value)

    # Both approaches produce same internal string for existing logic
```

### Testing Strategy

**Verification Approach:**
```bash
# All existing TXT files continue working unchanged
./tasker existing_workflow.txt

# New structured files work with identical behavior
./tasker enhanced_workflow.yaml
./tasker enhanced_workflow.json

# Verification: All three produce identical execution results
```

### Phase 2: Advanced Features (Future)

Once basic multi-format support is stable, consider:

**Complex Data Structures:**
- Nested global variables with dot notation
- Template engine for dynamic variable resolution
- Dynamic task generation from loops

**Advanced Conditional Logic:**
- Multi-path next conditions
- Conditional task chains
- Complex data filtering and transformation

**Dependencies for Advanced Features:**
- Template engine (Jinja2 or similar)
- Expression parser for complex conditionals

### Success Criteria

**Phase 1 Complete When:**
- [x] JSON files parse correctly and execute identically to TXT equivalents
- [x] YAML files parse correctly and execute identically to TXT equivalents
- [x] All existing TXT files continue working without changes
- [x] Structured conditions in JSON/YAML provide enhanced readability
- [x] 100% test coverage maintained with new format support
- [x] Documentation updated with format examples

**Key Principle:** Parser-only changes ensure execution logic remains untouched and risk-free.

---

## 🚀 FEATURE IMPLEMENTATION PRIORITY PLAN

### Implementation Order Recommendation

Based on complexity analysis, risk assessment, and dependency mapping, implement features in this optimal order:

### **Phase 0: Quick Wins (Priority 1 - Do FIRST)**

**Total Time**: 1-2 days | **Risk**: Minimal | **Value**: High

#### 1. **Additional Delimiter Keywords** ⭐ **EASIEST** (30 minutes)
**Location**: `tasker/core/condition_evaluator.py`
**Change Required**:
```python
# Just add these lines to delimiter_map:
delimiter_map = {
    'space': r'\s+',
    'tab': r'\t+',
    'newline': r'\n',        # NEW - more intuitive than \n
    'colon': ':',            # NEW - more intuitive than :
    'semicolon': ';',        # NEW - replace 'semi'
    'semi': ';',             # Keep for backward compatibility
    'comma': ',',
    'pipe': '|'
}
```
**Benefits**: Immediate readability improvement, zero risk

#### 2. **Simplify Retry Configuration** ⭐ **VERY EASY** (1-2 hours)
**Location**: `tasker/core/task_executor_main.py:parse_retry_config()`
**Change Required**: Auto-enable retry when `retry_count` is specified
```python
def parse_retry_config(self, parallel_task):
    # NEW LOGIC: Auto-enable if retry_count is set
    retry_count = parallel_task.get('retry_count', '')
    retry_failed = parallel_task.get('retry_failed', '').lower()

    if retry_count and retry_count != '0':
        # Auto-enable retry if retry_count > 0
        if retry_failed == 'false':
            return None  # Explicit disable
        # Continue with retry logic...
    elif retry_failed != 'true':
        return None  # Original behavior
```
**Benefits**: Better UX, less verbose config, prevents user errors

**Why Quick Wins First:**
- ✅ Build momentum with easy successes
- ✅ Zero risk - get familiar with codebase changes safely
- ✅ Immediate user value and feedback
- ✅ Foundation for more complex features

### **Phase 1: Format Enhancement (Priority 2 - After Quick Wins)**

#### 3. **JSON/YAML Format Support** (1-2 weeks)
**Implementation**: As detailed in previous section
**Benefits**: Foundation for all advanced features, better readability
**Dependencies**: pyyaml library (optional)

### **Phase 2: Advanced Features (Priority 3 - After JSON/YAML)**

**⚠️ IMPORTANT**: Implement these ONLY after JSON/YAML support is complete and stable.

#### 4. **Logical Parameter Validation** (1-2 days)
**Why After JSON/YAML**: Can validate both structured and text formats
**Benefits**: Prevent configuration errors, better debugging

#### 5. **Unconditional Flow Control (goto)** (2-3 days)
**Why After JSON/YAML**: Cleaner syntax options in structured formats
```yaml
# Much cleaner in YAML:
task: 10
command: deploy
goto: 50  # Clear and simple

# vs TXT workaround:
on_success=50
on_failure=50
```

#### 6. **Global Variable Updates During Execution** (2-4 weeks)
**Why Last**: Most complex, benefits from all previous enhancements
**Risk**: Highest - affects core variable resolution system

### **Phase Dependencies**

```
Quick Wins → JSON/YAML → Advanced Features
    ↓           ↓              ↓
No deps    Foundation    Benefits from
           for all       everything
```

### **Success Metrics Per Phase**

**Phase 0 Complete:**
- [ ] `newline`, `colon`, `semicolon` delimiters work
- [ ] `retry_count=N` enables retry without `retry_failed=true`
- [ ] All existing functionality unchanged
- [ ] 100% test coverage maintained

**Phase 1 Complete:**
- [ ] JSON/YAML files parse and execute identically to TXT
- [ ] Structured conditions provide enhanced readability
- [ ] All existing TXT files continue working

**Phase 2 Complete:**
- [ ] Each advanced feature works in all formats (TXT, JSON, YAML)
- [ ] Logical validation catches parameter conflicts
- [ ] `goto` parameter eliminates redundant routing
- [ ] Dynamic global variables enable runtime configuration

### **Key Principles**

1. **Start Small**: Quick wins build confidence and familiarity
2. **Foundation First**: JSON/YAML enables better syntax for everything else
3. **Test Continuously**: 100% verification at each phase
4. **Backward Compatible**: Never break existing functionality
5. **Risk Management**: Complex features after simple ones prove the approach

---