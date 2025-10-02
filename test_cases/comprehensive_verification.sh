#!/bin/bash

# COMPREHENSIVE VERIFICATION - Deep Behavior Validation
# ====================================================
# Goes beyond exit codes to validate actual behavior:
# - Variable resolution correctness
# - Execution path validation
# - Log content analysis
# - Pattern-based regression detection
#
# This catches issues that simple exit code checking misses.

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== COMPREHENSIVE VERIFICATION PROTOCOL ===${NC}"
echo "Deep behavior validation beyond exit codes"
echo "Validates variable resolution, execution paths, and log content"
echo "60-second timeout per test - 100% BEHAVIOR CORRECTNESS required"
echo

total_tests=0
passed_tests=0
failed_tests=()
false_positives=()

# Function to validate a single test comprehensively
validate_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .txt)

    echo -e "${YELLOW}[Testing: $test_name]${NC}"

    # Run test with full logging
    export PATH="../test_scripts:$PATH"
    local log_file="/tmp/tasker_test_${test_name}_$$.log"

    echo "  Running TASKER with comprehensive logging..."

    # Execute test and capture everything
    if timeout 60s ../tasker.py "$test_file" -r --skip-host-validation --log-level=DEBUG > "$log_file" 2>&1; then
        local exit_success=true
        local exit_code=0
    else
        local exit_success=false
        local exit_code=$?
    fi

    echo "    ${GREEN}Basic execution completed (exit: $exit_code)${NC}"

    # Now do comprehensive validation
    local validation_issues=()

    # 1. Variable Resolution Validation
    if grep -q "Unknown execution type '@" "$log_file"; then
        validation_issues+=("UNRESOLVED VARIABLES: Execution type contains @variables@")
    fi

    if grep -q "Unresolved variables" "$log_file"; then
        validation_issues+=("UNRESOLVED VARIABLES: Variables not replaced during execution")
    fi

    # Check for @variables@ in final execution commands (shouldn't be there)
    if grep -E "Task [0-9]+: Executing.*@[A-Z_]+@" "$log_file"; then
        validation_issues+=("VARIABLE RESOLUTION FAILURE: @variables@ found in final execution")
    fi

    # 2. Execution Type Validation (for tests that should use 'local')
    if [[ "$test_name" == "simple_test" || "$test_name" == "comprehensive_globals_test" ]]; then
        if ! grep -q "Task [0-9]*: Executing \[local\]:" "$log_file"; then
            validation_issues+=("WRONG EXECUTION TYPE: Expected [local] execution")
        fi

        if grep -q "using default 'pbrun'" "$log_file"; then
            validation_issues+=("EXECUTION TYPE FALLBACK: Fell back to pbrun instead of local")
        fi
    fi

    # 3. Error Pattern Detection
    if grep -q "\[Errno 2\] No such file or directory" "$log_file"; then
        validation_issues+=("COMMAND NOT FOUND: Commands are failing due to missing executables")
    fi

    # 4. Task Execution Flow Validation
    if [[ "$test_name" == "simple_test" ]]; then
        # Both tasks should execute for simple_test
        if ! grep -q "Task 0: Executing" "$log_file"; then
            validation_issues+=("TASK FLOW ERROR: Task 0 should execute")
        fi
        if ! grep -q "Task 1: Executing" "$log_file"; then
            validation_issues+=("TASK FLOW ERROR: Task 1 should execute")
        fi
        if grep -q "Task 1:.*evaluated to FALSE, skipping task" "$log_file"; then
            validation_issues+=("TASK FLOW ERROR: Task 1 should not be skipped")
        fi
    fi

    # 5. Success Pattern Validation
    if [[ "$test_name" == "simple_test" ]]; then
        # Should have specific expected outputs
        if ! grep -q "Testing /tmp/test/data" "$log_file"; then
            validation_issues+=("OUTPUT ERROR: Expected resolved path not found")
        fi
    fi

    # Determine final result
    local comprehensive_success=true
    if [[ ${#validation_issues[@]} -gt 0 ]]; then
        comprehensive_success=false
    fi

    # Report results
    if $comprehensive_success; then
        echo "  ✅ ${GREEN}COMPREHENSIVE PASS${NC}: All validations passed"
        ((passed_tests++))
    else
        echo "  ❌ ${RED}COMPREHENSIVE FAIL${NC}: Validation issues detected"
        failed_tests+=("$test_name")

        # Check if this is a false positive (exit success but behavior fail)
        if $exit_success; then
            echo "  🚨 ${RED}FALSE POSITIVE DETECTED${NC}: Exit code OK but behavior wrong!"
            false_positives+=("$test_name")
        fi

        echo "    ${RED}Validation Issues:${NC}"
        for issue in "${validation_issues[@]}"; do
            echo "      • $issue"
        done

        # Show relevant log excerpts
        echo "    ${YELLOW}Relevant Log Excerpts:${NC}"
        grep -E "(Unknown execution type|Unresolved variables|Errno|evaluated to FALSE)" "$log_file" | head -5 | while read line; do
            echo "      $line"
        done
    fi

    # Cleanup
    rm -f "$log_file"

    ((total_tests++))
}

# Function to reset state files
reset_state() {
    rm -f ../.toggle_value ../.my_counter
}

echo -e "${BLUE}=== Testing critical test cases ===${NC}"
echo "Focusing on tests that should catch regressions..."

# Reset state before starting
reset_state

# Test critical cases that were failing silently
critical_tests=(
    "simple_test.txt"
    "comprehensive_globals_test.txt"
    "clean_parallel_test.txt"
)

for test_file in "${critical_tests[@]}"; do
    if [[ -f "$test_file" ]]; then
        validate_test "$test_file"
        reset_state
    else
        echo -e "${YELLOW}⚠️  Test file not found: $test_file${NC}"
    fi
    echo
done

# Summary
echo -e "${BLUE}=== COMPREHENSIVE VALIDATION SUMMARY ===${NC}"
echo "Total tests executed: $total_tests"
echo -e "${GREEN}Comprehensive passes: $passed_tests${NC}"
echo -e "${RED}Comprehensive failures: $((total_tests - passed_tests))${NC}"

if [[ ${#false_positives[@]} -gt 0 ]]; then
    echo -e "${RED}🚨 FALSE POSITIVES DETECTED: ${#false_positives[@]}${NC}"
    echo "   These tests would have passed with basic exit code checking"
    echo "   but failed comprehensive behavior validation:"
    for fp in "${false_positives[@]}"; do
        echo "   • $fp"
    done
    echo
    echo -e "${YELLOW}This demonstrates why comprehensive validation is essential!${NC}"
fi

if [[ ${#failed_tests[@]} -gt 0 ]]; then
    echo -e "${RED}Failed tests:${NC}"
    printf ' • %s\n' "${failed_tests[@]}"
    echo
    echo -e "${RED}❌ COMPREHENSIVE VALIDATION FAILED${NC}"
    echo "   Issues detected that basic exit code testing would miss"
else
    echo -e "${GREEN}🎉 ALL TESTS PASSED COMPREHENSIVE VALIDATION${NC}"
    echo "   No false positives or hidden regressions detected"
fi

# Exit with appropriate code
if [[ $passed_tests -eq $total_tests ]]; then
    exit 0
else
    exit 1
fi