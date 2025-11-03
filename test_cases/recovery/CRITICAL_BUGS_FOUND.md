# CRITICAL AUTO-RECOVERY BUGS DISCOVERED

**Date:** 2025-11-03
**Severity:** PRODUCTION CRITICAL
**Status:** UNFIXED - DO NOT USE --auto-recovery WITH AFFECTED FEATURES

---

## Executive Summary

During comprehensive auto-recovery testing (Phase 2), **TWO CRITICAL BUGS** were discovered that cause auto-recovery to resume workflows at INCORRECT TASKS, leading to:
- Wrong branch execution (conditional blocks)
- Wrong routing decisions (parallel blocks)
- Catastrophic workflow failures

**RECOMMENDATION:** DO NOT use `--auto-recovery` in production with conditional blocks or parallel blocks that have routing parameters until these bugs are fixed.

---

## Bug #1: Conditional Block Recovery Resumes in WRONG BRANCH

### Severity: CATASTROPHIC

### Description
When a conditional block completes its if_true_tasks and then a subsequent task fails, recovery INCORRECTLY resumes in the if_false_tasks branch instead of continuing from the failed task.

### Test Case
`test_auto_recovery_conditional_block.txt`

### Reproduction Steps
1. Conditional block (task 1) evaluates condition=true
2. Executes if_true_tasks (10, 11) successfully
3. Continues to task 2 (next sequential task)
4. Task 2 fails → recovery file created
5. Recovery runs with execution_path: [0, 1, 10, 11]
6. **BUG:** Recovery resumes at task 20 (if_false_tasks) instead of task 2

### Expected Behavior
Recovery should resume at task 2 (the task that failed)

### Actual Behavior
```
# Restoring state from recovery file - resuming from task 20
# Previous execution path: [0, 1, 10, 11]
Task 20: Executing [local]: echo ERROR_False_branch_should_not_execute
```

Recovery executes the FALSE branch even though the TRUE branch was taken originally.

### Root Cause Analysis
The recovery logic does not understand conditional block structure:
- Execution path records: [0, 1, 10, 11]
- Last task: 11 (from if_true_tasks)
- Recovery tries to find "next" task after 11
- Incorrectly identifies task 20 (if_false_tasks) as next task
- Does NOT check that task 2 was the intended continuation point

**MISSING STATE:** Routing decision from conditional block not persisted.

### Impact
- **Data Corruption:** Wrong workflow path executed
- **Business Logic Failure:** Incorrect operations performed
- **Audit Trail Corruption:** Execution path shows wrong branches
- **Silent Failure:** No error - workflow completes "successfully" with wrong logic

### Affected Blocks
- Block 5: Conditional Block (type=conditional)
- Block 14: Conditional Block with Retry

---

## Bug #2: Parallel Block Routing Not Persisted

### Severity: CRITICAL

### Description
When a parallel block completes and routes via on_success/on_failure, the routing decision is NOT persisted in recovery state. Recovery resumes at the WRONG task, often jumping to failure handlers when it should continue the success path.

### Test Case
`test_auto_recovery_multi_task_success_min.txt`

### Reproduction Steps
1. Parallel block (task 1) executes subtasks (10-14) successfully
2. min_success=3 condition met (5/5 succeeded)
3. Parallel coordinator routes via on_success=2
4. Task 2 fails → recovery file created
5. Recovery runs with execution_path: [0, 1, 10, 11, 12, 13, 14]
6. **BUG:** Recovery resumes at task 99 (on_failure target) instead of task 2

### Expected Behavior
Recovery should resume at task 2 (on_success route)

### Actual Behavior
```
# Restoring state from recovery file - resuming from task 99
# Previous execution path: [0, 1, 10, 11, 12, 13, 14]
Task 99: Executing [local]: echo ERROR_Failure_handler_should_not_execute
```

Recovery jumps to the FAILURE handler even though parallel block succeeded.

### Root Cause Analysis
The recovery logic does not persist routing decisions:
- Execution path records: [0, 1, 10, 11, 12, 13, 14]
- Last task: 14 (parallel subtask)
- Recovery tries to determine next task from coordinator (task 1)
- Incorrectly evaluates on_failure route instead of on_success
- Does NOT record that on_success routing was taken during original execution

**MISSING STATE:** Routing decision (on_success vs on_failure) not persisted in recovery_data.

### Impact
- **Wrong Error Handling:** Failure handlers execute on success path
- **Workflow Corruption:** Tasks executed in wrong order
- **Alerting Failures:** False positive alerts triggered
- **Data Inconsistency:** Success path skipped, cleanup tasks missed

