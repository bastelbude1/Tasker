# TASKER TEST_METADATA Specification

This document defines the complete specification for TEST_METADATA in TASKER test cases.

## 📋 Overview

TEST_METADATA is a JSON comment that provides intelligent test validation capabilities beyond simple exit code checking. It enables sophisticated test validation including execution path verification, variable validation, performance benchmarking, and security test validation.

## 🔧 Format

```bash
# TEST_METADATA: {"description": "...", "test_type": "...", ...}
```

- **Location**: First line of test file (recommended)
- **Format**: JSON object in a comment line
- **Prefix**: `# TEST_METADATA:`
- **Encoding**: UTF-8, ASCII-safe characters only

## 📚 Required Fields

### **description** (string)
Clear, concise description of what the test validates.

```json
"description": "Basic sequential workflow with echo and date commands"
```

### **test_type** (string)
Test classification for appropriate validation logic.

**Valid Values:**
- `"positive"` - Normal successful workflow tests
- `"negative"` - Tests that should fail validation or execution
- `"validation_only"` - Tests run with --validate-only flag
- `"security_negative"` - Security tests that should reject malicious input
- `"performance"` - Performance benchmark tests with timing requirements

### **expected_exit_code** (number)
Expected numeric exit code from TASKER execution.

**Common Values:**
- `0` - Success (positive tests)
- `20` - Validation error (negative/security tests)
- `124` - Timeout (timeout tests)

### **expected_success** (boolean)
Boolean indication of whether test should succeed.

```json
"expected_success": true   // For positive tests
"expected_success": false  // For negative/security tests
```

## 🎯 Optional Fields

### **Execution Path Validation**

#### **expected_execution_path** (array)
Array of task IDs that should execute in order.

```json
"expected_execution_path": [0, 1, 3]
```

#### **expected_skipped_tasks** (array)
Array of task IDs that should be skipped.

```json
"expected_skipped_tasks": [2, 4]
```

#### **expected_final_task** (number)
Final task ID that should complete the workflow.

```json
"expected_final_task": 3
```

### **Variable Validation**

#### **expected_variables** (object)
Expected variable values captured during execution.

```json
"expected_variables": {
  "0_stdout": "Hello World",
  "1_stderr": "",
  "2_exit_code": "0"
}
```

### **Output Pattern Validation**

#### **expected_output_patterns** (object)
Patterns that should appear in stdout/stderr.

```json
"expected_output_patterns": {
  "stdout": ["Task 0: Executing", "Hello World"],
  "stderr": ["Warning: deprecated"]
}
```

### **Timeout Validation**

#### **timeout_expected** (boolean)
Whether test should timeout.

```json
"timeout_expected": true
```

### **Validation-Only Tests**

#### **validation_only** (boolean)
Indicates test should run with --validate-only flag.

```json
"validation_only": true
```

## 🔒 Security Test Fields

Required for `"test_type": "security_negative"`

### **security_category** (string)
Type of security vulnerability being tested.

**Valid Values:**
- `"command_injection"` - Shell command injection attempts
- `"path_traversal"` - Directory traversal attempts
- `"buffer_overflow"` - Buffer overflow attempts
- `"format_string"` - Format string attacks
- `"privilege_escalation"` - Privilege escalation attempts
- `"resource_exhaustion"` - Resource exhaustion attacks
- `"malformed_input"` - Malformed input validation
- `"null_injection"` - Null byte injection
- `"code_injection"` - Code injection attempts

### **risk_level** (string)
Severity assessment of the security test.

**Valid Values:**
- `"low"` - Minor security issue
- `"medium"` - Moderate security risk
- `"high"` - Serious security vulnerability
- `"critical"` - Critical security flaw

### **expected_rejection_phase** (string)
Phase where security test should be rejected.

**Valid Values:**
- `"validation"` - During task validation phase
- `"execution"` - During task execution phase

### **expected_error_patterns** (array)
Error patterns that should appear in output.

```json
"expected_error_patterns": [
  "dangerous characters detected",
  "security violation"
]
```

## ⚡ Performance Test Fields

Required for `"test_type": "performance"`

### **performance_benchmarks** (object)
Performance limits that must be met.

#### **max_execution_time** (number)
Maximum allowed execution time in seconds.

```json
"performance_benchmarks": {
  "max_execution_time": 10.0
}
```

#### **max_memory_usage_mb** (number)
Maximum allowed memory usage in megabytes.

```json
"performance_benchmarks": {
  "max_memory_usage_mb": 50
}
```

