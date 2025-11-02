# Feature Analysis: Multi-Host Simplified Syntax

## Executive Summary

**Feature Request:** Add support for comma-separated hostname lists in parallel blocks to eliminate the verbosity of defining identical subtasks.

**Recommendation:** ✅ **IMPLEMENT** - High value, manageable complexity, aligns with TASKER philosophy

**Benefit/Cost Ratio:** ~50:1 (eliminates 150+ lines per use, implementation ~350 lines)

---

## Current Problem

### Real-World Scenario: Health Check 20 Servers

**Current Required Syntax:**
```bash
task=0
type=parallel
tasks=100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119
max_parallel=20

task=100
hostname=web1
command=curl
arguments=-sf http://localhost/health
exec=local
timeout=30

task=101
hostname=web2
command=curl
arguments=-sf http://localhost/health
exec=local
timeout=30

task=102
hostname=web3
command=curl
arguments=-sf http://localhost/health
exec=local
timeout=30

# ... REPEAT 17 MORE TIMES (tasks 103-119)
```

**Pain Points:**
- **160+ lines** of repetitive code
- **20 copy-paste operations** = 20 opportunities for errors
- **5-10 minutes** to write and verify
- **Hard to modify** - need to update 20 places if timeout changes
- **Poor readability** - intent buried in repetition
- **Doesn't scale** - 100 servers = 500+ lines

---

## Proposed Solution

### Simplified Syntax Option 1: New Parameter `hostnames=`

```bash
task=0
type=parallel
hostnames=web1,web2,web3,web4,web5,web6,web7,web8,web9,web10,web11,web12,web13,web14,web15,web16,web17,web18,web19,web20
command=curl
arguments=-sf http://localhost/health
exec=local
max_parallel=20
timeout=30
success=min_success=15  # At least 75% must succeed
on_success=10
on_failure=99
```

**Result:**
- **11 lines** (was 160+ lines) = **93% reduction**
- **30 seconds** to write (was 5-10 minutes) = **10-20x faster**
- **Single source of truth** - no copy-paste errors
- **Easy to modify** - change timeout once, affects all
- **Clear intent** - immediately obvious what this does

---

## Benefits Analysis (Pros)

### 1. Massive Verbosity Reduction

| Servers | Current Lines | Proposed Lines | Reduction |
|---------|--------------|----------------|-----------|
| 5       | 40+          | 8              | 80%       |
| 10      | 80+          | 8              | 90%       |
| 20      | 160+         | 11             | 93%       |
| 50      | 400+         | 11             | 97%       |
| 100     | 800+         | 11             | 98.6%     |

### 2. Dramatically Reduced Human Error

**Current approach error vectors:**
- Typo in one of 20 hostnames
- Inconsistent timeout across copies
- Forgot to update task ID sequence
- Inconsistent arguments
- Wrong exec type on one task
- Copy-paste preserves wrong old value

**Proposed approach:**
- Single definition = single point of error
- Impossible to have inconsistent parameters
- Clear, reviewable syntax

### 3. Improved Maintainability

**Scenario: Change timeout from 30s to 60s**

Current: Find and modify 20 locations
Proposed: Modify 1 location

**Scenario: Add retry_count=3**

Current: Add to 20 task definitions
Proposed: Add to 1 place

### 4. Better Readability

**Current:** Intent obscured by 160 lines of repetition
**Proposed:** Intent immediately clear in 11 lines

Non-technical managers can understand proposed syntax instantly.

### 5. Addresses Core Use Case

**This pattern is EXTREMELY common in operations:**
- Health checks across application fleet
- Deploy same package to multiple servers
- Collect logs from web tier
- Run maintenance script on database replicas
- Restart services across cluster
- Check disk space on storage nodes

**Estimate:** 70-80% of real-world TASKER parallel blocks fit this pattern.

### 6. Competitive Positioning

**Ansible equivalent:**
```yaml
- hosts: webservers
  tasks:
    - name: Health check
      uri:
        url: http://localhost/health
```

