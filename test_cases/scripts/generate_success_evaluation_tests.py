#!/usr/bin/env python3
"""
Generate comprehensive test cases for multi-task success evaluation conditions.

This script generates test files for both parallel and conditional blocks,
covering all success evaluation conditions:
- min_success=N
- max_failed=N
- all_success
- any_success
- majority_success

Each condition is tested with multiple scenarios (met, not met, edge cases).
"""

import os
import json
from typing import Dict, List, Any

# Output directory for generated tests
OUTPUT_DIR = "../functional"

# Test case templates
PARALLEL_TEMPLATE = """# TEST_METADATA: {metadata}
# Test parallel execution with {condition} condition
# {description}

task=0
hostname=localhost
command=/usr/bin/echo
arguments={intro_message}
exec=local

# Parallel block with {condition} condition
# Section 10.1: Multi-Task Success Evaluation Block (next)
# If condition met → continue to task 2 (sequential)
# If condition not met → workflow ends
task=1
type=parallel
tasks={subtask_ids}
max_parallel={max_parallel}
next={next_condition}

{subtask_definitions}

# Task 2: Executed only if {condition} condition is met
# If condition not met, workflow ends after task 1
task=2
hostname=localhost
command=/usr/bin/echo
arguments=SUCCESS: {success_message}
exec=local
return=0
"""

CONDITIONAL_TEMPLATE = """# TEST_METADATA: {metadata}
# Test conditional execution with {condition} condition
# {description}

task=0
hostname=localhost
command=/usr/bin/echo
arguments={condition_value}
exec=local

# Conditional block with {condition} condition
# Section 10.1: Multi-Task Success Evaluation Block (next)
# If condition met → continue to task 2 (sequential)
# If condition not met → workflow ends
task=1
type=conditional
condition=@0_stdout@={condition_value}
if_true_tasks={subtask_ids}
if_false_tasks=20
next={next_condition}

{subtask_definitions}

# False branch placeholder (not executed in this test)
task=20
hostname=localhost
command=/usr/bin/echo
arguments=False branch - should not execute
exec=local

# Task 2: Executed only if {condition} condition is met
# If condition not met, workflow ends after task 1
task=2
hostname=localhost
command=/usr/bin/echo
arguments=SUCCESS: {success_message}
exec=local
return=0
"""

SUBTASK_TEMPLATE = """# Subtask {task_id}: {status} ({comment})
task={task_id}
hostname=localhost
command=success_pattern.sh
arguments={task_id} "{success_pattern}"
exec=local
"""


def generate_subtasks(task_ids: List[int], success_pattern: str) -> str:
    """Generate subtask definitions."""
    subtasks = []
    success_list = success_pattern.split(',') if success_pattern not in ['ALL', 'NONE'] else []

    for task_id in task_ids:
        if success_pattern == 'ALL' or str(task_id) in success_list:
            status = "SUCCESS"
            comment = "in success pattern"
        else:
            status = "FAILED"
            comment = "not in success pattern"

        subtasks.append(SUBTASK_TEMPLATE.format(
            task_id=task_id,
            status=status,
            comment=comment,
            success_pattern=success_pattern
        ))

    return '\n'.join(subtasks)


