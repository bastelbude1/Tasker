#!/bin/bash

# Signal Test Wrapper for TASKER
# Executes TASKER with task file, sends signal after delay, verifies cleanup
#
# Usage: signal_test_wrapper.sh <task_file> [signal_type] [signal_delay] [second_signal_delay]
#
# If signal parameters are not provided, they will be read from TEST_METADATA in the task file.
#
# Example with explicit parameters:
#   signal_test_wrapper.sh test_sigterm_sequential_basic.txt SIGTERM 2
#
# Example with metadata (reads signal_type, signal_delay_seconds from file):
#   signal_test_wrapper.sh test_sigint_sequential.txt
#
# Returns: Exit code from TASKER (143 for SIGTERM, 130 for SIGINT)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKER_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TASKER_BIN="$TASKER_ROOT/tasker.py"

# Parse arguments
TASK_FILE="$1"

if [ -z "$TASK_FILE" ]; then
    echo "ERROR: Task file required"
    echo "Usage: $0 <task_file> [signal_type] [signal_delay] [second_signal_delay]"
    echo ""
    echo "If signal parameters are omitted, they will be read from TEST_METADATA in the task file."
    exit 1
fi

if [ ! -f "$TASK_FILE" ]; then
    echo "ERROR: Task file not found: $TASK_FILE"
    exit 1
fi

# Function to extract value from JSON metadata
extract_metadata() {
    local field="$1"
    local task_file="$2"

    # Extract TEST_METADATA line and parse JSON field
    grep "TEST_METADATA" "$task_file" | sed 's/.*TEST_METADATA: *//' | grep -o "\"$field\": *[^,}]*" | sed 's/.*: *//' | tr -d '"'
}

# Read parameters from arguments OR metadata
if [ -n "$2" ]; then
    # Explicit arguments provided - use them
    SIGNAL_TYPE="$2"
    SIGNAL_DELAY="${3:-2}"
    SECOND_SIGNAL_DELAY="${4:-0}"
else
    # No arguments - read from TEST_METADATA
    SIGNAL_TYPE=$(extract_metadata "signal_type" "$TASK_FILE")
    SIGNAL_DELAY=$(extract_metadata "signal_delay_seconds" "$TASK_FILE")
    SECOND_SIGNAL_DELAY=$(extract_metadata "second_signal_delay" "$TASK_FILE")

    # Apply defaults if metadata fields are missing
    SIGNAL_TYPE="${SIGNAL_TYPE:-SIGTERM}"
    SIGNAL_DELAY="${SIGNAL_DELAY:-2}"
    SECOND_SIGNAL_DELAY="${SECOND_SIGNAL_DELAY:-0}"

    echo "INFO: Reading signal parameters from TEST_METADATA"
fi

# Temporary files for tracking
TASKER_PID_FILE="/tmp/tasker_signal_test_$$.pid"
TASKER_OUTPUT_FILE="/tmp/tasker_signal_test_$$.out"
TASKER_ERRORS_FILE="/tmp/tasker_signal_test_$$.err"
CLEANUP_REPORT="/tmp/tasker_cleanup_report_$$.txt"

# Cleanup function
cleanup() {
    rm -f "$TASKER_PID_FILE" "$TASKER_OUTPUT_FILE" "$TASKER_ERRORS_FILE" "$CLEANUP_REPORT" 2>/dev/null || true
}

trap cleanup EXIT

echo "=========================================="
echo "TASKER Signal Test Wrapper"
echo "=========================================="
echo "Task File:           $TASK_FILE"
echo "Signal Type:         $SIGNAL_TYPE"
echo "Signal Delay:        ${SIGNAL_DELAY}s"
if [ "$SECOND_SIGNAL_DELAY" != "0" ]; then
    echo "Second Signal Delay: ${SECOND_SIGNAL_DELAY}s"
fi
echo "=========================================="

# Start TASKER in background
echo "[$(date +%H:%M:%S)] Starting TASKER..."
"$TASKER_BIN" "$TASK_FILE" -r --skip-host-validation > "$TASKER_OUTPUT_FILE" 2> "$TASKER_ERRORS_FILE" &
TASKER_PID=$!

echo "$TASKER_PID" > "$TASKER_PID_FILE"
echo "[$(date +%H:%M:%S)] TASKER PID: $TASKER_PID"

# Record child processes before signal
sleep 0.5
echo "[$(date +%H:%M:%S)] Recording process tree..."
CHILD_PIDS=$(pgrep -P "$TASKER_PID" 2>/dev/null || true)
echo "Child PIDs: $CHILD_PIDS"

