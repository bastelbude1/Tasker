# tasker/executors/parallel_executor.py
"""
Parallel Task Executor
----------------------
Parallel task execution with threading, timeouts, and retry logic.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base_executor import BaseExecutor
from ..core.condition_evaluator import ConditionEvaluator


class ParallelExecutor(BaseExecutor):
    """Parallel task executor with threading and retry support."""
    
    @staticmethod
    def execute_single_task_for_parallel(task, master_timeout=None, retry_display="", executor_instance=None):
        """Execute a single task as part of parallel execution with enhanced retry display support."""
        return executor_instance._execute_task_core(task, master_timeout, "parallel", retry_display)


    @staticmethod
    def execute_single_task_with_retry(task, master_timeout, retry_config, executor_instance=None):
        """Execute a single task with retry logic and attempt numbering (.N notation)."""
        return ParallelExecutor._execute_single_task_with_retry_core(task, master_timeout, retry_config, "parallel", executor_instance)

    @staticmethod
    def _execute_single_task_with_retry_core(task, master_timeout, retry_config, context_type, executor_instance):
        """Unified retry logic for both parallel and conditional contexts."""
        task_id = int(task['task'])
    
        # Context-specific parent task ID and execution function
        if context_type == "parallel":
            parent_task_id = executor_instance._current_parallel_task
            execute_func = ParallelExecutor.execute_single_task_for_parallel
        else:  # conditional
            parent_task_id = executor_instance._current_conditional_task
            from .conditional_executor import ConditionalExecutor
            execute_func = ConditionalExecutor.execute_single_task_for_conditional_with_retry_display
    
        max_retries = retry_config.get('count', 0) if retry_config else 0
        retry_delay = retry_config.get('delay', 1) if retry_config else 1
    
        for attempt in range(max_retries + 1):
            # Retry display notation (only when retry is enabled)
            retry_display = f".{attempt + 1}" if retry_config else ""
        
            # Execute the task with context-specific function
            result = execute_func(task, master_timeout, retry_display, executor_instance=executor_instance)
            category = executor_instance.categorize_task_result(result)
        
            # Log attempt information with unique task ID
            if attempt == 0:
                executor_instance.log_debug(f"Task {parent_task_id}-{task_id}{retry_display}: Initial attempt - Result: {category}")
            else:
                executor_instance.log_debug(f"Task {parent_task_id}-{task_id}{retry_display}: Retry attempt {attempt} - Result: {category}")
        
            # Check if we should retry
            if category in ['SUCCESS', 'TIMEOUT']:
                # SUCCESS: Task completed successfully
                # TIMEOUT: Retry won't help - probably same result
                if attempt > 0:
                    if category == 'SUCCESS':
                        # SUCCESS after retry goes to NORMAL logging (not just debug)
                        executor_instance.log(f"Task {parent_task_id}-{task_id}{retry_display}: SUCCESS after {attempt} retry attempt(s)")
                    else:
                        executor_instance.log_debug(f"Task {parent_task_id}-{task_id}{retry_display}: TIMEOUT - no retry attempted")
                return result
            
            elif category == 'FAILED' and attempt < max_retries:
                # Real failure - retry makes sense
                next_attempt_display = f".{attempt + 2}" if retry_config else ""
                executor_instance.log(f"Task {parent_task_id}-{task_id}{retry_display}: FAILED - will retry as Task {parent_task_id}-{task_id}{next_attempt_display} in {retry_delay}s")
                if not executor_instance.dry_run:
                    time.sleep(retry_delay)
                continue
            
            else:
                # Max retries reached or other condition
                if attempt > 0:
                    executor_instance.log(f"Task {parent_task_id}-{task_id}{retry_display}: FAILED after {attempt} retry attempt(s) - giving up")
                return result
            
        # This should never be reached, but just in case
        return result

    @staticmethod
    def evaluate_parallel_next_condition(next_condition, results, debug_callback=None, log_callback=None):
        """Evaluate next condition specifically for parallel tasks."""
        if not results:
            if log_callback:
                log_callback(f"No results to evaluate for parallel next condition: '{next_condition}'")
            return False
            
        successful_tasks = [r for r in results if r['success']]
        failed_tasks = [r for r in results if not r['success']]
        total_tasks = len(results)
        success_count = len(successful_tasks)
        failed_count = len(failed_tasks)
        
        if debug_callback:
            debug_callback(f"Parallel condition evaluation: {success_count} successful, {failed_count} failed, total {total_tasks}")
        
        # Handle direct modifier conditions (min_success=N, max_failed=N, etc.)
        if '=' in next_condition:
            return ParallelExecutor.evaluate_direct_modifier_condition(next_condition, success_count, failed_count, total_tasks, debug_callback, log_callback)
        
        # Handle standard conditions
        if next_condition == 'always':
            if log_callback:
                log_callback(f"'next=always' found, proceeding to next task")
            return True
            
        if next_condition == 'all_success':
            result = success_count == total_tasks
            if debug_callback:
                debug_callback(f"all_success: {success_count} == {total_tasks} = {result}")
            return result
            
        elif next_condition == 'any_success':
            result = success_count > 0
            if debug_callback:
                debug_callback(f"any_success: {success_count} > 0 = {result}")
            return result
            
        elif next_condition == 'majority_success':
            majority_threshold = total_tasks / 2
            result = success_count > majority_threshold
            if debug_callback:
                debug_callback(f"majority_success: {success_count} > {majority_threshold} = {result}")
            return result
            
        else:
            if log_callback:
                log_callback(f"Unknown parallel next condition: '{next_condition}'")
            return False

    @staticmethod
    def evaluate_direct_modifier_condition(condition, success_count, failed_count, total_tasks, debug_callback=None, log_callback=None):
        """Evaluate direct modifier condition (min_success=N, max_failed=N, etc.)."""
        if '=' not in condition:
            if log_callback:
                log_callback(f"Invalid modifier condition format: '{condition}'")
            return False
            
        key, value = condition.split('=', 1)
        
        try:
            threshold = int(value)
        except ValueError:
            if log_callback:
                log_callback(f"Invalid modifier value: '{condition}'")
            return False
        
        if key == 'min_success':
            result = success_count >= threshold
            if debug_callback:
                debug_callback(f"min_success: {success_count} >= {threshold} = {result}")
            return result
            
        elif key == 'max_success':
            result = success_count <= threshold
            if debug_callback:
                debug_callback(f"max_success: {success_count} <= {threshold} = {result}")
            return result
            
        elif key == 'min_failed':
            result = failed_count >= threshold
            if debug_callback:
                debug_callback(f"min_failed: {failed_count} >= {threshold} = {result}")
            return result
            
        elif key == 'max_failed':
            result = failed_count <= threshold
            if debug_callback:
                debug_callback(f"max_failed: {failed_count} <= {threshold} = {result}")
            return result
            
        else:
            if log_callback:
                log_callback(f"Unknown modifier: '{key}' in condition '{condition}'")
            return False

    @staticmethod
    def execute_parallel_tasks(parallel_task, executor_instance):
        """Execute multiple tasks in parallel with ENHANCED RETRY LOGIC and IMPROVED LOGGING."""
        task_id = int(parallel_task['task'])
        
        # Set current parallel task for child task logging
        executor_instance._current_parallel_task = task_id
        
        # Parse task references
        tasks_str = parallel_task.get('tasks', '')
        if not tasks_str:
            executor_instance.log(f"Task {task_id}: No tasks specified")
            return task_id + 1
        
        # Get referenced task IDs and validate
        try:
            referenced_task_ids = []
            for task_ref in tasks_str.split(','):
                task_ref = task_ref.strip()
                if task_ref:
                    referenced_task_ids.append(int(task_ref))
        except ValueError as e:
            executor_instance.log(f"Task {task_id}: Invalid task reference: {str(e)}")
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
            executor_instance.log(f"Task {task_id}: Missing referenced tasks: {missing_tasks}")
            return None
        
        # Get parallel execution parameters
        max_parallel = int(parallel_task.get('max_parallel', len(tasks_to_execute)))
        
        # NEW: Parse retry configuration
        retry_config = executor_instance.parse_retry_config(parallel_task)
        
        # MASTER TIMEOUT ENFORCEMENT: One timeout rules them all
        master_timeout = executor_instance.get_task_timeout(parallel_task)
        
        # IMPROVED: Cleaner startup message with retry info
        retry_info = ""
        if retry_config:
            retry_info = f", retry_failed=true (count={retry_config['count']}, delay={retry_config['delay']}s)"
        
        executor_instance.log(f"Task {task_id}: Starting parallel execution of {len(tasks_to_execute)} tasks (max_parallel={max_parallel}, timeout={master_timeout}s{retry_info})")
        
        # Check for individual timeouts and warn about overrides (DEBUG ONLY)
        individual_timeout_count = 0
        for task in tasks_to_execute:
            if 'timeout' in task:
                individual_timeout_count += 1
        
        if individual_timeout_count > 0:
            executor_instance.log_debug(f"Task {task_id}: WARNING: {individual_timeout_count} sub-tasks have individual timeouts - MASTER timeout {master_timeout}s will override them")
        
        # Execute tasks in parallel with master timeout enforcement and retry logic
        results = []
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=max_parallel, thread_name_prefix=f"Task{task_id}") as thread_executor:
                # Submit tasks with or without retry based on config
                future_to_task = {}
                for task in tasks_to_execute:
                    # Check for shutdown before submitting each parallel task
                    if executor_instance._shutdown_requested:
                        executor_instance.log("Shutdown requested during parallel task submission")
                        thread_executor.shutdown(wait=False)
                        executor_instance._check_shutdown()

                    if retry_config:
                        # Mit retry config → .1, .2, etc.
                        future = thread_executor.submit(ParallelExecutor.execute_single_task_with_retry, task, master_timeout, retry_config, executor_instance=executor_instance)
                    else:
                        # Ohne retry config → keine Nummer
                        future = thread_executor.submit(ParallelExecutor.execute_single_task_for_parallel, task, master_timeout, "", executor_instance=executor_instance)
                    future_to_task[future] = task
                
                # Collect results with MASTER TIMEOUT enforcement
                try:
                    for future in as_completed(future_to_task, timeout=master_timeout):
                        task = future_to_task[future]
                        # Check for shutdown during result collection
                        if executor_instance._shutdown_requested:
                            # Cancel remaining tasks and exit gracefully
                            for f in future_to_task:
                                if not f.done():
                                    f.cancel()
                            executor_instance.log("Parallel execution interrupted by shutdown request")
                            executor_instance._check_shutdown()

                        try:
                            result = future.result()
                            
                            # Handle sleep AFTER task completion but BEFORE recording result
                            sleep_seconds = result.get('sleep_seconds', 0)
                            if sleep_seconds > 0:
                                task_display_id = f"{task_id}-{result['task_id']}"
                                executor_instance.log(f"Task {task_display_id}: Sleeping for {sleep_seconds} seconds...")
                                time.sleep(sleep_seconds)
                            
                            results.append(result)
                            
                            # IMPROVED: Simple completion message
                            success_text = "Success: True" if result['success'] else "Success: False"
                            if result['exit_code'] == 124:
                                success_text += " (timeout)"
                            elif result.get('skipped', False):
                                success_text += " (skipped)"
                            
                            executor_instance.log(f"Task {task_id}: Completed task {result['task_id']} - {success_text}")
                                
                        except Exception as e:
                            task_id_inner = int(task['task'])
                            executor_instance.log(f"Task {task_id}: [ERROR] Task {task_id_inner} exception: {str(e)}")
                            results.append({
                                'task_id': task_id_inner,
                                'exit_code': 1,
                                'stdout': '',
                                'stderr': f'Exception: {str(e)}',
                                'success': False,
                                'skipped': False
                            })
                            
                except Exception as timeout_exception:
                    # MASTER TIMEOUT REACHED - Graceful cancellation
                    elapsed = time.time() - start_time
                    executor_instance.log(f"Task {task_id}: MASTER TIMEOUT ({master_timeout}s) reached after {elapsed:.1f}s")
                    
                    # Cancel remaining futures and collect partial results
                    cancelled_count = 0
                    for future, task in future_to_task.items():
                        if not future.done():
                            future.cancel()
                            cancelled_count += 1
                            
                            # Create timeout result for cancelled tasks
                            task_id_inner = int(task['task'])
                            results.append({
                                'task_id': task_id_inner,
                                'exit_code': 124,  # Timeout exit code
                                'stdout': '',
                                'stderr': f'Task cancelled due to master timeout ({master_timeout}s)',
                                'success': False,
                                'skipped': False
                            })
                            
                    executor_instance.log(f"Task {task_id}: Cancelled {cancelled_count} remaining tasks due to master timeout")
                        
        except Exception as e:
            executor_instance.log(f"Task {task_id}: Parallel execution failed: {str(e)}")
            return None
        
        elapsed_time = time.time() - start_time
        executor_instance.log(f"Task {task_id}: Parallel execution completed in {elapsed_time:.2f} seconds")
        
        # Store individual task results for future reference - THREAD SAFE
        for result in results:
            executor_instance.store_task_result(result['task_id'], {
                'exit_code': result['exit_code'],
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'success': result['success']
            })
        
        # Calculate execution statistics with FIXED categorization
        successful_tasks = [r for r in results if r['success']]
        timeout_tasks = [r for r in results if r['exit_code'] == 124]
        failed_tasks = [r for r in results if not r['success'] and r['exit_code'] != 124]  # FIXED: Exclude timeouts from failures
        skipped_tasks = [r for r in results if r.get('skipped', False)]
        
        successful_count = len(successful_tasks)
        failed_count = len(failed_tasks)
        timeout_count = len(timeout_tasks)
        skipped_count = len(skipped_tasks)
        
        # Verify statistics add up correctly
        total_accounted = successful_count + failed_count + timeout_count + skipped_count
        if total_accounted != len(results):
            executor_instance.log_debug(f"Task {task_id}: WARNING: Statistics mismatch - {total_accounted} accounted vs {len(results)} total")
        
        # IMPROVED: Overall success determination and logging
        overall_success = successful_count == len(results)
        success_text = "Success: True" if overall_success else "Success: False"
        executor_instance.log_debug(f"Task {task_id}: Overall result - {success_text} ({successful_count}/{len(results)} tasks succeeded)")
        
        # NEW: Enhanced retry statistics logging
        if retry_config:
            retry_eligible_tasks = [r for r in results if not r['success'] and r['exit_code'] != 124]
            successful_after_potential_retry = [r for r in results if r['success']]
            
            if len(retry_eligible_tasks) > 0 or len(successful_after_potential_retry) > 0:
                executor_instance.log_debug(f"Task {task_id}: RETRY SUMMARY - Retry enabled with {retry_config['count']} max attempts, {retry_config['delay']}s delay")
                
                if len(successful_after_potential_retry) > 0:
                    executor_instance.log_debug(f"Task {task_id}: RETRY SUCCESS - {len(successful_after_potential_retry)} task(s) completed successfully (some may have used retries)")
                
                if len(retry_eligible_tasks) > 0:
                    failed_task_ids = [r['task_id'] for r in retry_eligible_tasks]
                    executor_instance.log_debug(f"Task {task_id}: RETRY EXHAUSTED - Tasks {failed_task_ids} failed after all retry attempts")
        
        # Move detailed statistics to debug mode only
        if not overall_success:
            if timeout_count > 0:
                timeout_task_ids = [r['task_id'] for r in timeout_tasks]
                executor_instance.log_debug(f"Task {task_id}: TIMEOUT DETAILS - Tasks {timeout_task_ids} exceeded master timeout of {master_timeout}s")
            
            if failed_count > 0:
                failed_task_ids = [r['task_id'] for r in failed_tasks]
                executor_instance.log_debug(f"Task {task_id}: FAILURE DETAILS - Tasks {failed_task_ids} failed (non-timeout)")
        
        # Create aggregated output with enhanced information
        aggregated_stdout = f"Parallel execution: {successful_count}/{len(results)} successful"
        if timeout_count > 0:
            aggregated_stdout += f", {timeout_count} timeout"
        if failed_count > 0:
            aggregated_stdout += f", {failed_count} failed"
        
        aggregated_stderr = ""
        
        # Separate error reporting
        if failed_count > 0:
            failed_task_ids = [r['task_id'] for r in failed_tasks]
            aggregated_stderr += f"Failed tasks: {failed_task_ids}. "
        
        if timeout_count > 0:
            timeout_task_ids = [r['task_id'] for r in timeout_tasks]
            aggregated_stderr += f"Timeout tasks: {timeout_task_ids}"
        
        aggregated_exit_code = 0 if overall_success else 1
        
        # Store the parallel task result - THREAD SAFE
        executor_instance.store_task_result(task_id, {
            'exit_code': aggregated_exit_code,
            'stdout': aggregated_stdout,
            'stderr': aggregated_stderr.strip(),
            'success': overall_success
        })
        
        # Update tracking for summary
        executor_instance.final_task_id = task_id
        executor_instance.final_hostname = "parallel"
        executor_instance.final_command = f"parallel execution of tasks {referenced_task_ids}"
        executor_instance.final_exit_code = aggregated_exit_code
        
        # Use enhanced parallel next condition evaluation
        should_continue = executor_instance.check_parallel_next_condition(parallel_task, results)
        
        # Determine final success based on should_continue result
        if should_continue == "NEVER":
            executor_instance.final_success = True
            return None

        if should_continue == "LOOP":
            return "LOOP" 
        
        # Handle on_success/on_failure jumps
        has_on_failure = 'on_failure' in parallel_task
        executor_instance.final_success = should_continue is True or (should_continue is False and has_on_failure)
        
        if should_continue and 'on_success' in parallel_task:
            try:
                on_success_task = int(parallel_task['on_success'])
                executor_instance.log(f"Task {task_id}: Parallel success ({successful_count}/{len(results)}), jumping to Task {on_success_task}")
                return on_success_task
            except ValueError:
                executor_instance.log(f"Task {task_id}: Invalid 'on_success' task. Continuing to next task.")
                return task_id + 1
        
        if not should_continue and 'on_failure' in parallel_task:
            try:
                on_failure_task = int(parallel_task['on_failure'])
                executor_instance.log(f"Task {task_id}: Parallel failure ({successful_count}/{len(results)}), jumping to Task {on_failure_task}")
                return on_failure_task
            except ValueError:
                executor_instance.log(f"Task {task_id}: Invalid 'on_failure' task. Stopping.")
                return None

        return task_id + 1 if should_continue else None

    def execute(self, task, **kwargs):
        """Execute a task using parallel execution."""
        executor_instance = kwargs.get('executor_instance')
        if not executor_instance:
            raise ValueError("executor_instance required for parallel execution")
        return ParallelExecutor.execute_parallel_tasks(task, executor_instance)