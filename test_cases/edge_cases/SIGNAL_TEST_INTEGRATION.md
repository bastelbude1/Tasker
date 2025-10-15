# Signal Test Integration with intelligent_test_runner.py

## Issue Resolved

**Problem:** Signal tests were being skipped by `intelligent_test_runner.py`

**Error Message:**
```
SKIPPED TESTS (Need TEST_METADATA):
  • test_sigint_sequential.txt: Invalid test_type. Must be one of: ['positive', 'negative', 'validation_only', 'security_negative', 'performance']
  • test_sigterm_cleanup_processes.txt: Invalid test_type. Must be one of: [...]
  ...
```

**Root Cause:** Tests used `"test_type": "signal_handling"` which is not a recognized type.

**Solution:** Changed all signal tests to `"test_type": "negative"` (since they expect non-zero exit codes).

## Valid Test Types

According to `intelligent_test_runner.py`, these are the only valid test types:

| Test Type | Purpose | Expected Exit Code | Expected Success |
|-----------|---------|-------------------|------------------|
| `positive` | Normal success scenarios | 0 | true |
| `negative` | Expected validation/execution failures | non-zero | false |
| `validation_only` | Validation-only execution | 20 | false |
| `security_negative` | Security rejection tests | 20 | false |
| `performance` | Performance benchmarks | 0 | true |

## Signal Test Classification

Signal handling tests are classified as **`negative`** because:

1. **Non-zero exit codes expected:**
   - SIGTERM: exit code 143 (128 + 15)
   - SIGINT: exit code 130 (128 + 2)

2. **Expected success is false:**
   - Tests expect workflow interruption
   - Not a successful completion

3. **Fits negative test definition:**
   - Expected execution failure (signal interruption)
   - Known non-zero exit code
   - Verifiable cleanup behavior

## Updated TEST_METADATA Format

### SIGTERM Tests (exit code 143)

```json
{
  "description": "SIGTERM during basic sequential task execution",
  "test_type": "negative",
  "expected_exit_code": 143,
  "expected_success": false,
  "signal_type": "SIGTERM",
  "signal_delay_seconds": 2,
  "verify_cleanup": true,
  "skip_host_validation": true
}
```

### SIGINT Tests (exit code 130)

```json
{
  "description": "SIGINT (Ctrl+C) during sequential task execution",
  "test_type": "negative",
  "expected_exit_code": 130,
  "expected_success": false,
  "signal_type": "SIGINT",
  "signal_delay_seconds": 2,
  "verify_cleanup": true,
  "skip_host_validation": true
}
```

## Custom Metadata Fields

Signal tests include custom metadata fields for test execution:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `signal_type` | string | Signal to send (SIGTERM/SIGINT) | "SIGTERM" |
| `signal_delay_seconds` | int | Delay before sending signal | 2 |
| `second_signal_delay` | int | Delay before second signal (optional) | 1 |
| `verify_cleanup` | bool | Verify resource cleanup | true |
| `verify_no_zombies` | bool | Verify no zombie processes | true |
| `verify_temp_files` | bool | Verify temp file cleanup | true |
| `verify_state_persistence` | bool | Verify state file integrity | true |
| `verify_state_integrity` | bool | Verify state JSON validity | true |
| `verify_immediate_exit` | bool | Verify immediate exit (< 1s) | true |

**Note:** These custom fields are informational only. The `intelligent_test_runner.py` does not use them for validation (yet).

## Running Signal Tests

### Method 1: Using signal_test_wrapper.sh (Recommended)

Signal tests require the wrapper script to send signals:

```bash
cd /home/baste/tasker/test_cases

# SIGTERM test
./bin/signal_test_wrapper.sh edge_cases/test_sigterm_sequential_basic.txt SIGTERM 2

# SIGINT test
./bin/signal_test_wrapper.sh edge_cases/test_sigint_sequential.txt SIGINT 2

# Double signal test
./bin/signal_test_wrapper.sh edge_cases/test_sigterm_double_signal.txt SIGTERM 2 1
```

