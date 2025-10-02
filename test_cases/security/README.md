# TASKER Security Testing Framework

## Overview

This directory contains comprehensive negative security testing for the TASKER 2.0 system. These tests are designed to **intentionally fail** to validate that TASKER properly rejects malicious or malformed inputs.

⚠️ **CRITICAL**: All tests in this directory MUST fail. If any test succeeds, it indicates a potential security vulnerability.

## Test Categories

### 1. Malformed Input Tests (5 files)
Tests invalid task file syntax and structure:

- **malformed_syntax_test.txt** - Missing required fields (hostname)
- **malformed_circular_dependency_test.txt** - Circular task dependencies
- **malformed_invalid_task_ids_test.txt** - Invalid task ID references
- **malformed_empty_fields_test.txt** - Empty required fields
- **malformed_duplicate_task_ids_test.txt** - Duplicate task IDs

### 2. Command Injection Tests (4 files)
Tests command injection attack vectors:

- **command_injection_basic_test.txt** - Basic injection in arguments
- **command_injection_hostname_test.txt** - Injection in hostname field
- **command_injection_command_test.txt** - Injection in command field
- **command_injection_global_vars_test.txt** - Injection via global variables

### 3. Path Traversal Tests (3 files)
Tests directory traversal attack attempts:

- **path_traversal_basic_test.txt** - Basic ../ traversal attempts
- **path_traversal_encoding_test.txt** - URL/Unicode encoded traversal
- **path_traversal_global_vars_test.txt** - Traversal via global variables

### 4. Buffer Overflow Tests (4 files)
Tests buffer overflow and resource exhaustion:

- **buffer_overflow_large_input_test.txt** - Extremely large input fields
- **buffer_overflow_memory_exhaustion_test.txt** - Memory exhaustion via parallel tasks
- **buffer_overflow_format_string_test.txt** - Format string vulnerabilities
- **buffer_overflow_null_bytes_test.txt** - Null byte injection

### 5. Resource Exhaustion Test (1 file)
Tests resource consumption attacks:

- **resource_exhaustion_test.txt** - Excessive timeouts, retries, loops

## Running Security Tests

### Automated Test Runner
```bash
cd test_cases/security/
./security_test_runner.sh
```

The runner will:
- Execute all 17 security test files
- Validate they fail as expected (exit code ≠ 0)
- Report security score (should be 100%)
- Flag any unexpected successes as vulnerabilities

### Manual Testing
```bash
# Set PATH for mock commands and skip host validation
export PATH="../test_scripts:$PATH"

# Run individual test (should fail)
../tasker.py malformed_syntax_test.txt -r --skip-host-validation

# Check exit code (should be non-zero)
echo $?
```

## Expected Behavior

✅ **EXPECTED**: All tests FAIL with non-zero exit codes
❌ **VULNERABILITY**: Any test that succeeds (exit code 0)

### Security Validation Mechanisms

TASKER should reject these attacks through:

1. **Input Validation**: Missing fields, invalid task IDs, empty values
2. **Command Sanitization**: Shell metacharacters, injection attempts
3. **Path Validation**: Directory traversal, encoded paths
4. **Resource Limits**: Memory exhaustion, excessive parallelism
5. **Buffer Protection**: Large inputs, format strings, null bytes

## Test Results Summary

**Current Status**: ✅ 100% Security Score
- Total tests: 17
- Expected failures: 17
- Unexpected successes: 0
- Execution errors: 0

## Integration with CI/CD

Add to your CI pipeline:
```bash
# Security regression testing
cd test_cases/security/
if ! ./security_test_runner.sh; then
    echo "SECURITY REGRESSION DETECTED"
    exit 1
fi
```

## Contributing New Security Tests

When adding new security tests:

1. Follow naming convention: `category_description_test.txt`
2. Document expected failure mode in comments
3. Ensure test intentionally fails
4. Update this README with test description
5. Run `./security_test_runner.sh` to validate

## Security Test Philosophy

These tests follow the principle of **negative testing** - validating that the system correctly rejects invalid/malicious inputs rather than processing them. This approach helps identify security vulnerabilities early and ensures robust input validation throughout the TASKER system.