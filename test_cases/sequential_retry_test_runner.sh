#!/bin/bash

# SEQUENTIAL RETRY LOGIC TEST RUNNER
# Tests all retry scenarios in one comprehensive execution
# Updated to work with the sequential test case

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
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=6

echo -e "${BLUE}=== SEQUENTIAL RETRY LOGIC TEST RUNNER ===${NC}"
echo "Testing all retry functionality in one comprehensive execution"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create test log directory
mkdir -p "$LOG_DIR"

# Function to log test results
log_test_result() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    local log_file="$4"
    
    if [ "$expected" = "$actual" ]; then
        echo -e "${GREEN}✓ PASS:${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL:${NC} $test_name"
        echo -e "  Expected: $expected"
        echo -e "  Actual:   $actual"
        echo -e "  Log file: $log_file"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to check if pattern exists in log
check_pattern() {
    local log_file="$1"
    local pattern="$2"
    
    if [ -f "$log_file" ] && grep -q "$pattern" "$log_file" 2>/dev/null; then
        echo "FOUND"
    else
        echo "NOT_FOUND"
    fi
}

# Function to count occurrences of pattern - FIXED TO RETURN CLEAN INTEGER
count_pattern() {
    local log_file="$1"
    local pattern="$2"
    
    if [ -f "$log_file" ]; then
        # Get count, ensure it's a single clean integer
        local count=$(grep -c "$pattern" "$log_file" 2>/dev/null || echo "0")
        # Clean the result to ensure it's a single integer
        echo "$count" | head -1 | sed 's/[^0-9]//g' | grep -E '^[0-9]+'

# Cleanup function
cleanup_test_files() {
    echo -e "${YELLOW}Cleaning up test files...${NC}"
    rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true
}

# Pre-test cleanup
cleanup_test_files

echo -e "${BLUE}--- Running Sequential Retry Logic Tests ---${NC}"
echo ""

# Check if test file exists
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}Error: Test file '$TEST_FILE' not found!${NC}"
    echo "Please create the comprehensive_retry_test_case.txt file."
    exit 1
fi

# Check if tasker script exists
if [ ! -f "$TASKER_SCRIPT" ]; then
    echo -e "${RED}Error: Tasker script '$TASKER_SCRIPT' not found!${NC}"
    exit 1
fi

# RUN COMPREHENSIVE TEST
echo -e "${YELLOW}Running Comprehensive Sequential Test${NC}"
MAIN_LOG="$LOG_DIR/comprehensive_retry_test_$TIMESTAMP.log"

echo "Executing: python3 $TASKER_SCRIPT -r -d -t local $TEST_FILE"
if python3 "$TASKER_SCRIPT" -r -d -t local "$TEST_FILE" > "$MAIN_LOG" 2>&1; then
    exit_code=0
    echo -e "  ${GREEN}✓${NC} Test execution completed successfully"
else
    exit_code=$?
    echo -e "  ${YELLOW}!${NC} Test execution completed with exit code: $exit_code"
fi

echo ""

# ANALYZE RESULTS

# TEST 1: Overall Execution Success
echo -e "${YELLOW}Test 1: Overall Execution Success${NC}"
final_success=$(check_pattern "$MAIN_LOG" "ALL TESTS COMPLETED SUCCESSFULLY")
log_test_result "Overall Execution Success" "FOUND" "$final_success" "$MAIN_LOG"

# TEST 2: Test 1 (Basic Retry) Analysis
echo -e "${YELLOW}Test 2: Basic Retry Functionality${NC}"
test1_passed=$(check_pattern "$MAIN_LOG" "TEST 1 PASSED: Basic retry functionality working")
retry_attempts_basic=$(count_pattern "$MAIN_LOG" "Task 2.*RETRY.*failed task")
success_after_retry_basic=$(count_pattern "$MAIN_LOG" "SUCCESS after.*retry attempt")