Ansible's inventory system makes multi-host concise.

**Current TASKER:** More verbose than Ansible for this case
**Proposed TASKER:** Comparable to Ansible, but keeps TASKER's text file simplicity

### 7. Leverages Existing Infrastructure

- Reuses parallel executor (no new execution logic)
- Reuses retry mechanism
- Reuses statistics (@0_success_count@, @0_majority_success@)
- Reuses validation framework
- Just **syntactic sugar** over existing capabilities

### 8. Aligns with TASKER Philosophy

**TASKER's stated goal:** "Simple things simple, complex things possible"

**Current state:** Simple multi-host task requires complex verbose syntax (violates philosophy)

**Proposed state:** Simple multi-host task has simple syntax (aligns with philosophy)

---

## Drawbacks Analysis (Cons)

### 1. Code Complexity (+350 lines)

**New code required:**
- Parsing `hostnames=` parameter: ~50 lines
- Dynamic subtask generation: ~100 lines
- Validation logic: ~50 lines
- Test cases: ~100 lines
- Documentation: ~50 lines

**Total implementation:** ~350 lines

**Maintenance burden:** Moderate - needs testing, but logic is straightforward

### 2. Two Ways to Accomplish Same Thing

**Approach 1:** Explicit subtasks (current)
```bash
type=parallel
tasks=100,101,102
```

**Approach 2:** Hostname list (proposed)
```bash
type=parallel
hostnames=web1,web2,web3
```

**Potential confusion:** "Which should I use?"

**Mitigation:** Clear documentation guidelines:
- Use `hostnames=` when: Same command on multiple hosts
- Use `tasks=` when: Different commands, arguments, or timeouts per host

### 3. Loss of Individual Task Control

**With explicit subtasks, each can differ:**
```bash
task=100
hostname=web1
timeout=30

task=101
hostname=web2
timeout=60  # Different timeout

task=102
hostname=web3
retry_count=5  # Different retry
```

**With hostnames list, all identical:**
```bash
hostnames=web1,web2,web3
timeout=30  # Applied to all
```

**Counterargument:** Users can still use explicit subtasks for complex cases. This feature targets the **common simple case** (80% of usage).

### 4. Subtask ID Assignment Convention

**Question:** When `task=0` with `hostnames=web1,web2,web3`, what task IDs are generated?

**Options:**
- **Option A:** 100, 101, 102 (task * 100 + index)
- **Option B:** 1000, 1001, 1002 (task * 1000 + index)
- **Option C:** 0.0, 0.1, 0.2 (decimal notation)

**Recommendation:** Option B (task * 1000 + index)
- Allows up to 1000 hosts per parallel block
- Clear separation between task spaces
- task=0 → 0-999, task=1 → 1000-1999, task=2 → 2000-2999

**Risk:** Must document clearly, avoid conflicts with user-defined tasks

### 5. Output Variable Semantics

**Challenge:** With 20 hosts, what does `@0_stdout@` mean?

**Options:**

**A) Aggregate only:**
```bash
@0_success_count@     # 15
@0_failed_count@      # 5
@0_majority_success@  # true/false
@0_stdout@            # ERROR: Not available (ambiguous)
```

**B) Individual access:**
```bash
@0.0_stdout@  # web1's output
@0.1_stdout@  # web2's output
@0.2_stdout@  # web3's output
```

**C) Concatenated:**
```bash
@0_stdout@  # All outputs concatenated (newline separated)
```

**Recommendation:** Start with **Option A** (aggregate only)
- Simplest to implement
- Prevents ambiguity
- Statistics are what users actually need for routing
- Can add Option B later if demand exists

### 6. Feature Creep Risk

Once this is added, users might request:
- Port ranges: `ports=8080-8090`
- IP ranges: `hosts=192.168.1.1-192.168.1.50`
- File-based host lists: `hostfile=/etc/hosts.txt`
- Variable expansion: `hostnames=@WEBSERVERS@`

