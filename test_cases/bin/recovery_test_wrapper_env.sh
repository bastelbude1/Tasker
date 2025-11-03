#!/bin/bash
# Recovery Test Wrapper for Environment Variable Re-expansion
# Runs TASKER twice with DIFFERENT environment variables to test re-expansion

set -e

if [ $# -lt 1 ]; then
    echo "ERROR: recovery_test_wrapper_env.sh requires TASK_FILE parameter" >&2
    exit 1
fi

TASK_FILE="$1"
shift
OPTIONS=("$@")

RECOVERY_DIR="$HOME/TASKER/recovery"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="${SCRIPT_DIR}:${PATH}"

# Derive TEST_ID from task file basename
TEST_ID=$(basename "$TASK_FILE" .txt)
STATE_FILE="/tmp/recovery_test_${TEST_ID}.state"

# Cleanup
echo "=== Recovery Test Wrapper (Env): Cleaning up ==="
rm -f "$RECOVERY_DIR"/*.recovery.json 2>/dev/null || true
rm -f "$STATE_FILE" 2>/dev/null || true

# First run - with initial environment
echo "=== Recovery Test Wrapper (Env): First run (expect failure) ==="
export TASKER_DEPLOY_HOST="server001"
export TASKER_BUILD_ID="build-12345"
echo "# First run environment: TASKER_DEPLOY_HOST=$TASKER_DEPLOY_HOST, TASKER_BUILD_ID=$TASKER_BUILD_ID"

set +e
tasker "$TASK_FILE" -r --auto-recovery "${OPTIONS[@]}"
FIRST_EXIT=$?
set -e

echo "=== Recovery Test Wrapper (Env): First run exit code: $FIRST_EXIT ==="

# Validate recovery file was created
RECOVERY_FILES=("$RECOVERY_DIR"/*.recovery.json)
if [ ! -f "${RECOVERY_FILES[0]}" ]; then
    echo "ERROR: Recovery file not created after first run" >&2
    exit 1
fi

echo "=== Recovery Test Wrapper (Env): Recovery file created ==="

# Second run - with CHANGED environment (simulates changed deployment target)
echo "=== Recovery Test Wrapper (Env): Second run (expect recovery with re-expansion) ==="
export TASKER_DEPLOY_HOST="server002"
export TASKER_BUILD_ID="build-67890"
echo "# Second run environment: TASKER_DEPLOY_HOST=$TASKER_DEPLOY_HOST, TASKER_BUILD_ID=$TASKER_BUILD_ID"

set +e
tasker "$TASK_FILE" -r --auto-recovery "${OPTIONS[@]}"
SECOND_EXIT=$?
set -e

echo "=== Recovery Test Wrapper (Env): Second run exit code: $SECOND_EXIT ==="

# Validate recovery file was deleted
RECOVERY_FILES_AFTER=("$RECOVERY_DIR"/*.recovery.json)
if [ -f "${RECOVERY_FILES_AFTER[0]}" ]; then
    echo "ERROR: Recovery file not deleted after successful second run" >&2
    exit 1
fi

echo "=== Recovery Test Wrapper (Env): Recovery file cleaned up ==="

# Validate success
if [ $SECOND_EXIT -eq 0 ]; then
    echo "=== Recovery Test Wrapper (Env): SUCCESS - Re-expansion works ==="
    exit 0
else
    echo "ERROR: Second run failed (exit code: $SECOND_EXIT)" >&2
    exit 1
fi
