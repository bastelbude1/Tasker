# TEST_METADATA: {"description": "exec=shell with command substitution - $(whoami) and $(date)", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0], "expected_final_task": 0}

# exec=shell with command substitution
# Shell mode enables command substitution using $()
# Example: Embed whoami and date in output

task=0
hostname=localhost
command=echo
arguments=Deployed by $(whoami) at $(date +%Y-%m-%d)
exec=shell
