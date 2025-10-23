#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decision Executor Module for TASKER

This module handles the execution of decision blocks (type=decision).
Decision blocks are pure routing blocks that evaluate conditions without
executing commands, making workflow decisions based on success/failure conditions.

Decision blocks support:
- success= condition for success path
- failure= condition for explicit failure path
- Standard flow control: on_success, on_failure, next
- No command execution - only condition evaluation and routing
"""

from tasker.core.condition_evaluator import ConditionEvaluator


class DecisionExecutor:
    """
    Handles execution of decision blocks in TASKER workflows.

    Decision blocks evaluate conditions and route workflow execution
    without running any commands. They act as pure decision points.
    """

    @staticmethod
    def execute_decision_block(decision_task, task_id, executor_instance):
        """
        Execute a decision block by evaluating its conditions and determining routing.

        Args:
            decision_task: The decision task dictionary containing success/failure conditions
            task_id: The ID of the decision task
            executor_instance: The TaskExecutor instance (for logging and state access)

        Returns:
            int or None: Next task ID to execute, or None if workflow should stop
        """
        # Log the start of decision evaluation
        executor_instance.log(f"Task {task_id}: DECISION - Evaluating conditions")

        # Get success and failure conditions
        success_condition = decision_task.get('success', '')
        failure_condition = decision_task.get('failure', '')

        # Validate that at least one condition is defined (should be caught in validation)
        if not success_condition and not failure_condition:
            executor_instance.log(f"ERROR: Task {task_id}: Decision block has no success or failure conditions defined")
            return None

        # Initialize decision result
        decision_result = None
        decision_type = None

        # Evaluate EITHER success OR failure condition (not both)
        if success_condition:
            # Use dummy values for exit_code, stdout, stderr since decision blocks don't execute commands
            success_result = ConditionEvaluator.evaluate_condition(
                success_condition,
                exit_code=0,  # Not applicable for decision blocks
                stdout='',    # No command output
                stderr='',    # No command output
                global_vars=executor_instance.global_vars,
                task_results=executor_instance.task_results,
                debug_callback=executor_instance.log_debug
            )

            executor_instance.log(f"Task {task_id}: Decision condition '{success_condition}' evaluated to: {success_result}")

            if success_result:
                decision_result = True
                decision_type = 'success'
                executor_instance.log(f"Task {task_id}: Decision PASSED")
            else:
                # Success condition failed
                decision_result = False
                decision_type = 'failure'
                executor_instance.log(f"Task {task_id}: Decision FAILED (success condition not met)")

        # Evaluate failure condition ONLY if success condition is not defined
        elif failure_condition:
            failure_result = ConditionEvaluator.evaluate_condition(
                failure_condition,
                exit_code=0,  # Not applicable
                stdout='',
                stderr='',
                global_vars=executor_instance.global_vars,
                task_results=executor_instance.task_results,
                debug_callback=executor_instance.log_debug
            )

            executor_instance.log(f"Task {task_id}: Failure condition '{failure_condition}' evaluated to: {failure_result}")

            if failure_result:
                # Failure condition is true - decision fails
                decision_result = False
                decision_type = 'failure'
                executor_instance.log(f"Task {task_id}: Decision FAILED (failure condition met)")
            else:
                # Failure condition is false - decision succeeds
                decision_result = True
                decision_type = 'success'
                executor_instance.log(f"Task {task_id}: Decision PASSED (failure condition not met)")

        # If neither condition was met, log that
        if decision_result is None:
            executor_instance.log(f"Task {task_id}: No decision conditions met, using default routing")
            # Default behavior - continue to next sequential task unless next=never
            if decision_task.get('next') == 'never':
                executor_instance.log(f"Task {task_id}: Decision block has next=never, stopping execution")
                return None
            elif 'next' in decision_task:
                try:
                    next_task = int(decision_task['next'])
                    executor_instance.log(f"Task {task_id}: Proceeding to task {next_task} (next)")
                    return next_task
                except (ValueError, TypeError):
                    executor_instance.log(f"Task {task_id}: Invalid next value, continuing to task {task_id + 1}")
                    return task_id + 1
            else:
                executor_instance.log(f"Task {task_id}: Continuing to task {task_id + 1}")
                return task_id + 1

        # Store the decision result in task results for potential use by later tasks
        executor_instance.task_results[task_id] = {
            'exit': 0 if decision_result else 1,  # 0 for success, 1 for failure
            'stdout': f"Decision: {decision_type}",
            'stderr': '',
            'success': decision_result if decision_result is not None else True
        }

        # Apply routing based on decision result
        if decision_result is True:  # Success path
            if 'on_success' in decision_task:
                try:
                    next_task = int(decision_task['on_success'])
                    executor_instance.log(f"Task {task_id}: Decision success, jumping to task {next_task} (on_success)")
                    return next_task
                except (ValueError, TypeError):
                    executor_instance.log(f"Task {task_id}: Invalid on_success value, using default routing")

        elif decision_result is False:  # Failure path
            if 'on_failure' in decision_task:
                try:
                    next_task = int(decision_task['on_failure'])
                    executor_instance.log(f"Task {task_id}: Decision failure, jumping to task {next_task} (on_failure)")
                    return next_task
                except (ValueError, TypeError):
                    executor_instance.log(f"Task {task_id}: Invalid on_failure value, using default routing")

        # Default routing if no specific routing was triggered
        if decision_task.get('next') == 'never':
            executor_instance.log(f"Task {task_id}: Decision block has next=never, stopping execution")
            return None
        elif 'next' in decision_task:
            try:
                next_task = int(decision_task['next'])
                executor_instance.log(f"Task {task_id}: Proceeding to task {next_task} (next)")
                return next_task
            except (ValueError, TypeError):
                executor_instance.log(f"Task {task_id}: Invalid next value, continuing to task {task_id + 1}")
                return task_id + 1
        else:
            # Continue to next sequential task
            executor_instance.log(f"Task {task_id}: Continuing to task {task_id + 1}")
            return task_id + 1