# TEST_METADATA: {"description": "Explicit routing for clarity with on_success and on_failure", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Explicit routing for clarity
# Task 0 has explicit next=success and routing defined
# Success continues to task 1, failure would go to task 99

task=0
hostname=localhost
command=echo
arguments=Health check passed
exec=local
on_success=1
on_failure=99

task=1
hostname=localhost
command=echo
arguments=Deploying application
exec=local

task=99
hostname=localhost
command=echo
arguments=Rolling back changes
exec=local
