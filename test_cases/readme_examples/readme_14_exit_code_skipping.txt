# TEST_METADATA: {"description": "Exit code-based task skipping with condition - Health check with conditional deployment", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Task 0: API health check
task=0
hostname=localhost
command=echo
arguments=healthy
exec=local

# Task 1: Deploy if healthy
task=1
# Skip this task if health check failed
condition=@0_exit@=0
hostname=localhost
command=echo
arguments=Deploying new version
exec=local

# Task 2: Send alert if unhealthy
task=2
# Skip this task if health check succeeded
condition=@0_exit@!=0
hostname=localhost
command=echo
arguments=Sending failure alert
exec=local
