# tasker/core/utilities.py
"""
TaskExecutor Core Utilities
---------------------------
Standalone utility functions with no complex dependencies.
"""

import os
import re
import sys
from datetime import datetime


# Enhanced Exit Code System - Two-layer approach for safe workflow preservation
class ExitCodes:
    """System-level exit codes for enhanced error reporting.
    
    CRITICAL: Task-level evaluation ALWAYS uses 0=success, other=failure.
    These codes only affect final tasker.py exit status, not internal workflow logic.
    """
    # Success
    SUCCESS = 0
    
    # Task execution failures (10-19)
    TASK_FAILED = 10
    TASK_TIMEOUT = 11
    TASK_DEPENDENCY_FAILED = 12
    PARALLEL_MIN_SUCCESS_NOT_MET = 13
    CONDITIONAL_EXECUTION_FAILED = 14
    
    # Validation failures (20-29)
    TASK_FILE_VALIDATION_FAILED = 20
    HOST_VALIDATION_FAILED = 21
    DEPENDENCY_VALIDATION_FAILED = 22
    SYNTAX_ERROR = 23
    NO_TASKS_FOUND = 24
    INSTANCE_ALREADY_RUNNING = 25

    # File/Resource errors (30-39)
    TASK_FILE_NOT_FOUND = 30
    TASK_FILE_READ_ERROR = 31
    LOG_DIRECTORY_ERROR = 32
    PERMISSION_DENIED = 33
    
    # System/Signal errors (40-49)
    SIGNAL_INTERRUPT = 40      # Ctrl+C (SIGINT)
    SIGNAL_TERMINATE = 41      # SIGTERM
    SIGNAL_KILL = 42           # SIGKILL
    
    # Configuration errors (50-59)
    INVALID_ARGUMENTS = 50
    INVALID_EXECUTION_TYPE = 51
    INVALID_TIMEOUT = 52
    INVALID_RETURN_CODE = 53
    
    # Network/Connection errors (60-69)
    HOST_UNREACHABLE = 60
    CONNECTION_FAILED = 61
    SSH_KEY_ERROR = 62
    
    # Internal errors (90-99)
    UNEXPECTED_ERROR = 99


class ExitHandler:
    """Safe exit code handler that preserves workflow functionality."""

    # Class variable to store alert callback
    _alert_callback = None

    @classmethod
    def set_alert_callback(cls, callback):
        """Set the alert callback to be called on failure exits.

        Args:
            callback: Callable that takes (exit_code, error_msg) as arguments
        """
        cls._alert_callback = callback

    @classmethod
    def exit_with_code(cls, code, message=None, debug=False):
        """Exit with specific code and optional message.

        IMPORTANT: This only affects final tasker.py exit status.
        Internal task evaluation continues to use 0=success, other=failure.

        Args:
            code: Exit code to use
            message: Optional message to display
            debug: If True, show message with timestamp (default: False)
        """
        if message and debug:
            timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
            if code == ExitCodes.SUCCESS:
                print(f"[{timestamp}] DEBUG: SUCCESS: {message}")
            else:
                print(f"[{timestamp}] DEBUG: FAILURE: {message} (Exit code: {code})")

        # Execute alert callback on failure (non-zero exit code)
        if code != ExitCodes.SUCCESS and cls._alert_callback:
            try:
                cls._alert_callback(code, message or '')
            except Exception as e:
                # Don't let alert failures prevent exit
                print(f"WARNING: Alert callback failed: {e}")

        sys.exit(code)
    
    @staticmethod
    def get_exit_code_description(code):
        """Get human-readable description of exit code."""
        descriptions = {
            0: "Success",
            10: "Task execution failed",
            11: "Task timeout",
            12: "Task dependency failed",
            13: "Parallel execution - minimum success not met",
            14: "Conditional execution failed",
            20: "Task file validation failed",
            21: "Host validation failed",
            22: "Dependency validation failed",
            23: "Syntax error in task file",
            24: "No tasks found",
            30: "Task file not found",
            31: "Task file read error",
            32: "Log directory error",
            33: "Permission denied",
            40: "Interrupted by signal (Ctrl+C)",
            41: "Terminated by signal",
            42: "Killed by signal",
            50: "Invalid command line arguments",
            51: "Invalid execution type",
            52: "Invalid timeout value",
            53: "Invalid return code",
            60: "Host unreachable",
            61: "Connection failed",
            62: "SSH key error",
            99: "Unexpected internal error"
        }
        return descriptions.get(code, f"Unknown exit code: {code}")

    @staticmethod
    def preserve_task_evaluation(exit_code):
        """Preserve original task evaluation logic.
        
        CRITICAL: This method ensures task-level evaluation never changes.
        Task success/failure MUST always be: 0=success, other=failure
        """
        return exit_code == 0


