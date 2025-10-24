# TEST_METADATA: {"description": "Conditional task execution with condition parameter - Service check with conditional restart", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Task 0: Check service status
task=0
hostname=localhost
command=echo
arguments=service_running
exec=local

# Task 1: Restart service (only if check succeeded)
task=1
hostname=localhost
# Skip this task if service check failed
condition=@0_exit@=0
command=echo
arguments=Restarting service
exec=local

# Task 2: Send alert (only if check failed)
task=2
hostname=localhost
# Skip this task if service check succeeded
condition=@0_exit@!=0
command=echo
arguments=Service check failed - sending alert
exec=local
