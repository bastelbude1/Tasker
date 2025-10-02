#!/bin/bash
# SAFE parallel TASKER execution with environment coordination

echo "=== SAFE NESTED PARALLELISM TEST ==="
echo "Starting 10 TASKER instances with thread pool coordination"

export PATH="../test_scripts:$PATH"
export TASKER_PARALLEL_INSTANCES=10  # Inform TASKER about parallel execution

# Start 10 TASKER instances in background
for i in {1..10}; do
    echo "Starting TASKER instance $i (aware of 10 parallel instances)"
    ../tasker.py nested_parallelism_test.txt -r --skip-host-validation > safe_nested_$i.log 2>&1 &
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

# Cleanup
rm -f safe_nested_*.log