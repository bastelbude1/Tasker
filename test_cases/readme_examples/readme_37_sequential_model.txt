# TEST_METADATA: {"description": "Sequential execution model", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2], "expected_final_task": 2}

# Sequential Execution Model
# Task-by-task execution with flow control
# Standard workflow where tasks must complete in order

task=0
hostname=localhost
command=echo
arguments=Stopping application
exec=local

task=1
hostname=localhost
command=echo
arguments=Deploying new version
exec=local

task=2
hostname=localhost
command=echo
arguments=Starting application
exec=local
