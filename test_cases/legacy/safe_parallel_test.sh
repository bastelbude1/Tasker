#!/bin/bash
# SAFE parallel TASKER execution with environment coordination

echo "=== SAFE NESTED PARALLELISM TEST ==="
echo "Starting 10 TASKER instances with thread pool coordination"

export PATH="../bin:$PATH"
export TASKER_PARALLEL_INSTANCES=10  # Inform TASKER about parallel execution

# Start 10 TASKER instances in background (with debug to see capping messages)
for i in {1..10}; do
    echo "Starting TASKER instance $i (aware of 10 parallel instances)"
    ../tasker.py nested_parallelism_test.txt -r --skip-host-validation -d > safe_nested_$i.log 2>&1 &
done

echo "Waiting for all instances to complete..."
wait

echo ""
echo "=== RESULTS ==="
success_count=0
for i in {1..10}; do
    if grep -q "SUCCESS: Task execution completed" safe_nested_$i.log 2>/dev/null; then
        echo "Instance $i: SUCCESS"
        ((success_count++))
    else
        echo "Instance $i: FAILED"
    fi
done

echo ""
echo "Summary: $success_count/10 instances succeeded"

echo ""
echo "=== THREAD CAPPING (showing first 3) ==="
grep "Capping thread pool" safe_nested_*.log 2>/dev/null | head -3

# Validation checks for test success
echo ""
echo "=== VALIDATION ==="

# Check 1: All instances must succeed
if [ $success_count -lt 10 ]; then
    echo "❌ FAILURE: Only $success_count/10 instances succeeded (expected 10)"
    echo "Test FAILED - Not all instances completed successfully"
    # Cleanup before exit
    rm -f safe_nested_*.log
    exit 1
fi
echo "✅ All 10 instances succeeded"

# Check 2: Thread capping must be active (at least one instance should show capping)
if ! grep -q "Capping thread pool" safe_nested_*.log 2>/dev/null; then
    echo "❌ FAILURE: No 'Capping thread pool' messages found"
    echo "Test FAILED - Thread pool capping not detected (TASKER_PARALLEL_INSTANCES may not be working)"
    # Cleanup before exit
    rm -f safe_nested_*.log
    exit 1
fi
echo "✅ Thread pool capping detected"

echo ""
echo "=== TEST PASSED ==="
echo "All instances succeeded and thread pool capping is working correctly"

# Cleanup
rm -f safe_nested_*.log

# Exit with success only when both conditions are met
exit 0