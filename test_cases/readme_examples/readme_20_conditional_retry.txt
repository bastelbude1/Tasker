# TEST_METADATA: {"description": "Conditional execution with retry - Environment-based deployment with retry logic", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [29, 30], "expected_final_task": 30, "acceptable_warnings": ["Task dependencies.*0-28.*unresolved", "Tasks 29.*may fail"]}

# Task 29: Detect environment
task=29
hostname=localhost
command=echo
arguments=development
exec=local

# Task 30: Conditional execution with retry
task=30
type=conditional
# Based on previous task output
condition=@29_stdout@~production
if_true_tasks=40,41,42
if_false_tasks=50,51
# Retry failed branch tasks
retry_count=2
# 5 second retry delay
retry_delay=5

# Task 40: Production deployment step 1
task=40
hostname=localhost
command=echo
arguments=Production deployment - step 1
exec=local

# Task 41: Production deployment step 2
task=41
hostname=localhost
command=echo
arguments=Production deployment - step 2
exec=local

# Task 42: Production deployment step 3
task=42
hostname=localhost
command=echo
arguments=Production deployment - step 3
exec=local

# Task 50: Development deployment step 1
task=50
hostname=localhost
command=echo
arguments=Development deployment - step 1
exec=local

# Task 51: Development deployment step 2
task=51
hostname=localhost
command=echo
arguments=Development deployment - step 2
exec=local
