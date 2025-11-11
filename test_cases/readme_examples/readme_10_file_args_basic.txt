# TEST_METADATA: {"description": "README Example: File-defined arguments and global variables", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "590-603", "features_demonstrated": ["file_defined_arguments", "global_variables", "variable_substitution", "skip_host_validation"]}

# File-defined arguments (must be at the very top)
--auto-recovery
--log-level=DEBUG

# Global variables come after file-defined arguments
ENVIRONMENT=production
TARGET_HOST=localhost

# Tasks come last
task=0
hostname=@TARGET_HOST@
command=echo
arguments=Deploying to @ENVIRONMENT@ environment on @TARGET_HOST@
exec=local
