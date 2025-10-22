# TASKER Test Cases Documentation

## 📋 Overview

This directory contains a comprehensive test suite for TASKER organized by functionality and purpose. Each test uses **metadata-driven validation** with the `intelligent_test_runner.py` framework, enabling sophisticated behavioral verification beyond simple exit code checking.

## 🗂️ Directory Structure

```
test_cases/
├── functional/          # Core functionality tests (150 tests)
├── edge_cases/         # Boundary conditions and edge cases (80 tests)
├── security/          # Security validation tests (27 tests)
├── integration/       # Multi-component integration tests (33 tests)
├── performance/       # Performance and timing tests (10 tests)
├── recovery/          # Auto-recovery and state persistence tests (8 tests)
├── resume/            # Resume from specific task tests (16 tests)
├── scripts/           # Testing infrastructure and utilities
├── templates/         # Test file templates
├── bin/              # Mock executables for testing
└── README.md          # This documentation

Total: 324 tests with TEST_METADATA
```

## 🎯 Test Categories

### 1. Functional Tests (`functional/`)

Tests that validate core TASKER functionality and ensure all TaskER FlowChart blocks work correctly:

#### 1.1 Basic Execution Blocks
- **Simple Task Execution**: Basic `task`, `hostname`, `command`, `arguments` parameters
- **Global Variables**: Variable definition and resolution with `@VARIABLE@` syntax (17 comprehensive tests)
- **Configuration Overrides**: `timeout`, `exec` parameter handling

#### 1.2 Flow Control Blocks
- **Success Check (next)**: `success`, `next` condition evaluation
- **Success Check (on_success/on_failure)**: Jump-based flow control
- **Sleep Block**: `sleep` parameter with various duration values

#### 1.3 Advanced Execution Blocks
- **Conditional Block**: `type=conditional`, `condition`, `if_true_tasks`, `if_false_tasks`
- **Loop Block**: `loop`, `next=loop`, `loop_break` functionality
- **Parallel Block**: `type=parallel`, `tasks`, `max_parallel` execution

#### 1.4 Enhanced Features
- **Parallel with Retry**: `retry_failed`, `retry_count`, `retry_delay` in parallel tasks
- **Conditional with Retry**: Retry logic in conditional task execution
- **Multi-Task Success Evaluation**: `min_success`, `max_failed`, `all_success`, etc.

#### 1.5 Output Processing
- **Output Split**: `stdout_split`, `stderr_split` with various delimiters
- **Task Result References**: `@taskid_stdout@`, `@taskid_exit@` usage

#### 1.6 Terminal Blocks
- **End Success**: `next=never`, `return=0` workflow termination
- **End Failure**: `return=1-255` error code handling

### 2. Edge Cases (`edge_cases/`)

Tests that validate boundary conditions and unusual but valid scenarios:

#### 2.1 Parameter Boundaries
- **Sleep Values**: Decimal values (0.5), maximum values (300), zero values
- **Loop Limits**: Maximum iterations (100), single iteration, edge cases
- **Timeout Limits**: Minimum (5s), maximum (3600s), edge values
- **Parallel Limits**: Maximum tasks (50), single task, resource constraints

#### 2.2 Flow Control Edge Cases
- **Complex Conditions**: Multi-variable expressions, nested conditions
- **Jump Sequences**: Non-sequential task IDs, forward/backward jumps
- **Task Sequences**: Gaps in task numbering, high starting IDs

#### 2.3 Resource Edge Cases
- **Memory Management**: Large output handling, resource cleanup
- **Environment Variables**: Missing values, empty values, special characters
- **Host Validation**: Various hostname formats, connection edge cases

### 3. Security Tests (`security/`)

Negative testing to ensure TASKER properly rejects malicious or dangerous inputs:

#### 3.1 Command Injection
- **Basic Injection**: Semicolon chaining, pipe operations, command substitution
- **Advanced Injection**: Shell metacharacters, environment manipulation
- **Context-Specific**: Injection in hostname, arguments, global variables

#### 3.2 Path Traversal
- **Basic Traversal**: `../` sequences, Windows path traversal
- **Encoded Traversal**: URL encoding, double encoding, mixed encoding
- **Target Files**: `/etc/passwd`, `/etc/shadow`, Windows system files

#### 3.3 Buffer Overflow
- **Large Inputs**: Extremely long arguments, commands, hostnames
- **Format Strings**: Format string attack patterns (`%s`, `%d`, `%x`, `%n`)
- **Memory Exhaustion**: Resource exhaustion attempts

