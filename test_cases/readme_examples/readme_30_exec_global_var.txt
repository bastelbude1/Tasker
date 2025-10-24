# TEST_METADATA: {"description": "Global variable for exec type - dynamic execution mode", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0], "expected_final_task": 0}

# Global variable for exec type
# EXEC_MODE controls execution mode dynamically
# Can be set to 'local' or 'shell' at runtime

EXEC_MODE=shell

task=0
hostname=localhost
command=echo "Process count:" && ps aux | grep -v grep | wc -l
exec=@EXEC_MODE@
