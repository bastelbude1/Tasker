# Tasker Refactoring Plan

## Overview
This document outlines the planned refactoring of the tasker.py module into a well-structured package to improve maintainability, modularity, and code organization.

## Current State
- Single monolithic `tasker.py` file (~3000+ lines)
- All functionality mixed together in one large TaskExecutor class
- Difficult to maintain and extend

## Target Package Structure

```
./
├── tasker.py                    # Main script (executable, NOT a module)
├── task_validator.py            # Existing script (remains unchanged)
│
tasker/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── condition_evaluator.py   # Variable replacement & condition logic
│   ├── utilities.py             # Standalone utility functions ✅ COMPLETED
│   └── task_executor_main.py    # Main class with Lifecycle, Logging, Validation
│
├── executors/
│   ├── __init__.py
│   ├── base_executor.py         # Abstract base class for all executors
│   ├── sequential_executor.py   # Normal task execution
│   ├── parallel_executor.py     # Parallel task execution + retry logic
│   └── conditional_executor.py  # Conditional task execution
│
└── validation/
    ├── __init__.py
    ├── task_validator_integration.py  # TaskValidator integration
    └── host_validator.py         # Host validation logic
```

## Module Responsibilities

### `core/` - Fundamental Services
- **`utilities.py`** ✅ **COMPLETED**
  - Standalone utility functions
  - Exit code management (`ExitCodes`, `ExitHandler`)
  - Value conversion functions (`convert_value`, `convert_to_number`)
  - String formatting utilities (`sanitize_filename`, `sanitize_for_tsv`)
  - Log directory management (`get_log_directory`)

- **`condition_evaluator.py`** 🔄 **NEXT**
  - Variable replacement using `@VARIABLE@` syntax
  - Condition evaluation logic
  - Expression parsing and comparison operators

- **`task_executor_main.py`** 🔄 **PLANNED**
  - Main TaskExecutor class with lifecycle management
  - Logging infrastructure
  - Task result storage and management
  - Signal handling
  - Configuration management

### `executors/` - Task Execution Engines
- **`base_executor.py`** 🔄 **PLANNED**
  - Abstract base class for all executors
  - Common execution interface
  - Shared execution utilities

- **`sequential_executor.py`** 🔄 **PLANNED**
  - Normal sequential task execution
  - Single task processing logic
  - Standard retry mechanisms

- **`parallel_executor.py`** 🔄 **PLANNED**
  - Parallel task execution with threading
  - Master timeout enforcement
  - Advanced retry logic for failed tasks
  - Result aggregation and success/failure thresholds

- **`conditional_executor.py`** 🔄 **PLANNED**
  - Conditional task execution based on conditions
  - Branch selection logic
  - Conditional flow control

### `validation/` - Validation Logic
- **`task_validator_integration.py`** 🔄 **PLANNED**
  - Integration with existing TaskValidator
  - Task file syntax validation
  - Dependency validation

- **`host_validator.py`** 🔄 **PLANNED**
  - Host connectivity validation
  - DNS resolution (`resolve_hostname`)
  - Connection testing (`check_host_alive`, `check_exec_connection`)

## Refactoring Progress

### ✅ Phase 1: Core Utilities (COMPLETED)
- [x] Created `tasker/core/utilities.py`
- [x] Moved `ExitCodes` and `ExitHandler` classes
- [x] Moved `convert_value`, `convert_to_number`, `sanitize_for_tsv` functions
- [x] Updated imports and exports
- [x] Committed to git (commit: 5f3b643)

### 🔄 Phase 2: Condition Evaluation (NEXT)
- [ ] Create `tasker/core/condition_evaluator.py`
- [ ] Extract condition evaluation methods:
  - `replace_variables()`
  - `evaluate_condition()`
  - `evaluate_simple_condition()`
  - `evaluate_operator_comparison()`
  - `split_output()`

### 🔄 Phase 3: Host Validation
- [ ] Create `tasker/validation/host_validator.py`
- [ ] Extract host validation methods:
  - `resolve_hostname()`
  - `check_host_alive()`
  - `check_exec_connection()`
  - `validate_hosts()`

### 🔄 Phase 4: Task Validation Integration
- [ ] Create `tasker/validation/task_validator_integration.py`
- [ ] Extract validation methods:
  - `validate_tasks()`
  - `validate_task_dependencies()`
  - `validate_start_from_task()`

### 🔄 Phase 5: Execution Engines
- [ ] Create base executor class
- [ ] Extract sequential execution logic
- [ ] Extract parallel execution logic
- [ ] Extract conditional execution logic

### 🔄 Phase 6: Main Executor Refactoring
- [ ] Create `tasker/core/task_executor_main.py`
- [ ] Refactor main TaskExecutor class
- [ ] Update `tasker.py` to use new modular structure

## Design Principles

1. **Single Responsibility**: Each module has a clear, focused purpose
2. **Loose Coupling**: Modules interact through well-defined interfaces
3. **High Cohesion**: Related functionality is grouped together
4. **Backwards Compatibility**: Existing functionality must be preserved
5. **Testability**: Each module should be independently testable

## Migration Strategy

- Refactor incrementally, one module at a time
- Maintain full functionality at each step
- Test thoroughly after each phase
- Update imports and dependencies as modules are created
- Preserve all existing command-line interfaces and behavior

## Files to be Kept Unchanged

- `tasker.py` - Main executable script (structure changes only)
- `task_validator.py` - Existing validation script
- All test cases and configuration files

## Success Criteria

- All existing functionality preserved
- Improved code maintainability and readability
- Clear separation of concerns
- Easier unit testing and debugging
- Foundation for future feature development