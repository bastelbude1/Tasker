#!/bin/bash

# Ensure PATH includes test scripts for host validation tests
export PATH="/home/baste/tasker/test_scripts:$PATH"

echo "=== EXTENDED VERIFICATION TEST ==="
echo "Testing all major test categories to verify functionality"
echo ""

# Test categories
declare -a basic_tests=(
    "simple_test.txt"
    "local_only_test.txt" 
    "first_test_simple.txt"
)

declare -a retry_tests=(
    "retry_test_1_basic.txt"
    "retry_test_2_timeout.txt"
    "retry_test_3_custom_success.txt"
    "retry_test_4_high_retry.txt"
    "retry_test_5_mixed.txt"
    "local_retry_test.txt"
    "retry_attempt_test_case.txt"
    "retry_logic_test_case.txt"
)

declare -a parallel_tests=(
    "clean_parallel_test.txt"
    "simplified_parallel_test.txt"
    "timeout_test_parallel.txt"
    "stress_test_parallel.txt"
)

declare -a complex_tests=(
    "comprehensive_globals_test.txt"
    "conditional_comprehensive_test.txt"
    "comprehensive_test_case.txt"
    "comprehensive_test_case_fixed.txt"
    "comprehensive_retry_test_case.txt"
    "master_timeout_comprehensive_test.txt"
)

declare -a timeout_tests=(
    "debug_timeout_test.txt"
    "simple_timeout_comparison.txt"
)

declare -a validation_tests=(
    "host_validation_localhost_test.txt"
    "host_validation_test.txt"
)

declare -a validation_fail_tests=(
    "comprehensive_retry_validation_test.txt"
    "host_validation_error_test.txt"
    "host_validation_connection_error_test.txt"
    "example_task.txt"
)

declare -a stats_tests=(
    "statistics_verification_test.txt"
)

# Function to run test category
run_test_category() {
    local category_name="$1"
    shift
    local tests=("$@")
    
    echo "=== $category_name ==="
    local passed=0
    local total=${#tests[@]}
    
    for test in "${tests[@]}"; do
        # Determine correct paths based on current directory
        if [ -f "test_cases/$test" ]; then
            test_file="test_cases/$test"
            tasker_script="./tasker.py"
        elif [ -f "$test" ]; then
            test_file="$test"
            tasker_script="../tasker.py"
        else
            echo "⚠️  SKIP $test (file not found)"
            continue
        fi
        
        echo -n "Testing $test... "
        # Clean up state files before each test
        rm -f ~/.toggle_value ~/.my_counter
        # Use --skip-host-validation for non-host-validation tests only
        if [[ "$test" == host_validation_* ]]; then
            # Host validation tests should NOT skip host validation and need PATH
            test_passed=$(PATH="/home/baste/tasker/test_scripts:$PATH" timeout 90 "$tasker_script" "$test_file" -r >/dev/null 2>&1; echo $?)
        else
            # Other tests can skip host validation for speed
            test_passed=$(timeout 90 "$tasker_script" "$test_file" -r --skip-host-validation >/dev/null 2>&1; echo $?)
        fi
        
        if [ "$test_passed" -eq 0 ]; then
            echo "✅ PASS"
            ((passed++))
        else
            echo "❌ FAIL (exit code: $?)"
        fi
    done
    
    echo "Result: $passed/$total tests passed"
    echo ""
}

# Function to run failing validation tests
run_validation_fail_category() {
    local category_name="$1"
    shift
    local tests=("$@")
    
    echo "=== $category_name ==="
    local passed=0
    local total=${#tests[@]}
    
    for test in "${tests[@]}"; do
        # Determine correct paths based on current directory
        if [ -f "test_cases/$test" ]; then
            test_file="test_cases/$test"
            tasker_script="./tasker.py"
        elif [ -f "$test" ]; then
            test_file="$test"
            tasker_script="../tasker.py"
        else
            echo "⚠️  SKIP $test (file not found)"
            continue
        fi
        
        echo -n "Testing $test (expecting failure)... "
        # Clean up state files before each test
        rm -f ~/.toggle_value ~/.my_counter
        # Use --skip-host-validation for non-host-validation tests only
        if [[ "$test" == host_validation_* ]]; then
            # Host validation tests should NOT skip host validation and need PATH
            PATH="/home/baste/tasker/test_scripts:$PATH" "$tasker_script" "$test_file" -r >/dev/null 2>&1
        else
            # Other tests can skip host validation for speed
            "$tasker_script" "$test_file" -r --skip-host-validation >/dev/null 2>&1
        fi
        exit_code=$?
        if [ $exit_code -ne 0 ]; then
            echo "✅ PASS (failed as expected, exit code: $exit_code)"
            ((passed++))
        else
            echo "❌ FAIL (should have failed but passed)"
        fi
    done
    
    echo "Result: $passed/$total tests passed"
    echo ""
}

# Run all test categories
run_test_category "Basic Functionality Tests" "${basic_tests[@]}"
run_test_category "Retry Logic Tests" "${retry_tests[@]}" 
run_test_category "Parallel Execution Tests" "${parallel_tests[@]}"
run_test_category "Complex Workflow Tests" "${complex_tests[@]}"
run_test_category "Timeout Handling Tests" "${timeout_tests[@]}"
run_test_category "Host Validation Tests" "${validation_tests[@]}"
run_validation_fail_category "Validation Failure Tests (should fail)" "${validation_fail_tests[@]}"
run_test_category "Statistics Tests" "${stats_tests[@]}"

echo "=== EXTENDED VERIFICATION COMPLETE ==="