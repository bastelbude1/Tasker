# ZeroDivisionError Fix - Environment Variable Validation

**Date**: Oct 2, 2025
**Issue**: Potential ZeroDivisionError when TASKER_PARALLEL_INSTANCES=0
**Component**: tasker/executors/parallel_executor.py
**Lines**: 270-315
**Priority**: HIGH

## Problem Description

The code reads `TASKER_PARALLEL_INSTANCES` from the environment and uses it as a divisor without validation, which could cause `ZeroDivisionError` when:
- Value is 0
- Value is negative
- Value is non-numeric (would cause ValueError)

### Vulnerable Code (Before Fix)
```python
parallel_instances = int(os.environ.get('TASKER_PARALLEL_INSTANCES', '1'))
# ...
absolute_max = max(10, 50 // parallel_instances)  # Could divide by zero!
```

## Solution Implemented

### Comprehensive Input Validation
```python
# Parse with error handling
try:
    parallel_instances = int(os.environ.get('TASKER_PARALLEL_INSTANCES', '1'))
except (ValueError, TypeError):
    parallel_instances = 1
    executor_instance.log_debug(f"Invalid TASKER_PARALLEL_INSTANCES value, defaulting to 1")

# Sanitize to prevent division by zero and negative values
if parallel_instances <= 0:
    executor_instance.log_debug(f"TASKER_PARALLEL_INSTANCES was {parallel_instances}, correcting to 1")
    parallel_instances = 1

# Clamp to reasonable maximum to prevent over-division
parallel_instances = min(parallel_instances, 1000)
```

### Key Safety Features

1. **Try-Except Block**: Handles non-numeric values gracefully
2. **Zero/Negative Check**: Forces minimum value of 1
3. **Maximum Cap**: Prevents extremely large values (capped at 1000)
4. **Debug Logging**: Informs about corrections made
5. **Safe Division**: All divisions now guaranteed safe (divisor >= 1)

## Test Results

### Test Cases and Outcomes

| Input Value | Expected Behavior | Actual Result | Status |
|-------------|------------------|---------------|---------|
| 0 | Correct to 1 | "correcting to 1" logged | ✅ PASS |
| -5 | Correct to 1 | "correcting to 1" logged | ✅ PASS |
| "abc" | Default to 1 | "Invalid value" logged | ✅ PASS |
| 999999 | Cap at 1000 | Clamped to 1000 | ✅ PASS |
| 10 | Use as-is | Used value 10 | ✅ PASS |

### Test Execution Logs

#### Test 1: Zero Value
```
TASKER_PARALLEL_INSTANCES=0
Result: DEBUG: Task 1: TASKER_PARALLEL_INSTANCES was 0, correcting to 1
Status: SUCCESS - No ZeroDivisionError
```

#### Test 2: Negative Value
```
TASKER_PARALLEL_INSTANCES=-5
Result: DEBUG: Task 1: TASKER_PARALLEL_INSTANCES was -5, correcting to 1
Status: SUCCESS - No ZeroDivisionError
```

#### Test 3: Non-Numeric Value
```
TASKER_PARALLEL_INSTANCES=abc
Result: DEBUG: Task 1: Invalid TASKER_PARALLEL_INSTANCES value, defaulting to 1
Status: SUCCESS - No ValueError
```

#### Test 4: Large Value
```
TASKER_PARALLEL_INSTANCES=999999
Result: DEBUG: Task 1: Nested/parallel execution detected (instances=1000, level=0)
Status: SUCCESS - Capped at 1000
```

## Additional Improvements

### TASKER_NESTED_LEVEL Validation
Also added validation for the `TASKER_NESTED_LEVEL` environment variable:
```python
try:
    nested_level = int(os.environ.get('TASKER_NESTED_LEVEL', '0'))
except (ValueError, TypeError):
    nested_level = 0
    executor_instance.log_debug(f"Invalid TASKER_NESTED_LEVEL value, defaulting to 0")

# Sanitize nested level
nested_level = max(0, nested_level)
```

## Impact

### Before Fix
- **Risk**: Production crash from ZeroDivisionError
- **User Experience**: Cryptic error message
- **Recovery**: Manual intervention required

### After Fix
- **Risk**: Eliminated
- **User Experience**: Graceful handling with informative logs
- **Recovery**: Automatic correction, continues execution

## Verification Commands

```bash
# Test with various edge cases
TASKER_PARALLEL_INSTANCES=0 ./tasker.py test.txt -r -d
TASKER_PARALLEL_INSTANCES=-10 ./tasker.py test.txt -r -d
TASKER_PARALLEL_INSTANCES=abc ./tasker.py test.txt -r -d
TASKER_PARALLEL_INSTANCES=999999 ./tasker.py test.txt -r -d

# All should complete successfully without errors
```

## Conclusion

The fix successfully prevents ZeroDivisionError and handles all edge cases gracefully:
- ✅ Zero values corrected to 1
- ✅ Negative values corrected to 1
- ✅ Non-numeric values default to 1
- ✅ Extremely large values capped at 1000
- ✅ All divisions now safe
- ✅ Informative debug logging added

**Status**: ✅ FIXED AND VERIFIED

---
*Critical bug fix preventing potential production crashes*