# tasker/core/task_runner.py
"""
TASKER 2.1 - Task Execution Component
------------------------------------
Handles core task execution logic and coordination.

Responsibilities:
- Core task execution coordination
- Command building and execution type determination
- Timeout handling and configuration
- Integration with specialized executor modules
- Execution context management
"""

import os
import shlex
from typing import Dict, Any, Optional, List
from .condition_evaluator import ConditionEvaluator
from .execution_context import ExecutionContext
from ..executors.base_executor import BaseExecutor
from ..executors.parallel_executor import ParallelExecutor
from ..executors.conditional_executor import ConditionalExecutor


class TaskRunner:
    """
    Coordinates task execution across different execution models.

    Manages the execution of individual tasks and delegates to appropriate
    specialized executors while handling common execution concerns.
    """

    def __init__(self, state_manager, workflow_controller, result_collector,
                 default_exec_type='local', default_timeout=300, dry_run=False,
                 logger_callback=None, debug_logger_callback=None):
        """
        Initialize task runner.

        Args:
            state_manager: StateManager instance for state access
            workflow_controller: WorkflowController instance for flow control
            result_collector: ResultCollector instance for result handling
            default_exec_type: Default execution type (loaded from config in TaskExecutorMain, fallback: 'local')
            default_timeout: Default timeout in seconds
            dry_run: Whether to run in dry-run mode
            logger_callback: Optional callback for regular logging
            debug_logger_callback: Optional callback for debug logging
        """
        self.state_manager = state_manager
        self.workflow_controller = workflow_controller
        self.result_collector = result_collector
        self.default_exec_type = default_exec_type
        self.default_timeout = default_timeout
        self.dry_run = dry_run

        # Logging callbacks
        self.log = logger_callback if logger_callback else lambda msg: None
        self.log_debug = debug_logger_callback if debug_logger_callback else lambda msg: None
        self.log_warn = logger_callback if logger_callback else lambda msg: None

        # Command-line override for execution type
        self.exec_type_override = None

    # ===== EXECUTION TYPE AND COMMAND BUILDING =====

    def set_execution_type_override(self, exec_type: Optional[str]) -> None:
        """
        Set command-line execution type override.

        Args:
            exec_type: Execution type override from command line
        """
        self.exec_type_override = exec_type

    def determine_execution_type(self, task: Dict[str, Any], task_display_id: str,
                                loop_display: str = "") -> str:
        """
        Determine which execution type to use, respecting priority order.

        Priority order:
        1. Task-specific 'exec' parameter (highest)
        2. Command-line argument override
        3. Environment variable TASK_EXECUTOR_TYPE
        4. Default execution type (lowest)

        Args:
            task: Task definition dictionary
            task_display_id: Task display identifier for logging
            loop_display: Loop iteration display string

        Returns:
            Execution type string
        """
        if 'exec' in task:
            exec_type, _ = ConditionEvaluator.replace_variables(
                task['exec'], self.state_manager.global_vars,
                self.state_manager.task_results, self.log_debug
            )
            self.log_debug(f"Task {task_display_id}{loop_display}: Using execution type from task: {exec_type}")
        elif self.exec_type_override:
            exec_type = self.exec_type_override
            self.log_debug(f"Task {task_display_id}{loop_display}: Using execution type from args: {exec_type}")
        elif 'TASK_EXECUTOR_TYPE' in os.environ:
            exec_type = os.environ['TASK_EXECUTOR_TYPE']
            self.log_debug(f"Task {task_display_id}{loop_display}: Using execution type from environment: {exec_type}")
        else:
            exec_type = self.default_exec_type
            self.log_debug(f"Task {task_display_id}{loop_display}: Using default execution type: {exec_type}")

        return exec_type

    def build_command_array(self, exec_type: str, hostname: str,
                           command: str, arguments: str = "") -> List[str]:
        """
        Build the command array based on execution type.

        Args:
            exec_type: Execution type (pbrun, p7s, local, wwrs)
            hostname: Target hostname
            command: Command to execute
            arguments: Command arguments

        Returns:
            List of command array elements
        """
        # Expand environment variables in arguments
        expanded_arguments = os.path.expandvars(arguments) if arguments else ""

        if exec_type == 'pbrun':
            return ["pbrun", "-n", "-h", hostname, command, *shlex.split(expanded_arguments)]
        elif exec_type == 'p7s':
            return ["p7s", hostname, command, *shlex.split(expanded_arguments)]
        elif exec_type == 'local':
            return [command, *shlex.split(expanded_arguments)]
        elif exec_type == 'wwrs':
            return ["wwrs_clir", hostname, command, *shlex.split(expanded_arguments)]
        else:
            # LEGACY FALLBACK: This code path should not be reached in normal operation.
            # The new architecture (TaskExecutorMain) uses exec_config_loader.build_command_array()
            # which supports all configured execution types from YAML.
            #
            # This fallback is reached if:
            # 1. TaskRunner is instantiated independently (testing/debugging)
            # 2. exec_config_loader.build_command_array() returns None (exec type not in YAML)
            # 3. A custom exec type is passed without corresponding YAML config
            #
            # Defensive programming: Fall back to local execution as the safest default.
            self.log_warn(f"Unknown execution type '{exec_type}', using 'local' as safe fallback")
            return [command, *shlex.split(expanded_arguments)]

    # ===== TIMEOUT HANDLING =====

    def get_task_timeout(self, task: Dict[str, Any]) -> int:
        """
        Determine the timeout for a task, respecting priority order.

        Priority order:
        1. Task-specific 'timeout' parameter (highest)
        2. Default timeout (lowest)

        Args:
            task: Task definition dictionary

        Returns:
            Timeout value in seconds
        """
        min_timeout = 5
        max_timeout = 1000

        # Get timeout from task (highest priority)
        if 'timeout' in task:
            timeout_str, resolved = ConditionEvaluator.replace_variables(
                task['timeout'], self.state_manager.global_vars,
                self.state_manager.task_results, self.log_debug
            )
            if resolved:
                try:
                    timeout = int(timeout_str)
                    self.log_debug(f"Using timeout from task: {timeout}")
                    # Clamp to valid range
                    return max(min_timeout, min(timeout, max_timeout))
                except ValueError:
                    self.log_warn(f"Invalid timeout value in task: '{timeout_str}'. Using default.")

        # Use default timeout
        self.log_debug(f"Using default timeout: {self.default_timeout}")
        return max(min_timeout, min(self.default_timeout, max_timeout))

    # ===== EXECUTION CONTEXT MANAGEMENT =====

    def get_execution_context(self) -> ExecutionContext:
        """
        Create execution context for task execution.

        Returns:
            ExecutionContext instance configured for current runner
        """
        # Create adapter object that mimics TaskExecutor interface
        class ExecutorAdapter:
            def __init__(self, runner_instance):
                # State access
                self.global_vars = runner_instance.state_manager.global_vars
                self.task_results = runner_instance.state_manager.task_results

                # Configuration
                self.dry_run = runner_instance.dry_run
                self.timeout = runner_instance.default_timeout

                # Logging callbacks
                self.log = runner_instance.log
                self.log_debug = runner_instance.log_debug
                self.log_error = runner_instance.log_error
                self.log_warn = runner_instance.log_warn
                self.log_info = runner_instance.log_info

                # Execution methods (delegate to runner)
                self.determine_execution_type = runner_instance.determine_execution_type
                self.build_command_array = runner_instance.build_command_array
                self.get_task_timeout = runner_instance.get_task_timeout

                # Additional methods that ExecutionContext may need
                self.categorize_task_result = getattr(runner_instance, 'categorize_task_result', None)
                self.store_task_result = getattr(runner_instance, 'store_task_result', None)
                self._check_shutdown = getattr(runner_instance, '_check_shutdown', None)

        adapter = ExecutorAdapter(self)
        return ExecutionContext(adapter)

    # ===== CORE TASK EXECUTION =====

    def execute_task_core(self, task: Dict[str, Any], master_timeout: Optional[int] = None,
                         context: str = "normal", retry_display: str = "") -> Dict[str, Any]:
        """
        Execute a single task using the appropriate executor.

        This is the unified entry point for all task execution that delegates
        to the BaseExecutor's standardized execution logic.

        Args:
            task: Task definition dictionary
            master_timeout: Optional master timeout override
            context: Execution context (normal, parallel, conditional)
            retry_display: Display string for retry attempts

        Returns:
            Task execution result dictionary
        """
        execution_context = self.get_execution_context()
        return BaseExecutor.execute_task_core(
            task, execution_context, master_timeout, context, retry_display
        )

    # ===== SPECIALIZED EXECUTION MODELS =====

    def execute_parallel_tasks(self, parallel_task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute multiple tasks in parallel with enhanced retry logic.

        Args:
            parallel_task: Parallel task definition dictionary

        Returns:
            List of task execution results
        """
        return ParallelExecutor.execute_parallel_tasks(parallel_task, self)

    def execute_conditional_tasks(self, conditional_task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute conditional tasks based on condition evaluation.

        Args:
            conditional_task: Conditional task definition dictionary

        Returns:
            List of task execution results from executed branch
        """
        return ConditionalExecutor.execute_conditional_tasks(conditional_task, self)

    # ===== TASK ROUTING AND FLOW CONTROL =====

    def should_execute_task(self, task: Dict[str, Any]) -> bool:
        """
        Determine if a task should be executed based on its condition.

        Args:
            task: Task definition dictionary

        Returns:
            True if task should be executed, False if should be skipped
        """
        if 'condition' not in task:
            return True

        try:
            result = ConditionEvaluator.evaluate_condition(
                task['condition'], 0, "", "",
                self.state_manager.global_vars, self.state_manager.task_results,
                self.log_debug
            )
            return result
        except Exception as e:
            self.log_warn(f"Error evaluating task condition '{task['condition']}': {str(e)}")
            return True  # Default to execute if condition evaluation fails

    def get_next_task_id(self, task: Dict[str, Any], task_result: Dict[str, Any]) -> Optional[int]:
        """
        Determine the next task ID based on execution result and flow control.

        Args:
            task: Current task definition
            task_result: Task execution result

        Returns:
            Next task ID or None to stop execution
        """
        current_task_id = int(task['task'])
        success = task_result['success']

        # Check for explicit routing (on_success/on_failure)
        next_task_id = self.workflow_controller.get_next_task_id(
            task, success, current_task_id
        )

        if next_task_id is not None:
            return next_task_id

        # If workflow_controller returned None and set failure flag, stop immediately
        # This handles on_success-only pattern where failure should exit with code 10
        if self.state_manager.workflow_failed_due_to_condition:
            return None

        # Check next condition for flow control
        next_result = self.workflow_controller.check_next_condition(
            task, task_result['exit_code'], task_result['stdout'],
            task_result['stderr'], success
        )

        if next_result == "LOOP":
            return current_task_id  # Loop back to same task
        elif next_result == "NEVER":
            # Explicit successful stop with next=never
            return None
        elif not next_result:
            # Condition not met - this is a workflow FAILURE
            # Set flag to indicate workflow stopped due to failed condition
            self.state_manager.workflow_failed_due_to_condition = True
            return None  # Stop execution
        else:
            return current_task_id + 1  # Continue to next sequential task

    # ===== UTILITY METHODS =====

    def store_task_result(self, task_id: int, result: Dict[str, Any]) -> None:
        """
        Store task execution result.

        Args:
            task_id: Task identifier
            result: Task execution result dictionary
        """
        self.state_manager.store_task_result(task_id, result)

    def get_task_result(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve task execution result.

        Args:
            task_id: Task identifier

        Returns:
            Task result dictionary or None if not found
        """
        return self.state_manager.get_task_result(task_id)

    def categorize_result(self, result: Dict[str, Any]) -> str:
        """
        Categorize task result for retry and reporting logic.

        Args:
            result: Task execution result dictionary

        Returns:
            Category string: 'TIMEOUT', 'SUCCESS', or 'FAILED'
        """
        return self.result_collector.categorize_task_result(result)

    # ===== COMPATIBILITY METHODS =====

    @property
    def current_task(self) -> int:
        """Get current task ID for compatibility."""
        return self.state_manager.current_task

    @current_task.setter
    def current_task(self, value: int) -> None:
        """Set current task ID for compatibility."""
        self.state_manager.current_task = value

    @property
    def global_vars(self) -> Dict[str, str]:
        """Get global variables for compatibility."""
        return self.state_manager.global_vars

    @property
    def task_results(self) -> Dict[int, Dict[str, Any]]:
        """Get task results for compatibility."""
        return self.state_manager.task_results