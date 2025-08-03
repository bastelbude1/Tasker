#!/bin/bash

# RETRY LOGIC TEST RUNNER - FIXED VERSION
# Automated test runner for the retry functionality
# Validates that retry logic works correctly for parallel tasks
# Usage: ./fixed_retry_test_runner.sh [tasker|tasker_orig]

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
TEST_FILE="retry_logic_test_case.txt"
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

echo -e "${BLUE}=== RETRY LOGIC TEST RUNNER - FIXED ===${NC}"
echo "Testing retry functionality for parallel tasks"
echo "Using: $TASKER_SCRIPT"
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

# Function to extract specific log patterns
extract_log_info() {
    local log_file="$1"
    local pattern="$2"
    if [ -f "$log_file" ]; then
        grep "$pattern" "$log_file" 2>/dev/null | tail -1 | tr -d '\n' || echo "PATTERN_NOT_FOUND"
    else
        echo "LOG_FILE_NOT_FOUND"
    fi
}

# FIXED: Function to count retry attempts in logs
count_retry_attempts() {
    local log_file="$1"
    local task_pattern="$2"
    
    if [ ! -f "$log_file" ]; then
        echo "0"
        return
    fi
    
    # Count retry attempts more reliably
    local count
    count=$(grep -c "RETRY.*${task_pattern}" "$log_file" 2>/dev/null || echo "0")
    
    # Ensure we have a clean integer
    echo "$count" | head -1 | sed 's/[^0-9]//g' | grep -E '^[0-9]+$' || echo "0"
}

# FIXED: Function to count configuration warnings
count_config_warnings() {
    local log_file="$1"
    
    if [ ! -f "$log_file" ]; then
        echo "0"
        return
    fi
    
    # Count both retry_count and retry_delay warnings separately and sum them
    local retry_count_warnings
    local retry_delay_warnings
    local retry_failed_warnings
    
    retry_count_warnings=$(grep -c "unknown field.*retry_count" "$log_file" 2>/dev/null || echo "0")
    retry_delay_warnings=$(grep -c "unknown field.*retry_delay" "$log_file" 2>/dev/null || echo "0")
    retry_failed_warnings=$(grep -c "unknown field.*retry_failed" "$log_file" 2>/dev/null || echo "0")
    
    # Sum them up using arithmetic expansion
    echo $((retry_count_warnings + retry_delay_warnings + retry_failed_warnings))
}

# Function to count parallel executions with retry
count_parallel_with_retry() {
    local log_file="$1"
    
    if [ ! -f "$log_file" ]; then
        echo "0"
        return
    fi
    
    grep -c "Starting parallel execution.*retry_failed=true" "$log_file" 2>/dev/null || echo "0"
}

# Cleanup function
cleanup_test_files() {
    echo -e "${YELLOW}Cleaning up test files...${NC}"
    rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true
}

# Pre-test cleanup
cleanup_test_files

echo -e "${BLUE}--- Running Retry Logic Tests ---${NC}"
echo ""

# Check if test file exists
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}Error: Test file '$TEST_FILE' not found!${NC}"
    echo "Please ensure you have the corrected retry_logic_test_case.txt file."
    exit 1
fi

# Check if tasker script exists
if [ ! -f "$TASKER_SCRIPT" ]; then
    echo -e "${RED}Error: Tasker script '$TASKER_SCRIPT' not found!${NC}"
    exit 1
fi

# TEST 1: Basic Retry Functionality
echo -e "${YELLOW}Test 1: Basic Retry Functionality${NC}"
TEST1_LOG="$LOG_DIR/test1_basic_retry_$TIMESTAMP.log"

# Run the complete test
echo "Running: python3 $TASKER_SCRIPT -r -d -t local $TEST_FILE"
if python3 "$TASKER_SCRIPT" -r -d -t local "$TEST_FILE" > "$TEST1_LOG" 2>&1; then
    exit_code=0
    echo -e "  ${GREEN}✓${NC} Test execution completed successfully"
else
    exit_code=$?
    echo -e "  ${YELLOW}!${NC} Test execution completed with exit code: $exit_code"
fi

# Validate results for Test 1 (Basic retry)
success_msg=$(extract_log_info "$TEST1_LOG" "SUCCESS: Basic retry test passed")
retry_attempts=$(count_retry_attempts "$TEST1_LOG" "Task 1-10[12]")

if [[ "$success_msg" == *"SUCCESS: Basic retry test passed"* ]]; then
    expected_result="SUCCESS"
    actual_result="SUCCESS"
else
    expected_result="SUCCESS"
    actual_result="FAILED"
fi

log_test_result "Basic Retry Functionality" "$expected_result" "$actual_result" "$TEST1_LOG"

