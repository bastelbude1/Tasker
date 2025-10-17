# TASKER Recovery Test Suite

Comprehensive test suite for automatic error recovery functionality.

## Overview

These tests validate the `--auto-recovery` feature which enables workflows to automatically resume from the point of failure.

## Test Cases

### 1. Basic Recovery Failure (`test_recovery_basic_failure.txt`)
- **Type**: Negative test
- **Purpose**: Validates that recovery file is created when a task fails
- **Expected**: Task 2 fails, recovery file created with execution_path [0, 1]
- **Exit Code**: 1 (task failure)

### 2. Safe Recovery Resume (`test_recovery_safe_resume.txt`)
- **Type**: Positive test
- **Purpose**: Validates automatic resume from failed task with no backward dependencies
- **Prerequisites**: Run `test_recovery_basic_failure.txt` first
- **Expected**: Resumes from task 2, completes successfully, deletes recovery file
- **Exit Code**: 0 (success)

### 3. Unsafe Backward Dependencies (`test_recovery_unsafe_backward_deps.txt`)
- **Type**: Negative test
- **Purpose**: Validates that backward dependencies are detected and prevent unsafe resume
- **Expected**: Dependency analyzer detects task 3 depends on task 0, blocks resume
- **Exit Code**: 15 (TASK_DEPENDENCY_FAILED)

### 4. Global Variables Preservation (`test_recovery_with_global_vars.txt`)
- **Type**: Positive test
- **Purpose**: Validates that global variables are preserved across recovery
- **Expected**: All global variables restored correctly after resume
- **Exit Code**: 0 (success)

### 5. Show Recovery Info (`test_recovery_show_info.txt`)
- **Type**: Validation only
- **Purpose**: Validates --show-recovery-info flag displays state without executing
- **Prerequisites**: Run `test_recovery_basic_failure.txt` first
- **Expected**: Displays recovery state, exits without execution
- **Exit Code**: 0 (success)

### 6. Cleanup on Success (`test_recovery_cleanup_on_success.txt`)
- **Type**: Positive test
- **Purpose**: Validates recovery file is deleted after successful completion
- **Expected**: Workflow completes, recovery file deleted
- **Exit Code**: 0 (success)

## Running Tests

### Manual Execution

```bash
# Test 1: Create recovery file (failure)
python3 tasker.py test_cases/recovery/test_recovery_basic_failure.txt -r --auto-recovery --skip-host-validation

# Verify recovery file created
ls ~/TASKER/recovery/

# Test 2: Resume from recovery file (success)
python3 tasker.py test_cases/recovery/test_recovery_safe_resume.txt -r --auto-recovery --skip-host-validation

# Verify recovery file deleted
ls ~/TASKER/recovery/

# Test 3: Show recovery info
python3 tasker.py test_cases/recovery/test_recovery_show_info.txt --auto-recovery --show-recovery-info --skip-host-validation

# Test 4: Backward dependency detection (should fail)
python3 tasker.py test_cases/recovery/test_recovery_unsafe_backward_deps.txt -r --auto-recovery --skip-host-validation

# Test 5: Global variables
python3 tasker.py test_cases/recovery/test_recovery_with_global_vars.txt -r --auto-recovery --skip-host-validation

# Test 6: Cleanup on success
python3 tasker.py test_cases/recovery/test_recovery_cleanup_on_success.txt -r --auto-recovery --skip-host-validation
```

### Automated Testing

```bash
# Run all recovery tests with intelligent test runner
python3 test_cases/scripts/intelligent_test_runner.py test_cases/recovery/ -r

# Run with verbose output
python3 test_cases/scripts/intelligent_test_runner.py test_cases/recovery/ -r -v
```

## Recovery File Location

Recovery files are stored in:
```
~/TASKER/recovery/{basename}_{hash}.recovery.json
```

Where:
- `basename`: Task file name without extension
- `hash`: First 8 characters of SHA-256(absolute_task_file_path)

## Key Features Tested

✅ Recovery file creation on failure
✅ Automatic state restoration and resume
✅ Backward dependency detection
✅ Global variable preservation
✅ Task file integrity verification (SHA-256)
✅ Recovery file cleanup on success
✅ --show-recovery-info flag
✅ Safe resume validation

## Test Metadata Format

All tests include TEST_METADATA with:
- `description`: Test purpose
- `test_type`: positive|negative|validation_only
- `expected_exit_code`: Expected exit code
- `expected_success`: Expected success state
- `requires_auto_recovery`: Flag indicating --auto-recovery required
- `requires_recovery_file`: Flag indicating existing recovery file needed
- `recovery_file_should_be_deleted`: Flag for cleanup validation

## Cleanup

To clean up all recovery files:
```bash
rm -rf ~/TASKER/recovery/*.recovery.json
```

## Known Limitations

1. **Sequential test dependencies**: Some tests require running `test_recovery_basic_failure.txt` first to create recovery file
2. **Manual cleanup**: Recovery files from failed tests may need manual cleanup
3. **Hash changes**: Modifying task file invalidates recovery file (by design)

## Future Enhancements

- Multi-stage recovery tests (resume multiple times)
- Loop state recovery
- Conditional block recovery
- Parallel task recovery
- Performance benchmarks for recovery overhead
