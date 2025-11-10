# TASKER 2.1 Architecture Diagram

## 1. High-Level System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         TASKER 2.1 SYSTEM                               │
│                   Professional Task Automation Framework                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
        ┌───────────────────────────────────────────────────┐
        │           CLI Entry Point (tasker.py)             │
        │  • Argument parsing                               │
        │  • Mode selection (execute, validate, resume)     │
        │  • Global configuration                           │
        └───────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        VALIDATION LAYER                               │
│ ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│ │ InputSanitizer  │  │  TaskValidator   │  │   HostValidator      │ │
│ │ • Security      │  │  • Syntax check  │  │   • DNS resolution   │ │
│ │ • Injection     │  │  • Dependencies  │  │   • Connectivity     │ │
│ │ • Buffer limits │  │  • Logic errors  │  │   • SSH validation   │ │
│ └─────────────────┘  └──────────────────┘  └──────────────────────┘ │
└───────────────┬───────────────────────────────────────────────────────┘
                │ ✅ Validated Tasks
                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         CORE ENGINE LAYER                             │
│ ┌─────────────────────────────────────────────────────────────────┐  │
│ │             TaskExecutorMain (Orchestrator)                     │  │
│ │  • Workflow state management                                    │  │
│ │  • Task scheduling and routing                                  │  │
│ │  • Result collection                                            │  │
│ │  • Timeout management                                           │  │
│ │  • Shutdown handling                                            │  │
│ └──────────────┬──────────────────────────────────────────────────┘  │
│                │                                                       │
│  ┌─────────────┴─────────────┐                                        │
│  │                           │                                        │
│  ▼                           ▼                                        │
│ ┌──────────────────┐  ┌──────────────────────┐                       │
│ │ ConditionEvaluator│  │ StreamingOutputHandler│                      │
│ │ • @VAR@ replace  │  │ • Memory efficiency   │                      │
│ │ • Success eval   │  │ • 1MB threshold       │                      │
│ │ • Variable mask  │  │ • Temp file mgmt      │                      │
│ └──────────────────┘  └──────────────────────┘                       │
│                                                                        │
│ ┌──────────────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│ │  StateManager    │  │  WorkflowController  │  │  ResultCollector│ │
│ │ • Loop counters  │  │  • Execution flow    │  │  • Task results │ │
│ │ • Task state     │  │  • Resume support    │  │  • JSON output  │ │
│ │ • Recovery info  │  │  • Branch control    │  │  • Statistics   │ │
│ └──────────────────┘  └──────────────────────┘  └─────────────────┘ │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      EXECUTOR PATTERN LAYER                           │
│                                                                        │
│                    ┌──────────────────────┐                           │
│                    │   BaseExecutor       │                           │
│                    │  (Abstract Base)     │                           │
│                    └──────────┬───────────┘                           │
│                               │                                       │
│         ┌─────────────────────┼─────────────────────┐                │
│         │                     │                     │                │
│         ▼                     ▼                     ▼                │
│  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐    │
│  │ Sequential   │   │   Parallel       │   │  Conditional     │    │
│  │  Executor    │   │   Executor       │   │   Executor       │    │
│  │              │   │                  │   │                  │    │
│  │ • Normal     │   │ • ThreadPool     │   │ • if_true_tasks  │    │
│  │   flow       │   │ • max_parallel   │   │ • if_false_tasks │    │
│  │ • Loops      │   │ • Timeout mgmt   │   │ • Condition eval │    │
│  │ • Retry      │   │ • Cancellation   │   │                  │    │
│  └──────────────┘   └──────────────────┘   └──────────────────┘    │
│                                                                        │
│         ┌──────────────────┐                                          │
│         │  DecisionExecutor│                                          │
│         │                  │                                          │
│         │ • Multi-branch   │                                          │
│         │ • Complex logic  │                                          │
│         └──────────────────┘                                          │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      TASK RUNNER LAYER                                │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │                     TaskRunner                                   │ │
│ │  • Command construction                                          │ │
│ │  • Subprocess management (Popen)                                 │ │
│ │  • Output streaming                                              │ │
│ │  • Exit code collection                                          │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    EXECUTION TARGETS                                  │
│                                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  exec=local │  │ exec=shell  │  │ exec=pbrun  │  │ exec=p7s   │ │
│  │  (direct)   │  │ (sh -c)     │  │ (wrapper)   │  │ (wrapper)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