#### 3.4 Malformed Input
- **Syntax Errors**: Invalid task definitions, malformed parameters
- **Circular Dependencies**: Self-referencing tasks, circular task chains
- **Invalid References**: Undefined global variables, invalid task IDs

#### 3.5 Resource Exhaustion
- **Process Limits**: Excessive parallel tasks, fork bombs
- **Memory Limits**: Large memory allocations, memory leaks
- **File System**: Disk space exhaustion, file descriptor limits

### 4. Recovery Tests (`recovery/`)

Tests that validate auto-recovery and state persistence functionality:

#### 4.1 Auto-Recovery Features
- **Basic Recovery**: Automatic state saving and recovery after failures
- **Global Variables**: Recovery with global variable preservation
- **Cleanup**: Proper cleanup of recovery files on success

#### 4.2 Recovery Scenarios
- **Safe Resume**: Recovery from safe resume points
- **Unsafe Dependencies**: Handling backward dependencies during recovery
- **Basic Failure**: Recovery after task failures

### 5. Resume Tests (`resume/`)

Tests that validate the `--start-from` resume capability:

#### 5.1 Basic Resume
- **From Start**: Resume from task 0 (baseline)
- **From Middle**: Resume from middle of workflow
- **From Last**: Resume from final task only
- **Explicit Zero**: Explicit `--start-from=0`

#### 5.2 Flow Control Resume
- **Before Branch**: Resume with on_success/on_failure routing
- **Into Success Branch**: Resume directly into routing target
- **Into Parallel Block**: Resume from parallel coordinator
- **Into Conditional Block**: Resume from conditional coordinator

#### 5.3 Variable Handling
- **Missing Variables**: Handling missing task variables
- **With Globals**: Resume with global variables
- **Variable Chain**: Variable dependency chains

#### 5.4 Edge Cases
- **Nonexistent Task**: Error handling for invalid task IDs
- **With Skip Validation**: Resume with `--skip-task-validation`
- **With Retry**: Resume with retry configuration
- **With Timeout**: Resume with timeout parameters

### 6. Integration Tests (`integration/`)

Tests that validate interaction between multiple TASKER components:

#### 6.1 Complex Workflows
- **Multi-Stage Pipelines**: Sequential task chains with dependencies
- **Branching Logic**: Complex conditional workflows with multiple paths
- **Parallel Coordination**: Coordinated parallel task execution

#### 6.2 Component Integration
- **Validation + Execution**: Input validation with actual task execution
- **Logging + Output**: Log generation with output processing
- **Host + Security**: Host validation with security checks

#### 6.3 Real-World Scenarios
- **Deployment Workflows**: Application deployment simulation
- **Health Checks**: System monitoring and alerting patterns
- **Data Processing**: ETL-style data transformation workflows

### 7. Performance Tests (`performance/`)

Tests that validate performance characteristics and timing behavior:

#### 7.1 Sleep Tests
- **Basic Sleep**: Simple sleep parameter validation
- **Float Sleep**: Decimal sleep values (0.5, 1.5 seconds)
- **Sleep Range**: Various sleep durations
- **Variable Sleep**: Sleep duration from variables

#### 7.2 Performance Scenarios
- **Parallel Sleep**: Sleep behavior in parallel tasks
- **Conditional Sleep**: Sleep in conditional branches
- **Loop with Sleep**: Sleep inside loop iterations
- **Basic Performance**: General performance benchmarks
- **Stress Testing**: High-load performance testing

## 📋 TEST_METADATA Specification

Every test file includes **TEST_METADATA** for intelligent validation:

```bash
# TEST_METADATA: {"description": "...", "test_type": "...", "expected_exit_code": 0, "expected_success": true}
```

### Required Fields

#### **description** (string)
Clear, concise description of what the test validates.

```json
"description": "Basic sequential workflow with global variables"
```

#### **test_type** (string)
Test classification for appropriate validation logic.

**Valid values:**
- `positive` - Test should succeed (exit code 0)
- `negative` - Test should fail validation/execution (exit code 1-255)
- `validation_only` - Test with `--validate-only` flag
- `security_negative` - Security test that should be rejected (exit code 20)
- `performance` - Performance/timing benchmark test

#### **expected_exit_code** (integer)
Expected exit code from TASKER execution.

```json
"expected_exit_code": 0    // Success
"expected_exit_code": 20   // Validation failure
"expected_exit_code": 124  // Timeout
```

#### **expected_success** (boolean)
Expected overall success status.

