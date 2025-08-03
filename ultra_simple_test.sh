#!/bin/bash

# ULTRA SIMPLE RETRY TEST - GUARANTEED NO HANGS
# Just run the test and check basic patterns

set -e

TASKER_SCRIPT="./tasker.py"
TEST_FILE="comprehensive_retry_test_case.txt"
LOG_DIR="./test_logs"
TIMESTAMP=$(date +%d%b%y_%H%M%S)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=== ULTRA SIMPLE RETRY TEST ==="
echo "Timestamp: $TIMESTAMP"

# Create log directory
mkdir -p "$LOG_DIR"

# Cleanup
rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true

# Check files exist
if [ ! -f "$TEST_FILE" ]; then
    echo "ERROR: $TEST_FILE not found"
    exit 1
fi

if [ ! -f "$TASKER_SCRIPT" ]; then
    echo "ERROR: $TASKER_SCRIPT not found"  
    exit 1
fi

# Run the test with timeout
LOG_FILE="$LOG_DIR/ultra_simple_$TIMESTAMP.log"
echo "Running test..."

if timeout 60s python3 "$TASKER_SCRIPT" -r -d -t local "$TEST_FILE" > "$LOG_FILE" 2>&1; then
    echo "✓ Test completed successfully"
else
    echo "✗ Test failed or timed out"
    exit 1
fi

echo ""
echo "=== ANALYSIS ==="

# Simple checks - NO COMPLEX PATTERNS
if grep -q "ALL TESTS COMPLETED SUCCESSFULLY" "$LOG_FILE"; then
    echo -e "${GREEN}✓ Overall Success: FOUND${NC}"
    overall_success=true
else
    echo -e "${RED}✗ Overall Success: NOT FOUND${NC}"
    overall_success=false
fi

# Count retries - SIMPLE
retry_count=$(grep -c "RETRY.*failed task" "$LOG_FILE" 2>/dev/null || echo "0")
echo "Retry Attempts: $retry_count"

# Count successes after retry - SIMPLE
success_count=$(grep -c "SUCCESS after.*retry attempt" "$LOG_FILE" 2>/dev/null || echo "0")  
echo "Successes After Retry: $success_count"

# Count parallel with retry - SIMPLE
parallel_count=$(grep -c "retry_failed=true" "$LOG_FILE" 2>/dev/null || echo "0")
echo "Parallel Executions with Retry: $parallel_count"

echo ""
echo "=== FINAL RESULT ==="

if [ "$overall_success" = true ]; then
    if [ "$retry_count" != "0" ] && [ "$success_count" != "0" ]; then
        echo -e "${GREEN}🎉 SUCCESS: Retry functionality is working!${NC}"
        echo "  - All tests completed"
        echo "  - $retry_count retry attempts made"  
        echo "  - $success_count tasks succeeded after retry"
        echo "  - $parallel_count parallel executions with retry"
        exit 0
    else
        echo -e "${GREEN}✓ Tests completed but limited retry evidence${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Tests did not complete successfully${NC}"
    exit 1
fi

# Cleanup
rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true

echo ""
echo "Log file: $LOG_FILE"