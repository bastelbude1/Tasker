# TEST_METADATA: {"description": "Default routing behavior - implicit sequential execution", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Default routing behavior (implicit sequential)
# No routing specified - uses implicit next=success
# Task 0 succeeds and continues to task 1
# If task 0 fails, workflow stops execution

task=0
hostname=localhost
command=echo
arguments=Health check passed
exec=local

task=1
hostname=localhost
command=echo
arguments=Deploying application
exec=local
