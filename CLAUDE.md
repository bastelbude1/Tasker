# Tasker Refactoring Plan

## Claude Code Instructions

### Working Methodology
- **Break down large tasks** into smaller, manageable sub-steps
- **Ask clarifying questions** when requirements are unclear or ambiguous
- **Think step-by-step** and explain reasoning for complex problems
- **Propose solution approaches** and ask for approval before implementation
- **Use concrete examples** to demonstrate solution approaches with pros and cons
- **Explain the thought process** in feedback and highlight problems and opportunities
- **Consult the knowledge repository** (this CLAUDE.md file) regularly to consider all information

### Code Quality Guidelines
- **NO inline comments** when creating test cases
- **Use ASCII-safe character set only** (avoid special Unicode characters)
- Maintain existing code style and conventions
- Preserve all existing functionality during refactoring
- Test thoroughly after each change

### Communication Style
- Provide detailed explanations of reasoning
- Present multiple solution options when applicable
- Highlight potential risks and benefits
- Ask for confirmation on major architectural decisions
- Document decisions and rationale

## Project Specification

### TASK ExecutoR - TASKER 2.0

**TASKER** is a simplified, robust task execution system that focuses on essential functionality with clean configuration management based on Python 3.6.8.

#### Design Philosophy
- **Simplicity over complexity**: Proven mechanisms only
- **Text format first**: Human-readable, version-control friendly
- **Configuration-driven**: Sensible defaults, easy customization
- **Scale-ready**: 1-1000 servers with @HOSTNAME@ placeholders
- **Safety-first**: Comprehensive validation and error handling

#### File Format Specification

**Required Fields:**
- `task`: Integer ID (0, 1, 2, ...)
- `hostname`: Target server or @HOSTNAME@ placeholder
- `command`: Command to execute

**Optional Fields:**
- `arguments`: Command arguments
- `exec`: Execution type (pbrun, p7s, local, wwrs)
- `timeout`: Command timeout in seconds (5-3600)
- `sleep`: Sleep after task execution (0-300 seconds)
- `condition`: Pre-execution condition
- `success`: Custom success criteria
- `next`: Flow control condition
- `on_success`: Task ID to execute on success
- `on_failure`: Task ID to execute on failure
- `loop`: Number of additional iterations
- `return`: Exit workflow with return code

#### Dependencies
**Required:**
- Python 3.6.8 or higher
- Standard library modules only (no external dependencies)

#### Success Criteria

**Functional Requirements:**
- Execute workflows reliably across 1-1000 servers
- Support all essential TASKER features
- Generate detailed logs and reports

**Quality Requirements:**
- 95%+ test coverage
- Sub-second startup time
- Memory usage < 50MB for typical workflows
- Compatible with Python 3.6.8+
- Clear error messages and documentation

**User Experience Requirements:**
- Simple installation (single script)
- Intuitive command line interface
- Helpful validation messages
- Comprehensive documentation

## Refactoring Overview
This document outlines the planned refactoring of the tasker.py module into a well-structured package to improve maintainability, modularity, and code organization while maintaining all TASKER 2.0 requirements.

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