# tasker/executors/parallel_executor.py
"""
Parallel Task Executor
----------------------
Parallel task execution with threading, timeouts, and retry logic.
"""

import os
import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base_executor import BaseExecutor
from ..core.condition_evaluator import ConditionEvaluator
from ..utils.non_blocking_sleep import sleep_async, get_sleep_manager


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
                if not executor_instance.dry_run and retry_delay > 0:
                    # Use non-blocking sleep for retry delay
                    retry_completed_event = threading.Event()

                    def retry_callback():
                        retry_completed_event.set()

                    retry_timer = sleep_async(
                        retry_delay,
                        retry_callback,
                        task_id=f"{parent_task_id}-{task_id}-retry-{attempt}",
                        logger_callback=executor_instance.log_debug
                    )

                    # Wait for retry delay with timeout to prevent infinite blocking
                    timeout_buffer = retry_delay + 5  # Add 5 second buffer for safety (matches Phase 2 sleep buffer)
                    if retry_completed_event.wait(timeout=timeout_buffer):
                        # Event was set - normal completion
                        executor_instance.log_debug(f"Task {parent_task_id}-{task_id}{retry_display}: Retry delay completed normally")
                    else:
                        # Timeout occurred - sleep_async callback never fired
                        executor_instance.log_warn(f"Task {parent_task_id}-{task_id}{retry_display}: Retry delay timer misfired (timeout after {timeout_buffer}s), continuing with retry attempt {attempt + 1}")
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
        """Evaluate next condition specifically for parallel tasks.

        Used in success-context (success parameter evaluation).
        Returns: bool (True/False only, never sentinel strings like "NEVER" or "LOOP")

        Note: check_parallel_next_condition() in TaskExecutor can return sentinel strings
        like "NEVER" or "LOOP" because it's used in next-context where special control
        flow is supported. This function only returns boolean for simpler success evaluation.
        """
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

        if next_condition == 'never':
            if log_callback:
                log_callback("'next=never' found, not proceeding to next task")
            # Return False (not "NEVER" string) because this function is used in success-context
            # where boolean True/False is expected. check_parallel_next_condition returns "NEVER"
            # string for next-context where special sentinel values are supported.
            return False

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
        # DEFAULT: 8 threads - safe for any system, user must explicitly override for higher values
        # This ensures users read documentation about risks before using high parallelism
        DEFAULT_MAX_PARALLEL = 8
        max_parallel = int(parallel_task.get('max_parallel', DEFAULT_MAX_PARALLEL))

        # Inform user about high parallelism only if TASKER_PARALLEL_INSTANCES is not set
        # If they set the env var, they're already aware of the implications
        parallel_instances_set = 'TASKER_PARALLEL_INSTANCES' in os.environ
        if max_parallel > 32 and not parallel_instances_set and executor_instance:
            executor_instance.log(f"Task {task_id}: INFO: High parallelism requested (max_parallel={max_parallel}). "
                                f"Consider setting TASKER_PARALLEL_INSTANCES if running multiple TASKER instances. See README.md for details.")
        
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

        # Cap thread pool size to prevent resource exhaustion
        # CRITICAL: Check for nested parallelism (multiple TASKER instances)
        cpu_count = multiprocessing.cpu_count()

        # Check if we're running in a nested/parallel context
        # This could be set by orchestration scripts or CI/CD systems
        try:
            parallel_instances = int(os.environ.get('TASKER_PARALLEL_INSTANCES', '1'))
        except (ValueError, TypeError):
            parallel_instances = 1
            if executor_instance:
                executor_instance.log_debug(f"Task {task_id}: Invalid TASKER_PARALLEL_INSTANCES value, defaulting to 1")

        # Sanitize to prevent division by zero and negative values
        if parallel_instances <= 0:
            if executor_instance:
                executor_instance.log_debug(f"Task {task_id}: TASKER_PARALLEL_INSTANCES was {parallel_instances}, correcting to 1")
            parallel_instances = 1

        # Clamp to reasonable maximum to prevent over-division
        parallel_instances = min(parallel_instances, 1000)

        try:
            nested_level = int(os.environ.get('TASKER_NESTED_LEVEL', '0'))
        except (ValueError, TypeError):
            nested_level = 0
            if executor_instance:
                executor_instance.log_debug(f"Task {task_id}: Invalid TASKER_NESTED_LEVEL value, defaulting to 0")

        # Sanitize nested level
        nested_level = max(0, nested_level)

        # Detect if multiple TASKER processes are running (heuristic)
        # This is a safeguard when TASKER_PARALLEL_INSTANCES isn't set
        if parallel_instances == 1 and nested_level == 0:
            # Try to detect parallel execution by checking for instance ID in environment
            if 'PARALLEL_INSTANCE_ID' in os.environ or 'CI_NODE_INDEX' in os.environ:
                parallel_instances = 10  # Assume reasonable number of parallel instances
                executor_instance.log_debug(f"Task {task_id}: Detected parallel execution environment, assuming {parallel_instances} instances")

        # Adjust limits based on parallel execution context
        if parallel_instances > 1 or nested_level > 0:
            # CONSERVATIVE limits for nested/parallel execution
            # parallel_instances is guaranteed to be >= 1 at this point due to sanitization
            if cpu_count <= 4:
                absolute_max = max(10, 50 // parallel_instances)  # Safe: parallel_instances >= 1
            elif cpu_count <= 8:
                absolute_max = max(15, 75 // parallel_instances)  # Safe: parallel_instances >= 1
            else:
                absolute_max = max(20, 100 // parallel_instances)  # Safe: parallel_instances >= 1

            recommended_max = max(cpu_count, cpu_count * 2 // parallel_instances)  # Safe: parallel_instances >= 1

            if executor_instance:
                executor_instance.log_debug(f"Task {task_id}: Nested/parallel execution detected (instances={parallel_instances}, level={nested_level})")
        else:
            # NORMAL limits for single instance execution
            if cpu_count <= 4:
                absolute_max = 50
            elif cpu_count <= 8:
                absolute_max = 75
            else:
                absolute_max = 100

            recommended_max = cpu_count * 4  # More reasonable for I/O-bound tasks

        # Apply progressive capping
        capped_max_workers = min(max_parallel, recommended_max, absolute_max)

        if capped_max_workers < max_parallel:
            details = f"CPU cores: {cpu_count}, recommended: {recommended_max}, absolute max: {absolute_max}"
            if parallel_instances > 1:
                details += f", parallel instances: {parallel_instances}"
            executor_instance.log_debug(f"Task {task_id}: Capping thread pool from {max_parallel} to {capped_max_workers} ({details})")

        try:
            with ThreadPoolExecutor(max_workers=capped_max_workers, thread_name_prefix=f"Task{task_id}") as thread_executor:
                # Submit tasks with or without retry based on config
                future_to_task = {}
                for task in tasks_to_execute:
                    # Check for shutdown before submitting each parallel task
                    if executor_instance._shutdown_requested:
                        executor_instance.log("Shutdown requested during parallel task submission")
                        thread_executor.shutdown(wait=False)
                        executor_instance._check_shutdown()

                    if retry_config:
                        # With retry config -> .1, .2, etc.
                        future = thread_executor.submit(ParallelExecutor.execute_single_task_with_retry, task, master_timeout, retry_config, executor_instance=executor_instance)
                    else:
                        # Without retry config -> no number
                        future = thread_executor.submit(ParallelExecutor.execute_single_task_for_parallel, task, master_timeout, "", executor_instance=executor_instance)
                    future_to_task[future] = task
                
                # Collect results with MASTER TIMEOUT enforcement
                # Phase 1: Collect all task results and start sleeps in parallel
                sleep_trackers = []  # Track sleep operations separately

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
                            task_display_id = f"{task_id}-{result['task_id']}"

                            # Handle sleep AFTER task completion - START WITHOUT WAITING
                            sleep_seconds = result.get('sleep_seconds', 0)
                            if sleep_seconds > 0 and not executor_instance.dry_run:
                                executor_instance.log(f"Task {task_display_id}: Scheduling non-blocking sleep for {sleep_seconds} seconds...")

                                # Create event for this sleep operation
                                result_completion_event = threading.Event()

                                def make_sleep_callback(event, task_id_local):
                                    """Create a closure to capture the correct event and task_id."""
                                    def sleep_completed_callback():
                                        """Process result after sleep completes."""
                                        executor_instance.log_debug(f"Task {task_id_local}: Sleep completed")
                                        event.set()
                                    return sleep_completed_callback

                                # Start the sleep timer without waiting
                                sleep_timer = sleep_async(
                                    sleep_seconds,
                                    make_sleep_callback(result_completion_event, task_display_id),
                                    task_id=f"{task_display_id}-post-sleep",
                                    logger_callback=executor_instance.log_debug
                                )

                                # Track this sleep operation for later collection
                                sleep_trackers.append({
                                    'event': result_completion_event,
                                    'timer': sleep_timer,
                                    'task_id': task_display_id,
                                    'duration': sleep_seconds,
                                    'result': result,
                                    'start_time': time.time()
                                })
                            else:
                                # No sleep needed, add result immediately
                                results.append(result)

                                # Log completion immediately for non-sleeping tasks
                                success_text = "Success: True" if result['success'] else "Success: False"
                                if result['exit_code'] == 124:
                                    success_text += " (timeout)"
                                elif result.get('skipped', False):
                                    success_text += " (skipped)"
                                executor_instance.log(f"Task {task_display_id}: Completed - {success_text}")
                                
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

                    # Also cancel any pending sleeps
                    for tracker in sleep_trackers:
                        if tracker['timer'] and not tracker['event'].is_set():
                            tracker['timer'].cancel()

                # Phase 2: Wait for all sleep operations to complete in parallel
                # This happens AFTER all task results are collected
                if sleep_trackers:
                    executor_instance.log_debug(f"Task {task_id}: Waiting for {len(sleep_trackers)} post-execution sleeps to complete...")

                    # Wait for each sleep tracker
                    for tracker in sleep_trackers:
                        task_display_id = tracker['task_id']
                        result = tracker['result']

                        # Calculate remaining wait time for this specific sleep
                        elapsed_since_start = time.time() - tracker['start_time']
                        remaining_wait = max(0, tracker['duration'] + 5.0 - elapsed_since_start)

                        if remaining_wait > 0:
                            if not tracker['event'].wait(timeout=remaining_wait):
                                executor_instance.log_warn(
                                    f"Task {task_display_id}: Post-sleep timer did not signal within timeout; proceeding"
                                )

                        # Add the result after sleep completion (or timeout)
                        results.append(result)

                        # Log completion after sleep
                        success_text = "Success: True" if result['success'] else "Success: False"
                        if result['exit_code'] == 124:
                            success_text += " (timeout)"
                        elif result.get('skipped', False):
                            success_text += " (skipped)"
                        executor_instance.log(f"Task {task_display_id}: Completed - {success_text}")

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
        
        # Check if we have a success parameter for flexible routing
        if 'success' in parallel_task:
            # Evaluate success condition using the same logic as next conditions
            success_condition = parallel_task['success']
            executor_instance.log_debug(f"Task {task_id}: Evaluating 'success' condition: {success_condition}")

            # Use the same evaluation function that handles min_success, max_failed, etc.
            # Note: This only returns True or False (never "NEVER" or "LOOP")
            should_continue = ParallelExecutor.evaluate_parallel_next_condition(
                success_condition, results, executor_instance.log_debug, executor_instance.log_info)

            executor_instance.log_info(f"Task {task_id}: Success condition '{success_condition}' evaluated to: {should_continue}")
        else:
            # Use enhanced parallel next condition evaluation (existing behavior)
            # Note: This can return True, False, "NEVER", or "LOOP"
            should_continue = executor_instance.check_parallel_next_condition(parallel_task, results)

            # Handle special return values from check_parallel_next_condition (only for 'next' parameter)
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

        # If condition not met and no on_failure routing, this is a workflow failure
        if not should_continue:
            executor_instance._state_manager.workflow_failed_due_to_condition = True
            return None

        return task_id + 1

    def execute(self, task, **kwargs):
        """Execute a task using parallel execution."""
        executor_instance = kwargs.get('executor_instance')
        if not executor_instance:
            raise ValueError("executor_instance required for parallel execution")
        return ParallelExecutor.execute_parallel_tasks(task, executor_instance)