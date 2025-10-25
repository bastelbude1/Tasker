#!/bin/bash
# Simple alert script for TASKER failures
# This script demonstrates basic alert functionality with environment variable access

echo "========================================"
echo "TASKER WORKFLOW FAILURE ALERT"
echo "========================================"
echo "Timestamp:    $TASKER_TIMESTAMP"
echo "Task File:    $TASKER_TASK_FILE"
echo "Failed Task:  $TASKER_FAILED_TASK"
echo "Exit Code:    $TASKER_EXIT_CODE"
echo "Error:        $TASKER_ERROR"
echo "Log File:     $TASKER_LOG_FILE"
echo "State File:   $TASKER_STATE_FILE"
echo "========================================"

# Show last 10 lines of log file if available
if [ -f "$TASKER_LOG_FILE" ]; then
    echo ""
    echo "Recent Log Entries (last 10 lines):"
    echo "----------------------------------------"
    tail -10 "$TASKER_LOG_FILE"
fi

exit 0
