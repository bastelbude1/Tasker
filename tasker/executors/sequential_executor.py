# tasker/executors/sequential_executor.py
"""
Sequential Task Executor
------------------------
Normal sequential task execution with flow control.
"""

import time
from .base_executor import BaseExecutor
from ..core.condition_evaluator import ConditionEvaluator
from ..core.utilities import ExitHandler, ExitCodes, format_output_for_log


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

        # Get loop iteration display if looping
        loop_display = ""
        if task_id in executor_instance.loop_iterations:
            loop_display = f".{executor_instance.loop_iterations[task_id]}"

        # Check for shutdown before task execution
        executor_instance._check_shutdown()

        # Check pre-execution condition
        if 'condition' in task:
            condition_result = ConditionEvaluator.evaluate_condition(task['condition'], 0, "", "", executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
            if not condition_result:
                executor_instance.log(f"Task {task_id}{loop_display}: Condition '{task['condition']}' evaluated to FALSE, skipping task")
                # CRITICAL: Store results for skipped task - THREAD SAFE
                executor_instance.store_task_result(task_id, {
                    'exit_code': -1,     # Special: Task was skipped
                    'stdout': '',
                    'stderr': 'Task skipped due to condition',
                    'success': False
                })
                return task_id + 1  # Continue to next task
            else:
                executor_instance.log(f"Task {task_id}{loop_display}: Condition '{task['condition']}' evaluated to TRUE, executing task")

        # Update tracking for summary
        executor_instance.final_task_id = task_id
        executor_instance.final_hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', 'N/A'), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
        executor_instance.final_command, _ = ConditionEvaluator.replace_variables(task.get('command', 'N/A'), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
        
        # Check if this is a return task
        if 'return' in task:
            if executor_instance.final_command == 'N/A': executor_instance.final_command = 'return'
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
                executor_instance.final_exit_code = 1  # Use 1 for invalid return codes (this is correct)
                executor_instance.final_success = False
                executor_instance.log("FAILURE: Task execution failed with invalid return code")
                executor_instance.cleanup() # clean up resources before exit
                ExitHandler.exit_with_code(ExitCodes.INVALID_ARGUMENTS, "Invalid return code specified", False)
        
        # Replace variables in command and arguments
        hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', ''), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
        command, _ = ConditionEvaluator.replace_variables(task.get('command', ''), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
        arguments, _ = ConditionEvaluator.replace_variables(task.get('arguments', ''), executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)

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
        if executor_instance.dry_run:
            executor_instance.log(f"Task {task_id}{loop_display}: [DRY RUN] Would execute: {full_command_display}")
            exit_code = 0
            stdout = "DRY RUN STDOUT"
            stderr = ""
        else:
            executor_instance.log(f"Task {task_id}{loop_display}: Executing [{exec_type}]: {full_command_display}")
            try:
                # Execute using contect manager for automatic cleanup
                import subprocess
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
                        executor_instance.log(f"Task {task_id}{loop_display}: Timeout after {task_timeout} seconds. Killing process.")
                        process.kill()
                        stdout, stderr = process.communicate()
                        exit_code = 124  # Common exit code for timeout
                        stderr += f"\nProcess killed after timeout of {task_timeout} seconds"
            except Exception as e:
                executor_instance.log(f"Task {task_id}{loop_display}: Error executing command: {str(e)}")
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
            executor_instance.log(f"Task {task_id}{loop_display}: Split STDOUT: '{stdout_stripped}' -> '{stdout}'")
            
        if 'stderr_split' in task:
            original_stderr = stderr
            stderr = ConditionEvaluator.split_output(stderr, task['stderr_split'])
            executor_instance.log(f"Task {task_id}{loop_display}: Split STDERR: '{stderr_stripped}' -> '{stderr}'")
        
        # Evaluate success condition if defined, otherwise default to exit_code == 0
        if 'success' in task:
            success_result = ConditionEvaluator.evaluate_condition(task['success'], exit_code, stdout, stderr, executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
            executor_instance.log(f"Task {task_id}{loop_display}: Success condition '{task['success']}' evaluated to: {success_result}")
        else:
            success_result = (exit_code == 0)
            executor_instance.log_debug(f"Task {task_id}{loop_display}: Success (default): {success_result}")
        
        # CRITICAL: Store the results for future reference - THREAD SAFE
        executor_instance.store_task_result(task_id, {
            'exit_code': exit_code,
            'stdout': stdout,
            'stderr': stderr,
            'success': success_result
        })
        
        # Check if we should sleep before the next task
        if 'sleep' in task:
            try:
                sleep_time_str, resolved = ConditionEvaluator.replace_variables(task['sleep'], executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
                if resolved:
                    sleep_time = float(sleep_time_str)
                    executor_instance.log(f"Task {task_id}{loop_display}: Sleeping for {sleep_time} seconds")
                    if not executor_instance.dry_run:
                        time.sleep(sleep_time)
                else:
                    executor_instance.log(f"Task {task_id}{loop_display}: Unresolved variables in sleep time. Skipping sleep.")
            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid sleep time '{task['sleep']}'. Continuing.")
        
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
                executor_instance.log(f"Task {task_id}{loop_display}: 'next' condition succeeded, jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                executor_instance.log(f"Task {task_id}{loop_display}: Invalid 'on_success' task '{task['on_success']}'. Continuing to next task.")
                return task_id + 1
        
        # If we shouldn't continue but we have an 'on_failure', jump to that task
        if not should_continue and 'on_failure' in task:
            try:
                on_failure_task = int(task['on_failure'])
                executor_instance.log(f"Task {task_id}{loop_display}: 'next' condition failed, jumping to Task {on_failure_task}")
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