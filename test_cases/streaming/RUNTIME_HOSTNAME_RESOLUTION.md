# Runtime Hostname Resolution in TASKER

## Overview

This document describes how TASKER handles runtime hostname resolution when the `hostname` parameter contains task result variables like `@0_stdout@`.

## Key Findings

### Validation Phase Limitation

**CRITICAL**: TASKER performs hostname validation during the **validation phase**, which occurs **before** any task execution. This creates a fundamental limitation:

- **Unresolved variables**: Variables like `@0_stdout@`, `@N_stdout@`, etc., are not available during validation
- **Validation failure**: If hostname contains unresolved variables, validation fails with exit code 20
- **Error message**: "Unresolved variables in hostname for task N"

### Required Configuration

To use runtime-resolved hostnames, you **MUST** include this in your test metadata:

```json
{
  "skip_unresolved_host_validation": true
}
```

**IMPORTANT**: Use `skip_unresolved_host_validation` (NOT `skip_host_validation`)!

**Security benefit**: `skip_unresolved_host_validation` only skips validation for hostnames with unresolved variables like `@0_stdout@`. Static hostnames in other tasks are **still validated**, catching typos and DNS errors before execution!

**Example from test case:**
```text
# TEST_METADATA: {"description": "...","skip_unresolved_host_validation": true,...}

task=0
hostname=localhost          # ✅ VALIDATED (catches typos!)
command=echo
arguments=pbrun-success-host
exec=local

task=1
hostname=@0_stdout@         # ⏭️ SKIPPED (runtime variable)
command=pbtest
exec=pbrun

task=2
hostname=prod-server.com    # ✅ VALIDATED (catches DNS errors!)
command=verify
exec=pbrun
```

### Execution Flow

1. **Task 0 executes**: Generates hostname string (e.g., "pbrun-success-host")
2. **Variable resolution**: TASKER resolves `@0_stdout@` to actual value
3. **Task 1 executes**: Uses resolved hostname for remote execution
4. **Connection attempt**: Remote executor (pbrun/p7s/wwrs) connects to target host

### Valid Execution Types

TASKER supports these remote execution types:

| Exec Type | Binary | Usage | Test Command |
|-----------|--------|-------|--------------|
| `pbrun` | pbrun | `pbrun -n -h hostname command args` | pbtest |
| `p7s` | p7s | `p7s hostname command args` | pbtest |
| `wwrs` | wwrs_clir | `wwrs_clir hostname command args` | wwrs_test |
| `local` | (none) | `command args` | N/A |

**Note**: The exec type is `wwrs`, not `wwrs_clir` (which is the binary name).

## Test Cases Created

### 1. test_runtime_hostname_pbrun_basic.txt

**Purpose**: Verify basic runtime hostname resolution with pbrun executor

**Flow**:
- Task 0: Generate hostname "pbrun-success-host"
- Task 1: Connect to `@0_stdout@` using pbrun + pbtest
- Task 2: Verify successful connection

**Expected Result**: All tasks execute successfully, connection established

### 2. test_runtime_hostname_pbrun_invalid.txt

**Purpose**: Verify error handling when runtime-resolved hostname is invalid

**Flow**:
- Task 0: Generate invalid hostname "nonexistent-invalid-host"
- Task 1: Attempt connection to `@0_stdout@` using pbrun
- Task 2: Should NOT execute (workflow stops on failure)

**Expected Result**: Task 1 fails, workflow terminates, exit code 1

### 3. test_runtime_hostname_multiple_executors.txt

**Purpose**: Verify all three remote executors handle runtime hostname resolution

**Flow**:
- Tasks 0-2: Test pbrun with runtime hostname "pbrun-connection-ok"
- Tasks 3-5: Test p7s with runtime hostname "p7s-connection-ok"
- Tasks 6-7: Test wwrs with runtime hostname "wwrs-connection-ok"

**Expected Result**: All 8 tasks execute successfully, all connections established

## Mock Test Infrastructure

### /etc/hosts Entries

Mock hostnames defined for testing:

**pbrun variants:**
- pbrun-success-host
- pbrun-connection-ok
- pbrun-fail-host
- pbrun-denied-host
- pbrun-timeout-host
- pbrun-empty-response

**p7s variants:**
- p7s-success-host
- p7s-connection-ok
- p7s-fail-host
- p7s-denied-host
- p7s-timeout-host
- p7s-empty-response

