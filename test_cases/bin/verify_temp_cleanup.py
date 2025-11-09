#!/usr/bin/env python3
"""
Verify temp file cleanup test script.
This script runs a tasker test file and verifies that temp files are properly cleaned up.
"""

import os
import glob
import subprocess
import sys
import tempfile

def get_tasker_temp_files():
    """Get list of existing tasker temp files."""
    temp_dir = tempfile.gettempdir()
    pattern1 = os.path.join(temp_dir, "tasker_stdout_*")
    pattern2 = os.path.join(temp_dir, "tasker_stderr_*")
    files = glob.glob(pattern1) + glob.glob(pattern2)
    return set(files)

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_temp_cleanup.py <test_file>")
        sys.exit(1)

    test_file = sys.argv[1]
    # Resolve absolute path to tasker.py (two levels up from test_cases/bin/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tasker_bin = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "tasker.py")

    print("=== Temp File Cleanup Verification ===")
    print(f"Test file: {test_file}")
    print(f"Temp directory: {tempfile.gettempdir()}")
    print("")

    # Count temp files before execution
    print("Checking for existing tasker temp files...")
    before_files = get_tasker_temp_files()
    print(f"Temp files before: {len(before_files)}")

    # Run tasker
    print("")
    print("Running tasker with test file...")
    try:
        result = subprocess.run(
            [tasker_bin, test_file, "--skip-host-validation", "--skip-security-validation"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"ERROR: Tasker execution failed with exit code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to run tasker: {e}")
        sys.exit(1)

    # Count temp files after execution
    print("")
    print("Checking for temp files after execution...")
    after_files = get_tasker_temp_files()
    new_files = after_files - before_files

    print(f"New temp files after execution: {len(new_files)}")

    # Verify no new temp files remain
    if len(new_files) > 0:
        print("")
        print(f"ERROR: Found {len(new_files)} temp files that were not cleaned up:")
        for f in sorted(new_files):
            print(f"  - {f}")
        print("")
        print("VERIFICATION FAILED: Temp files were not properly cleaned up!")
        sys.exit(1)

    print("")
    print("SUCCESS: All temp files were properly cleaned up!")
    sys.exit(0)

if __name__ == "__main__":
    main()
