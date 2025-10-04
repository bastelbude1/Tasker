# TASKER Test Case Templates

This directory contains standardized templates for creating test cases with proper TEST_METADATA.

## 📋 Available Templates

### **positive_test_template.txt** ✅
- **Purpose**: Basic successful workflow tests
- **Exit Code**: 0 (success)
- **Usage**: Copy and modify for normal functionality tests

### **negative_test_template.txt** ❌
- **Purpose**: Tests that should fail validation or execution
- **Exit Code**: 20 (validation error)
- **Usage**: Copy and modify for error condition tests

### **validation_only_template.txt** 🔍
- **Purpose**: Tests run with --validate-only flag
- **Exit Code**: 0 (validation success)
- **Usage**: Copy and modify for quick validation logic tests

### **security_negative_template.txt** 🔒
- **Purpose**: Security tests that should reject malicious input
- **Exit Code**: 20 (security rejection)
- **Required Fields**: security_category, risk_level
- **Usage**: Copy and modify for security vulnerability tests

### **performance_test_template.txt** ⚡
- **Purpose**: Performance benchmark tests
- **Exit Code**: 0 (success)
- **Required Fields**: performance_benchmarks, resource_limits
- **Usage**: Copy and modify for timing and resource usage tests

### **advanced_execution_path_template.txt** 🔀
- **Purpose**: Complex flow control and execution path validation
- **Exit Code**: 0 (success)
- **Required Fields**: expected_execution_path, expected_skipped_tasks
- **Usage**: Copy and modify for flow control tests

## 📝 How to Use Templates

1. **Copy** the appropriate template from this directory
2. **Rename** to descriptive test name (e.g., `user_authentication_test.txt`)
3. **Replace** `DESCRIPTION_HERE` with actual test description
4. **Modify** task definitions to match your test scenario
5. **Update** metadata fields as needed
6. **Validate** with `intelligent_test_runner.py`

## 🔧 Template Customization

### Required Metadata Fields
- `description`: Clear description of test purpose
- `test_type`: One of the supported types
- `expected_exit_code`: Expected numeric exit code
- `expected_success`: Boolean success expectation

### Optional Metadata Fields
- `expected_execution_path`: Array of task IDs that should execute
- `expected_skipped_tasks`: Array of task IDs that should be skipped
- `expected_final_task`: Final task ID that should complete
- `expected_variables`: Object with variable name/value pairs
- `timeout_expected`: Boolean if timeout is expected
- `performance_benchmarks`: Performance limits object
- `security_category`: Security vulnerability type
- `risk_level`: Security risk assessment

## 🚀 Example Usage

```bash
# Copy template
cp positive_test_template.txt ../functional/my_new_test.txt

# Edit the test
vim ../functional/my_new_test.txt

# Validate with intelligent test runner
cd ../scripts/
./intelligent_test_runner.py ../functional/my_new_test.txt
```

## 📚 Reference Examples

See `test_cases/functional/metadata_*.txt` files for complete working examples of each test type.