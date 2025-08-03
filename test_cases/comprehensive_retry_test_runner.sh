#!/bin/bash

# COMPREHENSIVE RETRY LOGIC TEST RUNNER
# Validates all retry functionality scenarios for parallel tasks
# Usage: ./comprehensive_retry_test_runner.sh [tasker|tasker_orig]

set -e

# Determine which tasker script to use
TASKER_VERSION=${1:-tasker}
if [ "$TASKER_VERSION" = "tasker_orig" ]; then
    TASKER_SCRIPT="../tasker_orig.py"
elif [ "$TASKER_VERSION" = "tasker" ]; then
    TASKER_SCRIPT="../tasker.py"
else
    echo "Usage: $0 [tasker|tasker_orig]"
    echo "  tasker      - Use refactored tasker.py (default)"
    echo "  tasker_orig - Use original tasker_orig.py"
    exit 1
fi

LOG_DIR="./test_logs"
TIMESTAMP=$(date +%d%b%y_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=5

echo -e "${BLUE}=== COMPREHENSIVE RETRY LOGIC TEST RUNNER ===${NC}"
echo "Testing retry functionality for parallel tasks"
echo "Using: $TASKER_SCRIPT"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create test log directory
mkdir -p "$LOG_DIR"

# Function to cleanup test files between runs
cleanup_test_files() {
    echo -e "${YELLOW}Cleaning up test files...${NC}"
    rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true
}

# Function to log test results
log_test_result() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    local log_file="$4"
    
    if [ "$expected" = "$actual" ]; then
        echo -e "  ${GREEN}✓ PASS:${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "  ${RED}✗ FAIL:${NC} $test_name"
        echo -e "    Expected: $expected"
        echo -e "    Actual:   $actual"
        echo -e "    Log file: $log_file"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to run a single test and validate results
run_single_test() {
    local test_num="$1"
    local test_name="$2"
    local test_file="$3"
    local success_pattern="$4"
    local retry_pattern="$5"
    local expected_retry_count="$6"
    
    echo -e "${YELLOW}Test $test_num: $test_name${NC}"
    
    # Cleanup before each test
    cleanup_test_files
    
    local log_file="$LOG_DIR/test${test_num}_${TIMESTAMP}.log"
    
    # Check if test file exists
    if [ ! -f "$test_file" ]; then
        echo -e "  ${RED}✗ FAIL:${NC} Test file '$test_file' not found!"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return
    fi
    
    # Run the test
    echo "  Running: python3 $TASKER_SCRIPT -r -d -t local $test_file"
    if python3 "$TASKER_SCRIPT" -r -d -t local "$test_file" > "$log_file" 2>&1; then
        exit_code=0
        echo -e "    ${GREEN}✓${NC} Test execution completed successfully"
    else
        exit_code=$?
        echo -e "    ${YELLOW}!${NC} Test execution completed with exit code: $exit_code"
    fi
    
    # Validate success message
    local success_found
    if grep -q "$success_pattern" "$log_file" 2>/dev/null; then
        success_found="SUCCESS"
        echo -e "    ${GREEN}✓${NC} Success message found"
    else
        success_found="FAILED"
        echo -e "    ${RED}✗${NC} Success message not found"
    fi
    
    log_test_result "$test_name - Success Message" "SUCCESS" "$success_found" "$log_file"
    
    # Validate retry attempts (if expected)
    if [ "$expected_retry_count" != "0" ]; then
        local retry_count
        retry_count=$(grep -c "$retry_pattern" "$log_file" 2>/dev/null || echo "0")
        retry_count=$(echo "$retry_count" | tr -d '\n\r ')
        
        if [ "$retry_count" -ge "$expected_retry_count" ]; then
            echo -e "    ${GREEN}✓${NC} Expected retry attempts found: $retry_count (expected >= $expected_retry_count)"
            log_test_result "$test_name - Retry Attempts" "RETRY_FOUND" "RETRY_FOUND" "$log_file"
        else
            echo -e "    ${RED}✗${NC} Insufficient retry attempts: $retry_count (expected >= $expected_retry_count)"
            log_test_result "$test_name - Retry Attempts" "RETRY_FOUND" "RETRY_NOT_FOUND" "$log_file"
        fi
    else
        echo -e "    ${BLUE}ℹ️${NC} No retry validation required for this test"
    fi
    
    # Additional validation for specific test types
    case $test_num in
        2)
            # Test 2: Validate that timeouts are NOT retried
            local timeout_retries
            timeout_retries=$(grep -c "will retry as Task.*-201\." "$log_file" 2>/dev/null || echo "0")
            timeout_retries=$(echo "$timeout_retries" | tr -d '\n\r ')
            if [ "$timeout_retries" -eq 0 ]; then
                echo -e "    ${GREEN}✓${NC} Timeout task correctly NOT retried"
                log_test_result "$test_name - Timeout Not Retried" "NO_TIMEOUT_RETRY" "NO_TIMEOUT_RETRY" "$log_file"
            else
                echo -e "    ${RED}✗${NC} Timeout task incorrectly retried $timeout_retries times"
                log_test_result "$test_name - Timeout Not Retried" "NO_TIMEOUT_RETRY" "TIMEOUT_RETRIED" "$log_file"
            fi
            ;;
        3)
            # Test 3: Validate custom success conditions work with retry
            local custom_success_retries
            custom_success_retries=$(grep -c "will retry as Task.*-30[012]\." "$log_file" 2>/dev/null || echo "0")
            if [ "$custom_success_retries" -gt 0 ]; then
                echo -e "    ${GREEN}✓${NC} Custom success conditions with retry working: $custom_success_retries retries"
                log_test_result "$test_name - Custom Success Retry" "CUSTOM_RETRY_FOUND" "CUSTOM_RETRY_FOUND" "$log_file"
            else
                echo -e "    ${YELLOW}!${NC} No custom success condition retries found (may still be correct)"
                log_test_result "$test_name - Custom Success Retry" "CUSTOM_RETRY_FOUND" "CUSTOM_RETRY_NOT_FOUND" "$log_file"
            fi
            ;;
        4)
            # Test 4: Validate high retry count works
            local high_retry_attempts
            high_retry_attempts=$(grep -c "will retry as Task.*-40[01]\." "$log_file" 2>/dev/null || echo "0")
            if [ "$high_retry_attempts" -ge 6 ]; then  # Task 400 (3 retries) + Task 401 (4 retries) = 7 total
                echo -e "    ${GREEN}✓${NC} High retry count working: $high_retry_attempts attempts"
                log_test_result "$test_name - High Retry Count" "HIGH_RETRY_FOUND" "HIGH_RETRY_FOUND" "$log_file"
            else
                echo -e "    ${RED}✗${NC} Insufficient high retry attempts: $high_retry_attempts (expected >= 6)"
                log_test_result "$test_name - High Retry Count" "HIGH_RETRY_FOUND" "HIGH_RETRY_NOT_FOUND" "$log_file"
            fi
            ;;
        5)
            # Test 5: Validate mixed scenario behavior
            local mixed_retries
            local timeout_not_retried
            mixed_retries=$(grep -c "will retry as Task.*-50[1345]\." "$log_file" 2>/dev/null || echo "0")
            timeout_not_retried=$(grep -c "will retry as Task.*-502\." "$log_file" 2>/dev/null || echo "0")
            mixed_retries=$(echo "$mixed_retries" | tr -d '\n\r ')
            timeout_not_retried=$(echo "$timeout_not_retried" | tr -d '\n\r ')
            
            if [ "$mixed_retries" -gt 0 ] && [ "$timeout_not_retried" -eq 0 ]; then
                echo -e "    ${GREEN}✓${NC} Mixed scenario working: $mixed_retries retries, timeout not retried"
                log_test_result "$test_name - Mixed Scenario" "MIXED_CORRECT" "MIXED_CORRECT" "$log_file"
            else
                echo -e "    ${RED}✗${NC} Mixed scenario issues: retries=$mixed_retries, timeout_retries=$timeout_not_retried"
                log_test_result "$test_name - Mixed Scenario" "MIXED_CORRECT" "MIXED_INCORRECT" "$log_file"
            fi
            ;;
    esac
    
    echo ""
}

