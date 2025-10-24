# TEST_METADATA: {"description": "Complex output processing with awk/sed/perl", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2, 3, 4], "expected_final_task": 4}

# Complex Output Processing with awk/sed/perl
# Demonstrates various text processing utilities for output manipulation

# Generate sample output for processing
task=0
hostname=localhost
command=echo
arguments=Status: error detected in module 3/4 with version 1.5
exec=local

# Using awk for complex extraction (extract 3rd and 4th words)
task=1
hostname=localhost
command=/bin/sh
arguments=-c "echo '@0_stdout@' | awk '{print $3 \" \" $4}'"
exec=local

# Using sed for pattern replacement (replace 'error' with 'warning')
task=2
hostname=localhost
command=/bin/sh
arguments=-c "echo '@0_stdout@' | sed 's/error/warning/gi'"
exec=local

# Using perl one-liner for advanced processing (format version numbers)
task=3
hostname=localhost
command=/bin/sh
arguments=-c "echo '@0_stdout@' | perl -pe 's/(\\d+)\\.(\\d+)/v$1.$2/g'"
exec=local

# Using external script simulation for complex logic
task=4
hostname=localhost
command=echo
arguments=Processed output from task 0: @0_stdout@
exec=local
