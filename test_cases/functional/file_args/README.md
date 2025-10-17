# File-Defined Arguments Test Suite

This test suite validates the file-defined arguments feature, which allows task files to define TASKER command-line arguments directly in the file header.

## Test Categories

### Basic Functionality Tests
- **test_file_args_basic_flag.txt**: Single boolean flag (`--skip-host-validation`)
- **test_file_args_value_option.txt**: Single value option (`--log-level=DEBUG`)
- **test_file_args_multiple.txt**: Multiple flags and options combined
- **test_file_args_no_args.txt**: No file-defined args (backward compatibility)

### Security Tests
- **test_file_args_help_forbidden.txt**: CLI-only flag `--help` should be rejected
- **test_file_args_version_forbidden.txt**: CLI-only flag `--version` should be rejected
- **test_file_args_security_warning.txt**: Security-sensitive flags should warn but allow

### Edge Cases
- **test_file_args_with_comments.txt**: Comments interspersed between arguments
- **test_file_args_spacing.txt**: Arguments with proper spacing

## Running Tests

```bash
# Run all file-defined arguments tests
python3 scripts/intelligent_test_runner.py functional/file_args/ -r

# Run specific test
python3 ../tasker.py functional/file_args/test_file_args_basic_flag.txt -r --skip-host-validation
```

## Expected Results

All tests should pass:
- **Basic functionality**: 4 tests
- **Security tests**: 3 tests
- **Edge cases**: 2 tests
- **Total**: 9 tests

## Test Coverage

These tests validate:
1. **Parsing**: Arguments correctly extracted from file headers
2. **Merging**: File args provide baseline, CLI can override
3. **Security**: CLI-only flags blocked, sensitive flags warned
4. **Compatibility**: Files without args still work
5. **Robustness**: Comments and spacing handled correctly

## Known Limitations

- Cannot test CLI override in automated tests (would require CLI execution)
- Warning count validation is approximate due to multiple warning sources
