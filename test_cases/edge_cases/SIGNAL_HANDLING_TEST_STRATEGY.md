# Signal Handling Test Strategy

## Overview

Signal handling is **CRITICAL** for production systems. TASKER must handle SIGTERM and SIGINT gracefully to:
1. Prevent data loss
2. Clean up resources (processes, files, locks)
3. Preserve state for potential resume
4. Provide clear error messages

## Test Categories

### 1. Sequential Execution Signal Tests

**Purpose:** Verify signal handling during normal sequential task execution

**Scenarios:**
- **sigterm_sequential_basic** - Signal during simple local command
- **sigterm_sequential_sleep** - Signal during sleep (tests non-blocking sleep handling)
- **sigterm_sequential_remote** - Signal during remote command execution (pbrun/p7s/wwrs)
- **sigterm_sequential_between_tasks** - Signal in transition between tasks
- **sigterm_sequential_long_output** - Signal during large output processing

### 2. Parallel Execution Signal Tests

**Purpose:** Verify signal handling with multiple concurrent tasks

**Scenarios:**
- **sigterm_parallel_all_running** - Signal with all parallel tasks actively executing
- **sigterm_parallel_mixed_state** - Signal with some tasks complete, some running
- **sigterm_parallel_with_timeout** - Signal during master timeout enforcement
- **sigterm_parallel_with_retry** - Signal during retry attempt
- **sigterm_parallel_nested** - Signal during nested parallel execution

### 3. Complex Workflow Signal Tests

**Purpose:** Verify signal handling in complex execution contexts

**Scenarios:**
- **sigterm_conditional_evaluation** - Signal during conditional block evaluation
- **sigterm_loop_iteration** - Signal during loop execution (mid-iteration)
- **sigterm_nested_structures** - Signal during parallel within conditional
- **sigterm_with_pending_routing** - Signal with on_success/on_failure pending

### 4. Resource Cleanup Verification Tests

**Purpose:** Verify all resources are properly cleaned up after signal

**Scenarios:**
- **sigterm_cleanup_processes** - No zombie processes left
- **sigterm_cleanup_temp_files** - Temp files deleted (streaming output handler)
- **sigterm_cleanup_file_handles** - All file handles closed
- **sigterm_cleanup_locks** - Lock files released
- **sigterm_cleanup_threads** - All threads terminated

### 5. State Persistence Tests

**Purpose:** Verify state is saved correctly for resume capability

**Scenarios:**
- **sigterm_state_persistence** - State file written with current execution point
- **sigterm_state_variables** - Global variables preserved
- **sigterm_state_loop_counters** - Loop counters preserved
- **sigterm_state_task_results** - Completed task results preserved

### 6. SIGINT (Keyboard Interrupt) Tests

**Purpose:** Verify Ctrl+C handling (SIGINT) behaves correctly

**Scenarios:**
- **sigint_sequential** - SIGINT during sequential execution
- **sigint_parallel** - SIGINT during parallel execution
- **sigint_interactive** - SIGINT with user confirmation (if implemented)

### 7. Signal Timing Edge Cases

**Purpose:** Test signal delivery at critical moments

**Scenarios:**
- **sigterm_at_task_start** - Signal immediately at task start
- **sigterm_at_task_end** - Signal at task completion (before next)
- **sigterm_during_validation** - Signal during validation phase
- **sigterm_during_output_processing** - Signal during stdout/stderr processing
- **sigterm_during_condition_evaluation** - Signal during condition parsing

### 8. Multiple Signal Tests

**Purpose:** Verify behavior with repeated signals

**Scenarios:**
- **sigterm_double_signal** - Second SIGTERM forces immediate exit
- **sigterm_then_sigkill** - SIGKILL after SIGTERM timeout
- **sigint_then_sigterm** - Mixed signal types

## Test Implementation Pattern

### Test File Structure

Each signal test will use this pattern:

```bash
# TEST_METADATA: {
#   "description": "SIGTERM during sequential task execution",
#   "test_type": "signal_handling",
#   "expected_exit_code": 143,  # 128 + 15 (SIGTERM)
#   "expected_success": false,
#   "signal_type": "SIGTERM",
#   "signal_timing": "after_task_start",
#   "signal_delay_seconds": 2,
#   "verify_cleanup": true,
#   "verify_state_persistence": true
# }

# Task that will be interrupted
task=0
hostname=localhost
command=sleep
arguments=10
exec=local

# Subsequent tasks (should not execute)
task=1
hostname=localhost
command=echo
arguments=This should not execute
exec=local
```

