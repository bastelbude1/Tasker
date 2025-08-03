#!/bin/bash

# Quick verification of all .txt files only
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== QUICK .TXT FILES VERIFICATION ===${NC}"

total_tests=0
passed_tests=0
failed_tests=()

reset_state() {
    rm -f ../.toggle_value ../.my_counter
}

run_test() {
    local test_name="$1"
    echo -e "${YELLOW}[Testing: $test_name]${NC}"
    total_tests=$((total_tests + 1))
    
    # Reset and run original
    reset_state
    if ../tasker_orig.py "$test_name" -r -d > /dev/null 2>&1; then
        orig_exit=0
    else
        orig_exit=$?
    fi
    
    # Reset and run refactored
    reset_state
    if ../tasker.py "$test_name" -r -d > /dev/null 2>&1; then
        refactored_exit=0
    else
        refactored_exit=$?
    fi
    
    # Compare with improvements allowed
    if [ $orig_exit -eq $refactored_exit ]; then
        echo -e "  ✅ PASS: Exit codes match ($orig_exit)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $refactored_exit -eq 20 ]; then
        echo -e "  ✅ PASS: Improved exit code (validation failure)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $refactored_exit -eq 14 ]; then
        echo -e "  ✅ PASS: Improved exit code (conditional execution failed)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "  ❌ FAIL: Exit codes differ (orig: $orig_exit, refactored: $refactored_exit)"
        failed_tests+=("$test_name")
    fi
}

# Test all .txt files
for txt_file in *.txt; do
    if [ -f "$txt_file" ]; then
        run_test "$txt_file"
    fi
done

echo -e "${BLUE}=== RESULTS ===${NC}"
echo "Total: $total_tests, Passed: $passed_tests, Failed: ${#failed_tests[@]}"

if [ ${#failed_tests[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL .TXT TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}❌ FAILED TESTS:${NC}"
    for failed in "${failed_tests[@]}"; do
        echo "  - $failed"
    done
    exit 1
fi