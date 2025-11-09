# Temp File Cleanup Verification

## Overview

This directory contains tests to verify that temporary files created by TASKER's streaming output handler are properly cleaned up after workflow execution.

## Background

TASKER uses temporary files to handle large outputs (>1MB) efficiently:
- Temp files are created as `tasker_stdout_XXXXXX` and `tasker_stderr_XXXXXX` in the system temp directory
- These files should be automatically deleted when the workflow completes
- **Bug Fixed (PR #92)**: The cleanup code was using incorrect glob patterns and failed to delete temp files

## Test Files

### `test_cleanup_verification.txt`
A task file that:
- Generates 2MB output in Task 0 (forces temp file creation)
- Generates 2MB output in Task 1 (creates second temp file)
- Verifies outputs can be accessed via cross-task variables in Task 2

### `../bin/verify_temp_cleanup.py`
Python script that verifies temp file cleanup:
1. Counts temp files before execution
2. Runs the test task file
3. Counts temp files after execution
4. Verifies no new temp files remain

## Usage

### Manual Verification Test

```bash
cd test_cases/
python3 bin/verify_temp_cleanup.py streaming/test_cleanup_verification.txt
```

**Expected Output:**
```
=== Temp File Cleanup Verification ===
Test file: test_cleanup_verification.txt
Temp directory: /tmp

Checking for existing tasker temp files...
Temp files before: N

Running tasker with test file...

Checking for temp files after execution...
New temp files after execution: 0

SUCCESS: All temp files were properly cleaned up!
```

### Running as Part of Test Suite

The test can also be run using the intelligent test runner:

```bash
cd test_cases/
python3 scripts/intelligent_test_runner.py streaming/test_cleanup_verification.txt
```

## What This Test Catches

This test would have caught the bug fixed in PR #92:
- **Bug**: Cleanup code used glob pattern `tasker_output_*_*.tmp` which didn't match actual filenames
- **Actual filenames**: `tasker_stdout_XXXXXX` and `tasker_stderr_XXXXXX`
- **Result**: Temp files accumulated in /tmp and were never deleted

## How It Works

1. **Before Execution**: Script captures list of existing tasker temp files
2. **During Execution**: Test file generates large outputs that trigger temp file creation
3. **After Execution**: Script checks if any new temp files remain
4. **Verification**: If new files exist, test fails and lists the leaked files

## Troubleshooting

### If the test fails:

1. **Check temp directory**:
   ```bash
   ls -lh /tmp/tasker_stdout_* /tmp/tasker_stderr_*
   ```

2. **Manually clean up leaked files**:
   ```bash
   rm -f /tmp/tasker_stdout_* /tmp/tasker_stderr_*
   ```

3. **Verify the cleanup code** in `tasker/core/task_executor_main.py` around line 920-966

## Related Files

- `tasker/core/task_executor_main.py` - Contains temp file cleanup logic
- `tasker/core/streaming_output_handler.py` - Creates temp files when output exceeds 1MB
- `ADVANCED_FEATURES.md` - Documents temp file lifecycle

## Testing Guidelines

- Run this test after any changes to temp file handling
- Run before creating releases to ensure no temp file leaks
- Monitor /tmp directory during development for unexpected temp files

---

**Note**: This test was created to prevent regression of the temp file cleanup bug discovered in PR #92.