## 2. Data Flow Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                    │
└──────────────────────────────────────────────────────────────────────┘

  Task File (.txt)
       │
       ▼
  ┌─────────────────┐
  │  File Parser    │ ──────┐
  └─────────────────┘       │
       │                    │ Global Variables
       ▼                    │ (HOSTNAME=server1)
  ┌─────────────────┐       │
  │ InputSanitizer  │◄──────┘
  └─────────────────┘
       │ ✅ Safe Data
       ▼
  ┌─────────────────┐
  │ TaskValidator   │
  └─────────────────┘
       │ ✅ Valid Structure
       ▼
  ┌──────────────────────────────────────┐
  │      TaskExecutorMain                │
  │                                      │
  │  ┌────────────────────────────────┐ │
  │  │  Task Queue                    │ │
  │  │  [0, 1, 2, 3, ...]            │ │
  │  └────────────────────────────────┘ │
  └──────────┬───────────────────────────┘
             │
             ▼
  ┌────────────────────────┐
  │  Executor Selection    │
  │  • Sequential?         │
  │  • Parallel?           │
  │  • Conditional?        │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Variable Replacement  │
  │  @HOSTNAME@ → server1  │
  │  @0_stdout@ → data     │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Command Execution     │
  │  subprocess.Popen()    │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────────────────┐
  │  Output Streaming                  │
  │                                    │
  │  Size < 1MB?                       │
  │  ├─ YES → Memory Buffer            │
  │  └─ NO  → Temp File                │
  │            /tmp/tasker_stdout_XXX  │
  └────────┬───────────────────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Success Evaluation    │
  │  • exit_0              │
  │  • stdout~pattern      │
  │  • @VAR@=value         │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Result Storage        │
  │  task_results[N] = {   │
  │    exit_code: 0        │
  │    stdout: "data"      │
  │    stderr: ""          │
  │    success: True       │
  │    stdout_file: path   │
  │  }                     │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Flow Control          │
  │  • next=always         │
  │  • on_success=5        │
  │  • on_failure=10       │
  │  • loop=3              │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Final Report          │
  │  • JSON output         │
  │  • Statistics          │
  │  • Execution path      │
  │  • Performance metrics │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │  Cleanup Phase         │
  │  • Close file handles  │
  │  • Delete temp files   │
  │  • Free resources      │
  └────────────────────────┘
