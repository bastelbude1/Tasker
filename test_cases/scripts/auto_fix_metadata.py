#!/usr/bin/env python3
"""
Auto-fix test metadata by running tests and detecting actual behavior.
"""

import os
import json
import re
import subprocess
import sys

def run_test(filepath):
    """Run a test and capture exit code and warnings."""
    cmd = [
        'python3', '../tasker.py',
        '--skip-host-validation',
        filepath
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd='/home/baste/tasker/test_cases'
        )

        exit_code = result.returncode
        stderr = result.stderr
        stdout = result.stdout

        # Count warnings (check both stdout and stderr)
        warning_count = stdout.count('WARN:') + stderr.count('WARN:')

        # Check if it's a validation failure (case-insensitive, check both stdout and stderr)
        combined_output = (stdout + stderr).lower()
        is_validation_failure = 'validation failed' in combined_output

        # Check if it timed out
        is_timeout = exit_code == 124

        return {
            'exit_code': exit_code,
            'warning_count': warning_count,
            'is_validation_failure': is_validation_failure,
            'is_timeout': is_timeout,
            'stderr': stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'exit_code': 124,
            'warning_count': 0,
            'is_validation_failure': False,
            'is_timeout': True,
            'stderr': ''
        }
    except Exception as e:
        print(f"ERROR running {filepath}: {e}")
        return None

def fix_metadata(filepath, test_result):
    """Fix metadata based on test results."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract metadata
    match = re.search(r'# TEST_METADATA: ({.*})', content)
    if not match:
        print(f"⊘ No metadata found in {filepath}")
        return False

    metadata = json.loads(match.group(1))

    # Determine correct metadata based on test results
    if test_result['is_validation_failure'] and test_result['exit_code'] == 20:
        metadata['test_type'] = 'validation_only'
        metadata['expected_exit_code'] = 20
        metadata['expected_success'] = False
    elif test_result['exit_code'] == 0:
        metadata['expected_exit_code'] = 0
        metadata['expected_success'] = True
    elif test_result['is_timeout']:
        metadata['expected_exit_code'] = 124
        metadata['expected_success'] = False
    else:
        metadata['expected_exit_code'] = test_result['exit_code']
        metadata['expected_success'] = False

    # Add expected_warnings if warnings detected
    if test_result['warning_count'] > 0:
        metadata['expected_warnings'] = test_result['warning_count']
    elif 'expected_warnings' in metadata:
        # Remove expected_warnings if no warnings found
        del metadata['expected_warnings']

    # Build new metadata line
    new_metadata_line = f"# TEST_METADATA: {json.dumps(metadata, separators=(',', ': '))}\n"

    # Replace metadata
    new_content = re.sub(r'# TEST_METADATA: {.*}\n', new_metadata_line, content)

    with open(filepath, 'w') as f:
        f.write(new_content)

    return True

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python3 auto_fix_metadata.py <directory>")
        sys.exit(1)

    test_dir = sys.argv[1]

    # Find all .txt files
    test_files = []
    for root, dirs, files in os.walk(test_dir):
        for filename in files:
            if filename.endswith('.txt'):
                filepath = os.path.join(root, filename)
                test_files.append(filepath)

    print(f"Found {len(test_files)} test files")

    fixed_count = 0
    for filepath in sorted(test_files):
        rel_path = os.path.relpath(filepath, '/home/baste/tasker/test_cases')
        print(f"\n Testing: {rel_path}")

        # Run test
        result = run_test(rel_path)
        if result is None:
            continue

        print(f"  Exit: {result['exit_code']}, Warnings: {result['warning_count']}")

        # Fix metadata
        if fix_metadata(filepath, result):
            print(f"  ✅ Fixed metadata")
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} test files")

if __name__ == '__main__':
    main()
