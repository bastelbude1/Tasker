#!/bin/bash
# Test script to verify --show-plan displays routing correctly

echo "Testing --show-plan routing display..."
echo "======================================"

# Test file
TEST_FILE="test_cases/functional/test_show_plan_routing_verification.txt"

# Run show-plan and capture output (both stdout and stderr)
echo "n" | python3 tasker.py "$TEST_FILE" --show-plan > /tmp/plan_output.txt 2>&1

# Function to check if a pattern exists in the output
check_routing() {
    task_id=$1
    expected_pattern=$2
    description=$3

    if grep -q "Task $task_id:" /tmp/plan_output.txt; then
        if grep -A 5 "Task $task_id:" /tmp/plan_output.txt | grep -q "$expected_pattern"; then
            echo "✅ Task $task_id: $description"
            return 0
        else
            echo "❌ Task $task_id: $description NOT FOUND"
            echo "   Expected pattern: $expected_pattern"
            grep -A 5 "Task $task_id:" /tmp/plan_output.txt | sed 's/^/   /'
            return 1
        fi
    else
        echo "❌ Task $task_id not found in output"
        return 1
    fi
}

# Verification checks
echo ""
echo "Verifying routing patterns:"
echo "----------------------------"

# Task 0: No routing (should have no routing lines)
if grep -A 3 "Task 0:" /tmp/plan_output.txt | grep -q "->"; then
    echo "❌ Task 0: Should have no routing, but found some"
else
    echo "✅ Task 0: No routing (as expected)"
fi

# Task 1: on_success only
check_routing 1 "on success: task 10" "on_success=10"
check_routing 1 "default: continue to task 2" "default continuation"

# Task 2: on_failure only
check_routing 2 "on failure: task 20" "on_failure=20"
check_routing 2 "default: continue to task 3" "default continuation"

# Task 3: Both on_success and on_failure
check_routing 3 "on success: task 30" "on_success=30"
check_routing 3 "on failure: task 40" "on_failure=40"
check_routing 3 "default: continue to task 4" "default continuation"

# Task 4: next=never
check_routing 4 "default: stop execution" "next=never"

# Task 5: next=always
check_routing 5 "default: always continue" "next=always"

# Task 6: next=loop
check_routing 6 "default: loop back to task 6" "next=loop"

# Task 7: on_success with different target
check_routing 7 "on success: task 50" "on_success=50"
check_routing 7 "default: continue to task 8" "default continuation"

# Task 8: on_failure with different target
check_routing 8 "on failure: task 60" "on_failure=60"
check_routing 8 "default: continue to task 9" "default continuation"

# Task 9: Both routing without next
check_routing 9 "on success: task 70" "on_success=70"
check_routing 9 "on failure: task 80" "on_failure=80"
check_routing 9 "default: continue to task 10" "default continuation"

echo ""
echo "======================================"
echo "Test completed. Check results above."
echo ""

# Show a summary of the actual plan output for reference
echo "Full execution plan output:"
echo "---------------------------"
sed -n '/=== EXECUTION PLAN ===/,/====/p' /tmp/plan_output.txt