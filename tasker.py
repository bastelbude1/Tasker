#!/usr/bin/env python3

"""
Server Task Executor (Linux Only) - Enhanced with Conditional Tasks
-------------------
This script reads a task file with instructions to execute commands on remote servers,
handles flow control based on various conditions, and logs results.
Enhanced with global variable support using @VARIABLE@ syntax, PARALLEL TASKS, and CONDITIONAL TASKS.
CRITICAL: Thread-safety fixes applied for task_results access.
NEW: Master Timeout Only enforcement for parallel tasks - individual timeouts are overridden.
NEW: Retry Logic for failed parallel tasks only (retry_failed=true).
NEW: Enhanced Retry Logging with Attempt Numbering (.N notation) for parallel tasks.
NEW: CONDITIONAL TASKS - Execute different task sequences based on conditions.
IMPROVED: Better parallel task logging for readability.
"""

import os
import sys

# Add the current directory to the path to ensure task_validator can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import re
import time
import argparse
import subprocess
from datetime import datetime
import time
import shlex
import socket
import shutil
import fcntl # Linux Only
import threading
import errno 
import signal 
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from our library package
from tasker.core.utilities import (
    sanitize_filename,
    get_log_directory,
    ExitCodes,
    ExitHandler,
    convert_value,
    convert_to_number,
    sanitize_for_tsv
)
from tasker.core.condition_evaluator import ConditionEvaluator

try:
   from task_validator import TaskValidator
except ImportError:
   TaskValidator = None  # Handle the case where task_validator isn't available


