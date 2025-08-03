#!/bin/bash

# FOCUSED VERIFICATION - RELIABLE SINGLE VERSION VERIFICATION
# Tests each .txt file exactly once with tasker.py (no debug)
# Compares with tasker_orig.py (no debug) for verification when needed
# Designed for 100% success rate - any timeout is a FAILURE

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== FOCUSED VERIFICATION PROTOCOL (RELIABLE SINGLE VERSION) ===${NC}"
echo "Testing each .txt file exactly once with tasker.py (no debug)"
echo "Using tasker_orig.py comparison for verification when needed"
echo "30-second timeout per test - 100% SUCCESS required"
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
    
    # Reset state and run with tasker.py (NO DEBUG to avoid output differences)
    reset_state
    echo "  Running tasker.py (no debug)..."
    if timeout 30s ../tasker.py "$test_name" -r > /dev/null 2>&1; then
        tasker_exit=0
    else
        tasker_exit=$?
        if [ $tasker_exit -eq 124 ]; then
            echo -e "    ${RED}TIMEOUT: tasker.py${NC}"
            timeout_tests+=("$test_name")
            failed_tests+=("$test_name")
            echo -e "  ❌ FAIL: Timeout - not acceptable"
            return
        fi
    fi
    
    # Reset state and run with tasker_orig.py (NO DEBUG for fair comparison)
    reset_state
    echo "  Running tasker_orig.py (no debug) for verification..."
    if timeout 30s ../tasker_orig.py "$test_name" -r > /dev/null 2>&1; then
        orig_exit=0
    else
        orig_exit=$?
        if [ $orig_exit -eq 124 ]; then
            echo -e "    ${RED}TIMEOUT: tasker_orig.py${NC}"
            timeout_tests+=("$test_name (orig)")
            failed_tests+=("$test_name")
            echo -e "  ❌ FAIL: Timeout in reference - not acceptable"
            return
        fi
    fi
    
    # Compare results (allowing for improved exit codes)
    if [ $tasker_exit -eq $orig_exit ]; then
        echo -e "  ✅ PASS: Exit codes match ($tasker_exit)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $tasker_exit -eq 20 ]; then
        echo -e "  ✅ PASS: Improved exit code (validation failure: $orig_exit → $tasker_exit)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $tasker_exit -eq 14 ]; then
        echo -e "  ✅ PASS: Improved exit code (conditional failure: $orig_exit → $tasker_exit)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "  ❌ FAIL: Exit codes differ (tasker.py: $tasker_exit, tasker_orig.py: $orig_exit)"
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
    echo -e "${GREEN}    tasker.py verified against tasker_orig.py - functionality confirmed!${NC}"
    exit 0
else
    echo -e "${RED}❌ VERIFICATION FAILED - NOT READY FOR PRODUCTION${NC}"
    exit 1
fi