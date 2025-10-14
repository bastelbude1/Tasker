# Signal Handling Tests - User Guide

## Overview

Signal handling tests verify that TASKER gracefully handles SIGTERM and SIGINT signals, properly cleans up resources, and persists state for resume capability.

## Test Files Created

### Week 1 Priority (MVP)

| Test File | Description | Signal | Delay | Key Focus |
|-----------|-------------|--------|-------|-----------|
| `test_sigterm_sequential_basic.txt` | Basic SIGTERM during sequential execution | SIGTERM | 2s | Basic signal handling |
| `test_sigterm_parallel_all_running.txt` | SIGTERM with all parallel tasks running | SIGTERM | 2s | Parallel task cleanup, no zombies |
| `test_sigterm_cleanup_processes.txt` | Comprehensive cleanup verification | SIGTERM | 3s | Process tree cleanup, temp files |
| `test_sigint_sequential.txt` | SIGINT (Ctrl+C) during sequential execution | SIGINT | 2s | Keyboard interrupt, faster cleanup |

### Week 2 Priority (Advanced)

| Test File | Description | Signal | Delay | Key Focus |
|-----------|-------------|--------|-------|-----------|
| `test_sigterm_sequential_sleep.txt` | SIGTERM during non-blocking sleep | SIGTERM | 2s | Timer thread cleanup |
| `test_sigterm_parallel_mixed_state.txt` | SIGTERM with mixed task states | SIGTERM | 3s | Partial completion, state preservation |
| `test_sigterm_state_persistence.txt` | State persistence for resume | SIGTERM | 3s | State file integrity, resume capability |
| `test_sigterm_double_signal.txt` | Double SIGTERM forces immediate exit | SIGTERM | 2s + 1s | Impatient user handling |

## Running Signal Tests

### Method 1: Using Signal Test Wrapper (Recommended)

The signal test wrapper automates signal delivery and cleanup verification:

```bash
cd /home/baste/tasker/test_cases

# Basic usage
./bin/signal_test_wrapper.sh edge_cases/test_sigterm_sequential_basic.txt SIGTERM 2

# With custom delay
./bin/signal_test_wrapper.sh edge_cases/test_sigterm_parallel_all_running.txt SIGTERM 3

# Double signal test
./bin/signal_test_wrapper.sh edge_cases/test_sigterm_double_signal.txt SIGTERM 2 1

# SIGINT test
./bin/signal_test_wrapper.sh edge_cases/test_sigint_sequential.txt SIGINT 2
```

### Method 2: Manual Testing

For debugging or interactive testing:

```bash
# Terminal 1: Start TASKER
cd /home/baste/tasker
./tasker.py test_cases/edge_cases/test_sigterm_sequential_basic.txt -r --skip-host-validation &
TASKER_PID=$!

# Terminal 1: Wait for task to start, then send signal
sleep 2
kill -TERM $TASKER_PID

# Terminal 1: Verify cleanup
wait $TASKER_PID
echo "Exit code: $?"
ps aux | grep defunct  # Check for zombies
ls -la /tmp/tasker_*   # Check for temp files
```

### Method 3: Integration with intelligent_test_runner.py

**Note:** Signal tests require special handling and cannot run with standard test runner yet. Future enhancement needed to integrate signal test wrapper with intelligent_test_runner.py.

## Verification Checklist

After each signal test, verify:

### Process Cleanup
- [ ] No zombie processes: `ps aux | grep defunct`
- [ ] No orphaned child processes: `pgrep -P <tasker_pid>`
- [ ] All subprocesses terminated

### File System Cleanup
- [ ] No temp files left: `ls -la /tmp/tasker_*`
- [ ] Log files properly closed (no partial writes)
- [ ] Summary files written (if enabled)

### State Persistence (if applicable)
- [ ] State file exists: `~/.tasker/state/<workflow>.json`
- [ ] State file is valid JSON: `jq . state.json`
- [ ] Contains completed task results
- [ ] Contains global variables
- [ ] Contains execution metadata

### Exit Code Verification
- [ ] SIGTERM: Exit code 143 (128 + 15)
- [ ] SIGINT: Exit code 130 (128 + 2)

### Error Messages
- [ ] Clear signal handling message in logs
- [ ] No Python tracebacks or exceptions
- [ ] Proper shutdown sequence logged

## Expected Behavior

### SIGTERM (Graceful Shutdown)

**Timeline:**
1. **T+0s:** SIGTERM received
2. **T+0s:** Stop accepting new tasks
3. **T+0-10s:** Let current tasks finish (with timeout)
4. **T+0-10s:** Clean up resources (processes, files, locks)
5. **T+0-10s:** Persist state for resume
6. **T+10s:** Exit with code 143

**Characteristics:**
- Graceful: Tries to complete current tasks
- Timeout: Maximum 10 seconds for cleanup
- State: Preserves state for resume
- Resources: Full cleanup performed

### SIGINT (Keyboard Interrupt)

