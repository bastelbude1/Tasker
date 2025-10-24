# TEST_METADATA: {"description": "README Example: Hello World - basic sequential execution", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "145-156", "features_demonstrated": ["sequential_execution", "exec_local", "basic_tasks"]}

# hello.txt - Your first TASKER task file
# Simple sequential execution with local commands

task=0
hostname=localhost
command=echo
arguments=Hello TASKER!
exec=local

task=1
hostname=localhost
command=date
exec=local
