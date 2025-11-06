# JSON Output Feature Test Suite

Comprehensive test cases for the `--output-json` flag feature.

## Test Coverage

### 1. Basic Success Case
**File:** `test_output_simple_success.txt`
- **Purpose:** Verify basic JSON output for successful workflow
- **Tests:** Complete execution, all tasks succeed, correct stats
- **Expected:** status=success, succeeded=3, execution_path=[0,1,2]

### 2. Task Failure Case
**File:** `test_output_task_failure.txt`
- **Purpose:** Verify JSON output when task fails
- **Tests:** Failure detection, failure_info, task counts
- **Expected:** status=failed, succeeded=1, failed=1, execution_path=[0]

### 3. Parallel Block Execution
**File:** `test_output_parallel_block.txt`
- **Purpose:** Verify JSON output for parallel task execution
- **Tests:** All parallel tasks in results, execution path tracking
- **Expected:** All 5 tasks (parallel block + subtasks + continuation) captured

### 4. Conditional Block Execution
**File:** `test_output_conditional_block.txt`
- **Purpose:** Verify JSON output for decision/conditional execution
- **Tests:** Conditional routing, skipped tasks NOT in results
- **Expected:** Only executed branch tasks in execution_path

### 5. Loop Execution
**File:** `test_output_with_loops.txt`
- **Purpose:** Verify JSON output for loop iterations
- **Tests:** Loop iterations in execution_path, task result capture
- **Expected:** Loop tasks properly tracked

### 6. on_success Routing
**File:** `test_output_on_success_routing.txt`
- **Purpose:** Verify JSON output with non-sequential routing
- **Tests:** Execution path shows jump, skipped tasks omitted
- **Expected:** execution_path=[0,10], task 1 NOT in results

### 7. Timeout Scenario
**File:** `test_output_timeout.txt`
- **Purpose:** Verify JSON output when task times out
- **Tests:** Timeout detection, exit code 124, timeout count
- **Expected:** status=failed, timeouts=1, task exit_code=124

### 8. Complex Variables
**File:** `test_output_variables.txt`
- **Purpose:** Verify variable capture in JSON output
- **Tests:** Static, env, multi-word, special char variables
- **Expected:** All variables in output JSON

### 9. Without Auto-Recovery Flag
**File:** `test_output_without_recovery.txt`
- **Purpose:** Verify graceful degradation without --auto-recovery
- **Tests:** Warning logged, no JSON file created
- **Expected:** WARN message, no output file

## Running Tests

### Individual Test
```bash
python3 tasker.py test_cases/output_json/test_output_simple_success.txt \
  -r --auto-recovery --output-json=/tmp/output.json --log-dir=/tmp/test
```

### Verify Output
```bash
jq '.' /tmp/output.json
jq '.execution_summary' /tmp/output.json
```

### Full Suite (Manual)
```bash
for test in test_cases/output_json/test_*.txt; do
    echo "Testing: $test"
    python3 tasker.py "$test" -r --auto-recovery \
      --output-json=/tmp/test_$(basename $test .txt).json \
      --log-dir=/tmp/test_output_json
done
```

## Expected JSON Structure

```json
{
  "workflow_metadata": {
    "task_file": "/path/to/file.txt",
    "execution_id": "hash",
    "status": "success|failed",
    "start_time": "ISO timestamp",
    "end_time": "ISO timestamp",
    "duration_seconds": 0.33,
    "log_file": "/path/to/log"
  },
  "execution_summary": {
    "total_tasks": 3,
    "executed": 3,
    "succeeded": 3,
    "failed": 0,
    "timeouts": 0,
    "execution_path": [0, 1, 2],
    "final_task": 2
  },
  "task_results": {
    "0": {"exit_code": 0, "stdout": "...", "stderr": "", "success": true},
    ...
  },
  "variables": {
    "VAR_NAME": "value",
    ...
  }
}
```

## Test Results

All tests pass successfully:
- ✅ Simple success - Complete JSON with correct stats
- ✅ Task failure - Failed status, failure_info included
- ✅ Parallel block - All parallel tasks captured
- ✅ Conditional block - Only executed branch tasks present
- ✅ Loop execution - Loop iterations tracked
- ✅ on_success routing - Execution path shows jump
- ✅ Timeout - Exit code 124, timeout count correct
- ✅ Variables - All variables captured correctly
- ✅ Without recovery - Warning logged, no file created
