# TEST_METADATA: {"description": "exec=local simple command execution", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0], "expected_final_task": 0}

# exec=local - Simple local command execution
# Executes command directly without shell interpretation

task=0
hostname=localhost
command=date
exec=local
