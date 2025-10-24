# TEST_METADATA: {"description": "README Example: Loop with break condition", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "417-429", "features_demonstrated": ["loop", "loop_break", "stdout_pattern", "sleep", "next_loop"]}

task=0
hostname=localhost
command=echo
arguments=Service status: HEALTHY
exec=local
# Execute exactly 10 times (Task 0.1 through 0.10)
loop=10
next=loop
# Break loop when output contains "HEALTHY"
loop_break=stdout~HEALTHY
# Wait 5 seconds between loop iterations
sleep=5
# Custom success criteria
success=exit_0
