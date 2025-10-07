#!/bin/bash
# retry_controller.sh <max_failures> [success_stdout] [success_stderr] [fail_stdout] [fail_stderr]
#
# Fails exactly max_failures times, then succeeds
# Uses process ownership tracking for test isolation
# Supports custom stdout/stderr for success and failure
#
# Examples:
#   retry_controller.sh 2                         # Fails 2 times, then succeeds
#   retry_controller.sh 1 "SUCCESS" "NONE"        # Fails once with default, then outputs SUCCESS
#   retry_controller.sh 2 "OK" "NONE" "FAIL" "ERROR"  # Custom messages for all states

# Validate arguments
if [ $# -lt 1 ]; then
    echo "Usage: retry_controller.sh <max_failures> [success_stdout] [success_stderr] [fail_stdout] [fail_stderr]" >&2
    echo "  max_failures: Number of times to fail before succeeding (1-100)" >&2
    echo "  success_stdout: Message for stdout on success (default: 'Task succeeded after retries')" >&2
    echo "  success_stderr: Message for stderr on success (default: 'NONE')" >&2
    echo "  fail_stdout: Message for stdout on failure (default: 'Task failed - will retry')" >&2
    echo "  fail_stderr: Message for stderr on failure (default: 'Temporary failure')" >&2
    exit 1
fi

MAX_FAILURES="${1}"
SUCCESS_STDOUT="${2:-Task succeeded after retries}"
SUCCESS_STDERR="${3:-NONE}"
FAIL_STDOUT="${4:-Task failed - will retry}"
FAIL_STDERR="${5:-Temporary failure}"

# Validate max_failures is a positive integer
if ! [[ "$MAX_FAILURES" =~ ^[0-9]+$ ]] || [ "$MAX_FAILURES" -le 0 ] || [ "$MAX_FAILURES" -gt 100 ]; then
    echo "Error: max_failures must be a positive integer between 1 and 100" >&2
    exit 1
fi

# Use unique counter file based on max_failures to allow multiple instances
COUNTER_FILE="/tmp/retry_controller_${MAX_FAILURES}_counter"
OWNER=${RETRY_CONTROLLER_OWNER:-$PPID}

# Atomic counter increment with ownership tracking
(
    flock -x 200

    if [ ! -f "$COUNTER_FILE" ]; then
        COUNTER=1
    else
        read -r STORED_OWNER STORED_COUNTER < "$COUNTER_FILE" 2>/dev/null || STORED_OWNER=
        if [ "$STORED_OWNER" = "$OWNER" ] && [[ "$STORED_COUNTER" =~ ^[0-9]+$ ]]; then
            COUNTER=$((STORED_COUNTER + 1))
        else
            # Different owner or invalid counter - reset to 1
            COUNTER=1
        fi
    fi

    # Store owner and counter
    printf '%s %s\n' "$OWNER" "$COUNTER" > "$COUNTER_FILE"

    # Debug output to stderr (only in debug mode)
    if [ "${DEBUG:-0}" = "1" ]; then
        echo "[DEBUG] retry_controller: max_failures=$MAX_FAILURES, counter=$COUNTER, owner=$OWNER" >&2
    fi

    if [ "$COUNTER" -le "$MAX_FAILURES" ]; then
        # Fail case
        [ "$FAIL_STDOUT" != "NONE" ] && echo "$FAIL_STDOUT"
        [ "$FAIL_STDERR" != "NONE" ] && echo "$FAIL_STDERR" >&2
        exit 1
    else
        # Success case - reset counter for next test
        rm -f "$COUNTER_FILE"
        [ "$SUCCESS_STDOUT" != "NONE" ] && echo "$SUCCESS_STDOUT"
        [ "$SUCCESS_STDERR" != "NONE" ] && echo "$SUCCESS_STDERR" >&2
        exit 0
    fi
) 200>"${COUNTER_FILE}.lock"