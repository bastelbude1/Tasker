# TEST_METADATA: {"description": "README Example: Sequential workflow with on_success/on_failure routing", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "241-263", "features_demonstrated": ["on_success", "on_failure", "success_criteria", "routing", "return"]}

# Jump to different tasks based on success/failure
task=0
hostname=localhost
command=echo
arguments=Deployment complete
exec=local
# Custom success criteria
success=exit_0&stdout~complete
# Jump to task 5 on success
on_success=5
# Jump to task 99 on failure
on_failure=99

# Success path
task=5
hostname=localhost
command=echo
arguments=Verifying deployment
exec=local

# Failure path
task=99
hostname=localhost
command=echo
arguments=ALERT: Deployment failed
exec=local
return=1
