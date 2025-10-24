# TEST_METADATA: {"description": "Success-only routing pattern - jumps to task 5 on success", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_warnings": 2, "expected_execution_path": [1, 5], "expected_final_task": 5, "expected_skipped_tasks": [2, 3, 4]}

# Success-only routing pattern
# Task 1 succeeds and jumps to task 5, skipping task 2
# If task 1 failed, workflow would exit with code 10

task=1
hostname=localhost
command=echo
arguments=Critical check passed
exec=local
on_success=5

task=2
hostname=localhost
command=echo
arguments=Skipped if task 1 succeeds
exec=local

task=5
hostname=localhost
command=echo
arguments=Critical check passed - continuing
exec=local
