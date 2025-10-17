# Resume Capability Test Suite

## Overview
Comprehensive test cases for the `--start-from` resume capability feature in TASKER.

## Purpose
The `--start-from=TASK_ID` parameter allows resuming workflow execution from a specific task, skipping all previous tasks. This is useful for:
- Emergency recovery after workflow interruption
- Development and testing (skip early setup tasks)
- Workflow optimization (continue from a known checkpoint)

## Test Structure

### Directory Organization
```
test_cases/resume/
├── test_resume_from_start.txt
├── test_resume_from_middle.txt
├── test_resume_from_last.txt
├── test_resume_nonexistent_task.txt
├── test_resume_with_task_gap.txt
├── test_resume_before_branch.txt
├── test_resume_into_success_branch.txt
├── test_resume_into_parallel_block.txt
├── test_resume_into_conditional_block.txt
├── test_resume_missing_variables.txt
├── test_resume_with_globals.txt
├── test_resume_variable_chain.txt
├── test_resume_from_zero_explicit.txt
├── test_resume_with_skip_validation.txt
├── test_resume_with_retry.txt
├── test_resume_with_timeout.txt
└── README.md
```

### Test Categories

#### 1. Basic Resume Tests (5 tests)
- **test_resume_from_start.txt**: Resume from task 0 (baseline test)
- **test_resume_from_middle.txt**: Resume from task 5 in 10-task workflow
- **test_resume_from_last.txt**: Resume from final task only
- **test_resume_nonexistent_task.txt**: Resume from non-existent task (negative)
- **test_resume_with_task_gap.txt**: Resume with non-sequential task IDs

#### 2. Flow Control Tests (4 tests)
- **test_resume_before_branch.txt**: Resume before on_success/on_failure branch
- **test_resume_into_success_branch.txt**: Resume directly into routing target
- **test_resume_into_parallel_block.txt**: Resume from parallel coordinator
- **test_resume_into_conditional_block.txt**: Resume from conditional coordinator

#### 3. Variable Tests (3 tests)
- **test_resume_missing_variables.txt**: Resume when task depends on skipped output
- **test_resume_with_globals.txt**: Resume with global variables
- **test_resume_variable_chain.txt**: Resume into variable dependency chain

#### 4. Edge Case Tests (4 tests)
- **test_resume_from_zero_explicit.txt**: Explicit --start-from=0
- **test_resume_with_skip_validation.txt**: Resume with --skip-task-validation
- **test_resume_with_retry.txt**: Resume from task with retry configuration
- **test_resume_with_timeout.txt**: Resume from task with timeout parameter

## Running Tests

### Run All Resume Tests
```bash
python3 test_cases/scripts/intelligent_test_runner.py test_cases/resume/ -r
```

### Run Single Test
```bash
python3 test_cases/scripts/intelligent_test_runner.py test_cases/resume/test_resume_from_middle.txt
```

### Manual Execution
```bash
python3 tasker.py test_cases/resume/test_resume_from_middle.txt -r --start-from=5 --skip-host-validation
```

## Metadata Fields

### Required Fields
```json
{
  "description": "Test description",
  "test_type": "positive|negative",
  "expected_exit_code": 0,
  "expected_success": true,
  "start_from_task": 5,
  "expected_execution_path": [5, 6, 7],
  "skip_host_validation": true,
  "expected_warnings": 1
}
```

### Field Descriptions
- **start_from_task**: Task ID to resume from (integer)
- **expected_execution_path**: Tasks that should execute (array of integers)
- **expected_warnings**: Number of warnings expected (varies based on skipped tasks)
- **skip_host_validation**: Skip host validation to avoid connectivity issues

## Known Limitations

### 1. Variable Dependencies
**Issue**: Tasks that depend on `@N_stdout@`, `@N_exit@`, or `@N_success@` from skipped tasks will have undefined variables.

**Example**: If resuming from task 5, but task 5 uses `@2_stdout@`, the variable will be empty/undefined.

**Workaround**:
- Use global variables for shared data
- Only resume from tasks that don't depend on previous task outputs
- Use state persistence feature (if implemented) to preserve task results

### 2. Warning Count Variations
**Issue**: The number of warnings varies based on how many tasks are skipped:
- 1 warning: Basic resume (host validation skip)
- 3 warnings: Resume with skipped task dependencies
- More warnings: Complex workflows with many dependencies

**Status**: Test metadata may need adjustment for `expected_warnings` values

### 3. State Persistence
**Current Status**: Resume feature does NOT persist state from previous runs. Each execution starts fresh with empty task results.

**Future Enhancement**: Implement state file persistence to preserve task results for true resume capability (see CLAUDE.md).

## Test Status

### Passing Tests
- ✅ test_resume_from_start.txt
- ✅ Basic framework validated
- ✅ Intelligent test runner supports `start_from_task` metadata

### Tests Requiring Adjustment
Several tests may need `expected_warnings` adjustments based on actual warning counts:
- Tests with many skipped tasks generate additional dependency warnings
- Tests with complex routing may generate routing-related warnings

## Development Notes

### Adding New Tests
1. Copy `test_cases/templates/resume_test_template.txt`
2. Update metadata fields (especially `start_from_task` and `expected_execution_path`)
3. Define tasks with appropriate skip points
4. Test manually first to determine actual warning count
5. Run via intelligent test runner for validation

### Metadata Best Practices
- Always set `skip_host_validation: true` to avoid network dependencies
- Set `expected_warnings` based on actual TASKER output (test manually first)
- Use clear task descriptions and comments
- Document expected behavior in comments

## Future Enhancements

1. **State Persistence**: Implement state file saving/loading for true resume
2. **Variable Preservation**: Save task results to allow resuming with dependencies
3. **Checkpoint System**: Automatic checkpoint creation at key workflow points
4. **Resume Validation**: Warn about missing dependencies before execution
5. **Dry-Run Resume**: Show what would execute without actually running

## References

- Main documentation: `/home/baste/tasker/CLAUDE.md`
- Template: `test_cases/templates/resume_test_template.txt`
- Test runner: `test_cases/scripts/intelligent_test_runner.py`
- Feature implementation: `tasker/core/task_executor_main.py` (lines 167-174, 1896-1929)

---

*TASKER Resume Capability Test Suite - Comprehensive Testing for Workflow Resume Functionality*
