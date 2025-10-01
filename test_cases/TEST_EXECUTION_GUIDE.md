# TASKER Test Suite Execution Guide

## 🎯 CRITICAL: 100% Success Rate Required

Per CLAUDE.md requirements, the test suite MUST achieve **100% success rate with ZERO TOLERANCE**:
- Any timeout = IMMEDIATE FAILURE
- Any Python exception = IMMEDIATE FAILURE
- Must test functionality, not environment issues

## ✅ Proper Test Execution Commands

### 1. Quick Verification (Recommended for development)
```bash
cd /home/baste/tasker/test_cases

# Test 5 representative files for quick validation
PASS=0 && TOTAL=0 && for file in clean_parallel_test.txt comprehensive_globals_test.txt delimiter_test.txt simple_test.txt timeout_summary_test.txt; do
    TOTAL=$((TOTAL+1))
    echo -n "Testing $file: "
    if PATH="../test_scripts:$PATH" timeout 20 ../tasker.py "$file" -r --skip-host-validation >/dev/null 2>&1; then
        echo "✅ PASS"
        PASS=$((PASS+1))
    else
        echo "❌ FAIL"
    fi
done && echo "RESULTS: $PASS/$TOTAL passed ($(echo "scale=1; $PASS * 100 / $TOTAL" | bc -l)% success rate)"
```

### 2. Full Verification (Required before commits)
```bash
cd /home/baste/tasker/test_cases

# Run complete verification with all fixes applied
./focused_verification.sh
```

### 3. Individual Test (For debugging specific issues)
```bash
cd /home/baste/tasker/test_cases

# Test specific file with full output
PATH="../test_scripts:$PATH" ../tasker.py [TEST_FILE.txt] -r --skip-host-validation

# Test with debug output
PATH="../test_scripts:$PATH" ../tasker.py [TEST_FILE.txt] -r --skip-host-validation -d
```

## 🔧 Critical Configuration Requirements

### PATH Setup (Essential)
The test_scripts directory must be in PATH for mock commands:
```bash
PATH="../test_scripts:$PATH"
```

**Mock Commands Available:**
- `pbrun` - Mock pbrun execution
- `p7s` - Mock p7s execution
- `wwrs_clir` - Mock wwrs execution

### Host Validation Skip (Essential)
Use `--skip-host-validation` to avoid connectivity issues:
```bash
--skip-host-validation
```

### Test File Exclusions
**Exclude these files** (designed to fail validation):
- `comprehensive_retry_validation_test.txt` - Intentional validation failure test

## 📊 Expected Results

### Success Criteria
- **Total Test Files:** 41
- **Functional Tests:** 40 (excluding 1 validation test)
- **Required Success Rate:** 40/40 = **100%**
- **Timeouts Allowed:** 0
- **Exceptions Allowed:** 0

### Sample Successful Output
```
=== RESULTS ===
Total: 40
Passed: 40
Failed: 0
Timeouts: 0

✅ SUCCESS: All tests passed - 100% success rate achieved
```

## 🚨 Troubleshooting Common Issues

### Issue: "pbrun: command not found"
**Solution:** PATH not set correctly
```bash
# Fix:
PATH="../test_scripts:$PATH" [command]
```

### Issue: Tests hanging or timing out
**Solution:** Host validation not skipped
```bash
# Fix:
--skip-host-validation
```

### Issue: Validation test failures
**Solution:** Exclude designed-to-fail validation tests
```bash
# These are intentionally designed to fail:
comprehensive_retry_validation_test.txt
```

### Issue: Permission denied on test_scripts
**Solution:** Ensure mock commands are executable
```bash
chmod +x ../test_scripts/pbrun
chmod +x ../test_scripts/p7s
chmod +x ../test_scripts/wwrs_clir
```

## 📁 Test Suite Structure

```
test_cases/
├── focused_verification.sh          # Main verification script
├── TEST_EXECUTION_GUIDE.md          # This guide
├── [40 functional test files].txt   # Core test cases
├── comprehensive_retry_validation_test.txt  # Validation test (skip)
└── ../test_scripts/
    ├── pbrun                         # Mock pbrun command
    ├── p7s                          # Mock p7s command
    └── wwrs_clir                    # Mock wwrs command
```

## 🎯 Development Workflow

### Before Making Code Changes
```bash
cd test_cases && ./focused_verification.sh
# Ensure 100% success rate baseline
```

### After Making Code Changes
```bash
cd test_cases && ./focused_verification.sh
# Verify no regressions, 100% success maintained
```

### Before Git Commit
```bash
cd test_cases && ./focused_verification.sh
# MANDATORY: Must achieve 100% success before commit
```

## 📝 Quick Reference Commands

```bash
# Navigate to test directory
cd /home/baste/tasker/test_cases

# Full verification
./focused_verification.sh

# Quick check (5 representative tests)
for file in clean_parallel_test.txt delimiter_test.txt simple_test.txt; do PATH="../test_scripts:$PATH" ../tasker.py "$file" -r --skip-host-validation >/dev/null 2>&1 && echo "$file: ✅" || echo "$file: ❌"; done

# Test new delimiter functionality specifically
PATH="../test_scripts:$PATH" ../tasker.py delimiter_test.txt -r --skip-host-validation

# Debug a specific failing test
PATH="../test_scripts:$PATH" ../tasker.py [FAILING_TEST.txt] -r --skip-host-validation -d
```

---

## 🏆 Success Confirmation

When you see this output, you've achieved the required 100% success rate:

```
✅ SUCCESS: All tests passed - 100% success rate achieved
Total: 40, Passed: 40, Failed: 0, Timeouts: 0
```

**Status: PRODUCTION READY** ✅