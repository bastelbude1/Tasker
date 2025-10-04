#!/bin/bash

# Quick test of just a few files
cd /home/baste/tasker/test_cases

echo "=== QUICK VERIFICATION TEST ==="

for test in simple_test.txt comprehensive_retry_validation_test.txt first_test_simple.txt; do
    echo "Testing: $test"
    if timeout 30s ../tasker.py "$test" -r -d > /dev/null 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi
    
    echo "  Exit code: $exit_code"
    
    if [ "$test" = "comprehensive_retry_validation_test.txt" ]; then
        if [ $exit_code -eq 20 ]; then
            echo "  ✅ PASS: Expected validation failure"
        else
            echo "  ❌ FAIL: Expected 20, got $exit_code"
        fi
    else
        if [ $exit_code -eq 0 ] || [ $exit_code -eq 1 ] || [ $exit_code -eq 14 ]; then
            echo "  ✅ PASS: Functional execution"
        else
            echo "  ❌ FAIL: Unexpected exit code $exit_code"
        fi
    fi
    echo
done