# TEST_METADATA: {"description": "Practical disk usage parsing example", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2, 3], "expected_final_task": 3}

# Practical Disk Usage Parsing Example
# Extract disk usage percentage from df output
# Demonstrates stdout_split for field extraction

# Simulate df output with echo (realistic format)
task=0
hostname=localhost
command=echo
arguments=Filesystem      Size  Used Avail Use% Mounted on
exec=local

# Get disk usage line (simulate df -h /data | tail -1)
task=1
hostname=localhost
command=echo
arguments=/dev/sda1       100G   75G   25G  75% /data
exec=local

# Extract and display disk usage line
task=2
hostname=localhost
command=echo
arguments=Disk usage line: @1_stdout@
condition=@1_stdout@~%
exec=local

# Extract 5th column (usage%) using stdout_split
# Note: stdout_split uses zero-based indexing, so index 4 = 5th column
task=3
hostname=localhost
command=echo
arguments=Disk usage percentage: @1_stdout@
condition=@1_stdout@~%
stdout_split=space,4
exec=local
