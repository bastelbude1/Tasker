# TEST_METADATA: {"description": "README Example: Simple sequential workflow", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "202-219", "features_demonstrated": ["sequential_execution", "basic_tasks", "arguments"]}

# Simple sequential tasks - execute in order 0, 1, 2, 3
task=0
hostname=localhost
command=echo
arguments=Stopping service
exec=local

task=1
hostname=localhost
command=echo
arguments=Backing up database
exec=local

task=2
hostname=localhost
command=echo
arguments=Deploying application version 1.2.3
exec=local

task=3
hostname=localhost
command=echo
arguments=Starting service
exec=local
