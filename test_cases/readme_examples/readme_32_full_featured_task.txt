# TEST_METADATA: {"description": "All parameters example showing every possible parameter", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2, 3, 4, 5], "expected_final_task": 5}

# Global variable for conditional execution
READY=true

# Minimal task (task 0)
task=0
hostname=localhost
command=date
exec=local

# Full-featured task showing all possible parameters (without loop to avoid complexity)
task=1
hostname=localhost
command=echo
arguments=Deployment v2.0 to production: deployed successfully
exec=local
timeout=300
sleep=10
condition=@READY@=true
success=exit_0
on_success=2
on_failure=18

# Parallel task showing all parallel parameters
task=2
type=parallel
max_parallel=5
tasks=6,7,8,9,10
retry_count=2
retry_delay=5
next=min_success=3

# Conditional task showing all conditional parameters
task=3
type=conditional
condition=@2_success@=true
if_true_tasks=12,13,14
if_false_tasks=15,16,17
next=all_success

# Success completion
task=4
hostname=localhost
command=echo
arguments=All tasks completed successfully
exec=local

# Firewall to prevent sequential execution into parallel and conditional subtasks
task=5
return=0

# Parallel worker tasks
task=6
hostname=localhost
command=echo
arguments=Worker 1 complete
exec=local

task=7
hostname=localhost
command=echo
arguments=Worker 2 complete
exec=local

task=8
hostname=localhost
command=echo
arguments=Worker 3 complete
exec=local

task=9
hostname=localhost
command=echo
arguments=Worker 4 complete
exec=local

task=10
hostname=localhost
command=echo
arguments=Worker 5 complete
exec=local

# Firewall for conditional subtasks
task=11
return=0

# True path tasks (executed by conditional)
task=12
hostname=localhost
command=echo
arguments=True path task 12
exec=local

task=13
hostname=localhost
command=echo
arguments=True path task 13
exec=local

task=14
hostname=localhost
command=echo
arguments=True path task 14
exec=local

# False path tasks (won't execute in this test)
task=15
hostname=localhost
command=echo
arguments=False path task 15
exec=local

task=16
hostname=localhost
command=echo
arguments=False path task 16
exec=local

task=17
hostname=localhost
command=echo
arguments=False path task 17
exec=local

# Return task showing return parameter
task=18
hostname=localhost
command=echo
arguments=Workflow complete
exec=local
return=1
