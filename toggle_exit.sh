#!/bin/bash
# Simple script that alternates between exit codes 0 and 1 based on timestamp

# Get current second
SECOND=$(date +%S)

# Exit 0 for even seconds, exit 1 for odd seconds
if [ $((SECOND % 2)) -eq 0 ]; then
    echo "Toggle: SUCCESS (even second: $SECOND)"
    exit 0
else
    echo "Toggle: FAILURE (odd second: $SECOND)"
    exit 1
fi
