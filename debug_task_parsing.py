#!/usr/bin/env python3
"""
Debug script to trace task parsing issues.
"""

import os
import sys

# Add the current directory to the path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_parse_task_file(task_file):
    """Debug version of task file parsing to see what's happening."""
    print(f"=== Debugging task file: {task_file} ===")

    if not os.path.exists(task_file):
        print(f"ERROR: Task file '{task_file}' not found.")
        return

    with open(task_file, 'r') as f:
        lines = f.readlines()

    print(f"Total lines in file: {len(lines)}")

    # Show file contents
    print("\n=== File Contents ===")
    for i, line in enumerate(lines, 1):
        print(f"{i:2d}: '{line.rstrip()}'")

    # PHASE 1: Collect global variables
    print("\n=== Phase 1: Global Variables ===")
    global_vars = {}
    global_count = 0

    known_task_fields = [
        'hostname', 'command', 'arguments', 'next', 'stdout_split', 'stderr_split',
        'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure',
        'on_success', 'success', 'condition', 'exec', 'timeout', 'return',
        'type', 'max_parallel', 'tasks', 'retry_failed', 'retry_count', 'retry_delay',
        'if_true_tasks', 'if_false_tasks'
    ]

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            print(f"  Line {line_num}: Skipped (empty/comment)")
            continue

        # Check if this is a global variable definition
        if '=' in line and not line.startswith('task='):
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if key not in known_task_fields:
                # This is a global variable
                global_vars[key] = value
                global_count += 1
                print(f"  Line {line_num}: Global variable: {key} = {value}")
            else:
                print(f"  Line {line_num}: Known task field, not global: {key} = {value}")
        else:
            print(f"  Line {line_num}: Not a global variable definition: '{line}'")

    print(f"\nFound {global_count} global variables")

    # PHASE 2: Parse tasks
    print("\n=== Phase 2: Task Parsing ===")
    tasks = {}
    current_task = None

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Parse key=value pairs
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            print(f"  Line {line_num}: Parsing {key} = {value}")

            # Check if this is a new task definition
            if key == 'task':
                # Save the previous task if it exists
                if current_task is not None and 'task' in current_task:
                    task_id = int(current_task['task'])
                    if 'arguments' not in current_task:
                        current_task['arguments'] = ''
                    tasks[task_id] = current_task
                    print(f"    Saved previous task {task_id}: {current_task}")

                # Start a new task
                current_task = {'task': value}
                print(f"    Started new task: {value}")
            else:
                # Add to current task
                if current_task is not None:
                    current_task[key] = value
                    print(f"    Added to current task: {key} = {value}")
                else:
                    print(f"    ERROR: No current task to add to!")
        else:
            print(f"  Line {line_num}: No '=' found in line: '{line}'")

    # Add the last task if it exists
    if current_task is not None and 'task' in current_task:
        task_id = int(current_task['task'])
        if 'arguments' not in current_task:
            current_task['arguments'] = ''
        tasks[task_id] = current_task
        print(f"  Saved final task {task_id}: {current_task}")

    print(f"\nParsed {len(tasks)} tasks total")
    for task_id, task in tasks.items():
        print(f"  Task {task_id}: {task}")

    # PHASE 3: Validate tasks
    print("\n=== Phase 3: Task Validation ===")
    valid_task_count = 0

    for task_id, task in tasks.items():
        print(f"Validating task {task_id}: {task}")

        # Different validation for parallel and conditional tasks
        if task.get('type') == 'parallel':
            if 'tasks' not in task:
                print(f"  INVALID: Parallel task {task_id} is missing required 'tasks' field.")
                continue
            valid_task_count += 1
            print(f"  VALID: Parallel task {task_id}")
        elif task.get('type') == 'conditional':
            if 'condition' not in task:
                print(f"  INVALID: Conditional task {task_id} is missing required 'condition' field.")
                continue
            if 'if_true_tasks' not in task and 'if_false_tasks' not in task:
                print(f"  INVALID: Conditional task {task_id} has no task branches defined.")
                continue
            valid_task_count += 1
            print(f"  VALID: Conditional task {task_id}")
        else:
            missing_fields = []
            if 'hostname' not in task and 'return' not in task:
                missing_fields.append('hostname')
            if 'command' not in task and 'return' not in task:
                missing_fields.append('command')

            if missing_fields:
                print(f"  INVALID: Task {task_id} is missing required fields: {missing_fields}")
                continue
            else:
                valid_task_count += 1
                print(f"  VALID: Standard task {task_id}")

    print(f"\n=== FINAL RESULT ===")
    print(f"Valid tasks: {valid_task_count}")
    print(f"Total tasks parsed: {len(tasks)}")

    return tasks, valid_task_count

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 debug_task_parsing.py <task_file>")
        sys.exit(1)

    task_file = sys.argv[1]
    debug_parse_task_file(task_file)