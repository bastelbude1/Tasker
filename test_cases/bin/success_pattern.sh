#!/bin/bash
set -euo pipefail

# success_pattern.sh [task_id] [success_pattern]
#
# Returns exit code based on task_id and success pattern
# Used for testing multi-task success evaluation conditions
#
# Arguments:
#   task_id: The task ID to check (e.g., 10, 11, 12)
#   success_pattern: Comma-separated list of task IDs that should succeed (e.g., "10,11")
#                    Use "ALL" for all tasks succeed
#                    Use "NONE" for all tasks fail
#
# Returns:
#   0 if task_id is in success_pattern
#   1 if task_id is not in success_pattern
#
# Examples:
#   success_pattern.sh 10 "10,11"     # Task 10 succeeds (exit 0)
#   success_pattern.sh 12 "10,11"     # Task 12 fails (exit 1)
#   success_pattern.sh 10 "ALL"       # Task 10 succeeds (exit 0)
#   success_pattern.sh 10 "NONE"      # Task 10 fails (exit 1)

TASK_ID=${1:-}
PATTERN=${2:-}

# Validate inputs
if [ -z "$TASK_ID" ]; then
    echo "Error: Missing task_id argument" >&2
    exit 2
fi

if [ -z "$PATTERN" ]; then
    echo "Error: Missing success_pattern argument" >&2
    exit 2
fi

# Validate TASK_ID is numeric
if ! [[ "$TASK_ID" =~ ^[0-9]+$ ]]; then
    echo "Error: task_id must be numeric: $TASK_ID" >&2
    exit 2
fi

# Handle special patterns
if [ "$PATTERN" = "ALL" ]; then
    echo "Task $TASK_ID: SUCCESS (pattern=ALL)"
    exit 0
elif [ "$PATTERN" = "NONE" ]; then
    echo "Task $TASK_ID: FAILED (pattern=NONE)"
    exit 1
fi

# Check if TASK_ID is in the success pattern
IFS=',' read -ra SUCCESS_TASKS <<< "$PATTERN"
for success_id in "${SUCCESS_TASKS[@]}"; do
    # Trim whitespace
    success_id=$(echo "$success_id" | xargs)

    if [ "$success_id" = "$TASK_ID" ]; then
        echo "Task $TASK_ID: SUCCESS (pattern=$PATTERN)"
        exit 0
    fi
done

# Task ID not in success pattern - fail
echo "Task $TASK_ID: FAILED (pattern=$PATTERN)"
exit 1