def convert_value(value):
    """Convert a string value to its appropriate type (bool, int, float, or string)."""
    if not isinstance(value, str):
        return value
        
    value = value.strip()
    
    # Boolean conversion
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    
    # Numerical conversion
    try:
        # Try integer first
        if '.' not in value:
            return int(value)
        else:
            return float(value)
    except ValueError:
        pass
    
    # Return as string
    return value


def convert_to_number(value):
    """Convert a value to a number, returning None if not possible."""
    try:
        if isinstance(value, (int, float)):
            return value
        elif isinstance(value, str):
            if '.' in value:
                return float(value)
            else:
                return int(value)
        elif isinstance(value, bool):
            return int(value)  # True -> 1, False -> 0
    except ValueError:
        pass
    return None


def sanitize_for_tsv(value):
    """Sanitize a value for TSV format by replacing problematic characters."""
    if value is None:
        return "N/A"
    return str(value).replace('\t', ' ').replace('\n', ' ').replace('\r', '')


def sanitize_filename(filename):
    """
    Sanitize a filename to make it safe for use as a log file prefix.
    Only allows alphanumeric characters, dots, hyphens, and underscores.
    
    Args:
        filename (str): The filename to sanitize
        
    Returns:
        str: Sanitized filename safe for filesystem use
    """
    # Get the base filename without path
    base_filename = os.path.basename(filename)

    # Remove file extension
    name_without_ext = os.path.splitext(base_filename)[0]

    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\._-]', '_', name_without_ext)

    # Ensure the filename is not empty after sanitization
    if not sanitized:
        sanitized = "task"

    # Limit length to avoid issues with too long filenames
    if len(sanitized) > 50:
        sanitized = sanitized[:50]

    return sanitized


def get_log_directory(cmd_log_dir=None, debug=False):
    """
    Determine and create the log directory based on priority:
    1. Command line argument
    2. Environment variable TASK_EXECUTOR_LOG
    3. Default location ~/TASKER/logs
    
    Args:
        cmd_log_dir (str, optional): Log directory specified via command line
        debug (bool): Enable debug output
        
    Returns:
        str: Path to the log directory
        
    Raises:
        SystemExit: If directory creation fails
    """
    timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')

    # Check command line argument first
    log_dir = cmd_log_dir

    # If not specified, check environment variable
    if not log_dir:
        log_dir = os.environ.get('TASK_EXECUTOR_LOG')

    # If still not specified, use default in home directory
    if not log_dir:
        home_dir = os.path.expanduser("~")
        log_dir = os.path.join(home_dir, "TASKER")

    # Last fallback is the current directory
    if not log_dir:
        log_dir = 'logs'

    # Create directory if it doesn't exist
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            if debug:
                print(f"[{timestamp}] # DEBUG: Created LOG directory: {log_dir}")
        except Exception as e:
            print(f"# ERROR: Creating LOG directory: {str(e)}")
            sys.exit(1)
   
    return log_dir


def format_output_for_log(output, max_length=200, label="OUTPUT"):
    """
    Format command output for logging with proper newline handling and length limiting.
    
    Args:
        output (str): Raw command output
        max_length (int): Maximum length before truncation
        label (str): Label for the output type (STDOUT/STDERR)
    
    Returns:
        str: Formatted output string suitable for logging
    """
    if not output or not output.strip():
        return ""
    
    # Strip leading/trailing whitespace
    cleaned = output.strip()
    
    # Replace actual newlines with \n for single-line logging
    formatted = cleaned.replace('\n', '\\n').replace('\r', '\\r')
    
    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length] + f"... ({len(cleaned)} chars total)"
    
    return formatted