```json
"expected_success": true   // Test should pass
"expected_success": false  // Test should fail
```

### Optional Fields

#### **expected_execution_path** (array)
Expected sequence of task IDs that should execute.

```json
"expected_execution_path": [0, 1, 2, 5]
```

#### **expected_variables** (object)
Expected variable values during execution.

```json
"expected_variables": {
  "HOSTNAME": "localhost",
  "BASE_PATH": "/opt/app"
}
```

#### **expected_warnings** (integer)
Number of expected warning messages.

```json
"expected_warnings": 2
```

#### **skip_host_validation** (boolean)
Skip host validation (for tests using invalid/mock hosts).

```json
"skip_host_validation": true
```

#### **security_category** (string)
Security test category (for `security_negative` tests).

```json
"security_category": "command_injection"
"security_category": "path_traversal"
"security_category": "buffer_overflow"
"security_category": "malformed_input"
```

#### **performance_benchmarks** (object)
Performance timing requirements.

```json
"performance_benchmarks": {
  "max_execution_time": 5.0,
  "min_execution_time": 2.0
}
```

### Example Metadata

```bash
# TEST_METADATA: {"description": "Global variable chaining with 3 levels", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0], "expected_variables": {"BASE": "/opt", "CONFIG": "/opt/config"}, "skip_host_validation": true}
```

## 🧪 Test Execution

### Using Intelligent Test Runner (Recommended)

```bash
# Run all test categories with metadata validation
cd test_cases/
python3 scripts/intelligent_test_runner.py functional/ edge_cases/ integration/ security/ performance/ recovery/ resume/

# Run specific category
python3 scripts/intelligent_test_runner.py functional/

# Run with verbose output
python3 scripts/intelligent_test_runner.py functional/ --verbose

# Run specific test pattern
python3 scripts/intelligent_test_runner.py functional/test_global_variables_*.txt
```

### Individual Test Execution

```bash
# Basic execution (skip host validation for mock tests)
../tasker.py functional/test_global_variables_basic.txt -r --skip-host-validation

# Debug mode
../tasker.py functional/test_global_variables_basic.txt -r --skip-host-validation --log-level=DEBUG

# Validation only
../tasker.py functional/test_global_variables_basic.txt --validate-only
```

### Verification Protocol (from CLAUDE.md)

**CRITICAL: Run before any code push:**

```bash
cd test_cases/
python3 scripts/intelligent_test_runner.py functional/ edge_cases/ integration/ security/ performance/ recovery/ resume/
```

**Success criteria:**
- ✅ **100% success rate with ZERO timeouts AND ZERO exceptions**
- Any Python exception = VERIFICATION FAILURE
- All test cases produce functionally identical results

## 📊 Coverage Matrix

| TaskER FlowChart Block | Functional | Edge Cases | Security | Integration |
|------------------------|------------|------------|----------|-------------|
| 1. Execution Block     | ✅ | ✅ | ✅ | ✅ |
| 2. Success Check (next) | ✅ | ✅ | ❌ | ✅ |
| 3. Success Check (jumps) | ✅ | ✅ | ❌ | ✅ |
| 4. Sleep Block         | ✅ | ✅ | ❌ | ✅ |
| 5. Conditional Block   | ✅ | ✅ | ✅ | ✅ |
| 6. Loop Block          | ✅ | ✅ | ❌ | ✅ |
| 7. Parallel Block      | ✅ | ✅ | ✅ | ✅ |
| 8. Parallel with Retry | ✅ | ✅ | ❌ | ✅ |
| 9. Conditional with Retry | ✅ | ✅ | ❌ | ✅ |
| 10.1. Multi-Task (next) | ✅ | ✅ | ❌ | ✅ |
| 10.2. Multi-Task (jumps) | ✅ | ✅ | ❌ | ✅ |
| 11. End Success       | ✅ | ✅ | ❌ | ✅ |
| 12. End Failure       | ✅ | ✅ | ❌ | ✅ |
| 13. Configuration     | ✅ | ✅ | ✅ | ✅ |
| 14. Global Variables  | ✅ | ✅ | ✅ | ✅ |
| 15. Output Processing | ✅ | ✅ | ❌ | ✅ |

**Legend:**
- ✅ = Comprehensive coverage
- ❌ = Not applicable for security testing

## 🎯 Test Naming Convention

Tests follow a structured naming pattern:

```
test_[component]_[scenario].txt

Examples:
- test_global_variables_basic.txt
- test_global_variables_chaining.txt
- test_conditional_block_basic.txt
- test_parallel_block_retry.txt
```

