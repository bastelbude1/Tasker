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
from datetime import datetime

# Add the current directory to the path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Support custom library paths for production environments (e.g., PyYAML location)
# This allows production servers to specify where additional libraries are installed
custom_lib_path = os.getenv('TASKER_LIB_PATH', '/app/COOL/lib')
if custom_lib_path and os.path.exists(custom_lib_path):
    sys.path.insert(0, custom_lib_path)
    # Debug output when custom path is added (check early for debug flag)
    if '--debug' in sys.argv or '-d' in sys.argv:
        print(f"DEBUG: Added custom library path: {custom_lib_path}")

# Import the core TaskExecutor and utilities
from tasker.core.task_executor_main import TaskExecutor
from tasker.core.utilities import get_log_directory, sanitize_filename
from tasker.config.exec_config_loader import get_loader as get_exec_config_loader

# Version information
VERSION = "2.1.6"

# Security: Flags that should NEVER be accepted from task files
CLI_ONLY_FLAGS = {'--help', '-h', '--version', '-V', '--force-instance'}

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
                    # Extract argument name for validation
                    arg_name = line.split('=')[0] if '=' in line else line

                    # Syntax validation: reject single-dash long names (e.g., -auto-recovery)
                    # This catches invalid syntax early before parse_known_args() silently discards it
                    if arg_name.startswith('-') and not arg_name.startswith('--'):
                        arg_without_dash = arg_name[1:]
                        if len(arg_without_dash) > 1:  # Multi-character name with single dash
                            print(f"ERROR: Invalid argument syntax '{arg_name}'", file=sys.stderr)
                            print(f"       Location: {task_file_path} at line {line_num}", file=sys.stderr)
                            print(f"       Long option names require double dash: '--{arg_without_dash}'", file=sys.stderr)
                            sys.exit(2)  # Argparse error code

                    # Security check: reject CLI-only flags
                    if arg_name in CLI_ONLY_FLAGS:
                        print(f"ERROR: File-defined argument '{arg_name}' is not allowed (CLI-only flag)", file=sys.stderr)
                        print(f"       Found in {task_file_path} at line {line_num}", file=sys.stderr)
                        sys.exit(20)  # Validation failed exit code

                    # Warning for security-sensitive flags
                    if arg_name in SECURITY_SENSITIVE_FLAGS:
                        print(f"WARNING: Security-sensitive flag '{arg_name}' found in task file.")
                        print(f"         Location: {task_file_path} at line {line_num}")
                        print("         Action: BLOCKED. Security flags cannot be set via file configuration.")
                        continue # Skip adding this flag

                    file_args.append(line)

    except (IOError, OSError) as e:
        print(f"ERROR: Failed to read task file for argument parsing: {e}", file=sys.stderr)
        sys.exit(1)

    return file_args


def get_explicit_args(parser, args_list):
    """
    Helper to extract only explicitly provided arguments from a list.
    
    Temporarily suppresses defaults to identify which arguments were
    actually provided by the user/file.
    
    Args:
        parser: ArgumentParser instance
        args_list: List of argument strings
        
    Returns:
        Namespace containing only explicit arguments
    """
    # Save original defaults
    defaults = {}
    for action in parser._actions:
        defaults[action] = action.default
        # Suppress defaults so they don't appear in the namespace
        # unless explicitly provided
        action.default = argparse.SUPPRESS
    
    try:
        # Use parse_known_args to avoid errors with partial args
        # or missing positionals (which we might not care about here)
        namespace, _ = parser.parse_known_args(args_list)
        return namespace
    except (argparse.ArgumentError, TypeError, ValueError):
        # Fallback for parsing errors (e.g., invalid argument types)
        # Note: We deliberately do NOT catch SystemExit to allow standard
        # argparse behavior (like --help) to work normally.
        return argparse.Namespace()
    finally:
        # Restore original defaults
        for action, default in defaults.items():
            action.default = default


