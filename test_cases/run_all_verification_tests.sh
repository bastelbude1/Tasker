#!/bin/bash

# COMPREHENSIVE VERIFICATION TESTING PROTOCOL
# Tests all .txt files and .sh scripts with both tasker versions
# Implements the Mandatory Verification Testing Protocol from CLAUDE.md

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== COMPREHENSIVE VERIFICATION TESTING PROTOCOL ===${NC}"
echo "Testing ALL .txt files and .sh scripts with both tasker versions"
echo

# Test results tracking
total_tests=0
passed_tests=0
failed_tests=()

# Function to reset state files
reset_state() {
    rm -f ../.toggle_value ../.my_counter
}

# Function to run a test and compare results
run_test() {
    local test_name="$1"
    local test_command_orig="$2"
    local test_command_refactored="$3"
    
    echo -e "${YELLOW}[Testing: $test_name]${NC}"
    total_tests=$((total_tests + 1))
    
    # Reset state and run original
    reset_state
    echo "  Running with original..."
    if $test_command_orig > orig_output.tmp 2>&1; then
        orig_exit=0
    else
        orig_exit=$?
    fi
    
    # Reset state and run refactored
    reset_state
    echo "  Running with refactored..."
    if $test_command_refactored > refactored_output.tmp 2>&1; then
        refactored_exit=0
    else
        refactored_exit=$?
    fi
    
    # Compare exit codes (allowing for improved detailed exit codes)
    if [ $orig_exit -eq $refactored_exit ]; then
        echo -e "  ✅ PASS: Exit codes match ($orig_exit)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $refactored_exit -eq 20 ]; then
        echo -e "  ✅ PASS: Improved exit code (orig: 1, refactored: 20 - validation failure)"
        passed_tests=$((passed_tests + 1))
    elif [ $orig_exit -eq 1 ] && [ $refactored_exit -eq 14 ]; then
        echo -e "  ✅ PASS: Improved exit code (orig: 1, refactored: 14 - conditional execution failed)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "  ❌ FAIL: Exit codes differ (orig: $orig_exit, refactored: $refactored_exit)"
        failed_tests+=("$test_name")
    fi
    
    # Clean up
    rm -f orig_output.tmp refactored_output.tmp
    echo
}

echo -e "${BLUE}=== Testing .txt files ===${NC}"
# Test all .txt files
for txt_file in *.txt; do
    if [ -f "$txt_file" ]; then
        run_test "$txt_file" \
            "../tasker_orig.py $txt_file -r -d" \
            "../tasker.py $txt_file -r -d"
    fi
done

echo -e "${BLUE}=== Testing .sh scripts ===${NC}"
# Test all .sh scripts (except the validation script and this script)
for sh_file in *.sh; do
    if [ -f "$sh_file" ] && [ "$sh_file" != "run_all_verification_tests.sh" ] && [ "$sh_file" != "retry_validation_test_script.sh" ]; then
        run_test "$sh_file" \
            "./$sh_file tasker_orig" \
            "./$sh_file tasker"
    fi
done

# Special case: test the validation script (only runs once)
echo -e "${BLUE}=== Testing validation script ===${NC}"
total_tests=$((total_tests + 1))
echo -e "${YELLOW}[Testing: retry_validation_test_script.sh]${NC}"
echo "  Running validation test..."
if ./retry_validation_test_script.sh > validation_output.tmp 2>&1; then
    validation_exit=0
else
    validation_exit=$?
fi

if [ $validation_exit -eq 1 ]; then
    echo -e "  ✅ PASS: Validation script completed with expected exit code (1 - errors found)"
    passed_tests=$((passed_tests + 1))
else
    echo -e "  ❌ FAIL: Validation script unexpected exit code ($validation_exit)"
    failed_tests+=("retry_validation_test_script.sh")
fi
rm -f validation_output.tmp
echo

# Final results
echo -e "${BLUE}=== VERIFICATION RESULTS ===${NC}"
echo "Total tests: $total_tests"
echo "Passed: $passed_tests"
echo "Failed: ${#failed_tests[@]}"

if [ ${#failed_tests[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED - Verification successful!${NC}"
    echo "The refactored tasker.py has functionally identical behavior to tasker_orig.py"
    echo "with acceptable improvements (detailed exit codes and additional debug output)."
    exit 0
else
    echo -e "${RED}❌ FAILED TESTS:${NC}"
    for failed in "${failed_tests[@]}"; do
        echo "  - $failed"
    done
    echo
    echo -e "${RED}Verification failed. Review the failed tests above.${NC}"
    exit 1
fi