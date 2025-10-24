# TEST_METADATA: {"description": "Error handler pattern with on_failure only routing", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_warnings": 2, "expected_execution_path": [1, 2], "expected_final_task": 2}

# Error handler pattern with on_failure only
# Task 1 succeeds and continues to task 2
# If task 1 failed, it would jump to task 99

task=1
hostname=localhost
command=echo
arguments=Critical operation succeeded
exec=local
on_failure=99

task=2
hostname=localhost
command=echo
arguments=This executes if task 1 succeeds
exec=local

# Error handler in special range 90-99
task=99
hostname=localhost
command=echo
arguments=Error handler - cleaning up after failure
exec=local
return=1
