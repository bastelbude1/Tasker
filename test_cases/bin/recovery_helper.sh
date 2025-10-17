#!/bin/bash
# Recovery Helper Script
# Stateful helper that fails on first execution, succeeds on second
#
# Usage: recovery_helper.sh TEST_ID
#
# The TEST_ID parameter ensures isolation between different test cases
# by creating unique state files per test.
#
# Behavior:
#   First run:  Creates state file, exits with code 1 (failure)
#   Second run: Removes state file, exits with code 0 (success)

set -e

if [ $# -ne 1 ]; then
    echo "ERROR: recovery_helper.sh requires TEST_ID parameter" >&2
    echo "Usage: recovery_helper.sh TEST_ID" >&2
    exit 2
fi

TEST_ID="$1"
STATE_FILE="/tmp/recovery_test_${TEST_ID}.state"

if [ -f "$STATE_FILE" ]; then
    # Second attempt - simulate success
    echo "Recovery helper: Second attempt detected - simulating success"
    rm -f "$STATE_FILE"
    exit 0
else
    # First attempt - simulate failure
    echo "Recovery helper: First attempt detected - simulating failure"
    touch "$STATE_FILE"
    exit 1
fi
