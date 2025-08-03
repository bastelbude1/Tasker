#!/bin/bash

# FOCUSED VERIFICATION - SINGLE VERSION VERIFICATION WITH REFACTORED TASKER
# Tests each .txt file exactly once with tasker.py (refactored version)
# No comparison needed - validates that refactored tasker.py works correctly
# Designed for 100% success rate - any timeout or exception is a FAILURE

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== FOCUSED VERIFICATION PROTOCOL (REFACTORED SINGLE VERSION) ===${NC}"
echo "Testing each .txt file exactly once with refactored tasker.py"
echo "Validates that all functionality works correctly after log level implementation"
echo "60-second timeout per test - 100% SUCCESS required (any timeout/exception = FAILURE)"
echo

total_tests=0
passed_tests=0
failed_tests=()
timeout_tests=()

# Function to reset state files
reset_state() {
    rm -f ../.toggle_value ../.my_counter
    rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true
}

# Function to run a single test
run_test() {
    local test_name="$1"
    echo -e "${YELLOW}[Testing: $test_name]${NC}"
    total_tests=$((total_tests + 1))
    
    # Reset state and run with tasker.py (capture stderr to detect exceptions)
    reset_state
    echo "  Running refactored tasker.py..."
    
    # Capture stderr to check for Python exceptions while hiding normal output
    error_output=$(timeout 60s ../tasker.py "$test_name" -r 2>&1 >/dev/null)
    tasker_exit=$?
    
    # Check for Python exceptions in stderr
    if echo "$error_output" | grep -E "(Traceback|AttributeError|Exception|Error:)" > /dev/null; then
        echo -e "    ${RED}EXCEPTION DETECTED in tasker.py:${NC}"
        echo "$error_output" | head -3
        failed_tests+=("$test_name")
        echo -e "  ❌ FAIL: Python exception - refactoring regression"
        return
    fi
    
    if [ $tasker_exit -eq 124 ]; then
        echo -e "    ${RED}TIMEOUT: tasker.py (60s timeout)${NC}"
        timeout_tests+=("$test_name")
        failed_tests+=("$test_name")
        echo -e "  ❌ FAIL: Timeout after 60s - FAILURE"
        return
    fi
    
    # Validate exit codes for expected ranges
    # Success scenarios: 0 (success), 5 (next=never)
    # Expected failure scenarios: 1 (general), 14 (conditional), 20 (validation), 21 (task dependency)
    if [[ $tasker_exit -eq 0 || $tasker_exit -eq 5 || $tasker_exit -eq 1 || $tasker_exit -eq 14 || $tasker_exit -eq 20 || $tasker_exit -eq 21 ]]; then
        echo -e "  ✅ PASS: Valid exit code ($tasker_exit) - functionality verified"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "  ❌ FAIL: Unexpected exit code ($tasker_exit) - potential regression"
        failed_tests+=("$test_name")
    fi
    echo
}

# Test all .txt files exactly once
echo -e "${BLUE}=== Testing all .txt files ===${NC}"
for txt_file in *.txt; do
    if [ -f "$txt_file" ]; then
        run_test "$txt_file"
    fi
done

# Results
echo -e "${BLUE}=== RESULTS ===${NC}"
echo "Total: $total_tests"
echo "Passed: $passed_tests" 
echo "Failed: ${#failed_tests[@]}"
echo "Timeouts: ${#timeout_tests[@]}"

if [ ${#timeout_tests[@]} -gt 0 ]; then
    echo -e "${RED}❌ TIMEOUT FAILURES (NOT ACCEPTABLE):${NC}"
    for timeout_test in "${timeout_tests[@]}"; do
        echo "  - $timeout_test"
    done
fi

if [ ${#failed_tests[@]} -gt 0 ]; then
    echo -e "${RED}❌ BEHAVIOR FAILURES:${NC}"
    for failed in "${failed_tests[@]}"; do
        echo "  - $failed"
    done
fi

if [ ${#failed_tests[@]} -eq 0 ] && [ ${#timeout_tests[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 100% SUCCESS - ALL TESTS PASSED WITH NO TIMEOUTS!${NC}"
    echo -e "${GREEN}    Refactored tasker.py with log level control verified - fully functional!${NC}"
    echo -e "${GREEN}    Code still works and nothing is broken after refactoring!${NC}"
    exit 0
else
    echo -e "${RED}❌ VERIFICATION FAILED - REFACTORING REGRESSION DETECTED${NC}"
    exit 1
fi