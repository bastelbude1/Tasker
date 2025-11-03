#!/bin/bash
# Recovery Test Wrapper for Missing Environment Variable with -y flag
# First run: Environment variable is set
# Second run: Environment variable is MISSING but -y flag uses saved value

set -e

if [ $# -lt 1 ]; then
    echo "ERROR: recovery_test_wrapper_env_missing.sh requires TASK_FILE parameter" >&2
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
echo "=== Recovery Test Wrapper (Missing Env): Cleaning up ==="
rm -f "$RECOVERY_DIR"/*.recovery.json 2>/dev/null || true
rm -f "$STATE_FILE" 2>/dev/null || true

# First run - with environment variable SET
echo "=== Recovery Test Wrapper (Missing Env): First run (expect failure) ==="
export TASKER_DEPLOY_HOST="server001"
echo "# First run environment: TASKER_DEPLOY_HOST=$TASKER_DEPLOY_HOST"

set +e
tasker "$TASK_FILE" -r "${OPTIONS[@]}"
FIRST_EXIT=$?
set -e

echo "=== Recovery Test Wrapper (Missing Env): First run exit code: $FIRST_EXIT ==="

# Validate recovery file was created
if ! ls "$RECOVERY_DIR"/*.recovery.json >/dev/null 2>&1; then
    echo "ERROR: Recovery file not created after first run" >&2
    exit 1
fi

echo "=== Recovery Test Wrapper (Missing Env): Recovery file created ==="

# Second run - with environment variable MISSING but -y flag set
echo "=== Recovery Test Wrapper (Missing Env): Second run (env var not set, -y flag active) ==="
unset TASKER_DEPLOY_HOST
echo "# Second run environment: TASKER_DEPLOY_HOST is NOT SET (will use saved value with -y)"

set +e
tasker "$TASK_FILE" -r "${OPTIONS[@]}"
SECOND_EXIT=$?
set -e

echo "=== Recovery Test Wrapper (Missing Env): Second run exit code: $SECOND_EXIT ==="

# Validate recovery file was deleted
if ls "$RECOVERY_DIR"/*.recovery.json >/dev/null 2>&1; then
    echo "ERROR: Recovery file not deleted after successful second run" >&2
    exit 1
fi

echo "=== Recovery Test Wrapper (Missing Env): Recovery file cleaned up ==="

# Validate success
if [ $SECOND_EXIT -eq 0 ]; then
    echo "=== Recovery Test Wrapper (Missing Env): SUCCESS - Uses saved values with -y ==="
    exit 0
else
    echo "ERROR: Second run failed (exit code: $SECOND_EXIT)" >&2
    exit 1
fi
