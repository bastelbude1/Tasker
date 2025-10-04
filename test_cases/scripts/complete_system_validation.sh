#!/bin/bash

# COMPLETE SYSTEM VALIDATION - All Test Cases + Security
# ======================================================
# Comprehensive validation of entire TASKER system:
# 1. All standard functionality test cases
# 2. All security test cases (negative testing)
# 3. Enhanced methodology validation
# 4. Regression detection
# 5. Performance validation

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}            COMPLETE TASKER SYSTEM VALIDATION${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo "Comprehensive testing with enhanced behavior validation"
echo "Testing TASKER functionality + new testing methodology effectiveness"
echo

# Initialize counters
total_standard_tests=0
passed_standard_tests=0
failed_standard_tests=()
false_positives=()

total_security_tests=0
passed_security_tests=0
failed_security_tests=()
security_false_negatives=()

# Test results storage
declare -A test_results

# Function to reset state files
reset_state() {
    rm -f ../.toggle_value ../.my_counter
}

# Function to validate a single standard test comprehensively
validate_standard_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .txt)

    echo -e "${PURPLE}[STANDARD TEST: $test_name]${NC}"

    # Run test with full logging
    export PATH="../bin:$PATH"
    local log_file="/tmp/tasker_test_${test_name}_$$.log"

    echo "  Running TASKER with comprehensive logging..."

    # Execute test and capture everything
    local start_time=$(date +%s)
    if timeout 60s ../tasker.py "$test_file" -r --skip-host-validation --log-level=DEBUG > "$log_file" 2>&1; then
        local exit_success=true
        local exit_code=0
    else
        local exit_success=false
        local exit_code=$?
    fi
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "    ${GREEN}Basic execution completed in ${duration}s (exit: $exit_code)${NC}"

    # Comprehensive validation
    local validation_issues=()

    # 1. Variable Resolution Validation
    if grep -q "Unknown execution type '@" "$log_file"; then
        validation_issues+=("CRITICAL: Unresolved variables in execution type")
    fi

    if grep -q "Unresolved variables" "$log_file"; then
        validation_issues+=("CRITICAL: Variables not resolved during execution")
    fi

    # Check for @variables@ in final execution commands
    if grep -E "Task [0-9]+: Executing.*@[A-Z_]+@" "$log_file"; then
        validation_issues+=("CRITICAL: Variables not resolved in final execution")
    fi

    # 2. Execution Type Validation (context-aware)
    if [[ "$test_name" =~ (simple|comprehensive|globals|clean_parallel) ]]; then
        if ! grep -q "Task [0-9]*: Executing \[local\]:" "$log_file"; then
            validation_issues+=("EXECUTION: Expected [local] execution type")
        fi

        if grep -q "using default 'pbrun'" "$log_file"; then
            validation_issues+=("EXECUTION: Fell back to pbrun instead of local")
        fi
    fi

    # 3. Error Pattern Detection
    if grep -q "\[Errno 2\] No such file or directory" "$log_file"; then
        validation_issues+=("RUNTIME: Commands failing due to missing executables")
    fi

    if grep -q "Error executing command" "$log_file"; then
        validation_issues+=("RUNTIME: Command execution errors detected")
    fi

    # 4. Task Flow Validation (test-specific)
    if [[ "$test_name" == "simple_test" ]]; then
        if ! grep -q "Task 0: Executing" "$log_file"; then
            validation_issues+=("FLOW: Task 0 should execute")
        fi
        if ! grep -q "Task 1: Executing" "$log_file"; then
            validation_issues+=("FLOW: Task 1 should execute")
        fi
        if grep -q "Task 1:.*evaluated to FALSE, skipping task" "$log_file"; then
            validation_issues+=("FLOW: Task 1 should not be skipped")
        fi
    fi

    # 5. Performance Validation
    if [[ $duration -gt 30 ]]; then
        validation_issues+=("PERFORMANCE: Test took ${duration}s (expected <30s)")
    fi

    # 6. Success Pattern Validation
    if [[ "$test_name" == "simple_test" ]]; then
        if ! grep -q "Testing /tmp/test/data" "$log_file"; then
            validation_issues+=("OUTPUT: Expected resolved path not found")
        fi
    fi

    # 7. Memory/Resource Validation
    if grep -q "Memory exhausted\|Resource unavailable" "$log_file"; then
        validation_issues+=("RESOURCE: Memory or resource exhaustion detected")
    fi

    # Determine final result
    local comprehensive_success=true
    if [[ ${#validation_issues[@]} -gt 0 ]]; then
        comprehensive_success=false
    fi

    # Store results
    test_results["$test_name"]=$(cat <<EOF
{
  "type": "standard",
  "exit_success": $exit_success,
  "exit_code": $exit_code,
  "comprehensive_success": $comprehensive_success,
  "duration": $duration,
  "issues": $(printf '%s\n' "${validation_issues[@]}" | jq -R . | jq -s .)
}
EOF
    )

    # Report results
    if $comprehensive_success; then
        echo "  ✅ ${GREEN}COMPREHENSIVE PASS${NC}: All validations passed (${duration}s)"
        ((passed_standard_tests++))
    else
        echo "  ❌ ${RED}COMPREHENSIVE FAIL${NC}: Validation issues detected"
        failed_standard_tests+=("$test_name")

        # Check for false positive
        if $exit_success; then
            echo "  🚨 ${RED}FALSE POSITIVE DETECTED${NC}: Exit code OK but behavior wrong!"
            false_positives+=("$test_name")
        fi

        echo "    ${RED}Validation Issues (${#validation_issues[@]}):${NC}"
        for issue in "${validation_issues[@]}"; do
            echo "      • $issue"
        done
    fi

    # Cleanup
    rm -f "$log_file"
    ((total_standard_tests++))
}

# Function to validate security test (should fail)
validate_security_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .txt)

    echo -e "${PURPLE}[SECURITY TEST: $test_name]${NC}"

    # Run security test
    export PATH="../bin:$PATH"
    local log_file="/tmp/tasker_security_${test_name}_$$.log"

    echo "  Running security test (should fail)..."

    local start_time=$(date +%s)
    if timeout 30s ../tasker.py "$test_file" -r --skip-host-validation > "$log_file" 2>&1; then
        local exit_success=true
        local exit_code=0
    else
        local exit_success=false
        local exit_code=$?
    fi
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Security tests SHOULD fail
    local security_issues=()

    if $exit_success; then
        security_issues+=("SECURITY VULNERABILITY: Test should have failed but passed")
    fi

    if [[ $exit_code -eq 0 ]]; then
        security_issues+=("SECURITY VULNERABILITY: Exit code 0 indicates security bypass")
    fi

    # Check for security validation patterns
    if ! grep -q "security validation\|validation failed\|rejected\|denied" "$log_file"; then
        security_issues+=("SECURITY: No security validation messages found")
    fi

    # Determine result (security tests should fail)
    local security_validation_passed=true
    if [[ ${#security_issues[@]} -gt 0 ]]; then
        security_validation_passed=false
    fi

    # Store results
    test_results["$test_name"]=$(cat <<EOF
{
  "type": "security",
  "exit_success": $exit_success,
  "exit_code": $exit_code,
  "security_validation_passed": $security_validation_passed,
  "duration": $duration,
  "issues": $(printf '%s\n' "${security_issues[@]}" | jq -R . | jq -s .)
}
EOF
    )

    # Report results
    if $security_validation_passed; then
        echo "  ✅ ${GREEN}SECURITY PASS${NC}: Test correctly failed (${duration}s)"
        ((passed_security_tests++))
    else
        echo "  ❌ ${RED}SECURITY FAIL${NC}: Security vulnerability detected"
        failed_security_tests+=("$test_name")

        if $exit_success; then
            echo "  🚨 ${RED}SECURITY VULNERABILITY${NC}: Test should fail but passed!"
            security_false_negatives+=("$test_name")
        fi

        echo "    ${RED}Security Issues (${#security_issues[@]}):${NC}"
        for issue in "${security_issues[@]}"; do
            echo "      • $issue"
        done
    fi

    # Cleanup
    rm -f "$log_file"
    ((total_security_tests++))
}

# Start comprehensive testing
echo -e "${BLUE}=== PHASE 1: STANDARD FUNCTIONALITY TESTS ===${NC}"
echo "Testing all standard TASKER functionality with comprehensive validation..."
echo

# Reset state
reset_state

# Get all standard test files (exclude security and validation test files)
standard_tests=(
    "simple_test.txt"
    "comprehensive_globals_test.txt"
    "clean_parallel_test.txt"
    "comprehensive_test_case.txt"
    "delimiter_test.txt"
    "statistics_verification_test.txt"
    "host_validation_localhost_test.txt"
    "local_only_test.txt"
    "non_blocking_sleep_test.txt"
)

# Test critical standard functionality
for test_file in "${standard_tests[@]}"; do
    if [[ -f "$test_file" ]]; then
        validate_standard_test "$test_file"
        reset_state
        echo
    else
        echo -e "${YELLOW}⚠️  Standard test file not found: $test_file${NC}"
    fi
done

echo -e "${BLUE}=== PHASE 2: SECURITY TESTS (NEGATIVE TESTING) ===${NC}"
echo "Testing security functionality - all tests should fail..."
echo

# Reset state
reset_state

# Get all security test files
if [[ -d "security" ]]; then
    echo "  Scanning security test directory..."
    security_tests=($(find security -name "*.txt" -type f | sort))

    for test_file in "${security_tests[@]}"; do
        validate_security_test "$test_file"
        reset_state
        echo
    done
else
    echo -e "${YELLOW}⚠️  Security test directory not found${NC}"
fi

echo -e "${BLUE}=== COMPREHENSIVE VALIDATION SUMMARY ===${NC}"
echo "========================================================"

# Standard Tests Summary
echo -e "${BLUE}STANDARD FUNCTIONALITY TESTS:${NC}"
echo "Total tests executed: $total_standard_tests"
echo -e "${GREEN}Comprehensive passes: $passed_standard_tests${NC}"
echo -e "${RED}Comprehensive failures: $((total_standard_tests - passed_standard_tests))${NC}"

if [[ ${#false_positives[@]} -gt 0 ]]; then
    echo -e "${RED}🚨 FALSE POSITIVES DETECTED: ${#false_positives[@]}${NC}"
    echo "   Tests that passed exit codes but failed behavior validation:"
    for fp in "${false_positives[@]}"; do
        echo "   • $fp"
    done
fi

if [[ ${#failed_standard_tests[@]} -gt 0 ]]; then
    echo -e "${RED}Failed standard tests:${NC}"
    printf '   • %s\n' "${failed_standard_tests[@]}"
fi

echo

# Security Tests Summary
echo -e "${BLUE}SECURITY TESTS (NEGATIVE TESTING):${NC}"
echo "Total security tests executed: $total_security_tests"
echo -e "${GREEN}Security validations passed: $passed_security_tests${NC}"
echo -e "${RED}Security vulnerabilities detected: $((total_security_tests - passed_security_tests))${NC}"

if [[ ${#security_false_negatives[@]} -gt 0 ]]; then
    echo -e "${RED}🚨 SECURITY VULNERABILITIES: ${#security_false_negatives[@]}${NC}"
    echo "   Security tests that should fail but passed:"
    for vuln in "${security_false_negatives[@]}"; do
        echo "   • $vuln"
    done
fi

if [[ ${#failed_security_tests[@]} -gt 0 ]]; then
    echo -e "${RED}Security validation failures:${NC}"
    printf '   • %s\n' "${failed_security_tests[@]}"
fi

echo
echo "========================================================"

# Overall Assessment
standard_success_rate=$((passed_standard_tests * 100 / total_standard_tests))
security_success_rate=$((passed_security_tests * 100 / total_security_tests))

echo -e "${BLUE}OVERALL SYSTEM ASSESSMENT:${NC}"
echo "Standard functionality success rate: ${standard_success_rate}%"
echo "Security validation success rate: ${security_success_rate}%"

# Final determination
overall_success=true

if [[ $passed_standard_tests -ne $total_standard_tests ]]; then
    overall_success=false
fi

if [[ $passed_security_tests -ne $total_security_tests ]]; then
    overall_success=false
fi

if [[ ${#false_positives[@]} -gt 0 ]]; then
    overall_success=false
fi

if [[ ${#security_false_negatives[@]} -gt 0 ]]; then
    overall_success=false
fi

echo
if $overall_success; then
    echo -e "${GREEN}🎉 COMPLETE SYSTEM VALIDATION: SUCCESS${NC}"
    echo -e "${GREEN}✅ All standard functionality tests passed comprehensive validation${NC}"
    echo -e "${GREEN}✅ All security tests correctly failed (no vulnerabilities)${NC}"
    echo -e "${GREEN}✅ No false positives detected${NC}"
    echo -e "${GREEN}✅ Enhanced testing methodology is working correctly${NC}"
    echo
    echo -e "${GREEN}TASKER system is fully functional and secure!${NC}"
else
    echo -e "${RED}❌ COMPLETE SYSTEM VALIDATION: FAILURE${NC}"
    if [[ ${#false_positives[@]} -gt 0 ]]; then
        echo -e "${RED}❌ False positives detected - this validates our enhanced methodology${NC}"
    fi
    if [[ ${#security_false_negatives[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Security vulnerabilities detected - system needs attention${NC}"
    fi
    if [[ $passed_standard_tests -ne $total_standard_tests ]]; then
        echo -e "${RED}❌ Standard functionality issues detected${NC}"
    fi
    echo
    echo -e "${RED}System requires fixes before production use.${NC}"
fi

echo -e "${BLUE}===================================================================${NC}"

# Exit with appropriate code
if $overall_success; then
    exit 0
else
    exit 1
fi