# Wait for signal delay
echo "[$(date +%H:%M:%S)] Waiting ${SIGNAL_DELAY}s before sending signal..."
sleep "$SIGNAL_DELAY"

# Send first signal
echo "[$(date +%H:%M:%S)] Sending $SIGNAL_TYPE to PID $TASKER_PID..."
if ! kill -s "$SIGNAL_TYPE" "$TASKER_PID" 2>/dev/null; then
    echo "WARNING: Process already exited or not found"
    TASKER_EXIT_CODE=1
else
    # If second signal requested, send it after additional delay
    if [ "$SECOND_SIGNAL_DELAY" != "0" ]; then
        sleep "$SECOND_SIGNAL_DELAY"
        echo "[$(date +%H:%M:%S)] Sending SECOND $SIGNAL_TYPE to PID $TASKER_PID..."
        kill -s "$SIGNAL_TYPE" "$TASKER_PID" 2>/dev/null || echo "Process already exited"
    fi

    # Wait for TASKER to exit (max 15 seconds)
    echo "[$(date +%H:%M:%S)] Waiting for TASKER to exit (max 15s)..."
    WAIT_START=$(date +%s)
    wait "$TASKER_PID" 2>/dev/null || TASKER_EXIT_CODE=$?
    WAIT_END=$(date +%s)
    WAIT_DURATION=$((WAIT_END - WAIT_START))

    echo "[$(date +%H:%M:%S)] TASKER exited after ${WAIT_DURATION}s with code: $TASKER_EXIT_CODE"
fi

# Verification Phase
echo "=========================================="
echo "Cleanup Verification"
echo "=========================================="

# 1. Check for zombie processes
echo -n "Checking for zombie processes... "
ZOMBIES=$(ps aux | grep defunct | grep -v grep || true)
if [ -z "$ZOMBIES" ]; then
    echo "✓ PASS (no zombies)"
else
    echo "✗ FAIL (zombies found):"
    echo "$ZOMBIES"
fi

# 2. Check for orphaned child processes
echo -n "Checking for orphaned processes... "
ORPHANS=""
for PID in $CHILD_PIDS; do
    if ps -p "$PID" > /dev/null 2>&1; then
        ORPHANS="$ORPHANS $PID"
    fi
done

if [ -z "$ORPHANS" ]; then
    echo "✓ PASS (no orphans)"
else
    echo "✗ FAIL (orphaned PIDs: $ORPHANS)"
fi

# 3. Check for temp files
echo -n "Checking for temp files... "
TEMP_FILES=$(ls -la /tmp/tasker_* 2>/dev/null | grep -v signal_test || true)
if [ -z "$TEMP_FILES" ]; then
    echo "✓ PASS (no temp files)"
else
    echo "⚠ WARNING (temp files found):"
    echo "$TEMP_FILES"
fi

# 4. Display TASKER output (full output for test validation)
echo "=========================================="
echo "TASKER Output:"
echo "=========================================="
cat "$TASKER_OUTPUT_FILE" 2>/dev/null || echo "(no output)"

# 5. Display TASKER errors (if any)
if [ -s "$TASKER_ERRORS_FILE" ]; then
    echo "=========================================="
    echo "TASKER Errors:"
    echo "=========================================="
    cat "$TASKER_ERRORS_FILE"
fi

# 6. Verify expected exit code
echo "=========================================="
echo "Exit Code Verification"
echo "=========================================="
EXPECTED_SIGTERM=143  # 128 + 15
EXPECTED_SIGINT=130   # 128 + 2

if [ "$SIGNAL_TYPE" = "SIGTERM" ]; then
    if [ "$TASKER_EXIT_CODE" = "$EXPECTED_SIGTERM" ]; then
        echo "✓ PASS: Exit code $TASKER_EXIT_CODE matches expected ($EXPECTED_SIGTERM)"
    else
        echo "✗ FAIL: Exit code $TASKER_EXIT_CODE does not match expected ($EXPECTED_SIGTERM)"
    fi
elif [ "$SIGNAL_TYPE" = "SIGINT" ]; then
    if [ "$TASKER_EXIT_CODE" = "$EXPECTED_SIGINT" ]; then
        echo "✓ PASS: Exit code $TASKER_EXIT_CODE matches expected ($EXPECTED_SIGINT)"
    else
        echo "✗ FAIL: Exit code $TASKER_EXIT_CODE does not match expected ($EXPECTED_SIGINT)"
    fi
fi

echo "=========================================="
echo "Test Complete"
echo "=========================================="

exit "$TASKER_EXIT_CODE"
