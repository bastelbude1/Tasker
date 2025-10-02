#!/usr/bin/env python3

"""
TASKER 2.1 - Command Line Interface
-----------------------------------
Clean CLI wrapper for the TASKER 2.1 task execution system.

This script provides the command-line interface and argument parsing for TASKER,
while delegating all core functionality to the modular TaskExecutor class.

The TASKER system reads task files with instructions to execute commands on remote servers,
handles flow control based on various conditions, and logs results with comprehensive
validation and error handling.

Enhanced Features:
- Global variable support using @VARIABLE@ syntax
- Parallel task execution with threading and retry logic  
- Conditional task execution based on runtime conditions
- Comprehensive logging with granular log levels (ERROR, WARN, INFO, DEBUG)
- Thread-safe execution with graceful shutdown handling
- Resume capability for long-running workflows
- Comprehensive validation with granular control options
"""

import os
import sys
import argparse

# Add the current directory to the path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the core TaskExecutor and utilities
from tasker.core.task_executor_main import TaskExecutor
from tasker.core.utilities import get_log_directory


def main():
    """Main entry point for TASKER 2.1 command-line interface."""
    parser = argparse.ArgumentParser(
        description='TASKER 2.1 - Execute tasks on remote servers with comprehensive flow control.',
        epilog='''
Examples:
  %(prog)s tasks.txt -r                    # Execute tasks (real run)
  %(prog)s tasks.txt --log-level=DEBUG     # Execute with debug logging  
  %(prog)s tasks.txt --show-plan           # Show execution plan first
  %(prog)s tasks.txt --start-from=5        # Resume from task 5
  %(prog)s tasks.txt --validate-only       # Only validate, don't execute
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional arguments
    parser.add_argument('task_file', help='Path to the task file')
    
    # Execution control
    parser.add_argument('-r', '--run', action='store_true', 
                       help='Actually run the commands (not dry run)')
    parser.add_argument('-l', '--log-dir', default=None, 
                       help='Directory to store log files')
    parser.add_argument('--log-level', choices=['ERROR', 'WARN', 'INFO', 'DEBUG'], 
                       default='INFO', help='Set logging level (default: INFO)')
    parser.add_argument('-t', '--type', choices=['pbrun', 'p7s', 'local', 'wwrs'], 
                       help='Execution type (overridden by task-specific settings)')
    parser.add_argument('-o', '--timeout', type=int, default=30, 
                       help='Default command timeout in seconds (5-1000, default: 30)')
    parser.add_argument('-c', '--connection-test', action='store_true', 
                       help='Check connectivity for pbrun,p7s,wwrs hosts')
    parser.add_argument('-p', '--project', 
                       help='Project name for summary logging')
    
    # Resume capability
    parser.add_argument('--start-from', type=int, metavar='TASK_ID', 
                       help='Start execution from specific task ID (resume capability)')
    
    # Granular validation control
    parser.add_argument('--skip-task-validation', action='store_true', 
                       help='Skip task file and dependency validation (faster resume)')
    parser.add_argument('--skip-host-validation', action='store_true', 
                       help='Skip host validation and use hostnames as-is (WARNING: risky!)')
    parser.add_argument('--skip-validation', action='store_true', 
                       help='Skip ALL validation (same as --skip-task-validation --skip-host-validation)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Perform complete validation (task + host) and exit - no task execution')
    
    # Execution planning
    parser.add_argument('--show-plan', action='store_true', 
                       help='Show execution plan and require confirmation before running')

    # Keep -d/--debug as convenient shorthand for --log-level=DEBUG
    parser.add_argument('-d', '--debug', action='store_true', 
                       help='Enable debug logging (shorthand for --log-level=DEBUG)')

    args = parser.parse_args()

    # Handle debug flag as shorthand
    if args.debug:
        if args.log_level == 'INFO':  # Only override if user didn't explicitly set log level
            args.log_level = 'DEBUG'

    # Get and create log directory
    log_dir = get_log_directory(args.log_dir, args.log_level == 'DEBUG')

    # Validate timeout range
    if args.timeout < 5:
        print(f"Warning: Timeout {args.timeout} too low, using minimum 5")
        args.timeout = 5
    elif args.timeout > 1000:
        print(f"Warning: Timeout {args.timeout} too high, using maximum 1000")
        args.timeout = 1000
    
    # Handle convenience flag
    skip_task_validation = args.skip_task_validation or args.skip_validation
    skip_host_validation = args.skip_host_validation or args.skip_validation

    # Warn about risky host validation skip
    if skip_host_validation:
        print("WARNING: Skipping host validation can lead to connection failures!")

    # Execute tasks with context manager for proper cleanup
    with TaskExecutor(
        task_file=args.task_file,
        log_dir=log_dir,
        dry_run=not args.run,
        log_level=args.log_level,
        exec_type=args.type,
        timeout=args.timeout,
        connection_test=args.connection_test,
        project=args.project,
        start_from_task=args.start_from,
        skip_task_validation=skip_task_validation,
        skip_host_validation=skip_host_validation,
        show_plan=args.show_plan,
        validate_only=args.validate_only
    ) as executor:
        executor.run()


### MAIN ###

if __name__ == '__main__':
    main()