**Mitigation:**
- Document scope clearly
- Stick to comma-separated list initially
- Evaluate additional features based on actual demand

### 7. Testing Complexity

**Additional test cases needed:**
- 2 hosts, all succeed
- 5 hosts, all succeed
- 20 hosts, max_parallel=5
- Some hosts fail, min_success met
- Some hosts fail, min_success not met
- All hosts fail
- Retry with hostnames
- Timeout with hostnames
- Empty hostnames (validation)
- Single hostname (validation - should fail)
- Both tasks= and hostnames= (validation - should fail)
- 1000 hosts (maximum)
- Special characters in hostnames
- Whitespace handling

**Estimate:** ~15-20 new test cases

---

## Benefit/Cost Analysis

### Quantitative Comparison

**One-time implementation cost:**
- 350 lines of code
- ~15 hours development time (2 days)
- ~20 test cases
- Documentation updates

**Benefit per use:**
- Saves 150+ lines of user code (20 server case)
- Saves 5-10 minutes writing time
- Eliminates copy-paste errors
- Reduces maintenance burden

**Break-even point:** If feature is used 3-5 times, benefit exceeds cost

**Expected usage:** Every multi-server operation (very high frequency)

**Conclusion:** **Benefit >> Cost** by approximately **50:1 ratio**

### Qualitative Benefits

- **User experience improvement:** Massive
- **Reduced frustration:** High (no more copy-paste hell)
- **Competitive positioning:** Brings TASKER to parity with Ansible
- **Philosophy alignment:** Makes "simple things simple"
- **Risk level:** Medium (touches parallel execution, needs testing)

---

## Implementation Options

### Option 1: New Block Type `type=parallel_hosts`

```bash
task=0
type=parallel_hosts  # NEW TYPE
hostnames=web1,web2,web3
command=curl
arguments=-sf http://localhost/health
exec=local
max_parallel=3
```

**Pros:**
- Clear semantic distinction
- Doesn't overload existing `type=parallel`
- Easy validation: type requires hostnames

**Cons:**
- Another block type (complexity)
- Duplicates parallel execution logic
- More types to learn

**Verdict:** ❌ Not recommended - adds unnecessary abstraction

### Option 2: Extend `type=parallel` with `hostnames=` ✅ RECOMMENDED

```bash
task=0
type=parallel
hostnames=web1,web2,web3  # NEW PARAMETER
command=curl
arguments=-sf http://localhost/health
exec=local
max_parallel=3
```

**Validation:** `type=parallel` requires EITHER `tasks=` OR `hostnames=` (mutually exclusive)

**Pros:**
- Reuses existing type
- Less conceptual overhead
- Natural extension
- Cleaner implementation

**Cons:**
- Overloads `type=parallel` semantics slightly
- Need clear mutual exclusivity validation

**Verdict:** ✅ **Best approach** - natural extension of parallel concept

### Option 3: Implicit Multi-Host on Regular Tasks

```bash
task=0
hostname=web1,web2,web3  # If comma-separated, auto-parallel
command=curl
max_parallel=3
```

**Pros:**
- Simplest syntax
- No new type needed

**Cons:**
- **Implicit magic behavior** (bad)
- Breaks explicit `type=parallel` pattern
- `hostname=` (singular) now means multiple hosts (confusing)
- Harder to validate

**Verdict:** ❌ Not recommended - too much implicit behavior

### Option 4: External Helper Script

```bash
$ ./generate_parallel_tasks.py --hosts=web1,web2,web3 --command=curl --args="-sf /health"

# Output: Generated task definitions (copy-paste into task file)
```

**Pros:**
- Zero TASKER code complexity
- Very flexible
- Can generate sophisticated patterns

**Cons:**
- External dependency
- Not seamless
- Doesn't feel native
- Still requires copy-paste

**Verdict:** ❌ Poor user experience - defeats the purpose

