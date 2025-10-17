"""
TASKER Dependency Analyzer
---------------------------
Analyzes task dependencies for safe resume validation.

This module provides functionality to:
- Parse variable references from task definitions
- Build dependency graphs
- Validate if resume points are safe (no backward dependencies)
- Provide clear error messages for unsafe resume scenarios

Dependency Types:
- Task output references: @0_stdout@, @1_success@, @2_exit_code@
- Global variable references: @GLOBAL_VAR@, @HOST_PREFIX@
"""

import re
from typing import Dict, List, Set, Tuple, Any


class DependencyAnalyzer:
    """Analyzes task dependencies for safe resume validation."""

    # Pattern for task output references: @N_field@ where N is a number
    TASK_REFERENCE_PATTERN = re.compile(r'@(\d+)_\w+@')

    def __init__(self, tasks: List[Dict[str, Any]], global_vars: Dict[str, str]):
        """
        Initialize DependencyAnalyzer.

        Args:
            tasks: List of task dictionaries from task file parser
            global_vars: Dictionary of global variables
        """
        self.tasks = tasks
        self.global_vars = global_vars
        self.dependency_graph = self._build_dependency_graph()

    def _extract_task_references(self, text: str) -> Set[int]:
        """
        Extract task ID references from text.

        Examples:
            "@0_stdout@" -> {0}
            "@1_success@ and @2_exit_code@" -> {1, 2}
            "@GLOBAL_VAR@" -> {} (not a task reference)

        Args:
            text: Text to search for task references

        Returns:
            Set of task IDs referenced
        """
        if not text:
            return set()

        matches = self.TASK_REFERENCE_PATTERN.findall(text)
        return {int(task_id) for task_id in matches}

    def _find_task_dependencies(self, task: Dict[str, Any]) -> Set[int]:
        """
        Find all task dependencies for a given task.

        Searches all task fields for task output references.

        Args:
            task: Task dictionary

        Returns:
            Set of task IDs this task depends on
        """
        dependencies = set()

        # Fields that may contain variable references
        searchable_fields = [
            'hostname', 'command', 'arguments', 'pbrun', 'p7s',
            'success', 'on_success', 'on_failure', 'condition',
            'set_variable', 'loop', 'retry_count', 'timeout'
        ]

        for field in searchable_fields:
            if field in task:
                value = str(task[field])
                dependencies.update(self._extract_task_references(value))

        return dependencies

    def _build_dependency_graph(self) -> Dict[int, Set[int]]:
        """
        Build dependency graph for all tasks.

        Returns:
            Dictionary mapping task_id -> set of task_ids it depends on
        """
        graph = {}

        for task in self.tasks:
            task_id = task.get('task')
            if task_id is None:
                continue

            dependencies = self._find_task_dependencies(task)
            graph[task_id] = dependencies

        return graph

    def get_dependencies(self, task_id: int) -> Set[int]:
        """
        Get dependencies for a specific task.

        Args:
            task_id: Task ID to get dependencies for

        Returns:
            Set of task IDs this task depends on
        """
        return self.dependency_graph.get(task_id, set())

    def can_resume_from(self, resume_task_id: int, executed_tasks: Set[int]) -> Tuple[bool, List[str]]:
        """
        Validate if it's safe to resume from a given task.

        A resume is safe if all tasks that will be executed have their
        dependencies satisfied by the already-executed tasks.

        Args:
            resume_task_id: Task ID to resume from
            executed_tasks: Set of task IDs that were already executed

        Returns:
            Tuple of (is_safe, error_messages)
        """
        errors = []

        # Ensure all task IDs are integers for comparison
        resume_task_id = int(resume_task_id)
        executed_tasks = {int(tid) for tid in executed_tasks}

        # Find all tasks that will be executed (resume_task_id and higher)
        tasks_to_execute = {int(task_id) for task_id in self.dependency_graph.keys()
                           if int(task_id) >= resume_task_id}

        # Check each task that will be executed
        for task_id in sorted(tasks_to_execute):
            dependencies = self.get_dependencies(task_id)

            # Find missing dependencies (required but not executed)
            missing_deps = dependencies - executed_tasks

            if missing_deps:
                # Filter out dependencies that will be executed later
                backward_deps = {dep for dep in missing_deps if dep < resume_task_id}

                if backward_deps:
                    error_msg = "Task {} depends on task(s) {} which were not executed".format(
                        task_id, sorted(backward_deps))
                    errors.append(error_msg)

        return (len(errors) == 0, errors)

    def validate_resume_point(self, resume_task_id: int, execution_path: List[int]) -> Tuple[bool, List[str]]:
        """
        Validate if resuming from a task is safe given an execution path.

        This is the main validation method used during recovery.

        Args:
            resume_task_id: Task ID to resume from
            execution_path: List of tasks that were executed before failure

        Returns:
            Tuple of (is_safe, error_messages)
        """
        executed_tasks = set(execution_path)
        return self.can_resume_from(resume_task_id, executed_tasks)

    def get_task_dependency_info(self, task_id: int) -> Dict[str, Any]:
        """
        Get detailed dependency information for a task.

        Useful for debugging and --show-recovery-info.

        Args:
            task_id: Task ID to get info for

        Returns:
            Dictionary with dependency details
        """
        dependencies = self.get_dependencies(task_id)

        # Find what this task provides (for other tasks)
        dependents = []
        for other_task_id, other_deps in self.dependency_graph.items():
            if task_id in other_deps:
                dependents.append(other_task_id)

        return {
            'task_id': task_id,
            'depends_on': sorted(dependencies),
            'required_by': sorted(dependents),
            'has_dependencies': len(dependencies) > 0,
            'is_dependency': len(dependents) > 0
        }

    def analyze_workflow(self) -> Dict[str, Any]:
        """
        Analyze entire workflow for dependency patterns.

        Returns:
            Dictionary with workflow analysis
        """
        total_tasks = len(self.dependency_graph)
        tasks_with_deps = sum(1 for deps in self.dependency_graph.values() if deps)

        all_dependencies = set()
        for deps in self.dependency_graph.values():
            all_dependencies.update(deps)

        return {
            'total_tasks': total_tasks,
            'tasks_with_dependencies': tasks_with_deps,
            'unique_dependencies': len(all_dependencies),
            'dependency_graph': {k: sorted(v) for k, v in self.dependency_graph.items() if v}
        }
