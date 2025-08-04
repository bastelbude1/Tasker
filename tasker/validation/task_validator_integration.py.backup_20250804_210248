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
    def validate_tasks(task_file, execution_context):
        """Validate the task file using ExecutionContext."""
        if TaskValidator is None:
            execution_context.log("Warning: TaskValidator not available. Skipping validation.")
            return True

        execution_context.log(f"# Validating task file: {task_file}")

        try:
            # Create a validator instance
            validator = TaskValidator(task_file)

            # Parse the file first
            if not validator.parse_file():
                execution_context.log("# Task validation FAILED - could not parse file.")
                for error in validator.errors:
                    execution_context.log_debug(f"# ERROR: {error}")
                return False

            # Run validation
            validation_success = validator.validate_tasks()

            if not validation_success or validator.errors:
                execution_context.log("# Task validation FAILED.")
                # Log each error
                for error in validator.errors:
                    execution_context.log_debug(f"# ERROR: {error}")
                return False
            else:
                # Log warnings if any
                if validator.warnings:
                    for warning in validator.warnings:
                        execution_context.log_debug(f"# WARNING: {warning}")

                # Validation passed
                execution_context.log("# Task validation passed successfully.")
                
                # Log warnings again for visibility (optional)
                if validator.warnings:
                    for warning in validator.warnings:
                        execution_context.log_debug(f"# WARNING: {warning}")
                
                return True

        except Exception as e:
            execution_context.log(f"Error during task validation: {str(e)}")
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
        
        if log_callback:
            log_callback(f"# Start-from validation: Starting from task {start_task_id}")
            log_callback(f"# WARNING: Tasks before {start_task_id} will be skipped")
            
            # Check for potential dependency issues
            skipped_tasks = [tid for tid in tasks.keys() if tid < start_task_id]
            if skipped_tasks:
                log_callback(f"# Skipped tasks: {sorted(skipped_tasks)}")
                log_callback(f"# CAUTION: Task {start_task_id} may fail if it depends on skipped tasks")
        
        return True