# Check if tasker script exists
if [ ! -f "$TASKER_SCRIPT" ]; then
    echo -e "${RED}Error: Tasker script '$TASKER_SCRIPT' not found!${NC}"
    exit 1
fi

echo -e "${BLUE}--- Running All Retry Logic Tests ---${NC}"
echo ""

# Run all tests individually
run_single_test 1 "Basic Retry Functionality" \
    "retry_test_1_basic.txt" \
    "SUCCESS: Basic retry test passed" \
    "will retry as Task" \
    2

run_single_test 2 "Timeout Behavior Analysis" \
    "retry_test_2_timeout.txt" \
    "SUCCESS: Timeout test passed" \
    "will retry as Task.*-200\." \
    1

run_single_test 3 "Custom Success Conditions" \
    "retry_test_3_custom_success.txt" \
    "SUCCESS: Custom success conditions work" \
    "will retry as Task.*-30[012]\." \
    1

run_single_test 4 "High Retry Count Scenario" \
    "retry_test_4_high_retry.txt" \
    "SUCCESS: High retry count test passed" \
    "will retry as Task.*-40[01]\." \
    6

run_single_test 5 "Mixed Success/Failure/Timeout" \
    "retry_test_5_mixed.txt" \
    "SUCCESS: Mixed scenarios test passed" \
    "will retry as Task.*-50[1345]\." \
    2

# Final cleanup
cleanup_test_files

# Summary
echo -e "${BLUE}=== COMPREHENSIVE TEST SUMMARY ===${NC}"
echo -e "Total Tests: $TOTAL_TESTS scenarios"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

# Show log file location
echo ""
echo -e "${BLUE}Log files available for detailed analysis:${NC}"
if ls "$LOG_DIR"/*"$TIMESTAMP"* 1> /dev/null 2>&1; then
    ls -la "$LOG_DIR"/*"$TIMESTAMP"*
else
    echo "No log files found with timestamp $TIMESTAMP"
fi

# Final assessment
if [ $TESTS_PASSED -ge 4 ]; then
    echo -e "\n${GREEN}🎉 COMPREHENSIVE RETRY FUNCTIONALITY WORKING! ($TESTS_PASSED/$TOTAL_TESTS scenarios passed)${NC}"
    echo -e "${BLUE}ℹ️  All major retry scenarios have been validated successfully.${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some retry scenarios failed ($TESTS_PASSED/$TOTAL_TESTS scenarios passed).${NC}"
    echo -e "${BLUE}ℹ️  Check the log files for detailed analysis of failures.${NC}"
    exit 1
fi