#!/bin/bash
# Wrapper script to verify temp file cleanup after workflow completion
# This script:
# 1. Runs the TASKER workflow with --output-json
# 2. Extracts temp file paths from the JSON output
# 3. Verifies that temp files no longer exist after workflow completion

set -e  # Exit on error

# Validate arguments
if [ -z "$1" ]; then
    echo "ERROR: Task file argument required"
    echo "Usage: $0 <task_file>"
    exit 1
fi

TASK_FILE="$1"
# Use unique name to avoid parallel test conflicts
JSON_OUTPUT="/tmp/cleanup_test_output_$$.json"

# Remove old JSON output if exists
rm -f "$JSON_OUTPUT"

# Run TASKER workflow (use script directory for relative path)
# Override --output-json from task file with our unique path
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/../../tasker.py" "$TASK_FILE" -r --no-task-backup --output-json="$JSON_OUTPUT"

# Check if JSON output was created
if [ ! -f "$JSON_OUTPUT" ]; then
    echo "ERROR: JSON output file not created: $JSON_OUTPUT"
    exit 1
fi

# Extract temp file paths from JSON and verify they don't exist
# Pass JSON_OUTPUT path as argument to Python script
python3 - "$JSON_OUTPUT" << 'EOF'
import json
import os
import sys

# Get JSON path from command line argument
if len(sys.argv) < 2:
    print("ERROR: JSON output path not provided")
    print("Usage: python3 script.py <json_output_path>")
    sys.exit(1)

json_path = sys.argv[1]

with open(json_path, 'r') as f:
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