### Method 2: Using intelligent_test_runner.py (Limited)

**Note:** Signal tests will now be **recognized** by intelligent_test_runner.py, but they **cannot execute correctly** without signal delivery mechanism.

```bash
cd /home/baste/tasker/test_cases

# This will recognize the tests but they will timeout (waiting 10s for signal that never comes)
python3 scripts/intelligent_test_runner.py edge_cases/test_sigterm_sequential_basic.txt
```

**Expected behavior:**
- Test will be **recognized** (not skipped)
- Test will **timeout** after 120 seconds (waiting for task to complete)
- Exit code will be 124 (timeout) instead of expected 143

### Method 3: Integration (Future Enhancement)

Future work to integrate signal delivery into `intelligent_test_runner.py`:

```python
# Proposed enhancement for intelligent_test_runner.py

def execute_signal_test(task_file, metadata):
    """Execute test that requires signal delivery."""
    signal_type = metadata.get('signal_type', 'SIGTERM')
    signal_delay = metadata.get('signal_delay_seconds', 2)
    second_signal_delay = metadata.get('second_signal_delay', 0)

    # Use signal_test_wrapper.sh internally
    wrapper_path = os.path.join(TEST_CASES_DIR, 'bin', 'signal_test_wrapper.sh')
    cmd = [wrapper_path, task_file, signal_type, str(signal_delay)]
    if second_signal_delay:
        cmd.append(str(second_signal_delay))

    # Execute and verify cleanup
    # ...
```

## Test Status Summary

### All 8 Signal Tests Now Valid

| Test File | Test Type | Exit Code | Status |
|-----------|-----------|-----------|--------|
| `test_sigterm_sequential_basic.txt` | negative | 143 | ✅ Valid |
| `test_sigterm_parallel_all_running.txt` | negative | 143 | ✅ Valid |
| `test_sigterm_cleanup_processes.txt` | negative | 143 | ✅ Valid |
| `test_sigint_sequential.txt` | negative | 130 | ✅ Valid |
| `test_sigterm_sequential_sleep.txt` | negative | 143 | ✅ Valid |
| `test_sigterm_parallel_mixed_state.txt` | negative | 143 | ✅ Valid |
| `test_sigterm_state_persistence.txt` | negative | 143 | ✅ Valid |
| `test_sigterm_double_signal.txt` | negative | 143 | ✅ Valid |

### Tests Will No Longer Be Skipped

Before fix:
```
SKIPPED TESTS (Need TEST_METADATA): 8 tests
TOTAL TESTS: 267 (8 skipped)
```

After fix:
```
SKIPPED TESTS (Need TEST_METADATA): 0 tests
TOTAL TESTS: 275 (0 skipped)
```

## Commits

**Commit 1:** `90bd2b6` - Feature: Add comprehensive signal handling test suite
- Created 8 test files
- Created signal_test_wrapper.sh
- Created documentation (strategy + readme)
- +1,355 lines

**Commit 2:** `6d6b482` - Fix: Change signal test_type from 'signal_handling' to 'negative'
- Fixed TEST_METADATA in all 8 test files
- Changed "signal_handling" → "negative"
- Tests now properly recognized

## Next Steps

1. **Manual testing** - Verify signal tests work with wrapper script
2. **Implementation check** - Verify TASKER actually handles signals
3. **Test runner integration** - Add signal test support to intelligent_test_runner.py
4. **CI/CD integration** - Add automated signal testing
5. **Coverage tracking** - Include signal tests in coverage reports

## References

- `SIGNAL_HANDLING_TEST_STRATEGY.md` - Complete test strategy
- `SIGNAL_HANDLING_TESTS_README.md` - User guide and troubleshooting
- `signal_test_wrapper.sh` - Signal delivery and verification script
- `intelligent_test_runner.py` - Test validation framework
