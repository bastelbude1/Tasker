#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASKER 2.1 - Professional Task Automation System
Copyright (C) 2024-2025 Bastelbude and Contributors

This file is part of TASKER.

TASKER is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

TASKER is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with TASKER. If not, see <https://www.gnu.org/licenses/>.

IMPORTANT NOTICE:
Any use of this software in a network/server environment requires
making the complete source code available to all users under AGPL-3.0.
Commercial use must comply with all AGPL-3.0 requirements.

-----------------------------------
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


# Security: Flags that should NEVER be accepted from task files
CLI_ONLY_FLAGS = {'--help', '-h', '--version'}

# Security: Flags that should generate warnings when found in files
SECURITY_SENSITIVE_FLAGS = {
    '--skip-security-validation',
    '--skip-validation',
    '--fire-and-forget'
}


def parse_file_args(task_file_path):
    """
    Parse TASKER arguments from task file header.

    Arguments must appear at the very beginning of the file, before any
    global variables or task definitions. The args block ends at the first
    line that contains '=' but doesn't start with '-' or '--'.

    Args:
        task_file_path: Path to the task file

    Returns:
        List of argument strings (e.g., ['--auto-recovery', '--skip-host-validation'])
    """
    file_args = []

    try:
        with open(task_file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Args block ends at first task or global variable definition
                # (line with '=' that doesn't start with a flag)
                if '=' in line and not line.startswith(('-', '--')):
                    break

                # Collect argument lines (start with - or --)
                if line.startswith(('-', '--')):
                    # Security check: reject CLI-only flags
                    arg_name = line.split('=')[0] if '=' in line else line
                    if arg_name in CLI_ONLY_FLAGS:
                        print(f"ERROR: File-defined argument '{arg_name}' is not allowed (CLI-only flag)", file=sys.stderr)
                        print(f"       Found in {task_file_path} at line {line_num}", file=sys.stderr)
                        sys.exit(20)  # Validation failed exit code

                    # Warning for security-sensitive flags
                    if arg_name in SECURITY_SENSITIVE_FLAGS:
                        print(f"WARNING: File defines security-sensitive flag: {arg_name}")
                        print(f"         Found in {task_file_path} at line {line_num}")
                        print("         This flag reduces security checks - ensure this is intentional")

                    file_args.append(line)

    except (IOError, OSError) as e:
        print(f"ERROR: Failed to read task file for argument parsing: {e}", file=sys.stderr)
        sys.exit(1)

    return file_args


def merge_args(parser, file_args, cli_args):
    """
    Merge file-defined arguments with CLI arguments.

    Precedence: File args provide baseline, CLI args are additive/override.

    Strategy:
    - Parse file args through argparse to get file_namespace
    - Parse CLI args through argparse to get cli_namespace
    - Merge: CLI args override file args for value-based options
    - Merge: CLI args are additive to file args for boolean flags

    Args:
        parser: Configured ArgumentParser instance
        file_args: List of argument strings from file
        cli_args: List of argument strings from CLI (sys.argv[1:])

    Returns:
        Merged argparse.Namespace with effective arguments
    """
    # Parse file args (skip task_file positional arg for now)
    if file_args:
        # Temporarily make task_file optional for file args parsing
        task_file_action = None
        for action in parser._actions:
            if action.dest == 'task_file':
                task_file_action = action
                action.required = False
                break

        # Parse file args with a dummy task file
        file_namespace = parser.parse_args([*file_args, '__dummy__'])

        # Restore task_file requirement
        if task_file_action:
            task_file_action.required = True
    else:
        # No file args, create empty namespace
        file_namespace = parser.parse_args(['__dummy__'])
        # Reset to defaults
        for action in parser._actions:
            if action.dest != 'task_file' and hasattr(file_namespace, action.dest):
                setattr(file_namespace, action.dest, action.default)

    # Parse CLI args normally
    cli_namespace = parser.parse_args(cli_args)

    # Merge: CLI overrides/adds to file args
    merged = argparse.Namespace()

    for action in parser._actions:
        dest = action.dest

        # Skip special argparse internals
        if dest in ('help', 'version'):
            continue

        file_value = getattr(file_namespace, dest, action.default)
        cli_value = getattr(cli_namespace, dest, action.default)

        # For task_file, always use CLI value
        if dest == 'task_file':
            setattr(merged, dest, cli_value)
            continue

        # Boolean flags: combine (file OR cli) - if either is True, result is True
        if isinstance(action, argparse._StoreTrueAction):
            merged_value = file_value or cli_value
            setattr(merged, dest, merged_value)

        # Value options: CLI overrides file
        else:
            # If CLI provided a value different from default, use CLI value
            if cli_value != action.default:
                setattr(merged, dest, cli_value)
            # Otherwise use file value
            else:
                setattr(merged, dest, file_value)

    return merged


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
    parser.add_argument('-t', '--type', choices=['pbrun', 'p7s', 'local', 'wwrs', 'shell'],
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
    parser.add_argument('--auto-recovery', action='store_true',
                       help='Enable automatic error recovery (saves state after each task, auto-resumes on failure)')
    parser.add_argument('--show-recovery-info', action='store_true',
                       help='Display recovery state information and exit')

    # Granular validation control
    parser.add_argument('--skip-task-validation', action='store_true',
                       help='Skip task file and dependency validation (use for faster resume)')
    parser.add_argument('--skip-host-validation', action='store_true',
                       help='Skip host validation - use hostnames as-is without FQDN/connectivity checks (WARNING: may cause connection failures)')
    parser.add_argument('--skip-command-validation', action='store_true',
                       help='Skip command existence validation - allows missing local commands (WARNING: may cause execution failures)')
    parser.add_argument('--skip-security-validation', action='store_true',
                       help='Skip security pattern validation - disables input sanitization checks (WARNING: allows potentially risky patterns)')
    parser.add_argument('--strict-env-validation', action='store_true',
                       help='Require TASKER_ prefix for environment variables in global variable definitions (security: prevents accidental secret leakage)')
    parser.add_argument('--skip-subtask-range-validation', action='store_true',
                       help='Skip subtask ID range convention warnings - suppresses recommendations for distinct ID ranges')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip ALL validation checks (same as --skip-task-validation --skip-host-validation --skip-command-validation --skip-security-validation)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Perform complete validation (task + host + command + security) and exit without task execution')

    # Execution behavior
    parser.add_argument('--fire-and-forget', action='store_true',
                       help='Continue workflow execution even when tasks fail (no routing parameters). WARNING: Failed tasks will not stop execution - use for non-critical workflows only')
    parser.add_argument('--no-task-backup', action='store_true',
                       help='Disable task file backup creation (reduces file clutter, useful for testing)')

    # Execution planning
    parser.add_argument('--show-plan', action='store_true',
                       help='Show execution plan and require confirmation before running')

    # Keep -d/--debug as convenient shorthand for --log-level=DEBUG
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug logging (shorthand for --log-level=DEBUG)')

    # Debug flag to show effective arguments after merging
    parser.add_argument('--show-effective-args', action='store_true',
                       help='Display effective arguments (file + CLI merged) and exit')

    # First, robustly extract task file path using argparse so option values are not mistaken for the positional.
    task_file_path = None
    task_file_action = None
    for action in parser._actions:
        if action.dest == 'task_file':
            task_file_action = action
            break
    if task_file_action:
        # Temporarily make positional optional to allow pre-parse without errors
        task_file_action.required = False
        try:
            pre_args, _unknown = parser.parse_known_args(sys.argv[1:])
            task_file_path = getattr(pre_args, 'task_file', None)
        finally:
            task_file_action.required = True

    if not task_file_path:
        # No task file provided, let argparse handle the error
        args = parser.parse_args()
    else:
        # Parse file-defined arguments
        file_args = parse_file_args(task_file_path)

        # Merge file args with CLI args
        args = merge_args(parser, file_args, sys.argv[1:])

        # Display effective args if requested
        if args.show_effective_args:
            print("Effective TASKER arguments (file + CLI merged):")
            print("=" * 60)
            if file_args:
                print(f"File-defined arguments from {task_file_path}:")
                for arg in file_args:
                    print(f"  {arg}")
                print()
            print("Final effective arguments:")
            for key, value in sorted(vars(args).items()):
                if key != 'task_file' and value not in (None, False, [], ''):
                    print(f"  --{key.replace('_', '-')}: {value}")
            sys.exit(0)

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
    skip_command_validation = args.skip_command_validation or args.skip_validation
    skip_security_validation = args.skip_security_validation or args.skip_validation

    # Warn about risky validation skips
    if skip_task_validation:
        print("WARNING: Skipping task validation can lead to invalid workflows!")
    if skip_host_validation:
        print("WARNING: Skipping host validation can lead to connection failures!")
    if skip_command_validation:
        print("WARNING: Skipping command validation can lead to execution failures!")
    if skip_security_validation:
        print("WARNING: Skipping security validation allows potentially risky patterns!")

    if args.fire_and_forget:
        print("WARNING: Fire-and-forget mode enabled - failed tasks will NOT stop execution!")

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
        skip_security_validation=skip_security_validation,
        skip_subtask_range_validation=args.skip_subtask_range_validation,
        strict_env_validation=args.strict_env_validation,
        show_plan=args.show_plan,
        validate_only=args.validate_only,
        fire_and_forget=args.fire_and_forget,
        no_task_backup=args.no_task_backup,
        auto_recovery=args.auto_recovery,
        show_recovery_info=args.show_recovery_info
    ) as executor:
        executor.run()


### MAIN ###

if __name__ == '__main__':
    main()