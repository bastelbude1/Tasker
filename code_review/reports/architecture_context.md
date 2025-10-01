# TASKER Architecture Review Context

## Architecture Overview
TASKER 2.0 uses a modular architecture with the Executor pattern for task processing.

## Key Architectural Patterns
1. **Executor Pattern**: Separate executors for sequential and parallel task processing
2. **Callback Architecture**: Logging and debugging via callback functions
3. **Validation Layer**: Separate task validation logic
4. **Condition Evaluation**: Centralized success/failure condition processing
5. **Modular Design**: Clear separation of concerns across modules

## Module Structure
```
tasker/
├── core/              # Core execution logic
│   ├── task_executor_main.py
│   ├── condition_evaluator.py
│   └── timeout_manager.py
├── executors/         # Task execution strategies
│   ├── base_executor.py
│   ├── sequential_executor.py
│   └── parallel_executor.py
├── validation/        # Input validation
│   └── task_validator.py
└── utils/            # Utility functions
    └── format_utils.py
```

## Architecture Principles
- **Single Responsibility**: Each module has one clear purpose
- **Open/Closed**: Extensible via new executors without modification
- **Dependency Inversion**: Main logic depends on abstractions (callbacks)
- **Interface Segregation**: Clean interfaces between modules
- **DRY**: Shared functionality in base classes and utilities

## Critical Interfaces
- **Executor Interface**: Base class with execute() method
- **Callback Interface**: log_callback, debug_callback parameters
- **Validation Interface**: Task parameter validation
- **Condition Interface**: Success/failure evaluation

## Design Goals
- Easy addition of new task execution strategies
- Clean separation between parsing, validation, and execution
- Consistent error handling and logging across modules
- Minimal coupling between components
- Clear data flow and state management
