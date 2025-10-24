# TEST_METADATA: {"description": "Both on_success AND on_failure routing - divergent paths", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_warnings": 2, "expected_execution_path": [1, 10], "expected_final_task": 10}

# Both on_success AND on_failure routing
# Task 1 determines the execution path
# Success goes to task 10, failure would go to task 99

task=1
hostname=localhost
command=echo
arguments=Check status - returning success
exec=local
on_success=10
on_failure=99

task=10
hostname=localhost
command=echo
arguments=Success path
exec=local

task=99
hostname=localhost
command=echo
arguments=Failure path
exec=local
