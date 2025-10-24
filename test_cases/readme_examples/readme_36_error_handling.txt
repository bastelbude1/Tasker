# TEST_METADATA: {"description": "Success/failure notifications", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Example 4: Error Handling
# Deployment with failure/success handling

task=0
hostname=localhost
command=echo
arguments=Application deployed successfully
exec=local

task=1
condition=@0_exit@=0
hostname=localhost
command=echo
arguments=SUCCESS: Deployment completed
exec=local

task=99
condition=@0_exit@!=0
hostname=localhost
command=echo
arguments=FAILURE: Deployment failed - @0_stderr@
exec=local
