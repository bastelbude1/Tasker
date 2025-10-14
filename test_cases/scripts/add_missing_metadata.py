#!/usr/bin/env python3
"""
Add TEST_METADATA to tests that are missing it.
Intelligently determines metadata based on file content and naming patterns.
"""

import os
import re
import sys

def detect_test_type(filepath, content):
    """Detect test type based on file path and content."""
    filename = os.path.basename(filepath)
    dirname = os.path.basename(os.path.dirname(filepath))

    # Security tests
    if 'security' in filepath:
        return {
            'test_type': 'security_negative',
            'expected_exit_code': 20,
            'expected_success': False,
            'risk_level': 'high'
        }

    # Timeout/stress tests typically have longer execution
    if 'timeout' in filename or 'stress' in filename:
        return {
            'test_type': 'performance',
            'expected_exit_code': 0,
            'expected_success': True
        }

    # Retry validation tests
    if 'retry_validation' in filename:
        return {
            'test_type': 'validation_only',
            'expected_exit_code': 20,
            'expected_success': False
        }

    # Most edge cases and integration tests are positive
    return {
        'test_type': 'positive',
        'expected_exit_code': 0,
        'expected_success': True
    }

def generate_description(filepath):
    """Generate description from filename."""
    filename = os.path.basename(filepath).replace('.txt', '').replace('_', ' ')
    # Capitalize first letter
    return filename[0].upper() + filename[1:]

def add_metadata(filepath):
    """Add TEST_METADATA to a test file."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Skip if already has metadata
    if 'TEST_METADATA' in content:
        return False

    # Detect test characteristics
    test_info = detect_test_type(filepath, content)
    description = generate_description(filepath)

    # Build metadata
    metadata = {
        'description': description,
        **test_info,
        'skip_host_validation': True
    }

    # Format as JSON
    import json
    metadata_line = f"# TEST_METADATA: {json.dumps(metadata, separators=(',', ': '))}\n"

    # Add metadata as first line
    new_content = metadata_line + content

    # Write back
    with open(filepath, 'w') as f:
        f.write(new_content)

    return True

def main():
    """Main function."""
    test_cases_dir = '/home/baste/tasker/test_cases'

    # Find all .txt files missing TEST_METADATA
    for root, dirs, files in os.walk(test_cases_dir):
        # Skip logs, old, legacy directories
        dirs[:] = [d for d in dirs if d not in ['logs', 'old', 'legacy', '__pycache__']]

        for filename in files:
            if filename.endswith('.txt'):
                filepath = os.path.join(root, filename)

                # Check if missing metadata
                with open(filepath, 'r') as f:
                    if 'TEST_METADATA' not in f.read():
                        if add_metadata(filepath):
                            print(f"✅ Added metadata to: {filepath}")
                        else:
                            print(f"⊘ Skipped (already has metadata): {filepath}")

if __name__ == '__main__':
    main()
