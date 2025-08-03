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

