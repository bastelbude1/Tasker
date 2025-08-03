#!/bin/bash

# Quick test of the improved verification approach
cd /home/baste/tasker/test_cases

echo "=== QUICK TEST - IMPROVED VERIFICATION ==="

reset_state() {
    rm -f ../.toggle_value ../.my_counter
    rm -f /tmp/task*_attempt /tmp/task*_counter 2>/dev/null || true
}

test_count=0
pass_count=0

for test in simple_test.txt comprehensive_retry_validation_test.txt first_test_simple.txt; do
    echo "Testing: $test"
    test_count=$((test_count + 1))
    
    # Test with tasker.py (no debug)
    reset_state
    if timeout 30s ../tasker.py "$test" -r > /dev/null 2>&1; then
        tasker_exit=0
    else
        tasker_exit=$?
    fi
    
    # Test with tasker_orig.py (no debug)  
    reset_state
    if timeout 30s ../tasker_orig.py "$test" -r > /dev/null 2>&1; then
        orig_exit=0
    else
        orig_exit=$?
    fi
    
    echo "  tasker.py exit: $tasker_exit"
    echo "  tasker_orig.py exit: $orig_exit"
    
    # Compare (allowing for improved exit codes)
    if [ $tasker_exit -eq $orig_exit ]; then
        echo "  ✅ PASS: Exit codes match"
        pass_count=$((pass_count + 1))
    elif [ $orig_exit -eq 1 ] && [ $tasker_exit -eq 20 ]; then
        echo "  ✅ PASS: Improved exit code (validation: $orig_exit → $tasker_exit)"
        pass_count=$((pass_count + 1))
    elif [ $orig_exit -eq 1 ] && [ $tasker_exit -eq 14 ]; then
        echo "  ✅ PASS: Improved exit code (conditional: $orig_exit → $tasker_exit)"
        pass_count=$((pass_count + 1))
    else
        echo "  ❌ FAIL: Different exit codes"
    fi
    echo
done

echo "Results: $pass_count/$test_count passed"