def merge_args(parser, file_args, cli_args):
    """
    Merge file-defined arguments with CLI arguments.

    Precedence: Default < File < CLI (Explicit)
    
    Logic:
    1. CLI Explicit args override everything.
    2. File Explicit args override Defaults (if not overridden by CLI).
    3. Boolean flags are additive (True if either File or CLI is True).

    Args:
        parser: Configured ArgumentParser instance
        file_args: List of argument strings from file
        cli_args: List of argument strings from CLI (sys.argv[1:])

    Returns:
        Merged argparse.Namespace with effective arguments
    """
    # 1. Get explicit CLI args (what the user actually typed)
    cli_explicit = get_explicit_args(parser, cli_args)
    
    # 2. Get explicit File args
    # We must include a dummy positional arg if one is required (task_file)
    # to prevent parse_known_args from potentially getting confused
    # (though parse_known_args usually handles missing positionals gracefully,
    # the current parser setup expects it)
    file_args_with_dummy = list(file_args) + ['__dummy__'] if file_args else ['__dummy__']
    file_explicit = get_explicit_args(parser, file_args_with_dummy)

    # 3. Get full standard parse from CLI
    # This provides the baseline: Defaults + CLI args (with type conversion etc.)
    # This is our starting point for the merged namespace.
    final_ns = parser.parse_args(cli_args)
    
    # 4. Apply File args where appropriate
    for action in parser._actions:
        dest = action.dest
        
        # Skip special internals and the positional argument
        # (task_file is handled by the main CLI parse)
        if dest in ('help', 'version', 'task_file'):
            continue
            
        # If the file explicitly provided this argument...
        if hasattr(file_explicit, dest):
            file_val = getattr(file_explicit, dest)
            
            # Special handling for boolean store_true (Additive)
            if isinstance(action, argparse._StoreTrueAction):
                # Note: store_true flags are toggle-only and cannot be explicitly set to False
                # For store_false or BooleanOptionalAction, different logic would be needed.
                # Current logic implements an OR operation (File=True OR CLI=True).
                if file_val:
                    setattr(final_ns, dest, True)
            else:
                # For values: Only apply file value if CLI did NOT explicitly provide it
                if not hasattr(cli_explicit, dest):
                    setattr(final_ns, dest, file_val)
                    
    return final_ns


