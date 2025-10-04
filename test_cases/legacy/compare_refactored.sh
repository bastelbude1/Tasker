#!/bin/bash

# REFACTORING VERIFICATION - Compare tasker.py vs tasker_backup.py
# Comprehensive comparison of all *.txt test cases
# Ensures refactored version behaves identically to pre-refactoring version

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== REFACTORING VERIFICATION ====${NC}"
echo "Comparing refactored tasker.py vs tasker_backup.py (pre-refactoring)"
echo "Testing each .txt file with both versions to ensure identical behavior"
echo "60-second timeout per test - 100% SUCCESS required (any timeout = FAILURE)"
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

# Function to run a single comparison test
run_comparison_test() {
    local test_name="$1"
    echo -e "${YELLOW}[Testing: $test_name]${NC}"
    total_tests=$((total_tests + 1))
    
    # Reset state and run with tasker_backup.py (pre-refactoring)
    reset_state
    echo "  Running tasker_backup.py (pre-refactoring)..."
    
    # Capture stderr to check for Python exceptions
    backup_error=$(timeout 60s ../tasker_backup.py "$test_name" -r 2>&1 >/dev/null)
    backup_exit=$?
    
    # Check for Python exceptions in backup version
    if echo "$backup_error" | grep -E "(Traceback|AttributeError|Exception|Error:)" > /dev/null; then
        echo -e "    ${RED}EXCEPTION DETECTED in tasker_backup.py:${NC}"
        echo "$backup_error" | head -3
        failed_tests+=("$test_name")
        echo -e "  ❌ FAIL: Python exception in backup - unexpected"
        return
    fi
    
    if [ $backup_exit -eq 124 ]; then
        echo -e "    ${RED}TIMEOUT: tasker_backup.py (60s timeout)${NC}"
        timeout_tests+=("$test_name (backup)")
        failed_tests+=("$test_name")
        echo -e "  ❌ FAIL: Timeout in backup after 60s - FAILURE"
        return
    fi
    
    # Reset state and run with tasker.py (refactored)
    reset_state
    echo "  Running tasker.py (refactored)..."
    
    # Capture stderr to check for Python exceptions
    refactored_error=$(timeout 60s ../tasker.py "$test_name" -r 2>&1 >/dev/null)
    refactored_exit=$?
    
    # Check for Python exceptions in refactored version
    if echo "$refactored_error" | grep -E "(Traceback|AttributeError|Exception|Error:)" > /dev/null; then
        echo -e "    ${RED}EXCEPTION DETECTED in tasker.py:${NC}"
        echo "$refactored_error" | head -3
        failed_tests+=("$test_name")
        echo -e "  ❌ FAIL: Python exception in refactored - regression bug"
        return
    fi
    
    if [ $refactored_exit -eq 124 ]; then
        echo -e "    ${RED}TIMEOUT: tasker.py (60s timeout)${NC}"
        timeout_tests+=("$test_name (refactored)")
        failed_tests+=("$test_name")
        echo -e "  ❌ FAIL: Timeout in refactored after 60s - FAILURE"
        return
    fi
    
    # Compare results
    if [ $refactored_exit -eq $backup_exit ]; then
        echo -e "  ✅ PASS: Exit codes match ($refactored_exit)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "  ❌ FAIL: Exit codes differ (refactored: $refactored_exit, backup: $backup_exit)"
        failed_tests+=("$test_name")
    fi
    echo
}

# Test all .txt files
echo -e "${BLUE}=== Testing all .txt files ===${NC}"
for txt_file in *.txt; do
    if [ -f "$txt_file" ]; then
        run_comparison_test "$txt_file"
    fi
done

# Results
echo -e "${BLUE}=== REFACTORING VERIFICATION RESULTS ===${NC}"
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
    echo -e "${GREEN}🎉 100% SUCCESS - REFACTORING VERIFIED!${NC}"
    echo -e "${GREEN}    Refactored tasker.py behaves identically to pre-refactoring version!${NC}"
    echo -e "${GREEN}    All functionality preserved - optimal refactoring achieved!${NC}"
    exit 0
else
    echo -e "${RED}❌ REFACTORING VERIFICATION FAILED${NC}"
    echo -e "${RED}    Refactoring introduced behavioral changes - needs investigation${NC}"
    exit 1
fi