**wwrs variants:**
- wwrs-success-host
- wwrs-connection-ok
- wwrs-fail-host
- wwrs-denied-host
- wwrs-timeout-host
- wwrs-empty-response

### Mock Executors

Located in `test_cases/bin/`:

**pbrun mock** (`test_cases/bin/pbrun`):
- Accepts `-n -h hostname command [args...]`
- Recognizes `pbtest` as connection test command
- Returns "pbtest connection OK" for valid hostnames

**p7s mock** (`test_cases/bin/p7s`):
- Accepts `hostname command [args...]`
- Recognizes `pbtest` as connection test command
- Returns "p7s connection test OK" for valid hostnames

**wwrs_clir mock** (`test_cases/bin/wwrs_clir`):
- Accepts `hostname command [args...]`
- Recognizes `wwrs_test` as connection test command (different!)
- Returns "wwrs_clir test OK" for valid hostnames

## Best Practices

### When to Use Runtime Hostname Resolution

✅ **Good use cases:**
- Dynamic environment discovery (task generates list of hosts)
- Load balancer selection (task queries which backend to use)
- Conditional host selection based on previous task results
- Service discovery patterns

❌ **Avoid when:**
- Hostname is known at workflow design time
- Pre-validation of hosts is critical for security
- You need validation phase to catch hostname typos

### Security Considerations

**IMPROVED SECURITY**: `skip_unresolved_host_validation` provides better security than the old `skip_host_validation` flag:

**Old flag (`skip_host_validation`):**
- ❌ Skips validation for ALL hostnames in workflow
- ❌ Typos in static hostnames go undetected
- ❌ DNS errors only found at runtime
- ❌ No early detection of configuration errors

**New flag (`skip_unresolved_host_validation`):**
- ✅ Validates ALL static hostnames (catches typos!)
- ✅ Only skips hostnames with unresolved variables
- ✅ DNS errors detected during validation phase
- ✅ Early detection of configuration errors

**Example comparison:**
```text
task=0: hostname=prodserver1.exmaple.com  # Typo: "exmaple"
task=1: hostname=@0_stdout@               # Runtime variable
task=2: hostname=prod-backup.example.com  # Static hostname

With skip_host_validation:       ALL 3 hostnames unchecked ❌
With skip_unresolved_host_validation:  Tasks 0 & 2 validated, catches typo ✅
```

**Remaining considerations** (for runtime-resolved hostnames only):
1. **Runtime detection**: Invalid runtime hostnames detected during execution (not validation)
2. **Dynamic errors**: Hostname generation logic errors cause runtime failures

**Best practices:**
- Use explicit hostname generation (echo "known-hostname") rather than complex logic
- Add verification tasks after runtime-resolved connections
- Log resolved hostnames for audit trail
- Prefer global variables when hostname is known at design time (validated at start)

## Technical Implementation

### Variable Resolution Timing

From `tasker/validation/host_validator.py`:

```python
hostname, resolved = ConditionEvaluator.replace_variables(
    task['hostname'], global_vars, task_results, debug_callback)

if not resolved:
    unresolved_hostnames.append({
        'task_id': task.get('task_id', 'unknown'),
        'hostname': task['hostname'],
        'resolved_to': hostname
    })
```

- `resolved=False`: Variable contains `@N_stdout@` or similar unresolved placeholder
- **Result**: Validation fails with exit code 20 unless `skip_host_validation=true`

### Runtime Resolution

During task execution (sequential_executor.py / parallel_executor.py):

1. Task N-1 completes, output stored in `task_results[N-1]['stdout']`
2. Task N hostname `@N-1_stdout@` is resolved using `ConditionEvaluator.replace_variables()`
3. Resolved hostname passed to remote executor
4. Remote executor constructs command based on exec type
5. Connection attempt proceeds with actual hostname value

## Related Files

- Test cases: `test_cases/streaming/test_runtime_hostname_*.txt`
- Host validation: `tasker/validation/host_validator.py`
- Variable resolution: `tasker/core/condition_evaluator.py`
- Task execution: `tasker/executors/sequential_executor.py`
- Mock executors: `test_cases/bin/{pbrun,p7s,wwrs_clir}`

## Verification Commands

```bash
# Run runtime hostname resolution tests
cd /home/baste/tasker/test_cases
python3 scripts/intelligent_test_runner.py streaming/test_runtime_hostname_*.txt

# Expected output: [SUCCESS] ALL TESTS PASSED!
```

---

**Document Created**: November 10, 2025
**TASKER Version**: 2.1
**Branch**: feature/test-runtime-hostname-resolution
