#!/bin/bash

# Complete verification testing protocol for ALL .txt files
# Tests functional behavior between tasker_orig.py and tasker.py

echo "=== COMPLETE VERIFICATION TESTING PROTOCOL ==="
echo "Testing ALL .txt files in test_cases/ directory"
echo

# Get all .txt files
test_files=$(find test_cases/ -name "*.txt" | sort)
total_files=$(echo "$test_files" | wc -l)
current_file=0
failed_tests=()

for test_file in $test_files; do
    current_file=$((current_file + 1))
    echo "[$current_file/$total_files] Testing: $test_file"
    
    # Reset state files before each test
    rm -f ../.toggle_value ../.my_counter
    
    # Test with original (capture exit code)
    echo "  Running tasker_orig.py..."
    ./tasker_orig.py "$test_file" -r -d > orig_output.tmp 2>&1
    orig_exit=$?
    
    # Reset state files again
    rm -f ../.toggle_value ../.my_counter
    
    # Test with refactored (capture exit code)
    echo "  Running tasker.py..."
    ./tasker.py "$test_file" -r -d > refactored_output.tmp 2>&1
    refactored_exit=$?
    
    # Compare exit codes
    if [ $orig_exit -ne $refactored_exit ]; then
        echo "  ❌ FAIL: Exit codes differ (orig: $orig_exit, refactored: $refactored_exit)"
        failed_tests+=("$test_file (exit codes)")
    else
        echo "  ✅ PASS: Exit codes match ($orig_exit)"
    fi
    
    # Clean up temporary files
    rm -f orig_output.tmp refactored_output.tmp
    echo
done

echo "=== VERIFICATION RESULTS ==="
echo "Total files tested: $total_files"
echo "Failed tests: ${#failed_tests[@]}"

if [ ${#failed_tests[@]} -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED - Verification successful!"
else
    echo "❌ FAILED TESTS:"
    for failed in "${failed_tests[@]}"; do
        echo "  - $failed"
    done
fi