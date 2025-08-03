# tasker/executors/base_executor.py
"""
Base Executor for Task Execution
---------------------------------
Abstract base class for all task execution engines with common functionality.
"""

import subprocess
from abc import ABC, abstractmethod
from ..core.condition_evaluator import ConditionEvaluator


class BaseExecutor(ABC):
    """Abstract base class for all task executors."""
    
    @staticmethod
    def _get_task_display_id(task_id, context_type, retry_display="", current_parallel_task=None, current_conditional_task=None):
        """Get consistent task display ID for different execution contexts."""
        if context_type == "parallel" and current_parallel_task is not None:
            return f"{current_parallel_task}-{task_id}{retry_display}"
        elif context_type == "conditional" and current_conditional_task is not None:
            return f"{current_conditional_task}-{task_id}{retry_display}"
        else:
            return f"{task_id}{retry_display}"
    
    @staticmethod
    def _log_task_result(task_display_id, exit_code, stdout, stderr, log_callback=None):
        """Log task execution results consistently."""
        if log_callback:
            log_callback(f"Task {task_display_id}: Exit code: {exit_code}")
            log_callback(f"Task {task_display_id}: STDOUT: {stdout}")
            log_callback(f"Task {task_display_id}: STDERR: {stderr}")
    
    @staticmethod
    def _handle_output_splitting(task, task_display_id, stdout, stderr, debug_callback=None):
        """Handle output splitting operations and return processed stdout/stderr."""
        # Check if this task uses output splitting operations
        stdout_operations = []
        stderr_operations = []
        
        # Check for split operations in task attributes
        for key, value in task.items():
            if key.startswith('stdout_split'):
                stdout_operations.append((key, value))
            elif key.startswith('stderr_split'):
                stderr_operations.append((key, value))
        
        # Process stdout operations
        modified_stdout = stdout
        for op_key, op_value in stdout_operations:
            try:
                # Expected format: "delimiter,index" (0-based indexing)
                parts = op_value.split(',')
                if len(parts) == 2:
                    delimiter = parts[0]
                    index = int(parts[1])
                    
                    split_result = stdout.split(delimiter)
                    if 0 <= index < len(split_result):
                        modified_stdout = split_result[index]
                        if debug_callback:
                            debug_callback(f"Task {task_display_id}: Applied {op_key}='{delimiter},{index}': '{stdout}' -> '{modified_stdout}'")
                    else:
                        if debug_callback:
                            debug_callback(f"Task {task_display_id}: {op_key} index {index} out of range for split result (length: {len(split_result)})")
                        
            except (ValueError, IndexError) as e:
                if debug_callback:
                    debug_callback(f"Task {task_display_id}: Error in {op_key}: {str(e)}")
        
        # Process stderr operations
        modified_stderr = stderr
        for op_key, op_value in stderr_operations:
            try:
                # Expected format: "delimiter,index" (0-based indexing)
                parts = op_value.split(',')
                if len(parts) == 2:
                    delimiter = parts[0]
                    index = int(parts[1])
                    
                    split_result = stderr.split(delimiter)
                    if 0 <= index < len(split_result):
                        modified_stderr = split_result[index]
                        if debug_callback:
                            debug_callback(f"Task {task_display_id}: Applied {op_key}='{delimiter},{index}': '{stderr}' -> '{modified_stderr}'")
                    else:
                        if debug_callback:
                            debug_callback(f"Task {task_display_id}: {op_key} index {index} out of range for split result (length: {len(split_result)})")
                        
            except (ValueError, IndexError) as e:
                if debug_callback:
                    debug_callback(f"Task {task_display_id}: Error in {op_key}: {str(e)}")
        
        return modified_stdout, modified_stderr
    
    @staticmethod
    def execute_task_core(task, global_vars, task_results, determine_execution_type_callback, 
                         build_command_array_callback, get_task_timeout_callback, dry_run=False,
                         master_timeout=None, context="normal", retry_display="", 
                         current_parallel_task=None, current_conditional_task=None,
                         debug_callback=None, log_callback=None):
        """Unified task execution core for parallel, conditional, and normal execution."""
        task_id = int(task['task'])
        task_display_id = BaseExecutor._get_task_display_id(task_id, context, retry_display, current_parallel_task, current_conditional_task)
        
        try:
            # 1. Pre-execution condition check
            if 'condition' in task:
                condition_result = ConditionEvaluator.evaluate_condition(task['condition'], 0, "", "", global_vars, task_results, debug_callback)
                if not condition_result:
                    if log_callback:
                        log_callback(f"Task {task_display_id}: Condition '{task['condition']}' evaluated to FALSE, skipping task")
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
                if log_callback:
                    log_callback(f"Task {task_display_id}: Return task with exit code {return_code}")
                return {
                    'task_id': task_id,
                    'exit_code': return_code,
                    'stdout': '',
                    'stderr': f'Return task: {return_code}',
                    'success': (return_code == 0),
                    'skipped': False
                }
            
            # 3. Variable replacement
            hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', ''), global_vars, task_results, debug_callback)
            command, _ = ConditionEvaluator.replace_variables(task.get('command', ''), global_vars, task_results, debug_callback)
            arguments, _ = ConditionEvaluator.replace_variables(task.get('arguments', ''), global_vars, task_results, debug_callback)

            # 4. Execution type and command building
            exec_type = determine_execution_type_callback(task, task_display_id)
            cmd_array = build_command_array_callback(exec_type, hostname, command, arguments)
            full_command_display = ' '.join(cmd_array)

            # 5. Timeout handling
            if master_timeout is not None:
                task_timeout = master_timeout
                if 'timeout' in task:
                    individual_timeout_str, _ = ConditionEvaluator.replace_variables(task['timeout'], global_vars, task_results, debug_callback)
                    try:
                        individual_timeout = int(individual_timeout_str)
                        if individual_timeout != master_timeout:
                            if debug_callback:
                                debug_callback(f"Task {task_display_id}: OVERRIDING individual timeout {individual_timeout}s with MASTER timeout {master_timeout}s")
                    except ValueError:
                        pass
                else:
                    if debug_callback:
                        debug_callback(f"Task {task_display_id}: Using MASTER timeout {master_timeout}s")
            else:
                task_timeout = get_task_timeout_callback(task)
                if debug_callback:
                    debug_callback(f"Task {task_display_id}: Using individual timeout {task_timeout}s")

            # 6. Command execution
            if dry_run:
                if log_callback:
                    log_callback(f"Task {task_display_id}: [DRY RUN] Would execute: {full_command_display}")
                exit_code = 0
                stdout = f"DRY RUN STDOUT - Task {task_id}"
                stderr = ""
            else:
                if log_callback:
                    log_callback(f"Task {task_display_id}: Executing [{exec_type}]: {full_command_display}")
                
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
                            if log_callback:
                                log_callback(f"Task {task_display_id}: TIMEOUT after {task_timeout}s - killing process")
                            process.kill()
                            stdout, stderr = process.communicate()
                            exit_code = 124  # Standard timeout exit code
                            stderr += f"\nProcess killed after timeout of {task_timeout}s"
                            
                except Exception as e:
                    if log_callback:
                        log_callback(f"Task {task_display_id}: Error executing command: {str(e)}")
                    exit_code = 1
                    stdout = ""
                    stderr = str(e)
            
            # 7. Result logging and processing
            BaseExecutor._log_task_result(task_display_id, exit_code, stdout, stderr, log_callback)
            stdout, stderr = BaseExecutor._handle_output_splitting(task, task_display_id, stdout, stderr, debug_callback)
            
            # 8. Success evaluation
            if 'success' in task:
                success_condition = task['success']
                success_result = ConditionEvaluator.evaluate_condition(success_condition, exit_code, stdout, stderr, global_vars, task_results, debug_callback)
                if log_callback:
                    log_callback(f"Task {task_display_id}: Success condition '{success_condition}' evaluated to: {success_result}")
            else:
                # Default success: exit code 0
                success_result = (exit_code == 0)
            
            # 9. Sleep information (don't execute here - return for caller to handle)
            sleep_seconds = 0
            if 'sleep' in task:
                sleep_str, _ = ConditionEvaluator.replace_variables(task['sleep'], global_vars, task_results, debug_callback)
                try:
                    sleep_seconds = int(sleep_str)
                except ValueError:
                    if debug_callback:
                        debug_callback(f"Task {task_display_id}: Invalid sleep value: {sleep_str}")
                    sleep_seconds = 0
            
            return {
                'task_id': task_id,
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'success': success_result,
                'skipped': False,
                'sleep_seconds': sleep_seconds
            }
            
        except Exception as e:
            if log_callback:
                log_callback(f"Task {task_display_id}: Unexpected error: {str(e)}")
            return {
                'task_id': task_id,
                'exit_code': 1,
                'stdout': '',
                'stderr': f'Unexpected error: {str(e)}',
                'success': False,
                'skipped': False,
                'sleep_seconds': 0
            }

    @abstractmethod
    def execute(self, task, **kwargs):
        """Execute a task - must be implemented by subclasses."""
        pass