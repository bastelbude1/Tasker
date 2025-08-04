#!/bin/bash

echo "=== QUICK VERIFICATION TEST ==="
echo "Testing representative sample of test cases to verify functionality"
echo ""

# Test basic functionality
echo "=== Basic Functionality Tests ==="
basic_tests=(
    "simple_test.txt"
    "local_only_test.txt" 
    "first_test_simple.txt"
)

for test in "${basic_tests[@]}"; do
    echo -n "Testing $test... "
    if timeout 30 ./tasker.py "test_cases/$test" --skip-host-validation >/dev/null 2>&1; then
        echo "✅ PASS"
    else
        echo "❌ FAIL (exit code: $?)"
    fi
done

echo ""
echo "=== Advanced Functionality Tests ==="
advanced_tests=(
    "retry_test_1_basic.txt"
    "retry_test_2_timeout.txt"
    "comprehensive_globals_test.txt"
    "conditional_comprehensive_test.txt"
)

for test in "${advanced_tests[@]}"; do
    echo -n "Testing $test... "
    if timeout 60 ./tasker.py "test_cases/$test" --skip-host-validation >/dev/null 2>&1; then
        echo "✅ PASS"
    else
        echo "❌ FAIL (exit code: $?)"
    fi
done

echo ""
echo "=== Validation Tests (should fail) ==="
validation_tests=(
    "comprehensive_retry_validation_test.txt"
)

for test in "${validation_tests[@]}"; do
    echo -n "Testing $test (expecting validation failure)... "
    ./tasker.py "test_cases/$test" --skip-host-validation >/dev/null 2>&1
    exit_code=$?
    if [ $exit_code -eq 20 ]; then
        echo "✅ PASS (validation failed as expected)"
    else
        echo "❌ FAIL (exit code: $exit_code, expected 20)"
    fi
done

echo ""
echo "=== Validate-only Flag Tests ==="
echo -n "Testing --validate-only with valid file... "
if ./tasker.py "test_cases/simple_test.txt" --validate-only --skip-host-validation >/dev/null 2>&1; then
    echo "✅ PASS"
else
    echo "❌ FAIL (exit code: $?)"
fi

echo -n "Testing --validate-only with invalid file... "
./tasker.py "test_cases/comprehensive_retry_validation_test.txt" --validate-only --skip-host-validation >/dev/null 2>&1
exit_code=$?
if [ $exit_code -eq 20 ]; then
    echo "✅ PASS (validation failed as expected)"
else
    echo "❌ FAIL (exit code: $exit_code, expected 20)"
fi

echo ""
echo "=== Debug Flag Test ==="
echo -n "Testing -d flag (no deprecation warning)... "
output=$(./tasker.py "test_cases/simple_test.txt" --validate-only --skip-host-validation -d 2>&1)
if echo "$output" | grep -q "deprecated" >/dev/null 2>&1; then
    echo "❌ FAIL (deprecation warning still present)"
else
    echo "✅ PASS (no deprecation warning)"
fi

echo ""
echo "=== VERIFICATION COMPLETE ==="