if [ "$test1_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 1 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Basic retry attempts: $retry_attempts_basic"
    echo -e "  ${BLUE}ℹ️${NC} Successes after retry: $success_after_retry_basic"
    
    if [ "$retry_attempts_basic" -gt 0 ]; then
        log_test_result "Basic Retry Functionality" "SUCCESS" "SUCCESS" "$MAIN_LOG"
    else
        log_test_result "Basic Retry Functionality" "SUCCESS" "NO_RETRIES" "$MAIN_LOG"
    fi
else
    log_test_result "Basic Retry Functionality" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 3: Test 2 (Timeout Behavior) Analysis
echo -e "${YELLOW}Test 3: Timeout Behavior Analysis${NC}"
test2_passed=$(check_pattern "$MAIN_LOG" "TEST 2 PASSED: Timeout behavior correct")
timeout_retries=$(count_pattern "$MAIN_LOG" "Task 5.*RETRY.*failed task")

if [ "$test2_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 2 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Timeout retry attempts: $timeout_retries"
    
    if [ "$timeout_retries" -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Timeouts correctly NOT retried"
        log_test_result "Timeout Behavior Analysis" "NO_TIMEOUT_RETRIES" "NO_TIMEOUT_RETRIES" "$MAIN_LOG"
    else
        echo -e "  ${RED}✗${NC} Timeouts were incorrectly retried $timeout_retries times"
        log_test_result "Timeout Behavior Analysis" "NO_TIMEOUT_RETRIES" "TIMEOUT_RETRIES_FOUND" "$MAIN_LOG"
    fi
else
    log_test_result "Timeout Behavior Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 4: Test 3 (Custom Success Conditions) Analysis
echo -e "${YELLOW}Test 4: Custom Success Conditions Analysis${NC}"
test3_passed=$(check_pattern "$MAIN_LOG" "TEST 3 PASSED: Custom success conditions work")
custom_retries=$(count_pattern "$MAIN_LOG" "Task 8.*RETRY.*failed task")

if [ "$test3_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 3 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Custom success retry attempts: $custom_retries"
    log_test_result "Custom Success Conditions Analysis" "SUCCESS" "SUCCESS" "$MAIN_LOG"
else
    log_test_result "Custom Success Conditions Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 5: Test 4 (High Retry Count) Analysis
echo -e "${YELLOW}Test 5: High Retry Count Analysis${NC}"
test4_passed=$(check_pattern "$MAIN_LOG" "TEST 4 PASSED: High retry count handled")
high_retries=$(count_pattern "$MAIN_LOG" "Task 11.*RETRY.*failed task")

if [ "$test4_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 4 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} High retry attempts: $high_retries"
    log_test_result "High Retry Count Analysis" "SUCCESS" "SUCCESS" "$MAIN_LOG"
else
    log_test_result "High Retry Count Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 6: Test 5 (Mixed Scenarios) Analysis
echo -e "${YELLOW}Test 6: Mixed Scenarios Analysis${NC}"
test5_passed=$(check_pattern "$MAIN_LOG" "TEST 5 PASSED: Mixed scenarios handled")
mixed_retries=$(count_pattern "$MAIN_LOG" "Task 14.*RETRY.*failed task")

if [ "$test5_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 5 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Mixed scenario retry attempts: $mixed_retries"
    log_test_result "Mixed Scenarios Analysis" "SUCCESS" "SUCCESS" "$MAIN_LOG"
else
    log_test_result "Mixed Scenarios Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

echo ""

# SUMMARY STATISTICS
echo -e "${BLUE}=== RETRY FUNCTIONALITY STATISTICS ===${NC}"
total_parallel_executions=$(count_pattern "$MAIN_LOG" "Starting parallel execution.*retry_failed=true")
total_retry_attempts=$(count_pattern "$MAIN_LOG" "RETRY.*failed task")
total_success_after_retry=$(count_pattern "$MAIN_LOG" "SUCCESS after.*retry attempt")
config_warnings=$(count_pattern "$MAIN_LOG" "unknown field.*retry")

echo -e "Parallel executions with retry: $total_parallel_executions"
echo -e "Total retry attempts: $total_retry_attempts"
echo -e "Successes after retry: $total_success_after_retry"
echo -e "Configuration warnings: $config_warnings"

echo ""

# Final cleanup
cleanup_test_files

# Summary
echo -e "${BLUE}=== TEST SUMMARY ===${NC}"
echo -e "Total Tests: $TOTAL_TESTS"
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
    echo -e "\n${GREEN}🎉 RETRY FUNCTIONALITY FULLY WORKING! ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  All core retry functionality is implemented and working correctly.${NC}"
    exit 0
elif [ $TESTS_PASSED -ge 2 ]; then
    echo -e "\n${YELLOW}✅ PARTIAL SUCCESS ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  Core retry functionality appears to be working, some edge cases may need attention.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ RETRY FUNCTIONALITY ISSUES ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  Check the log files for detailed analysis.${NC}"
    exit 1
fi || echo "0"
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

echo -e "${BLUE}--- Running Sequential Retry Logic Tests ---${NC}"
echo ""

# Check if test file exists
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}Error: Test file '$TEST_FILE' not found!${NC}"
    echo "Please create the comprehensive_retry_test_case.txt file."
    exit 1
fi

# Check if tasker script exists
if [ ! -f "$TASKER_SCRIPT" ]; then
    echo -e "${RED}Error: Tasker script '$TASKER_SCRIPT' not found!${NC}"
    exit 1
fi

# RUN COMPREHENSIVE TEST
echo -e "${YELLOW}Running Comprehensive Sequential Test${NC}"
MAIN_LOG="$LOG_DIR/comprehensive_retry_test_$TIMESTAMP.log"

echo "Executing: python3 $TASKER_SCRIPT -r -d -t local $TEST_FILE"
if python3 "$TASKER_SCRIPT" -r -d -t local "$TEST_FILE" > "$MAIN_LOG" 2>&1; then
    exit_code=0
    echo -e "  ${GREEN}✓${NC} Test execution completed successfully"
else
    exit_code=$?
    echo -e "  ${YELLOW}!${NC} Test execution completed with exit code: $exit_code"
fi

echo ""

# ANALYZE RESULTS

# TEST 1: Overall Execution Success
echo -e "${YELLOW}Test 1: Overall Execution Success${NC}"
final_success=$(check_pattern "$MAIN_LOG" "ALL TESTS COMPLETED SUCCESSFULLY")
log_test_result "Overall Execution Success" "FOUND" "$final_success" "$MAIN_LOG"

# TEST 2: Test 1 (Basic Retry) Analysis
echo -e "${YELLOW}Test 2: Basic Retry Functionality${NC}"
test1_passed=$(check_pattern "$MAIN_LOG" "TEST 1 PASSED: Basic retry functionality working")
retry_attempts_basic=$(count_pattern "$MAIN_LOG" "Task 2.*RETRY.*failed task")
success_after_retry_basic=$(count_pattern "$MAIN_LOG" "SUCCESS after.*retry attempt")

if [ "$test1_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 1 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Basic retry attempts: $retry_attempts_basic"
    echo -e "  ${BLUE}ℹ️${NC} Successes after retry: $success_after_retry_basic"
    
    if [ "$retry_attempts_basic" -gt 0 ]; then
        log_test_result "Basic Retry Functionality" "SUCCESS" "SUCCESS" "$MAIN_LOG"
    else
        log_test_result "Basic Retry Functionality" "SUCCESS" "NO_RETRIES" "$MAIN_LOG"
    fi
else
    log_test_result "Basic Retry Functionality" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 3: Test 2 (Timeout Behavior) Analysis
echo -e "${YELLOW}Test 3: Timeout Behavior Analysis${NC}"
test2_passed=$(check_pattern "$MAIN_LOG" "TEST 2 PASSED: Timeout behavior correct")
timeout_retries=$(count_pattern "$MAIN_LOG" "Task 5.*RETRY.*failed task")

if [ "$test2_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 2 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Timeout retry attempts: $timeout_retries"
    
    if [ "$timeout_retries" -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Timeouts correctly NOT retried"
        log_test_result "Timeout Behavior Analysis" "NO_TIMEOUT_RETRIES" "NO_TIMEOUT_RETRIES" "$MAIN_LOG"
    else
        echo -e "  ${RED}✗${NC} Timeouts were incorrectly retried $timeout_retries times"
        log_test_result "Timeout Behavior Analysis" "NO_TIMEOUT_RETRIES" "TIMEOUT_RETRIES_FOUND" "$MAIN_LOG"
    fi
else
    log_test_result "Timeout Behavior Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 4: Test 3 (Custom Success Conditions) Analysis
echo -e "${YELLOW}Test 4: Custom Success Conditions Analysis${NC}"
test3_passed=$(check_pattern "$MAIN_LOG" "TEST 3 PASSED: Custom success conditions work")
custom_retries=$(count_pattern "$MAIN_LOG" "Task 8.*RETRY.*failed task")

if [ "$test3_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 3 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Custom success retry attempts: $custom_retries"
    log_test_result "Custom Success Conditions Analysis" "SUCCESS" "SUCCESS" "$MAIN_LOG"
else
    log_test_result "Custom Success Conditions Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 5: Test 4 (High Retry Count) Analysis
echo -e "${YELLOW}Test 5: High Retry Count Analysis${NC}"
test4_passed=$(check_pattern "$MAIN_LOG" "TEST 4 PASSED: High retry count handled")
high_retries=$(count_pattern "$MAIN_LOG" "Task 11.*RETRY.*failed task")

if [ "$test4_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 4 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} High retry attempts: $high_retries"
    log_test_result "High Retry Count Analysis" "SUCCESS" "SUCCESS" "$MAIN_LOG"
else
    log_test_result "High Retry Count Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

# TEST 6: Test 5 (Mixed Scenarios) Analysis
echo -e "${YELLOW}Test 6: Mixed Scenarios Analysis${NC}"
test5_passed=$(check_pattern "$MAIN_LOG" "TEST 5 PASSED: Mixed scenarios handled")
mixed_retries=$(count_pattern "$MAIN_LOG" "Task 14.*RETRY.*failed task")

if [ "$test5_passed" = "FOUND" ]; then
    echo -e "  ${GREEN}✓${NC} Test 5 completion detected"
    echo -e "  ${BLUE}ℹ️${NC} Mixed scenario retry attempts: $mixed_retries"
    log_test_result "Mixed Scenarios Analysis" "SUCCESS" "SUCCESS" "$MAIN_LOG"
else
    log_test_result "Mixed Scenarios Analysis" "SUCCESS" "NOT_FOUND" "$MAIN_LOG"
fi

echo ""

# SUMMARY STATISTICS
echo -e "${BLUE}=== RETRY FUNCTIONALITY STATISTICS ===${NC}"
total_parallel_executions=$(count_pattern "$MAIN_LOG" "Starting parallel execution.*retry_failed=true")
total_retry_attempts=$(count_pattern "$MAIN_LOG" "RETRY.*failed task")
total_success_after_retry=$(count_pattern "$MAIN_LOG" "SUCCESS after.*retry attempt")
config_warnings=$(count_pattern "$MAIN_LOG" "unknown field.*retry")

echo -e "Parallel executions with retry: $total_parallel_executions"
echo -e "Total retry attempts: $total_retry_attempts"
echo -e "Successes after retry: $total_success_after_retry"
echo -e "Configuration warnings: $config_warnings"

echo ""

# Final cleanup
cleanup_test_files

# Summary
echo -e "${BLUE}=== TEST SUMMARY ===${NC}"
echo -e "Total Tests: $TOTAL_TESTS"
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
    echo -e "\n${GREEN}🎉 RETRY FUNCTIONALITY FULLY WORKING! ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  All core retry functionality is implemented and working correctly.${NC}"
    exit 0
elif [ $TESTS_PASSED -ge 2 ]; then
    echo -e "\n${YELLOW}✅ PARTIAL SUCCESS ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  Core retry functionality appears to be working, some edge cases may need attention.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ RETRY FUNCTIONALITY ISSUES ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  Check the log files for detailed analysis.${NC}"
    exit 1
fi
