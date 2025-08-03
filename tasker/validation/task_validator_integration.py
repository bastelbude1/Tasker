# tasker/validation/task_validator_integration.py
"""
Task Validation Integration
---------------------------
Integration with existing TaskValidator and task dependency validation.
Provides modular, testable components for the TASKER system.
"""

import os
import re

# Import TaskValidator with fallback handling (copied 1:1 from tasker.py)
try:
    from task_validator import TaskValidator
except ImportError:
    TaskValidator = None  # Handle the case where task_validator isn't available


class TaskValidatorIntegration:
    """
    Handles task validation integration and dependency checking for TASKER tasks.
    
    This class provides stateless validation by accepting required
    data (tasks, task_file) as parameters rather than storing state.
    """
    
    @staticmethod
    def validate_tasks(task_file, log_callback=None, debug_callback=None):
        """Validate the task file using TaskValidator."""
        if TaskValidator is None:
            if log_callback:
                log_callback("Warning: TaskValidator not available. Skipping validation.")
            return True

        if log_callback:
            log_callback(f"# Validating task file: {task_file}")

        try:
            # Create a validator instance
            validator = TaskValidator(task_file)

            # Run validation
            if validator.parse_file():
                validator.validate_tasks()

            # Get validation results
            has_errors = len(validator.errors) > 0

            # Log validation results
            if has_errors:
                if log_callback:
                    log_callback("# Task validation FAILED.")
                for error in validator.errors:
                    if debug_callback:
                        debug_callback(f"# ERROR: {error}")

                # Also log warnings
                if validator.warnings:
                    for warning in validator.warnings:
                        if debug_callback:
                            debug_callback(f"# WARNING: {warning}")
                return False

            else:
                if log_callback:
                    log_callback("# Task validation passed successfully.")
                # Log any warnings

                if validator.warnings:
                    for warning in validator.warnings:
                        if debug_callback:
                            debug_callback(f"# WARNING: {warning}")
                return True

        except Exception as e:
            if log_callback:
                log_callback(f"Error during task validation: {str(e)}")
            return False

    @staticmethod
    def validate_task_dependencies(tasks, log_callback=None):
        """Validate that task dependencies can be resolved given the execution flow."""
        dependency_issues = []
        pattern = r'@(\d+)_(stdout|stderr|success)@'
        
        for task_id, task in tasks.items():
            # Check condition dependencies
            if 'condition' in task:
                matches = re.findall(pattern, task['condition'])
                for dep_task_str, _ in matches:
                    dep_task = int(dep_task_str)
                    if dep_task not in tasks:
                        dependency_issues.append(f"Task {task_id} condition references non-existent Task {dep_task}")
                    elif dep_task >= task_id:
                        dependency_issues.append(f"Task {task_id} condition references future Task {dep_task} - this may cause execution issues")
            
            # Check argument dependencies
            if 'arguments' in task:
                matches = re.findall(pattern, task['arguments'])
                for dep_task_str, _ in matches:
                    dep_task = int(dep_task_str)
                    if dep_task not in tasks:
                        dependency_issues.append(f"Task {task_id} arguments reference non-existent Task {dep_task}")
                    elif dep_task >= task_id:
                        dependency_issues.append(f"Task {task_id} arguments reference future Task {dep_task} - this may cause execution issues")
        
        if dependency_issues:
            if log_callback:
                log_callback("# WARNING: Task dependency issues detected:")
            for issue in dependency_issues:
                if log_callback:
                    log_callback(f"#   {issue}")
            if log_callback:
                log_callback("# These may cause tasks to be skipped due to unresolved dependencies.")
            return False
        else:
            if log_callback:
                log_callback("# Task dependency validation passed.")
            return True

    @staticmethod
    def validate_start_from_task(start_task_id, tasks, log_callback=None):
        """Validate and provide warnings for --start-from usage."""
        if start_task_id not in tasks:
            available_tasks = sorted(tasks.keys())
            if log_callback:
                log_callback(f"ERROR: Start task {start_task_id} not found")
                log_callback(f"Available task IDs: {available_tasks}")
            return False
    
        # Check for potential dependency issues
        dependency_warnings = []
        pattern = r'@(\d+)_(stdout|stderr|success)@'
    
        for task_id in range(start_task_id, max(tasks.keys()) + 1):
            if task_id not in tasks:
                continue
            
            task = tasks[task_id]
            for field_name, field_value in task.items():
                if isinstance(field_value, str):
                    matches = re.findall(pattern, field_value)
                    for dep_task_str, dep_type in matches:
                        dep_task = int(dep_task_str)
                        if dep_task < start_task_id:
                            dependency_warnings.append(
                                f"Task {task_id} field '{field_name}' references @{dep_task}_{dep_type}@ (before start point)"
                            )
    
        if dependency_warnings:
            if log_callback:
                log_callback(f"# DEPENDENCY WARNINGS for --start-from {start_task_id}:")
            for warning in dependency_warnings[:5]:  # Limit to first 5 warnings
                if log_callback:
                    log_callback(f"#   {warning}")
            if len(dependency_warnings) > 5:
                if log_callback:
                    log_callback(f"#   ... and {len(dependency_warnings) - 5} more dependency issues")
            if log_callback:
                log_callback(f"# These tasks may fail due to unresolved variable references")
        
        return True