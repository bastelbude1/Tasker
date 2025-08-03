# tasker/core/execution_context.py
"""
Execution Context - Unified Callback System
-------------------------------------------
Provides a unified interface for all execution callbacks and context information,
eliminating the need to pass multiple callback parameters to every method.

This class encapsulates:
- Logging callbacks (log, log_debug, log_error, log_warn, log_info)
- Execution callbacks (determine_execution_type, build_command_array, get_task_timeout)
- State management (global_vars, task_results)
- Configuration (dry_run, timeout settings)
"""


class ExecutionContext:
    """Unified execution context for all TASKER operations."""
    
    def __init__(self, executor_instance):
        """Initialize execution context from TaskExecutor instance."""
        self.executor = executor_instance
        
        # Logging callbacks
        self.log = executor_instance.log
        self.log_debug = executor_instance.log_debug
        self.log_error = executor_instance.log_error
        self.log_warn = executor_instance.log_warn
        self.log_info = executor_instance.log_info
        
        # Execution callbacks
        self.determine_execution_type = executor_instance.determine_execution_type
        self.build_command_array = executor_instance.build_command_array
        self.get_task_timeout = executor_instance.get_task_timeout
        
        # State access
        self.global_vars = executor_instance.global_vars
        self.task_results = executor_instance.task_results
        
        # Configuration
        self.dry_run = executor_instance.dry_run
        self.timeout = executor_instance.timeout
        
        # Task execution context
        self._current_parallel_task = getattr(executor_instance, '_current_parallel_task', None)
        self._current_conditional_task = getattr(executor_instance, '_current_conditional_task', None)
        
        # Additional methods that may be needed
        self.categorize_task_result = executor_instance.categorize_task_result
        self.store_task_result = executor_instance.store_task_result
        self._check_shutdown = executor_instance._check_shutdown
    
    def update_parallel_context(self, task_id):
        """Update current parallel task context."""
        self._current_parallel_task = task_id
        if hasattr(self.executor, '_current_parallel_task'):
            self.executor._current_parallel_task = task_id
    
    def update_conditional_context(self, task_id):
        """Update current conditional task context.""" 
        self._current_conditional_task = task_id
        if hasattr(self.executor, '_current_conditional_task'):
            self.executor._current_conditional_task = task_id
    
    def reset_context(self):
        """Reset execution context to normal state."""
        self._current_parallel_task = None
        self._current_conditional_task = None
        if hasattr(self.executor, '_current_parallel_task'):
            self.executor._current_parallel_task = None  
        if hasattr(self.executor, '_current_conditional_task'):
            self.executor._current_conditional_task = None