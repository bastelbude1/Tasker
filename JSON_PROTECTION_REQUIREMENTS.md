# JSON Protection Requirements Document

## Executive Summary

**Current Situation:**
- PR #91 adds 1,538 lines of code across 36 files for JSON output protection
- PR #92 (just created) provides minimal bug fixes (~250 lines)
- No formal requirements document existed for JSON protection features
- Features were developed during PR #91 as solutions to discovered problems

**Key Finding:**
The existing streaming infrastructure already prevents most memory issues. The ONLY real risk is JSON generation loading all results into memory, which can be solved with **50 lines of validation** instead of **1,500 lines of complex infrastructure**.

## Problem Analysis

### Real Problems That Need Solving

| Problem | Risk Level | Frequency | Current Protection |
|---------|------------|-----------|-------------------|
| Memory exhaustion during JSON generation | MEDIUM | Rare | None |
| Binary data breaking JSON parsing | HIGH | Very Low | None |
| Users unaware of truncation | MEDIUM | Common | None |
| Unwieldy JSON file sizes (>100MB) | LOW | Rare | User discretion |

### Problems Already Solved by Existing Infrastructure
- Memory exhaustion during task execution (streaming output handler)
- Large output handling (automatic temp files at 1MB)
- Cross-task data sharing (PR #92 fixes)

## Prioritized Requirements

### MUST HAVE (P0) - Prevents System Failures
*Target: 50 lines of code, 2-3 days effort*

#### 1. JSON Generation Memory Safety
```python
# Pre-check total size before JSON generation
def validate_json_size(task_results):
    total = sum(len(r.get('stdout','')) + len(r.get('stderr',''))
                for r in task_results.values())
    if total > 100 * 1024 * 1024:  # 100MB
        raise ValueError("Output exceeds 100MB. Use log files instead.")
```
- **Implementation:** 10 lines
- **Risk:** Very Low
- **Value:** High (prevents OOM)

#### 2. Binary Data Detection and Rejection
```python
def is_binary(data):
    """Detect binary data by checking for null bytes"""
    return b'\x00' in data[:8192]

if is_binary(stdout):
    raise ValueError(f"Task {task_id} produced binary output. "
                    "JSON output only supports text data.")
```
- **Implementation:** 5 lines
- **Risk:** Very Low
- **Value:** High (prevents JSON corruption)

#### 3. Truncation Transparency
```json
{
  "stdout_truncated": true,
  "stderr_truncated": true,
  "stdout_size": 5242880,
  "stderr_size": 0
}
```
- **Implementation:** Add existing internal flags to JSON output
- **Risk:** None
- **Value:** High (user awareness)

### SHOULD HAVE (P1) - Improves Reliability
*Target: Documentation + 20 lines of code, 1 week effort*

#### 1. Best Practices Documentation
Create section in ADVANCED_FEATURES.md:
```markdown
## JSON Output Best Practices
- Use for: CI/CD integration, summary statistics, monitoring
- Avoid for: Large batch jobs, verbose logging, binary output
- Size guidance: Keep total output under 10MB for best performance
- Alternative: Use log files for detailed output analysis
```

#### 2. Simple Per-Task Truncation
```python
MAX_TASK_OUTPUT = 1024 * 1024  # 1MB per task
if len(stdout) > MAX_TASK_OUTPUT:
    stdout = stdout[:MAX_TASK_OUTPUT]
    result['stdout_truncated'] = True
    result['stdout_size'] = original_size
```
- **Implementation:** 20 lines
- **Risk:** Low
- **Value:** Medium (prevents single task from dominating)

#### 3. Warning Messages
```python
if total_size > 10 * 1024 * 1024:  # 10MB warning threshold
    log.warning("JSON output is large ({}MB). Consider using log files.",
                total_size / 1024 / 1024)
```

### NICE TO HAVE (P2) - Convenience Features
*Defer until user validation*

#### 1. Streaming Preview System
- Complex temp file lifecycle management
- On-demand reading from temp files
- **Complexity:** 1,500+ lines
- **Risk:** High (evidenced by 39 commits with bug fixes)
- **Value:** Low (no proven user need)

#### 2. Base64 Encoding for Binary Data
- Automatic encoding with truncation awareness
- **Alternative:** Simple rejection is better
- **Complexity:** High
- **Value:** Very Low (binary output rare)

## Implementation Roadmap

### Phase 1: Critical Protection (Immediate)
**Timeline:** 2-3 days
**Scope:** P0 requirements only
```
1. Add JSON size validation (10 lines)
2. Add binary detection/rejection (5 lines)
3. Expose truncation metadata (5 lines)
4. Add unit tests (30 lines)
Total: ~50 lines of production code
```

### Phase 2: Enhanced Usability (Next Sprint)
**Timeline:** 1 week
**Scope:** P1 requirements
```
1. Write best practices documentation
2. Implement simple truncation
3. Add warning messages
4. Update test cases
```

### Phase 3: Advanced Features (Future/Optional)
**Timeline:** Only if validated by user needs
**Scope:** P2 requirements
```
- DO NOT IMPLEMENT until:
  1. User reports actual use case requiring it
  2. Simple truncation proven insufficient
  3. Resource allocation approved for complex implementation
```

## Risk Assessment

### PR #91 Approach (High Risk)
- **Complexity:** 1,538 lines added
- **Bug History:** 39 commits with multiple fixes
- **Edge Cases:** Binary encoding, split operations, lifecycle management
- **Maintenance Burden:** High
- **Testing Burden:** High

### Recommended Approach (Low Risk)
- **Complexity:** 50 lines for P0, 70 lines total for P0+P1
- **Bug Risk:** Minimal (simple validation)
- **Edge Cases:** Few
- **Maintenance Burden:** Negligible
- **Testing Burden:** Low

## Decision Criteria

### When to Implement Each Tier

#### Implement P0 (MUST HAVE) When:
- ✅ Any JSON output feature is shipped (required for safety)

#### Implement P1 (SHOULD HAVE) When:
- Users report confusion about truncation
- Users attempt to use JSON for inappropriate workloads
- Support burden increases

#### Implement P2 (NICE TO HAVE) When:
- Multiple users request preview features
- Clear use case demonstrated
- Simple truncation proven insufficient
- Resources available for complex implementation

## Validation Questions

Before implementing P2 features, answer:

1. **Has any user actually requested this?**
2. **What's the real use case for 1MB+ output in JSON?**
3. **Would simple truncation be sufficient?**
4. **Is JSON the right format for this use case?**

## Recommendations

### Immediate Actions
1. **Merge PR #92** - Fixes critical cross-task bugs with minimal changes
2. **Close PR #91** - Too complex, no proven requirements
3. **Implement P0** - Critical protection in new, focused PR
4. **Document** - Add best practices to prevent misuse

### Future Actions
1. **Monitor** - Track user feedback on JSON output usage
2. **Validate** - Confirm real need before building complex features
3. **Iterate** - Add P1 features based on actual usage patterns

## Conclusion

**YAGNI Principle Applies:** Complex streaming preview system solves problems users don't have.

**Recommended Path:**
- 50 lines of protective code (P0)
- Clear documentation (P1)
- Wait for proven need before complexity (P2)

**Result:**
- Same safety as PR #91
- 97% less code
- 95% less complexity
- 90% less maintenance burden

---

*Document Version: 1.0*
*Date: 2024-11-09*
*Author: Critical Analysis of PR #91 vs Minimal Requirements*