### Affected Blocks
- Block 10: Parallel Task Block (with on_success/on_failure)
- Block 11: Parallel Task Block with Retry
- Block 12: Parallel Host Block (NEW v2.1)
- Block 13: Parallel Host Block with Retry
- Block 15: Multi-Task Success Evaluation (next)
- Block 16: Multi-Task Success Evaluation (on_success/on_failure)

---

## Tests Successfully Passing

### test_auto_recovery_on_failure_routing.txt ✅
**Scenario:** Task fails, routes to error handler via on_failure, error handler fails, recovery continues

**Why It Works:** Simple sequential routing (task 2 → task 50 → task 51). No coordinator tasks, no parallel blocks, no complex routing logic.

**Execution Path:**
- First run: [0, 1, 2, 50, 51] - task 51 fails
- Recovery: Resumes at task 51 ✅ CORRECT

This test passes because it doesn't involve conditional/parallel blocks with subtasks.

---

## Fundamental Issue: Incomplete Recovery State

### Current State Structure (recovery_state.py lines 125-140)
```python
recovery_data = {
    'execution_path': [0, 1, 10, 11],  # Which tasks executed
    'task_results': {...},             # Outputs from each task
    'global_vars': {...},              # Global variables
    'loop_state': {},                  # TODO: NOT IMPLEMENTED
    # MISSING: Routing decisions!
}
```

### What's Missing
```python
# NEEDED:
'routing_state': {
    1: {'routed_to': 2, 'reason': 'on_success', 'condition_met': True},
    10: {'routed_to': 11, 'reason': 'sequential'},
    11: {'routed_to': 2, 'reason': 'conditional_complete'}
}
```

Without routing state, recovery cannot determine:
1. Which branch a conditional took (if_true vs if_false)
2. Which route a parallel block took (on_success vs on_failure)
3. Where execution should resume after coordinator tasks

---

## Required Fixes

### Fix #1: Add routing_state to Recovery Data
**File:** `tasker/core/recovery_state.py`

**Changes:**
1. Add `'routing_state': {}` to recovery_data structure
2. Populate routing_state when tasks complete with routing decisions
3. Record:
   - task_id that made routing decision
   - target task_id
   - reason (on_success, on_failure, conditional_true, conditional_false, sequential, next_condition)

### Fix #2: Update Resume Logic to Use Routing State
**File:** `tasker/core/task_executor_main.py` (or wherever recovery resume logic lives)

**Changes:**
1. When loading recovery state, check routing_state
2. For conditional blocks: Use routing_state to determine which branch was taken
3. For parallel blocks: Use routing_state to determine on_success vs on_failure route
4. Fall back to execution_path logic only if routing_state missing (backward compatibility)

### Fix #3: Update Conditional/Parallel Executors
**Files:**
- `tasker/executors/conditional_executor.py`
- `tasker/executors/parallel_executor.py`

**Changes:**
1. When routing decision is made, record it in recovery state
2. Pass routing_state to recovery_state_manager.save_state()
3. Ensure routing decisions logged before execution continues

---

## Test Plan After Fixes

### Phase 1: Verify Bug Fixes
1. Run `test_auto_recovery_conditional_block.txt` - should PASS (currently FAILS)
2. Run `test_auto_recovery_multi_task_success_min.txt` - should PASS (currently FAILS)
3. Run `test_auto_recovery_on_failure_routing.txt` - should still PASS

### Phase 2: Regression Testing
1. Run all 7 existing recovery tests (should all still pass)
2. Run all 21 parallel hostnames tests (no regressions)
3. Run full test suite (434 tests)

### Phase 3: Complete Phase 2 Testing
1. Create remaining tests:
   - test_auto_recovery_timeout_elapsed.txt
   - test_auto_recovery_retry_limitation.txt
2. Verify all Phase 2 tests pass
3. Update test metadata from negative to positive

---

## Workarounds (Until Fixed)

### DO NOT Use --auto-recovery With:
- ❌ Conditional blocks (type=conditional)
- ❌ Parallel blocks with on_success/on_failure routing
- ❌ Multi-task success evaluation with routing
- ❌ Decision blocks with on_success/on_failure

### SAFE To Use --auto-recovery With:
- ✅ Simple sequential tasks
- ✅ Tasks with retry_count (no routing)
- ✅ Loops (with limitation: restarts from iteration 1)
- ✅ Parallel blocks WITHOUT routing (but will restart from beginning)
- ✅ Global variables

---

## Priority

**CRITICAL - P0**

These bugs cause INCORRECT WORKFLOW EXECUTION, not just failures. Silent data corruption is worse than loud failures.

**Fix immediately before v2.1 release.**

---

## Related Issues

- Loop state not persisted (TODO comment line 138) - DOCUMENTED limitation
- Retry attempts not persisted - UNDOCUMENTED limitation
- Timeout state not persisted - UNKNOWN behavior

All of these stem from the same fundamental issue: **recovery state is incomplete**.
