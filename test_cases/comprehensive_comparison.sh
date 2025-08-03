#!/bin/bash

# Comprehensive comparison between tasker.py and tasker_orig.py
# Tests all *.txt files in test_cases directory

cd /home/baste/tasker

# State reset function to ensure clean test environment
reset_state() {
    rm -f ../.toggle_value ../.my_counter
}

echo "=== COMPREHENSIVE COMPARISON: tasker.py vs tasker_orig.py ==="
echo "Testing all *.txt files in test_cases/"
echo

# Counter variables
total_tests=0
identical_results=0
different_results=0
both_failed=0
only_orig_worked=0
only_tasker_worked=0

# Get all test files
test_files=$(find test_cases -name "*.txt" | sort)

for test_file in $test_files; do
    total_tests=$((total_tests + 1))
    test_name=$(basename "$test_file")
    
    echo "=== Test $total_tests: $test_name ==="
    
    # Reset state before each test
    reset_state
    
    # Run tasker_orig.py (using compatible parameters)
    echo -n "Running tasker_orig.py... "
    ./tasker_orig.py "$test_file" -r > /tmp/orig_output.txt 2>&1
    orig_exit=$?
    echo "Exit: $orig_exit"
    
    # Reset state again
    reset_state
    
    # Run tasker.py (using compatible parameters)
    echo -n "Running tasker.py... "
    ./tasker.py "$test_file" -r > /tmp/tasker_output.txt 2>&1
    tasker_exit=$?
    echo "Exit: $tasker_exit"
    
    # Compare results
    if [ $orig_exit -eq $tasker_exit ]; then
        if [ $orig_exit -eq 0 ]; then
            echo "✅ BOTH SUCCEEDED (exit $orig_exit)"
            identical_results=$((identical_results + 1))
        else
            echo "✅ BOTH FAILED IDENTICALLY (exit $orig_exit)"
            both_failed=$((both_failed + 1))
        fi
    else
        echo "⚠️  DIFFERENT EXIT CODES: orig=$orig_exit, tasker=$tasker_exit"
        different_results=$((different_results + 1))
        
        # Check which one worked
        if [ $orig_exit -eq 0 ] && [ $tasker_exit -ne 0 ]; then
            echo "   ❌ Only original worked"
            only_orig_worked=$((only_orig_worked + 1))
        elif [ $orig_exit -ne 0 ] && [ $tasker_exit -eq 0 ]; then
            echo "   ✅ Only refactored worked"
            only_tasker_worked=$((only_tasker_worked + 1))
        fi
        
        # Show output differences for failed cases
        echo "   --- Original output (last 3 lines) ---"
        tail -n 3 /tmp/orig_output.txt
        echo "   --- Refactored output (last 3 lines) ---"
        tail -n 3 /tmp/tasker_output.txt
    fi
    
    echo
done

# Summary
echo "=========================================="
echo "COMPREHENSIVE COMPARISON SUMMARY"
echo "=========================================="
echo "Total tests: $total_tests"
echo "Identical results: $identical_results"
echo "Both failed identically: $both_failed"
echo "Different exit codes: $different_results"
echo "  - Only original worked: $only_orig_worked"
echo "  - Only refactored worked: $only_tasker_worked"
echo
echo "Success rate comparison:"
echo "  - Identical behavior: $((identical_results + both_failed))/$total_tests tests"
echo "  - Functional compatibility: $(((total_tests - only_orig_worked)))/$total_tests tests"

# Cleanup
rm -f /tmp/orig_output.txt /tmp/tasker_output.txt