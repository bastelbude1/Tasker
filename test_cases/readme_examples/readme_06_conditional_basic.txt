# TEST_METADATA: {"description": "README Example: Conditional block with if_true/if_false branches", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_warnings": 2, "source_readme_lines": "309-324", "features_demonstrated": ["conditional_execution", "condition", "if_true_tasks", "if_false_tasks", "retry_count", "all_success"]}

# Task 4: Produce output for conditional check
task=4
hostname=localhost
command=echo
arguments=production
exec=local

# Conditional block - branch based on condition
task=5
# Required
type=conditional
# Required: Expression to evaluate
condition=@4_stdout@~production
# Execute if TRUE (custom order)
if_true_tasks=200,201,202
# Execute if FALSE (custom order)
if_false_tasks=300,301
# Retry failed tasks
retry_count=2
# All branch tasks must succeed
success=all_success
# Jump if condition met
on_success=10

# TRUE branch tasks (production environment)
task=200
hostname=localhost
command=echo
arguments=Production deployment step 1
exec=local

task=201
hostname=localhost
command=echo
arguments=Production deployment step 2
exec=local

task=202
hostname=localhost
command=echo
arguments=Production deployment step 3
exec=local

# FALSE branch tasks (non-production environment)
task=300
hostname=localhost
command=echo
arguments=Non-production deployment step 1
exec=local

task=301
hostname=localhost
command=echo
arguments=Non-production deployment step 2
exec=local

# Success path
task=10
hostname=localhost
command=echo
arguments=Conditional execution completed successfully
exec=local
