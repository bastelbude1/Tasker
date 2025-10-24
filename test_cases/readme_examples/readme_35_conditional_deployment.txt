# TEST_METADATA: {"description": "Deployment approval gating", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2], "expected_final_task": 2}

# Example 3: Conditional Deployment
# Approval gate workflow with conditional deployment
ENVIRONMENT=production

task=0
hostname=localhost
command=echo
arguments=Deployment approved for @ENVIRONMENT@
exec=local

task=1
condition=@0_exit@=0
hostname=localhost
command=echo
arguments=Deploying application version latest to @ENVIRONMENT@-app
exec=local

task=2
condition=@1_exit@=0
hostname=localhost
command=echo
arguments=Deployment verified successfully
exec=local
