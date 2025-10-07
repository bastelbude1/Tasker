# Failure Condition Parameter

## Overview

The `failure=` parameter provides an inverse alternative to the `success=` parameter, making it easier to define workflows where most exit codes represent success.

## Problem Solved

**Before (complex success definition):**
```bash
# Task succeeds for exit codes 0, 2, 3, 4, 5
# Only fails for exit code 1
success=exit_0,exit_2,exit_3,exit_4,exit_5
```

**After (simple failure definition):**
```bash
# Task fails ONLY for exit code 1
# Succeeds for all other exit codes
failure=exit_1
```

## How It Works

The `failure=` parameter uses **inverse logic**:

1. **Default**: Task is assumed to succeed (`success = true`)
2. **Evaluate**: Check if failure condition is met
3. **Invert**: If failure condition is true → task failed (`success = false`)

### Examples

#### Single Failure Code
```bash
task=1
hostname=localhost
command=/usr/bin/some_command
exec=local
failure=exit_1  # Fail if exit code is 1, success otherwise
```

#### Multiple Failure Codes
```bash
task=1
hostname=localhost
command=/usr/bin/some_command
exec=local
failure=exit_1|exit_2|exit_127  # Fail if exit 1, 2, or 127
```

#### Complex Failure Conditions
```bash
task=1
hostname=localhost
command=/usr/bin/some_command
exec=local
failure=@0_success@=false  # Fail if task 0 failed
```

```bash
task=2
hostname=localhost
command=/usr/bin/some_command
exec=local
failure=@1_stdout@=ERROR  # Fail if task 1's stdout contains "ERROR"
```

## Validation Rules

**Mutual Exclusion**: `success` and `failure` **cannot** be used together on the same task.

```bash
# ❌ INVALID - Will fail validation
task=1
hostname=localhost
command=/usr/bin/some_command
exec=local
success=exit_0
failure=exit_1
```

**Error message:**
```
ERROR: Task 1 cannot use 'success' and 'failure' together.
Use either 'success' for positive conditions OR 'failure' for inverse conditions, not both.
```

## When to Use

### Use `failure=` when:
- ✅ Most exit codes represent success
- ✅ Only a few specific codes represent failure
- ✅ You want simpler, more readable task definitions

**Example**: A deployment script where only exit code 1 (permission denied) represents failure:
```bash
failure=exit_1  # Much clearer than success=exit_0|exit_2|exit_3|...
```

### Use `success=` when:
- ✅ Only a few specific codes represent success
- ✅ Most exit codes represent failure
- ✅ You need explicit positive condition logic

**Example**: A validation script where only exit 0 and 2 are acceptable:
```bash
success=exit_0|exit_2  # Clearer than listing all other codes as failures
```

## Comparison with Success Parameter

| Scenario | Using `success=` | Using `failure=` |
|----------|------------------|------------------|
| Fail on exit 1 only | `success=exit_0\|exit_2\|exit_3\|...` | `failure=exit_1` ✅ |
| Success on exit 0 only | `success=exit_0` ✅ | `failure=exit_1\|exit_2\|exit_3\|...` |
| Fail if task 0 failed | `success=@0_success@=true` | `failure=@0_success@=false` ✅ |
| Success if stdout contains "OK" | `success=@stdout@=OK` ✅ | `failure=@stdout@!=OK` |

## Implementation Details

- **Evaluation Order**: Checked after `success` parameter (mutually exclusive)
- **Default Behavior**: When `failure` is present, success defaults to `true`
- **Condition Evaluator**: Reuses existing condition evaluation infrastructure
- **Routing**: Works seamlessly with `on_success`, `on_failure`, and `next` parameters

## Test Cases

See `test_cases/functional/` for examples:
- `test_failure_simple.txt` - Single failure code
- `test_failure_simple_fails.txt` - Task actually fails
- `test_failure_multiple.txt` - Multiple failure codes
- `test_failure_complex.txt` - Complex variable-based condition
- `test_failure_validation.txt` - Mutual exclusion validation

## Benefits

1. **Simpler Definitions** - Fewer codes to list for common scenarios
2. **More Readable** - Intent is clearer (what constitutes failure)
3. **Less Error-Prone** - No risk of missing a success code in a long list
4. **Flexible** - Supports all condition types (exit codes, variables, expressions)