```

## 3. Cross-Task Variable Substitution Flow

```text
┌────────────────────────────────────────────────────────────────┐
│         CROSS-TASK DATA FLOW (PR #92)                          │
└────────────────────────────────────────────────────────────────┘

Task 0 Execution:
  ┌──────────────────────┐
  │  command: curl ...   │
  │  Output: 5MB data    │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │  StreamingOutputHandler      │
  │  Size check: 5MB > 1MB?      │
  │  └─ YES                      │
  │     ├─ Create temp file      │
  │     │  /tmp/tasker_stdout_XX │
  │     └─ Store path in result  │
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │  task_results[0] = {         │
  │    stdout: "5MB data"        │ ← Kept in memory temporarily
  │    stdout_file: "/tmp/..."  │ ← Path to temp file
  │    exit_code: 0              │
  │    success: True             │
  │  }                           │
  └──────────────────────────────┘

Task 1 Execution:
  ┌──────────────────────────────────┐
  │  command: process               │
  │  arguments: @0_stdout@          │ ← Variable to replace
  └──────────┬───────────────────────┘
             │
             ▼
  ┌──────────────────────────────────────┐
  │  ConditionEvaluator                  │
  │  replace_variables()                 │
  │                                      │
  │  @0_stdout@ found                    │
  │  ├─ Check stdout_file exists?        │
  │  │  └─ YES: /tmp/tasker_stdout_XX    │
  │  ├─ File size: 5MB                   │
  │  ├─ Read first 100KB (ARG_MAX safe) │ ← CRITICAL: Prevents errors
  │  └─ Substitute truncated data        │
  │                                      │
  │  WARNING: Large output truncated     │
  │  Use @0_stdout_file@ for full data   │
  └──────────┬───────────────────────────┘
             │
             ▼
  ┌──────────────────────────────────┐
  │  Final Command:                  │
  │  process [100KB data]            │ ← Safe for exec
  └──────────────────────────────────┘

Alternative: Full File Access
  ┌──────────────────────────────────┐
  │  command: process               │
  │  arguments: @0_stdout_file@     │ ← Request file path
  └──────────┬───────────────────────┘
             │
             ▼
  ┌──────────────────────────────────┐
  │  Substitution:                   │
  │  @0_stdout_file@ →               │
  │  /tmp/tasker_stdout_XX           │
  │                                  │
  │  Final Command:                  │
  │  process /tmp/tasker_stdout_XX   │ ← Full data accessible
  └──────────────────────────────────┘

Cleanup (Workflow End):
  ┌──────────────────────────────────┐
  │  Phase 3: Temp File Cleanup      │
  │  ├─ Find all /tmp/tasker_*       │
  │  ├─ Close file descriptors       │
  │  └─ Unlink temp files            │
  └──────────────────────────────────┘
```

## 4. Module Dependency Graph

```text
┌────────────────────────────────────────────────────────────────┐
│                    MODULE DEPENDENCIES                         │
└────────────────────────────────────────────────────────────────┘

tasker.py (CLI Entry Point)
    │
    ├─→ tasker/validation/
    │       ├─→ input_sanitizer.py
    │       ├─→ task_validator.py
    │       └─→ host_validator.py
    │
    └─→ tasker/core/
            ├─→ task_executor_main.py
            │       ├─→ condition_evaluator.py
            │       │       └─→ constants.py
            │       │       └─→ utilities.py
            │       │
            │       ├─→ streaming_output_handler.py
            │       │
            │       ├─→ state_manager.py
            │       ├─→ workflow_controller.py
            │       ├─→ result_collector.py
            │       └─→ task_runner.py
            │
            └─→ executors/
                    ├─→ base_executor.py
                    ├─→ sequential_executor.py
                    │       ├─→ conditional_executor.py
                    │       ├─→ parallel_executor.py
                    │       └─→ decision_executor.py
                    │
                    └─→ All executors depend on:
                            ├─→ condition_evaluator.py
                            ├─→ streaming_output_handler.py
                            └─→ utilities.py

tasker/utils/
    └─→ non_blocking_sleep.py (standalone utility)

TASKER Main Application (tasker.py): NONE (Standard library only)
    ✅ subprocess
    ✅ threading
    ✅ tempfile
    ✅ json
    ✅ re (regex)

Note: Test infrastructure & utilities may use third-party packages
      (e.g., psutil for performance monitoring in test runners)
```

## 5. Execution Strategy Pattern

```text
┌────────────────────────────────────────────────────────────────┐
│              EXECUTOR PATTERN ARCHITECTURE                     │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    BaseExecutor                             │
│                   (Abstract Base)                           │
│                                                             │
│  + execute_task(task, executor_instance)                   │
│  + _check_shutdown()                                        │
│  + store_task_result()                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┼───────────┬─────────────┐
          │           │           │             │
          ▼           ▼           ▼             ▼
┌──────────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│ Sequential   │ │Parallel │ │Conditional│ │Decision  │
│  Executor    │ │Executor │ │ Executor  │ │Executor  │
└──────────────┘ └─────────┘ └──────────┘ └──────────┘
      │               │            │             │
      │               │            │             │
      ▼               ▼            ▼             ▼

Normal Flow:     ThreadPool:   If/Else:     Multi-branch:
  Task 0           Task 0        Task 0       Task 0 (decision)
    ↓              Task 1        ├─ TRUE      ├─ Branch A
  Task 1           Task 2        │  Task 1    │  Tasks 1,2,3
    ↓              Task 3        │    ↓       ├─ Branch B
  Task 2           (parallel)    │  Task 2    │  Tasks 4,5,6
    ↓              ↓              │            └─ Fallback
  Task 3           Wait all      └─ FALSE        Tasks 7,8
    ↓              Task 4           Task 3
  Task 4             ↓
                   Task 5
```

## 6. Security Validation Pipeline

```text
┌────────────────────────────────────────────────────────────────┐
│              SECURITY VALIDATION PIPELINE                      │
└────────────────────────────────────────────────────────────────┘

User Input (task.txt)
    │
    ▼
┌─────────────────────────────────────┐
│  Layer 1: Input Sanitizer          │
│  ✓ Null byte detection              │
│  ✓ Length validation (field limits) │
│  ✓ Type coercion safety             │
└─────────────┬───────────────────────┘
              │ ✅ Sanitized
              ▼
┌─────────────────────────────────────┐
│  Layer 2: Field-Specific Validation │
│  ✓ Hostname format                  │
│  ✓ Command structure                │
│  ✓ Arguments safety                 │
│  ✓ Numeric ranges                   │
└─────────────┬───────────────────────┘
              │ ✅ Valid Format
              ▼
┌─────────────────────────────────────┐
│  Layer 3: Security Pattern Detection│
│  ✓ Command injection (11 patterns) │
│  ✓ Path traversal (12 patterns)    │
│  ✓ Format string attacks            │
│  ✓ Buffer overflow attempts         │
│  ✓ Encoding obfuscation             │
└─────────────┬───────────────────────┘
              │ ✅ No Threats
              ▼
┌─────────────────────────────────────┐
│  Layer 4: Context-Aware Rules       │
│  exec=local?                        │
│  ├─ YES: Strict (no shell syntax)   │
│  └─ NO:  Permissive (shell allowed) │
└─────────────┬───────────────────────┘
              │ ✅ Context Valid
              ▼
┌─────────────────────────────────────┐
│  Layer 5: Task Structure Validation │
│  ✓ Field count limits               │
│  ✓ Privilege escalation detection   │
│  ✓ Suspicious combinations          │
└─────────────┬───────────────────────┘
              │ ✅ Structure Safe
              ▼
         Safe for Execution
```

## 7. Test Infrastructure Architecture

```text
┌────────────────────────────────────────────────────────────────┐
│           TEST INFRASTRUCTURE (465 tests)                      │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  intelligent_test_runner.py (Orchestrator)                  │
│  • Metadata parsing                                         │
│  • Test discovery (10 categories)                           │
│  • Parallel execution                                       │
│  • Result aggregation                                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│              TEST METADATA VALIDATION                        │
│                                                              │
│  TEST_METADATA: {                                           │
│    "expected_exit_code": 0,           ← Exit code match     │
│    "expected_execution_path": [0,1,2] ← Flow validation     │
│    "expected_variables": {...}        ← Variable resolution │
│    "expected_success": true           ← Success criteria    │
│  }                                                           │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│              TEST CATEGORIES (10)                            │
│                                                              │
│  functional/      (~180) Basic features                     │
│  integration/     (~80)  End-to-end workflows               │
│  edge_cases/      (~60)  Boundary conditions                │
│  security/        (~40)  Security validation                │
│  streaming/       (~25)  Cross-task data flow               │
│  output_json/     (~15)  JSON output validation             │
│  performance/     (~10)  Timing tests                       │
│  recovery/        (~10)  Failure recovery                   │
│  resume/          (~10)  Workflow resumption                │
│  readme_examples/ (~35)  Documentation examples             │
│                                                              │
│  (Total: 465 tests ✓)                                       │
│  Note: templates/ contains test templates, not test cases   │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│              MOCK INFRASTRUCTURE                             │
│                                                              │
│  test_cases/bin/                                            │
│  ├─ pbrun                (execution wrapper)                │
│  ├─ p7s                  (execution wrapper)                │
│  ├─ wwrs_clir            (execution wrapper)                │
│  ├─ verify_cleanup_wrapper.sh  (temp file verification)    │
│  ├─ verify_temp_cleanup.py     (Python cleanup verification)│
│  ├─ retry_controller.sh   (retry testing)                  │
│  └─ recovery_helper.sh    (recovery testing)               │
└──────────────────────────────────────────────────────────────┘
```

## 8. Memory Management Strategy

```text
┌────────────────────────────────────────────────────────────────┐
│           MEMORY-EFFICIENT OUTPUT HANDLING                     │
└────────────────────────────────────────────────────────────────┘

Task Output Size:
    │
    ▼
┌─────────────────────┐
│  Size < 1MB?        │
└──┬──────────────┬───┘
   │ YES          │ NO
   ▼              ▼
┌──────────┐  ┌─────────────────────────┐
│ Memory   │  │  Temp File Strategy     │
│ Buffer   │  │  ┌────────────────────┐ │
│          │  │  │ 1. Create temp file│ │
│ O(n)     │  │  │ 2. Write data      │ │
│ memory   │  │  │ 3. Store path      │ │
│          │  │  │ 4. Free memory     │ │
│          │  │  └────────────────────┘ │
│          │  │                         │
│          │  │  Memory Usage: O(1)     │
└────┬─────┘  └────────┬────────────────┘
     │                 │
     └────────┬────────┘
              ▼
    ┌──────────────────────┐
    │  Result Storage      │
    │  ┌────────────────┐  │
    │  │ stdout         │  │ ← Full content (if <1MB)
    │  │ stdout_file    │  │ ← Path (if ≥1MB)
    │  │ stderr         │  │
    │  │ stderr_file    │  │
    │  │ exit_code      │  │
    │  │ success        │  │
    │  └────────────────┘  │
    └──────────────────────┘

Command-line Substitution:
    │
    ▼
┌─────────────────────────┐
│  @N_stdout@ requested   │
└──────────┬──────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Check file size             │
│  Size > 100KB?               │
└──┬───────────────────────┬───┘
   │ NO                    │ YES
   ▼                       ▼
┌──────────┐        ┌──────────────────────┐
│ Full     │        │ Truncate to 100KB    │
│ content  │        │ (ARG_MAX protection) │
└──────────┘        └──────────────────────┘
```

---

## Summary

**TASKER 2.1 Architecture Highlights**:

1. **Layered Design**: Clear separation (Validation → Core → Execution → Target)
2. **Executor Pattern**: Pluggable strategies (4 execution strategies)
3. **Security-First**: Multi-layer validation with defense-in-depth
4. **Memory Efficient**: O(1) memory for unlimited output sizes (1MB threshold)
5. **Cross-Task Data**: Sophisticated variable substitution with ARG_MAX protection
6. **Test Infrastructure**: Metadata-driven validation (465/465 tests passing)
7. **No External Dependencies**: Pure Python 3.6.8 standard library

**Key Design Patterns**:

- ✅ Strategy Pattern (Executors)
- ✅ Template Method (BaseExecutor)
- ✅ Singleton (Constants)
- ✅ Factory (create_memory_efficient_handler)
- ✅ Context Manager (StreamingOutputHandler)