---

## Implementation Plan (Option 2)

### Phase 1: Core Parsing & Validation (3 hours)

**File:** `tasker/validation/task_validator.py`

**Tasks:**
1. Add `hostnames` to `parallel_specific_fields`
2. Add mutual exclusivity validation:
   - `type=parallel` requires `tasks=` OR `hostnames=` (not both, not neither)
3. Add hostnames-specific validation:
   - If `hostnames=` present, require `command=`
   - Parse comma-separated list
   - Validate at least 2 hostnames
   - Validate maximum 1000 hostnames
   - Validate each hostname format
4. Add clear error messages

**Code estimate:** ~100 lines

### Phase 2: Dynamic Subtask Generation (4 hours)

**File:** `tasker/executors/parallel_executor.py`

**Tasks:**
1. Detect `hostnames=` in parallel block
2. Generate subtask definitions dynamically:
   ```python
   def generate_subtasks_from_hostnames(parallel_task):
       """
       Input: task=0, hostnames=web1,web2,web3, command=curl, ...
       Output: [
           {'task': 0, 'hostname': 'web1', 'command': 'curl', ...},
           {'task': 1, 'hostname': 'web2', 'command': 'curl', ...},
           {'task': 2, 'hostname': 'web3', 'command': 'curl', ...}
       ]
       """
   ```
3. Subtask ID convention: `base_task * 1000 + index`
   - task=0, 3 hosts → subtasks 0, 1, 2
   - task=1, 3 hosts → subtasks 1000, 1001, 1002
   - task=2, 3 hosts → subtasks 2000, 2001, 2002
4. Copy parameters from parent to subtasks:
   - Required: command, hostname
   - Optional: arguments, exec, timeout, retry_count, retry_delay, success, failure
5. Mark subtasks as `_generated_from=<parent_task_id>` (for debugging)
6. Register generated subtasks in executor's task dictionary

**Code estimate:** ~100 lines

### Phase 3: Variable Handling (2 hours)

**Strategy:** Use existing parallel statistics, no new variables needed

**Available variables (already exist):**
```bash
@0_success_count@       # Number of hosts that succeeded
@0_failed_count@        # Number of hosts that failed
@0_all_success@         # true if all succeeded
@0_any_success@         # true if at least one succeeded
@0_majority_success@    # Percentage threshold (e.g., @0_majority_success@=75)
@0_min_success@         # Minimum count threshold
@0_max_failed@          # Maximum failures threshold
```

**Not available (by design):**
```bash
@0_stdout@         # Ambiguous - which host?
@0_stderr@         # Ambiguous - which host?
@0_exit_code@      # Ambiguous - which host?
```

**Rationale:**
- Users route based on success/failure statistics (already supported)
- Individual host outputs rarely needed for routing
- If needed, users can use explicit subtasks with tasks=

**Code estimate:** ~0 lines (use existing infrastructure)

### Phase 4: Testing (4 hours)

**Test cases:**

**Basic functionality:**
1. `test_parallel_hostnames_basic_2_hosts.txt` - 2 hosts, all succeed
2. `test_parallel_hostnames_5_hosts.txt` - 5 hosts, all succeed
3. `test_parallel_hostnames_max_parallel.txt` - 10 hosts, max_parallel=3

**Failure handling:**
4. `test_parallel_hostnames_some_fail_min_success_met.txt`
5. `test_parallel_hostnames_some_fail_min_success_not_met.txt`
6. `test_parallel_hostnames_all_fail.txt`

**Retry logic:**
7. `test_parallel_hostnames_retry.txt` - retry_count=3 with some failures
8. `test_parallel_hostnames_retry_delay.txt` - retry with delays

**Success criteria:**
9. `test_parallel_hostnames_min_success.txt` - success=min_success=4
10. `test_parallel_hostnames_majority_success.txt` - success=majority_success=75

