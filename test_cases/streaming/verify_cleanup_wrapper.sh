#!/bin/bash
# Wrapper script to verify temp file cleanup after workflow completion
# This script:
# 1. Runs the TASKER workflow with --output-json
# 2. Extracts temp file paths from the JSON output
# 3. Verifies that temp files no longer exist after workflow completion

set -e  # Exit on error

TASK_FILE="$1"
JSON_OUTPUT="/tmp/cleanup_test_output.json"

# Remove old JSON output if exists
rm -f "$JSON_OUTPUT"

# Run TASKER workflow
# Note: --output-json is already specified in the task file
python3 ../../tasker.py "$TASK_FILE" -r --no-task-backup

# Check if JSON output was created
if [ ! -f "$JSON_OUTPUT" ]; then
    echo "ERROR: JSON output file not created: $JSON_OUTPUT"
    exit 1
fi

# Extract temp file paths from JSON and verify they don't exist
python3 << 'EOF'
import json
import os
import sys

with open('/tmp/cleanup_test_output.json', 'r') as f:
    data = json.load(f)

# Check task results for temp file paths
cleanup_verified = True
temp_files_found = []

for task_id, result in data.get('task_results', {}).items():
    stdout_file = result.get('stdout_file')
    stderr_file = result.get('stderr_file')

    if stdout_file:
        temp_files_found.append(('stdout', task_id, stdout_file))
        if os.path.exists(stdout_file):
            print(f"ERROR: Task {task_id} stdout temp file still exists: {stdout_file}")
            cleanup_verified = False

    if stderr_file:
        temp_files_found.append(('stderr', task_id, stderr_file))
        if os.path.exists(stderr_file):
            print(f"ERROR: Task {task_id} stderr temp file still exists: {stderr_file}")
            cleanup_verified = False

if not temp_files_found:
    print("WARNING: No temp files were created (output might have been <1MB)")
    sys.exit(0)

if cleanup_verified:
    print(f"SUCCESS: All {len(temp_files_found)} temp files cleaned up correctly")
    for stream_type, task_id, path in temp_files_found:
        print(f"  Task {task_id} {stream_type}: {path} (deleted ✓)")
    sys.exit(0)
else:
    print(f"FAILURE: Some temp files were not cleaned up")
    sys.exit(1)
EOF
