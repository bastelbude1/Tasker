# TEST_METADATA: {"description": "exec=shell with piping - shell features enabled", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0], "expected_final_task": 0}

# exec=shell with piping
# Shell mode enables pipes, redirects, and other shell features
# Example: echo test and grep for it

task=0
hostname=localhost
command=echo "test output" | grep "test" | wc -l
exec=shell