#### **min_throughput_tasks_per_second** (number)
Minimum required task execution throughput.

```json
"performance_benchmarks": {
  "min_throughput_tasks_per_second": 2.0
}
```

### **resource_limits** (object)
Resource usage thresholds (warnings, not failures).

#### **cpu_threshold_percent** (number)
CPU usage threshold percentage.

```json
"resource_limits": {
  "cpu_threshold_percent": 80
}
```

#### **memory_threshold_mb** (number)
Memory usage threshold in megabytes.

```json
"resource_limits": {
  "memory_threshold_mb": 100
}
```

### **timing_validation** (object)
Individual task timing validation.

#### **expected_task_duration** (object)
Expected duration for specific tasks.

```json
"timing_validation": {
  "expected_task_duration": {
    "0": 1.0,
    "1": 2.5
  }
}
```

#### **max_total_duration** (number)
Maximum total workflow duration.

```json
"timing_validation": {
  "max_total_duration": 15.0
}
```

## 📝 Complete Examples

### Basic Positive Test
```json
{
  "description": "Simple echo workflow",
  "test_type": "positive",
  "expected_exit_code": 0,
  "expected_success": true,
  "expected_execution_path": [0, 1],
  "expected_final_task": 1
}
```

### Negative Validation Test
```json
{
  "description": "Invalid hostname validation test",
  "test_type": "negative",
  "expected_exit_code": 20,
  "expected_success": false
}
```

### Security Test
```json
{
  "description": "Command injection attempt",
  "test_type": "security_negative",
  "expected_exit_code": 20,
  "expected_success": false,
  "security_category": "command_injection",
  "risk_level": "high",
  "expected_rejection_phase": "validation",
  "expected_error_patterns": ["dangerous characters detected"]
}
```

### Performance Test
```json
{
  "description": "Parallel execution performance test",
  "test_type": "performance",
  "expected_exit_code": 0,
  "expected_success": true,
  "performance_benchmarks": {
    "max_execution_time": 10.0,
    "max_memory_usage_mb": 50
  },
  "resource_limits": {
    "cpu_threshold_percent": 80,
    "memory_threshold_mb": 100
  }
}
```

### Advanced Execution Path Test
```json
{
  "description": "Complex flow control with conditional branching",
  "test_type": "positive",
  "expected_exit_code": 0,
  "expected_success": true,
  "expected_execution_path": [0, 1, 3, 5],
  "expected_skipped_tasks": [2, 4],
  "expected_final_task": 5,
  "expected_variables": {
    "0_stdout": "Start",
    "5_stdout": "End"
  }
}
```

## 🚀 Usage with Intelligent Test Runner

```bash
# Run single test
./test_cases/scripts/intelligent_test_runner.py test_cases/functional/my_test.txt

# Run all tests in directory
./test_cases/scripts/intelligent_test_runner.py test_cases/functional/

# Run recursively
./test_cases/scripts/intelligent_test_runner.py test_cases/ --recursive
```

## ✅ Validation Rules

1. **Required Fields**: description, test_type, expected_exit_code, expected_success
2. **Test Type Validation**: Must be one of the valid test_type values
3. **Security Fields**: security_category and risk_level required for security_negative tests
4. **Performance Fields**: performance_benchmarks required for performance tests
5. **JSON Format**: Must be valid JSON syntax
6. **Field Types**: All fields must match expected data types

## 🐛 Common Issues

### Invalid JSON Syntax
```bash
# WRONG - Missing quotes
# TEST_METADATA: {description: Test, test_type: positive}

# CORRECT
# TEST_METADATA: {"description": "Test", "test_type": "positive"}
```

### Missing Required Fields
```bash
# WRONG - Missing required fields
# TEST_METADATA: {"description": "Test"}

# CORRECT
# TEST_METADATA: {"description": "Test", "test_type": "positive", "expected_exit_code": 0, "expected_success": true}
```

### Invalid Test Type
```bash
# WRONG - Invalid test type
# TEST_METADATA: {"test_type": "invalid_type"}

# CORRECT
# TEST_METADATA: {"test_type": "positive"}
```

## 📖 References

- **Templates**: See `test_cases/templates/` for ready-to-use templates
- **Examples**: See `test_cases/functional/metadata_*.txt` for working examples
- **Implementation**: See `test_cases/scripts/intelligent_test_runner.py` for validation logic
- **Guidelines**: See `CLAUDE.md` for Claude Code enforcement policies