# TEST_METADATA: {"description": "Exit code-based routing with on_success/on_failure - API health check with branching", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Task 0: Health check
task=0
hostname=localhost
command=echo
arguments=healthy
exec=local
# Define success as exit code 0
success=exit_0
# Jump to task 1 if health check passed
on_success=1
# Jump to task 2 if health check failed
on_failure=2

# Task 1: Success notification
task=1
hostname=localhost
command=echo
arguments=API is healthy
exec=local
# Stop here - don't continue to task 2
next=never

# Task 2: Failure notification
task=2
hostname=localhost
command=echo
arguments=API health check failed
exec=local
