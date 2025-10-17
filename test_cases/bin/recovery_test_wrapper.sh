#!/bin/bash
# Recovery Test Wrapper Script
# Runs TASKER twice to test automatic error recovery functionality
#
# Usage: recovery_test_wrapper.sh TASK_FILE [OPTIONS...]
#
# This wrapper:
#   1. Cleans up existing recovery files
#   2. Runs TASKER with --auto-recovery (expects failure)
#   3. Validates recovery file was created
#   4. Runs TASKER again with --auto-recovery (expects success via recovery)
#   5. Validates recovery file was deleted after success
#   6. Returns 0 if all validations pass, 1 otherwise
#
# Exit codes:
#   0 - All tests passed (first run failed, second run succeeded with recovery)
#   1 - Test failed (validation error or unexpected behavior)

set -e

if [ $# -lt 1 ]; then
    echo "ERROR: recovery_test_wrapper.sh requires TASK_FILE parameter" >&2
    echo "Usage: recovery_test_wrapper.sh TASK_FILE [OPTIONS...]" >&2
    exit 1
fi

TASK_FILE="$1"
shift
OPTIONS="$@"

RECOVERY_DIR="$HOME/TASKER/recovery"

# Set PATH to include test helper scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="${SCRIPT_DIR}:${PATH}"

# Derive TEST_ID from task file basename (for state file cleanup)
TEST_ID=$(basename "$TASK_FILE" .txt)
STATE_FILE="/tmp/recovery_test_${TEST_ID}.state"

# Cleanup any existing recovery files and state files
echo "=== Recovery Test Wrapper: Cleaning up existing recovery and state files ==="
rm -f "$RECOVERY_DIR"/*.recovery.json 2>/dev/null || true
rm -f "$STATE_FILE" 2>/dev/null || true

# First run - expect failure and recovery file creation
echo "=== Recovery Test Wrapper: First run (expect failure) ==="
set +e
python3 tasker.py "$TASK_FILE" -r --auto-recovery $OPTIONS
FIRST_EXIT=$?
set -e

echo "=== Recovery Test Wrapper: First run exit code: $FIRST_EXIT ==="

# Validate recovery file was created
RECOVERY_FILES=("$RECOVERY_DIR"/*.recovery.json)
if [ ! -f "${RECOVERY_FILES[0]}" ]; then
    echo "ERROR: Recovery file not created after first run" >&2
    exit 1
fi

echo "=== Recovery Test Wrapper: Recovery file created: ${RECOVERY_FILES[0]} ==="

# Second run - expect success with recovery
echo "=== Recovery Test Wrapper: Second run (expect recovery and success) ==="
set +e
python3 tasker.py "$TASK_FILE" -r --auto-recovery $OPTIONS
SECOND_EXIT=$?
set -e

echo "=== Recovery Test Wrapper: Second run exit code: $SECOND_EXIT ==="

# Validate recovery file was deleted after success
RECOVERY_FILES_AFTER=("$RECOVERY_DIR"/*.recovery.json)
if [ -f "${RECOVERY_FILES_AFTER[0]}" ]; then
    echo "ERROR: Recovery file not deleted after successful second run" >&2
    exit 1
fi

echo "=== Recovery Test Wrapper: Recovery file cleaned up ==="

# Validate exit codes
if [ $FIRST_EXIT -eq 1 ] && [ $SECOND_EXIT -eq 0 ]; then
    echo "=== Recovery Test Wrapper: SUCCESS - All validations passed ==="
    exit 0
else
    echo "ERROR: Unexpected exit codes (first=$FIRST_EXIT, expected=1) (second=$SECOND_EXIT, expected=0)" >&2
    exit 1
fi
