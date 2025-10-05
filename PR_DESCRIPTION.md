# Pull Request: Smart Task Sequence Validation

## Repository
https://github.com/bastelbude1/Tasker

## Branch
feature/metadata-conditional-block-tests

## Pull Request URL
https://github.com/bastelbude1/Tasker/compare/master...feature/metadata-conditional-block-tests

## Title
feat: Smart task sequence validation with enterprise patterns

## Description

### Summary
- Implements intelligent gap validation that recognizes common enterprise patterns
- Adds reachability analysis for orphaned task detection
- Fixes --show-plan to respect validation order

### Key Changes

#### Smart Gap Validation
- Recognizes special task ID ranges used in enterprise workflows:
  - **90-99**: Common range for cleanup/error handlers (e.g., firewall tasks)
  - **100+**: Common range for parallel task groups and special handlers
- Only flags gaps as errors when tasks are truly unreachable
- Considers explicit routing (on_success, on_failure, next) when evaluating gaps

#### Reachability Analysis
- Implements graph traversal to detect orphaned/unreachable tasks
- Uses BFS from start task to identify connected components
- Warns about tasks that can never be executed

#### Validation Order Fix
- Ensures --show-plan respects validation and doesn't show plans for invalid files
- Moves validation before execution plan display
- Prevents misleading output for workflows with validation errors

### Test Plan
✅ Created comprehensive test cases:
- test_firewall_handler.txt - Error handler at task 99 (passes)
- test_parallel_group.txt - Parallel tasks in 100+ range (passes)
- test_orphaned_task.txt - Unreachable task detection (fails as expected)
- test_real_gap.txt - Actual gap that should fail (fails as expected)
- test_conditional_gap.txt - Gap after conditional (now allowed)

✅ Verification:
- All test cases validate correctly
- --show-plan properly rejects invalid files
- Backward compatibility maintained for existing workflows

### Impact
This enhancement makes TASKER validation more intelligent and user-friendly while ensuring workflow integrity. It recognizes common enterprise patterns without requiring workarounds or validation bypasses.

### Commits Included (after rebase)
- 129a1b6 fix: Ensure --show-plan respects validation order
- 75c6cb3 feat: Implement smart sequence validation with hybrid approach

Note: This branch has been rebased onto the latest master and contains only the 2 new commits specific to the smart validation feature. Previous commits were already merged via other PRs.