#!/bin/bash
# Wrapper script to verify temp file cleanup
# Usage: verify_cleanup_wrapper.sh <test_file>

set -eo pipefail

TEST_FILE="$1"
TEMP_DIR="${TMPDIR:-/tmp}"
TASKER_BIN="../../tasker.py"

echo "=== Temp File Cleanup Verification ==="
echo "Test file: $TEST_FILE"
echo "Temp directory: $TEMP_DIR"
echo ""

# Count temp files before execution
echo "Checking for existing tasker temp files..."
BEFORE_COUNT=$(find "$TEMP_DIR" -name "tasker_stdout_*" -o -name "tasker_stderr_*" 2>/dev/null | wc -l)
echo "Temp files before: $BEFORE_COUNT"

# Get list of existing temp files (to exclude from after check)
EXISTING_FILES=$(mktemp)
find "$TEMP_DIR" -name "tasker_stdout_*" -o -name "tasker_stderr_*" 2>/dev/null | sort > "$EXISTING_FILES"

echo ""
echo "Running tasker with test file..."
# Run tasker
if ! "$TASKER_BIN" "$TEST_FILE" --skip-host-validation --skip-security-validation; then
    echo "ERROR: Tasker execution failed"
    rm -f "$EXISTING_FILES"
    exit 1
fi

echo ""
echo "Checking for temp files after execution..."
# Count temp files after execution (excluding pre-existing ones)
CURRENT_FILES=$(mktemp)
find "$TEMP_DIR" -name "tasker_stdout_*" -o -name "tasker_stderr_*" 2>/dev/null | sort > "$CURRENT_FILES"

# Find new files (files in CURRENT_FILES but not in EXISTING_FILES)
NEW_FILES=$(comm -13 "$EXISTING_FILES" "$CURRENT_FILES")
NEW_COUNT=$(echo "$NEW_FILES" | grep -c . || true)

echo "New temp files after execution: $NEW_COUNT"

# Cleanup temp files
rm -f "$EXISTING_FILES" "$CURRENT_FILES"

# Verify no new temp files remain
if [ "$NEW_COUNT" -gt 0 ]; then
    echo ""
    echo "ERROR: Found $NEW_COUNT temp files that were not cleaned up:"
    echo "$NEW_FILES"
    echo ""
    echo "VERIFICATION FAILED: Temp files were not properly cleaned up!"
    exit 1
fi

echo ""
echo "SUCCESS: All temp files were properly cleaned up!"
exit 0
