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
│ │ • Buffer limits │  │  • Logic errors  │  │   • Validation tests │ │
│ └─────────────────┘  └──────────────────┘  └──────────┬───────────┘ │
│                                                        │             │
│ ┌──────────────────────────────────────────────────────┘             │
│ │                                                                    │
│ │  ┌────────────────────────────────────────────────────────────┐   │
│ │  │           ExecConfigLoader (Singleton)                     │   │
│ │  │  • Load cfg/execution_types.yaml                           │   │
│ │  │  • Platform detection (Linux/Windows)                      │   │
│ │  │  • Execution type definitions                              │   │
│ │  │  • Validation test configuration                           │   │
│ │  └────────────────────────────────────────────────────────────┘   │
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
│  ┌─────────────┐  ┌──────────────────────────────────────────────┐  │
│  │  exec=local │  │    Config-based Execution Types              │  │
│  │  (direct)   │  │    (loaded from cfg/execution_types.yaml)    │  │
│  │  hardcoded  │  │                                              │  │
│  └─────────────┘  │  ┌─────────────┐  ┌─────────────┐           │  │
│                   │  │ exec=shell  │  │ exec=pbrun  │           │  │
│                   │  │ (sh -c)     │  │ (wrapper)   │           │  │
│                   │  └─────────────┘  └─────────────┘           │  │
│                   │                                              │  │
│                   │  ┌─────────────┐  ┌─────────────┐           │  │
│                   │  │ exec=p7s    │  │ exec=wwrs   │           │  │
│                   │  │ (wrapper)   │  │ (wrapper)   │           │  │
│                   │  └─────────────┘  └─────────────┘           │  │
│                   │                                              │  │
│                   │  + Custom types via YAML config              │  │
│                   └──────────────────────────────────────────────┘  │
│                                                                       │
│  Note: Only exec=local is hardcoded. All other execution types are   │
│        loaded dynamically from cfg/execution_types.yaml (PR#96)      │
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
  │     ├─ Stream data to file   │
  │     ├─ Release memory buffer │ ← Frees memory immediately
  │     └─ Store path in result  │
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │  task_results[0] = {         │
  │    stdout: ""                │ ← Empty (memory freed)
  │    stdout_file: "/tmp/..."  │ ← Path for file-based access
  │    exit_code: 0              │
  │    success: True             │
  │  }                           │
  │                              │
  │  Note: For outputs < 1MB:    │
  │    stdout: "small data"      │ ← Kept in memory
  │    stdout_file: None         │ ← No temp file needed
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
    ├─→ cfg/
    │       └─→ execution_types.yaml (Platform-specific execution configs)
    │
    ├─→ tasker/config/
    │       └─→ exec_config_loader.py (Singleton, loads YAML config)
    │
    ├─→ tasker/validation/
    │       ├─→ input_sanitizer.py
    │       ├─→ task_validator.py
    │       └─→ host_validator.py
    │               └─→ Uses ExecConfigLoader for validation tests
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

## 5. Config-Based Execution Type System (PR#96)

```text
┌────────────────────────────────────────────────────────────────┐
│         CONFIG-BASED EXECUTION TYPE ARCHITECTURE               │
└────────────────────────────────────────────────────────────────┘

Initialization (tasker.py startup):
    │
    ▼
┌─────────────────────────────────────┐
│  ExecConfigLoader (Singleton)       │
│  ├─ Detect platform (Linux/Windows) │
│  ├─ Resolve script directory        │
│  ├─ Load cfg/execution_types.yaml   │
│  └─ Parse platform-specific configs │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Configuration Structure (YAML)                             │
│                                                             │
│  platforms:                                                 │
│    linux:                                                   │
│      shell:                                                 │
│        description: "Local shell execution with Bash"       │
│        binary: /bin/bash                                    │
│        command_template:                                    │
│          - "{binary}"                                       │
│          - "-c"                                             │
│          - "{command} {arguments}"                          │
│        validation_test:                                     │
│          command: echo                                      │
│          arguments: OK          ← Optional (PR#97)          │
│          expected_exit: 0                                   │
│          expected_output: "OK"                              │
│                                                             │
│      pbrun:                                                 │
│        description: "PowerBroker Run privilege escalation"  │
│        binary: /usr/local/bin/pbrun                         │
│        command_template:                                    │
│          - "{binary}"                                       │
│          - "-h"                                             │
│          - "{hostname}"                                     │
│          - "{command}"                                      │
│          - "{arguments_split}"                              │
│        validation_test:                                     │
│          command: echo                                      │
│          arguments: "test"      ← Optional (PR#97)          │
│          expected_exit: 0                                   │
│          expected_output: "test"                            │
└─────────────────────────────────────────────────────────────┘

Template Variable Substitution:
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Available Template Variables:                              │
│  • {binary}          → Execution binary path                │
│  • {hostname}        → Target hostname                      │
│  • {command}         → Command to execute                   │
│  • {arguments}       → Full arguments string                │
│  • {arguments_split} → Arguments split into list elements   │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Example Transformation:                                    │
│                                                             │
│  Task Definition:                                           │
│    hostname=server1                                         │
│    command=cat                                              │
│    arguments=/etc/hosts                                     │
│    exec=pbrun                                               │
│                                                             │
│  Template: ["{binary}", "-h", "{hostname}",                 │
│             "{command}", "{arguments_split}"]               │
│                                                             │
│  Final Command:                                             │
│    ["/usr/local/bin/pbrun", "-h", "server1",                │
│     "cat", "/etc/hosts"]                                    │
└─────────────────────────────────────────────────────────────┘

Validation Test Execution (PR#97):
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  HostValidator Integration                                  │
│  ├─ For each unique (hostname, exec_type) combination       │
│  ├─ Load validation_test from config                        │
│  ├─ Build command using template + test command/arguments   │
│  ├─ Execute test command on target host                     │
│  ├─ Validate: expected_exit AND/OR expected_output          │
│  └─ Report: SUCCESS or FAILURE                              │
│                                                             │
│  Requirements (PR#97):                                      │
│  • At least ONE of expected_exit or expected_output         │
│  • Optional arguments field for parameterized tests         │
│  • Automatic execution during --validate or --validate-only │
└─────────────────────────────────────────────────────────────┘

Error Handling:
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Graceful Degradation                                       │
│  ├─ Config file missing    → Fall back to exec=local only   │
│  ├─ Config file corrupt    → Error + fall back to local     │
│  ├─ Undefined exec type    → Error: "Unknown exec type"     │
│  ├─ Invalid template vars  → Error: "Invalid template"      │
│  └─ Validation test fails  → Warning: "Connectivity issue"  │
└─────────────────────────────────────────────────────────────┘

Benefits:
  ✅ Extensibility: Add custom exec types without code changes
  ✅ Platform support: Different configs for Linux/Windows
  ✅ Centralized: Single source of truth for execution commands
  ✅ Validated: Automatic connectivity testing per host/exec_type
  ✅ Flexible: Template-based command construction
  ✅ Maintainable: YAML configuration instead of hardcoded logic
```

## 6. Execution Strategy Pattern

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

## 7. Security Validation Pipeline

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

## 8. Test Infrastructure Architecture

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

## 9. Memory Management Strategy

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
2. **Config-Based Execution**: External YAML configuration for execution types (PR#96, PR#97)
3. **Executor Pattern**: Pluggable strategies (4 execution strategies)
4. **Security-First**: Multi-layer validation with defense-in-depth
5. **Memory Efficient**: O(1) memory for unlimited output sizes (1MB threshold)
6. **Cross-Task Data**: Sophisticated variable substitution with ARG_MAX protection
7. **Test Infrastructure**: Metadata-driven validation (465/465 tests passing)
8. **No External Dependencies**: Pure Python 3.6.8 standard library

**Key Design Patterns** (with rationale):

- ✅ **Strategy Pattern** (Executors)
  - *Why*: Support multiple execution modes (Sequential, Parallel, Conditional,
    Decision) without conditional branching in core logic
  - *Benefit*: Easy addition of new execution strategies without modifying
    existing code

- ✅ **Template Method** (BaseExecutor)
  - *Why*: Define common execution workflow while allowing subclasses to
    customize specific steps
  - *Benefit*: Ensures consistent behavior (validation, timeout handling,
    result collection)

- ✅ **Singleton** (Constants, ExecConfigLoader)
  - *Why*: Centralize magic numbers and thresholds (MAX_CMDLINE_SUBST,
    MAX_VARIABLE_EXPANSION_DEPTH); Load execution type config once at startup
  - *Benefit*: Single source of truth, prevents duplication and inconsistency;
    Efficient config loading with callback updates for dynamic changes

- ✅ **Factory** (create_memory_efficient_handler)
  - *Why*: Encapsulate complex object creation logic for streaming handlers
  - *Benefit*: Hides implementation details, simplifies client code

- ✅ **Context Manager** (StreamingOutputHandler)
  - *Why*: Guarantee proper resource cleanup (temp files, file descriptors)
    even on exceptions
  - *Benefit*: Prevents resource leaks in production, automatic cleanup