def create_test_case(
    test_name: str,
    block_type: str,  # 'parallel' or 'conditional'
    condition: str,
    next_condition: str,
    num_tasks: int,
    success_pattern: str,
    description: str,
    expected_success_count: int,
    expected_failed_count: int,
    expected_condition_met: bool,
    intro_message: str = None,
    success_message: str = None,
    failure_message: str = None
) -> Dict[str, Any]:
    """Create a test case configuration."""

    task_ids = list(range(10, 10 + num_tasks))
    subtask_ids = ','.join(str(tid) for tid in task_ids)
    expected_subtasks = [f"1-{tid}" for tid in task_ids]

    # Default messages
    if not intro_message:
        intro_message = f"Starting {condition} test - {description}"
    if not success_message:
        success_message = f"{condition} condition met - {expected_success_count}/{num_tasks} tasks succeeded"
    if not failure_message:
        failure_message = f"{condition} condition not met"

    # Expected execution path (Section 10.1 behavior)
    # Condition MET → [0, 1, 2] (continues to task 2, exit 0)
    # Condition NOT MET → [0, 1] (workflow ends after task 1, exit 10)
    # Exit code 10 = TASK_FAILED (condition failed due to task execution results)
    expected_final_task = 2 if expected_condition_met else 1
    expected_exit_code = 0 if expected_condition_met else 10
    expected_path = [0, 1, 2] if expected_condition_met else [0, 1]

    # Build metadata
    metadata = {
        "description": f"{block_type.capitalize()} {description}",
        "test_type": "positive",
        "expected_exit_code": expected_exit_code,
        "expected_success": expected_condition_met,
        "skip_host_validation": True,
        "expected_execution_path": expected_path,
        "expected_subtasks": expected_subtasks,
        "expected_success_count": expected_success_count,
        "expected_failed_count": expected_failed_count,
        "expected_condition_met": expected_condition_met,
        "expected_final_task": expected_final_task,
        "success_condition": next_condition
    }

    # Generate subtasks
    subtask_definitions = generate_subtasks(task_ids, success_pattern)

    # Choose template
    template = PARALLEL_TEMPLATE if block_type == 'parallel' else CONDITIONAL_TEMPLATE

    # Format template
    content = template.format(
        metadata=json.dumps(metadata),
        condition=condition,
        description=description,
        intro_message=intro_message,
        next_condition=next_condition,
        subtask_ids=subtask_ids,
        max_parallel=num_tasks,
        subtask_definitions=subtask_definitions,
        success_message=success_message,
        condition_value="PRODUCTION" if block_type == 'conditional' else ""
    )

    return {
        'filename': f"{test_name}.txt",
        'content': content,
        'metadata': metadata
    }


