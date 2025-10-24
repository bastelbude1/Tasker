# TEST_METADATA: {"description": "Parallel deployment with automatic retry - Deploy to multiple servers with retry logic", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [10], "expected_final_task": 10, "acceptable_warnings": ["Task dependencies.*0-9.*unresolved", "Tasks 10.*may fail"]}

# Task 10: Parallel deployment with retry
task=10
type=parallel
max_parallel=3
tasks=20,21,22
# Retry each failed task up to 3 times
retry_count=3
# Wait 10 seconds between retries
retry_delay=10
# Continue if majority succeed
next=majority_success

# Task 20: Deploy to server 1
task=20
hostname=localhost
command=echo
arguments=Deploying to server-1
exec=local

# Task 21: Deploy to server 2
task=21
hostname=localhost
command=echo
arguments=Deploying to server-2
exec=local

# Task 22: Deploy to server 3
task=22
hostname=localhost
command=echo
arguments=Deploying to server-3
exec=local
