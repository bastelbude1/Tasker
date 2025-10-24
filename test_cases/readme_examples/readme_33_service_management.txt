# TEST_METADATA: {"description": "Basic sequential service management workflow", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2], "expected_final_task": 2}

# Example 1: Basic Sequential Tasks
# Service management workflow (stop -> start -> status)
# Using echo commands instead of systemctl for testing

task=0
hostname=localhost
command=echo
arguments=Stopping nginx service
exec=local

task=1
hostname=localhost
command=echo
arguments=Starting nginx service
exec=local

task=2
hostname=localhost
command=echo
arguments=nginx service is active (running)
exec=local
