#!/bin/bash
# conditional_exit.sh [target_iteration]
# Exits with code 0 when counter reaches target iteration, otherwise exit 1
# Used for loop_break testing

COUNTER_FILE="/tmp/conditional_exit_counter_shared"
TARGET=${1:-3}  # Default target is iteration 3

# Initialize or increment counter (with atomic operation)
(
    flock -x 200
    if [ ! -f "$COUNTER_FILE" ]; then
        COUNTER=1
        echo "$COUNTER" > "$COUNTER_FILE"
    else
        COUNTER=$(cat "$COUNTER_FILE")
        COUNTER=$((COUNTER + 1))
        echo "$COUNTER" > "$COUNTER_FILE"
    fi

    echo "Iteration: $COUNTER, Target: $TARGET"

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