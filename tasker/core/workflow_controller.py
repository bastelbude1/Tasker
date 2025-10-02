# tasker/core/workflow_controller.py
"""
TASKER 2.1 - Workflow Control Component
--------------------------------------
Handles workflow flow control, routing, and loop management.

Responsibilities:
- Next condition evaluation and routing
- Loop handling for sequential and parallel tasks
- Success condition evaluation
- Task jumping and workflow navigation
- Break condition handling
"""

from typing import Dict, Any, Optional, Union, List
from .condition_evaluator import ConditionEvaluator


class WorkflowController:
    """
    Controls task execution flow, routing, and loop management.

    Manages all aspects of workflow navigation including conditional
    routing, loop handling, and success criteria evaluation.
    """

    def __init__(self, state_manager, logger_callback=None, debug_logger_callback=None):
        """
        Initialize workflow controller.

        Args:
            state_manager: StateManager instance for accessing state
            logger_callback: Optional callback for logging messages
            debug_logger_callback: Optional callback for debug logging
        """
        self.state_manager = state_manager
        self.log_info = logger_callback if logger_callback else lambda msg: None
        self.log_debug = debug_logger_callback if debug_logger_callback else lambda msg: None

    # ===== NEXT CONDITION EVALUATION =====

    def check_next_condition(self, task: Dict[str, Any], exit_code: int,
                           stdout: str, stderr: str,
                           current_task_success: Optional[bool] = None) -> Union[bool, str]:
        """
        Check if the 'next' condition is satisfied.

        Args:
            task: Task definition dictionary
            exit_code: Task exit code
            stdout: Task stdout
            stderr: Task stderr
            current_task_success: Optional explicit success status

        Returns:
            True: Proceed to next task
            False: Stop execution
            "NEVER": Special stop condition
            "LOOP": Loop back to current task
        """
        task_id = int(task['task'])

        # Get loop iteration display if looping
        loop_display = ""
        loop_iteration = self.state_manager.get_loop_iteration(task_id)
        if loop_iteration > 0:
            loop_display = f".{loop_iteration}"

        if 'next' not in task:
            self.log_info(f"Task {task_id}{loop_display}: No 'next' condition specified, proceeding to next task")
            return True  # Default to True if not specified

        next_condition = task['next']

        # Special cases
        if next_condition == 'never':
            self.log_info(f"Task {task_id}{loop_display}: 'next=never' found, stopping execution")
            return "NEVER"  # Special case

        if next_condition == 'always':
            self.log_info(f"Task {task_id}{loop_display}: 'next=always' found, proceeding to next task")
            return True

        # Handle the loop case with simplified syntax
        if next_condition == 'loop' and 'loop' in task:
            return self._handle_sequential_loop(task, exit_code, stdout, stderr)

        # Check if it's a success condition
        if next_condition == 'success':
            # Use provided success status or evaluate default condition
            if current_task_success is not None:
                result = current_task_success
            else:
                # Default success condition: exit_code == 0
                result = (exit_code == 0)

            if result:
                self.log_info(f"Task {task_id}{loop_display}: 'next=success' condition met, proceeding to next task")
            else:
                self.log_info(f"Task {task_id}{loop_display}: 'next=success' condition not met, stopping execution")

            return result

        # General condition evaluation
        try:
            result = ConditionEvaluator.evaluate_condition(
                next_condition, exit_code, stdout, stderr,
                self.state_manager.global_vars, self.state_manager.task_results,
                self.log_debug  # Pass proper debug callback for traceability
            )

            if result:
                self.log_info(f"Task {task_id}{loop_display}: 'next' condition '{next_condition}' met, proceeding to next task")
            else:
                self.log_info(f"Task {task_id}{loop_display}: 'next' condition '{next_condition}' not met, stopping execution")

            return result

        except Exception as e:
            # Detailed exception logging for better diagnosability
            import traceback
            self.log_info(f"Task {task_id}{loop_display}: Error evaluating 'next' condition '{next_condition}': {str(e)}")
            self.log_debug(f"Task {task_id}{loop_display}: Exception traceback:\n{traceback.format_exc()}")
            return False

    def _handle_sequential_loop(self, task: Dict[str, Any], exit_code: int,
                              stdout: str, stderr: str) -> Union[str, bool]:
        """
        Handle loop logic for sequential tasks.

        Args:
            task: Task definition dictionary
            exit_code: Task exit code
            stdout: Task stdout
            stderr: Task stderr

        Returns:
            "LOOP": Continue looping
            True: Exit loop and proceed
        """
        task_id = int(task['task'])

        # Check if this is the first time we're seeing this task
        if self.state_manager.get_loop_counter(task_id) == 0:
            loop_count = int(task['loop'])
            self.state_manager.set_loop_counter(task_id, loop_count)
            self.state_manager.set_loop_iteration(task_id, 1)
            self.log_info(f"Task {task_id}: Loop initialized with count {loop_count}")
        else:
            # Increment iteration counter
            current_iteration = self.state_manager.get_loop_iteration(task_id)
            self.state_manager.set_loop_iteration(task_id, current_iteration + 1)

        # Check loop_break condition first (if exists)
        if 'loop_break' in task:
            loop_break_result = ConditionEvaluator.evaluate_condition(
                task['loop_break'], exit_code, stdout, stderr,
                self.state_manager.global_vars, self.state_manager.task_results,
                lambda msg: None  # Debug callback
            )

            if loop_break_result:
                # Break condition met
                self.log_info(f"Task {task_id}: Breaking loop - loop_break condition "
                            f"'{task['loop_break']}' satisfied")
                self.state_manager.clear_loop_tracking(task_id)
                return True  # Exit loop

        # Check remaining loops
        remaining = self.state_manager.decrement_loop_counter(task_id)

        if remaining > 0:
            # Continue looping
            current_iteration = self.state_manager.get_loop_iteration(task_id)
            self.log_info(f"Task {task_id}.{current_iteration}: Loop iteration completed, "
                        f"{remaining} iterations remaining")
            return "LOOP"
        else:
            # Loop completed
            self.log_info(f"Task {task_id}: Loop completed, proceeding to next task")
            self.state_manager.clear_loop_tracking(task_id)
            return True

    # ===== PARALLEL TASK FLOW CONTROL =====

    def check_parallel_next_condition(self, parallel_task: Dict[str, Any],
                                    results: List[Dict[str, Any]]) -> bool:
        """
        Check next condition for parallel task execution.

        Args:
            parallel_task: Parallel task definition
            results: List of execution results from parallel tasks

        Returns:
            True if condition is met, False otherwise
        """
        task_id = int(parallel_task['task'])

        if 'next' not in parallel_task:
            # Default behavior: all tasks must succeed
            all_success = all(result['success'] for result in results)
            self.log_info(f"Task {task_id}: Default condition (all_success) evaluated to: {all_success}")
            return all_success

        next_condition = parallel_task['next']

        # Special conditions for parallel tasks
        if next_condition == 'all_success':
            result = all(r['success'] for r in results)
            self.log_info(f"Task {task_id}: all_success condition evaluated to: {result}")
            return result

        if next_condition == 'any_success':
            result = any(r['success'] for r in results)
            self.log_info(f"Task {task_id}: any_success condition evaluated to: {result}")
            return result

        if next_condition == 'majority_success':
            successful_count = sum(1 for r in results if r['success'])
            result = successful_count > len(results) / 2
            self.log_info(f"Task {task_id}: majority_success condition evaluated to: {result}")
            return result

        if next_condition.startswith('min_success='):
            try:
                min_required = int(next_condition.split('=')[1])
                successful_count = sum(1 for r in results if r['success'])
                result = successful_count >= min_required
                self.log_info(f"Task {task_id}: min_success={min_required} condition evaluated to: {result}")
                return result
            except (ValueError, IndexError):
                self.log_info(f"Task {task_id}: Invalid min_success condition format")
                return False

        if next_condition.startswith('max_failed='):
            try:
                max_failed = int(next_condition.split('=')[1])
                failed_count = sum(1 for r in results if not r['success'])
                result = failed_count <= max_failed
                self.log_info(f"Task {task_id}: max_failed={max_failed} condition evaluated to: {result}")
                return result
            except (ValueError, IndexError):
                self.log_info(f"Task {task_id}: Invalid max_failed condition format")
                return False

        # Delegate unknown/complex conditions to ConditionEvaluator for legacy compatibility
        try:
            # Create context with derived values for complex expression evaluation
            successful_count = sum(1 for r in results if r['success'])
            failed_count = sum(1 for r in results if not r['success'])
            total_count = len(results)

            # Construct aggregated context similar to how parallel loop_break works
            aggregated_exit_code = 0 if successful_count == total_count else 1
            aggregated_stdout = (f"Parallel execution summary: {successful_count} successful, "
                               f"{failed_count} failed, {total_count} total")
            aggregated_stderr = ""

            # Attempt to evaluate as a complex condition using ConditionEvaluator
            self.log_info(f"Task {task_id}: Attempting to evaluate complex condition '{next_condition}' via ConditionEvaluator")

            result = ConditionEvaluator.evaluate_condition(
                next_condition, aggregated_exit_code, aggregated_stdout, aggregated_stderr,
                self.state_manager.global_vars, self.state_manager.task_results,
                lambda msg: None  # Debug callback
            )

            self.log_info(f"Task {task_id}: Complex condition '{next_condition}' evaluated to: {result}")
            return result

        except Exception as e:
            # If ConditionEvaluator cannot interpret the expression, log and default to False
            self.log_info(f"Task {task_id}: Invalid/unsupported parallel next condition '{next_condition}': {str(e)}. Defaulting to False")
            return False

    def handle_parallel_loop(self, parallel_task: Dict[str, Any],
                           results: List[Dict[str, Any]]) -> bool:
        """
        Handle loop logic for parallel tasks.

        Args:
            parallel_task: Parallel task definition
            results: List of execution results

        Returns:
            True if should break loop, False if should continue
        """
        task_id = int(parallel_task['task'])

        # Check if this is the first time we're seeing this task
        if self.state_manager.get_loop_counter(task_id) == 0:
            loop_count = int(parallel_task['loop'])
            self.state_manager.set_loop_counter(task_id, loop_count)
            self.state_manager.set_loop_iteration(task_id, 1)
            self.log_info(f"Task {task_id}: Loop initialized with count {loop_count}")
        else:
            # Increment iteration counter
            current_iteration = self.state_manager.get_loop_iteration(task_id)
            self.state_manager.set_loop_iteration(task_id, current_iteration + 1)

        # Check loop_break condition first (if exists)
        if 'loop_break' in parallel_task:
            # For parallel tasks, evaluate loop_break against aggregated results
            successful_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            aggregated_exit_code = 0 if successful_count == len(results) else 1
            aggregated_stdout = (f"Parallel execution summary: {successful_count} successful, "
                               f"{failed_count} failed")
            aggregated_stderr = ""

            loop_break_result = ConditionEvaluator.evaluate_condition(
                parallel_task['loop_break'], aggregated_exit_code, aggregated_stdout,
                aggregated_stderr, self.state_manager.global_vars,
                self.state_manager.task_results, lambda msg: None
            )

            if loop_break_result:
                self.log_info(f"Task {task_id}: Breaking loop - condition "
                            f"'{parallel_task['loop_break']}' satisfied")
                self.state_manager.clear_loop_tracking(task_id)
                return True

        # Check remaining loops
        remaining = self.state_manager.decrement_loop_counter(task_id)

        if remaining > 0:
            current_iteration = self.state_manager.get_loop_iteration(task_id)
            self.log_info(f"Task {task_id}.{current_iteration}: Parallel loop iteration completed, "
                        f"{remaining} iterations remaining")
            return False  # Continue looping
        else:
            self.log_info(f"Task {task_id}: Parallel loop completed")
            self.state_manager.clear_loop_tracking(task_id)
            return True  # Break loop

    # ===== TASK ROUTING =====

    def get_next_task_id(self, task: Dict[str, Any], success: bool,
                        current_task_id: int) -> Optional[int]:
        """
        Determine the next task ID based on success/failure routing.

        Args:
            task: Current task definition
            success: Whether current task succeeded
            current_task_id: Current task ID

        Returns:
            Next task ID or None to stop execution
        """
        if success and 'on_success' in task:
            try:
                next_id = int(task['on_success'])
                self.log_info(f"Task {current_task_id}: Success - jumping to Task {next_id}")
                return next_id
            except ValueError:
                self.log_info(f"Task {current_task_id}: Invalid 'on_success' task ID '{task['on_success']}'")
                return current_task_id + 1

        if not success and 'on_failure' in task:
            try:
                next_id = int(task['on_failure'])
                self.log_info(f"Task {current_task_id}: Failure - jumping to Task {next_id}")
                return next_id
            except ValueError:
                self.log_info(f"Task {current_task_id}: Invalid 'on_failure' task ID '{task['on_failure']}'")
                return None

        # Default sequential progression
        if success:
            return current_task_id + 1
        else:
            return None  # Stop on failure if no on_failure specified

    # ===== CONDITION UTILITIES =====

    def evaluate_task_condition(self, condition: str, exit_code: int,
                               stdout: str, stderr: str) -> bool:
        """
        Evaluate a task condition string.

        Args:
            condition: Condition string to evaluate
            exit_code: Task exit code
            stdout: Task stdout
            stderr: Task stderr

        Returns:
            True if condition is met, False otherwise
        """
        try:
            return ConditionEvaluator.evaluate_condition(
                condition, exit_code, stdout, stderr,
                self.state_manager.global_vars, self.state_manager.task_results,
                lambda msg: None  # Debug callback
            )
        except Exception:
            return False

    def should_skip_task(self, task: Dict[str, Any]) -> bool:
        """
        Check if a task should be skipped based on its condition.

        Args:
            task: Task definition dictionary

        Returns:
            True if task should be skipped, False otherwise
        """
        if 'condition' not in task:
            return False

        try:
            # Evaluate condition with dummy values for initial check
            result = ConditionEvaluator.evaluate_condition(
                task['condition'], 0, "", "",
                self.state_manager.global_vars, self.state_manager.task_results,
                lambda msg: None
            )
            return not result
        except Exception:
            # If condition evaluation fails, don't skip
            return False