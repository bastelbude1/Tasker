#!/usr/bin/env python3
"""
Fix security test metadata by adding required security_category field.
"""

import os
import json
import re

def extract_security_category(filename):
    """Extract security category from filename."""
    if 'command_injection' in filename:
        return 'command_injection'
    elif 'path_traversal' in filename:
        return 'path_traversal'
    elif 'buffer_overflow' in filename:
        return 'buffer_overflow'
    elif 'malformed' in filename:
        return 'malformed_input'
    elif 'resource_exhaustion' in filename:
        return 'resource_exhaustion'
    else:
        return 'security_violation'

def fix_security_metadata(filepath):
    """Add security_category to security test metadata."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Check if it has TEST_METADATA
    if 'TEST_METADATA' not in content:
        return False

    # Extract and parse metadata
    match = re.search(r'# TEST_METADATA: ({.*})', content)
    if not match:
        return False

    metadata = json.loads(match.group(1))

    # Add security_category (or update if exists)
    filename = os.path.basename(filepath)
    metadata['security_category'] = extract_security_category(filename)

    # Build new metadata line
    new_metadata_line = f"# TEST_METADATA: {json.dumps(metadata, separators=(',', ': '))}\n"

    # Replace old metadata line
    new_content = re.sub(r'# TEST_METADATA: {.*}\n', new_metadata_line, content)

    # Write back
    with open(filepath, 'w') as f:
        f.write(new_content)

    return True

def main():
    """Main function."""
    security_dir = '/home/baste/tasker/test_cases/security'

    fixed_count = 0
    for filename in os.listdir(security_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(security_dir, filename)
            if fix_security_metadata(filepath):
                print(f"✅ Fixed: {filename}")
                fixed_count += 1
            else:
                print(f"⊘ Skipped: {filename}")

    print(f"\n✅ Fixed {fixed_count} security test files")

if __name__ == '__main__':
    main()
