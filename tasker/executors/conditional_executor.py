# tasker/executors/conditional_executor.py
"""
Conditional Task Executor
-------------------------
Conditional task execution based on condition evaluation.
"""

import time
import threading
from .base_executor import BaseExecutor
from ..core.condition_evaluator import ConditionEvaluator
from ..utils.non_blocking_sleep import sleep_async


class ConditionalExecutor(BaseExecutor):
    """Conditional task executor for branch-based execution."""
    
    @staticmethod
    def execute_single_task_for_conditional(task, master_timeout=None, executor_instance=None):
        """Execute a single task as part of conditional execution (sequential)."""
        return executor_instance._execute_task_core(task, master_timeout, "conditional")

    @staticmethod
    def execute_single_task_for_conditional_with_retry_display(task, master_timeout=None, retry_display="", executor_instance=None):
        """Execute a single task as part of conditional execution with retry display support."""
        return executor_instance._execute_task_core(task, master_timeout, "conditional", retry_display)

    @staticmethod
    def execute_single_task_with_retry_conditional(task, master_timeout, retry_config, executor_instance=None):
        """Execute a single task with retry logic for conditional tasks."""
        from .parallel_executor import ParallelExecutor
        return ParallelExecutor._execute_single_task_with_retry_core(task, master_timeout, retry_config, "conditional", executor_instance)

    @staticmethod
    def check_conditional_next_condition(conditional_task, results, executor_instance):
        """Check next condition for conditional tasks - uses same logic as parallel tasks."""
        if 'next' not in conditional_task:
            return True  # Default to continue if no condition
        
        next_condition = conditional_task['next']
        
        # Use same evaluation logic as parallel tasks
        from .parallel_executor import ParallelExecutor
        return ParallelExecutor.evaluate_parallel_next_condition(next_condition, results, executor_instance.log_debug, executor_instance.log)

    @staticmethod
    def execute_conditional_tasks(conditional_task, executor_instance):
        """Execute conditional tasks based on condition evaluation - sequential execution."""
        task_id = int(conditional_task['task'])
        
        # Set current conditional task for child task logging
        executor_instance._current_conditional_task = task_id
        
        # Evaluate the condition
        condition = conditional_task.get('condition', '')
        if not condition:
            executor_instance.log(f"Task {task_id}: No condition specified, skipping conditional task")
            return task_id + 1
        
        # Evaluate condition using existing logic
        condition_result = ConditionEvaluator.evaluate_condition(condition, 0, "", "", executor_instance.global_vars, executor_instance.task_results, executor_instance.log_debug)
        branch = "TRUE" if condition_result else "FALSE"
        
        executor_instance.log_debug(f"Task {task_id}: Conditional condition '{condition}' evaluated to {branch}")
        
        # Determine which tasks to execute
        if condition_result and 'if_true_tasks' in conditional_task:
            tasks_str = conditional_task['if_true_tasks']
        elif not condition_result and 'if_false_tasks' in conditional_task:
            tasks_str = conditional_task['if_false_tasks']
        else:
            # CRITICAL: Missing branch is a fatal error - conditional blocks must have both branches
            executor_instance.log(f"ERROR: Task {task_id}: FATAL - Conditional block missing {branch} branch (if_{branch.lower()}_tasks). Both branches are mandatory.")
            executor_instance.log("ERROR: Conditional blocks must define both if_true_tasks and if_false_tasks to ensure deterministic workflow.")
            return None  # Fatal error - stop execution

        # Parse task references - empty branches are also fatal
        if not tasks_str.strip():
            # CRITICAL: Empty branch is a fatal error - defeats the purpose of conditional execution
            executor_instance.log(f"ERROR: Task {task_id}: FATAL - Empty task list for {branch} branch. Conditional blocks must have at least one task in each branch.")
            executor_instance.log("ERROR: Empty conditional branches create ambiguous workflow paths and are not permitted.")
            return None  # Fatal error - stop execution
        
        try:
            referenced_task_ids = []
            for task_ref in tasks_str.split(','):
                task_ref = task_ref.strip()
                if task_ref:
                    referenced_task_ids.append(int(task_ref))
        except ValueError as e:
            executor_instance.log(f"Task {task_id}: Invalid task reference in {branch} branch: {str(e)}")
            return None
        
        # Validate that all referenced tasks exist
        missing_tasks = []
        tasks_to_execute = []
        for ref_id in referenced_task_ids:
            if ref_id in executor_instance.tasks:
                tasks_to_execute.append(executor_instance.tasks[ref_id])
            else:
                missing_tasks.append(ref_id)
        
        if missing_tasks:
            executor_instance.log(f"Task {task_id}: Missing referenced tasks in {branch} branch: {missing_tasks}")
            return None
        
        # Get conditional execution parameters (similar to parallel)
        retry_config = executor_instance.parse_retry_config(conditional_task)

        # Log execution start
        retry_info = ""
        if retry_config:
            retry_info = f", retry_failed=true (count={retry_config['count']}, delay={retry_config['delay']}s)"

        executor_instance.log(f"Task {task_id}: Executing {branch} branch with {len(tasks_to_execute)} tasks (sequential{retry_info})")

        # Execute tasks sequentially in chosen branch
        results = []
        start_time = time.time()

        for task in tasks_to_execute:
            # Check for shutdown before each conditional task
            executor_instance._check_shutdown()

            # Execute task with retry logic if enabled
            # NOTE: Pass None for task_timeout to let each task use its own timeout
            if retry_config:
                result = ConditionalExecutor.execute_single_task_with_retry_conditional(task, None, retry_config, executor_instance=executor_instance)
            else:
                result = ConditionalExecutor.execute_single_task_for_conditional(task, None, executor_instance=executor_instance)

            results.append(result)

            # Handle sleep AFTER task completion (similar to parallel executor)
            sleep_seconds = result.get('sleep_seconds', 0)
            if sleep_seconds > 0 and not executor_instance.dry_run:
                task_display_id = f"{task_id}-{result['task_id']}"
                executor_instance.log(f"Task {task_display_id}: Sleeping for {sleep_seconds} seconds...")
                sleep_completion_event = threading.Event()

                # Bind loop variables to avoid capturing mutated state
                def sleep_callback(event=sleep_completion_event, display_id=task_display_id):
                    try:
                        executor_instance.log_debug(f"Task {display_id}: Sleep completed")
                    except Exception as e:
                        # Log the logging exception but don't let it prevent event signaling
                        try:
                            executor_instance.log(f"Task {display_id}: Sleep callback logging failed: {e}")
                        except Exception:
                            # Even fallback logging failed - just ignore to ensure event gets set
                            pass
                    finally:
                        # Always signal completion regardless of logging success/failure
                        event.set()

                sleep_async(
                    sleep_seconds,
                    sleep_callback,
                    task_id=f"{task_display_id}-sleep",
                    logger_callback=executor_instance.log_debug
                )

                # Wait with timeout to prevent indefinite blocking
                if not sleep_completion_event.wait(timeout=sleep_seconds + 5.0):
                    executor_instance.log_warn(f"Task {task_display_id}: Sleep timer did not complete within timeout, proceeding")

            # Store individual task results for future reference - THREAD SAFE
            executor_instance.store_task_result(result['task_id'], {
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

            executor_instance.log(f"Task {task_id}-{result['task_id']}: Completed - {success_text}")
            
            # For sequential execution, we could stop on first failure if needed
            # But for consistency with parallel tasks, we continue executing all tasks
        
        elapsed_time = time.time() - start_time
        executor_instance.log(f"Task {task_id}: Conditional execution completed in {elapsed_time:.2f} seconds")
        
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
        executor_instance.log_debug(f"Task {task_id}: Overall result - {success_text} ({successful_count}/{len(results)} tasks succeeded)")
        
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
        executor_instance.store_task_result(task_id, {
            'exit_code': aggregated_exit_code,
            'stdout': aggregated_stdout,
            'stderr': aggregated_stderr.strip(),
            'success': overall_success
        })
        
        # Update tracking for summary
        executor_instance.final_task_id = task_id
        executor_instance.final_hostname = "conditional"
        executor_instance.final_command = f"conditional {branch} branch execution of tasks {referenced_task_ids}"
        executor_instance.final_exit_code = aggregated_exit_code
        
        # Check if we have a success parameter for flexible routing
        if 'success' in conditional_task:
            # Evaluate success condition using the same logic as next conditions
            from .parallel_executor import ParallelExecutor
            success_condition = conditional_task['success']
            executor_instance.log_debug(f"Task {task_id}: Evaluating 'success' condition: {success_condition}")

            # Use the same evaluation function that handles min_success, max_failed, etc.
            # Note: This only returns True or False (never "NEVER" or "LOOP")
            should_continue = ParallelExecutor.evaluate_parallel_next_condition(
                success_condition, results, executor_instance.log_debug, executor_instance.log_info)

            executor_instance.log_info(f"Task {task_id}: Success condition '{success_condition}' evaluated to: {should_continue}")
        else:
            # Use conditional next condition evaluation (reuses parallel logic)
            # Note: This only returns True or False (check_conditional_next_condition doesn't return "NEVER"/"LOOP")
            should_continue = ConditionalExecutor.check_conditional_next_condition(conditional_task, results, executor_instance)

        # Handle on_success/on_failure jumps (same as parallel)
        # Note: should_continue is always True or False (never "NEVER" or "LOOP" in conditional blocks)
        has_on_failure = 'on_failure' in conditional_task
        executor_instance.final_success = should_continue is True or (should_continue is False and has_on_failure)
        
        if should_continue and 'on_success' in conditional_task:
            try:
                on_success_task = int(conditional_task['on_success'])
                executor_instance.log(f"Task {task_id}: Conditional success ({successful_count}/{len(results)}), jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                executor_instance.log(f"Task {task_id}: Invalid 'on_success' task. Continuing to next task.")
                return task_id + 1
        
        if not should_continue and 'on_failure' in conditional_task:
            try:
                on_failure_task = int(conditional_task['on_failure'])
                executor_instance.log(f"Task {task_id}: Conditional failure ({successful_count}/{len(results)}), jumping to Task {on_failure_task}")
                return on_failure_task
            except ValueError:
                executor_instance.log(f"Task {task_id}: Invalid 'on_failure' task. Stopping.")
                return None

        # If condition not met and no on_failure routing, this is a workflow failure
        if not should_continue:
            executor_instance._state_manager.workflow_failed_due_to_condition = True
            return None

        return task_id + 1

    def execute(self, task, **kwargs):
        """Execute a task using conditional execution."""
        executor_instance = kwargs.get('executor_instance')
        if not executor_instance:
            raise ValueError("executor_instance required for conditional execution")
        return ConditionalExecutor.execute_conditional_tasks(task, executor_instance)