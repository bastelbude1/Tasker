# TEST_METADATA: {"description": "README Example: Parallel block with max_parallel and min_success", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "271-287", "features_demonstrated": ["parallel_execution", "max_parallel", "retry_count", "min_success", "on_success", "on_failure"], "expected_warnings": 2}

# Parallel block - execute tasks 100-104 concurrently
task=1
# Required
type=parallel
# Required: Task IDs to execute
tasks=100,101,102,103,104
# Limit concurrent execution (default: 8 if not specified)
max_parallel=5
# Retry failed tasks up to 3 times
retry_count=3
# At least 3 must succeed
success=min_success=3
# Jump if condition met
on_success=10
# Jump if condition not met
on_failure=99

# Subtasks for parallel execution
task=100
hostname=localhost
command=echo
arguments=Parallel task 100 executing
exec=local

task=101
hostname=localhost
command=echo
arguments=Parallel task 101 executing
exec=local

task=102
hostname=localhost
command=echo
arguments=Parallel task 102 executing
exec=local

task=103
hostname=localhost
command=echo
arguments=Parallel task 103 executing
exec=local

task=104
hostname=localhost
command=echo
arguments=Parallel task 104 executing
exec=local

# Success path
task=10
hostname=localhost
command=echo
arguments=Parallel execution succeeded
exec=local

# Failure path
task=99
hostname=localhost
command=echo
arguments=Parallel execution failed
exec=local
return=1