def get_available_exec_types():
    """
    Get available execution types from config file.

    Returns:
        list: Sorted list of available execution types including 'local'
    """
    # Capture config loading messages to detect errors
    config_messages = []

    def capture_callback(msg):
        config_messages.append(msg)

    try:
        # Load config with message capture
        loader = get_exec_config_loader(debug_callback=capture_callback)
        config_types = loader.get_execution_types()

        # Warn if config loading had errors (but not for expected missing file)
        error_messages = [msg for msg in config_messages if 'ERROR:' in msg or 'WARNING:' in msg]
        if error_messages:
            # Filter out expected "missing config" warnings
            unexpected_errors = [msg for msg in error_messages
                                if 'No execution_types.yaml config found' not in msg
                                and 'PyYAML not available' not in msg]
            if unexpected_errors:
                print("Warning: Configuration loading issues detected:", file=sys.stderr)
                for msg in unexpected_errors:
                    print(f"         {msg}", file=sys.stderr)
                print("         Only 'local' execution type will be available.", file=sys.stderr)

        # Always include 'local', then add config-based types
        return sorted(['local', *config_types])
    except Exception as e:
        # Catch any unexpected exceptions during argument parsing
        print(f"Warning: Unexpected error loading config: {e}", file=sys.stderr)
        print("         Only 'local' execution type will be available.", file=sys.stderr)
        return ['local']


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

    # Version information
    parser.add_argument('-V', '--version', action='version', version=f'TASKER v{VERSION}')

    # Positional arguments
    parser.add_argument('task_file', help='Path to the task file')
    
    # Execution control
    parser.add_argument('-r', '--run', action='store_true', 
                       help='Actually run the commands (not dry run)')
    parser.add_argument('-l', '--log-dir', default=None, 
                       help='Directory to store log files')
    parser.add_argument('--log-level', choices=['ERROR', 'WARN', 'INFO', 'DEBUG'],
                       default='INFO', help='Set logging level (default: INFO)')
    parser.add_argument('-t', '--type', choices=get_available_exec_types(),
                       help='Execution type (overridden by task-specific settings)')
    parser.add_argument('-p', '--project',
                       help='Project name for summary logging')
    
    # Resume capability
    parser.add_argument('--start-from', type=int, metavar='TASK_ID',
                       help='Start execution from specific task ID (resume capability)')
    parser.add_argument('--auto-recovery', action='store_true',
                       help='Enable automatic error recovery (saves state after each task, auto-resumes on failure)')
    parser.add_argument('--show-recovery-info', action='store_true',
                       help='Display recovery state information and exit')
    parser.add_argument('-y', '--yes', action='store_true',
                       help='Auto-confirm all prompts (use saved environment values during recovery, skip confirmations)')

    # Granular validation control
    parser.add_argument('--skip-task-validation', action='store_true',
                       help='Skip task file and dependency validation (use for faster resume)')
    parser.add_argument('--skip-host-validation', action='store_true',
                       help='Skip host validation - use hostnames as-is without FQDN/connectivity checks (WARNING: may cause connection failures)')
    parser.add_argument('--skip-unresolved-host-validation', action='store_true',
                       help='Allow unresolved hostname variables - enables runtime hostname resolution pattern (only skips validation for hostnames with variables like @0_stdout@)')
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
    parser.add_argument('--instance-check', action='store_true',
                       help='Enable workflow instance control - prevents multiple instances of the same workflow from running concurrently (hash-based lock file in ~/TASKER/locks/)')
    parser.add_argument('--force-instance', action='store_true',
                       help='Force workflow execution even if instance already running - bypasses instance control check (requires --instance-check)')

    # Execution planning
    parser.add_argument('--show-plan', action='store_true',
                       help='Show execution plan and require confirmation before running')

    # Alert on failure
    parser.add_argument('--alert-on-failure', metavar='SCRIPT_PATH',
                       help='Execute alert script when workflow fails (receives context via environment variables: TASKER_LOG_FILE, TASKER_STATE_FILE, TASKER_TASK_FILE, TASKER_FAILED_TASK, TASKER_EXIT_CODE, TASKER_ERROR, TASKER_TIMESTAMP)')

    # Output and Reporting
    parser.add_argument('--output-json', metavar='PATH', nargs='?', const=True,
                       help='Generate machine-readable workflow summary in JSON format. If PATH is provided, saves to that location. If flag is used without PATH, auto-generates filename (taskfile_YYYYMMDD_HHMMSS_microsec.json) in ~/TASKER/output/. Automatically enables --auto-recovery.')

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

    
    # Handle convenience flag
    skip_task_validation = args.skip_task_validation or args.skip_validation
    skip_host_validation = args.skip_host_validation or args.skip_validation
    skip_unresolved_host_validation = args.skip_unresolved_host_validation
    skip_command_validation = args.skip_command_validation or args.skip_validation
    skip_security_validation = args.skip_security_validation or args.skip_validation

    # Warn about risky validation skips
    if skip_task_validation:
        print("WARNING: Skipping task validation can lead to invalid workflows!")
    if skip_host_validation:
        print("WARNING: Skipping host validation can lead to connection failures!")
    if skip_unresolved_host_validation:
        if not skip_host_validation:
            print("INFO: Runtime hostname resolution enabled - hostnames with variables will be resolved during execution")
        else:
            print("INFO: --skip-unresolved-host-validation has no effect when --skip-host-validation is set")
    if skip_command_validation:
        print("WARNING: Skipping command validation can lead to execution failures!")
    if skip_security_validation:
        print("WARNING: Skipping security validation allows potentially risky patterns!")

    if args.fire_and_forget:
        print("WARNING: Fire-and-forget mode enabled - failed tasks will NOT stop execution!")

    # Warn if --force-instance is set without --instance-check
    if args.force_instance and not args.instance_check:
        print("WARNING: --force-instance has no effect without --instance-check; ignoring.")

    # Auto-enable --auto-recovery when --output-json is specified (required dependency)
    if args.output_json and not args.auto_recovery:
        args.auto_recovery = True
        print("INFO: --auto-recovery automatically enabled (required by --output-json)")

    # Generate default output JSON path if flag used without value
    if args.output_json is True:
        # Create default output directory
        default_output_dir = os.path.expanduser('~/TASKER/output')
        try:
            os.makedirs(default_output_dir, exist_ok=True)
        except OSError as e:
            print(f"ERROR: Failed to create output directory {default_output_dir}: {e}", file=sys.stderr)
            sys.exit(1)

        # Generate filename using same pattern as log files
        sanitized_prefix = sanitize_filename(args.task_file)
        file_ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        args.output_json = os.path.join(default_output_dir, f"{sanitized_prefix}_{file_ts}.json")
        print(f"INFO: JSON output will be saved to: {args.output_json}")

    # Execute tasks with context manager for proper cleanup
    with TaskExecutor(
        task_file=args.task_file,
        log_dir=log_dir,
        dry_run=not args.run,
        log_level=args.log_level,
        exec_type=args.type,
        timeout=None,  # Timeout now comes from YAML config or defaults to 300
        project=args.project,
        start_from_task=args.start_from,
        skip_task_validation=skip_task_validation,
        skip_host_validation=skip_host_validation,
        skip_unresolved_host_validation=skip_unresolved_host_validation,
        skip_command_validation=skip_command_validation,
        skip_security_validation=skip_security_validation,
        skip_subtask_range_validation=args.skip_subtask_range_validation,
        strict_env_validation=args.strict_env_validation,
        show_plan=args.show_plan,
        validate_only=args.validate_only,
        fire_and_forget=args.fire_and_forget,
        no_task_backup=args.no_task_backup,
        instance_check=args.instance_check,
        force_instance=args.force_instance,
        auto_recovery=args.auto_recovery,
        show_recovery_info=args.show_recovery_info,
        auto_confirm=args.yes,
        alert_on_failure=args.alert_on_failure,
        output_json=args.output_json
    ) as executor:
        executor.run()


### MAIN ###

if __name__ == '__main__':
    main()