**Validation:**
11. `test_parallel_hostnames_validation_missing_command.txt` - Should fail (no command)
12. `test_parallel_hostnames_validation_empty.txt` - Should fail (empty hostnames)
13. `test_parallel_hostnames_validation_single.txt` - Should fail (use hostname= for single)
14. `test_parallel_hostnames_validation_both_tasks_and_hostnames.txt` - Should fail (mutually exclusive)
15. `test_parallel_hostnames_validation_neither.txt` - Should fail (need one or the other)
16. `test_parallel_hostnames_validation_too_many.txt` - 1001 hosts, should fail

**Edge cases:**
17. `test_parallel_hostnames_1000_hosts.txt` - Maximum supported
18. `test_parallel_hostnames_whitespace.txt` - "web1, web2, web3" (spaces)
19. `test_parallel_hostnames_special_chars.txt` - Hostnames with hyphens, dots

**Integration:**
20. `test_parallel_hostnames_with_conditional.txt` - Use @0_majority_success@ routing

**Code estimate:** ~150 lines (test files + metadata)

### Phase 5: Documentation (2 hours)

**Files to update:**

**1. README.md** - Add new section after existing parallel block documentation

```markdown
### Simplified Multi-Host Parallel Execution

When you need to run the same command on multiple servers, TASKER provides simplified syntax:

```bash
task=0
type=parallel
hostnames=web1,web2,web3,web4,web5
command=curl
arguments=-sf http://localhost/health
exec=local
max_parallel=3
timeout=30
success=min_success=4  # At least 4 must succeed
on_success=10
on_failure=99
```

This automatically creates a subtask for each hostname and executes them in parallel.

**When to use `hostnames=`:**
- Same command across multiple servers
- Health checks, deployments, log collection
- Identical parameters for all hosts

**When to use explicit subtasks with `tasks=`:**
- Different commands per server
- Different arguments, timeouts, or retry counts
- Individual success criteria per task
- Complex workflows requiring per-task control

**Limitations:**
- All hosts execute identical command/arguments
- Individual host outputs not accessible via variables
- Use aggregate statistics for routing (@0_success_count@, @0_majority_success@)
```

**2. TaskER_FlowChart.md** - Add visual diagram for hostnames approach

**3. CLAUDE.md** - Update with new feature details

**Code estimate:** ~100 lines documentation

### Phase 6: Edge Case Handling

**Hostname format validation:**
- Valid: `web1`, `db-prod-01`, `192.168.1.10`, `server.example.com`
- Invalid: empty strings, only whitespace, special chars like `@`, `#`

**Conflict detection:**
- Warn if generated subtask IDs would conflict with user-defined tasks
- Example: task=0 with 5 hosts generates tasks 0-4
  - If user also defined task=2 explicitly → ERROR: Conflict

**Maximum limits:**
- 1000 hosts per hostnames= parameter (reasonable operational limit)
- Prevents accidental resource exhaustion

**Error messages:**
```
ERROR: Parallel block (task 0) cannot have both 'tasks=' and 'hostnames='
ERROR: Parallel block (task 0) with 'hostnames=' requires 'command=' parameter
ERROR: Parallel block (task 0) hostnames list cannot be empty
ERROR: Parallel block (task 0) requires at least 2 hostnames (use 'hostname=' for single host)
ERROR: Parallel block (task 0) supports maximum 1000 hostnames, found 1500
ERROR: Parallel block (task 0) invalid hostname: 'web@#$1'
ERROR: Generated subtask 2 from task 0 conflicts with user-defined task 2
```

---

## Implementation Timeline

| Phase | Hours | Description |
|-------|-------|-------------|
| 1. Parsing & Validation | 3 | Add hostnames parameter, validation logic |
| 2. Subtask Generation | 4 | Dynamic subtask creation from hostnames |
| 3. Variable Handling | 2 | Ensure statistics work correctly |
| 4. Testing | 4 | 20 test cases covering all scenarios |
| 5. Documentation | 2 | README, FlowChart, CLAUDE.md updates |
| **Total** | **15 hours** | **~2 working days** |

