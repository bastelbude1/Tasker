# TEST_METADATA: {"description": "Parallel execution model with deployment tasks", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Parallel Execution Model
# Multi-threaded execution with aggregation and retry logic
# Deploy to multiple servers simultaneously

# Parallel execution master task
task=0
type=parallel
max_parallel=3
tasks=10,11,12
retry_count=2
retry_delay=5
next=all_success

# Parallel worker tasks - Deploy to multiple web servers
task=10
hostname=localhost
command=echo
arguments=Deploying application to web1
exec=local

task=11
hostname=localhost
command=echo
arguments=Deploying application to web2
exec=local

task=12
hostname=localhost
command=echo
arguments=Deploying application to web3
exec=local

# Success notification
task=1
hostname=localhost
command=echo
arguments=All deployments successful
exec=local

# Failure notification
task=99
hostname=localhost
command=echo
arguments=Deployment failed on one or more servers
exec=local
