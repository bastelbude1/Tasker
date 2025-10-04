#!/bin/bash

echo "=== QUICK VERIFICATION TEST ==="
echo "Testing representative sample of test cases to verify functionality"
echo "Updated for organized directory structure"
echo ""

# Get script directory for absolute path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$TEST_ROOT")"

# Set PATH for supporting scripts
export PATH="$TEST_ROOT/bin:$PATH"

# Test basic functionality (now from functional/ directory)
echo "=== Basic Functionality Tests ==="
basic_tests=(
    "$TEST_ROOT/functional/simple_test.txt"
    "$TEST_ROOT/functional/local_only_test.txt"
    "$TEST_ROOT/functional/first_test_simple.txt"
)

for test in "${basic_tests[@]}"; do
    echo -n "Testing $test... "
    if timeout 30 "$REPO_ROOT/tasker.py" "$test" -r --skip-host-validation >/dev/null 2>&1; then
        echo "✅ PASS"
    else
        echo "❌ FAIL (exit code: $?)"
    fi
done

echo ""
echo "=== Advanced Functionality Tests ==="
advanced_tests=(
    "$TEST_ROOT/functional/retry_test_1_basic.txt"
    "$TEST_ROOT/edge_cases/retry_test_2_timeout.txt"
    "$TEST_ROOT/integration/comprehensive_globals_test.txt"
    "$TEST_ROOT/integration/conditional_comprehensive_test.txt"
)

for test in "${advanced_tests[@]}"; do
    echo -n "Testing $test... "
    if timeout 60 "$REPO_ROOT/tasker.py" "$test" -r --skip-host-validation >/dev/null 2>&1; then
        echo "✅ PASS"
    else
        echo "❌ FAIL (exit code: $?)"
    fi
done

echo ""
echo "=== Validation Tests (should fail) ==="
validation_tests=(
    "$TEST_ROOT/edge_cases/comprehensive_retry_validation_test.txt"
)

for test in "${validation_tests[@]}"; do
    echo -n "Testing $test (expecting validation failure)... "
    "$REPO_ROOT/tasker.py" "$test" --skip-host-validation >/dev/null 2>&1
    exit_code=$?
    if [ $exit_code -eq 20 ]; then
        echo "✅ PASS (validation failed as expected)"
    else
        echo "❌ FAIL (exit code: $exit_code, expected 20)"
    fi
done

echo ""
echo "=== Security Tests (should fail) ==="
security_tests=(
    "$TEST_ROOT/security/command_injection_basic_test.txt"
    "$TEST_ROOT/security/malformed_syntax_test.txt"
)

for test in "${security_tests[@]}"; do
    echo -n "Testing $test (expecting security rejection)... "
    "$REPO_ROOT/tasker.py" "$test" --validate-only >/dev/null 2>&1
    exit_code=$?
    if [ $exit_code -eq 20 ] || [ $exit_code -eq 21 ]; then
        echo "✅ PASS (security rejection as expected)"
    else
        echo "❌ FAIL (exit code: $exit_code, expected 20 or 21)"
    fi
done

echo ""
echo "=== Validate-only Flag Tests ==="
echo -n "Testing --validate-only with valid file... "
if "$REPO_ROOT/tasker.py" "$TEST_ROOT/functional/simple_test.txt" --validate-only --skip-host-validation >/dev/null 2>&1; then
    echo "✅ PASS"
else
    echo "❌ FAIL (exit code: $?)"
fi

echo -n "Testing --validate-only with invalid file... "
"$REPO_ROOT/tasker.py" "$TEST_ROOT/edge_cases/comprehensive_retry_validation_test.txt" --validate-only --skip-host-validation >/dev/null 2>&1
exit_code=$?
if [ $exit_code -eq 20 ]; then
    echo "✅ PASS (validation failed as expected)"
else
    echo "❌ FAIL (exit code: $exit_code, expected 20)"
fi

echo ""
echo "=== Debug Flag Test ==="
echo -n "Testing -d flag (no deprecation warning)... "
output=$("$REPO_ROOT/tasker.py" "$TEST_ROOT/functional/simple_test.txt" --validate-only --skip-host-validation -d 2>&1)
if echo "$output" | grep -q "deprecated" >/dev/null 2>&1; then
    echo "❌ FAIL (deprecation warning still present)"
else
    echo "✅ PASS (no deprecation warning)"
fi

echo ""
echo "=== VERIFICATION COMPLETE ==="