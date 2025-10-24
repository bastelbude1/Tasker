# TEST_METADATA: {"description": "Custom success with on_failure routing - Critical operation with error detection", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Task 0: Critical operation
task=0
hostname=localhost
command=echo
arguments=Operation completed successfully
exec=local
# Success: exit 0 AND no errors in stderr
success=exit_0&stderr!~error
# Continue to task 1 if success (default behavior)
# If success criteria not met, jump to task 99
on_failure=99

# Task 1: Continue workflow
task=1
hostname=localhost
command=echo
arguments=Continuing workflow after successful operation
exec=local

# Task 99: Failure alert
task=99
hostname=localhost
command=echo
arguments=Critical operation failed - sending alert
exec=local
