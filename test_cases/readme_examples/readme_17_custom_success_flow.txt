# TEST_METADATA: {"description": "Custom success criteria with next=success - Database backup with completion verification", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1], "expected_final_task": 1}

# Task 0: Database backup
task=0
hostname=localhost
command=echo
arguments=Backup complete: 100% finished
exec=local
# Must complete AND show 100%
success=exit_0&stdout~100%
# Continue ONLY if success criteria met
next=success

# Task 1: Backup success notification
task=1
hostname=localhost
command=echo
arguments=Backup notification sent
exec=local
