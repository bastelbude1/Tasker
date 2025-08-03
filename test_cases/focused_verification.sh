#!/bin/bash

# FOCUSED VERIFICATION - NO DUPLICATES, PROPER TIMEOUTS
# Tests each .txt file exactly once with both versions
# Designed for 100% success rate - any timeout is a FAILURE

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== FOCUSED VERIFICATION PROTOCOL ===${NC}"
echo "Testing each .txt file exactly once - no duplicates"
echo "60-second timeout per test (handles complex retry scenarios)"
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
    
    # Reset and run original (60s timeout - allows for complex tests)
    reset_state
    echo "  Testing with original..."
    if timeout 60s ../tasker_orig.py "$test_name" -r -d > /dev/null 2>&1; then
        orig_exit=0
    else
        orig_exit=$?
        if [ $orig_exit -eq 124 ]; then
            echo -e "    ${RED}TIMEOUT: Original version${NC}"
            timeout_tests+=("$test_name (original)")
            failed_tests+=("$test_name")
            echo -e "  ❌ FAIL: Timeout (original)"
            return
        fi
    fi
    
    # Reset and run refactored (60s timeout)
    reset_state  
    echo "  Testing with refactored..."
    if timeout 60s ../tasker.py "$test_name" -r -d > /dev/null 2>&1; then
        refactored_exit=0
    else
        refactored_exit=$?
        if [ $refactored_exit -eq 124 ]; then
            echo -e "    ${RED}TIMEOUT: Refactored version${NC}"
            timeout_tests+=("$test_name (refactored)")
            failed_tests+=("$test_name")
            echo -e "  ❌ FAIL: Timeout (refactored)"
            return
        fi
    fi
    
    # Compare results (allowing for improved exit codes)
    if [ $orig_exit -eq $refactored_exit ]; then
        echo -e "  ✅ PASS: Exit codes match ($orig_exit)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $refactored_exit -eq 20 ]; then
        echo -e "  ✅ PASS: Improved exit code (validation failure: $orig_exit → $refactored_exit)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $refactored_exit -eq 14 ]; then
        echo -e "  ✅ PASS: Improved exit code (conditional failure: $orig_exit → $refactored_exit)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "  ❌ FAIL: Exit codes differ (orig: $orig_exit, refactored: $refactored_exit)"
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
    echo -e "${RED}❌ OTHER FAILURES:${NC}"
    for failed in "${failed_tests[@]}"; do
        echo "  - $failed"
    done
fi

if [ ${#failed_tests[@]} -eq 0 ] && [ ${#timeout_tests[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 100% SUCCESS - ALL TESTS PASSED WITH NO TIMEOUTS!${NC}"
    exit 0
else
    echo -e "${RED}❌ VERIFICATION FAILED - NOT READY FOR PRODUCTION${NC}"
    exit 1
fi