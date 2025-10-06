#!/bin/bash
set -euo pipefail
# shellcheck disable=SC2086

# conditional_exit.sh [target_iteration]
# Exits with code 0 when counter reaches target iteration, otherwise exit 1
# Used for loop_break testing

COUNTER_FILE="/tmp/conditional_exit_counter_shared"
TARGET=${1:-3}  # Default target is iteration 3

# Validate TARGET is a positive integer
if ! [[ "$TARGET" =~ ^[0-9]+$ ]] || [ "$TARGET" -le 0 ]; then
    echo "Error: Invalid target iteration: $TARGET (must be positive integer)" >&2
    exit 2
fi

# Initialize or increment counter (with atomic operation and process ownership)
(
    flock -x 200

    # Use CONDITIONAL_EXIT_OWNER env var if set, otherwise use parent process ID
    # This allows test isolation while supporting manual testing
    OWNER=${CONDITIONAL_EXIT_OWNER:-$PPID}

    if [ ! -f "$COUNTER_FILE" ]; then
        COUNTER=1
    else
        # Read owner and counter from file
        read -r STORED_OWNER STORED_COUNTER < "$COUNTER_FILE" || STORED_OWNER=

        # Only increment if same owner and counter is valid
        if [ "$STORED_OWNER" = "$OWNER" ] && [[ "$STORED_COUNTER" =~ ^[0-9]+$ ]]; then
            COUNTER=$((STORED_COUNTER + 1))
        else
            # Different owner or invalid counter - reset to 1
            COUNTER=1
        fi
    fi

    # Store owner and counter
    printf '%s %s\n' "$OWNER" "$COUNTER" > "$COUNTER_FILE"

    echo "Iteration: $COUNTER, Target: $TARGET (Owner: $OWNER)"

    # Check if we've reached the target
    if [ "$COUNTER" -eq "$TARGET" ]; then
        echo "Target reached! Breaking loop."
        rm -f "$COUNTER_FILE"  # Cleanup
        exit 0
    else
        echo "Continue looping..."
        exit 1
    fi
) 200>"$COUNTER_FILE.lock"