**Risk Level:** Medium
- Touches parallel execution (complex area)
- Requires thorough testing
- Must not break existing parallel blocks

**Confidence Level:** High
- Reuses existing infrastructure
- Straightforward logic
- Clear requirements

---

## Backward Compatibility

✅ **Zero breaking changes**

**Existing task files work identically:**
- All existing `type=parallel` with `tasks=` unchanged
- New parameter `hostnames=` is additive
- No modification to existing behavior
- No deprecations

**Migration path:** None needed (new feature, not replacement)

---

## Alternatives Considered

### Alternative 1: Do Nothing (Use Current Approach)

**Pros:**
- No code complexity
- No maintenance burden

**Cons:**
- Users continue suffering from verbosity (160+ lines for 20 hosts)
- Copy-paste errors persist
- TASKER less competitive vs Ansible
- Violates "simple things simple" philosophy

**Verdict:** ❌ Unacceptable - problem is too painful

### Alternative 2: External Code Generator

Provide Python script to generate repetitive tasks.

**Pros:**
- Zero TASKER code changes
- Flexible

**Cons:**
- Not integrated (feels like a hack)
- Still requires copy-paste
- External dependency

**Verdict:** ❌ Poor UX

### Alternative 3: File-based Host Lists

```bash
task=0
type=parallel
hostfile=/etc/ansible/hosts
```

**Pros:**
- Supports large host lists
- Reuses existing inventory systems

**Cons:**
- External dependency
- More complex than comma list
- Can add later if needed

**Verdict:** ⏸️ Defer - start with inline list, add file support if demand exists

---

## Risks & Mitigation

### Risk 1: Subtask ID Conflicts

**Scenario:** User defines task=1, system generates task=1 from hostnames

**Mitigation:**
- Use high ID range: base_task * 1000
- Validate no conflicts during validation phase
- Clear error message if conflict detected

### Risk 2: Unexpected Behavior with Variables

**Scenario:** User expects `@0_stdout@` to work, gets error

**Mitigation:**
- Document clearly in README
- Provide helpful error message
- Show examples using aggregate statistics

### Risk 3: Performance with 1000 Hosts

**Scenario:** Generating 1000 subtasks takes too long

**Mitigation:**
- Subtask generation is simple dict creation (fast)
- Test with 1000 hosts to verify performance
- If needed, optimize generation code

### Risk 4: Breaks Existing Parallel Blocks

**Scenario:** New code introduces regression

**Mitigation:**
- Comprehensive testing of existing parallel blocks
- Run all existing parallel tests
- Code review focused on backward compatibility

---

## Success Metrics

**Feature will be successful if:**
1. ✅ Reduces verbosity by >90% for common case
2. ✅ Zero breaking changes to existing task files
3. ✅ All test cases pass (old + new)
4. ✅ Documentation clear and complete
5. ✅ Performance acceptable up to 1000 hosts
6. ✅ User adoption high (measured by usage in examples/issues)

---

## Decision Recommendation

### ✅ **IMPLEMENT THIS FEATURE**

**Justification:**

1. **Addresses Critical Pain Point**
   - Multi-host operations are CORE to TASKER's purpose
   - Current 160+ line verbosity is unacceptable
   - 95% reduction in code volume is massive win

2. **Exceptional Value Proposition**
   - Benefit/cost ratio: ~50:1
   - Implementation: 15 hours (manageable)
   - Ongoing maintenance: Low (straightforward logic)

3. **Aligns with TASKER Philosophy**
   - "Simple things simple, complex things possible"
   - Currently simple thing (run on 20 servers) requires complex syntax
   - Feature makes simple thing simple

4. **Competitive Necessity**
   - Ansible makes multi-host concise
   - TASKER currently more verbose
   - Feature brings TASKER to competitive parity

5. **Leverages Existing Infrastructure**
   - Reuses parallel executor
   - Reuses statistics
   - Just syntactic sugar (~10% new code, 90% reuse)

