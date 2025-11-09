# tasker/executors/sequential_executor.py
"""
Sequential Task Executor
------------------------
Normal sequential task execution with flow control.
"""

import time
import threading
from .base_executor import BaseExecutor
from ..core.condition_evaluator import ConditionEvaluator
from ..core.utilities import ExitHandler, ExitCodes, format_output_for_log
from ..core.streaming_output_handler import create_memory_efficient_handler


class SequentialExecutor(BaseExecutor):
    """Sequential task executor for normal task execution."""
    
    @staticmethod
    def execute_task(task, executor_instance):
        """Execute a single task and return whether to continue to the next task."""
        task_id = int(task['task'])
        executor_instance.current_task = task_id # track current task

        # NEW: Check if this is a conditional task
        if task.get('type') == 'conditional':
            from .conditional_executor import ConditionalExecutor
            return ConditionalExecutor.execute_conditional_tasks(task, executor_instance)

        # NEW: Check if this is a parallel task
        if task.get('type') == 'parallel':
            from .parallel_executor import ParallelExecutor
            return ParallelExecutor.execute_parallel_tasks(task, executor_instance)

        # NEW: Check if this is a decision block
        if task.get('type') == 'decision':
            from .decision_executor import DecisionExecutor
            next_task_id = DecisionExecutor.execute_decision_block(task, task_id, executor_instance)
            # Decision blocks return next task ID or None
            if next_task_id is None:
                return False  # Stop execution
            else:
                # Return the next task ID to execute
                return next_task_id

        # Get loop iteration display if looping
        # For tasks with loop parameter, always show iteration number starting from .1
        loop_display = ""
        if 'loop' in task and task.get('next') == 'loop':
            # Initialize both loop counter AND iteration counter on first encounter
            if hasattr(executor_instance, '_state_manager'):
                if executor_instance._state_manager.get_loop_counter(task_id) == 0:
                    # First time seeing this loop task - initialize everything
                    executor_instance._state_manager.set_loop_counter(task_id, int(task['loop']))
                    executor_instance._state_manager.set_loop_iteration(task_id, 1)
                loop_display = f".{executor_instance._state_manager.get_loop_iteration(task_id)}"
            else:
                if not hasattr(executor_instance, 'loop_iterations'):
                    executor_instance.loop_iterations = {}
                if not hasattr(executor_instance, 'loop_counter'):
                    executor_instance.loop_counter = {}

                if task_id not in executor_instance.loop_counter:
                    # First time seeing this loop task - initialize everything
                    executor_instance.loop_counter[task_id] = int(task['loop'])
                    executor_instance.loop_iterations[task_id] = 1
                loop_display = f".{executor_instance.loop_iterations[task_id]}"
        elif hasattr(executor_instance, 'loop_iterations') and task_id in executor_instance.loop_iterations:
            # For tasks already in loop (after first iteration)
            loop_display = f".{executor_instance.loop_iterations[task_id]}"

        # Check for shutdown before task execution
        executor_instance._check_shutdown()

        # Check pre-execution condition
        if 'condition' in task:
            condition_result = ConditionEvaluator.evaluate_condition(task['condition'], 0, "", "", executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
            if not condition_result:
                executor_instance.log(f"Task {task_id}{loop_display}: Condition '{task['condition']}' evaluated to FALSE, skipping task")
                # CRITICAL: Store results for skipped task - THREAD SAFE
                skip_msg = 'Task skipped due to condition'
                executor_instance.store_task_result(task_id, {
                    'exit_code': -1,     # Special: Task was skipped
                    'stdout': '',
                    'stderr': skip_msg,
                    'stdout_file': None,
                    'stderr_file': None,
                    'stdout_size': 0,
                    'stderr_size': len(skip_msg),
                    'stdout_truncated': False,
                    'stderr_truncated': False,
                    'success': False
                })
                return task_id + 1  # Continue to next task
            else:
                executor_instance.log(f"Task {task_id}{loop_display}: Condition '{task['condition']}' evaluated to TRUE, executing task")

        # Update tracking for summary
        executor_instance.final_task_id = task_id
        state_mgr = getattr(executor_instance, '_state_manager', None)
        executor_instance.final_hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', 'N/A'), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug, state_mgr)
        executor_instance.final_command, _ = ConditionEvaluator.replace_variables(task.get('command', 'N/A'), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug, state_mgr)
        
        # Check if this is a return-only task (has return but no command)
        if 'return' in task and 'command' not in task:
            # Pure return block - no command to execute
            executor_instance.log(f"Task {task_id}{loop_display}: Return-only task (no command to execute)")

            # Parse and validate the return value FIRST
            if executor_instance.final_command == 'N/A':
                executor_instance.final_command = 'return'

            try:
                return_code = int(task['return'])
                executor_instance.log(f"Task {task_id}{loop_display}: Returning with exit code {return_code}")

                # Determine exit_code and success based on the actual return value
                exit_code = return_code
                stdout = ""
                stderr = ""
                success_result = (return_code == 0)

                # Store the accurate results
                executor_instance.store_task_result(task_id, {
                    'exit_code': exit_code,
                    'stdout': stdout,
                    'stderr': stderr,
                    'stdout_file': None,
                    'stderr_file': None,
                    'stdout_size': len(stdout),
                    'stderr_size': len(stderr),
                    'stdout_truncated': False,
                    'stderr_truncated': False,
                    'success': success_result
                })

                # Update final status
                executor_instance.final_exit_code = return_code
                executor_instance.final_success = success_result

                # Log success or failure
                if return_code == 0:
                    executor_instance.log("SUCCESS: Task execution completed successfully with return code 0")
                else:
                    executor_instance.log(f"FAILURE: Task execution failed with return code {return_code}")

                # Cleanup and exit
                executor_instance.cleanup()
                ExitHandler.exit_with_code(return_code, f"Task execution completed with return code {return_code}", False)

            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid return code '{task['return']}'. Exiting with code 1.")

                # Store failure results for invalid return code
                exit_code = 1
                stdout = ""
                stderr = f"Invalid return code: {task['return']}"
                success_result = False

                executor_instance.store_task_result(task_id, {
                    'exit_code': exit_code,
                    'stdout': stdout,
                    'stderr': stderr,
                    'stdout_file': None,
                    'stderr_file': None,
                    'stdout_size': len(stdout),
                    'stderr_size': len(stderr),
                    'stdout_truncated': False,
                    'stderr_truncated': False,
                    'success': success_result
                })

                # Update final status
                executor_instance.final_exit_code = 1
                executor_instance.final_success = False

                executor_instance.log("FAILURE: Task execution failed with invalid return code")

                # Cleanup and exit
                executor_instance.cleanup()
                ExitHandler.exit_with_code(ExitCodes.INVALID_ARGUMENTS, "Invalid return code specified", False)
            # This point is never reached due to exit above
            return None
        
        # Replace variables in command and arguments
        state_mgr = getattr(executor_instance, '_state_manager', None)
        hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', ''), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug, state_mgr)
        command, _ = ConditionEvaluator.replace_variables(task.get('command', ''), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug, state_mgr)
        arguments, _ = ConditionEvaluator.replace_variables(task.get('arguments', ''), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug, state_mgr)

        # Determine execution type (from task, args, env, or default)
        exec_type = executor_instance.determine_execution_type(task, task_id, loop_display)
        # special case for local host
        if executor_instance.final_hostname == '': executor_instance.final_hostname = exec_type

        # Construct the command array based on execution type
        cmd_array = executor_instance.build_command_array(exec_type, hostname, command, arguments)
        executor_instance.log_debug(f"Command array: {cmd_array}")

        # Log the full command for the user
        full_command_display = ' '.join(cmd_array)
        executor_instance.final_command = full_command_display # better to have full command in the summary log

        # Get timeout for this task
        task_timeout = executor_instance.get_task_timeout(task)
        #executor_instance.log(f"Task {task_id}{loop_display}: Using timeout of {task_timeout} [s]")

        # Execute the command (or simulate in dry run mode)
        output_handler = None  # Initialize for dry-run mode compatibility
        if executor_instance.dry_run:
            executor_instance.log(f"Task {task_id}{loop_display}: [DRY RUN] Would execute: {full_command_display}")
            exit_code = 0
            stdout = "DRY RUN STDOUT"
            stderr = ""
        else:
            executor_instance.log(f"Task {task_id}{loop_display}: Executing [{exec_type}]: {full_command_display}")
            try:
                # Execute using context manager for automatic cleanup
                import subprocess

                # Create memory-efficient output handler with 1MB limit for cross-task compatibility
                # Lowered from 10MB to ensure temp files are created for outputs ≥1MB
                max_memory_mb = 1

                with create_memory_efficient_handler(max_memory_mb) as output_handler:
                    with subprocess.Popen(
                        cmd_array,
                        shell=False, # More secure
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    ) as process:
                        # GUIDELINE DEVIATION: Using manual streaming instead of process.communicate(timeout=X)
                        # This intentionally deviates from repo coding guidelines to achieve memory efficiency.
                        # Standard communicate() loads entire output into memory, causing OOM with large outputs (1GB+).
                        # Manual streaming with temp file fallback prevents memory exhaustion while maintaining timeout support.

                        # Create shutdown check callback to terminate subprocess on signal
                        def shutdown_check():
                            return getattr(executor_instance, '_shutdown_requested', False)

                        stdout, stderr, exit_code, timed_out = output_handler.stream_process_output(
                            process, timeout=task_timeout, shutdown_check=shutdown_check
                        )

                        # Log memory usage for large outputs
                        memory_info = output_handler.get_memory_usage_info()
                        if memory_info['using_temp_files']:
                            executor_instance.log_debug(f"Task {task_id}{loop_display}: Used temp files for large output "
                                                       f"(stdout: {memory_info['stdout_size']} characters, "
                                                       f"stderr: {memory_info['stderr_size']} characters)")

                        if timed_out:
                            executor_instance.log(f"Task {task_id}{loop_display}: Timeout after {task_timeout} seconds. Process killed.")
                            exit_code = 124  # Common exit code for timeout
                            stderr += f"\nProcess killed after timeout of {task_timeout} seconds"
            except Exception as e:
                executor_instance.log(f"Task {task_id}{loop_display}: Error executing command: {str(e)}")

                # CRITICAL: Fatal error detection for missing commands
                error_msg = str(e).lower()
                if "no such file or directory" in error_msg or "[errno 2]" in error_msg:
                    executor_instance.log("FATAL ERROR: # EXECUTION TERMINATED: Missing command detected during runtime")

                    # ExitCodes already imported at top of file
                    import sys
                    sys.exit(ExitCodes.TASK_FILE_VALIDATION_FAILED)

                exit_code = 1
                stdout = ""
                stderr = str(e)
        
        # Log the results
        stdout_stripped = stdout.rstrip('\n')
        stderr_stripped = stderr.rstrip('\n')
        executor_instance.log(f"Task {task_id}{loop_display}: Exit code: {exit_code}")
        
        # Format STDOUT for clean logging
        formatted_stdout = format_output_for_log(stdout_stripped, max_length=200, label="STDOUT")
        if formatted_stdout:
            executor_instance.log(f"Task {task_id}{loop_display}: STDOUT: {formatted_stdout}")
        
        # Format STDERR for clean logging  
        formatted_stderr = format_output_for_log(stderr_stripped, max_length=200, label="STDERR")
        if formatted_stderr:
            executor_instance.log(f"Task {task_id}{loop_display}: STDERR: {formatted_stderr}")
        
        # Process output splitting if specified
        if 'stdout_split' in task:
            original_stdout = stdout
            stdout = ConditionEvaluator.split_output(stdout, task['stdout_split'])
            # INFO mode: Show only result with proper formatting; DEBUG mode: Show detailed split operation
            formatted_split_stdout = format_output_for_log(stdout, max_length=200, label="STDOUT")
            if formatted_split_stdout:
                executor_instance.log(f"Task {task_id}{loop_display}: Split STDOUT: {formatted_split_stdout}")
            executor_instance.log_debug(f"Task {task_id}{loop_display}: Split STDOUT (stdout_split={task['stdout_split']}): '{stdout_stripped}' -> '{stdout}'")

        if 'stderr_split' in task:
            stderr = ConditionEvaluator.split_output(stderr, task['stderr_split'])
            # INFO mode: Show only result with proper formatting; DEBUG mode: Show detailed split operation
            formatted_split_stderr = format_output_for_log(stderr, max_length=200, label="STDERR")
            if formatted_split_stderr:
                executor_instance.log(f"Task {task_id}{loop_display}: Split STDERR: {formatted_split_stderr}")
            executor_instance.log_debug(f"Task {task_id}{loop_display}: Split STDERR (stderr_split={task['stderr_split']}): '{stderr_stripped}' -> '{stderr}'")
        
        # Evaluate success condition if defined, otherwise default to exit_code == 0
        # Support for 'failure' parameter: inverse of success condition
        if 'success' in task:
            success_result = ConditionEvaluator.evaluate_condition(task['success'], exit_code, stdout, stderr, executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)

            # Enhanced logging: show variable resolution when splits are involved
            split_info = ""
            if ('stdout_split' in task or 'stderr_split' in task) and ('stdout' in task['success'] or 'stderr' in task['success']):
                resolution_parts = []
                if 'stdout' in task['success']:
                    resolution_parts.append(f"stdout='{stdout}'")
                if 'stderr' in task['success']:
                    resolution_parts.append(f"stderr='{stderr}'")
                if resolution_parts:
                    split_info = f" ({', '.join(resolution_parts)})"

            executor_instance.log(f"Task {task_id}{loop_display}: Success condition '{task['success']}' evaluated to: {success_result}{split_info}")
        elif 'failure' in task:
            # Inverse logic: default to success=true, then check failure condition
            success_result = True
            failure_result = ConditionEvaluator.evaluate_condition(task['failure'], exit_code, stdout, stderr, executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)

            # If failure condition is met, task failed (invert)
            if failure_result:
                success_result = False

            # Enhanced logging: show variable resolution when splits are involved
            split_info = ""
            if ('stdout_split' in task or 'stderr_split' in task) and ('stdout' in task['failure'] or 'stderr' in task['failure']):
                resolution_parts = []
                if 'stdout' in task['failure']:
                    resolution_parts.append(f"stdout='{stdout}'")
                if 'stderr' in task['failure']:
                    resolution_parts.append(f"stderr='{stderr}'")
                if resolution_parts:
                    split_info = f" ({', '.join(resolution_parts)})"

            executor_instance.log(f"Task {task_id}{loop_display}: Failure condition '{task['failure']}' evaluated to: {failure_result}{split_info} → success={success_result}")
        else:
            success_result = (exit_code == 0)
            executor_instance.log_debug(f"Task {task_id}{loop_display}: Success (default): {success_result}")

        # Get temp file paths and memory info from output handler
        stdout_file_path = output_handler.get_temp_file_path('stdout') if output_handler else None
        stderr_file_path = output_handler.get_temp_file_path('stderr') if output_handler else None
        memory_info = output_handler.get_memory_usage_info() if output_handler else {}

        # Strategy: Store full output when small (<1MB), use 1MB previews only for large outputs (with temp files)
        # This preserves cross-task variable substitution for small outputs while maintaining JSON size limits
        if stdout_file_path:
            # Large output (≥1MB) - temp file exists, use 1MB preview for JSON
            stdout_preview = output_handler.get_preview('stdout') if output_handler else stdout
        else:
            # Small output (<1MB) - no temp file, data already in memory, store full output
            stdout_preview = stdout

        if stderr_file_path:
            # Large output (≥1MB) - temp file exists, use 1MB preview for JSON
            stderr_preview = output_handler.get_preview('stderr') if output_handler else stderr
        else:
            # Small output (<1MB) - no temp file, data already in memory, store full output
            stderr_preview = stderr

        # Preserve split output if splitting was applied (lines 285-300 above)
        # Split operations always override preview logic to ensure workflow correctness
        stdout_modified = 'stdout_split' in task
        stderr_modified = 'stderr_split' in task

        # Calculate metadata based on whether split operations were applied
        # CRITICAL: When split operations are applied, use processed output size (not raw)
        # Truncation flags and sizes must reflect the STORED content (preview or split result)
        if stdout_modified:
            # Split operation applied - store full processed result
            stdout_preview = stdout  # Use split result
            stdout_truncated = False  # Split result stored in full (not truncated)
            stdout_size = len(stdout)  # Size of split result
            # CRITICAL: Clear temp file reference when split is applied
            # Split result is authoritative - prevent StateManager from reading raw temp file
            stdout_file_path = None
        else:
            # No split - use preview/temp file logic
            # (stdout_preview already set by lines 350-358)
            # CRITICAL: Check BOTH size threshold AND handler's preview truncation flag
            # Handler flag catches binary data truncated to fit base64 under 1MB
            stdout_truncated = (
                (memory_info.get('stdout_size', len(stdout)) > output_handler.MAX_JSON_TASK_OUTPUT
                 if output_handler else False) or
                (output_handler.preview_was_truncated('stdout') if output_handler else False)
            )
            stdout_size = memory_info.get('stdout_size', len(stdout))

        if stderr_modified:
            # Split operation applied - store full processed result
            stderr_preview = stderr  # Use split result
            stderr_truncated = False  # Split result stored in full (not truncated)
            stderr_size = len(stderr)  # Size of split result
            # CRITICAL: Clear temp file reference when split is applied
            # Split result is authoritative - prevent StateManager from reading raw temp file
            stderr_file_path = None
        else:
            # No split - use preview/temp file logic
            # (stderr_preview already set by lines 359-365)
            # CRITICAL: Check BOTH size threshold AND handler's preview truncation flag
            # Handler flag catches binary data truncated to fit base64 under 1MB
            stderr_truncated = (
                (memory_info.get('stderr_size', len(stderr)) > output_handler.MAX_JSON_TASK_OUTPUT
                 if output_handler else False) or
                (output_handler.preview_was_truncated('stderr') if output_handler else False)
            )
            stderr_size = memory_info.get('stderr_size', len(stderr))

        # CRITICAL: Store the results for future reference - THREAD SAFE
        executor_instance.store_task_result(task_id, {
            'exit_code': exit_code,
            'stdout': stdout_preview,  # Preview or full output depending on size
            'stderr': stderr_preview,  # Preview or full output depending on size
            'stdout_file': stdout_file_path,  # Temp file path for cross-task access
            'stderr_file': stderr_file_path,  # Temp file path for cross-task access
            'stdout_size': stdout_size,
            'stderr_size': stderr_size,
            'stdout_truncated': stdout_truncated,
            'stderr_truncated': stderr_truncated,
            'success': success_result
        })
        
        # Check if we should sleep before the next task
        if 'sleep' in task:
            try:
                state_mgr = getattr(executor_instance, '_state_manager', None)
                sleep_time_str, resolved = ConditionEvaluator.replace_variables(task['sleep'], executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug, state_mgr)
                if resolved:
                    sleep_time = float(sleep_time_str)
                    executor_instance.log(f"Task {task_id}{loop_display}: Sleeping for {sleep_time} seconds")
                    if not executor_instance.dry_run and sleep_time > 0:
                        # Sequential execution: use simple time.sleep() with periodic shutdown checks
                        # Parallel executor uses non-blocking sleep to avoid thread pool starvation
                        sleep_interval = 0.5  # Check every 500ms
                        elapsed = 0
                        while elapsed < sleep_time:
                            if getattr(executor_instance, '_shutdown_requested', False):
                                executor_instance.log(f"Task {task_id}{loop_display}: Sleep interrupted by shutdown signal")
                                executor_instance._check_shutdown()  # Trigger shutdown
                                break
                            chunk = min(sleep_interval, sleep_time - elapsed)
                            time.sleep(chunk)
                            elapsed += chunk
                else:
                    executor_instance.log(f"Task {task_id}{loop_display}: Unresolved variables in sleep time. Skipping sleep.")
            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid sleep time '{task['sleep']}'. Continuing.")

        # Check if this task has a return parameter (processed AFTER task execution)
        # This handles tasks that have both command AND return
        if 'return' in task and 'command' in task:
            try:
                return_code = int(task['return'])
                executor_instance.log(f"Task {task_id}{loop_display}: Returning with exit code {return_code}")
                executor_instance.final_exit_code = return_code
                executor_instance.final_success = (return_code == 0)  # Consider success if return code is 0

                # Add completion message before immediate exit
                if return_code == 0:
                    executor_instance.log("SUCCESS: Task execution completed successfully with return code 0")
                else:
                    executor_instance.log(f"FAILURE: Task execution failed with return code {return_code}")

                executor_instance.cleanup() # clean up resources before exit
                ExitHandler.exit_with_code(return_code, f"Task execution completed with return code {return_code}", False)
            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid return code '{task['return']}'. Exiting with code 1.")
                executor_instance.final_exit_code = 1  # Use 1 for invalid return codes
                executor_instance.final_success = False
                executor_instance.log("FAILURE: Task execution failed with invalid return code")
                executor_instance.cleanup() # clean up resources before exit
                ExitHandler.exit_with_code(ExitCodes.INVALID_ARGUMENTS, "Invalid return code specified", False)

        # Check the 'next' condition to determine if we should continue
        should_continue = executor_instance.check_next_condition(task, exit_code, stdout, stderr, success_result)

        # Update final exit code
        executor_instance.final_exit_code = exit_code

        # Determine if this task succeeded
        has_on_failure = 'on_failure' in task
        executor_instance.final_success = should_continue is True or (should_continue is False and has_on_failure)

        if should_continue == "NEVER":
            executor_instance.final_success = True;
            return None # Stop execution, do not check for on_failure

        if should_continue == "LOOP":
            return "LOOP" 
        
        # If we should continue and we have an 'on_success', jump to that task
        if should_continue and 'on_success' in task:
            try:
                on_success_task = int(task['on_success'])
                # Use main task ID (without loop display) if loop is completed
                display_id = task_id if task_id not in executor_instance.loop_iterations else f"{task_id}{loop_display}"
                executor_instance.log(f"Task {display_id}: Success condition met, jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid 'on_success' task '{task['on_success']}'. Continuing to next task.")
                return task_id + 1
        
        # If we shouldn't continue but we have an 'on_failure', jump to that task
        if not should_continue and 'on_failure' in task:
            try:
                on_failure_task = int(task['on_failure'])
                executor_instance.log(f"Task {task_id}{loop_display}: Success condition not met, jumping to Task {on_failure_task}")
                return on_failure_task
            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid 'on_failure' task '{task['on_failure']}'. Stopping.")
                return None

        # Return the next task ID or None to stop
        if should_continue:
            return task_id + 1
        else:
            return None

    def execute(self, task, **kwargs):
        """Execute a task using sequential execution."""
        executor_instance = kwargs.get('executor_instance')
        if not executor_instance:
            raise ValueError("executor_instance required for sequential execution")
        return SequentialExecutor.execute_task(task, executor_instance)