## 🔧 Testing Infrastructure

### Scripts Available

- **`intelligent_test_runner.py`** ⭐ - Main test runner with metadata validation
- **`unit_test_non_blocking_sleep.py`** - Unit tests for non-blocking sleep
- **`generate_success_evaluation_tests.py`** - Generate multi-task success tests
- **`add_missing_metadata.py`** - Add TEST_METADATA to tests missing it
- **`auto_fix_metadata.py`** - Auto-correct metadata based on actual behavior
- **`fix_security_metadata.py`** - Fix security test metadata

### Templates

- **`templates/positive_test_template.txt`** - Template for positive tests
- **`templates/negative_test_template.txt`** - Template for negative tests

## 📈 Quality Metrics

### Success Criteria
- **100% test pass rate** for functional and integration tests
- **100% test fail rate** for security tests (negative testing)
- **Zero false positives** in validation results
- **Complete coverage** of all TaskER FlowChart blocks

### Validation Levels
1. **Exit Code Validation**: Basic pass/fail determination
2. **Metadata Validation**: Verify execution matches TEST_METADATA expectations
3. **Behavioral Validation**: Execution path and variable state verification
4. **Security Validation**: Injection detection and proper rejection
5. **Performance Validation**: Execution timing and resource usage

## 🚀 Contributing New Tests

### 1. Identify Coverage Gaps
- Review coverage matrix above
- Check TaskER FlowChart for untested scenarios
- Consider real-world use cases

### 2. Create Test File
- Use appropriate template from `templates/`
- Follow naming convention
- Use appropriate category directory
- Add comprehensive TEST_METADATA

### 3. Validate Test
```bash
# Run test individually
../tasker.py functional/your_new_test.txt -r --skip-host-validation

# Run with intelligent_test_runner
python3 scripts/intelligent_test_runner.py functional/your_new_test.txt
```

### 4. Verify Metadata
```bash
# Auto-detect correct metadata if uncertain
python3 scripts/auto_fix_metadata.py functional/your_new_test.txt
```

## 📚 Global Variable Testing

The `functional/` directory includes **17 comprehensive global variable tests**:

### Basic Functionality
- `test_global_variables_basic.txt` - Basic global variable definition and usage
- `test_global_variables_chaining.txt` - Variable chaining (@VAR1@ contains @VAR2@)
- `test_global_variables_override.txt` - Task-specific variable overrides

### Advanced Features
- `test_global_variables_circular.txt` - Circular reference handling
- `test_global_variables_conditions.txt` - Variables in condition expressions
- `test_global_variables_edge_cases.txt` - Empty values, special characters
- `test_global_variables_with_blocks.txt` - Variables with parallel/conditional blocks
- `test_global_variables_with_task_results.txt` - Mixing globals with task results

### Validation & Security
- `test_global_variables_reserved_keywords.txt` - Reserved keyword rejection
- `test_global_variables_task_keyword.txt` - 'task' keyword causes parser error
- `test_global_variables_task_fields.txt` - Task field names cause validation errors
- `test_global_variables_safe_names.txt` - Safe names (stdout, stderr, exit)
- `test_global_variables_undefined.txt` - Undefined variable handling
- `test_global_variables_security.txt` - Security validation (command injection)

### Integration
- `test_global_variables_all_fields.txt` - Variables in all task fields
- `test_global_variables_reserved_impact.txt` - Impact analysis of reserved keywords
- `test_global_variables_parent.txt` - Parent-child task variable passing

### Validation Rules
1. **Reserved Keywords**: `task` cannot be used (causes parser crash)
2. **Task Field Names**: Cannot use `hostname`, `command`, `success`, etc. (validation error)
3. **Safe Names**: `stdout`, `stderr`, `exit` are safe (different from `@X_stdout@` pattern)
4. **Variable Expansion**: Max depth of 10 to prevent infinite loops
5. **Parsing Scope**: Global variables only valid BEFORE first `task=` line

## 📚 Related Documentation

- [`../TaskER_FlowChart.md`](../TaskER_FlowChart.md) - Complete workflow block specifications
- [`../CLAUDE.md`](../CLAUDE.md) - Development guidelines and testing requirements
- [`../README.md`](../README.md) - Main TASKER documentation

---

*Last updated: October 22, 2025*
*TASKER Version: 2.1*
*Total Tests: 324 test cases with TEST_METADATA*
*Test Framework: Metadata-driven with intelligent_test_runner.py*
