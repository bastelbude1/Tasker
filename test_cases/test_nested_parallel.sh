#!/bin/bash
# WARNING: This test demonstrates the nested parallelism problem
# Running too many instances could overwhelm the system

echo "=== NESTED PARALLELISM TEST ==="
echo "Starting 10 TASKER instances in parallel, each with parallel tasks"
echo "Without protection, this could create 10 * 50 = 500 threads!"

export PATH="../test_scripts:$PATH"

# Start 10 TASKER instances in background
for i in {1..10}; do
    echo "Starting TASKER instance $i"
    ../tasker.py nested_parallelism_test.txt -r --skip-host-validation > nested_$i.log 2>&1 &
done

echo "Waiting for all instances to complete..."
wait

echo "=== RESULTS ==="
for i in {1..10}; do
    if grep -q "SUCCESS: Task execution completed" nested_$i.log 2>/dev/null; then
        echo "Instance $i: SUCCESS"
    else
        echo "Instance $i: FAILED or still running"
    fi
done

# Check system thread count during execution
echo ""
echo "Checking for thread capping messages:"
grep "Capping thread pool" nested_*.log 2>/dev/null | head -5 || echo "No capping messages found"

# Cleanup
rm -f nested_*.log