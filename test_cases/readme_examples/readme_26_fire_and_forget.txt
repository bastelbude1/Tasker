# TEST_METADATA: {"description": "Fire-and-forget mode - best-effort cleanup continues regardless of failures", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2], "expected_final_task": 2, "note": "Run with --fire-and-forget flag for true fire-and-forget behavior"}

# Fire-and-forget mode - best-effort cleanup
# Each cleanup task continues regardless of individual failures
# Completes cleanup on all servers even if some fail

task=0
hostname=localhost
command=echo
arguments=Cleaning up temporary files on server1
exec=local

task=1
hostname=localhost
command=echo
arguments=Cleaning up log files on server2
exec=local

task=2
hostname=localhost
command=echo
arguments=Cleaning up cache on server3
exec=local
