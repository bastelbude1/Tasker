# TEST_METADATA: {"description": "Output pattern task skipping with multiple conditions - Multi-environment deployment", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 3], "expected_final_task": 3}

# Task 0: Detect environment
task=0
hostname=localhost
command=echo
arguments=staging
exec=local

# Task 1: Production deployment
task=1
# Skip unless output contains "production"
condition=@0_stdout@~production
hostname=localhost
command=echo
arguments=Deploying to production
exec=local

# Task 2: Development deployment
task=2
# Skip unless output contains "development"
condition=@0_stdout@~development
hostname=localhost
command=echo
arguments=Deploying to development
exec=local

# Task 3: Staging deployment
task=3
# Skip unless output contains "staging"
condition=@0_stdout@~staging
hostname=localhost
command=echo
arguments=Deploying to staging
exec=local
