# tasker/executors/base_executor.py
"""
Base Executor for Task Execution
---------------------------------
Abstract base class for all task execution engines with common functionality.
"""

import time
import subprocess
from abc import ABC, abstractmethod
from ..core.utilities import format_output_for_log
from ..core.condition_evaluator import ConditionEvaluator
from ..core.execution_context import ExecutionContext
from ..core.streaming_output_handler import StreamingOutputHandler, create_memory_efficient_handler


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
            
            # Format STDOUT for clean logging
            formatted_stdout = format_output_for_log(stdout, max_length=200, label="STDOUT")
            if formatted_stdout:
                log_callback(f"Task {task_display_id}: STDOUT: {formatted_stdout}")
            
            # Format STDERR for clean logging
            formatted_stderr = format_output_for_log(stderr, max_length=200, label="STDERR") 
            if formatted_stderr:
                log_callback(f"Task {task_display_id}: STDERR: {formatted_stderr}")
    
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
    def execute_task_core(task, execution_context, master_timeout=None, context="normal", retry_display=""):
        """
        Unified task execution core using ExecutionContext.
        Simplified interface that replaces the old callback-heavy method.
        """
        task_id = int(task['task'])
        task_display_id = BaseExecutor._get_task_display_id(
            task_id, context, retry_display, 
            execution_context._current_parallel_task, 
            execution_context._current_conditional_task
        )
        
        try:
            # 1. Pre-execution condition check
            if 'condition' in task:
                condition_result = ConditionEvaluator.evaluate_condition(
                    task['condition'], 0, "", "", 
                    execution_context.global_vars, 
                    execution_context.task_results, 
                    execution_context.log_debug
                )
                if not condition_result:
                    execution_context.log(f"Task {task_display_id}: Condition '{task['condition']}' evaluated to FALSE, skipping task")
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
                execution_context.log(f"Task {task_display_id}: Return task with exit code {return_code}")
                return {
                    'task_id': task_id,
                    'exit_code': return_code,
                    'stdout': '',
                    'stderr': f'Return task: {return_code}',
                    'success': (return_code == 0),
                    'skipped': False
                }
            
            # 3. Variable replacement
            hostname, _ = ConditionEvaluator.replace_variables(task.get('hostname', ''), execution_context.global_vars, execution_context.task_results, execution_context.log_debug)
            command, _ = ConditionEvaluator.replace_variables(task.get('command', ''), execution_context.global_vars, execution_context.task_results, execution_context.log_debug)
            arguments, _ = ConditionEvaluator.replace_variables(task.get('arguments', ''), execution_context.global_vars, execution_context.task_results, execution_context.log_debug)

            # 4. Execution type and command building
            exec_type = execution_context.determine_execution_type(task, task_display_id)
            cmd_array = execution_context.build_command_array(exec_type, hostname, command, arguments)
            full_command_display = ' '.join(cmd_array)

            # 5. Timeout handling
            if master_timeout is not None:
                task_timeout = master_timeout
                if 'timeout' in task:
                    execution_context.log_debug(f"Task {task_display_id}: Task-specific timeout ({task['timeout']}s) overridden by master timeout ({master_timeout}s)")
            else:
                task_timeout = execution_context.get_task_timeout(task)

            # 6. Log execution details
            execution_context.log(f"Task {task_display_id}: Executing [{exec_type}]: {full_command_display}")

            # 7. Execute or dry run
            if execution_context.dry_run:
                execution_context.log(f"Task {task_display_id}: DRY RUN - Command would be executed")
                return {
                    'task_id': task_id,
                    'exit_code': 0,
                    'stdout': 'DRY RUN - Command not executed',
                    'stderr': '',
                    'success': True,
                    'skipped': False,
                    'sleep_seconds': int(task.get('sleep', 0))
                }

            # 8. Real execution with memory-efficient streaming
            start_time = time.time()
            try:
                # Create memory-efficient output handler
                # Configure based on task or system defaults (10MB memory limit)
                max_memory_mb = int(task.get('max_output_memory_mb', 10))

                with create_memory_efficient_handler(max_memory_mb) as output_handler:
                    # Use Popen pattern for Python 3.6.8 compatibility
                    with subprocess.Popen(
                        cmd_array,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    ) as process:
                        # Stream output with memory efficiency
                        raw_stdout, raw_stderr, exit_code, timed_out = output_handler.stream_process_output(
                            process, timeout=task_timeout
                        )
                        execution_time = time.time() - start_time

                        # Log memory usage information for debugging
                        memory_info = output_handler.get_memory_usage_info()
                        if memory_info['using_temp_files']:
                            execution_context.log_debug(f"Task {task_display_id}: Used temp files for large output "
                                                      f"(stdout: {memory_info['stdout_size']} bytes, "
                                                      f"stderr: {memory_info['stderr_size']} bytes)")

                        if timed_out:
                            execution_context.log(f"Task {task_display_id}: TIMEOUT after {task_timeout}s")
                            return {
                                'task_id': task_id,
                                'exit_code': 124,
                                'stdout': '',
                                'stderr': f'Command timed out after {task_timeout} seconds',
                                'success': False,
                                'skipped': False,
                                'sleep_seconds': int(task.get('sleep', 0))
                            }

            except Exception as e:
                execution_time = time.time() - start_time
                execution_context.log(f"Task {task_display_id}: Execution error: {str(e)}")
                return {
                    'task_id': task_id,
                    'exit_code': 1,
                    'stdout': '',
                    'stderr': str(e),
                    'success': False,
                    'skipped': False,
                    'sleep_seconds': int(task.get('sleep', 0))
                }

            # 9. Handle output splitting if configured
            processed_stdout, processed_stderr = BaseExecutor._handle_output_splitting(task, task_display_id, raw_stdout, raw_stderr, execution_context.log_debug)

            # 10. Log results
            BaseExecutor._log_task_result(task_display_id, exit_code, processed_stdout, processed_stderr, execution_context.log)

            # 11. Success condition evaluation
            success_condition = task.get('success', 'exit_0')
            success = ConditionEvaluator.evaluate_condition(success_condition, exit_code, processed_stdout, processed_stderr, execution_context.global_vars, execution_context.task_results, execution_context.log_debug)
            execution_context.log(f"Task {task_display_id}: Success condition '{success_condition}' evaluated to: {success}")

            return {
                'task_id': task_id,
                'exit_code': exit_code,
                'stdout': processed_stdout,
                'stderr': processed_stderr,
                'success': success,
                'skipped': False,
                'sleep_seconds': int(task.get('sleep', 0))
            }

        except Exception as e:
            execution_context.log_error(f"Task {task_display_id}: Unexpected error during execution: {str(e)}")
            return {
                'task_id': task_id,
                'exit_code': 255,
                'stdout': '',
                'stderr': f'Execution error: {str(e)}',
                'success': False,
                'skipped': False,
                'sleep_seconds': 0
            }

    @abstractmethod
    def execute(self, task, **kwargs):
        """Execute a task - must be implemented by subclasses."""
        pass