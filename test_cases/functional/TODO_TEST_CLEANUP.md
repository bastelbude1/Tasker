# Test Cleanup Investigation TODO

This document tracks test files that need investigation for potential cleanup, consolidation, or removal.

## Category 0: BROKEN TESTS REQUIRING FIXES

### Tests with Validation Errors (MUST FIX OR REMOVE)

Tests that violate current validation rules (next + on_success/on_failure conflict):

- **statistics_verification_test.txt** - Uses both next= and on_success/on_failure
  - Error: "cannot use 'next' together with on_success, on_failure"
  - Action: Remove `next=` parameter (rely on on_success/on_failure only) OR create separate tests

- **delimiter_test.txt** - Check for validation errors
  - Action: Run validation, fix any issues

- **nested_parallelism_test.txt** - Check for validation errors
  - Action: Run validation, fix any issues

- **retry_test_1_basic.txt** - Uses both next= and on_success/on_failure
  - Action: Remove `next=` parameter

- **retry_test_3_custom_success.txt** - Check for validation errors
  - Action: Run validation, fix any issues

- **retry_test_4_high_retry.txt** - Check for validation errors
  - Action: Run validation, fix any issues

- **retry_test_5_mixed.txt** - Check for validation errors
  - Action: Run validation, fix any issues

**Priority: HIGH** - These tests were just given metadata but have underlying issues

## Category 1: Likely Redundant/Legacy Tests (INVESTIGATE FOR REMOVAL)

### Minimal/Debug Tests
- **debug_minimal_test.txt** - Only 6 lines, unclear purpose
  - Action: Determine purpose or delete

- **simple_test.txt** - Name suggests basic/legacy test
  - Action: Check if covered by modern tests, consider removal

- **first_test_simple.txt** - Name suggests early development test
  - Action: Check if covered by modern tests, consider removal

### Non-Deterministic Tests
- **example_task.txt** - Marked as "not suitable for automated testing"
  - Uses toggle_exit.sh with non-deterministic behavior
  - Action: Either fix for determinism or remove from automated suite

## Category 2: Potentially Redundant Parallel Tests (CHECK FOR OVERLAP)

These may overlap with existing test_parallel_*.txt files that have proper metadata:

- **clean_parallel_test.txt** - Tests parallel next conditions
  - Covered by: test_parallel_min_success_*.txt, test_parallel_all_success_*.txt, etc.
  - Action: Verify coverage overlap, consider removal

- **default_parallel_test.txt**
  - Action: Determine what "default" means, check for overlap

- **simplified_parallel_test.txt**
  - Action: Check if covered by other parallel tests

- **parallel_complex_next_conditions_test.txt**
  - Action: Review complexity, may provide unique coverage
  - Consider: Add metadata if unique, otherwise consolidate

## Category 3: Potentially Redundant Retry Tests (CHECK FOR OVERLAP)

These may overlap with retry_test_1/3/4/5.txt files that now have metadata:

- **local_retry_test.txt**
  - Action: Compare with retry_test_*.txt, check for unique local-specific coverage

- **retry_attempt_test_case.txt**
  - Action: Likely redundant with retry_test_1_basic.txt

- **retry_logic_test_case.txt**
  - Action: Likely redundant with retry_test_*.txt files

## Category 4: Local Execution Tests (CONSOLIDATE?)

- **local_only_test.txt**
  - Action: Check if exec=local is adequately covered elsewhere
  - Consider: Consolidate into single comprehensive local execution test

## Category 5: Host Validation Tests (SPECIAL HANDLING REQUIRED)

These test remote host validation and may not work in standard CI/CD:

- **host_validation_connection_error_test.txt**
- **host_validation_error_test.txt**
- **host_validation_localhost_test.txt**
- **host_validation_mixed_scenarios_test.txt**
- **host_validation_success_test.txt**
- **host_validation_test.txt**

**Action Required:**
1. Determine if these tests can run in CI/CD (likely need mock/stub)
2. Consider creating a separate test suite for integration/manual testing
3. If keeping: Add appropriate TEST_METADATA with skip flags
4. If removing: Document the validation scenarios they cover

## Recommended Actions Summary

### High Priority
1. **Remove clearly redundant tests**: debug_minimal_test.txt, example_task.txt
2. **Investigate parallel test overlap**: Compare clean_parallel_test.txt vs test_parallel_*.txt
3. **Investigate retry test overlap**: Compare retry_attempt/retry_logic vs retry_test_*.txt

### Medium Priority
4. **Review host validation tests**: Determine CI/CD compatibility
5. **Check local execution coverage**: Consolidate local_only_test.txt if redundant

### Low Priority
6. **Document retained tests**: Any test kept should have clear purpose documentation
7. **Add metadata to keepers**: If tests provide unique coverage, add TEST_METADATA

## Decision Criteria

Keep test if:
- ✅ Provides unique coverage not found in other tests
- ✅ Tests edge cases or boundary conditions
- ✅ Can run reliably in automated CI/CD
- ✅ Has clear, documented purpose

Remove test if:
- ❌ Functionality fully covered by tests with metadata
- ❌ Non-deterministic or requires manual intervention
- ❌ Unclear purpose after code review
- ❌ Legacy test from early development

---

*Last Updated: 2025-10-08*
*Branch: feature/add-test-metadata*