class TaskExecutor:
    
    # ===== 1. CLASS LIFECYCLE =====
    
    def __init__(self, task_file, log_dir='logs', dry_run=True, debug=False, exec_type=None, timeout=30, connection_test=False, project = None, start_from_task=None, skip_task_validation=False, skip_host_validation=False, show_plan=False):
        self.task_file = task_file
        self.log_dir = log_dir
        self.dry_run = dry_run
        self.debug = debug
        self.tasks = {}  # Changed to dictionary for sparse task IDs
        self.task_results = {}
        self.current_task = 0 # Track current task
        self.loop_counter = {} # Track remaining loops
        self.loop_iterations = {} # Track current iteration number
        self.exec_type = exec_type  # From command line argument
        self.default_exec_type = 'pbrun'  # Default execution type
        self.timeout = timeout # Default timeout from command line
        self.connection_test = connection_test # Whether to make an connection test
        self.project = sanitize_filename(project) if project else None # get an sanitized project name if one exists
        self.show_plan = show_plan

        # NEW: Configurable timeouts for cleanup and summary operations
        self.summary_lock_timeout = 20  # Seconds for summary file locking (longer for shared files)
        # Adjust timeouts based on system load or user preference
        if os.environ.get('TASK_EXECUTOR_HIGH_LOAD'):
            self.summary_lock_timeout = 45

        # NEW: Global variables support
        self.global_vars = {}  # Store global variables
        
        # NEW: Thread safety for logging
        self.log_lock = threading.Lock()
        
        # CRITICAL: Thread safety for task results
        self.task_results_lock = threading.Lock()
        
        # NEW: Simple shutdown handling
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # NEW: Track current parallel task for improved logging
        self._current_parallel_task = None
        
        # NEW: Track current conditional task for improved logging
        self._current_conditional_task = None

        # NEW: Resume capability parameters
        self.start_from_task = start_from_task
        self.skip_task_validation = skip_task_validation
        self.skip_host_validation = skip_host_validation

        # NEW: Log resume information
        if self.start_from_task is not None:
            self.log(f"# Resume mode: Starting from Task {self.start_from_task}")
            if self.skip_task_validation:
                self.log(f"# Task Validation will be skipped")
            if self.skip_host_validation:
                self.log(f"# Host Validation will be skipped - ATTENTION")

        # Initialize summary tracking variables
        self.final_task_id = None
        self.final_exit_code = None
        self.final_success = None
        self.final_hostname = None
        self.final_command = None

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

        # Copy the task file to the tasks directory as backup
        try:
            task_filename = os.path.basename(task_file)
            task_copy_path = os.path.join(self.log_dir, f"{task_filename}_{timestamp}")
            shutil.copy2(task_file, task_copy_path)
            self.debug_log(f"Created task file copy: {task_copy_path}")
        except Exception as e:
            self.debug_log(f"Warning: Could not copy task file to tasks directory: {str(e)}")

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

        # Start loggin task exec
        self.log(f"=== Task Execution Start: {timestamp} ===")
        self.log(f"# Task file: {task_file}")

        if self.exec_type:
            exec_type=self.exec_type
            self.log(f"# Execution type from args: {exec_type}")
        elif 'TASK_EXECUTOR_TYPE' in os.environ:
            exec_type = os.environ.get('TASK_EXECUTOR_TYPE')
            self.log(f"# Execution type from environment: {exec_type}")
        else:
            exec_type = self.default_exec_type
            self.log(f"# Execution type (Default): {exec_type} (if not overriden by task)")

        if dry_run: self.log(f"# Dry run mode")
        self.log(f"# Default timeout: {timeout} [s]")
    
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
                            self.log(f"Info: Summary file '{self.project}.summary' is currently in use by another tasker instance.")
                            self.log(f"Summary writes will wait for the other instance to complete.")
                except Exception:
                    pass  # Ignore test errors

    def __enter__(self):
        """Enable use of the class as a context manager"""
        return self;

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up ressources when exiting the context manager"""
        self.cleanup()
        return False # Dont suppress exceptions

    # --- cleanup
    def cleanup(self):
        """
        Timeout-geschuetzter cleanup().
        """
        cleanup_errors = []

        # PHASE 1: Log file cleanup (unveraendert)
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

        # PHASE 2: FIXED - Timeout-geschuetzter Summary log cleanup
        if hasattr(self, 'summary_log'):
            try:
                # Step 1: TIMEOUT-GESCHueTZTER final summary write
                if (self.summary_log and not self.summary_log.closed and 
                    self.final_task_id is not None):
                    try:
                        # NEUE METHODE mit 5s Timeout
                        self.write_final_summary_with_timeout(5)
                    
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
        
                # Step 2: Summary file close (unveraendert)
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

        # PHASE 3: Error reporting (unveraendert)
        if cleanup_errors:
            error_count = len(cleanup_errors)
            error_summary = f"Cleanup completed with {error_count} error(s):"
            for i, error in enumerate(cleanup_errors, 1):
                error_summary += f"\n  {i}. {error}"
    
            self._safe_error_report(error_summary)

    def _signal_handler(self, signum, frame):
        """Simple signal handler - just set flag and log"""
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.log(f"Received {signal_name}, initiating graceful shutdown...")
        self._shutdown_requested = True
    
        # Store signal info for summary
        self._shutdown_signal = signal_name

    def _check_shutdown(self):
        """Check if shutdown was requested - call at natural breakpoints"""
        if self._shutdown_requested:
            self.log("Graceful shutdown requested - stopping execution")
        
            # NEW: Ensure summary gets written for graceful shutdown
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
                if not 'graceful_shutdown' in str(self.final_command):
                    # Add signal info to command if available
                    signal_info = getattr(self, '_shutdown_signal', 'SIGNAL')
                    self.final_command = f"{self.final_command} [GRACEFUL_SHUTDOWN_{signal_info}]"
        
            self.cleanup()
            ExitHandler.exit_with_code(ExitCodes.SIGNAL_INTERRUPT, "Task execution interrupted by signal", self.debug)

    def __del__(self):
        if hasattr(self, 'log_file') and self.log_file:
            self.log(f"# Log file: {self.log_file_path}")
            self.log("=== Task Execution End: {} ===".format(datetime.now().strftime('%d%b%y_%H%M%S')))
            self.log_file.close()
            self.log_file = None
    
    # ===== 2. CORE UTILITIES =====
    
    # Thread-safe helpers
    def store_task_result(self, task_id, result):
        """Thread-safe method to store task results."""
        with self.task_results_lock:
            self.task_results[task_id] = result
            
    def get_task_result(self, task_id):
        """Thread-safe method to get task results."""
        with self.task_results_lock:
            return self.task_results.get(task_id)
            
    def has_task_result(self, task_id):
        """Thread-safe method to check if task result exists."""
        with self.task_results_lock:
            return task_id in self.task_results
    
    # Logging
    def log(self, message):
        """Log a message to the log file and print to console with thread safety."""
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
    
        # NEW: Thread-safe logging with reentrancy protection
        with self.log_lock:
            print(log_message)
            if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
                self.log_file.write(log_message + "\n")
                self.log_file.flush()

    def _log_direct(self, message):
        """Direct logging without acquiring log_lock - for internal use only."""
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
    
        # Direct write without lock - caller must ensure thread safety
        print(log_message)
        if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
            self.log_file.write(log_message + "\n")
            self.log_file.flush()

    def debug_log(self, message):
        """Log a debug message if debug mode is enabled."""
        if self.debug:
            self.log(f"DEBUG: {message}")

    # --- write_final_summary -helper

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
                with tempfile.NamedTemporaryFile(mode='w', prefix='tasker_error_', delete=False) as f:
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
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        with open(emergency_file, 'a') as f:
            f.write(f"[{timestamp}] EMERGENCY: {message}\n")

    def _acquire_file_lock_atomically(self, timeout_seconds=5):
        """
        ATOMARE Lock-Akquisition mit Retry - eliminiert Race Conditions.
        Produktionstaugliche Loesung mit Retry-Logik.
        """
        try:
            # Atomare Validierung und Lock-Akquisition in einem Schritt
            if (not hasattr(self, 'summary_log') or not self.summary_log or 
                self.summary_log.closed):
                return None, False
            
            file_no = self.summary_log.fileno()
        
            # RETRY-LOOP mit Timeout (wie in der originalen Methode)
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(file_no, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return file_no, True
                
                except (OSError, IOError) as e:
                    if e.errno in (errno.EAGAIN, errno.EACCES):
                        # File ist gesperrt - pruefe Timeout
                        elapsed = time.time() - start_time
                        if elapsed >= timeout_seconds:
                            return None, False  # Timeout erreicht
                        time.sleep(0.1)  # Kurz warten, dann retry
                        continue
                    else:
                        # Anderer Fehler (EBADF, etc.) - File Handle ungueltig
                        return None, False
                
        except Exception:
            # Jeder andere Fehler - safe fallback
            return None, False

    def write_final_summary_with_timeout(self, timeout_seconds=5):
        """
        Thread-basierter Timeout for cleanup() - vermeidet Signal-Konflikte.
        Minimale, robuste Losung for Produktionsumgebung.
        """
        import threading
    
        result = {'completed': False, 'error': None}
    
        def write_worker():
            try:
                self.write_final_summary()
                result['completed'] = True
            except Exception as e:
                result['error'] = e
    
        # Starte Write-Operation in separatem Thread  
        worker_thread = threading.Thread(target=write_worker, daemon=True)
        worker_thread.start()
    
        # Warte mit Timeout
        worker_thread.join(timeout=timeout_seconds)
    
        if worker_thread.is_alive():
            # Thread lauft noch - Timeout erreicht
            raise TimeoutError(f"write_final_summary timeout after {timeout_seconds}s")
    
        if result['error']:
            # Exception im Worker-Thread
            raise result['error']
    
        if not result['completed']:
            # Unerwarteter Zustand
            raise RuntimeError("write_final_summary completed unexpectedly")

    # --- write_final_summary
    def write_final_summary(self):
        """
        Race-condition-freie Summary Write mit Retry-Logik.
        """
        # Schnelle Validierung und Exit
        if (not hasattr(self, 'summary_log') or not self.summary_log or 
            self.final_task_id is None):
            return
    
        # Message Vorbereitung AUSSERHALB der kritischen Sektion
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        status = "SUCCESS" if self.final_success else "FAILURE"
        log_file = os.path.basename(getattr(self, 'log_file_path', 'unknown.log'))
    
    
        fields = [
            timestamp,
            sanitize_for_tsv(os.path.basename(self.task_file)),
            sanitize_for_tsv(self.final_task_id),
            sanitize_for_tsv(self.final_hostname),
            sanitize_for_tsv(self.final_command),
            sanitize_for_tsv(self.final_exit_code),
            status,
            log_file
        ]
        message = '\t'.join(fields)
    
        # ATOMARE Lock-Akquisition und Write mit Retry
        with self.log_lock:
            # Verwende konfigurierbaren Timeout (wie in der Original-Methode)
            timeout_seconds = getattr(self, 'summary_lock_timeout', 20)
            file_no, lock_acquired = self._acquire_file_lock_atomically(timeout_seconds)
        
            if not lock_acquired:
                # Detaillierte Error-Message (wie in Original)
                project_name = getattr(self, 'project', 'unknown')
                raise TimeoutError(
                    f"Could not acquire lock on shared summary file '{project_name}.summary' "
                    f"within {timeout_seconds} seconds. Another tasker instance "
                    f"is currently writing to the summary file."
                )
        
            try:
                # Letzte Validierung nach Lock (Defense in Depth)
                if self.summary_log.closed:
                    raise ValueError("Summary log unexpectedly closed after lock acquisition")
                
                # Atomare Write-Operationen
                self.summary_log.seek(0, 2)  # End of file
                self.summary_log.write(f"{message}\n")
                self.summary_log.flush()
            
                # Verification (wie in Original)
                current_pos = self.summary_log.tell()
                if current_pos == 0:
                    raise IOError("Write verification failed - file position is 0")
                
            finally:
                # GARANTIERTE Lock-Freigabe
                if file_no is not None:
                    try:
                        fcntl.flock(file_no, fcntl.LOCK_UN)
                    except Exception:
                        # Lock wird beim Process-Exit automatisch freigegeben
                        pass

    # ===== 3. VALIDATION & SETUP =====
    
    def validate_tasks(self):
        """Validate the task file using TaskValidator."""
        if TaskValidator is None:
            self.log("Warning: TaskValidator not available. Skipping validation.")
            return True

        self.log(f"# Validating task file: {self.task_file}")

        try:
            # Create a validator instance
            validator = TaskValidator(self.task_file)

            # Run validation
            if validator.parse_file():
                validator.validate_tasks()

            # Get validation results
            has_errors = len(validator.errors) > 0

            # Log validation results
            if has_errors:
                self.log("# Task validation FAILED.")
                for error in validator.errors:
                    self.debug_log(f"# ERROR: {error}")

                # Also log warnings
                if validator.warnings:
                    for warning in validator.warnings:
                        self.debug_log(f"# WARNING: {warning}")
                return False

            else:
                self.log("# Task validation passed successfully.")
                # Log any warningsa

                if validator.warnings:
                    for warning in validator.warnings:
                        self.debug_log(f"# WARNING: {warning}")
                return True

        except Exception as e:
            self.log(f"Error during task validation: {str(e)}")
            return False

    def parse_task_file(self):
        """Parse the task file and extract global variables and task definitions."""
        if not os.path.exists(self.task_file):
            self.log(f"Error: Task file '{self.task_file}' not found.")
            ExitHandler.exit_with_code(ExitCodes.TASK_FILE_NOT_FOUND, f"Task file '{self.task_file}' not found", self.debug)
            
        with open(self.task_file, 'r') as f:
            lines = f.readlines()
        
        # PHASE 1: Collect global variables (first pass)
        self.log(f"# Parsing global variables from '{self.task_file}'")
        global_count = 0
        
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
                    self.global_vars[key] = value
                    global_count += 1
                    self.debug_log(f"Global variable: {key} = {value}")
        
        self.log(f"# Found {global_count} global variables")
        if self.debug and global_count > 0:
            for key, value in self.global_vars.items():
                self.debug_log(f"#   {key} = {value}")
        
        # PHASE 2: Parse tasks (second pass)
        current_task = None
        
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
                        self.tasks[task_id] = current_task
                    
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
            self.tasks[task_id] = current_task
        
        # Validate tasks - now we only check that required fields are present
        valid_task_count = 0
        for task_id, task in self.tasks.items():
            # NEW: Different validation for parallel and conditional tasks
            if task.get('type') == 'parallel':
                if 'tasks' not in task:
                    self.log(f"Warning: Parallel task {task_id} is missing required 'tasks' field.")
                    continue
                valid_task_count += 1
            elif task.get('type') == 'conditional':
                if 'condition' not in task:
                    self.log(f"Warning: Conditional task {task_id} is missing required 'condition' field.")
                    continue
                if 'if_true_tasks' not in task and 'if_false_tasks' not in task:
                    self.log(f"Warning: Conditional task {task_id} has no task branches defined.")
                    continue
                valid_task_count += 1
            else:
                if 'hostname' not in task and 'return' not in task:
                    self.log(f"Warning: Task {task_id} is missing required 'hostname' field.")
                    continue
                    
                if 'command' not in task and 'return' not in task:
                    self.log(f"Warning: Task {task_id} is missing required 'command' field.")
                    continue
                    
                valid_task_count += 1
            
        self.log(f"# Successfully parsed {valid_task_count} valid tasks from '{self.task_file}'")

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
            self.log("# WARNING: Task dependency issues detected:")
            for issue in dependency_issues:
                self.log(f"#   {issue}")
            self.log("# These may cause tasks to be skipped due to unresolved dependencies.")
            return False
        else:
            self.log("# Task dependency validation passed.")
            return True

    def validate_start_from_task(self, start_task_id):
        """Validate and provide warnings for --start-from usage."""
        if start_task_id not in self.tasks:
            available_tasks = sorted(self.tasks.keys())
            self.log(f"ERROR: Start task {start_task_id} not found")
            self.log(f"Available task IDs: {available_tasks}")
            return False
    
        # Check for potential dependency issues
        dependency_warnings = []
        pattern = r'@(\d+)_(stdout|stderr|success)@'
    
        for task_id in range(start_task_id, max(self.tasks.keys()) + 1):
            if task_id not in self.tasks:
                continue
            
            task = self.tasks[task_id]
            for field_name, field_value in task.items():
                if isinstance(field_value, str):
                    matches = re.findall(pattern, field_value)
                    for dep_task_str, dep_type in matches:
                        dep_task = int(dep_task_str)
                        if dep_task < start_task_id:
                            dependency_warnings.append(
                                f"Task {task_id} field '{field_name}' references @{dep_task}_{dep_type}@ (before start point)"
                            )
    
        if dependency_warnings:
            self.log(f"# DEPENDENCY WARNINGS for --start-from {start_task_id}:")
            for warning in dependency_warnings[:5]:  # Limit to first 5 warnings
                self.log(f"#   {warning}")
            if len(dependency_warnings) > 5:
                self.log(f"#   ... and {len(dependency_warnings) - 5} more dependency issues")
            self.log(f"# These tasks may fail due to unresolved variable references")
        
        return True
    def show_execution_plan(self):
        """Show execution plan and get user confirmation."""
        self.log("=== EXECUTION PLAN ===")
    
        # Determine starting point
        start_id = self.start_from_task if self.start_from_task is not None else 0
        if self.start_from_task is not None:
            self.log(f"# Resume mode: Starting from Task {start_id}")
    
        # Count and show tasks
        task_count = 0
        for task_id, task in sorted(self.tasks.items()):
            if task_id < start_id:
                continue
            
            task_count += 1
            task_type = task.get('type', 'normal')
        
            if task_type == 'parallel':
                tasks_str = task.get('tasks', '')
                self.log(f"  Task {task_id}: PARALLEL -> tasks [{tasks_str}]")
            elif task_type == 'conditional':
                condition = task.get('condition', 'N/A')
                self.log(f"  Task {task_id}: CONDITIONAL [{condition}]")
            elif 'return' in task:
                return_code = task.get('return', 'N/A')
                self.log(f"  Task {task_id}: RETURN {return_code}")
            else:
                hostname = task.get('hostname', 'N/A')
                command = task.get('command', 'N/A')
                self.log(f"  Task {task_id}: {hostname} -> {command}")
    
        self.log(f"# Total: {task_count} tasks to execute")
        self.log("=" * 50)
    
        # User confirmation
        if not self._get_user_confirmation():
            self.log("Execution cancelled by user.")
            ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Execution cancelled by user", self.debug)

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

    def validate_hosts(self, check_connectivity=False):
        """
        Validate all unique hostnames in the task list.
        Returns a dict mapping original hostnames to validated FQDNs if successfull,
        or False if validation failed.
        """

        # Collect unique hostnames from all tasks
        hostnames = set()
        host_exec_types = {}

        for task in self.tasks.values():  # Changed to iterate over values
            if 'hostname' in task and task['hostname']:
                # Replace variables in hostname before validation
                hostname, resolved = ConditionEvaluator.replace_variables(task['hostname'], self.global_vars, self.task_results, self.debug_log)
                if resolved and hostname:  # Only validate if variable resolution succeeded
                    hostnames.add(hostname)

                    # Track execution type for each hostname
                    if 'exec' in task:
                        exec_type = task['exec']
                    elif self.exec_type:
                        exec_type = self.exec_type
                    elif 'TASK_EXECUTOR_TYPE' in os.environ:
                        exec_type = os.environ['TASK_EXECUTOR_TYPE']
                    else:
                        exec_type = self.default_exec_type

                    # Store the exec type for this hostname
                    if hostname not in host_exec_types:
                        host_exec_types[hostname] = set()

                    host_exec_types[hostname].add(exec_type)

        # Check each unique hostname
        failed_hosts = []
        validated_hosts = {} # will map original hostnames to validated FQDNs

        self.log(f"# Validating {len(hostnames)} unique hostnames...")

        for hostname in hostnames:
            # Try to resolve hostname
            resolved, resolved_name = self.resolve_hostname(hostname)

            if not resolved:
                #self.debug_log(f"WARNING: Could not resolve hostname '{hostname}'")
                failed_hosts.append(hostname)
                continue

            # Store the resolved hostname
            validated_hosts[hostname] = resolved_name

            # Check if host is alive
            if not self.check_host_alive(resolved_name):
                self.debug_log(f"WARNING: Host '{hostname}' ({resolved_name}) is not reachable")
                failed_hosts.append(hostname)
                continue

            # If requested, check specific connection type
            if check_connectivity:
                conn_failed = False
                for exec_type in host_exec_types[hostname]:
                    if exec_type in ['pbrun', 'p7s', 'wwrs']:
                        if not self.check_exec_connection(exec_type, resolved_name):
                            self.debug_log(f"WARNING: Connection test failed for {exec_type} to '{hostname}' ({resolved_name})")
                            failed_hosts.append(f"{hostname} ({exec_type})")
                            conn_failed = True

                # if any connection test failed, don't consider this as an validated host 
                if conn_failed:
                    if hostname in validated_hosts:
                        del validated_hosts[hostname]

        # If any hosts failed validation, abort execution
        if failed_hosts:
            self.log(f"# ERROR: {len(failed_hosts)} host(s) failed validation: {', '.join(failed_hosts)}")
            return False

        self.log(f"# All {len(hostnames)} hosts passed successfully.")
        return validated_hosts

    def resolve_hostname(self, hostname):
        """Try to resolve hostname using DNS or op mc_isac if needed."""
        try:
            # Try direct DNS resolution first
            socket.gethostbyname(hostname)
            self.debug_log(f"Hostname '{hostname}' resolved via DNS")
            return True, hostname

        except socket.gaierror:
            self.debug_log(f"Hostname '{hostname}' not found in DNS, trying op mc_isac")
            try:
                # Try using op mc_isac to get FQDN
                with subprocess.Popen(
                    ["op", "mc_isac", "-f", hostname],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                ) as process:

                    try:
                        stdout, stderr = process.communicate(timeout=10)
                        if process.returncode == 0 and stdout.strip():
                            fqdn = stdout.strip()
                            self.debug_log(f"Resolved '{hostname}' to FQDN '{fqdn}' using op mc_isac")
                            return True, fqdn
                        else:
                            self.debug_log(f"ERROR: Could not resolve hostname '{hostname}' with op mc_isac: {stderr.strip()}")
                            return False, hostname

                    except subprocess.TimeoutExpired:
                        process.kill()
                        stdout, stderr = process.communicate()
                        self.debug_log(f"ERROR: op mc_isac for hostname '{hostname}' timed out")
                        return False, hostname

            except Exception as e:
                self.debug_log(f"ERROR: op mc_isac for hostname '{hostname}' failed: {str(e)}")
                return False, hostname

    def check_host_alive(self, hostname):
        """Check if host is reachable via ping."""
        try:
            # Use ping to check if host is alive
            if sys.platform == "win32":
                # Windows ping command
                ping_cmd = ["ping", "-n", "1", "-w", "1000", hostname]
            else:
                # Linux/Unix ping command
                ping_cmd = ["ping", "-c", "1", "-W", "1", hostname]

            with subprocess.Popen(
                ping_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            ) as process:

                try:
                    stdout, stderr = process.communicate(timeout=5)
                    self.debug_log(f"ping '{hostname}' is alive")
                    return process.returncode == 0
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    self.debug_log(f"ERROR: ping to '{hostname}' timed out")
                    return False

        except Exception as e:
            self.debug_log(f"ERROR: pinging host '{hostname}': {str(e)}")
            return False

    def check_exec_connection(self, exec_type, hostname):
        """Test connectivity for specific execution type."""
        if exec_type not in ['pbrun', 'p7s', 'wwrs']:
            # For local or unknown exec types, just return True
            return True

        # Build command array based on exec_type
        if exec_type == 'pbrun':
            cmd_array = ["pbrun", "-n", "-h", hostname, "pbtest"]
        elif exec_type == 'p7s':
            cmd_array = ["p7s", hostname, "pbtest"]
        elif exec_type == 'wwrs':
            cmd_array = ["wwrs_clir", hostname, "wwrs_test"]

        self.debug_log(f"Testing {exec_type} connection to '{hostname}' with: {' '.join(cmd_array)}")

        try:
            with subprocess.Popen(
                cmd_array,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            ) as process:

                try:
                    stdout, stderr = process.communicate(timeout=10)
                    success = process.returncode == 0 and "OK" in stdout
                    if success:
                        self.debug_log(f"{exec_type} connection to '{hostname}' successful")
                    else:
                        self.debug_log(f"ERROR: {exec_type} connection to '{hostname}' failed: {stderr.strip()}")
                    return success

                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    self.debug_log(f"ERROR: {exec_type} connection to '{hostname}' timed out")
                    return False

        except Exception as e:
            self.debug_log(f"ERROR: testing {exec_type} connection to '{hostname}': {str(e)}")
            return False

    # ===== 4. VARIABLE & CONDITION PROCESSING =====
    
        """
        Replace variables like @task_number_stdout@, @task_number_stderr@, @task_number_success@, 
        or @GLOBAL_VAR@ with actual values. Supports variable chaining like @PATH@/@SUBDIR@.
        CRITICAL: Thread-safe access to task_results.
        """
        if not text:
            return text, True  # Return text and resolution status
            
        # Enhanced pattern to match both task result variables and global variables
        task_result_pattern = r'@(\d+)_(stdout|stderr|success)@'
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'
        
        replaced_text = text
        unresolved_variables = []
        original_text = text
        
        # First, handle task result variables (@X_stdout@, etc.) - THREAD SAFE
        task_matches = re.findall(task_result_pattern, text)
        for task_num, output_type in task_matches:
            task_num = int(task_num)
            
            # CRITICAL: Thread-safe access to task_results
            task_result = self.get_task_result(task_num)
            if task_result is not None:
                if output_type == 'stdout':
                    value = task_result.get('stdout', '').rstrip('\n')
                elif output_type == 'stderr':
                    value = task_result.get('stderr', '').rstrip('\n')
                elif output_type == 'success':
                    value = str(task_result.get('success', False))
                else:
                    value = ''
                pattern_replace = f"@{task_num}_{output_type}@"
                replaced_text = replaced_text.replace(pattern_replace, value)
                self.debug_log(f"Replaced task variable {pattern_replace} with '{value}'")
            else:
                unresolved_variables.append(f"@{task_num}_{output_type}@")
        
        # Second, handle global variables (@VARIABLE_NAME@) - supports chaining
        global_matches = re.findall(global_var_pattern, replaced_text)
        for var_name in global_matches:
            # Skip if this is a task result variable (already handled above)
            if re.match(r'\d+_(stdout|stderr|success)$', var_name):
                continue
                
            # Check if it's a defined global variable
            if var_name in self.global_vars:
                value = self.global_vars[var_name]
                pattern_replace = f"@{var_name}@"
                replaced_text = replaced_text.replace(pattern_replace, value)
                self.debug_log(f"Replaced global variable @{var_name}@ with '{value}'")
            else:
                unresolved_variables.append(f"@{var_name}@")
        
        # Handle nested global variables (variable chaining support)
        # Keep replacing until no more global variables are found or max iterations reached
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            nested_matches = re.findall(global_var_pattern, replaced_text)
            nested_replaced = False
            
            for var_name in nested_matches:
                # Skip task result variables
                if re.match(r'\d+_(stdout|stderr|success)$', var_name):
                    continue
                    
                if var_name in self.global_vars:
                    value = self.global_vars[var_name]
                    pattern_replace = f"@{var_name}@"
                    replaced_text = replaced_text.replace(pattern_replace, value)
                    self.debug_log(f"Replaced nested global variable @{var_name}@ with '{value}' (iteration {iteration})")
                    nested_replaced = True
            
            # If no nested replacements were made, we're done
            if not nested_replaced:
                break
        
        # Final check for any remaining unresolved variables
        final_matches = re.findall(global_var_pattern, replaced_text)
        for var_name in final_matches:
            if not re.match(r'\d+_(stdout|stderr|success)$', var_name):
                if var_name not in self.global_vars:
                    unresolved_variables.append(f"@{var_name}@")
                
        if unresolved_variables:
            self.debug_log(f"Unresolved variables in '{original_text}': {', '.join(set(unresolved_variables))}")
            return replaced_text, False
        
        if original_text != replaced_text:
            self.debug_log(f"Variable replacement: '{original_text}' -> '{replaced_text}'")
        
        return replaced_text, True

    def split_output(self, output, split_spec):
        """Split the output based on the specification and return the selected part."""
        if not output or not split_spec:
            return output
            
        parts = split_spec.split(',')
        if len(parts) != 2:
            self.log(f"Warning: Invalid split specification '{split_spec}'. Format should be 'delimiter,index'")
            return output
            
        delimiter, index = parts
        try:
            index = int(index)
        except ValueError:
            self.log(f"Warning: Invalid index '{index}' in split specification.")
            return output
            
        # Convert delimiter keywords to actual regex patterns
        delimiter_map = {
            'space': r'\s+',
            'tab': r'\t+',
            'semi': ';',
            'comma': ',',
            'pipe': '|'
        }
        
        delimiter_pattern = delimiter_map.get(delimiter, delimiter)
        
        # Split the output
        split_output = re.split(delimiter_pattern, output)
        
        # Return the selected part if index is valid
        if 0 <= index < len(split_output):
            return split_output[index]
        else:
            self.log(f"Warning: Index {index} out of bounds for split output (0-{len(split_output)-1}).")
            return output

    def evaluate_condition(self, condition, exit_code, stdout, stderr):
        """Evaluate a complex condition expression."""
        # Replace variables and check resolution status
        original_condition = condition
        condition, all_resolved = ConditionEvaluator.replace_variables(condition, self.global_vars, self.task_results, self.debug_log)
        
        if original_condition != condition:
            self.debug_log(f"Condition after variable replacement: '{original_condition}' -> '{condition}'")

        # If not all variables could be resolved, condition fails
        if not all_resolved:
            self.debug_log(f"Condition '{original_condition}' contains unresolved variables, evaluating to FALSE")
            return False

        # First, handle parentheses by recursively evaluating what's inside
        while '(' in condition and ')' in condition:
            # Find the innermost parentheses
            start = condition.rfind('(')
            end = condition.find(')', start)
            if start == -1 or end == -1:
                self.log(f"Warning: Mismatched parentheses in condition: {condition}")
                return False
           
            inner_expr = condition[start+1:end]
            self.debug_log(f"Evaluating sub-condition: ({inner_expr})")
            inner_result = ConditionEvaluator.evaluate_condition(inner_expr, exit_code, stdout, stderr, self.global_vars, self.task_results, self.debug_log)     
            # Replace the parentheses expression with its result
            condition = condition[:start] + ("true" if inner_result else "false") + condition[end+1:]
            self.debug_log(f"Condition after substitution: {condition}")
        
        # Now we have a flat condition with only AND/OR operators
        # Clean up boolean string literals from variable replacement
        condition = condition.replace('True', 'true').replace('False', 'false')

        # Handle strings like "exit_0&true" or "exit_0&false"
        if '&true' in condition:
            condition = condition.replace('&true', '')
        if '&false' in condition:
            return False
        if '|true' in condition:
            return True
        if '|false' in condition:
            condition = condition.replace('|false', '')

        # If we now have just "true" or "false"
        if condition == "true":
            return True
        if condition == "false":
            return False
        
        # Split by OR first
        or_parts = condition.split('|')
        for or_part in or_parts:
            # All AND parts must be true for this OR part to be true
            and_parts = or_part.split('&')
            if all(self.evaluate_simple_condition(p.strip(), exit_code, stdout, stderr) for p in and_parts):
                return True
                
        # If we get here, no OR part was fully true
        return False

    def evaluate_simple_condition(self, condition, exit_code, stdout, stderr):
        """Evaluate a simple condition without AND/OR/parentheses."""

        # Check for boolean literals (handle both Python and string representations)
        if condition.lower() in ["true"]:
            self.debug_log(f"Simple condition '{condition}' evaluated to True")
            return True
        if condition.lower() in ["false"]:
            self.debug_log(f"Simple condition '{condition}' evaluated to False")
            return False

        # Check for unresolved variable references - these should not reach here anymore
        # but we keep it as a safety net
        if re.match(r'@\d+_(stdout|stderr|success)@', condition):
            self.debug_log(f"WARNING: Unresolved variable reference '{condition}' in simple condition - this should have been caught earlier")
            return False

        # Check for success condition - use the stored success value for current task - THREAD SAFE
        if condition == "success":
            task_id = self.current_task
            task_result = self.get_task_result(task_id)
            if task_result is not None and 'success' in task_result:
                success_value = task_result['success']
                self.debug_log(f"Success condition for task {task_id}: {success_value}")
                return success_value
            else:
                # If no success value stored yet, default to exit_code == 0
                success_value = (exit_code == 0)
                self.debug_log(f"Success condition (default) for task {task_id}: {success_value}")
                return success_value

        # Check for exit code condition
        if condition.startswith('exit_'):
            try:
                expected_exit = int(condition[5:])
                result = exit_code == expected_exit
                self.debug_log(f"Exit code condition '{condition}': expected {expected_exit}, actual {exit_code}, result {result}")
                return result
            except ValueError:
                self.log(f"Warning: Invalid exit code in condition: {condition}")
                return False

        # NEW: Enhanced operator support - but only for non-stdout/stderr conditions
        # Order matters: check longer operators first (!=, !~, <=, >=)
        if not condition.startswith(('stdout', 'stderr')):
            operators = ['!=', '!~', '<=', '>=', '=', '~', '<', '>']
            for op in operators:
                if op in condition:
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()
                        return self.evaluate_operator_comparison(left, op, right, exit_code, stdout, stderr)
        
        # Check for stdout/stderr conditions (legacy support maintained)
        if condition.startswith('stdout'):
            stdout_stripped = stdout.rstrip('\n')
            if condition == 'stdout~':
                result = stdout.strip() == ''
                self.debug_log(f"Stdout empty check: '{stdout.strip()}' is {'empty' if result else 'not empty'}")
                return result
            elif condition == 'stdout!~':
                result = stdout.strip() != ''
                self.debug_log(f"Stdout not empty check: '{stdout.strip()}' is {'not empty' if result else 'empty'}")
                return result
            elif '~' in condition:
                pattern = condition.split('~', 1)[1]
                if condition.startswith('stdout!~'):
                    result = pattern not in stdout
                    self.debug_log(f"Stdout pattern not match: '{pattern}' is {'absent' if result else 'present'} in '{stdout_stripped}'")
                    return result
                else:
                    result = pattern in stdout
                    self.debug_log(f"Stdout pattern match: '{pattern}' is {'present' if result else 'absent'} in '{stdout_stripped}'")
                    return result
            elif '_count' in condition:
                try:
                    count_parts = condition.split('_count')
                    operator = count_parts[1][0] if len(count_parts[1]) > 0 else '='
                    expected_count = int(count_parts[1][1:])
                    actual_count = len(stdout.strip().split('\n'))
                    
                    if operator == '=':
                        return actual_count == expected_count
                    elif operator == '<':
                        return actual_count < expected_count
                    elif operator == '>':
                        return actual_count > expected_count
                    else:
                        self.log(f"Warning: Invalid operator in count condition: {condition}")
                        return False
                except (ValueError, IndexError):
                    self.log(f"Warning: Invalid count specification in condition: {condition}")
                    return False

        # Check for stderr conditions 
        if condition.startswith('stderr'):
            stderr_stripped = stderr.rstrip('\n')
            if condition == 'stderr~':
                result = stderr.strip() == ''
                self.debug_log(f"Stderr empty check: '{stderr.strip()}' is {'empty' if result else 'not empty'}")
                return result
            elif condition == 'stderr!~':
                result = stderr.strip() != ''
                self.debug_log(f"Stderr not empty check: '{stderr.strip()}' is {'not empty' if result else 'empty'}")
                return result
            elif '~' in condition:
                pattern = condition.split('~', 1)[1]
                if condition.startswith('stderr!~'):
                    result = pattern not in stderr
                    self.debug_log(f"Stderr pattern not match: '{pattern}' is {'absent' if result else 'present'} in '{stderr_stripped}'")
                    return result
                else:
                    result = pattern in stderr
                    self.debug_log(f"Stderr pattern match: '{pattern}' is {'present' if result else 'absent'} in '{stderr_stripped}'")
                    return result
            elif '_count' in condition:
                try:
                    count_parts = condition.split('_count')
                    operator = count_parts[1][0] if len(count_parts[1]) > 0 else '='
                    expected_count = int(count_parts[1][1:])
                    actual_count = len(stderr.strip().split('\n'))
                    
                    if operator == '=':
                        return actual_count == expected_count
                    elif operator == '<':
                        return actual_count < expected_count
                    elif operator == '>':
                        return actual_count > expected_count
                    else:
                        self.log(f"Warning: Invalid operator in count condition: {condition}")
                        return False
                except (ValueError, IndexError):
                    self.log(f"Warning: Invalid count specification in condition: {condition}")
                    return False
        
        # If we get here, the condition wasn't recognized
        self.log(f"Warning: Unrecognized condition: '{condition}'")
        return False

    def evaluate_operator_comparison(self, left, operator, right, exit_code, stdout, stderr):
        """Evaluate a comparison between two values using the specified operator."""
        
        # Handle special cases for stdout/stderr as left operand
        if left == 'stdout':
            left_val = stdout.rstrip('\n')
        elif left == 'stderr':
            left_val = stderr.rstrip('\n')
        else:
            left_val = convert_value(left)
        
        right_val = convert_value(right)
        
        try:
            if operator == '=':
                result = left_val == right_val
                self.debug_log(f"Equality comparison '{left}' = '{right}': {left_val} == {right_val} = {result}")
                return result
            elif operator == '!=':
                result = left_val != right_val
                self.debug_log(f"Inequality comparison '{left}' != '{right}': {left_val} != {right_val} = {result}")
                return result
            elif operator == '~':
                # Contains check (string operation)
                left_str = str(left_val)
                right_str = str(right_val)
                result = right_str in left_str
                self.debug_log(f"Contains comparison '{left}' ~ '{right}': '{right_str}' in '{left_str}' = {result}")
                return result
            elif operator == '!~':
                # Not contains check (string operation)
                left_str = str(left_val)
                right_str = str(right_val)
                result = right_str not in left_str
                self.debug_log(f"Not-contains comparison '{left}' !~ '{right}': '{right_str}' not in '{left_str}' = {result}")
                return result
            elif operator in ['<', '<=', '>', '>=']:
                # Numerical comparisons
                left_num = convert_to_number(left_val)
                right_num = convert_to_number(right_val)
                
                if left_num is None or right_num is None:
                    self.debug_log(f"Non-numerical comparison '{left}' {operator} '{right}' - treating as False")
                    return False
                
                if operator == '<':
                    result = left_num < right_num
                elif operator == '<=':
                    result = left_num <= right_num
                elif operator == '>':
                    result = left_num > right_num
                elif operator == '>=':
                    result = left_num >= right_num
                
                self.debug_log(f"Numerical comparison '{left}' {operator} '{right}': {left_num} {operator} {right_num} = {result}")
                return result
                
        except Exception as e:
            self.debug_log(f"Error in operator comparison '{left}' {operator} '{right}': {str(e)}")
            return False
        
        return False


    # ===== 5. TASK EXECUTION HELPERS =====
    
    def determine_execution_type(self, task, task_display_id, loop_display=""):
        """Determine which execution type to use, respecting priority order."""
        if 'exec' in task:
            exec_type, _ = ConditionEvaluator.replace_variables(task['exec'], self.global_vars, self.task_results, self.debug_log)
            self.log(f"Task {task_display_id}{loop_display}: Using execution type from task: {exec_type}")
        elif self.exec_type:
            exec_type = self.exec_type
            self.debug_log(f"Task {task_display_id}{loop_display}: Using execution type from args: {exec_type}")
        elif 'TASK_EXECUTOR_TYPE' in os.environ:
            exec_type = os.environ['TASK_EXECUTOR_TYPE']
            self.debug_log(f"Task {task_display_id}{loop_display}: Using execution type from environment: {exec_type}")
        else:
            exec_type = self.default_exec_type
            self.debug_log(f"Task {task_display_id}{loop_display}: Using default execution type: {exec_type}")
        return exec_type

    def build_command_array(self, exec_type, hostname, command, arguments):
        """Build the command array based on execution type."""
        if exec_type == 'pbrun':
            return ["pbrun", "-n", "-h", hostname, command] + shlex.split(arguments)
        elif exec_type == 'p7s':
            return ["p7s", hostname, command] + shlex.split(arguments)
        elif exec_type == 'local':
            return [command] + shlex.split(arguments)
        elif exec_type == 'wwrs':
            return ["wwrs_clir", hostname, command] + shlex.split(arguments)
        else:
            # Default to pbrun if unknown exec_type
            self.log(f"Unknown execution type '{exec_type}', using default 'pbrun'")
            return ["pbrun", "-n", "-h", hostname, command] + shlex.split(arguments)

    def get_task_timeout(self, task):
        """Determine the timeout for a task, respecting priority order."""
        # Start with the default range
        min_timeout = 5
        max_timeout = 1000

        # Get timeout from task (highest priority)
        if 'timeout' in task:
            timeout_str, resolved = ConditionEvaluator.replace_variables(task['timeout'], self.global_vars, self.task_results, self.debug_log)
            if resolved:
                try:
                    timeout = int(timeout_str)
                    self.debug_log(f"Using timeout from task: {timeout}")
                except ValueError:
                    self.log(f"Warning: Invalid timeout value in task: '{timeout_str}'. Using default.")
                    timeout = self.timeout
            else:
                self.log(f"Warning: Unresolved variables in timeout. Using default.")
                timeout = self.timeout

        # Get timeout from command line argument (medium priority)
        elif self.timeout:
            timeout = self.timeout
            self.debug_log(f"Using timeout from command line: {timeout}")

        # Get timeout from environment (lower priority)
        elif 'TASK_EXECUTOR_TIMEOUT' in os.environ:
            try:
                timeout = int(os.environ['TASK_EXECUTOR_TIMEOUT'])
                self.debug_log(f"Using timeout from environment: {timeout}")
            except ValueError:
                self.log(f"Warning: Invalid timeout value in environment: '{os.environ['TASK_EXECUTOR_TIMEOUT']}'. Using default.")
                timeout = 30

        # Use default timeout (lowest priority)
        else:
            timeout = 30
            self.debug_log(f"Using default timeout: {timeout}")

        # Ensure timeout is within valid range
        if timeout < min_timeout:
            self.log(f"Warning: Timeout {timeout} too low, using minimum {min_timeout}")
            timeout = min_timeout
        elif timeout > max_timeout:
            self.log(f"Warning: Timeout {timeout} too high, using maximum {max_timeout}")
            timeout = max_timeout
        return timeout

    def categorize_task_result(self, result):
        """Categorize task result for retry logic."""
        if result['exit_code'] == 124:
            return 'TIMEOUT'     # Master timeout reached - don't retry
        elif result['success']:
            return 'SUCCESS'     # Success condition met - don't retry
        else:
            return 'FAILED'      # Real failure - eligible for retry

    def parse_retry_config(self, parallel_task):
        """Parse retry configuration from parallel task."""
        if parallel_task.get('retry_failed', '').lower() != 'true':
            return None
            
        try:
            # Resolve global variables first before int conversion
            retry_count_str, _ = ConditionEvaluator.replace_variables(parallel_task.get('retry_count', '1'), self.global_vars, self.task_results, self.debug_log)
            retry_delay_str, _ = ConditionEvaluator.replace_variables(parallel_task.get('retry_delay', '1'), self.global_vars, self.task_results, self.debug_log)
        
            retry_count = int(retry_count_str)
            retry_delay = int(retry_delay_str)
            
            # Validate retry parameters
            if retry_count < 0 or retry_count > 10:
                self.log(f"Warning: retry_count {retry_count} out of range (0-10), using 1")
                retry_count = 1
                
            if retry_delay < 0 or retry_delay > 300:
                self.log(f"Warning: retry_delay {retry_delay} out of range (0-300), using 1")
                retry_delay = 1
                
            return {
                'count': retry_count,
                'delay': retry_delay
            }
        except ValueError as e:
            self.log(f"Warning: Invalid retry configuration: {str(e)}. Retry disabled.")
            return None

    # Unified execution helpers
    def _get_task_display_id(self, task_id, context_type, retry_display=""):
        """Get consistent task display ID for different execution contexts."""
        if context_type == "parallel" and self._current_parallel_task is not None:
            return f"{self._current_parallel_task}-{task_id}{retry_display}"
        elif context_type == "conditional" and self._current_conditional_task is not None:
            return f"{self._current_conditional_task}-{task_id}{retry_display}"
        else:
            return f"{task_id}{retry_display}"

    def _log_task_result(self, task_display_id, exit_code, stdout, stderr):
        """Log task execution results consistently."""
        self.log(f"Task {task_display_id}: Exit code: {exit_code}")
        if stdout.strip():
            self.log(f"Task {task_display_id}: STDOUT: {stdout.rstrip()}")
        if stderr.strip():
            self.log(f"Task {task_display_id}: STDERR: {stderr.rstrip()}")

    def _handle_output_splitting(self, task, task_display_id, stdout, stderr):
        """Handle stdout/stderr splitting if specified in task."""
        if 'stdout_split' in task:
            stdout = ConditionEvaluator.split_output(stdout, task['stdout_split'])
            self.log(f"Task {task_display_id}: Split STDOUT: '{stdout}'")
            
        if 'stderr_split' in task:
            stderr = ConditionEvaluator.split_output(stderr, task['stderr_split'])
            self.log(f"Task {task_display_id}: Split STDERR: '{stderr}'")
        
        return stdout, stderr

    def _execute_task_core(self, task, master_timeout=None, context="normal", retry_display=""):
        """Unified task execution core for parallel, conditional, and normal execution."""
        task_id = int(task['task'])
        task_display_id = self._get_task_display_id(task_id, context, retry_display)
        
        try:
            # 1. Pre-execution condition check
            if 'condition' in task:
                condition_result = ConditionEvaluator.evaluate_condition(task['condition'], 0, "", "", self.global_vars, self.task_results, self.debug_log)
                if not condition_result:
                    self.log(f"Task {task_display_id}: Condition '{task['condition']}' evaluated to FALSE, skipping task")
                    return {
                        'task_id': task_id,
                        'exit_code': -1,
                        'stdout': '',
                        'stderr': 'Task skipped due to condition',
                        'success': False,
                        'skipped': True
                    }

            # 2. Handle return tasks
            if 'return' in task:
                return_code = int(task['return'])
                self.log(f"Task {task_display_id}: Return task with exit code {return_code}")
                return {
                    'task_id': task_id,
                    'exit_code': return_code,
                    'stdout': '',
                    'stderr': f'Return task: {return_code}',
                    'success': (return_code == 0),
                    'skipped': False
                }
            
            # 3. Variable replacement
            hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', ''), self.global_vars, self.task_results, self.debug_log)
            command, _ = ConditionEvaluator.replace_variables(task.get('command', ''), self.global_vars, self.task_results, self.debug_log)
            arguments, _ = ConditionEvaluator.replace_variables(task.get('arguments', ''), self.global_vars, self.task_results, self.debug_log)

            # 4. Execution type and command building
            exec_type = self.determine_execution_type(task, task_display_id)
            cmd_array = self.build_command_array(exec_type, hostname, command, arguments)
            full_command_display = ' '.join(cmd_array)

            # 5. Timeout handling
            if master_timeout is not None:
                task_timeout = master_timeout
                if 'timeout' in task:
                    individual_timeout_str, _ = ConditionEvaluator.replace_variables(task['timeout'], self.global_vars, self.task_results, self.debug_log)
                    try:
                        individual_timeout = int(individual_timeout_str)
                        if individual_timeout != master_timeout:
                            self.debug_log(f"Task {task_display_id}: OVERRIDING individual timeout {individual_timeout}s with MASTER timeout {master_timeout}s")
                    except ValueError:
                        pass
                else:
                    self.debug_log(f"Task {task_display_id}: Using MASTER timeout {master_timeout}s")
            else:
                task_timeout = self.get_task_timeout(task)
                self.debug_log(f"Task {task_display_id}: Using individual timeout {task_timeout}s")

            # 6. Command execution
            if self.dry_run:
                self.log(f"Task {task_display_id}: [DRY RUN] Would execute: {full_command_display}")
                exit_code = 0
                stdout = f"DRY RUN STDOUT - Task {task_id}"
                stderr = ""
            else:
                self.log(f"Task {task_display_id}: Executing [{exec_type}]: {full_command_display}")
                
                try:
                    with subprocess.Popen(
                        cmd_array,
                        shell=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    ) as process:
                        try:
                            stdout, stderr = process.communicate(timeout=task_timeout)
                            exit_code = process.returncode
                            
                        except subprocess.TimeoutExpired: 
                            self.log(f"Task {task_display_id}: TIMEOUT after {task_timeout}s - killing process")
                            process.kill()
                            stdout, stderr = process.communicate()
                            exit_code = 124  # Standard timeout exit code
                            stderr += f"\nProcess killed after timeout of {task_timeout}s"
                            
                except Exception as e:
                    self.log(f"Task {task_display_id}: Error executing command: {str(e)}")
                    exit_code = 1
                    stdout = ""
                    stderr = str(e)
            
            # 7. Result logging and processing (using Phase 1 helpers)
            self._log_task_result(task_display_id, exit_code, stdout, stderr)
            stdout, stderr = self._handle_output_splitting(task, task_display_id, stdout, stderr)
            
            # 8. Success evaluation
            if 'success' in task:
                success_result = ConditionEvaluator.evaluate_condition(task['success'], exit_code, stdout, stderr, self.global_vars, self.task_results, self.debug_log)
                self.log(f"Task {task_display_id}: Success condition '{task['success']}' evaluated to: {success_result}")
            else:
                success_result = (exit_code == 0) 
                self.debug_log(f"Task {task_display_id}: Success (default): {success_result}")
            
            # 9. Sleep handling
            if 'sleep' in task:
                try:
                    sleep_time_str, resolved = ConditionEvaluator.replace_variables(task['sleep'], self.global_vars, self.task_results, self.debug_log)
                    if resolved:
                        sleep_time = float(sleep_time_str)
                        self.log(f"Task {task_display_id}: Sleeping for {sleep_time} seconds")
                        if not self.dry_run:
                            time.sleep(sleep_time)
                except ValueError:
                    self.log(f"Task {task_display_id}: Invalid sleep time '{task['sleep']}'. Continuing.")
            
            # 10. Return result
            return {
                'task_id': task_id,
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'success': success_result,
                'skipped': False
            }
            
        except Exception as e:
            self.log(f"Task {task_display_id}: Unexpected error: {str(e)}")
            return {
                'task_id': task_id,
                'exit_code': 1,
                'stdout': '',
                'stderr': f'Unexpected error: {str(e)}',
                'success': False,
                'skipped': False
            }

    def _execute_single_task_with_retry_core(self, task, master_timeout, retry_config, context_type):
        """Unified retry logic for both parallel and conditional contexts."""
        task_id = int(task['task'])
    
        # Context-specific parent task ID and execution function
        if context_type == "parallel":
            parent_task_id = self._current_parallel_task
            execute_func = self.execute_single_task_for_parallel
        else:  # conditional
            parent_task_id = self._current_conditional_task
            execute_func = self.execute_single_task_for_conditional_with_retry_display
    
        max_retries = retry_config.get('count', 0) if retry_config else 0
        retry_delay = retry_config.get('delay', 1) if retry_config else 1
    
        for attempt in range(max_retries + 1):
            # Retry display notation (only when retry is enabled)
            retry_display = f".{attempt + 1}" if retry_config else ""
        
            # Execute the task with context-specific function
            result = execute_func(task, master_timeout, retry_display)
            category = self.categorize_task_result(result)
        
            # Log attempt information with unique task ID
            if attempt == 0:
                self.debug_log(f"Task {parent_task_id}-{task_id}{retry_display}: Initial attempt - Result: {category}")
            else:
                self.debug_log(f"Task {parent_task_id}-{task_id}{retry_display}: Retry attempt {attempt} - Result: {category}")
        
            # Check if we should retry
            if category in ['SUCCESS', 'TIMEOUT']:
                # SUCCESS: Task completed successfully
                # TIMEOUT: Retry won't help - probably same result
                if attempt > 0:
                    if category == 'SUCCESS':
                        # SUCCESS after retry goes to NORMAL logging (not just debug)
                        self.log(f"Task {parent_task_id}-{task_id}{retry_display}: SUCCESS after {attempt} retry attempt(s)")
                    else:
                        self.debug_log(f"Task {parent_task_id}-{task_id}{retry_display}: TIMEOUT - no retry attempted")
                return result
            
            elif category == 'FAILED' and attempt < max_retries:
                # Real failure - retry makes sense
                next_attempt_display = f".{attempt + 2}" if retry_config else ""
                self.log(f"Task {parent_task_id}-{task_id}{retry_display}: FAILED - will retry as Task {parent_task_id}-{task_id}{next_attempt_display} in {retry_delay}s")
                if not self.dry_run:
                    time.sleep(retry_delay)
                continue
            
            else:
                # Max retries reached or other condition
                if attempt > 0:
                    self.log(f"Task {parent_task_id}-{task_id}{retry_display}: FAILED after {attempt} retry attempt(s) - giving up")
                return result
            
        # This should never be reached, but just in case
        return result

    # ===== 6. PARALLEL TASK EXECUTION =====
    
    def execute_single_task_for_parallel(self, task, master_timeout=None, retry_display=""):
        """Execute a single task as part of parallel execution with enhanced retry display support."""
        return self._execute_task_core(task, master_timeout, "parallel", retry_display)

    def execute_single_task_with_retry(self, task, master_timeout, retry_config):
        """Execute a single task with retry logic and attempt numbering (.N notation)."""
        return self._execute_single_task_with_retry_core(task, master_timeout, retry_config, "parallel")

    def evaluate_parallel_next_condition(self, next_condition, results):
        """Evaluate next condition specifically for parallel tasks."""
        if not results:
            self.log(f"No results to evaluate for parallel next condition: '{next_condition}'")
            return False
            
        successful_tasks = [r for r in results if r['success']]
        failed_tasks = [r for r in results if not r['success']]
        total_tasks = len(results)
        success_count = len(successful_tasks)
        failed_count = len(failed_tasks)
        
        self.debug_log(f"Parallel condition evaluation: {success_count} successful, {failed_count} failed, total {total_tasks}")
        
        # Handle direct modifier conditions (min_success=N, max_failed=N, etc.)
        if '=' in next_condition:
            return self.evaluate_direct_modifier_condition(next_condition, success_count, failed_count, total_tasks)
        
        # Handle standard conditions
        if next_condition == 'all_success':
            result = success_count == total_tasks
            self.debug_log(f"all_success: {success_count} == {total_tasks} = {result}")
            return result
            
        elif next_condition == 'any_success':
            result = success_count > 0
            self.debug_log(f"any_success: {success_count} > 0 = {result}")
            return result
            
        elif next_condition == 'majority_success':
            majority_threshold = total_tasks / 2
            result = success_count > majority_threshold
            self.debug_log(f"majority_success: {success_count} > {majority_threshold} = {result}")
            return result
            
        else:
            self.log(f"Unknown parallel next condition: '{next_condition}'")
            return False

    def evaluate_direct_modifier_condition(self, condition, success_count, failed_count, total_tasks):
        """Evaluate direct modifier condition (min_success=N, max_failed=N, etc.)."""
        if '=' not in condition:
            self.log(f"Invalid modifier condition format: '{condition}'")
            return False
            
        key, value = condition.split('=', 1)
        
        try:
            threshold = int(value)
        except ValueError:
            self.log(f"Invalid modifier value: '{condition}'")
            return False
        
        if key == 'min_success':
            result = success_count >= threshold
            self.debug_log(f"min_success: {success_count} >= {threshold} = {result}")
            return result
            
        elif key == 'max_success':
            result = success_count <= threshold
            self.debug_log(f"max_success: {success_count} <= {threshold} = {result}")
            return result
            
        elif key == 'min_failed':
            result = failed_count >= threshold
            self.debug_log(f"min_failed: {failed_count} >= {threshold} = {result}")
            return result
            
        elif key == 'max_failed':
            result = failed_count <= threshold
            self.debug_log(f"max_failed: {failed_count} <= {threshold} = {result}")
            return result
            
        else:
            self.log(f"Unknown modifier: '{key}' in condition '{condition}'")
            return False

    def check_parallel_next_condition(self, parallel_task, results):
        """Check next condition for parallel tasks with simplified syntax."""
        task_id = int(parallel_task['task'])
        
        if 'next' not in parallel_task:
            # No explicit next condition - use overall success (all must succeed)
            successful_count = len([r for r in results if r['success']])
            total_count = len(results)
            should_continue = successful_count == total_count
            self.log(f"Task {task_id}: No 'next' condition, using all_success logic: {successful_count}/{total_count} = {should_continue}")
            return should_continue
            
        next_condition = parallel_task['next']
        self.log(f"Task {task_id}: Evaluating 'next' condition: {next_condition}")
        
        # Special cases
        if next_condition == 'never':
            self.log(f"Task {task_id}: 'next=never' found, stopping execution")
            return "NEVER"

        if next_condition == 'always':
            self.log(f"Task {task_id}: 'next=always' found, proceeding to next task")
            return True

        if next_condition == 'loop' and 'loop' in parallel_task:
            # Handle loop logic (reuse existing loop logic but with parallel results)
            return self.handle_parallel_loop(parallel_task, results)
        
        # Handle backwards compatibility for 'success' - treat as 'all_success'
        if next_condition == 'success':
            self.log(f"Task {task_id}: Legacy 'success' condition treated as 'all_success'")
            result = self.evaluate_parallel_next_condition('all_success', results)
            self.log(f"Task {task_id}: Condition 'success' (→ all_success) evaluated to: {result}")
            return result
        
        # Handle parallel-specific conditions (simplified syntax)
        if next_condition in ['all_success', 'any_success', 'majority_success'] or '=' in next_condition:
            result = self.evaluate_parallel_next_condition(next_condition, results)
            self.log(f"Task {task_id}: Condition '{next_condition}' evaluated to: {result}")
            return result
        
        # Handle complex condition expressions (delegate to existing logic)
        # Use aggregated results for complex expressions
        successful_count = len([r for r in results if r['success']])
        failed_count = len([r for r in results if not r['success']])
        
        aggregated_exit_code = 0 if successful_count == len(results) else 1
        aggregated_stdout = f"Parallel execution summary: {successful_count} successful, {failed_count} failed"
        aggregated_stderr = f"Failed tasks: {[r['task_id'] for r in results if not r['success']]}" if failed_count > 0 else ""
        
        result = ConditionEvaluator.evaluate_condition(next_condition, aggregated_exit_code, aggregated_stdout, aggregated_stderr, self.global_vars, self.task_results, self.debug_log)
        self.log(f"Task {task_id}: Complex condition '{next_condition}' evaluated to: {result}")
        return result

    def handle_parallel_loop(self, parallel_task, results):
        """Handle loop logic for parallel tasks."""
        task_id = int(parallel_task['task'])
        
        # Check if this is the first time we're seeing this task
        if task_id not in self.loop_counter:
            self.loop_counter[task_id] = int(parallel_task['loop'])
            self.loop_iterations[task_id] = 1
            self.log(f"Task {task_id}: Loop initialized with count {self.loop_counter[task_id]}")
        else:
            self.loop_iterations[task_id] += 1

        # Check loop_break condition first (if exists)
        if 'loop_break' in parallel_task:
            # For parallel tasks, evaluate loop_break against aggregated results
            successful_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            aggregated_exit_code = 0 if successful_count == len(results) else 1
            aggregated_stdout = f"Parallel execution summary: {successful_count} successful, {failed_count} failed"
            aggregated_stderr = ""
            
            loop_break_result = ConditionEvaluator.evaluate_condition(parallel_task['loop_break'], aggregated_exit_code, aggregated_stdout, aggregated_stderr, self.global_vars, self.task_results, self.debug_log)
            if loop_break_result:
                self.log(f"Task {task_id}: Breaking loop - condition '{parallel_task['loop_break']}' satisfied")
                del self.loop_counter[task_id]
                del self.loop_iterations[task_id]
                return True

        # Decrement the counter
        self.loop_counter[task_id] -= 1
        
        if self.loop_counter[task_id] >= 0:
            self.log(f"Task {task_id}: Looping (iteration {self.loop_iterations[task_id]}, {self.loop_counter[task_id]} remaining)")
            return "LOOP"
        else:
            self.log(f"Task {task_id}: Loop complete - max iterations reached")
            del self.loop_counter[task_id]
            del self.loop_iterations[task_id]
            return True

    def execute_parallel_tasks(self, parallel_task):
        """Execute multiple tasks in parallel with ENHANCED RETRY LOGIC and IMPROVED LOGGING."""
        task_id = int(parallel_task['task'])
        
        # Set current parallel task for child task logging
        self._current_parallel_task = task_id
        
        # Parse task references
        tasks_str = parallel_task.get('tasks', '')
        if not tasks_str:
            self.log(f"Task {task_id}: No tasks specified")
            return task_id + 1
        
        # Get referenced task IDs and validate
        try:
            referenced_task_ids = []
            for task_ref in tasks_str.split(','):
                task_ref = task_ref.strip()
                if task_ref:
                    referenced_task_ids.append(int(task_ref))
        except ValueError as e:
            self.log(f"Task {task_id}: Invalid task reference: {str(e)}")
            return None
        
        # Validate that all referenced tasks exist
        missing_tasks = []
        tasks_to_execute = []
        for ref_id in referenced_task_ids:
            if ref_id in self.tasks:
                tasks_to_execute.append(self.tasks[ref_id])
            else:
                missing_tasks.append(ref_id)
        
        if missing_tasks:
            self.log(f"Task {task_id}: Missing referenced tasks: {missing_tasks}")
            return None
        
        # Get parallel execution parameters
        max_parallel = int(parallel_task.get('max_parallel', len(tasks_to_execute)))
        
        # NEW: Parse retry configuration
        retry_config = self.parse_retry_config(parallel_task)
        
        # MASTER TIMEOUT ENFORCEMENT: One timeout rules them all
        master_timeout = self.get_task_timeout(parallel_task)
        
        # IMPROVED: Cleaner startup message with retry info
        retry_info = ""
        if retry_config:
            retry_info = f", retry_failed=true (count={retry_config['count']}, delay={retry_config['delay']}s)"
        
        self.log(f"Task {task_id}: Starting parallel execution of {len(tasks_to_execute)} tasks (max_parallel={max_parallel}, timeout={master_timeout}s{retry_info})")
        
        # Check for individual timeouts and warn about overrides (DEBUG ONLY)
        individual_timeout_count = 0
        for task in tasks_to_execute:
            if 'timeout' in task:
                individual_timeout_count += 1
        
        if individual_timeout_count > 0:
            self.debug_log(f"Task {task_id}: WARNING: {individual_timeout_count} sub-tasks have individual timeouts - MASTER timeout {master_timeout}s will override them")
        
        # Execute tasks in parallel with master timeout enforcement and retry logic
        results = []
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=max_parallel, thread_name_prefix=f"Task{task_id}") as executor:
                # Submit tasks with or without retry based on config
                future_to_task = {}
                for task in tasks_to_execute:
                    # Check for shutdown before submitting each parallel task
                    if self._shutdown_requested:
                        self.log("Shutdown requested during parallel task submission")
                        executor.shutdown(wait=False)
                        self._check_shutdown()

                    if retry_config:
                        # Mit retry config → .1, .2, etc.
                        future = executor.submit(self.execute_single_task_with_retry, task, master_timeout, retry_config)
                    else:
                        # Ohne retry config → keine Nummer
                        future = executor.submit(self.execute_single_task_for_parallel, task, master_timeout, "")
                    future_to_task[future] = task
                
                # Collect results with MASTER TIMEOUT enforcement
                try:
                    for future in as_completed(future_to_task, timeout=master_timeout):
                        task = future_to_task[future]
                        # Check for shutdown during result collection
                        if self._shutdown_requested:
                            # Cancel remaining tasks and exit gracefully
                            for f in future_to_task:
                                if not f.done():
                                    f.cancel()
                            self.log("Parallel execution interrupted by shutdown request")
                            self._check_shutdown()

                        try:
                            result = future.result()
                            results.append(result)
                            
                            # IMPROVED: Simple completion message
                            success_text = "Success: True" if result['success'] else "Success: False"
                            if result['exit_code'] == 124:
                                success_text += " (timeout)"
                            elif result.get('skipped', False):
                                success_text += " (skipped)"
                            
                            self.log(f"Task {task_id}: Completed task {result['task_id']} - {success_text}")
                                
                        except Exception as e:
                            task_id_inner = int(task['task'])
                            self.log(f"Task {task_id}: [ERROR] Task {task_id_inner} exception: {str(e)}")
                            results.append({
                                'task_id': task_id_inner,
                                'exit_code': 1,
                                'stdout': '',
                                'stderr': f'Exception: {str(e)}',
                                'success': False,
                                'skipped': False
                            })
                            
                except Exception as timeout_exception:
                    # MASTER TIMEOUT REACHED - Graceful cancellation
                    elapsed = time.time() - start_time
                    self.log(f"Task {task_id}: MASTER TIMEOUT ({master_timeout}s) reached after {elapsed:.1f}s")
                    
                    # Cancel remaining futures and collect partial results
                    cancelled_count = 0
                    for future, task in future_to_task.items():
                        if not future.done():
                            future.cancel()
                            cancelled_count += 1
                            
                            # Create timeout result for cancelled tasks
                            task_id_inner = int(task['task'])
                            results.append({
                                'task_id': task_id_inner,
                                'exit_code': 124,  # Timeout exit code
                                'stdout': '',
                                'stderr': f'Task cancelled due to master timeout ({master_timeout}s)',
                                'success': False,
                                'skipped': False
                            })
                            
                    self.log(f"Task {task_id}: Cancelled {cancelled_count} remaining tasks due to master timeout")
                        
        except Exception as e:
            self.log(f"Task {task_id}: Parallel execution failed: {str(e)}")
            return None
        
        elapsed_time = time.time() - start_time
        self.log(f"Task {task_id}: Parallel execution completed in {elapsed_time:.2f} seconds")
        
        # Store individual task results for future reference - THREAD SAFE
        for result in results:
            self.store_task_result(result['task_id'], {
                'exit_code': result['exit_code'],
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'success': result['success']
            })
        
        # Calculate execution statistics with FIXED categorization
        successful_tasks = [r for r in results if r['success']]
        timeout_tasks = [r for r in results if r['exit_code'] == 124]
        failed_tasks = [r for r in results if not r['success'] and r['exit_code'] != 124]  # FIXED: Exclude timeouts from failures
        skipped_tasks = [r for r in results if r.get('skipped', False)]
        
        successful_count = len(successful_tasks)
        failed_count = len(failed_tasks)
        timeout_count = len(timeout_tasks)
        skipped_count = len(skipped_tasks)
        
        # Verify statistics add up correctly
        total_accounted = successful_count + failed_count + timeout_count + skipped_count
        if total_accounted != len(results):
            self.debug_log(f"Task {task_id}: WARNING: Statistics mismatch - {total_accounted} accounted vs {len(results)} total")
        
        # IMPROVED: Overall success determination and logging
        overall_success = successful_count == len(results)
        success_text = "Success: True" if overall_success else "Success: False"
        self.log(f"Task {task_id}: Overall result - {success_text} ({successful_count}/{len(results)} tasks succeeded)")
        
        # NEW: Enhanced retry statistics logging
        if retry_config:
            retry_eligible_tasks = [r for r in results if not r['success'] and r['exit_code'] != 124]
            successful_after_potential_retry = [r for r in results if r['success']]
            
            if len(retry_eligible_tasks) > 0 or len(successful_after_potential_retry) > 0:
                self.log(f"Task {task_id}: RETRY SUMMARY - Retry enabled with {retry_config['count']} max attempts, {retry_config['delay']}s delay")
                
                if len(successful_after_potential_retry) > 0:
                    self.debug_log(f"Task {task_id}: RETRY SUCCESS - {len(successful_after_potential_retry)} task(s) completed successfully (some may have used retries)")
                
                if len(retry_eligible_tasks) > 0:
                    failed_task_ids = [r['task_id'] for r in retry_eligible_tasks]
                    self.debug_log(f"Task {task_id}: RETRY EXHAUSTED - Tasks {failed_task_ids} failed after all retry attempts")
        
        # Move detailed statistics to debug mode only
        if not overall_success:
            if timeout_count > 0:
                timeout_task_ids = [r['task_id'] for r in timeout_tasks]
                self.debug_log(f"Task {task_id}: TIMEOUT DETAILS - Tasks {timeout_task_ids} exceeded master timeout of {master_timeout}s")
            
            if failed_count > 0:
                failed_task_ids = [r['task_id'] for r in failed_tasks]
                self.debug_log(f"Task {task_id}: FAILURE DETAILS - Tasks {failed_task_ids} failed (non-timeout)")
        
        # Create aggregated output with enhanced information
        aggregated_stdout = f"Parallel execution: {successful_count}/{len(results)} successful"
        if timeout_count > 0:
            aggregated_stdout += f", {timeout_count} timeout"
        if failed_count > 0:
            aggregated_stdout += f", {failed_count} failed"
        
        aggregated_stderr = ""
        
        # Separate error reporting
        if failed_count > 0:
            failed_task_ids = [r['task_id'] for r in failed_tasks]
            aggregated_stderr += f"Failed tasks: {failed_task_ids}. "
        
        if timeout_count > 0:
            timeout_task_ids = [r['task_id'] for r in timeout_tasks]
            aggregated_stderr += f"Timeout tasks: {timeout_task_ids}"
        
        aggregated_exit_code = 0 if overall_success else 1
        
        # Store the parallel task result - THREAD SAFE
        self.store_task_result(task_id, {
            'exit_code': aggregated_exit_code,
            'stdout': aggregated_stdout,
            'stderr': aggregated_stderr.strip(),
            'success': overall_success
        })
        
        # Update tracking for summary
        self.final_task_id = task_id
        self.final_hostname = "parallel"
        self.final_command = f"parallel execution of tasks {referenced_task_ids}"
        self.final_exit_code = aggregated_exit_code
        
        # Use enhanced parallel next condition evaluation
        should_continue = self.check_parallel_next_condition(parallel_task, results)
        
        # Determine final success based on should_continue result
        if should_continue == "NEVER":
            self.final_success = True
            return None

        if should_continue == "LOOP":
            return "LOOP" 
        
        # Handle on_success/on_failure jumps
        has_on_failure = 'on_failure' in parallel_task
        self.final_success = should_continue is True or (should_continue is False and has_on_failure)
        
        if should_continue and 'on_success' in parallel_task:
            try:
                on_success_task = int(parallel_task['on_success'])
                self.log(f"Task {task_id}: Parallel execution succeeded, jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                self.log(f"Task {task_id}: Invalid 'on_success' task. Continuing to next task.")
                return task_id + 1
        
        if not should_continue and 'on_failure' in parallel_task:
            try:
                on_failure_task = int(parallel_task['on_failure'])
                self.log(f"Task {task_id}: Parallel execution failed, jumping to Task {on_failure_task}")
                return on_failure_task
            except ValueError:
                self.log(f"Task {task_id}: Invalid 'on_failure' task. Stopping.")
                return None

        return task_id + 1 if should_continue else None

    # ===== 7. CONDITIONAL TASK EXECUTION =====
    
    def execute_single_task_for_conditional(self, task, master_timeout=None):
        """Execute a single task as part of conditional execution (sequential)."""
        return self._execute_task_core(task, master_timeout, "conditional")

    def execute_single_task_for_conditional_with_retry_display(self, task, master_timeout=None, retry_display=""):
        """Execute a single task as part of conditional execution with retry display support."""
        return self._execute_task_core(task, master_timeout, "conditional", retry_display)

    def execute_single_task_with_retry_conditional(self, task, master_timeout, retry_config):
        """Execute a single task with retry logic for conditional tasks."""
        return self._execute_single_task_with_retry_core(task, master_timeout, retry_config, "conditional")

    def check_conditional_next_condition(self, conditional_task, results):
        """Check next condition for conditional tasks - uses same logic as parallel tasks."""
        task_id = int(conditional_task['task'])
        
        if 'next' not in conditional_task:
            # No explicit next condition - use overall success (all must succeed)
            successful_count = len([r for r in results if r['success']])
            total_count = len(results)
            should_continue = successful_count == total_count
            self.log(f"Task {task_id}: No 'next' condition, using all_success logic: {successful_count}/{total_count} = {should_continue}")
            return should_continue
            
        next_condition = conditional_task['next']
        self.log(f"Task {task_id}: Evaluating 'next' condition: {next_condition}")
        
        # Special cases
        if next_condition == 'never':
            self.log(f"Task {task_id}: 'next=never' found, stopping execution")
            return "NEVER"

        if next_condition == 'always':
            self.log(f"Task {task_id}: 'next=always' found, proceeding to next task")
            return True

        # Handle backwards compatibility for 'success' - treat as 'all_success'
        if next_condition == 'success':
            self.log(f"Task {task_id}: Legacy 'success' condition treated as 'all_success'")
            result = self.evaluate_parallel_next_condition('all_success', results)
            self.log(f"Task {task_id}: Condition 'success' (→ all_success) evaluated to: {result}")
            return result
        
        # Handle conditional-specific conditions (reuse parallel logic)
        if next_condition in ['all_success', 'any_success', 'majority_success'] or '=' in next_condition:
            result = self.evaluate_parallel_next_condition(next_condition, results)
            self.log(f"Task {task_id}: Condition '{next_condition}' evaluated to: {result}")
            return result
        
        # Handle complex condition expressions
        successful_count = len([r for r in results if r['success']])
        failed_count = len([r for r in results if not r['success']])
        
        aggregated_exit_code = 0 if successful_count == len(results) else 1
        aggregated_stdout = f"Conditional execution: {successful_count} successful, {failed_count} failed"
        aggregated_stderr = f"Failed tasks: {[r['task_id'] for r in results if not r['success']]}" if failed_count > 0 else ""
        
        result = ConditionEvaluator.evaluate_condition(next_condition, aggregated_exit_code, aggregated_stdout, aggregated_stderr, self.global_vars, self.task_results, self.debug_log)
        self.log(f"Task {task_id}: Complex condition '{next_condition}' evaluated to: {result}")
        return result

    def execute_conditional_tasks(self, conditional_task):
        """Execute conditional tasks based on condition evaluation - sequential execution."""
        task_id = int(conditional_task['task'])
        
        # Set current conditional task for child task logging
        self._current_conditional_task = task_id
        
        # Evaluate the condition
        condition = conditional_task.get('condition', '')
        if not condition:
            self.log(f"Task {task_id}: No condition specified, skipping conditional task")
            return task_id + 1
        
        # Evaluate condition using existing logic
        condition_result = ConditionEvaluator.evaluate_condition(condition, 0, "", "", self.global_vars, self.task_results, self.debug_log)
        branch = "TRUE" if condition_result else "FALSE"
        
        self.log(f"Task {task_id}: Conditional condition '{condition}' evaluated to {branch}")
        
        # Determine which tasks to execute
        if condition_result and 'if_true_tasks' in conditional_task:
            tasks_str = conditional_task['if_true_tasks']
        elif not condition_result and 'if_false_tasks' in conditional_task:
            tasks_str = conditional_task['if_false_tasks']
        else:
            # No matching branch - skip to next task
            self.log(f"Task {task_id}: No tasks defined for {branch} branch, skipping to next task")
            return task_id + 1
        
        # Parse task references
        if not tasks_str.strip():
            self.log(f"Task {task_id}: Empty task list for {branch} branch, skipping to next task")
            return task_id + 1
        
        try:
            referenced_task_ids = []
            for task_ref in tasks_str.split(','):
                task_ref = task_ref.strip()
                if task_ref:
                    referenced_task_ids.append(int(task_ref))
        except ValueError as e:
            self.log(f"Task {task_id}: Invalid task reference in {branch} branch: {str(e)}")
            return None
        
        # Validate that all referenced tasks exist
        missing_tasks = []
        tasks_to_execute = []
        for ref_id in referenced_task_ids:
            if ref_id in self.tasks:
                tasks_to_execute.append(self.tasks[ref_id])
            else:
                missing_tasks.append(ref_id)
        
        if missing_tasks:
            self.log(f"Task {task_id}: Missing referenced tasks in {branch} branch: {missing_tasks}")
            return None
        
        # Get conditional execution parameters (similar to parallel)
        retry_config = self.parse_retry_config(conditional_task)
        master_timeout = self.get_task_timeout(conditional_task)
        
        # Log execution start
        retry_info = ""
        if retry_config:
            retry_info = f", retry_failed=true (count={retry_config['count']}, delay={retry_config['delay']}s)"
        
        self.log(f"Task {task_id}: Executing {branch} branch with {len(tasks_to_execute)} tasks (sequential, timeout={master_timeout}s{retry_info})")
        
        # Execute tasks sequentially in chosen branch
        results = []
        start_time = time.time()
        
        for task in tasks_to_execute:
            # Check for shutdown before each conditional task
            self._check_shutdown()

            # Execute task with retry logic if enabled
            if retry_config:
                result = self.execute_single_task_with_retry_conditional(task, master_timeout, retry_config)
            else:
                result = self.execute_single_task_for_conditional(task, master_timeout)
            
            results.append(result)
            
            # Store individual task results for future reference - THREAD SAFE
            self.store_task_result(result['task_id'], {
                'exit_code': result['exit_code'],
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'success': result['success']
            })
            
            # Log completion
            success_text = "Success: True" if result['success'] else "Success: False"
            if result['exit_code'] == 124:
                success_text += " (timeout)"
            elif result.get('skipped', False):
                success_text += " (skipped)"
            
            self.log(f"Task {task_id}: Completed task {result['task_id']} - {success_text}")
            
            # For sequential execution, we could stop on first failure if needed
            # But for consistency with parallel tasks, we continue executing all tasks
        
        elapsed_time = time.time() - start_time
        self.log(f"Task {task_id}: Conditional execution completed in {elapsed_time:.2f} seconds")
        
        # Calculate execution statistics (same as parallel)
        successful_tasks = [r for r in results if r['success']]
        timeout_tasks = [r for r in results if r['exit_code'] == 124]
        failed_tasks = [r for r in results if not r['success'] and r['exit_code'] != 124]
        skipped_tasks = [r for r in results if r.get('skipped', False)]
        
        successful_count = len(successful_tasks)
        failed_count = len(failed_tasks)
        timeout_count = len(timeout_tasks)
        skipped_count = len(skipped_tasks)
        
        # Overall success determination
        overall_success = successful_count == len(results)
        success_text = "Success: True" if overall_success else "Success: False"
        self.log(f"Task {task_id}: Overall result - {success_text} ({successful_count}/{len(results)} tasks succeeded)")
        
        # Create aggregated output
        aggregated_stdout = f"Conditional {branch} branch: {successful_count}/{len(results)} successful"
        if timeout_count > 0:
            aggregated_stdout += f", {timeout_count} timeout"
        if failed_count > 0:
            aggregated_stdout += f", {failed_count} failed"
        
        aggregated_stderr = ""
        if failed_count > 0:
            failed_task_ids = [r['task_id'] for r in failed_tasks]
            aggregated_stderr += f"Failed tasks: {failed_task_ids}. "
        if timeout_count > 0:
            timeout_task_ids = [r['task_id'] for r in timeout_tasks]
            aggregated_stderr += f"Timeout tasks: {timeout_task_ids}"
        
        aggregated_exit_code = 0 if overall_success else 1
        
        # Store the conditional task result - THREAD SAFE
        self.store_task_result(task_id, {
            'exit_code': aggregated_exit_code,
            'stdout': aggregated_stdout,
            'stderr': aggregated_stderr.strip(),
            'success': overall_success
        })
        
        # Update tracking for summary
        self.final_task_id = task_id
        self.final_hostname = "conditional"
        self.final_command = f"conditional {branch} branch execution of tasks {referenced_task_ids}"
        self.final_exit_code = aggregated_exit_code
        
        # Use conditional next condition evaluation (reuses parallel logic)
        should_continue = self.check_conditional_next_condition(conditional_task, results)
        
        # Determine final success based on should_continue result
        if should_continue == "NEVER":
            self.final_success = True
            return None

        # Handle on_success/on_failure jumps (same as parallel)
        has_on_failure = 'on_failure' in conditional_task
        self.final_success = should_continue is True or (should_continue is False and has_on_failure)
        
        if should_continue and 'on_success' in conditional_task:
            try:
                on_success_task = int(conditional_task['on_success'])
                self.log(f"Task {task_id}: Conditional execution succeeded, jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                self.log(f"Task {task_id}: Invalid 'on_success' task. Continuing to next task.")
                return task_id + 1
        
        if not should_continue and 'on_failure' in conditional_task:
            try:
                on_failure_task = int(conditional_task['on_failure'])
                self.log(f"Task {task_id}: Conditional execution failed, jumping to Task {on_failure_task}")
                return on_failure_task
            except ValueError:
                self.log(f"Task {task_id}: Invalid 'on_failure' task. Stopping.")
                return None

        return task_id + 1 if should_continue else None

    # ===== 8. NORMAL TASK EXECUTION =====
    
    def check_next_condition(self, task, exit_code, stdout, stderr):
        """
        Check if the 'next' condition is satisfied.
        Return True if we should proceed to the next task, False otherwise.
        Also return an special value for 'never' to distinguish it from normal failure
        """

        task_id = int(task['task'])

        # Get loop iteration display if looping
        loop_display = ""
        if task_id in self.loop_iterations:
            loop_display = f".{self.loop_iterations[task_id]}"

        if 'next' not in task:
            self.log(f"Task {task_id}{loop_display}: No 'next' condition specified, proceeding to next task")
            return True  # Default to True if not specified
            
        next_condition = task['next']
        self.log(f"Task {task_id}{loop_display}: 'next' evaluating condition: {next_condition}")
        
        # Special cases
        if next_condition == 'never':
            self.log(f"Task {task_id}{loop_display}: 'next=never' found, stopping execution")
            return "NEVER" # Special Case 

        if next_condition == 'always':
            self.log(f"Task {task_id}{loop_display}: 'next=always' found, proceeding to next task")
            return True

        # Handle the loop case with new simplified syntax
        if next_condition == 'loop' and 'loop' in task:
            # Check if this is the first time we're seeing this task
            if task_id not in self.loop_counter:
                self.loop_counter[task_id] = int(task['loop'])
                self.loop_iterations[task_id] = 1 # Start at iteration 1
                self.log(f"Task {task_id}{loop_display}: Loop initialized with count {self.loop_counter[task_id]}")
            else:
                self.loop_iterations[task_id] += 1 # increment the iteration counter by 1

            # Check loop_break condition first (if exists)
            if 'loop_break' in task:
                loop_break_result = ConditionEvaluator.evaluate_condition(task['loop_break'], exit_code, stdout, stderr, self.global_vars, self.task_results, self.debug_log)
                if loop_break_result:
                    # Break condition met
                    self.log(f"Task {task_id}: Breaking loop - loop_break condition '{task['loop_break']}' satisfied")
                    del self.loop_counter[task_id]
                    del self.loop_iterations[task_id]
                    self.log(f"Task {task_id}: Loop complete, proceeding to next task")
                    return True  # Proceed to next task

            # Decrement the counter
            self.loop_counter[task_id] -= 1
            
            # If counter is still >= 0, continue looping
            if self.loop_counter[task_id] >= 0:
                self.log(f"Task {task_id}: Looping (iteration {self.loop_iterations[task_id]}, {self.loop_counter[task_id]} remaining)")
                return "LOOP"  # Trigger the loop
            else:
                # Max iterations reached
                self.log(f"Task {task_id}: Loop complete - max iterations reached")
                del self.loop_counter[task_id]
                del self.loop_iterations[task_id]
                return True  # Proceed to next task
        
        # Parse complex conditions
        result = ConditionEvaluator.evaluate_condition(next_condition, exit_code, stdout, stderr, self.global_vars, self.task_results, self.debug_log)
        if result:
            self.log(f"Task {task_id}{loop_display}: 'next' condition evaluated to TRUE, proceeding to next task")
        else:
            self.log(f"Task {task_id}{loop_display}: 'next' condition evaluated to FALSE, stopping")

        return result

    def execute_task(self, task):
        """Execute a single task and return whether to continue to the next task."""
        task_id = int(task['task'])
        self.current_task = task_id # track current task

        # NEW: Check if this is a conditional task
        if task.get('type') == 'conditional':
            return self.execute_conditional_tasks(task)

        # NEW: Check if this is a parallel task
        if task.get('type') == 'parallel':
            return self.execute_parallel_tasks(task)

        # Get loop iteration display if looping
        loop_display = ""
        if task_id in self.loop_iterations:
            loop_display = f".{self.loop_iterations[task_id]}"

        # Check for shutdown before task execution
        self._check_shutdown()

        # Check pre-execution condition
        if 'condition' in task:
            condition_result = ConditionEvaluator.evaluate_condition(task['condition'], 0, "", "", self.global_vars, self.task_results, self.debug_log)
            if not condition_result:
                self.log(f"Task {task_id}{loop_display}: Condition '{task['condition']}' evaluated to FALSE, skipping task")
                # CRITICAL: Store results for skipped task - THREAD SAFE
                self.store_task_result(task_id, {
                    'exit_code': -1,     # Special: Task was skipped
                    'stdout': '',
                    'stderr': 'Task skipped due to condition',
                    'success': False
                })
                return task_id + 1  # Continue to next task
            else:
                self.log(f"Task {task_id}{loop_display}: Condition '{task['condition']}' evaluated to TRUE, executing task")

        # Update tracking for summary
        self.final_task_id = task_id
        self.final_hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', 'N/A'), self.global_vars, self.task_results, self.debug_log)
        self.final_command, _ = ConditionEvaluator.replace_variables(task.get('command', 'N/A'), self.global_vars, self.task_results, self.debug_log)
        
        # Check if this is a return task
        if 'return' in task:
            if self.final_command == 'N/A': self.final_command = 'return'
            try:
                return_code = int(task['return'])
                self.log(f"Task {task_id}{loop_display}: Returning with exit code {return_code}")
                self.final_exit_code = return_code
                self.final_success = (return_code == 0)  # Consider success if return code is 0
                
                # Add completion message before immediate exit
                if return_code == 0:
                    self.log("SUCCESS: Task execution completed successfully with return code 0")
                else:
                    self.log(f"FAILURE: Task execution failed with return code {return_code}")
                
                self.cleanup() # clean up resources before exit
                ExitHandler.exit_with_code(return_code, f"Task execution completed with return code {return_code}", self.debug)
            except ValueError:
                self.log(f"Task {task_id}{loop_display}: Invalid return code '{task['return']}'. Exiting with code 1.")
                self.final_exit_code = 1  # Use 1 for invalid return codes (this is correct)
                self.final_success = False
                self.log("FAILURE: Task execution failed with invalid return code")
                self.cleanup() # clean up resources before exit
                ExitHandler.exit_with_code(ExitCodes.INVALID_ARGUMENT, "Invalid return code specified", self.debug)
        
        # Replace variables in command and arguments
        hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', ''), self.global_vars, self.task_results, self.debug_log)
        command, _ = ConditionEvaluator.replace_variables(task.get('command', ''), self.global_vars, self.task_results, self.debug_log)
        arguments, _ = ConditionEvaluator.replace_variables(task.get('arguments', ''), self.global_vars, self.task_results, self.debug_log)

        # Determine execution type (from task, args, env, or default)
        exec_type = self.determine_execution_type(task, task_id, loop_display)
        # special case for local host
        if self.final_hostname == '': self.final_hostname = exec_type

        # Construct the command array based on execution type
        cmd_array = self.build_command_array(exec_type, hostname, command, arguments)
        self.debug_log(f"Command array: {cmd_array}")

        # Log the full command for the user
        full_command_display = ' '.join(cmd_array)
        self.final_command = full_command_display # better to have full command in the summary log

        # Get timeout for this task
        task_timeout = self.get_task_timeout(task)
        #self.log(f"Task {task_id}{loop_display}: Using timeout of {task_timeout} [s]")

        # Execute the command (or simulate in dry run mode)
        if self.dry_run:
            self.log(f"Task {task_id}{loop_display}: [DRY RUN] Would execute: {full_command_display}")
            exit_code = 0
            stdout = "DRY RUN STDOUT"
            stderr = ""
        else:
            self.log(f"Task {task_id}{loop_display}: Executing [{exec_type}]: {full_command_display}")
            try:
                # Execute using contect manager for automatic cleanup
                with subprocess.Popen(
                    cmd_array,
                    shell=False, # More secure
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                ) as process:
                    try:
                        stdout, stderr = process.communicate(timeout=task_timeout)
                        exit_code = process.returncode
                    except subprocess.TimeoutExpired: 
                        # Process timed out - kill it
                        self.log(f"Task {task_id}{loop_display}: Timeout after {task_timeout} seconds. Killing process.")
                        process.kill()
                        stdout, stderr = process.communicate()
                        exit_code = 124  # Common exit code for timeout
                        stderr += f"\nProcess killed after timeout of {task_timeout} seconds"
            except Exception as e:
                self.log(f"Task {task_id}{loop_display}: Error executing command: {str(e)}")
                exit_code = 1
                stdout = ""
                stderr = str(e)
        
        # Log the results
        stdout_stripped = stdout.rstrip('\n')
        stderr_stripped = stderr.rstrip('\n')
        self.log(f"Task {task_id}{loop_display}: Exit code: {exit_code}")
        self.log(f"Task {task_id}{loop_display}: STDOUT: {stdout_stripped}")
        self.log(f"Task {task_id}{loop_display}: STDERR: {stderr_stripped}")
        
        # Process output splitting if specified
        if 'stdout_split' in task:
            original_stdout = stdout
            stdout = ConditionEvaluator.split_output(stdout, task['stdout_split'])
            self.log(f"Task {task_id}{loop_display}: Split STDOUT: '{stdout_stripped}' -> '{stdout}'")
            
        if 'stderr_split' in task:
            original_stderr = stderr
            stderr = ConditionEvaluator.split_output(stderr, task['stderr_split'])
            self.log(f"Task {task_id}{loop_display}: Split STDERR: '{stderr_stripped}' -> '{stderr}'")
        
        # Evaluate success condition if defined, otherwise default to exit_code == 0
        if 'success' in task:
            success_result = ConditionEvaluator.evaluate_condition(task['success'], exit_code, stdout, stderr, self.global_vars, self.task_results, self.debug_log)
            self.log(f"Task {task_id}{loop_display}: Success condition '{task['success']}' evaluated to: {success_result}")
        else:
            success_result = (exit_code == 0)
            self.debug_log(f"Task {task_id}{loop_display}: Success (default): {success_result}")
        
        # CRITICAL: Store the results for future reference - THREAD SAFE
        self.store_task_result(task_id, {
            'exit_code': exit_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': success_result
        })
        
        # Check if we should sleep before the next task
        if 'sleep' in task:
            try:
                sleep_time_str, resolved = ConditionEvaluator.replace_variables(task['sleep'], self.global_vars, self.task_results, self.debug_log)
                if resolved:
                    sleep_time = float(sleep_time_str)
                    self.log(f"Task {task_id}{loop_display}: Sleeping for {sleep_time} seconds")
                    if not self.dry_run:
                        time.sleep(sleep_time)
                else:
                    self.log(f"Task {task_id}{loop_display}: Unresolved variables in sleep time. Skipping sleep.")
            except ValueError:
                self.log(f"Task {task_id}{loop_display}: Invalid sleep time '{task['sleep']}'. Continuing.")
        
        # Check the 'next' condition to determine if we should continue
        should_continue = self.check_next_condition(task, exit_code, stdout, stderr)

        # Update final exit code
        self.final_exit_code = exit_code

        # Determine if this task succeeded
        has_on_failure = 'on_failure' in task
        self.final_success = should_continue is True or (should_continue is False and has_on_failure)

        if should_continue == "NEVER":
            self.final_success = True;
            return None # Stop execution, do not check for on_failure

        if should_continue == "LOOP":
            return "LOOP" 
        
        # If we should continue and we have an 'on_success', jump to that task
        if should_continue and 'on_success' in task:
            try:
                on_success_task = int(task['on_success'])
                self.log(f"Task {task_id}{loop_display}: 'next' condition succeeded, jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                self.log(f"Task {task_id}{loop_display}: Invalid 'on_success' task '{task['on_success']}'. Continuing to next task.")
                return task_id + 1
        
        # If we shouldn't continue but we have an 'on_failure', jump to that task
        if not should_continue and 'on_failure' in task:
            try:
                on_failure_task = int(task['on_failure'])
                self.log(f"Task {task_id}{loop_display}: 'next' condition failed, jumping to Task {on_failure_task}")
                return on_failure_task
            except ValueError:
                self.log(f"Task {task_id}{loop_display}: Invalid 'on_failure' task '{task['on_failure']}'. Stopping.")
                return None

        # Return the next task ID or None to stop
        return task_id + 1 if should_continue else None

    # ===== 9. MAIN ORCHESTRATION =====
    
    def run(self):
        """Execute all tasks based on their flow control."""

        self.parse_task_file()

        # Check for shutdown after parsing
        self._check_shutdown()

        if not self.tasks:
            self.log("No valid tasks found. Exiting.")
            return

        # NEW: Show execution plan if requested
        if self.show_plan:
            self.show_execution_plan()

        # NEW: Conditional validation based on resume mode
        if not self.skip_task_validation:
            validation_successful = self.validate_tasks()
            if not validation_successful:
                ExitHandler.exit_with_code(ExitCodes.TASK_FILE_VALIDATION_FAILED, "Task file validation failed", self.debug)
            # Add shutdown check after potentially long operation
            self._check_shutdown()
        else:
            self.log("# Skipping task file validation due to --skip_task_validation flag")

        # NEW: Additional validation for --start-from
        if self.start_from_task is not None:
            if not self.validate_start_from_task(self.start_from_task):
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, "Start-from task validation failed", self.debug)
            # Optional: Add shutdown check after start-from validation
            self._check_shutdown()

        # NEW: Conditional task dependency validation
        if not self.skip_task_validation:
            self.validate_task_dependencies()
            # Check for shutdown after dependency validation
            self._check_shutdown()
        else:
            self.log("# Skipping task dependency validation due to --skip_task_validation flag")

        # NEW: Conditional host validation
        if not self.skip_host_validation:
            validated_hosts = self.validate_hosts(self.connection_test)
            if validated_hosts is False:
                self.debug_log("Host validation failed. Exiting.")
                self.cleanup()
                ExitHandler.exit_with_code(ExitCodes.HOST_VALIDATION_FAILED, "Host validation failed", self.debug)
            # Check for shutdown after host validation
            self._check_shutdown()
        else:
            self.log("# WARNING: Skipping host validation due to --skip-host-validation flag")
            self.log("# WARNING: Using hostnames as-is without FQDN resolution or reachability check")
            # Create dummy validated_hosts dict for resume mode
            validated_hosts = {}
    
        # For resume mode, collect hostnames but don't validate them
        for task in self.tasks.values():
            if 'hostname' in task and task['hostname']:
                hostname, resolved = ConditionEvaluator.replace_variables(task['hostname'], self.global_vars, self.task_results, self.debug_log)
                if resolved and hostname:
                    validated_hosts[hostname] = hostname  # Use as-is without validation

        # Replace hostnames with validated FQDNs in all tasks
        # NEW: Conditional hostname FQDN replacement
        if not self.skip_host_validation and validated_hosts:
            # Only replace hostnames if we actually validated them
            for task_id, task in self.tasks.items():
                if 'hostname' in task and task['hostname'] in validated_hosts:
                    orig_hostname = task['hostname']
                    fqdn = validated_hosts[orig_hostname]
                    if orig_hostname != fqdn:
                        self.debug_log(f"Replacing hostname '{orig_hostname}' with validated FQDN '{fqdn}'")
                        task['hostname'] = fqdn
        elif self.skip_host_validation:
            self.log("# Skipping hostname FQDN replacement due to --skip-host-validation flag")

        # NEW: Determine starting task ID
        if self.start_from_task is not None:
            start_task_id = self.start_from_task
            
            # Validate that start task exists
            if start_task_id not in self.tasks:
                self.log(f"ERROR: Start task {start_task_id} not found in task definitions")
                available_tasks = sorted(self.tasks.keys())
                self.log(f"Available tasks: {available_tasks}")
                ExitHandler.exit_with_code(ExitCodes.TASK_DEPENDENCY_FAILED, f"Start task {start_task_id} not found", self.debug)
            
            # NEW: Warning about unresolved dependencies
            if start_task_id > 0:
                self.log(f"# WARNING: Task dependencies @X_stdout@, @X_stderr@, @X_success@ for tasks 0-{start_task_id-1} will be unresolved")
                self.log(f"# Tasks {start_task_id}+ may fail if they depend on results from earlier tasks")
                
            self.log(f"# Starting execution from Task {start_task_id}")
        else:
            start_task_id = 0

        next_task_id = start_task_id
        while next_task_id is not None and next_task_id in self.tasks:  # Changed condition
            # Check for shutdown before each task
            self._check_shutdown()

            task = self.tasks[next_task_id]
            if task is None:
                self.log(f"Task {next_task_id}: Task not found. Stopping.")
                break

            result = self.execute_task(task)

            # handle ste special LOOP case
            if result == "LOOP":
                continue # Re-execute the same task

            # Otherwise, update the next_task_id normally
            next_task_id = result

        # Check how we exited the loop
        if next_task_id is None:
            # We exited because a 'next' condition failed
            if self.current_task in self.tasks:
                last_task = self.tasks[self.current_task]
                if 'next' in last_task and last_task['next'] == 'never':
                    # This is a successful completion with 'next=never'
                    self.log("SUCCESS: Task execution completed successfully with 'next=never'.")
                    ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Task execution completed successfully with 'next=never'", self.debug)
                else:
                    # This is a failure due to a 'next' condition
                    self.log("FAILED: Task execution stopped: 'next' condition was not satisfied.")
                    ExitHandler.exit_with_code(ExitCodes.CONDITIONAL_EXECUTION_FAILED, "Task execution stopped: 'next' condition was not satisfied", self.debug)
            else:
                self.log("FAILED: Task execution stopped for an unknown reason.")
                ExitHandler.exit_with_code(ExitCodes.TASK_FAILED, "Task execution stopped for an unknown reason", self.debug)
        elif next_task_id not in self.tasks:  # Changed condition
            # We've successfully completed all tasks or reached a non-existent task
            self.log("SUCCESS: Task execution completed - reached end of defined tasks.")
            ExitHandler.exit_with_code(ExitCodes.SUCCESS, "Task execution completed successfully", self.debug)
        else:
            # Something else stopped execution
            self.log("FAILED: Task execution stopped for an unknown reason.")
            ExitHandler.exit_with_code(ExitCodes.TASK_FAILED, "Task execution stopped for unknown reason", self.debug)


# ===== 10. ENTRY POINT =====

def main():
    parser = argparse.ArgumentParser(description='Execute tasks on remote servers.')
    parser.add_argument('task_file', help='Path to the task file')
    parser.add_argument('-r', '--run', action='store_true', help='Actually run the commands (not dry run)')
    parser.add_argument('-l', '--log-dir', default=None, help='Directory to store log files')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('-t', '--type', choices=['pbrun', 'p7s', 'local', 'wwrs'], help='Execution type (overridden by task-specific settings)')
    parser.add_argument('-o', '--timeout', type=int, default=30, help='Default command timeout in seconds (5-1000, default: 30)')
    parser.add_argument('-c', '--connection-test', action='store_true', help='Check connectivity for pbrun,p7s,wwrs hosts')
    parser.add_argument('-p', '--project', help='Project name for summary logging')
    
    # NEW: Resume capability
    parser.add_argument('--start-from', type=int, metavar='TASK_ID', help='Start execution from specific task ID (resume capability)')
    # NEW: Granular validation control
    parser.add_argument('--skip-task-validation', action='store_true', help='Skip task file and dependency validation (faster resume)')
    parser.add_argument('--skip-host-validation', action='store_true', help='Skip host validation and use hostnames as-is (WARNING: risky!)')
    parser.add_argument('--skip-validation', action='store_true', help='Skip ALL validation (same as --skip-task-validation --skip-host-validation)')
    # show plan
    parser.add_argument('--show-plan', action='store_true', help='Show execution plan and require confirmation before running')

    args = parser.parse_args()

    # Get and create log directory
    log_dir = get_log_directory(args.log_dir, args.debug)

    # Validate timeout range
    if args.timeout < 5:
        print(f"Warning: Timeout {args.timeout} too low, using minimum 5")
        args.timeout = 5
    elif args.timeout > 1000:
        print(f"Warning: Timeout {args.timeout} too high, using maximum 1000")
        args.timeout = 1000
    
    # NEW: Handle convenience flag
    skip_task_validation = args.skip_task_validation or args.skip_validation
    skip_host_validation = args.skip_host_validation or args.skip_validation

    # Warn about risky host validation skip
    if skip_host_validation:
        print("WARNING: Skipping host validation can lead to connection failures!")

    with TaskExecutor(args.task_file, log_dir, not args.run, args.debug, args.type, args.timeout, args.connection_test, args.project, args.start_from, skip_task_validation, skip_host_validation, args.show_plan) as executor:
        executor.run()

### MAIN ###

if __name__ == '__main__':
    main()
