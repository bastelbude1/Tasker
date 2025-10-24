# TEST_METADATA: {"description": "README Example: Service health check with routing", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "50-82", "features_demonstrated": ["success_criteria", "on_success", "on_failure", "next_never", "routing"]}

# health_check.txt - Your first TASKER workflow!
# This example demonstrates basic routing based on success criteria

# Task 0: Check if service is running (simulated with true/false)
task=0
hostname=localhost
command=echo
arguments=Service check: OK
exec=local
# Define success as exit code 0
success=exit_0
# If success (exit code 0), go to task 1
on_success=1
# If failure (exit code not 0), go to task 2
on_failure=2

# Task 1: Log successful status
task=1
hostname=localhost
command=echo
arguments=Service is healthy
exec=local
# STOP here - don't continue to task 2
next=never

# Task 2: Alert about failure (only reached via on_failure=2)
task=2
hostname=localhost
command=echo
arguments=ALERT: Service is down!
exec=local
# After alert, continue to task 3 (default sequential flow)

# Task 3: Try to restart the service
task=3
hostname=localhost
command=echo
arguments=Attempting to restart service...
exec=local
# Workflow ends after restart attempt