**Timeline:**
1. **T+0s:** SIGINT received (Ctrl+C)
2. **T+0s:** Cancel all tasks immediately
3. **T+0-5s:** Quick cleanup (5-second timeout)
4. **T+5s:** Exit with code 130

**Characteristics:**
- Immediate: Cancels tasks immediately
- Fast: 5-second cleanup timeout
- User-focused: Prioritizes responsiveness
- Resources: Best-effort cleanup

### Double Signal (Impatient User)

**Timeline:**
1. **First signal:** Graceful shutdown begins
2. **Second signal:** Immediate exit (< 1 second)

**Characteristics:**
- Force exit: No graceful shutdown
- Immediate: Exits within 1 second
- Cleanup: Best-effort only
- User control: Respects impatient user

## Test Scenarios by Category

### Sequential Execution Tests
- Basic task interruption
- Sleep interruption (timer threads)
- Remote command interruption
- Between-task signal delivery

### Parallel Execution Tests
- All tasks running (worst case)
- Mixed states (some complete, some running)
- Nested parallel execution
- Timeout interaction with signals

### Resource Cleanup Tests
- Process tree cleanup (no zombies)
- Temp file cleanup
- File handle closure
- Lock release
- Thread termination

### State Persistence Tests
- State file writing on signal
- Task results preservation
- Global variables preservation
- Loop counter preservation
- Resume capability foundation

### Edge Case Tests
- Signal during validation
- Signal during output processing
- Signal during condition evaluation
- Multiple signals (double SIGTERM)
- Mixed signal types (SIGINT then SIGTERM)

## Troubleshooting

### Test Fails: Zombie Processes Found

**Symptoms:** `ps aux | grep defunct` shows zombie processes

**Diagnosis:**
```bash
# Check process tree
pstree -p <tasker_pid>

# Check for subprocesses not reaped
ps aux | grep sleep
```

**Likely Cause:**
- Subprocess.Popen() not using context manager
- Missing process.wait() after termination
- Signal handler not propagating to subprocesses

### Test Fails: Temp Files Not Cleaned

**Symptoms:** `/tmp/tasker_*` files remain after test

**Diagnosis:**
```bash
# List temp files
ls -la /tmp/tasker_*

# Check file descriptors
lsof | grep tasker
```

**Likely Cause:**
- StreamingOutputHandler not cleaning up temp files
- Exception during cleanup phase
- Signal delivered during file write

### Test Fails: Wrong Exit Code

**Symptoms:** Exit code doesn't match expected (143 or 130)

**Diagnosis:**
```bash
# Check what signal was received
echo "Exit code: $?"
# 143 = SIGTERM, 130 = SIGINT, 137 = SIGKILL
```

**Likely Cause:**
- Signal handler not registered correctly
- Python exception during signal handling
- Process killed (SIGKILL) instead of terminated

### Test Fails: State File Corrupted

**Symptoms:** State file not valid JSON or incomplete

**Diagnosis:**
```bash
# Validate JSON
jq . ~/.tasker/state/test.json

# Check file size
ls -lh ~/.tasker/state/test.json
```

**Likely Cause:**
- Signal during state file write
- No atomic write (write + rename)
- Exception during JSON serialization

## Future Enhancements

### Short-term (1-2 weeks)
- [ ] Integration with intelligent_test_runner.py
- [ ] Automated cleanup verification in test framework
- [ ] State file diff tool for resume testing
- [ ] Performance timing verification (graceful vs immediate)

### Medium-term (1 month)
- [ ] Resume capability tests (`--start-from` after signal)
- [ ] Stress testing (signal with 100+ parallel tasks)
- [ ] Signal timing edge cases (signal at exact moment)
- [ ] Cross-platform testing (Linux, WSL, macOS)

### Long-term (2-3 months)
- [ ] CI/CD integration for signal tests
- [ ] Fuzzing signal timing (random delays)
- [ ] Multi-signal patterns (SIGINT → SIGTERM → SIGKILL)
- [ ] Performance benchmarks (cleanup time)

## Contributing

When adding new signal tests:

1. **Follow TEST_METADATA format** with signal_* fields
2. **Use signal_test_wrapper.sh** for execution
3. **Document expected behavior** in test file comments
4. **Include verification steps** in test comments
5. **Test locally** before committing
6. **Update this README** with new test descriptions

## References

- POSIX Signals: https://man7.org/linux/man-pages/man7/signal.7.html
- Python signal handling: https://docs.python.org/3/library/signal.html
- TASKER Signal Strategy: `SIGNAL_HANDLING_TEST_STRATEGY.md`
- Subprocess cleanup: https://docs.python.org/3/library/subprocess.html

## Questions?

For questions about signal handling tests:
1. Read `SIGNAL_HANDLING_TEST_STRATEGY.md` for design details
2. Review test file comments for specific scenarios
3. Check signal_test_wrapper.sh for execution details
4. Consult CLAUDE.md for general testing guidelines
