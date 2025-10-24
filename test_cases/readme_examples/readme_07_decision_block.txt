# TEST_METADATA: {"description": "README Example: Decision blocks for dynamic routing", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "382-409", "features_demonstrated": ["decision_blocks", "type_decision", "success_criteria", "logical_or", "routing"]}

# Task 0: Check port 80
task=0
hostname=localhost
command=echo
arguments=Port 80 is available
exec=local

# Task 1: Check port 443
task=1
hostname=localhost
command=echo
arguments=Port 443 is available
exec=local

# Task 2: Decision - which port to use?
task=2
type=decision
# At least one port must be available
success=@0_exit@=0|@1_exit@=0
on_success=3
on_failure=99

# Task 3: Next decision - prefer HTTP or HTTPS?
task=3
type=decision
success=@0_exit@=0
on_success=10
on_failure=20

# HTTP path (port 80 available)
task=10
hostname=localhost
command=echo
arguments=Using HTTP connection on port 80
exec=local

# HTTPS path (port 80 not available, use port 443)
task=20
hostname=localhost
command=echo
arguments=Using HTTPS connection on port 443
exec=local

# No ports available path
task=99
hostname=localhost
command=echo
arguments=ERROR: No ports available
exec=local
return=1
