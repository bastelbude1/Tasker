#!/bin/bash
# test_alert.sh - Test alert script for automated testing
# This script logs all TASKER environment variables to a temp file for validation

# Get output file from argument or use default
OUTPUT_FILE="${1:-/tmp/tasker_alert_test.log}"

# Write alert execution timestamp and all environment variables
{
  echo "ALERT_EXECUTED=true"
  echo "ALERT_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')"
  echo "TASKER_LOG_FILE=${TASKER_LOG_FILE:-}"
  echo "TASKER_STATE_FILE=${TASKER_STATE_FILE:-}"
  echo "TASKER_TASK_FILE=${TASKER_TASK_FILE:-}"
  echo "TASKER_FAILED_TASK=${TASKER_FAILED_TASK:-}"
  echo "TASKER_EXIT_CODE=${TASKER_EXIT_CODE:-}"
  echo "TASKER_ERROR=${TASKER_ERROR:-}"
  echo "TASKER_TIMESTAMP=${TASKER_TIMESTAMP:-}"
} > "$OUTPUT_FILE"

exit 0
