# TEST_METADATA: {"description": "Conditional execution model with environment detection", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2, 3], "expected_final_task": 3}

# Conditional Execution Model
# Dynamic workflow branching based on runtime conditions
# Choose deployment path based on detected environment

# Environment detection
task=0
hostname=localhost
command=echo
arguments=production
exec=local

# Conditional execution based on environment
task=1
type=conditional
condition=@0_stdout@~production
if_true_tasks=10,11
if_false_tasks=20,21
next=all_success

# Success notification
task=2
hostname=localhost
command=echo
arguments=Deployment completed successfully
exec=local

# Firewall to prevent sequential execution
task=3
return=0

# Failure handler
task=99
hostname=localhost
command=echo
arguments=Deployment failed
exec=local

# Production deployment tasks (executed only by conditional)
task=10
hostname=localhost
command=echo
arguments=Deploying to production environment
exec=local

task=11
hostname=localhost
command=echo
arguments=Updating production load balancer
exec=local

# Development deployment tasks (executed only by conditional)
task=20
hostname=localhost
command=echo
arguments=Deploying to development environment
exec=local

task=21
hostname=localhost
command=echo
arguments=Running integration tests
exec=local
