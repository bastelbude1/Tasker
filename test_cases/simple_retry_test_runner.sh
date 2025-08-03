#!/bin/bash

# SIMPLE RETRY LOGIC TEST RUNNER - NO FORK BOMB
# Simplified version to avoid infinite loops
# NO complex pattern matching that could cause hangs

set -e

# Configuration
TASKER_SCRIPT="./tasker.py"
TEST_FILE="comprehensive_retry_test_case.txt"
LOG_DIR="./test_logs"
TIMESTAMP=$(date +%d%b%y_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== SIMPLE RETRY LOGIC TEST RUNNER ===${NC}"
echo "Testing retry functionality - simplified version"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create test log directory
mkdir -p "$LOG_DIR"

# SIMPLE pattern check function - NO COMPLEX REGEX
simple_check() {
    local log_file="$1"
    local pattern="$2"
    
    if [ -f "$log_file" ]; then
        if grep -q "$pattern" "$log_file" 2>/dev/null; then
            echo "FOUND"
        else
            echo "NOT_FOUND"
        fi
    else
        echo "FILE_NOT_FOUND"
    fi
}

# SIMPLE count function - NO COMPLEX PROCESSING
simple_count() {
    local log_file="$1"
    local pattern="$2"
    
    if [ -f "$log_file" ]; then
        local count=$(grep -c "$pattern" "$log_file" 2>/dev/null || echo "0")
        # Just return the first character sequence that looks like a number
        echo "$count" | head -1 | cut -c1-2 | tr -cd '0-9' | head -c2
        [ -z "$(echo "$count" | head -1 | cut -c1-2 | tr -cd '0-9' | head -c2)" ] && echo "0"
    else
        echo "0"
    fi
}

# Cleanup function
cleanup_test_files() {
    echo -e "${YELLOW}Cleaning up test files...${NC}"
    rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true
}

# Pre-test cleanup
cleanup_test_files

echo -e "${BLUE}--- Running Simple Retry Logic Test ---${NC}"
echo ""

# Check if files exist
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}Error: Test file '$TEST_FILE' not found!${NC}"
    exit 1
fi

if [ ! -f "$TASKER_SCRIPT" ]; then
    echo -e "${RED}Error: Tasker script '$TASKER_SCRIPT' not found!${NC}"
    exit 1
fi

# RUN THE TEST
echo -e "${YELLOW}Running Comprehensive Sequential Test${NC}"
MAIN_LOG="$LOG_DIR/simple_retry_test_$TIMESTAMP.log"

echo "Executing: python3 $TASKER_SCRIPT -r -d -t local $TEST_FILE"

# Run with timeout to prevent hanging
timeout 120s python3 "$TASKER_SCRIPT" -r -d -t local "$TEST_FILE" > "$MAIN_LOG" 2>&1
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} Test execution completed successfully"
elif [ $exit_code -eq 124 ]; then
    echo -e "  ${RED}✗${NC} Test execution timed out after 120 seconds"
    exit 1
else
    echo -e "  ${YELLOW}!${NC} Test execution completed with exit code: $exit_code"
fi

echo ""

# SIMPLE ANALYSIS - NO COMPLEX PATTERN MATCHING
echo -e "${BLUE}=== SIMPLE RETRY ANALYSIS ===${NC}"

# Check if final success message exists
final_success=$(simple_check "$MAIN_LOG" "ALL TESTS COMPLETED SUCCESSFULLY")
echo -e "Overall Success: $final_success"

# Count retry attempts - SIMPLE
retry_count=$(simple_count "$MAIN_LOG" "RETRY.*failed task")
echo -e "Total Retry Attempts: $retry_count"

# Count successes after retry - SIMPLE  
success_count=$(simple_count "$MAIN_LOG" "SUCCESS after.*retry attempt")
echo -e "Successes After Retry: $success_count"

# Count parallel executions - SIMPLE
parallel_count=$(simple_count "$MAIN_LOG" "Starting parallel execution.*retry_failed=true")
echo -e "Parallel Executions with Retry: $parallel_count"

echo ""

# SIMPLE ASSESSMENT
echo -e "${BLUE}=== SIMPLE ASSESSMENT ===${NC}"

if [ "$final_success" = "FOUND" ]; then
    echo -e "${GREEN}✓ OVERALL SUCCESS: All tests completed successfully${NC}"
    
    if [ "$retry_count" != "0" ] && [ "$success_count" != "0" ]; then
        echo -e "${GREEN}✓ RETRY FUNCTIONALITY: Working ($retry_count retries, $success_count successes)${NC}"
    else
        echo -e "${YELLOW}⚠ RETRY FUNCTIONALITY: Limited evidence of retries${NC}"
    fi
    
    if [ "$parallel_count" != "0" ]; then
        echo -e "${GREEN}✓ PARALLEL RETRY: $parallel_count parallel executions with retry enabled${NC}"
    else
        echo -e "${YELLOW}⚠ PARALLEL RETRY: No parallel executions detected${NC}"
    fi
    
else
    echo -e "${RED}✗ OVERALL FAILURE: Tests did not complete successfully${NC}"
fi

echo ""
echo -e "${BLUE}Log file: $MAIN_LOG${NC}"
echo -e "${BLUE}Size: $(wc -l < "$MAIN_LOG") lines${NC}"

# Final cleanup
cleanup_test_files

# Simple exit decision
if [ "$final_success" = "FOUND" ] && [ "$retry_count" != "0" ]; then
    echo -e "\n${GREEN}🎉 RETRY FUNCTIONALITY IS WORKING!${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Check the log file for details${NC}"
    exit 1
fi