### Test Execution Wrapper

Tests will use a wrapper script: `test_cases/bin/signal_test_wrapper.sh`

```bash
#!/bin/bash
# Signal test wrapper - starts TASKER, sends signal, verifies cleanup

TASK_FILE=$1
SIGNAL_TYPE=$2
SIGNAL_DELAY=$3

# Start TASKER in background
tasker.py "$TASK_FILE" -r &
TASKER_PID=$!

# Wait for signal delay
sleep "$SIGNAL_DELAY"

# Send signal
kill -s "$SIGNAL_TYPE" "$TASKER_PID"

# Wait for TASKER to exit
wait "$TASKER_PID"
EXIT_CODE=$?

# Verify cleanup
# 1. Check for zombie processes
# 2. Check temp files cleaned
# 3. Check state file integrity
# 4. Check log files closed

exit $EXIT_CODE
```

## Verification Checklist

For each signal test, verify:

- [ ] **Exit Code:** Correct signal-based exit code (130 for SIGINT, 143 for SIGTERM)
- [ ] **Process Tree:** No zombie processes (`ps aux | grep defunct`)
- [ ] **Temp Files:** No temp files left in `/tmp/tasker_*`
- [ ] **File Handles:** All file handles closed (`lsof -p <pid>`)
- [ ] **Lock Files:** Lock files released (if any)
- [ ] **State File:** Valid JSON, contains expected data
- [ ] **Log Files:** Properly closed, no corruption
- [ ] **Error Messages:** Clear signal handling message in logs
- [ ] **Summary Log:** Summary written (if enabled)
- [ ] **Threads:** All threads terminated (no hung threads)

## Expected Behavior

### SIGTERM (Graceful Shutdown)

1. **Immediate:** Stop accepting new tasks
2. **Allow Current:** Let currently executing tasks complete (with timeout)
3. **Cancel Pending:** Cancel tasks that haven't started
4. **Cleanup:** Release all resources
5. **Persist State:** Save current state for resume
6. **Exit:** Exit with code 143 (128 + 15)

### SIGINT (Interrupt)

1. **Immediate:** Stop accepting new tasks
2. **Cancel All:** Cancel even running tasks
3. **Quick Cleanup:** Fast cleanup (5-second timeout)
4. **Exit:** Exit with code 130 (128 + 2)

### Multiple Signals

1. **First Signal:** Graceful shutdown (as above)
2. **Second Signal:** Immediate exit (SIGKILL-like behavior)
3. **No Cleanup:** Best-effort cleanup only

## Race Conditions to Test

1. **Signal during process spawn** - Race between subprocess.Popen() and signal
2. **Signal during file write** - Ensure file integrity
3. **Signal during lock acquisition** - Deadlock prevention
4. **Signal during thread join** - Thread cleanup races
5. **Signal during state save** - State file corruption prevention

## Performance Considerations

Signal handling should be **fast**:
- Graceful shutdown: < 10 seconds for typical workflows
- Cleanup: < 5 seconds
- State persistence: < 2 seconds

## Integration with Existing Tests

Signal tests should:
1. Use existing mock commands (pbrun, p7s, wwrs_clir)
2. Follow TEST_METADATA standard
3. Use `skip_host_validation: true`
4. Be runnable via `intelligent_test_runner.py`
5. Be categorized under `edge_cases/` directory

## Priority Test Cases (MVP)

**Must-Have (Week 1):**
1. sigterm_sequential_basic
2. sigterm_parallel_all_running
3. sigterm_cleanup_processes
4. sigint_sequential

**Should-Have (Week 2):**
5. sigterm_sequential_sleep
6. sigterm_parallel_mixed_state
7. sigterm_state_persistence
8. sigterm_double_signal

**Nice-to-Have (Week 3-4):**
9. sigterm_nested_structures
10. sigterm_loop_iteration
11. sigterm_timing_edge_cases
12. sigterm_cleanup_comprehensive

## Success Criteria

Signal handling test suite is complete when:
- [ ] 15+ signal test cases implemented
- [ ] All critical scenarios covered (sequential, parallel, cleanup, state)
- [ ] 100% pass rate with signal delivery
- [ ] Cleanup verification passes for all tests
- [ ] Documentation complete
- [ ] Integration with CI/CD (optional)

## References

- POSIX Signal Handling: https://man7.org/linux/man-pages/man7/signal.7.html
- Python signal module: https://docs.python.org/3/library/signal.html
- Exit codes: 128 + signal_number (130=SIGINT, 143=SIGTERM)
