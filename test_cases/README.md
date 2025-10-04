# TASKER Test Cases Documentation

## 📋 Overview

This directory contains a comprehensive test suite for TASKER organized by functionality and purpose. Each test category validates specific aspects of the TASKER workflow engine, ensuring complete coverage of all TaskER FlowChart blocks.

## 🗂️ Directory Structure

```
test_cases/
├── functional/          # Core functionality tests
├── edge_cases/         # Boundary conditions and edge cases
├── security/          # Security validation tests (negative testing)
├── integration/       # Multi-component integration tests
├── performance/       # Performance and scalability tests (future)
├── README.md         # This documentation
└── [legacy files]    # Original test files (to be organized)
```

## 🔍 Test Categories

### 1. Functional Tests (`functional/`)

Tests that validate core TASKER functionality and ensure all TaskER FlowChart blocks work correctly:

#### 1.1 Basic Execution Blocks
- **Simple Task Execution**: Basic `task`, `hostname`, `command`, `arguments` parameters
- **Global Variables**: Variable definition and resolution with `@VARIABLE@` syntax
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
- **Task Result References**: `@taskid_stdout@`, `@taskid_exit_code@` usage

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
- **Task Sequences**: Gaps in task numbering, duplicate IDs, high starting IDs

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

### 4. Integration Tests (`integration/`)

Tests that validate interaction between multiple TASKER components:

#### 4.1 Complex Workflows
- **Multi-Stage Pipelines**: Sequential task chains with dependencies
- **Branching Logic**: Complex conditional workflows with multiple paths
- **Parallel Coordination**: Coordinated parallel task execution

#### 4.2 Component Integration
- **Validation + Execution**: Input validation with actual task execution
- **Logging + Output**: Log generation with output processing
- **Host + Security**: Host validation with security checks

#### 4.3 Real-World Scenarios
- **Deployment Workflows**: Application deployment simulation
- **Health Checks**: System monitoring and alerting patterns
- **Data Processing**: ETL-style data transformation workflows

#### 4.4 State Management
- **Global State**: Global variable updates during execution
- **Task Dependencies**: Complex task interdependencies
- **Error Recovery**: Error handling and recovery workflows

### 5. Performance Tests (`performance/`) - Future Implementation

Will contain tests for performance validation and scalability:

- **Execution Speed**: Task execution timing benchmarks
- **Memory Usage**: Memory consumption profiling
- **Concurrent Load**: High-concurrency parallel execution
- **Scalability**: Large workflow processing

## 🎯 Test Naming Convention

Tests follow a structured naming pattern for easy identification:

```
[category]_[component]_[scenario]_test.txt

Examples:
- functional_basic_execution_test.txt
- functional_global_variables_test.txt
- edge_cases_sleep_decimal_test.txt
- edge_cases_timeout_maximum_test.txt
- security_command_injection_basic_test.txt
- security_path_traversal_encoding_test.txt
- integration_deployment_workflow_test.txt
- integration_parallel_coordination_test.txt
```

## 📋 Test Specification Format

Each test includes embedded documentation in comments:

```bash
# TEST PURPOSE: Brief description of what this test validates
# EXPECTED BEHAVIOR: What should happen when test runs
# VALIDATION CRITERIA: How to determine if test passed
# FLOWCHART BLOCKS: Which TaskER blocks this test covers
# CATEGORY: functional|edge_cases|security|integration
# COMPLEXITY: simple|moderate|complex

# Test content...
task=1
hostname=localhost
command=echo
arguments=test
```

## 🧪 Test Execution

### Quick Verification
```bash
# Run focused verification on core tests
./focused_verification.sh

# Run specific category
./focused_verification.sh functional/
./focused_verification.sh security/
```

### Comprehensive Validation
```bash
# Run complete system validation
./complete_system_validation.sh

# Run with enhanced validation
./enhanced_test_validator.py
```

### Individual Test Execution
```bash
# Basic execution
../tasker.py functional/simple_execution_test.txt -r --skip-host-validation

# Debug mode
../tasker.py functional/global_variables_test.txt -r --skip-host-validation --log-level=DEBUG
```

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
- 🔄 = Partial coverage (needs improvement)

## 🔧 Test Validation Tools

### 1. Enhanced Test Validator (`enhanced_test_validator.py`)
- Comprehensive behavioral validation beyond exit codes
- Variable resolution verification
- Execution path validation
- Pattern-based regression detection

### 2. Focused Verification (`focused_verification.sh`)
- Quick execution of core test suite
- State cleanup between tests
- Timeout protection (60s per test)
- 100% success rate requirement

### 3. Complete System Validation (`complete_system_validation.sh`)
- Full system testing with enhanced validation
- Standard functionality + security testing
- False positive detection
- Performance validation

### 4. Security Test Runner (`security/security_test_runner.sh`)
- Specialized security test execution
- Negative testing validation (tests should fail)
- Security vulnerability detection
- Injection pattern verification

## 📈 Quality Metrics

### Success Criteria
- **100% test pass rate** for functional and integration tests
- **100% test fail rate** for security tests (negative testing)
- **Zero false positives** in validation results
- **Complete coverage** of all TaskER FlowChart blocks

### Validation Levels
1. **Exit Code Validation**: Basic pass/fail determination
2. **Behavioral Validation**: Output content and execution path verification
3. **Security Validation**: Injection detection and proper rejection
4. **Performance Validation**: Execution timing and resource usage

## 🚀 Contributing New Tests

### 1. Identify Coverage Gaps
- Review coverage matrix above
- Check TaskER FlowChart for untested scenarios
- Consider real-world use cases

### 2. Create Test File
- Follow naming convention
- Include test specification comments
- Use appropriate category directory

### 3. Validate Test
- Run test individually to verify behavior
- Add to focused verification if appropriate
- Test both positive and negative scenarios

### 4. Update Documentation
- Update coverage matrix
- Add test description to appropriate category
- Update any relevant validation tools

## 📚 Related Documentation

- [`TaskER_FlowChart.md`](../TaskER_FlowChart.md) - Complete workflow block specifications
- [`CLAUDE.md`](../CLAUDE.md) - Development guidelines and requirements
- [`COMPREHENSIVE_TESTING_METHODOLOGY.md`](COMPREHENSIVE_TESTING_METHODOLOGY.md) - Testing methodology
- [`security/README.md`](security/README.md) - Security testing guidelines

---

*Last updated: October 2025*
*TASKER Version: 2.0*
*Test Framework Version: 1.0*