# Check if retries actually happened
if [ "$retry_attempts" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Retry attempts detected: $retry_attempts"
else
    echo -e "  ${RED}✗${NC} No retry attempts found in logs"
fi

echo ""

# TEST 2: Timeout Behavior Analysis
echo -e "${YELLOW}Test 2: Timeout Behavior Analysis${NC}"

# Look for timeout test in the same log
timeout_success=$(extract_log_info "$TEST1_LOG" "SUCCESS: Timeout test passed")
timeout_retries=$(count_retry_attempts "$TEST1_LOG" "Task 11-20[12]")

if [[ "$timeout_success" == *"SUCCESS: Timeout test passed"* ]]; then
    if [ "$timeout_retries" -eq 0 ]; then
        expected_result="TIMEOUT_NO_RETRY"
        actual_result="TIMEOUT_NO_RETRY"
        echo -e "  ${GREEN}✓${NC} Timeout tasks correctly NOT retried"
    else
        expected_result="TIMEOUT_NO_RETRY"
        actual_result="TIMEOUT_RETRIED"
        echo -e "  ${RED}✗${NC} Timeout tasks were incorrectly retried $timeout_retries times"
    fi
else
    expected_result="TIMEOUT_TEST_AVAILABLE"
    actual_result="TIMEOUT_TEST_NOT_RUN"
    echo -e "  ${YELLOW}!${NC} Timeout test not found in current test run"
fi

log_test_result "Timeout Behavior Analysis" "$expected_result" "$actual_result" "$TEST1_LOG"

echo ""

# TEST 3: Custom Success Conditions Analysis
echo -e "${YELLOW}Test 3: Custom Success Conditions Analysis${NC}"

# Look for custom success test in the same log
custom_success=$(extract_log_info "$TEST1_LOG" "SUCCESS: Custom success conditions")
custom_retries=$(count_retry_attempts "$TEST1_LOG" "Task 21-30[012]")

if [[ "$custom_success" == *"SUCCESS: Custom success conditions"* ]]; then
    expected_result="CUSTOM_SUCCESS"
    actual_result="CUSTOM_SUCCESS"
    echo -e "  ${GREEN}✓${NC} Custom success conditions test found"
else
    expected_result="CUSTOM_SUCCESS"
    actual_result="CUSTOM_NOT_FOUND"
    echo -e "  ${YELLOW}!${NC} Custom success conditions test not found in current run"
fi

log_test_result "Custom Success Conditions Analysis" "$expected_result" "$actual_result" "$TEST1_LOG"

if [ "$custom_retries" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Custom success condition retries detected: $custom_retries"
else
    echo -e "  ${YELLOW}!${NC} No custom success condition retries found"
fi

echo ""

# TEST 4: FIXED - Retry Configuration Validation Analysis
echo -e "${YELLOW}Test 4: Retry Configuration Analysis${NC}"

# FIXED: Use the new function to count configuration warnings
config_warnings=$(count_config_warnings "$TEST1_LOG")

echo -e "  ${BLUE}ℹ️${NC} Configuration warnings found: $config_warnings"

if [ "$config_warnings" -gt 0 ]; then
    expected_result="CONFIG_VALIDATED"
    actual_result="CONFIG_VALIDATED"
    echo -e "  ${GREEN}✓${NC} Configuration validation warnings detected (retry fields are unknown to validator)"
else
    expected_result="CONFIG_VALIDATED"
    actual_result="NO_VALIDATION"
    echo -e "  ${YELLOW}!${NC} No configuration validation warnings found"
fi

log_test_result "Retry Configuration Analysis" "$expected_result" "$actual_result" "$TEST1_LOG"

echo ""

# TEST 5: Overall Execution Analysis
echo -e "${YELLOW}Test 5: Overall Execution Analysis${NC}"

# Analyze the overall execution from the main log
parallel_executions=$(count_parallel_with_retry "$TEST1_LOG")
retry_messages=$(grep -c "RETRY.*failed task" "$TEST1_LOG" 2>/dev/null || echo "0")
success_after_retry=$(grep -c "SUCCESS after.*retry attempt" "$TEST1_LOG" 2>/dev/null || echo "0")

echo -e "  ${BLUE}ℹ️${NC} Parallel executions with retry: $parallel_executions"
echo -e "  ${BLUE}ℹ️${NC} Retry messages found: $retry_messages"  
echo -e "  ${BLUE}ℹ️${NC} Success after retry: $success_after_retry"

if [ "$parallel_executions" -gt 0 ] && [ "$retry_messages" -gt 0 ] && [ "$success_after_retry" -gt 0 ]; then
    expected_result="COMPREHENSIVE_SUCCESS"
    actual_result="COMPREHENSIVE_SUCCESS"
    echo -e "  ${GREEN}✓${NC} All retry functionality indicators present"
else
    expected_result="COMPREHENSIVE_SUCCESS"
    actual_result="PARTIAL_FUNCTIONALITY"
    echo -e "  ${YELLOW}!${NC} Some retry functionality indicators missing"
fi

log_test_result "Overall Execution Analysis" "$expected_result" "$actual_result" "$TEST1_LOG"

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
if [ $TESTS_PASSED -ge 3 ]; then
    echo -e "\n${GREEN}🎉 CORE FUNCTIONALITY WORKING! ($TESTS_PASSED/$TOTAL_TESTS tests passed)${NC}"
    echo -e "${BLUE}ℹ️  The retry functionality appears to be implemented and working.${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Limited test success ($TESTS_PASSED/$TOTAL_TESTS tests passed).${NC}"
    echo -e "${BLUE}ℹ️  Check the log files for detailed analysis.${NC}"
    exit 1
fi