6. **Low Risk, High Reward**
   - Backward compatible (zero breaking changes)
   - Clear requirements
   - Straightforward implementation
   - Comprehensive testing planned

7. **User Experience Transformation**
   - Eliminates copy-paste hell
   - Reduces errors dramatically
   - Saves 5-10 minutes per workflow
   - Makes TASKER more accessible

**Recommended Approach:** Option 2 (Extend `type=parallel` with `hostnames=`)

**Recommended Timeline:** 2 days implementation + testing + documentation

**Recommended Priority:** High - Core operational use case

---

## Next Steps (If Approved)

1. ✅ User reviews and approves this analysis
2. ⏸️ Create feature branch: `feature/parallel-hostnames-list`
3. ⏸️ Implement Phase 1: Parsing & Validation
4. ⏸️ Implement Phase 2: Subtask Generation
5. ⏸️ Implement Phase 3: Variable Handling (minimal)
6. ⏸️ Implement Phase 4: Comprehensive Testing
7. ⏸️ Implement Phase 5: Documentation Updates
8. ⏸️ Code Review
9. ⏸️ Merge to main
10. ⏸️ Update presentation materials to showcase new feature

---

## Appendix: Example Use Cases

### Use Case 1: Health Check Before Deployment

```bash
# Health check 50 web servers
task=0
type=parallel
hostnames=web01,web02,web03,...,web50
command=/usr/local/bin/health_check.sh
exec=local
max_parallel=20
timeout=30
success=min_success=45  # 90% must be healthy
on_success=10   # Proceed with deployment
on_failure=99   # Alert ops team

# Deploy if healthy
task=10
type=parallel
hostnames=web01,web02,web03,...,web50
command=/opt/deploy.sh
arguments=v2.1.0
exec=pbrun
max_parallel=5
on_success=50

# Success
task=50
hostname=localhost
command=echo
arguments=Deployment completed successfully
exec=local

# Alert on failure
task=99
hostname=localhost
command=/opt/alert_ops.sh
arguments=Deployment aborted: Health check failed
exec=local
return=1
```

**Benefit:** 400+ lines → 40 lines (90% reduction)

### Use Case 2: Log Collection from Database Cluster

```bash
# Collect slow query logs from 10 database replicas
task=0
type=parallel
hostnames=db-replica-01,db-replica-02,db-replica-03,db-replica-04,db-replica-05,db-replica-06,db-replica-07,db-replica-08,db-replica-09,db-replica-10
command=/opt/scripts/collect_slow_queries.sh
arguments=--last-hour
exec=pbrun
max_parallel=10
timeout=120
on_success=1

# Aggregate logs locally
task=1
hostname=localhost
command=/usr/local/bin/aggregate_slow_queries.py
exec=local
on_success=2

# Generate report
task=2
hostname=localhost
command=/usr/local/bin/generate_db_performance_report.py
exec=local
```

**Benefit:** 80+ lines → 30 lines (62% reduction)

### Use Case 3: Maintenance Window - Restart Services

```bash
# Restart application services across 30 servers
task=0
type=parallel
hostnames=app01,app02,app03,...,app30
command=/usr/local/bin/graceful_restart.sh
exec=pbrun
max_parallel=3  # Rolling restart, 3 at a time
timeout=300
retry_count=2
success=min_success=28  # Allow 2 failures
on_success=10
on_failure=99

# Success
task=10
hostname=localhost
command=echo
arguments=Rolling restart completed successfully
exec=local

# Failure
task=99
hostname=localhost
command=/opt/alert_ops.sh
arguments=Rolling restart failed on multiple servers
exec=local
return=1
```

**Benefit:** 240+ lines → 35 lines (85% reduction)

---

**Document Version:** 1.0
**Created:** 2025-11-02
**Author:** Analysis for TASKER Feature Request
**Status:** Awaiting User Decision
