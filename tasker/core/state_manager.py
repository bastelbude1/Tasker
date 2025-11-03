# tasker/core/state_manager.py
"""
TASKER 2.1 - State Management Component
--------------------------------------
Handles all state storage and retrieval operations in a thread-safe manner.

Responsibilities:
- Task results storage and retrieval
- Loop counters and iteration tracking
- Current task tracking
- Global variables management
- Thread-safe state operations
"""

import threading
from typing import Dict, Any, Optional


class StateManager:
    """
    Thread-safe state management for TASKER execution.

    Manages all stateful data during task execution including results,
    loop tracking, and global variables.
    """

    def __init__(self):
        """Initialize state manager with thread-safe storage."""
        # Thread-safe lock for all state operations
        self._lock = threading.RLock()

        # Core state storage
        self._task_results = {}  # Store task execution results
        self._current_task = 0   # Track current executing task
        self._loop_counter = {}  # Track remaining loop iterations
        self._loop_iterations = {}  # Track current iteration number
        self._global_vars = {}   # Store global variables
        self._global_vars_metadata = {}  # Store global variable source metadata (env vs literal)
        self._execution_path = []  # Track task execution order for recovery

        # Additional state tracking
        self._tasks = {}  # Task definitions storage

        # Workflow failure tracking
        self.workflow_failed_due_to_condition = False  # Track if workflow stopped due to failed next condition

    # ===== TASK RESULTS MANAGEMENT =====

    def store_task_result(self, task_id: int, result: Dict[str, Any]) -> None:
        """
        Store task execution result in thread-safe manner.

        Args:
            task_id: Task identifier
            result: Task execution result dictionary
        """
        with self._lock:
            self._task_results[task_id] = result.copy()

    def get_task_result(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve task execution result.

        Args:
            task_id: Task identifier

        Returns:
            Task result dictionary or None if not found
        """
        with self._lock:
            result = self._task_results.get(task_id)
            return result.copy() if isinstance(result, dict) else None

    def has_task_result(self, task_id: int) -> bool:
        """
        Check if task result exists.

        Args:
            task_id: Task identifier

        Returns:
            True if result exists, False otherwise
        """
        with self._lock:
            return task_id in self._task_results

    def get_all_task_results(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all task results (thread-safe copy).

        Returns:
            Copy of all task results
        """
        with self._lock:
            return self._task_results.copy()

    # ===== CURRENT TASK TRACKING =====

    def set_current_task(self, task_id: int) -> None:
        """
        Set the currently executing task.

        Args:
            task_id: Task identifier
        """
        with self._lock:
            self._current_task = task_id

    def get_current_task(self) -> int:
        """
        Get the currently executing task.

        Returns:
            Current task identifier
        """
        with self._lock:
            return self._current_task

    # ===== LOOP TRACKING =====

    def set_loop_counter(self, task_id: int, remaining: int) -> None:
        """
        Set remaining loop iterations for a task.

        Args:
            task_id: Task identifier
            remaining: Remaining loop iterations
        """
        with self._lock:
            self._loop_counter[task_id] = remaining

    def get_loop_counter(self, task_id: int) -> int:
        """
        Get remaining loop iterations for a task.

        Args:
            task_id: Task identifier

        Returns:
            Remaining loop iterations (0 if not found)
        """
        with self._lock:
            return self._loop_counter.get(task_id, 0)

    def decrement_loop_counter(self, task_id: int) -> int:
        """
        Decrement loop counter and return new value.

        Args:
            task_id: Task identifier

        Returns:
            New loop counter value
        """
        with self._lock:
            if task_id in self._loop_counter:
                self._loop_counter[task_id] -= 1
                return self._loop_counter[task_id]
            return 0

    def set_loop_iteration(self, task_id: int, iteration: int) -> None:
        """
        Set current loop iteration number for a task.

        Args:
            task_id: Task identifier
            iteration: Current iteration number
        """
        with self._lock:
            self._loop_iterations[task_id] = iteration

    def get_loop_iteration(self, task_id: int) -> int:
        """
        Get current loop iteration number for a task.

        Args:
            task_id: Task identifier

        Returns:
            Current iteration number (0 if not found)
        """
        with self._lock:
            return self._loop_iterations.get(task_id, 0)

    def clear_loop_tracking(self, task_id: int) -> None:
        """
        Clear all loop tracking for a task.

        Args:
            task_id: Task identifier
        """
        with self._lock:
            self._loop_counter.pop(task_id, None)
            self._loop_iterations.pop(task_id, None)

    # ===== GLOBAL VARIABLES =====

    def set_global_vars(self, global_vars: Dict[str, str], metadata: Optional[Dict] = None) -> None:
        """
        Set global variables (replaces existing).

        Args:
            global_vars: Dictionary of global variables
            metadata: Optional metadata about variable sources (env vs literal)
        """
        with self._lock:
            self._global_vars = global_vars.copy()
            if metadata is not None:
                self._global_vars_metadata = metadata.copy()

    def get_global_vars(self) -> Dict[str, str]:
        """
        Get global variables (thread-safe copy).

        Returns:
            Copy of global variables dictionary
        """
        with self._lock:
            return self._global_vars.copy()

    def get_global_vars_metadata(self) -> Dict:
        """
        Get global variables metadata (thread-safe copy).

        Returns:
            Copy of global variables metadata dictionary
        """
        with self._lock:
            return self._global_vars_metadata.copy()

    def get_global_var(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get specific global variable.

        Args:
            key: Variable name
            default: Default value if not found

        Returns:
            Variable value or default
        """
        with self._lock:
            return self._global_vars.get(key, default)

    # ===== EXECUTION PATH TRACKING =====

    def append_to_execution_path(self, task_id: int) -> None:
        """
        Append task ID to execution path.

        Args:
            task_id: Task identifier to append
        """
        with self._lock:
            if task_id not in self._execution_path:
                self._execution_path.append(task_id)

    def get_execution_path(self):
        """
        Get execution path (list of executed task IDs).

        Returns:
            Copy of execution path list
        """
        with self._lock:
            return self._execution_path.copy()

    def set_execution_path(self, path):
        """
        Set execution path (used for recovery state restoration).

        Args:
            path: List of task IDs
        """
        with self._lock:
            self._execution_path = list(path)

    # ===== TASK DEFINITIONS =====

    def set_tasks(self, tasks: Dict[int, Dict[str, Any]]) -> None:
        """
        Set task definitions.

        Args:
            tasks: Dictionary of task definitions
        """
        with self._lock:
            self._tasks = tasks.copy()

    def get_tasks(self) -> Dict[int, Dict[str, Any]]:
        """
        Get task definitions (thread-safe copy).

        Returns:
            Copy of task definitions
        """
        with self._lock:
            return self._tasks.copy()

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get specific task definition.

        Args:
            task_id: Task identifier

        Returns:
            Task definition or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)

    # ===== STATE CLEANUP =====

    def clear_all_state(self) -> None:
        """Clear all state data."""
        with self._lock:
            self._task_results.clear()
            self._current_task = 0
            self._loop_counter.clear()
            self._loop_iterations.clear()
            self._global_vars.clear()
            self._execution_path.clear()
            self._tasks.clear()
            self.workflow_failed_due_to_condition = False

    # ===== COMPATIBILITY PROPERTIES =====

    @property
    def task_results(self) -> Dict[int, Dict[str, Any]]:
        """Backward compatibility property for task_results access."""
        return self.get_all_task_results()

    @property
    def current_task(self) -> int:
        """Backward compatibility property for current_task access."""
        return self.get_current_task()

    @current_task.setter
    def current_task(self, value: int) -> None:
        """Backward compatibility setter for current_task."""
        self.set_current_task(value)

    @property
    def loop_counter(self) -> Dict[int, int]:
        """Backward compatibility property for loop_counter access."""
        with self._lock:
            return self._loop_counter.copy()

    @property
    def loop_iterations(self) -> Dict[int, int]:
        """Backward compatibility property for loop_iterations access."""
        with self._lock:
            return self._loop_iterations.copy()

    @property
    def global_vars(self) -> Dict[str, str]:
        """Backward compatibility property for global_vars access."""
        return self.get_global_vars()

    @property
    def tasks(self) -> Dict[int, Dict[str, Any]]:
        """Backward compatibility property for tasks access."""
        return self.get_tasks()