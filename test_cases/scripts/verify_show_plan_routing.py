#!/usr/bin/env python3
"""
Verify that --show-plan correctly displays routing as defined in task files.
"""

import subprocess
import re
import sys
import json

def parse_task_file(filepath):
    """Parse a task file and extract routing information."""
    tasks = {}
    current_task = None

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key == 'task':
                    current_task = int(value)
                    tasks[current_task] = {
                        'hostname': None,
                        'command': None,
                        'return': None,
                        'on_success': None,
                        'on_failure': None,
                        'next': None,
                        'type': 'normal',
                        'loop': None
                    }
                elif current_task is not None:
                    if key in tasks[current_task]:
                        tasks[current_task][key] = value

    return tasks

def extract_plan_output(filepath):
    """Run --show-plan and extract the routing information."""
    cmd = ['python3', 'tasker.py', filepath, '--show-plan', '--validate-only']
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse the execution plan output
    plan_tasks = {}
    current_task = None
    in_plan = False

    for line in result.stdout.split('\n'):
        if '=== EXECUTION PLAN ===' in line:
            in_plan = True
            continue
        if '====' in line and in_plan:
            break
        if not in_plan:
            continue

        # Match task line
        task_match = re.match(r'\s*Task (\d+):\s*(.*)', line)
        if task_match:
            current_task = int(task_match.group(1))
            plan_tasks[current_task] = {
                'description': task_match.group(2),
                'on_success': None,
                'on_failure': None,
                'default': None
            }
            continue

        # Match routing lines
        if current_task is not None:
            success_match = re.match(r'\s*-> on success:\s*task\s*(\d+)', line)
            failure_match = re.match(r'\s*-> on failure:\s*task\s*(\d+)', line)
            default_match = re.match(r'\s*-> default:\s*(.*)', line)

            if success_match:
                plan_tasks[current_task]['on_success'] = int(success_match.group(1))
            elif failure_match:
                plan_tasks[current_task]['on_failure'] = int(failure_match.group(1))
            elif default_match:
                plan_tasks[current_task]['default'] = default_match.group(1)

    return plan_tasks

def verify_routing(task_def, plan_output):
    """Verify that the plan output matches the task definition."""
    errors = []

    # Check on_success
    if task_def['on_success']:
        expected = int(task_def['on_success'])
        actual = plan_output.get('on_success')
        if actual != expected:
            errors.append(f"on_success mismatch: expected {expected}, got {actual}")

    # Check on_failure
    if task_def['on_failure']:
        expected = int(task_def['on_failure'])
        actual = plan_output.get('on_failure')
        if actual != expected:
            errors.append(f"on_failure mismatch: expected {expected}, got {actual}")

    # Check default routing
    if task_def['next'] == 'never':
        if plan_output.get('default') != 'stop execution':
            errors.append(f"default mismatch: expected 'stop execution', got '{plan_output.get('default')}'")
    elif task_def['next'] == 'always':
        if plan_output.get('default') != 'always continue to next task':
            errors.append(f"default mismatch: expected 'always continue', got '{plan_output.get('default')}'")
    elif task_def['next'] == 'loop':
        expected_msg = f"loop back to task {task_id}"
        if plan_output.get('default') != expected_msg:
            errors.append(f"default mismatch: expected '{expected_msg}', got '{plan_output.get('default')}'")

    return errors

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 verify_show_plan_routing.py <task_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    print(f"Verifying --show-plan routing for: {filepath}")
    print("-" * 60)

    # Parse task file
    tasks = parse_task_file(filepath)

    # Get plan output
    plan = extract_plan_output(filepath)

    # Verify each task
    all_passed = True
    for task_id, task_def in sorted(tasks.items()):
        if task_id not in plan:
            print(f"Task {task_id}: NOT IN PLAN OUTPUT")
            all_passed = False
            continue

        plan_output = plan[task_id]
        errors = verify_routing(task_def, plan_output)

        if errors:
            print(f"Task {task_id}: FAILED")
            for error in errors:
                print(f"  - {error}")
            all_passed = False
        else:
            # Only print details for tasks with routing
            if task_def['on_success'] or task_def['on_failure'] or task_def['next']:
                print(f"Task {task_id}: PASSED")
                if task_def['on_success']:
                    print(f"  ✓ on_success: {task_def['on_success']}")
                if task_def['on_failure']:
                    print(f"  ✓ on_failure: {task_def['on_failure']}")
                if task_def['next']:
                    print(f"  ✓ next: {task_def['next']}")

    print("-" * 60)
    if all_passed:
        print("✅ ALL ROUTING VERIFIED SUCCESSFULLY")
        sys.exit(0)
    else:
        print("❌ ROUTING VERIFICATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    # Need to set task_id for loop verification
    global task_id
    task_id = None
    main()