def generate_all_tests():
    """Generate all test cases."""
    test_cases = []

    # ========================================
    # PARALLEL: min_success=N (5 tests)
    # ========================================

    # 1. min_success=3 met exactly (3/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_min_success_met",
        block_type="parallel",
        condition="min_success=3",
        next_condition="min_success=3",
        num_tasks=5,
        success_pattern="10,11,12",
        description="min_success=3 with exactly 3 successes - condition met",
        expected_success_count=3,
        expected_failed_count=2,
        expected_condition_met=True
    ))

    # 2. min_success=3 exceeded (4/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_min_success_exceeded",
        block_type="parallel",
        condition="min_success=3",
        next_condition="min_success=3",
        num_tasks=5,
        success_pattern="10,11,12,13",
        description="min_success=3 with 4 successes - condition exceeded",
        expected_success_count=4,
        expected_failed_count=1,
        expected_condition_met=True
    ))

    # 3. min_success=3 not met (2/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_min_success_not_met",
        block_type="parallel",
        condition="min_success=3",
        next_condition="min_success=3",
        num_tasks=5,
        success_pattern="10,11",
        description="min_success=3 with only 2 successes - condition not met",
        expected_success_count=2,
        expected_failed_count=3,
        expected_condition_met=False
    ))

    # 4. min_success=5 all succeed (5/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_min_success_all_succeed",
        block_type="parallel",
        condition="min_success=5",
        next_condition="min_success=5",
        num_tasks=5,
        success_pattern="ALL",
        description="min_success=5 with all 5 successes - condition met",
        expected_success_count=5,
        expected_failed_count=0,
        expected_condition_met=True
    ))

    # 5. min_success=1 edge case (1/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_min_success_edge_one",
        block_type="parallel",
        condition="min_success=1",
        next_condition="min_success=1",
        num_tasks=5,
        success_pattern="10",
        description="min_success=1 with 1 success - edge case met",
        expected_success_count=1,
        expected_failed_count=4,
        expected_condition_met=True
    ))

    # ========================================
    # PARALLEL: max_failed=N (5 tests)
    # ========================================

    # 1. max_failed=2 met exactly (2/5 fail)
    test_cases.append(create_test_case(
        test_name="test_parallel_max_failed_met",
        block_type="parallel",
        condition="max_failed=2",
        next_condition="max_failed=2",
        num_tasks=5,
        success_pattern="10,11,12",
        description="max_failed=2 with exactly 2 failures - condition met",
        expected_success_count=3,
        expected_failed_count=2,
        expected_condition_met=True
    ))

    # 2. max_failed=2 under limit (1/5 fail)
    test_cases.append(create_test_case(
        test_name="test_parallel_max_failed_under",
        block_type="parallel",
        condition="max_failed=2",
        next_condition="max_failed=2",
        num_tasks=5,
        success_pattern="10,11,12,13",
        description="max_failed=2 with only 1 failure - under limit",
        expected_success_count=4,
        expected_failed_count=1,
        expected_condition_met=True
    ))

    # 3. max_failed=2 exceeded (3/5 fail)
    test_cases.append(create_test_case(
        test_name="test_parallel_max_failed_exceeded",
        block_type="parallel",
        condition="max_failed=2",
        next_condition="max_failed=2",
        num_tasks=5,
        success_pattern="10,11",
        description="max_failed=2 with 3 failures - condition exceeded",
        expected_success_count=2,
        expected_failed_count=3,
        expected_condition_met=False
    ))

    # 4. max_failed=0 none failed (0/5 fail)
    test_cases.append(create_test_case(
        test_name="test_parallel_max_failed_none",
        block_type="parallel",
        condition="max_failed=0",
        next_condition="max_failed=0",
        num_tasks=5,
        success_pattern="ALL",
        description="max_failed=0 with no failures - all succeed",
        expected_success_count=5,
        expected_failed_count=0,
        expected_condition_met=True
    ))

    # 5. max_failed=4 all but one (4/5 fail)
    test_cases.append(create_test_case(
        test_name="test_parallel_max_failed_all_but_one",
        block_type="parallel",
        condition="max_failed=4",
        next_condition="max_failed=4",
        num_tasks=5,
        success_pattern="10",
        description="max_failed=4 with 4 failures - edge case met",
        expected_success_count=1,
        expected_failed_count=4,
        expected_condition_met=True
    ))

    # ========================================
    # PARALLEL: all_success (3 tests)
    # ========================================

    # 1. all_success met (3/3 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_all_success_met",
        block_type="parallel",
        condition="all_success",
        next_condition="all_success",
        num_tasks=3,
        success_pattern="ALL",
        description="all_success with all 3 tasks succeeding - condition met",
        expected_success_count=3,
        expected_failed_count=0,
        expected_condition_met=True
    ))

    # 2. all_success not met (2/3 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_all_success_not_met",
        block_type="parallel",
        condition="all_success",
        next_condition="all_success",
        num_tasks=3,
        success_pattern="10,11",
        description="all_success with 1 failure - condition not met",
        expected_success_count=2,
        expected_failed_count=1,
        expected_condition_met=False
    ))

    # 3. all_success single task (1/1 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_all_success_single",
        block_type="parallel",
        condition="all_success",
        next_condition="all_success",
        num_tasks=1,
        success_pattern="ALL",
        description="all_success with single task succeeding - edge case",
        expected_success_count=1,
        expected_failed_count=0,
        expected_condition_met=True
    ))

    # ========================================
    # PARALLEL: any_success (3 tests)
    # ========================================

    # 1. any_success one (1/3 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_any_success_one",
        block_type="parallel",
        condition="any_success",
        next_condition="any_success",
        num_tasks=3,
        success_pattern="10",
        description="any_success with 1 task succeeding - condition met",
        expected_success_count=1,
        expected_failed_count=2,
        expected_condition_met=True
    ))

    # 2. any_success all (3/3 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_any_success_all",
        block_type="parallel",
        condition="any_success",
        next_condition="any_success",
        num_tasks=3,
        success_pattern="ALL",
        description="any_success with all tasks succeeding - condition met",
        expected_success_count=3,
        expected_failed_count=0,
        expected_condition_met=True
    ))

    # 3. any_success none (0/3 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_any_success_none",
        block_type="parallel",
        condition="any_success",
        next_condition="any_success",
        num_tasks=3,
        success_pattern="NONE",
        description="any_success with no tasks succeeding - condition not met",
        expected_success_count=0,
        expected_failed_count=3,
        expected_condition_met=False
    ))

    # ========================================
    # PARALLEL: majority_success (5 tests)
    # ========================================

    # 1. majority_success 60% (3/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_majority_success_met_60",
        block_type="parallel",
        condition="majority_success",
        next_condition="majority_success",
        num_tasks=5,
        success_pattern="10,11,12",
        description="majority_success with 3/5 (60%) - condition met",
        expected_success_count=3,
        expected_failed_count=2,
        expected_condition_met=True
    ))

    # 2. majority_success 75% (3/4 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_majority_success_met_75",
        block_type="parallel",
        condition="majority_success",
        next_condition="majority_success",
        num_tasks=4,
        success_pattern="10,11,12",
        description="majority_success with 3/4 (75%) - condition met",
        expected_success_count=3,
        expected_failed_count=1,
        expected_condition_met=True
    ))

    # 3. majority_success 40% (2/5 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_majority_success_not_met_40",
        block_type="parallel",
        condition="majority_success",
        next_condition="majority_success",
        num_tasks=5,
        success_pattern="10,11",
        description="majority_success with 2/5 (40%) - condition not met",
        expected_success_count=2,
        expected_failed_count=3,
        expected_condition_met=False
    ))

    # 4. majority_success tie 50% (2/4 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_majority_success_tie_50",
        block_type="parallel",
        condition="majority_success",
        next_condition="majority_success",
        num_tasks=4,
        success_pattern="10,11",
        description="majority_success with 2/4 (50%) tie - condition not met",
        expected_success_count=2,
        expected_failed_count=2,
        expected_condition_met=False
    ))

    # 5. majority_success all (3/3 succeed)
    test_cases.append(create_test_case(
        test_name="test_parallel_majority_success_all",
        block_type="parallel",
        condition="majority_success",
        next_condition="majority_success",
        num_tasks=3,
        success_pattern="ALL",
        description="majority_success with 3/3 (100%) - condition met",
        expected_success_count=3,
        expected_failed_count=0,
        expected_condition_met=True
    ))

    # ========================================
    # NOW REPEAT ALL TESTS FOR CONDITIONAL
    # ========================================

    # Create conditional versions of all parallel tests
    conditional_tests = []
    for test in test_cases:
        # Clone the test but change to conditional
        conditional_name = test['filename'].replace('parallel', 'conditional')
        conditional_test = create_test_case(
            test_name=conditional_name.replace('.txt', ''),
            block_type='conditional',
            condition=test['metadata']['success_condition'],
            next_condition=test['metadata']['success_condition'],
            num_tasks=len(test['metadata']['expected_subtasks']),
            success_pattern=','.join([str(i) for i in range(10, 10 + test['metadata']['expected_success_count'])])
                           if test['metadata']['expected_success_count'] > 0 and test['metadata']['expected_success_count'] < len(test['metadata']['expected_subtasks'])
                           else ('ALL' if test['metadata']['expected_success_count'] == len(test['metadata']['expected_subtasks']) else 'NONE'),
            description=test['metadata']['description'].replace('Parallel', 'Conditional'),
            expected_success_count=test['metadata']['expected_success_count'],
            expected_failed_count=test['metadata']['expected_failed_count'],
            expected_condition_met=test['metadata']['expected_condition_met']
        )
        conditional_tests.append(conditional_test)

    # Combine all tests
    all_tests = test_cases + conditional_tests

    return all_tests


