# Flexible Routing with on_success and on_failure

## Overview

TASKER now supports flexible routing patterns where `on_success` and `on_failure` can be used independently, providing more powerful and concise workflow control.

## Three Routing Patterns

### Pattern 1: on_failure ONLY (Error Handler Pattern)

**Use Case**: Firewall/cleanup handlers that execute on failure, while success continues normally.

**Behavior**:
- **Success**: Continue to next sequential task (task_id + 1)
- **Failure**: Jump to error handler task

**Example**:
```bash
task=1
hostname=localhost
command=/usr/bin/somecommand
exec=local
on_failure=99  # Jump to error handler on failure

task=2
hostname=localhost
command=/usr/bin/echo
arguments=This executes if task 1 succeeds
exec=local

# Error handler in special range 90-99
task=99
hostname=localhost
command=/usr/bin/echo
arguments=ERROR HANDLER: Cleaning up
exec=local
return=1
```

**Advantages**:
- Clean separation of happy path and error handling
- Common pattern for firewall/cleanup tasks
- No need to specify on_success for every task

### Pattern 2: on_success ONLY (Strict Success Pattern)

**Use Case**: Workflows where success jumps to a specific task, but failure should terminate immediately.

**Behavior**:
- **Success**: Jump to specified task
- **Failure**: Workflow exits with code 10 (TASK_FAILED)

**Example**:
```bash
task=1
hostname=localhost
command=/usr/bin/critical_check
exec=local
on_success=5  # Jump to task 5 on success
# No on_failure defined → failure exits with code 10

task=2
hostname=localhost
command=/usr/bin/echo
arguments=Skipped if task 1 succeeds
exec=local

task=5
hostname=localhost
command=/usr/bin/echo
arguments=Critical check passed - continuing
exec=local
```

**Advantages**:
- Enforces that failures are fatal
- Cleaner for workflows where failures should not continue
- Exit code 10 provides clear signal to calling scripts

### Pattern 3: BOTH on_success AND on_failure (Explicit Routing)

**Use Case**: Complete control over both success and failure paths.

**Behavior**:
- **Success**: Jump to on_success target
- **Failure**: Jump to on_failure target

**Example**:
```bash
task=1
hostname=localhost
command=/usr/bin/somecommand
exec=local
on_success=10  # Success path
on_failure=99  # Failure path

task=10
hostname=localhost
command=/usr/bin/echo
arguments=Success path
exec=local

task=99
hostname=localhost
command=/usr/bin/echo
arguments=Failure path
exec=local
```

**Advantages**:
- Most explicit control
- Both outcomes handled
- Traditional TASKER behavior

## Exit Codes

- **Pattern 1** (on_failure only): Failure jumps to handler, handler's return code determines workflow exit code
- **Pattern 2** (on_success only): Failure exits with code **10** (TASK_FAILED)
- **Pattern 3** (both): Determined by final executed task

## Validation

The validator now:
- ✅ Allows on_success without on_failure
- ✅ Allows on_failure without on_success
- ✅ Validates target task IDs when routing parameters are present
- ✅ Enforces that on_success/on_failure cannot be used with 'next' parameter

## Migration Notes

**Previous behavior**: Both on_success AND on_failure were required together.

**New behavior**: They can be used independently for more flexible workflows.

**Backward compatibility**: Existing workflows with both parameters continue to work unchanged.

## Test Cases

See `test_cases/functional/` for examples:
- `test_on_failure_only_pattern.txt` - Error handler pattern (failure case)
- `test_on_failure_only_success.txt` - Error handler pattern (success case)
- `test_on_success_only_pattern.txt` - Strict success pattern (success case)
- `test_on_success_only_failure.txt` - Strict success pattern (failure case)
- `test_firewall_handler.txt` - Real-world firewall handler example
