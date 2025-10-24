# TEST_METADATA: {"description": "Global variables with service management", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Example 2: With Global Variables
# Global variables for service management
SERVICE=nginx
ENVIRONMENT=production

task=0
hostname=localhost
command=echo
arguments=Restarting @SERVICE@ on @ENVIRONMENT@-web
exec=local

task=1
hostname=localhost
command=echo
arguments=@SERVICE@ is active (running)
exec=local
success=exit_0&stdout~active
