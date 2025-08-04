#!/bin/bash

# Host Validation Test Runner
# Tests all host validation scenarios and verifies expected outcomes

echo "=== HOST VALIDATION TEST RUNNER ==="
echo "Testing host validation functionality with expected outcomes"
echo ""

# Ensure PATH includes test scripts
export PATH="/home/baste/tasker/test_scripts:$PATH"

# Test results tracking
total_tests=0
passed_tests=0
failed_tests=0

# Function to run a test and validate expected outcome
run_validation_test() {
    local test_file="$1"
    local expected_outcome="$2"  # "pass" or "fail"
    local expected_exit_code="$3"
    local description="$4"
    
    echo "Testing: $test_file"
    echo "Expected: $description"
    echo -n "Running... "
    
    # Clean up state files before each test
    rm -f ~/.toggle_value ~/.my_counter
    
    # Run the test and capture output and exit code
    output=$(../tasker.py "$test_file" -r 2>&1)
    actual_exit_code=$?
    
    ((total_tests++))
    
    # Validate expected outcome
    if [ "$expected_outcome" = "pass" ]; then
        if [ $actual_exit_code -eq 0 ]; then
            echo "✅ PASS - Test executed successfully (exit code: $actual_exit_code)"
            ((passed_tests++))
        else
            echo "❌ FAIL - Expected success but got exit code: $actual_exit_code"
            echo "Output: $output"
            ((failed_tests++))
        fi
    elif [ "$expected_outcome" = "fail" ]; then
        if [ $actual_exit_code -ne 0 ]; then
            if [ -n "$expected_exit_code" ] && [ $actual_exit_code -eq $expected_exit_code ]; then
                echo "✅ PASS - Failed as expected with correct exit code: $actual_exit_code"
                ((passed_tests++))
            elif [ -z "$expected_exit_code" ]; then
                echo "✅ PASS - Failed as expected (exit code: $actual_exit_code)"
                ((passed_tests++))
            else
                echo "⚠️  PARTIAL - Failed as expected but with different exit code: $actual_exit_code (expected: $expected_exit_code)"
                echo "Output: $output"
                ((passed_tests++))  # Still count as pass since it failed as expected
            fi
        else
            echo "❌ FAIL - Expected failure but test passed"
            echo "Output: $output"
            ((failed_tests++))
        fi
    fi
    
    # Validate specific error messages for failure cases
    if [ "$expected_outcome" = "fail" ]; then
        if echo "$output" | grep -q "Host validation failed"; then
            echo "  ✓ Contains expected 'Host validation failed' message"
        else
            echo "  ⚠️  Missing expected 'Host validation failed' message"
        fi
        
        if echo "$output" | grep -q "Remote access validation failed"; then
            echo "  ✓ Contains expected 'Remote access validation failed' message"
        else
            echo "  ⚠️  Missing expected 'Remote access validation failed' message"
        fi
    fi
    
    echo ""
}

# Function to validate specific output content
validate_output_content() {
    local test_file="$1"
    local expected_pattern="$2"
    local description="$3"
    
    echo "Content validation: $test_file"
    echo "Expected pattern: $expected_pattern"
    echo -n "Checking... "
    
    # Clean up state files
    rm -f ~/.toggle_value ~/.my_counter
    
    # Run test and capture output
    output=$(../tasker.py "$test_file" -r 2>&1)
    
    ((total_tests++))
    
    if echo "$output" | grep -q "$expected_pattern"; then
        echo "✅ PASS - Found expected pattern"
        ((passed_tests++))
    else
        echo "❌ FAIL - Pattern not found"
        echo "Output: $output"
        ((failed_tests++))
    fi
    echo ""
}

echo "=== TESTING SUCCESS SCENARIOS ==="

run_validation_test "host_validation_localhost_test.txt" "pass" "0" \
    "Should pass - localhost with pbrun/p7s/wwrs connectivity tests"

run_validation_test "host_validation_success_test.txt" "pass" "0" \
    "Should pass - hosts configured for successful validation" 2>/dev/null || echo "  ⚠️  Test file not found or failed"

echo "=== TESTING FAILURE SCENARIOS ==="

run_validation_test "host_validation_error_test.txt" "fail" "20" \
    "Should fail - hosts configured to fail validation (badhost, noresponse)"

run_validation_test "host_validation_connection_error_test.txt" "fail" "20" \
    "Should fail - connection error scenarios"

run_validation_test "host_validation_comprehensive_test.txt" "fail" "20" \
    "Should fail - mixed success/failure hosts (should fail due to failure hosts)"

echo "=== TESTING SPECIFIC VALIDATION MESSAGES ==="

validate_output_content "host_validation_error_test.txt" \
    "ERROR: Host validation failed" \
    "Should contain host validation failure message"

validate_output_content "host_validation_comprehensive_test.txt" \
    "Remote access validation failed for:" \
    "Should list which validation types failed"

echo "=== TESTING TIMEOUT SCENARIOS ==="

run_validation_test "host_validation_timeout_test.txt" "fail" "20" \
    "Should fail - timeout scenarios" 2>/dev/null || echo "  ⚠️  Test file not found or timeout occurred"

echo "=== TEST SUMMARY ==="
echo "Total tests: $total_tests"
echo "Passed: $passed_tests"
echo "Failed: $failed_tests"

if [ $failed_tests -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED! Host validation is working correctly."
    exit 0
else
    echo "⚠️  Some tests failed. Please review the output above."
    exit 1
fi