# TEST_METADATA: {"description": "Output pattern routing with stdout matching - Environment detection with branching", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 10], "expected_final_task": 10}

# Task 0: Detect environment
task=0
hostname=localhost
command=echo
arguments=production
exec=local
# Define success as output containing "production"
success=stdout~production
# Jump to production tasks if success
on_success=10
# Jump to non-production tasks if no success
on_failure=20

# Task 10: Production deployment
task=10
hostname=localhost
command=echo
arguments=Deploying to production
exec=local
# Stop here - don't fall through to task 20
next=never

# Task 20: Development deployment
task=20
hostname=localhost
command=echo
arguments=Deploying to development
exec=local