def main():
    """Main execution."""
    print("=" * 60)
    print("TASKER Multi-Task Success Evaluation Test Generator")
    print("=" * 60)

    # Generate all test cases
    test_cases = generate_all_tests()

    print(f"\nGenerating {len(test_cases)} test cases...")
    print(f"Output directory: {OUTPUT_DIR}")

    # Create output directory if needed
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Write test files
    created_count = 0
    for test in test_cases:
        filepath = os.path.join(OUTPUT_DIR, test['filename'])
        with open(filepath, 'w') as f:
            f.write(test['content'])
        created_count += 1
        print(f"  ✓ Created: {test['filename']}")

    print(f"\n✅ Successfully created {created_count} test files!")
    print("\nTest breakdown:")
    print("  - Parallel tests: 26")
    print("  - Conditional tests: 26")
    print("\nConditions covered:")
    print("  - min_success=N: 10 tests (5 parallel + 5 conditional)")
    print("  - max_failed=N: 10 tests (5 parallel + 5 conditional)")
    print("  - all_success: 6 tests (3 parallel + 3 conditional)")
    print("  - any_success: 6 tests (3 parallel + 3 conditional)")
    print("  - majority_success: 10 tests (5 parallel + 5 conditional)")
    print(f"\n{'=' * 60}")


if __name__ == '__main__':
    main()
