# tasker/core/task_executor_main.py
"""
TASKER 2.1 - Main Task Executor Class
-------------------------------------
The central orchestration engine for TASKER 2.1.

This module contains the main TaskExecutor class that coordinates all task execution,
logging, validation, and lifecycle management. It delegates specific execution types
to specialized modules while maintaining overall orchestration control.

Architecture:
- Core orchestration and lifecycle management
- Thread-safe logging with granular log levels  
- Comprehensive validation and error handling
- Delegated execution to specialized executor modules
"""

import os
import sys
import re
import time
import subprocess
from datetime import datetime
import shlex
import socket
import shutil
import fcntl  # Linux Only
import threading
import errno 
import signal 
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from our library package
from .utilities import (
    sanitize_filename,
    get_log_directory,
    ExitCodes,
    ExitHandler,
    convert_value,
    convert_to_number,
    sanitize_for_tsv
)
from .condition_evaluator import ConditionEvaluator
from ..validation.host_validator import HostValidator
from ..validation.task_validator import TaskValidator
from ..executors.sequential_executor import SequentialExecutor
from ..executors.parallel_executor import ParallelExecutor
from ..executors.conditional_executor import ConditionalExecutor

# Import new modular components
from .state_manager import StateManager
from .result_collector import ResultCollector
from .workflow_controller import WorkflowController
from .task_runner import TaskRunner


class TaskExecutor:
    """
    TASKER 2.1 - Modular Task Execution System
    
    A sophisticated task execution framework that orchestrates sequential, parallel,
    and conditional task execution with comprehensive logging and validation.
    
    Architecture:
    - Core orchestration and lifecycle management (this class)
    - Delegated execution to specialized modules in tasker/ package
    - Thread-safe logging and result storage with granular log levels
    - Comprehensive validation and error handling
    """
    
    # Log level constants
    LOG_LEVELS = {
        'ERROR': 1,
        'WARN': 2,
        'INFO': 3,
        'DEBUG': 4
    }
    
    # ===== 1. CLASS LIFECYCLE =====
    
    def __init__(self, task_file, log_dir='logs', dry_run=True, log_level='INFO',
                 exec_type=None, timeout=30, connection_test=False, project=None,
                 start_from_task=None, skip_task_validation=False,
                 skip_host_validation=False, skip_security_validation=False,
                 show_plan=False, validate_only=False):
        # Clear debug logging cache for new execution session
        from .condition_evaluator import ConditionEvaluator
        ConditionEvaluator.clear_debug_cache()

        self.task_file = task_file
        self.log_dir = log_dir
        self.dry_run = dry_run
        self.log_level = log_level.upper()
        self.log_level_num = self.LOG_LEVELS.get(self.log_level, 3)  # Default to INFO
        self.tasks = {}  # Changed to dictionary for sparse task IDs
        self.task_results = {}
        self.current_task = 0 # Track current task
        self.loop_counter = {} # Track remaining loops
        self.loop_iterations = {} # Track current iteration number
        self.exec_type = exec_type  # From command line argument
        self.default_exec_type = 'pbrun'  # Default execution type
        self.timeout = timeout # Default timeout from command line
        self.connection_test = connection_test # Whether to make an connection test
        self.project = sanitize_filename(project) if project else None  # Sanitized project name
        self.show_plan = show_plan
        self.validate_only = validate_only

        # Configurable timeouts for cleanup and summary operations
        self.summary_lock_timeout = 20  # Seconds for summary file locking (longer for shared files)
        # Adjust timeouts based on system load or user preference
        if os.environ.get('TASK_EXECUTOR_HIGH_LOAD'):
            self.summary_lock_timeout = 45

        # Global variables support
        self.global_vars = {}  # Store global variables
        
        # Thread safety for logging
        self.log_lock = threading.Lock()
        
        # Thread safety for task results
        self.task_results_lock = threading.Lock()
        
        # Graceful shutdown handling
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Track current parallel/conditional tasks for improved logging
        self._current_parallel_task = None
        
        self._current_conditional_task = None

        # Resume capability parameters
        self.start_from_task = start_from_task
        self.skip_task_validation = skip_task_validation
        self.skip_host_validation = skip_host_validation
        self.skip_security_validation = skip_security_validation

        # Log resume information
        if self.start_from_task is not None:
            self.log_info(f"# Resume mode: Starting from Task {self.start_from_task}")
            if self.skip_task_validation:
                self.log_warn(f"# Task Validation will be skipped")
            if self.skip_host_validation:
                self.log_warn(f"# Host Validation will be skipped - ATTENTION")
            if self.skip_security_validation:
                self.log_warn(f"# Security Validation will be skipped - ATTENTION")

        # Initialize summary tracking variables
        self.final_task_id = None
        self.final_exit_code = None
        self.final_success = None
        self.final_hostname = None
        self.final_command = None
        self._summary_written = False  # Track if summary has been written

        # Generate timestamp for both log file and task copy 
        timestamp = datetime.now().strftime('%d%b%y_%H%M%S')

        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up logging with sanitized task filename as prefix
        sanitized_prefix = sanitize_filename(task_file) 
        timestamp = datetime.now().strftime('%d%b%y_%H%M%S')
        log_appendix = 'log'
        if self.dry_run: log_appendix = 'dryrun'
        self.log_file_path = os.path.join(self.log_dir, f"{sanitized_prefix}_{timestamp}.{log_appendix}")
        self.log_file = open(self.log_file_path, 'w')

        # Copy the task file to the tasks directory as backup (only if file exists)
        if os.path.exists(task_file):
            try:
                task_filename = os.path.basename(task_file)
                task_copy_path = os.path.join(self.log_dir, f"{task_filename}_{timestamp}")
                shutil.copy2(task_file, task_copy_path)
                self.log_debug(f"Created task file copy: {task_copy_path}")
            except Exception as e:
                self.log_warn(f"Could not copy task file to tasks directory: {str(e)}")
        else:
            self.log_debug(f"Skipping task file copy - file does not exist: {task_file}")

        # Set up project summary logging if project is specified
        if self.project:
            self.summary_log_path = os.path.join(self.log_dir, f"{self.project}.summary")

            # Check if file exists to determine if we need to write headers
            file_exists = os.path.exists(self.summary_log_path)

            # Open in append mode with buffering disabled
            self.summary_log = open(self.summary_log_path, 'a', buffering=1)

            # Write headers if this is a new file
            if not file_exists:
                # Write headers directly with locking
                try:
                    fcntl.flock(self.summary_log.fileno(), fcntl.LOCK_EX)
                    self.summary_log.write(f"#Timestamp\tTask File\tTask ID\tHostname\tCommand\tExit Code\tStatus\tLog File\n")
                finally:
                    fcntl.flock(self.summary_log.fileno(), fcntl.LOCK_UN)
        else:
            self.summary_log = None

        # Start logging task execution
        self.log_info(f"=== Task Execution Start: {timestamp} ===")
        self.log_info(f"# Task file: {task_file}")
        self.log_info(f"# Log level: {self.log_level}")

        if self.exec_type:
            exec_type=self.exec_type
            self.log_debug(f"# Execution type from args: {exec_type}")
        elif 'TASK_EXECUTOR_TYPE' in os.environ:
            exec_type = os.environ.get('TASK_EXECUTOR_TYPE')
            self.log_debug(f"# Execution type from environment: {exec_type}")
        else:
            exec_type = self.default_exec_type
            self.log_debug(f"# Execution type (Default): {exec_type} (if not overriden by task)")

        if dry_run:
            self.log_info("# Dry run mode")
        self.log_debug(f"# Default timeout: {timeout} [s]")
    
        # Only add minimal warning for shared summary files
        if self.project:
            # Check if summary file is currently locked by another process
            summary_file_path = os.path.join(self.log_dir, f"{self.project}.summary")
        
            if os.path.exists(summary_file_path):
                try:
                    # Quick non-blocking test if file is locked
                    with open(summary_file_path, 'a') as test_file:
                        try:
                            fcntl.flock(test_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                            fcntl.flock(test_file.fileno(), fcntl.LOCK_UN)
                            # File is not locked
                        except (OSError, IOError):
                            # File is currently locked by another process
                            self.log_info(f"Info: Summary file '{self.project}.summary' is currently in use by another tasker instance.")
                            self.log_info("Summary writes will wait for the other instance to complete.")
                except Exception:
                    pass  # Ignore test errors

        # ===== NEW MODULAR ARCHITECTURE INITIALIZATION =====
        # Initialize the new modular components while maintaining backward compatibility

        # Initialize StateManager with existing state
        self._state_manager = StateManager()

        # Transfer fallback values to StateManager
        if hasattr(self, '_global_vars_fallback'):
            self._state_manager.set_global_vars(self._global_vars_fallback)
        if hasattr(self, '_current_task_fallback'):
            self._state_manager.set_current_task(self._current_task_fallback)
        if hasattr(self, '_tasks_fallback'):
            self._state_manager.set_tasks(self._tasks_fallback)
        if hasattr(self, '_task_results_fallback'):
            # Transfer any existing task results
            for task_id, result in self._task_results_fallback.items():
                self._state_manager.store_task_result(task_id, result)

        # Initialize ResultCollector
        self._result_collector = ResultCollector(self.task_file, self.project)

        # Setup summary logging for ResultCollector if project is specified
        if self.project and hasattr(self, 'summary_log') and self.summary_log:
            try:
                self._result_collector.setup_summary_logging(self.summary_log, self.log_file_path)
                self._result_collector.summary_lock_timeout = self.summary_lock_timeout
                self.log_debug(f"Summary logging configured for ResultCollector: {self.summary_log_path}")
            except Exception as e:
                self.log_warn(f"Failed to setup summary logging for ResultCollector: {e}")

        # Transfer fallback values to ResultCollector
        if hasattr(self, '_final_task_id_fallback'):
            self._result_collector.final_task_id = self._final_task_id_fallback
        if hasattr(self, '_final_hostname_fallback'):
            self._result_collector.final_hostname = self._final_hostname_fallback
        if hasattr(self, '_final_command_fallback'):
            self._result_collector.final_command = self._final_command_fallback
        if hasattr(self, '_final_exit_code_fallback'):
            self._result_collector.final_exit_code = self._final_exit_code_fallback
        if hasattr(self, '_final_success_fallback'):
            self._result_collector.final_success = self._final_success_fallback

        # Initialize WorkflowController with StateManager and logging
        self._workflow_controller = WorkflowController(
            self._state_manager,
            logger_callback=self.log_info,
            debug_logger_callback=self.log_debug
        )

        # Initialize TaskRunner with all components
        self._task_runner = TaskRunner(
            state_manager=self._state_manager,
            workflow_controller=self._workflow_controller,
            result_collector=self._result_collector,
            default_exec_type=self.default_exec_type,
            default_timeout=self.timeout,
            dry_run=self.dry_run,
            logger_callback=self.log,
            debug_logger_callback=self.log_debug
        )

        # Set execution type override from command line
        self._task_runner.set_execution_type_override(self.exec_type)

        # ===== BACKWARD COMPATIBILITY PROPERTIES =====
        # Create property wrappers for seamless transition to new architecture

    # State management properties for backward compatibility
    @property
    def tasks(self):
        """Backward compatibility property for tasks access."""
        if hasattr(self, '_state_manager'):
            return self._state_manager.tasks
        else:
            # Fallback during initialization
            return getattr(self, '_tasks_fallback', {})

    @tasks.setter
    def tasks(self, value):
        """Backward compatibility setter for tasks."""
        if hasattr(self, '_state_manager'):
            self._state_manager.set_tasks(value)
        else:
            # Store in fallback during initialization
            self._tasks_fallback = value

    @property
    def task_results(self):
        """Backward compatibility property for task_results access."""
        if hasattr(self, '_state_manager'):
            return self._state_manager.task_results
        else:
            # Fallback during initialization
            return getattr(self, '_task_results_fallback', {})

    @task_results.setter
    def task_results(self, value):
        """Backward compatibility setter for task_results."""
        if hasattr(self, '_state_manager'):
            # Clear existing results and set new ones
            self._state_manager.clear_all_state()
            for task_id, result in value.items():
                self._state_manager.store_task_result(task_id, result)
        else:
            # Store in fallback during initialization
            self._task_results_fallback = value

    @property
    def current_task(self):
        """Backward compatibility property for current_task access."""
        if hasattr(self, '_state_manager'):
            return self._state_manager.current_task
        else:
            # Fallback during initialization
            return getattr(self, '_current_task_fallback', 0)

    @current_task.setter
    def current_task(self, value):
        """Backward compatibility setter for current_task."""
        if hasattr(self, '_state_manager'):
            self._state_manager.set_current_task(value)
        else:
            # Store in fallback during initialization
            self._current_task_fallback = value

    @property
    def loop_counter(self):
        """Backward compatibility property for loop_counter access."""
        if hasattr(self, '_state_manager'):
            return self._state_manager.loop_counter
        else:
            return getattr(self, '_loop_counter_fallback', {})

    @loop_counter.setter
    def loop_counter(self, value):
        """Backward compatibility setter for loop_counter."""
        if hasattr(self, '_state_manager'):
            self._state_manager.loop_counter = value
        else:
            self._loop_counter_fallback = value

    @property
    def loop_iterations(self):
        """Backward compatibility property for loop_iterations access."""
        if hasattr(self, '_state_manager'):
            return self._state_manager.loop_iterations
        else:
            return getattr(self, '_loop_iterations_fallback', {})

    @loop_iterations.setter
    def loop_iterations(self, value):
        """Backward compatibility setter for loop_iterations."""
        if hasattr(self, '_state_manager'):
            self._state_manager.loop_iterations = value
        else:
            self._loop_iterations_fallback = value

    @property
    def global_vars(self):
        """Backward compatibility property for global_vars access."""
        if hasattr(self, '_state_manager'):
            return self._state_manager.global_vars
        else:
            # Fallback during initialization
            return getattr(self, '_global_vars_fallback', {})

    @global_vars.setter
    def global_vars(self, value):
        """Backward compatibility setter for global_vars."""
        if hasattr(self, '_state_manager'):
            self._state_manager.set_global_vars(value)
        else:
            # Store in fallback during initialization
            self._global_vars_fallback = value

    # Result collector properties
    @property
    def final_task_id(self):
        """Backward compatibility property for final_task_id access."""
        if hasattr(self, '_result_collector'):
            return self._result_collector.final_task_id
        else:
            return getattr(self, '_final_task_id_fallback', None)

    @final_task_id.setter
    def final_task_id(self, value):
        """Backward compatibility setter for final_task_id."""
        if hasattr(self, '_result_collector'):
            self._result_collector.final_task_id = value
        else:
            self._final_task_id_fallback = value

    @property
    def final_hostname(self):
        """Backward compatibility property for final_hostname access."""
        if hasattr(self, '_result_collector'):
            return self._result_collector.final_hostname
        else:
            return getattr(self, '_final_hostname_fallback', "")

    @final_hostname.setter
    def final_hostname(self, value):
        """Backward compatibility setter for final_hostname."""
        if hasattr(self, '_result_collector'):
            self._result_collector.final_hostname = value
        else:
            self._final_hostname_fallback = value

    @property
    def final_command(self):
        """Backward compatibility property for final_command access."""
        if hasattr(self, '_result_collector'):
            return self._result_collector.final_command
        else:
            return getattr(self, '_final_command_fallback', "")

    @final_command.setter
    def final_command(self, value):
        """Backward compatibility setter for final_command."""
        if hasattr(self, '_result_collector'):
            self._result_collector.final_command = value
        else:
            self._final_command_fallback = value

    @property
    def final_exit_code(self):
        """Backward compatibility property for final_exit_code access."""
        if hasattr(self, '_result_collector'):
            return self._result_collector.final_exit_code
        else:
            return getattr(self, '_final_exit_code_fallback', None)

    @final_exit_code.setter
    def final_exit_code(self, value):
        """Backward compatibility setter for final_exit_code."""
        if hasattr(self, '_result_collector'):
            self._result_collector.final_exit_code = value
        else:
            self._final_exit_code_fallback = value

    @property
    def final_success(self):
        """Backward compatibility property for final_success access."""
        if hasattr(self, '_result_collector'):
            return self._result_collector.final_success
        else:
            return getattr(self, '_final_success_fallback', False)

    @final_success.setter
    def final_success(self, value):
        """Backward compatibility setter for final_success."""
        if hasattr(self, '_result_collector'):
            self._result_collector.final_success = value
        else:
            self._final_success_fallback = value

    def __enter__(self):
        """Enable use of the class as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting the context manager."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def cleanup(self):
        """
        Timeout-protected cleanup with comprehensive error handling.
        """
        cleanup_errors = []

        # PHASE 1: Log file cleanup
        if hasattr(self, 'log_file'):
            try:
                if self.log_file and not self.log_file.closed:
                    try:
                        with self.log_lock:
                            self._log_direct(f"# Log file: {getattr(self, 'log_file_path', 'unknown')}")
                            self._log_direct("=== Task Execution End: {} ===".format(
                                datetime.now().strftime('%d%b%y_%H%M%S')))
                    except Exception as log_error:
                        cleanup_errors.append(f"Final log write failed: {log_error}")

                        try:
                            timestamp = datetime.now().strftime('%d%b%y_%H%M%S')
                            self.log_file.write(f"# Log file: {getattr(self, 'log_file_path', 'unknown')}\n")
                            self.log_file.write(f"=== Task Execution End: {timestamp} ===\n")
                            self.log_file.flush()
                        except Exception as fallback_error:
                            cleanup_errors.append(f"Fallback log write failed: {fallback_error}")
            
                    try:
                        if not self.log_file.closed:
                            self.log_file.close()
                    except Exception as close_error:
                        cleanup_errors.append(f"Log file close failed: {close_error}")
                    
            except Exception as cleanup_error:
                cleanup_errors.append(f"Log file cleanup phase failed: {cleanup_error}")
            finally:
                self.log_file = None

        # PHASE 2: Timeout-protected summary log cleanup
        if hasattr(self, 'summary_log'):
            try:
                # Step 1: TIMEOUT-GESCHueTZTER final summary write
                if (self.summary_log and not self.summary_log.closed and 
                    self.final_task_id is not None):
                    try:
                        # Delegate to ResultCollector to avoid duplicate flock/timeout logic
                        self._result_collector.write_final_summary_with_timeout(self.summary_lock_timeout)
                    
                    except TimeoutError as timeout_error:
                        cleanup_errors.append(f"TIMEOUT: Summary write timed out: {timeout_error}")
                    except Exception as write_error:
                        error_msg = str(write_error).lower()
                        if "timeout" in error_msg or "lock" in error_msg:
                            cleanup_errors.append(f"SHARED FILE CONFLICT: {write_error}")
                        elif "closed" in error_msg or "invalid" in error_msg:
                            cleanup_errors.append(f"File state error: {write_error}")
                        else:
                            cleanup_errors.append(f"Final summary write failed: {write_error}")
        
                # Step 2: Summary file close
                if self.summary_log:
                    try:
                        with self.log_lock:
                            if not self.summary_log.closed:
                                try:
                                    self.summary_log.flush()
                                except Exception as flush_error:
                                    cleanup_errors.append(f"Summary flush failed: {flush_error}")
                        
                                try:
                                    self.summary_log.close()
                                except Exception as close_error:
                                    cleanup_errors.append(f"Summary close failed: {close_error}")
                            
                    except Exception as lock_error:
                        cleanup_errors.append(f"Summary lock cleanup failed: {lock_error}")
                
                        try:
                            if hasattr(self.summary_log, 'close'):
                                self.summary_log.close()
                        except Exception as final_close_error:
                            cleanup_errors.append(f"Final summary close attempt failed: {final_close_error}")
                    
            except Exception as phase2_error:
                cleanup_errors.append(f"Summary cleanup phase failed: {phase2_error}")
            finally:
                self.summary_log = None

        # PHASE 3: Error reporting
        if cleanup_errors:
            error_count = len(cleanup_errors)
            error_summary = f"Cleanup completed with {error_count} error(s):"
            for i, error in enumerate(cleanup_errors, 1):
                error_summary += f"\n  {i}. {error}"
    
            self._safe_error_report(error_summary)

    def _signal_handler(self, signum, frame):
        """Signal handler for graceful shutdown."""
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.log_warn(f"Received {signal_name}, initiating graceful shutdown...")
        self._shutdown_requested = True
        
        # Store signal info for summary
        self._shutdown_signal = signal_name

    def _check_shutdown(self):
        """Check if shutdown was requested - call at natural breakpoints."""
        if self._shutdown_requested:
            self.log_warn("Graceful shutdown requested - stopping execution")
            
            # Ensure summary gets written for graceful shutdown
            if hasattr(self, 'summary_log') and self.summary_log:
                # Set final task info for graceful shutdown if not already set
                if self.final_task_id is None:
                    # Use current task or last known task
                    if hasattr(self, 'current_task') and self.current_task is not None:
                        self.final_task_id = self.current_task
                        task = self.tasks.get(self.current_task, {})
                        self.final_hostname = task.get('hostname', 'graceful_shutdown')
                        self.final_command = task.get('command', 'interrupted_by_signal')
                    else:
                        # Fallback if no current task
                        self.final_task_id = 'interrupted'
                        self.final_hostname = 'graceful_shutdown'
                        self.final_command = 'interrupted_by_signal'
                
                # Set graceful shutdown specific values
                self.final_exit_code = 130  # Standard SIGINT exit code
                self.final_success = False  # Graceful shutdown is not success
                
                # Add graceful shutdown marker to command for clarity
                if 'graceful_shutdown' not in str(self.final_command):
                    # Add signal info to command if available
                    signal_info = getattr(self, '_shutdown_signal', 'SIGNAL')
                    self.final_command = f"{self.final_command} [GRACEFUL_SHUTDOWN_{signal_info}]"
            
            self.cleanup()
            ExitHandler.exit_with_code(ExitCodes.SIGNAL_INTERRUPT, 
                                     "Task execution interrupted by signal", False)

    def __del__(self):
        """Destructor - ensure log file is closed."""
        if hasattr(self, 'log_file') and self.log_file:
            self.log_info(f"# Log file: {self.log_file_path}")
            self.log_info("=== Task Execution End: {} ===".format(
                datetime.now().strftime('%d%b%y_%H%M%S')))
            self.log_file.close()
            self.log_file = None
    
    # ===== 2. CORE UTILITIES =====
    
    # Thread-safe task result management
    def store_task_result(self, task_id, result):
        """Thread-safe method to store task results."""
        # Delegate to StateManager for thread-safe operation
        self._state_manager.store_task_result(task_id, result)

    def get_task_result(self, task_id):
        """Thread-safe method to get task results."""
        # Delegate to StateManager for thread-safe operation
        return self._state_manager.get_task_result(task_id)

    def has_task_result(self, task_id):
        """Thread-safe method to check if task result exists."""
        # Delegate to StateManager for thread-safe operation
        return self._state_manager.has_task_result(task_id)
    
    # Enhanced logging infrastructure with log levels
    def _should_log(self, level):
        """Check if message should be logged based on current log level."""
        return self.LOG_LEVELS.get(level, 0) <= self.log_level_num

    def _log_with_level(self, level, message):
        """Internal method to log with specified level."""
        if not self._should_log(level):
            return
            
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        level_prefix = f"{level}: " if level != 'INFO' else ""
        log_message = f"[{timestamp}] {level_prefix}{message}"
        
        # Thread-safe logging with reentrancy protection
        with self.log_lock:
            print(log_message)
            if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
                self.log_file.write(log_message + "\n")
                self.log_file.flush()

    def log_error(self, message):
        """Log an error message."""
        self._log_with_level('ERROR', message)

    def log_warn(self, message):
        """Log a warning message."""
        self._log_with_level('WARN', message)

    def log_info(self, message):
        """Log an info message."""
        self._log_with_level('INFO', message)

    def log_debug(self, message):
        """Log a debug message."""
        self._log_with_level('DEBUG', message)

    # Backward compatibility methods
    def log(self, message):
        """Legacy log method - maps to log_info for backward compatibility."""
        self.log_info(message)

    def debug_log(self, message):
        """Legacy debug_log method - maps to log_debug for backward compatibility."""
        self.log_debug(message)

    def _log_direct(self, message):
        """Direct logging without acquiring log_lock - for internal use only."""
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        # Direct write without lock - caller must ensure thread safety
        print(log_message)
        if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
            self.log_file.write(log_message + "\n")
            self.log_file.flush()

    # Safe error reporting with multiple fallback channels

    def _safe_error_report(self, message, *fallback_channels):
        """Ultra-safe error reporting with multiple fallback channels."""
        reported = False
        
        # Try each channel in order until one succeeds
        channels = [
            ("direct_log", lambda: self._try_direct_log_write(message)),
            ("stderr", lambda: self._try_stderr_write(message)),
            ("stdout", lambda: self._try_stdout_write(message)),
            ("file_direct", lambda: self._try_emergency_file_write(message))
        ]
        
        for channel_name, channel_func in channels:
            try:
                channel_func()
                reported = True
                break
            except:
                continue  # Try next channel
        
        # If absolutely nothing worked, there's nothing more we can do
        if not reported:
            # Last resort: try to create a temp file in /tmp
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', prefix='tasker_error_', 
                                               delete=False) as f:
                    f.write(f"EMERGENCY ERROR REPORT: {message}\n")
            except:
                pass  # Truly nothing we can do

    def _try_direct_log_write(self, message):
        """Try to write directly to log file without locks."""
        if (hasattr(self, 'log_file') and self.log_file and 
            not self.log_file.closed):
            timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
            self.log_file.write(f"[{timestamp}] ERROR: {message}\n")
            self.log_file.flush()

    def _try_stderr_write(self, message):
        """Try to write to stderr."""
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        sys.stderr.write(f"[{timestamp}] ERROR: {message}\n")
        sys.stderr.flush()

    def _try_stdout_write(self, message):
        """Try to write to stdout."""
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        sys.stdout.write(f"[{timestamp}] ERROR: {message}\n")
        sys.stdout.flush()

    def _try_emergency_file_write(self, message):
        """Try to write to emergency log file in home directory."""
        home_dir = os.path.expanduser("~")
        emergency_file = os.path.join(home_dir, "tasker_emergency.log")
        timestamp = datetime.now().strftime('%d%b%y_%H%M%S')
        with open(emergency_file, 'a') as f:
            f.write(f"[{timestamp}] EMERGENCY: {message}\n")

    def _acquire_file_lock_atomically(self, timeout_seconds=5):
        """
        Atomic lock acquisition with retry - eliminates race conditions.
        Production-ready solution with retry logic.
        """
        try:
            # Atomic validation and lock acquisition in one step
            if (not hasattr(self, 'summary_log') or not self.summary_log or 
                self.summary_log.closed):
                return None, False
            
            file_no = self.summary_log.fileno()
        
            # Retry loop with timeout
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(file_no, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return file_no, True
                
                except (OSError, IOError) as e:
                    if e.errno in (errno.EAGAIN, errno.EACCES):
                        # File is locked - check timeout
                        elapsed = time.time() - start_time
                        if elapsed >= timeout_seconds:
                            return None, False  # Timeout reached
                        time.sleep(0.1)  # Wait briefly, then retry
                        continue
                    else:
                        # Other error (EBADF, etc.) - file handle invalid
                        return None, False
                
        except Exception:
            # Any other error - safe fallback
            return None, False

    def write_final_summary_with_timeout(self, timeout_seconds=5):
        """
        Thread-based timeout for cleanup() - avoids signal conflicts.
        Minimal, robust solution for production environment.
        """
        import threading
    
        result = {'completed': False, 'error': None}
    
        def write_worker():
            try:
                self.write_final_summary()
                result['completed'] = True
            except Exception as e:
                result['error'] = e
    
        # Start write operation in separate thread
        worker_thread = threading.Thread(target=write_worker, daemon=True)
        worker_thread.start()
        
        # Wait with timeout
        worker_thread.join(timeout=timeout_seconds)
        
        if worker_thread.is_alive():
            # Thread still running - timeout reached
            raise TimeoutError(f"write_final_summary timeout after {timeout_seconds}s")
        
        if result['error']:
            # Exception in worker thread
            raise result['error']
        
        if not result['completed']:
            # Unexpected state
            raise RuntimeError("write_final_summary completed unexpectedly")

    def write_final_summary(self):
        """
        Race-condition-free summary write with retry logic.
        """
        # Quick validation and exit
        if (not hasattr(self, 'summary_log') or not self.summary_log or
            self.final_task_id is None):
            return

        # Prevent duplicate writes
        if getattr(self, '_summary_written', False):
            return
        self._summary_written = True
    
        # Atomic lock acquisition and write with retry
        with self.log_lock:
            # Snapshot final_* fields under lock to avoid torn reads
            final_task_id_snapshot = self.final_task_id
            final_hostname_snapshot = self.final_hostname
            final_command_snapshot = self.final_command
            final_exit_code_snapshot = self.final_exit_code
            final_success_snapshot = self.final_success

            # Message preparation with snapshotted values
            timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
            status = "SUCCESS" if final_success_snapshot else "FAILURE"
            log_file = os.path.basename(getattr(self, 'log_file_path', 'unknown.log'))

            fields = [
                timestamp,
                sanitize_for_tsv(os.path.basename(self.task_file)),
                sanitize_for_tsv(final_task_id_snapshot),
                sanitize_for_tsv(final_hostname_snapshot),
                sanitize_for_tsv(final_command_snapshot),
                sanitize_for_tsv(final_exit_code_snapshot),
                status,
                log_file
            ]
            message = '\t'.join(fields)
            # Use configurable timeout
            timeout_seconds = getattr(self, 'summary_lock_timeout', 20)
            file_no, lock_acquired = self._acquire_file_lock_atomically(timeout_seconds)
            
            if not lock_acquired:
                # Detailed error message
                project_name = getattr(self, 'project', 'unknown')
                raise TimeoutError(
                    f"Could not acquire lock on shared summary file '{project_name}.summary' "
                    f"within {timeout_seconds} seconds. Another tasker instance "
                    f"is currently writing to the summary file."
                )
            
            try:
                # Final validation after lock (defense in depth)
                if self.summary_log.closed:
                    raise ValueError("Summary log unexpectedly closed after lock acquisition")
                
                # Atomic write operations
                self.summary_log.seek(0, 2)  # End of file
                self.summary_log.write(f"{message}\n")
                self.summary_log.flush()
                
                # Verification
                current_pos = self.summary_log.tell()
                if current_pos == 0:
                    raise IOError("Write verification failed - file position is 0")
                
            finally:
                # Guaranteed lock release
                if file_no is not None:
                    try:
                        fcntl.flock(file_no, fcntl.LOCK_UN)
                    except Exception:
                        # Lock will be automatically released on process exit
                        pass

    # ===== 3. VALIDATION & SETUP =====
    
    def validate_tasks(self):
        """Validate the task file using TaskValidator module."""
        self.log_info(f"# Validating task file: {self.task_file}")
        
        try:
            # Use the new TaskValidator module
            result = TaskValidator.validate_task_file(
                self.task_file,
                debug=(self.log_level == 'DEBUG'),
                log_callback=self.log_info,
                debug_callback=self.log_debug if self.log_level == 'DEBUG' else None,
                skip_security_validation=self.skip_security_validation
            )
            
            if not result['success']:
                self.log_info("# Task validation FAILED.")
                # Log each error
                for error in result['errors']:
                    self.log_error(error)
                return False
            else:
                # Log warnings if any
                if result['warnings']:
                    for warning in result['warnings']:
                        self.log_debug(f"# WARNING: {warning}")
                
                # Validation passed
                self.log_info("# Task validation passed successfully.")
                return True
                
        except Exception as e:
            self.log_error(f"Error during task validation: {str(e)}")
            return False

    def parse_task_file(self):
        """Parse the task file and extract global variables and task definitions."""
        if not os.path.exists(self.task_file):
            self.log_error(f"Task file '{self.task_file}' not found.")
            ExitHandler.exit_with_code(ExitCodes.TASK_FILE_NOT_FOUND, f"Task file '{self.task_file}' not found", False)
            
        with open(self.task_file, 'r') as f:
            lines = f.readlines()
        
        # PHASE 1: Collect global variables (first pass)
        self.log_info(f"# Parsing global variables from '{self.task_file}'")
        parsed_global_vars = {}  # Local dictionary to collect global variables

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Check if this is a global variable definition
            if '=' in line and not line.startswith('task='):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Check if this is a global variable (not a known task field)
                known_task_fields = [
                    'hostname', 'command', 'arguments', 'next', 'stdout_split', 'stderr_split',
                    'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure',
                    'on_success', 'success', 'condition', 'exec', 'timeout', 'return',
                    'type', 'max_parallel', 'tasks', 'retry_failed', 'retry_count', 'retry_delay',  # Parallel fields
                    'if_true_tasks', 'if_false_tasks'  # NEW: Conditional task fields
                ]

                if key not in known_task_fields:
                    # This is a global variable
                    parsed_global_vars[key] = value
                    self.log_debug(f"Global variable: {key} = {value}")

        # Assign all global variables at once (compatible with StateManager property system)
        self.global_vars = parsed_global_vars
        global_count = len(parsed_global_vars)
        self.log_info(f"# Found {global_count} global variables")
        if global_count > 0:
            for key, value in self.global_vars.items():
                self.log_debug(f"#   {key} = {value}")
        
        # PHASE 2: Parse tasks (second pass)
        current_task = None
        parsed_tasks = {}  # Local dictionary to collect tasks

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse key=value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Check if this is a new task definition
                if key == 'task':
                    # Save the previous task if it exists
                    if current_task is not None and 'task' in current_task:
                        task_id = int(current_task['task'])
                        if 'arguments' not in current_task:
                            current_task['arguments'] = ''

                        # CRITICAL: Check for duplicate task IDs
                        if task_id in parsed_tasks:
                            self.log_error(f"DUPLICATE TASK ID {task_id} detected in task file!")
                            self.log_debug(f"Previous task {task_id}: {parsed_tasks[task_id]}")
                            self.log_debug(f"Duplicate task {task_id}: {current_task}")
                            self.log_error("Each task ID must be unique. Please fix the task file.")
                            ExitHandler.exit_with_code(ExitCodes.TASK_FILE_VALIDATION_FAILED, f"Duplicate task ID {task_id} found", False)

                        parsed_tasks[task_id] = current_task

                    # Start a new task
                    current_task = {'task': value}
                else:
                    # Add to current task (only if it's a known task field)
                    if current_task is not None:
                        current_task[key] = value

        # Add the last task if it exists
        if current_task is not None and 'task' in current_task:
            task_id = int(current_task['task'])
            if 'arguments' not in current_task:
                current_task['arguments'] = ''

            # CRITICAL: Check for duplicate task IDs (last task)
            if task_id in parsed_tasks:
                self.log_error(f"DUPLICATE TASK ID {task_id} detected in task file!")
                self.log_debug(f"Previous task {task_id}: {parsed_tasks[task_id]}")
                self.log_debug(f"Duplicate task {task_id}: {current_task}")
                self.log_error("Each task ID must be unique. Please fix the task file.")
                ExitHandler.exit_with_code(ExitCodes.TASK_FILE_VALIDATION_FAILED, f"Duplicate task ID {task_id} found", False)

            parsed_tasks[task_id] = current_task

        # Assign all parsed tasks at once (compatible with StateManager property system)
        self.tasks = parsed_tasks
        
        # Validate tasks - now we only check that required fields are present
        valid_task_count = 0
        for task_id, task in self.tasks.items():
            # Different validation for parallel and conditional tasks
            if task.get('type') == 'parallel':
                if 'tasks' not in task:
                    self.log_warn(f"Parallel task {task_id} is missing required 'tasks' field.")
                    continue
                valid_task_count += 1
            elif task.get('type') == 'conditional':
                if 'condition' not in task:
                    self.log_warn(f"Conditional task {task_id} is missing required 'condition' field.")
                    continue
                if 'if_true_tasks' not in task and 'if_false_tasks' not in task:
                    self.log_warn(f"Conditional task {task_id} has no task branches defined.")
                    continue
                valid_task_count += 1
            else:
                if 'hostname' not in task and 'return' not in task:
                    self.log_warn(f"Task {task_id} is missing required 'hostname' field.")
                    continue
                    
                if 'command' not in task and 'return' not in task:
                    self.log_warn(f"Task {task_id} is missing required 'command' field.")
                    continue
                    
                valid_task_count += 1
            
        self.log_info(f"# Successfully parsed {valid_task_count} valid tasks from '{self.task_file}'")

    def validate_task_dependencies(self):
        """Validate that task dependencies can be resolved given the execution flow."""
        dependency_issues = []
        pattern = r'@(\d+)_(stdout|stderr|success)@'
        
        for task_id, task in self.tasks.items():
            # Check condition dependencies
            if 'condition' in task:
                matches = re.findall(pattern, task['condition'])
                for dep_task_str, _ in matches:
                    dep_task = int(dep_task_str)
                    if dep_task not in self.tasks:
                        dependency_issues.append(f"Task {task_id} condition references non-existent Task {dep_task}")
                    elif dep_task >= task_id:
                        dependency_issues.append(f"Task {task_id} condition references future Task {dep_task} - this may cause execution issues")
            
            # Check argument dependencies
            if 'arguments' in task:
                matches = re.findall(pattern, task['arguments'])
                for dep_task_str, _ in matches:
                    dep_task = int(dep_task_str)
                    if dep_task not in self.tasks:
                        dependency_issues.append(f"Task {task_id} arguments reference non-existent Task {dep_task}")
                    elif dep_task >= task_id:
                        dependency_issues.append(f"Task {task_id} arguments reference future Task {dep_task} - this may cause execution issues")
        
        if dependency_issues:
            self.log_info("# WARNING: Task dependency issues detected:")
            for issue in dependency_issues:
                self.log_info(f"#   {issue}")
            self.log_info("# These may cause tasks to be skipped due to unresolved dependencies.")
            return False
        else:
            self.log_info("# Task dependency validation passed.")
            return True

    def validate_start_from_task(self, start_task_id):
        """Validate and provide warnings for --start-from usage."""
        if start_task_id not in self.tasks:
            available_tasks = sorted(self.tasks.keys())
            self.log_info(f"ERROR: Start task {start_task_id} not found")
            self.log_info(f"Available task IDs: {available_tasks}")
            return False
        
        self.log_info(f"# Start-from validation: Starting from task {start_task_id}")
        self.log_info(f"# WARNING: Tasks before {start_task_id} will be skipped")
        
        # Check for potential dependency issues
        skipped_tasks = [tid for tid in self.tasks.keys() if tid < start_task_id]
        if skipped_tasks:
            self.log_info(f"# Skipped tasks: {sorted(skipped_tasks)}")
            self.log_info(f"# CAUTION: Task {start_task_id} may fail if it depends on skipped tasks")
        
        return True
    def show_execution_plan(self):
        """Show execution plan and get user confirmation."""
        self.log_info("=== EXECUTION PLAN ===")
    
        # Determine starting point
        start_id = self.start_from_task if self.start_from_task is not None else 0
        if self.start_from_task is not None:
            self.log_info(f"# Resume mode: Starting from Task {start_id}")
    
        # Count and show tasks
        task_count = 0
        for task_id, task in sorted(self.tasks.items()):
            if task_id < start_id:
                continue
            
            task_count += 1
            task_type = task.get('type', 'normal')
        
            if task_type == 'parallel':
                tasks_str = task.get('tasks', '')
                next_param = task.get('next', '')
                on_success = task.get('on_success', '')
                on_failure = task.get('on_failure', '')

                self.log_info(f"  Task {task_id}: PARALLEL -> execute [{tasks_str}]")
                if next_param:
                    self.log_info(f"            -> then continue based on 'next={next_param}'")
                elif on_success or on_failure:
                    if on_success:
                        self.log_info(f"            -> on success: task {on_success}")
                    if on_failure:
                        self.log_info(f"            -> on failure: task {on_failure}")
                else:
                    self.log_info(f"            -> then continue to task {task_id + 1}")
            elif task_type == 'conditional':
                condition = task.get('condition', 'N/A')
                if_true = task.get('if_true_tasks', '')
                if_false = task.get('if_false_tasks', '')
                on_success = task.get('on_success', '')
                on_failure = task.get('on_failure', '')

                self.log_info(f"  Task {task_id}: CONDITIONAL [{condition}]")
                if if_true:
                    self.log_info(f"            -> if TRUE: execute [{if_true}]")
                if if_false:
                    self.log_info(f"            -> if FALSE: execute [{if_false}]")

                if on_success or on_failure:
                    if on_success:
                        self.log_info(f"            -> on success: task {on_success}")
                    if on_failure:
                        self.log_info(f"            -> on failure: task {on_failure}")
                else:
                    self.log_info(f"            -> then continue to task {task_id + 1}")
            elif 'return' in task:
                return_code = task.get('return', 'N/A')
                self.log_info(f"  Task {task_id}: RETURN {return_code}")
            else:
                hostname = task.get('hostname', 'N/A')
                command = task.get('command', 'N/A')
                self.log_info(f"  Task {task_id}: {hostname} -> {command}")
    
        self.log_info(f"# Total: {task_count} tasks to execute")
        self.log_info("=" * 50)
    
        # User confirmation
        if not self._get_user_confirmation():
            self.log_info("Execution cancelled by user.")
            ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Execution cancelled by user", False)

    def _get_user_confirmation(self):
        """Get user confirmation to proceed."""
        while True:
            try:
                response = input("Proceed with execution? [y/N]: ").strip().lower()
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no', '']:
                    return False
                else:
                    print("Please enter 'y' for yes or 'n' for no.")
            except (KeyboardInterrupt, EOFError):
                print("\nExecution cancelled by user.")
                return False

    # ===== 4. VARIABLE & CONDITION PROCESSING =====
    #
    # Variable replacement (@VARIABLE@ syntax) and condition evaluation logic
    # has been moved to: tasker/core/condition_evaluator.py
    #
    # This module provides:
    # - replace_variables(): Variable replacement with @VARIABLE@ syntax
    # - evaluate_condition(): Complex condition evaluation with boolean operators
    # - evaluate_simple_condition(): Simple condition evaluation
    # - evaluate_operator_comparison(): Comparison operators (=, !=, ~, !~, <, >, etc.)
    # - split_output(): Output splitting by delimiter
    #
    # Usage: All condition processing is now delegated through ConditionEvaluator static methods

    # ===== 5. TASK EXECUTION HELPERS =====
    
    def determine_execution_type(self, task, task_display_id, loop_display=""):
        """Determine which execution type to use, respecting priority order."""
        if 'exec' in task:
            exec_type, _ = ConditionEvaluator.replace_variables(task['exec'], self.global_vars, self.task_results, self.log_debug)
            self.log_debug(f"Task {task_display_id}{loop_display}: Using execution type from task: {exec_type}")
        elif self.exec_type:
            exec_type = self.exec_type
            self.log_debug(f"Task {task_display_id}{loop_display}: Using execution type from args: {exec_type}")
        elif 'TASK_EXECUTOR_TYPE' in os.environ:
            exec_type = os.environ['TASK_EXECUTOR_TYPE']
            self.log_debug(f"Task {task_display_id}{loop_display}: Using execution type from environment: {exec_type}")
        else:
            exec_type = self.default_exec_type
            self.log_debug(f"Task {task_display_id}{loop_display}: Using default execution type: {exec_type}")
        return exec_type

    def build_command_array(self, exec_type, hostname, command, arguments):
        """Build the command array based on execution type."""
        # Expand environment variables in arguments
        expanded_arguments = os.path.expandvars(arguments) if arguments else ""

        if exec_type == 'pbrun':
            return ["pbrun", "-n", "-h", hostname, command] + shlex.split(expanded_arguments)
        elif exec_type == 'p7s':
            return ["p7s", hostname, command] + shlex.split(expanded_arguments)
        elif exec_type == 'shell':
            # Execute via bash -c with command+arguments as a single shell script
            # This allows complex shell syntax: pipes, redirects, command substitution, etc.
            full_script = f"{command} {expanded_arguments}".strip()
            return ["/bin/bash", "-c", full_script]
        elif exec_type == 'local':
            return [command] + shlex.split(expanded_arguments)
        elif exec_type == 'wwrs':
            return ["wwrs_clir", hostname, command] + shlex.split(expanded_arguments)
        else:
            # Default to pbrun if unknown exec_type
            self.log_warn(f"Unknown execution type '{exec_type}', using default 'pbrun'")
            return ["pbrun", "-n", "-h", hostname, command] + shlex.split(expanded_arguments)

    def get_task_timeout(self, task):
        """Determine the timeout for a task, respecting priority order."""
        # Start with the default range
        min_timeout = 5
        max_timeout = 1000

        # Get timeout from task (highest priority)
        if 'timeout' in task:
            timeout_str, resolved = ConditionEvaluator.replace_variables(task['timeout'], self.global_vars, self.task_results, self.log_debug)
            if resolved:
                try:
                    timeout = int(timeout_str)
                    self.log_debug(f"Using timeout from task: {timeout}")
                except ValueError:
                    self.log_warn(f"Invalid timeout value in task: '{timeout_str}'. Using default.")
                    timeout = self.timeout
            else:
                self.log_warn(f"Unresolved variables in timeout. Using default.")
                timeout = self.timeout

        # Get timeout from command line argument (medium priority)
        elif self.timeout:
            timeout = self.timeout
            self.log_debug(f"Using timeout from command line: {timeout}")

        # Get timeout from environment (lower priority)
        elif 'TASK_EXECUTOR_TIMEOUT' in os.environ:
            try:
                timeout = int(os.environ['TASK_EXECUTOR_TIMEOUT'])
                self.log_debug(f"Using timeout from environment: {timeout}")
            except ValueError:
                self.log_warn(f"Invalid timeout value in environment: '{os.environ['TASK_EXECUTOR_TIMEOUT']}'. Using default.")
                timeout = 30

        # Use default timeout (lowest priority)
        else:
            timeout = 30
            self.log_debug(f"Using default timeout: {timeout}")

        # Ensure timeout is within valid range
        if timeout < min_timeout:
            self.log_warn(f"Timeout {timeout} too low, using minimum {min_timeout}")
            timeout = min_timeout
        elif timeout > max_timeout:
            self.log_warn(f"Timeout {timeout} too high, using maximum {max_timeout}")
            timeout = max_timeout
        return timeout

    def categorize_task_result(self, result):
        """Categorize task result for retry logic."""
        return self._result_collector.categorize_task_result(result)

    def parse_retry_config(self, parallel_task):
        """Parse retry configuration from parallel task."""
        if parallel_task.get('retry_failed', '').lower() != 'true':
            return None
            
        try:
            # Resolve global variables first before int conversion
            retry_count_str, _ = ConditionEvaluator.replace_variables(parallel_task.get('retry_count', '1'), self.global_vars, self.task_results, self.log_debug)
            retry_delay_str, _ = ConditionEvaluator.replace_variables(parallel_task.get('retry_delay', '1'), self.global_vars, self.task_results, self.log_debug)
        
            retry_count = int(retry_count_str)
            retry_delay = int(retry_delay_str)
            
            # Validate retry parameters
            if retry_count < 0 or retry_count > 10:
                self.log_warn(f"retry_count {retry_count} out of range (0-10), using 1")
                retry_count = 1
                
            if retry_delay < 0 or retry_delay > 300:
                self.log_warn(f"retry_delay {retry_delay} out of range (0-300), using 1")
                retry_delay = 1
                
            return {
                'count': retry_count,
                'delay': retry_delay
            }
        except ValueError as e:
            self.log_warn(f"Invalid retry configuration: {str(e)}. Retry disabled.")
            return None

    # Unified execution helpers
    def get_execution_context(self):
        """Create ExecutionContext for simplified callback passing."""
        from ..core.execution_context import ExecutionContext
        return ExecutionContext(self)

    def _execute_task_core(self, task, master_timeout=None, context="normal", retry_display=""):
        """Unified task execution core using ExecutionContext."""
        from ..executors.base_executor import BaseExecutor
        
        execution_context = self.get_execution_context()
        return BaseExecutor.execute_task_core(task, execution_context, master_timeout, context, retry_display)


    # ===== 6. PARALLEL TASK EXECUTION =====
    
    def execute_parallel_tasks(self, parallel_task):
        """Execute multiple tasks in parallel with enhanced retry logic and improved logging."""
        return ParallelExecutor.execute_parallel_tasks(parallel_task, self)

    def check_parallel_next_condition(self, parallel_task, results):
        """Check next condition for parallel tasks with simplified syntax."""
        task_id = int(parallel_task['task'])
        
        if 'next' not in parallel_task:
            # No explicit next condition - use overall success (all must succeed)
            successful_count = len([r for r in results if r['success']])
            total_count = len(results)
            should_continue = successful_count == total_count
            self.log_info(f"Task {task_id}: No 'next' condition, using all_success logic: "
                    f"{successful_count}/{total_count} = {should_continue}")
            return should_continue
            
        next_condition = parallel_task['next']
        self.log_debug(f"Task {task_id}: Evaluating 'next' condition: {next_condition}")
        
        # Special cases
        if next_condition == 'never':
            self.log_info(f"Task {task_id}: 'next=never' found, stopping execution")
            return "NEVER"

        if next_condition == 'always':
            self.log_info(f"Task {task_id}: 'next=always' found, proceeding to next task")
            return True

        if next_condition == 'loop' and 'loop' in parallel_task:
            # Handle loop logic (reuse existing loop logic but with parallel results)
            return self.handle_parallel_loop(parallel_task, results)
        
        # Handle backwards compatibility for 'success' - treat as 'all_success'
        if next_condition == 'success':
            self.log_info(f"Task {task_id}: Legacy 'success' condition treated as 'all_success'")
            result = ParallelExecutor.evaluate_parallel_next_condition(
                'all_success', results, self.log_debug, self.log_info)
            self.log_debug(f"Task {task_id}: Condition 'success' (-> all_success) evaluated to: {result}")
            return result
        
        # Handle parallel-specific conditions (simplified syntax)
        parallel_conditions = ['all_success', 'any_success', 'majority_success']
        if next_condition in parallel_conditions or '=' in next_condition:
            result = ParallelExecutor.evaluate_parallel_next_condition(
                next_condition, results, self.log_debug, self.log_info)
            self.log_debug(f"Task {task_id}: Condition '{next_condition}' evaluated to: {result}")
            return result
        
        # Handle complex condition expressions (delegate to existing logic)
        # Use aggregated results for complex expressions
        successful_count = len([r for r in results if r['success']])
        failed_count = len([r for r in results if not r['success']])
        
        aggregated_exit_code = 0 if successful_count == len(results) else 1
        aggregated_stdout = (f"Parallel execution summary: {successful_count} successful, "
                           f"{failed_count} failed")
        failed_task_ids = [r['task_id'] for r in results if not r['success']]
        aggregated_stderr = f"Failed tasks: {failed_task_ids}" if failed_count > 0 else ""
        
        result = ConditionEvaluator.evaluate_condition(
            next_condition, aggregated_exit_code, aggregated_stdout, aggregated_stderr, 
            self.global_vars, self.task_results, self.log_debug)
        self.log_info(f"Task {task_id}: Complex condition '{next_condition}' evaluated to: {result}")
        return result

    def handle_parallel_loop(self, parallel_task, results):
        """Handle loop logic for parallel tasks."""
        task_id = int(parallel_task['task'])
        
        # Check if this is the first time we're seeing this task
        if task_id not in self.loop_counter:
            self.loop_counter[task_id] = int(parallel_task['loop'])
            self.loop_iterations[task_id] = 1
            self.log_info(f"Task {task_id}: Loop initialized with count {self.loop_counter[task_id]}")
        else:
            self.loop_iterations[task_id] += 1

        # Check loop_break condition first (if exists)
        if 'loop_break' in parallel_task:
            # For parallel tasks, evaluate loop_break against aggregated results
            successful_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            aggregated_exit_code = 0 if successful_count == len(results) else 1
            aggregated_stdout = (f"Parallel execution summary: {successful_count} successful, "
                               f"{failed_count} failed")
            aggregated_stderr = ""
            
            loop_break_result = ConditionEvaluator.evaluate_condition(
                parallel_task['loop_break'], aggregated_exit_code, aggregated_stdout, 
                aggregated_stderr, self.global_vars, self.task_results, self.log_debug)
            if loop_break_result:
                self.log_info(f"Task {task_id}: Breaking loop - condition "
                        f"'{parallel_task['loop_break']}' satisfied")
                del self.loop_counter[task_id]
                del self.loop_iterations[task_id]
                return True

        # Decrement the counter
        self.loop_counter[task_id] -= 1
        
        if self.loop_counter[task_id] >= 0:
            self.log_debug(f"Task {task_id}: Looping (iteration {self.loop_iterations[task_id]}, "
                    f"{self.loop_counter[task_id]} remaining)")
            return "LOOP"
        else:
            self.log_info(f"Task {task_id}: Loop complete - max iterations reached")
            del self.loop_counter[task_id]
            del self.loop_iterations[task_id]
            return True
    
    def execute_conditional_tasks(self, conditional_task):
        """Execute conditional tasks based on condition evaluation - sequential execution."""
        return ConditionalExecutor.execute_conditional_tasks(conditional_task, self)

    # ===== 7. SEQUENTIAL TASK EXECUTION =====
    
    def check_next_condition(self, task, exit_code, stdout, stderr, current_task_success=None):
        """
        Check if the 'next' condition is satisfied.
        Return True if we should proceed to the next task, False otherwise.
        Also return a special value for 'never' to distinguish it from normal failure.
        """

        task_id = int(task['task'])

        # Get loop iteration display if looping
        loop_display = ""
        if task_id in self.loop_iterations:
            loop_display = f".{self.loop_iterations[task_id]}"

        if 'next' not in task:
            # When on_success/on_failure are present but next is not, use the success result for routing
            if ('on_success' in task or 'on_failure' in task):
                # Use the provided success status if available (this is the evaluated success condition)
                if current_task_success is not None:
                    self.log_info(f"Task {task_id}{loop_display}: No 'next' condition specified, using success evaluation for routing: {current_task_success}")
                    return current_task_success
                else:
                    # Fallback to exit code if no explicit success evaluation was provided
                    success_by_exit = (exit_code == 0)
                    self.log_info(f"Task {task_id}{loop_display}: No 'next' condition specified, using exit code for routing: {success_by_exit}")
                    return success_by_exit
            else:
                # No routing parameters at all - continue to next sequential task
                self.log_info(f"Task {task_id}{loop_display}: No 'next' condition specified, proceeding to next task")
                return True  # Default to True if not specified
            
        next_condition = task['next']

        # Special cases
        if next_condition == 'never':
            self.log_info(f"Task {task_id}{loop_display}: 'next=never' found, stopping execution")
            return "NEVER"  # Special case

        if next_condition == 'always':
            self.log_info(f"Task {task_id}{loop_display}: 'next=always' found, proceeding to next task")
            return True

        # Handle the loop case with simplified syntax
        if next_condition == 'loop' and 'loop' in task:
            # Check if this is the first time we're seeing this task
            if task_id not in self.loop_counter:
                # Use StateManager methods if available, otherwise fallback to direct assignment
                if hasattr(self, '_state_manager'):
                    self._state_manager.set_loop_counter(task_id, int(task['loop']))
                    self._state_manager.set_loop_iteration(task_id, 1)
                else:
                    self._loop_counter_fallback[task_id] = int(task['loop'])
                    self._loop_iterations_fallback[task_id] = 1

                self.log_info(f"Task {task_id}{loop_display}: Loop initialized with count "
                        f"{int(task['loop'])}")
            else:
                # Increment iteration counter
                if hasattr(self, '_state_manager'):
                    current_iterations = self._state_manager.get_loop_iteration(task_id)
                    self._state_manager.set_loop_iteration(task_id, current_iterations + 1)
                else:
                    self._loop_iterations_fallback[task_id] += 1

            # Check loop_break condition first (if exists)
            if 'loop_break' in task:
                loop_break_result = ConditionEvaluator.evaluate_condition(
                    task['loop_break'], exit_code, stdout, stderr, 
                    self.global_vars, self.task_results, self.log_debug)
                if loop_break_result:
                    # Break condition met
                    self.log_info(f"Task {task_id}: Breaking loop - loop_break condition "
                            f"'{task['loop_break']}' satisfied")
                    if hasattr(self, '_state_manager'):
                        self._state_manager.clear_loop_tracking(task_id)
                    else:
                        self._loop_counter_fallback.pop(task_id, None)
                        self._loop_iterations_fallback.pop(task_id, None)
                    self.log_info(f"Task {task_id}: Loop complete, proceeding to next task")
                    return True  # Proceed to next task

            # Decrement the counter
            if hasattr(self, '_state_manager'):
                remaining = self._state_manager.decrement_loop_counter(task_id)
                current_iteration = self._state_manager.get_loop_iteration(task_id)
            else:
                self._loop_counter_fallback[task_id] -= 1
                remaining = self._loop_counter_fallback[task_id]
                current_iteration = self._loop_iterations_fallback[task_id]

            # If counter is still >= 0, continue looping
            if remaining >= 0:
                self.log_debug(f"Task {task_id}: Looping (iteration {current_iteration}, "
                        f"{remaining} remaining)")
                return "LOOP"  # Trigger the loop
            else:
                # Max iterations reached
                self.log_info(f"Task {task_id}: Loop complete - max iterations reached")
                if hasattr(self, '_state_manager'):
                    self._state_manager.clear_loop_tracking(task_id)
                else:
                    self._loop_counter_fallback.pop(task_id, None)
                    self._loop_iterations_fallback.pop(task_id, None)
                return True  # Proceed to next task
        
        # Parse complex conditions
        result = ConditionEvaluator.evaluate_condition(
            next_condition, exit_code, stdout, stderr, self.global_vars, 
            self.task_results, self.log_debug, current_task_success)
        if result:
            self.log_info(f"Task {task_id}{loop_display}: Proceeding to next task ({next_condition}=TRUE)")
        else:
            self.log_info(f"Task {task_id}{loop_display}: Stopping execution ({next_condition}=FALSE)")

        return result

    def execute_task(self, task):
        """Execute a single task and return whether to continue to the next task."""
        return SequentialExecutor.execute_task(task, self)

    # ===== 8. MAIN ORCHESTRATION =====
    
    def run(self):
        """Execute all tasks based on their flow control."""

        self.parse_task_file()

        # Check for shutdown after parsing
        self._check_shutdown()

        if not self.tasks:
            self.log_warn("No valid tasks found. Exiting.")
            self.cleanup() # clean up resources before exit
            ExitHandler.exit_with_code(ExitCodes.NO_TASKS_FOUND, "No valid tasks to execute", False)

        # Conditional validation based on resume mode
        # IMPORTANT: Validation must happen BEFORE showing execution plan
        if not self.skip_task_validation:
            validation_successful = self.validate_tasks()
            if not validation_successful:
                ExitHandler.exit_with_code(ExitCodes.TASK_FILE_VALIDATION_FAILED, "Task file validation failed", False)
            # Add shutdown check after potentially long operation
            self._check_shutdown()
        else:
            self.log_info("# Skipping task file validation due to --skip_task_validation flag")

        # Show execution plan if requested (AFTER validation passes)
        if self.show_plan:
            self.show_execution_plan()

        # Additional validation for --start-from
        if self.start_from_task is not None:
            if not self.validate_start_from_task(self.start_from_task):
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, "Start-from task validation failed", False)
            # Optional: Add shutdown check after start-from validation
            self._check_shutdown()

        # Conditional task dependency validation
        if not self.skip_task_validation:
            self.validate_task_dependencies()
            # Check for shutdown after dependency validation
            self._check_shutdown()
        else:
            self.log_info("# Skipping task dependency validation due to --skip_task_validation flag")

        # Conditional host validation
        if not self.skip_host_validation:
            validated_hosts = HostValidator.validate_hosts(
                self.tasks, 
                self.global_vars, 
                self.task_results, 
                self.exec_type, 
                self.default_exec_type, 
                True,  # Always check connectivity for remote hosts
                self.log_debug if self.log_level == 'DEBUG' else None,  # Only detailed output in debug mode
                self.log_info
            )
            
            # Handle new return format
            if isinstance(validated_hosts, dict) and 'error' in validated_hosts:
                # Extract the specific exit code
                exit_code = validated_hosts.get('exit_code', ExitCodes.HOST_VALIDATION_FAILED)
                self.log_error("Host validation failed. Exiting.")
                self.cleanup()
                ExitHandler.exit_with_code(exit_code, "Host validation failed", False)
            elif validated_hosts is False:
                # Legacy compatibility
                self.log_error("Host validation failed. Exiting.")
                self.cleanup()
                ExitHandler.exit_with_code(ExitCodes.HOST_VALIDATION_FAILED, "Host validation failed", False)
            # Check for shutdown after host validation
            self._check_shutdown()
        else:
            self.log_warn("# WARNING: Skipping host validation due to --skip-host-validation flag")
            self.log_warn("# WARNING: Using hostnames as-is without FQDN resolution or reachability check")
            # Create dummy validated_hosts dict for resume mode
            validated_hosts = {}
    
        # For resume mode, collect hostnames but don't validate them
        for task in self.tasks.values():
            if 'hostname' in task and task['hostname']:
                hostname, resolved = ConditionEvaluator.replace_variables(task['hostname'], self.global_vars, self.task_results, self.log_debug)
                if resolved and hostname:
                    validated_hosts[hostname] = hostname  # Use as-is without validation

        # Replace hostnames with validated FQDNs in all tasks
        # Conditional hostname FQDN replacement
        if not self.skip_host_validation and validated_hosts:
            # Only replace hostnames if we actually validated them
            for task_id, task in self.tasks.items():
                if 'hostname' in task and task['hostname'] in validated_hosts:
                    orig_hostname = task['hostname']
                    fqdn = validated_hosts[orig_hostname]
                    if orig_hostname != fqdn:
                        self.log_debug(f"Replacing hostname '{orig_hostname}' with validated FQDN '{fqdn}'")
                        task['hostname'] = fqdn
        elif self.skip_host_validation:
            self.log_info("# Skipping hostname FQDN replacement due to --skip-host-validation flag")

        # If validate-only mode, exit after all validations complete
        if self.validate_only:
            self.log_info("# All validations completed successfully")
            self.log_info("# Validate-only mode: exiting without task execution")
            ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Validation completed", False)

        # Determine starting task ID
        if self.start_from_task is not None:
            start_task_id = self.start_from_task
            
            # Validate that start task exists
            if start_task_id not in self.tasks:
                self.log_error(f"Start task {start_task_id} not found in task definitions")
                available_tasks = sorted(self.tasks.keys())
                self.log_error(f"Available tasks: {available_tasks}")
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, f"Start task {start_task_id} not found", False)
            
            # Warning about unresolved dependencies
            if start_task_id > 0:
                self.log_warn(f"# WARNING: Task dependencies @X_stdout@, @X_stderr@, @X_success@ for tasks 0-{start_task_id-1} will be unresolved")
                self.log_warn(f"# Tasks {start_task_id}+ may fail if they depend on results from earlier tasks")
                
            self.log_info(f"# Starting execution from Task {start_task_id}")
        else:
            start_task_id = 0

        next_task_id = start_task_id
        tasks_executed_count = 0  # Track how many tasks actually executed

        # HYBRID STARTING STRATEGY: Try starting task, auto-fallback for user-friendliness
        if next_task_id not in self.tasks:
            available_tasks = sorted(self.tasks.keys())

            # If user explicitly specified --start-from, fail strictly
            if self.start_from_task is not None:
                self.log_error(f"Starting task {next_task_id} not found in task definitions")
                self.log_error(f"Available tasks: {available_tasks}")
                if available_tasks:
                    suggested_start = available_tasks[0]
                    self.log_error(f"Suggestion: Use --start-from {suggested_start} or add task {next_task_id} to the file")
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, f"Starting task {next_task_id} not found", False)

            # Auto-fallback for user-friendliness when defaulting to task 0
            elif available_tasks and next_task_id == 0:
                auto_start = available_tasks[0]
                self.log_info(f"Task 0 not found, auto-starting from lowest available task {auto_start}")
                if auto_start > 0:
                    self.log_warn(f"# WARNING: Task dependencies @X_stdout@, @X_stderr@, @X_success@ for tasks 0-{auto_start-1} will be unresolved")
                    self.log_warn(f"# Tasks {auto_start}+ may fail if they depend on results from earlier tasks")
                next_task_id = auto_start
            else:
                # No tasks available at all
                self.log_error(f"Starting task {next_task_id} not found in task definitions")
                self.log_error(f"Available tasks: {available_tasks}")
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, f"No executable tasks found", False)

        while next_task_id is not None and next_task_id in self.tasks:  # Changed condition
            # Check for shutdown before each task
            self._check_shutdown()

            task = self.tasks[next_task_id]
            if task is None:
                self.log_error(f"Task {next_task_id}: Task not found. Stopping.")
                break

            result = self.execute_task(task)
            tasks_executed_count += 1  # Increment count for each task executed

            # handle the special LOOP case
            if result == "LOOP":
                continue # Re-execute the same task

            # Otherwise, update the next_task_id normally
            next_task_id = result

        # Check how we exited the loop
        if next_task_id is None:
            # We exited because a task returned None (either 'next=never' or end of task sequence)
            if self.current_task in self.tasks:
                last_task = self.tasks[self.current_task]
                if 'next' in last_task and last_task['next'] == 'never':
                    # This is a successful completion with 'next=never'
                    self.log_info("SUCCESS: Task execution completed successfully with 'next=never'.")
                elif tasks_executed_count > 0:
                    # This is a successful completion - we reached the end of the task sequence
                    self.log_info(f"SUCCESS: Task execution completed successfully - {tasks_executed_count} task(s) executed.")
                else:
                    # This shouldn't happen, but handle it anyway
                    self.log_error("FAILED: Task execution stopped with no tasks executed.")
                    # Write summary before exiting
                    if self.summary_log and self.final_task_id is not None:
                        try:
                            self.write_final_summary()
                        except Exception as e:
                            self.log_warn(f"Failed to write final summary: {e}")
                    ExitHandler.exit_with_code(ExitCodes.TASK_FAILED, "No tasks executed", False)
            else:
                # We don't have a current task reference, but if we executed tasks, it's a success
                if tasks_executed_count > 0:
                    self.log_info(f"SUCCESS: Task execution completed successfully - {tasks_executed_count} task(s) executed.")
                else:
                    self.log_error("FAILED: Task execution stopped with no tasks executed.")
                    # Write summary before exiting
                    if self.summary_log and self.final_task_id is not None:
                        try:
                            self.write_final_summary()
                        except Exception as e:
                            self.log_warn(f"Failed to write final summary: {e}")
                    ExitHandler.exit_with_code(ExitCodes.TASK_FAILED, "No tasks executed", False)

            # Write summary before exiting (for success cases)
            if self.summary_log and self.final_task_id is not None:
                try:
                    self.write_final_summary()
                except Exception as e:
                    self.log_warn(f"Failed to write final summary: {e}")
            ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Task execution completed successfully", False)
        elif next_task_id not in self.tasks:  # Changed condition
            # Check if we actually executed any tasks
            if tasks_executed_count == 0:
                available_tasks = sorted(self.tasks.keys())
                self.log_error("FAILED: No tasks were executed.")
                self.log_error(f"Available tasks in file: {available_tasks}")
                if available_tasks:
                    suggested_start = available_tasks[0]
                    self.log_error(f"Suggestion: Use --start-from {suggested_start} to start from the first available task")
                self.log_error("This often occurs when using --skip-task-validation with files that don't start from task 0")
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, "No tasks executed", False)
            else:
                # We've successfully completed tasks
                self.log_info(f"SUCCESS: Task execution completed - {tasks_executed_count} task(s) executed successfully.")
                # Write summary before exiting
                if self.summary_log and self.final_task_id is not None:
                    try:
                        self.write_final_summary()
                    except Exception as e:
                        self.log_warn(f"Failed to write final summary: {e}")
                ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Task execution completed successfully", False)
        else:
            # Something else stopped execution
            self.log_error("FAILED: Task execution stopped for an unknown reason.")
            # Write summary before exiting
            if self.summary_log and self.final_task_id is not None:
                try:
                    self.write_final_summary()
                except Exception as e:
                    self.log_warn(f"Failed to write final summary: {e}")
            ExitHandler.exit_with_code(ExitCodes.TASK_FAILED, "Task execution stopped for unknown reason", False)