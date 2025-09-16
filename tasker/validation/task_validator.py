# tasker/validation/task_validator.py
"""
Task Configuration Validator - Enhanced with Parallel Task Support, Retry Logic, and CONDITIONAL TASKS
---------------------------
This module validates task configuration files to ensure they are correctly formatted
and all required fields are present with valid values.
Enhanced with support for global variables using @VARIABLE@ syntax, variable chaining,
unused variable warnings, inline comment detection, PARALLEL TASKS, RETRY LOGIC, and CONDITIONAL TASKS.
"""
import os
import re


class TaskValidator:
    def __init__(self):
        self.debug = False # For validation purpose
        self.task_file = None
        self.tasks = []
        self.errors = []
        self.warnings = []
        
        # Global variables support
        self.global_vars = {}  # Store global variables for validation
        self.referenced_global_vars = set()  # Track which global variables are used
        
        # Define required and optional fields for tasks
        self.required_fields = ['task']
        self.conditional_fields = {
            'normal': ['hostname', 'command'],
            'return': ['return'],
            'parallel': ['type', 'tasks'],  # Parallel tasks need type and tasks
            'conditional': ['type', 'condition']  # NEW: Conditional tasks need type and condition
        }
        self.optional_fields = [
            'arguments', 'next', 'stdout_split', 'stderr_split',
            'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure', 'on_success', 'success', 'condition', 'exec', 'timeout',
            'type', 'max_parallel', 'tasks',  # Parallel task fields
            'if_true_tasks', 'if_false_tasks'  # NEW: Conditional task fields
        ]
        
        # NEW: Parallel and Conditional-specific optional fields (including retry)
        self.parallel_conditional_specific_fields = [
            'retry_failed', 'retry_count', 'retry_delay'
        ]
        
        # Valid values for certain fields - SIMPLIFIED
        self.valid_next_values = [
            'always', 'never', 'loop', 'success',
            # Parallel and Conditional-specific next conditions  
            'all_success', 'any_success', 'majority_success'
        ]
        
        # Valid direct modifiers (no partial_success prefix needed)
        self.valid_direct_modifiers = ['min_success', 'max_failed', 'min_failed', 'max_success']
        
        # Valid task types - NEW: Added 'conditional'
        self.valid_task_types = ['parallel', 'conditional']
        
        # Known split delimiters
        self.known_delimiters = ['space', 'tab', 'semi', 'comma', 'pipe']
        
        # Enhanced operator support
        self.valid_operators = ['!=', '!~', '<=', '>=', '=', '~', '<', '>']

    @staticmethod
    def validate_task_file(task_file, debug=False, log_callback=None, debug_callback=None):
        """
        Validate a task file and return results.
        
        Args:
            task_file: Path to task file to validate
            debug: Enable debug mode
            log_callback: Optional function for main logging
            debug_callback: Optional function for debug logging
            
        Returns:
            dict with 'success', 'errors', 'warnings', 'global_vars', 'tasks'
        """
        validator = TaskValidator()
        validator.task_file = task_file
        validator.debug = debug
        validator._log_callback = log_callback
        validator._debug_callback = debug_callback
        
        # Parse and validate
        parse_success = validator.parse_file()
        if parse_success:
            validator.validate_tasks()
            
        return {
            'success': len(validator.errors) == 0,
            'errors': validator.errors[:],  # Copy the list
            'warnings': validator.warnings[:],  # Copy the list
            'global_vars': validator.global_vars.copy(),
            'tasks': len(validator.tasks)
        }

    def debug_log(self, message):
        """ Log a debug message if debug mode is enabled"""
        if self.debug and hasattr(self, '_debug_callback') and self._debug_callback:
            self._debug_callback(f"TaskValidator: {message}")
        elif self.debug:
            print(f"# DEBUG: {message}")

    def check_for_inline_comments(self, key, value, line_number):
        """Check if a field value contains inline comments and flag as error."""
        if '#' in value:
            # Check if there's content after # that looks like a comment
            hash_pos = value.find('#')
            before_hash = value[:hash_pos].rstrip()
            after_hash = value[hash_pos:].strip()
            
            # If there's whitespace before # and content after, it's likely a comment
            if len(before_hash) < len(value[:hash_pos]) and after_hash:
                self.errors.append(
                    f"Line {line_number}: Field '{key}' contains inline comment: '{value}'. "
                    f"Use separate comment lines starting with # instead."
                )
                return True
        return False

    def resolve_global_variables_for_validation(self, text):
        """Resolve global variables in text for validation purposes only."""
        if not text or '@' not in text:
            return text
            
        # Only resolve global variables, not task result variables
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'
        
        def replace_var(match):
            var_name = match.group(1)
            # Skip task result variables (e.g., @0_stdout@)
            task_var_pattern = r'\d+_(stdout|stderr|success)$'
            if re.match(task_var_pattern, var_name):
                return match.group(0)  # Return unchanged
            # Replace with global variable value if defined
            if var_name in self.global_vars:
                return self.global_vars[var_name]
            else:
                return match.group(0)  # Return unchanged if not defined
        
        # Replace global variables
        resolved = re.sub(global_var_pattern, replace_var, text)
        
        # Handle nested variables (variable chaining) - max 5 iterations to prevent infinite loops
        for _ in range(5):
            new_resolved = re.sub(global_var_pattern, replace_var, resolved)
            if new_resolved == resolved:
                break  # No more changes
            resolved = new_resolved
            
        return resolved

    def clean_field_value(self, value):
        """Clean field value by removing extra whitespace only."""
        if not isinstance(value, str):
            return value
        return value.strip()

    def parse_file(self):
        """Parse the task file into global variables and individual tasks."""
        if not os.path.exists(self.task_file):
            self.errors.append(f"Task file '{self.task_file}' not found.")
            return False
        try:
            with open(self.task_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            self.errors.append(f"Error reading task file: {str(e)}")
            return False

        # PHASE 1: Parse global variables (first pass)
        self.debug_log("Parsing global variables...")
        global_count = 0
        
        for line_number, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            # Parse key=value pairs
            if '=' in line and not line.startswith('task='):
                try:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Check if this is a global variable (not a known task field)
                    known_task_fields = [
                        'hostname', 'command', 'arguments', 'next', 'stdout_split', 'stderr_split',
                        'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure', 
                        'on_success', 'success', 'condition', 'exec', 'timeout', 'return',
                        'type', 'max_parallel', 'tasks',  # Parallel task fields
                        'if_true_tasks', 'if_false_tasks'  # NEW: Conditional task fields
                    ] + self.parallel_conditional_specific_fields  # Add retry fields
                    
                    if key not in known_task_fields:
                        # Check for inline comments in global variables
                        if self.check_for_inline_comments(key, value, line_number):
                            continue  # Skip this global variable if it has inline comments
                            
                        # Validate global variable name
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                            self.errors.append(f"Line {line_number}: Invalid global variable name '{key}'. Must start with letter/underscore and contain only letters, numbers, underscores.")
                        else:
                            self.global_vars[key] = value
                            global_count += 1
                            self.debug_log(f"Found global variable: {key} = {value}")
                            
                except Exception as e:
                    self.errors.append(f"Line {line_number}: Error parsing global variable: {str(e)}")
        
        self.debug_log(f"Parsed {global_count} global variables")

        # PHASE 2: Parse tasks (existing logic with minor updates)
        current_task = None
        line_number = 0
        
        for line in lines:
            line_number += 1
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value pairs
            if '=' in line:
                try:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Check if this is a new task definition
                    if key == 'task':
                        # Save the previous task if it exists
                        if current_task is not None:
                            self.tasks.append((current_task, current_task.get('line_start', line_number)))
                        # Start a new task
                        current_task = {'task': value, 'line_start': line_number}
                    else:
                        # Add to current task (only if it's a known task field)
                        if current_task is not None:
                            # Check for inline comments in task fields
                            if self.check_for_inline_comments(key, value, line_number):
                                continue  # Skip this field if it has inline comments
                            current_task[key] = value
                        else:
                            # Only warn if it's not a global variable
                            if key not in self.global_vars:
                                self.warnings.append(f"Line {line_number}: Key '{key}' found outside of a task definition.")
                except Exception as e:
                    self.errors.append(f"Line {line_number}: Error parsing line: {str(e)}")
            else:
                self.warnings.append(f"Line {line_number}: Line does not contain a key=value pair: '{line}'")
        
        # Add the last task if it exists
        if current_task is not None:
            self.tasks.append((current_task, current_task.get('line_start', line_number)))

        return len(self.errors) == 0

    def validate_tasks(self):
        """Validate all tasks for correctness including global variable references, parallel tasks, conditional tasks, and retry logic."""
        if not self.tasks:
            self.errors.append("No tasks found in the file.")
            return False

        task_ids = set()
        referenced_tasks = set()
        parallel_tasks = set()  # Track tasks referenced by parallel tasks
        conditional_tasks = set()  # NEW: Track tasks referenced by conditional tasks

        for task, line_number in self.tasks:

            # Ensure task has a task ID
            if 'task' not in task:
                self.errors.append(f"Line {line_number}: Missing required field 'task'.")

            # Check that task ID is an integer
            task_id = task.get('task')
            try:
                task_id = int(task_id)
                if task_id < 0 or task_id >= 1000:
                    self.warnings.append(f"Line {line_number}: Task ID {task_id} should be between 0 and 999.")
                task_ids.add(task_id)
            except ValueError:
                self.errors.append(f"Line {line_number}: Task ID '{task_id}' is not an integer.")

            # Determine task type (normal, return, parallel, or conditional)
            task_type = 'normal'
            if 'return' in task:
                task_type = 'return'
            elif 'type' in task and task['type'] == 'parallel':
                task_type = 'parallel'
            elif 'type' in task and task['type'] == 'conditional':  # NEW: Conditional task detection
                task_type = 'conditional'

            # Check for required fields based on task type
            for field in self.required_fields:
                if field not in task:
                    self.errors.append(f"Line {line_number}: Task {task_id} is missing required field '{field}'.")

            # Check for conditional required fields based on task type
            for field in self.conditional_fields[task_type]:
                if field not in task:
                    self.errors.append(f"Line {line_number}: Task {task_id} ({task_type} type) is missing required field '{field}'.")

            # Check for unknown fields
            all_known_fields = set(self.required_fields + self.conditional_fields['normal'] +
                                  self.conditional_fields['return'] + self.conditional_fields['parallel'] + 
                                  self.conditional_fields['conditional'] +  # NEW: Add conditional fields
                                  self.optional_fields + self.parallel_conditional_specific_fields + ['line_start'])
            for field in task:
                if field not in all_known_fields:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has unknown field '{field}'.")

            # NEW: Check for retry fields in non-parallel/non-conditional tasks
            self.validate_retry_field_usage(task, task_id, task_type, line_number)

            # Validate specific field values
            self.validate_field_values(task, task_id, line_number)

            # Validate parallel task specific fields
            if task_type == 'parallel':
                self.validate_parallel_task(task, task_id, line_number, parallel_tasks)
                # NEW: Validate retry configuration for parallel tasks
                self.validate_retry_configuration(task, task_id, line_number)

            # NEW: Validate conditional task specific fields
            if task_type == 'conditional':
                self.validate_conditional_task(task, task_id, line_number, conditional_tasks)
                # NEW: Validate retry configuration for conditional tasks
                self.validate_retry_configuration(task, task_id, line_number)

            # Validate global variable references
            self.validate_global_variable_references(task, task_id, line_number)

            # Collect referenced tasks
            self.collect_referenced_tasks(task, referenced_tasks)

        # Check for duplicate task IDs
        duplicate_ids = [id for id in task_ids if list(t[0].get('task') for t in self.tasks).count(str(id)) > 1]
        for id in duplicate_ids:
            self.errors.append(f"Task ID {id} is defined multiple times.")

        # Check for missing but referenced tasks
        missing_refs = referenced_tasks - task_ids
        for ref in missing_refs:
            self.errors.append(f"Task {ref} is referenced but not defined.")

        # Check for missing parallel-referenced tasks
        missing_parallel_refs = parallel_tasks - task_ids
        for ref in missing_parallel_refs:
            self.errors.append(f"Task {ref} is referenced by parallel task but not defined.")

        # NEW: Check for missing conditional-referenced tasks
        missing_conditional_refs = conditional_tasks - task_ids
        for ref in missing_conditional_refs:
            self.errors.append(f"Task {ref} is referenced by conditional task but not defined.")

        # Check for unused global variables
        self.check_unused_global_variables()

        return len(self.errors) == 0

    def validate_retry_field_usage(self, task, task_id, task_type, line_number):
        """NEW: Validate that retry fields are only used with parallel or conditional tasks."""
        retry_fields_found = []
        
        for field in self.parallel_conditional_specific_fields:
            if field in task:
                retry_fields_found.append(field)
        
        if retry_fields_found and task_type not in ['parallel', 'conditional']:  # NEW: Allow conditional tasks
            fields_str = ', '.join(retry_fields_found)
            self.warnings.append(
                f"Line {line_number}: Task {task_id} uses retry field(s) '{fields_str}' but is not a parallel or conditional task. "
                f"Retry logic only applies to parallel and conditional tasks."
            )

    def validate_retry_configuration(self, task, task_id, line_number):
        """NEW: Validate retry configuration for parallel and conditional tasks."""
        has_retry_failed = 'retry_failed' in task
        has_retry_count = 'retry_count' in task
        has_retry_delay = 'retry_delay' in task
        
        # If any retry field is present, validate the configuration
        if has_retry_failed or has_retry_count or has_retry_delay:
            
            # Validate retry_failed field
            if has_retry_failed:
                retry_failed_value = task['retry_failed'].lower().strip()
                if retry_failed_value not in ['true', 'false']:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid retry_failed value '{task['retry_failed']}'. Must be 'true' or 'false'.")
                
                # If retry is enabled, check for consistency
                if retry_failed_value == 'true':
                    if not has_retry_count:
                        self.warnings.append(f"Line {line_number}: Task {task_id} has retry_failed=true but no retry_count specified. Will use default (1).")
                    if not has_retry_delay:
                        self.warnings.append(f"Line {line_number}: Task {task_id} has retry_failed=true but no retry_delay specified. Will use default (1).")
            
            # Validate retry_count field
            if has_retry_count:
                try:
                    retry_count_resolved = self.resolve_global_variables_for_validation(task['retry_count'])
                    retry_count = int(retry_count_resolved)
                    if retry_count < 0:
                        self.errors.append(f"Line {line_number}: Task {task_id} has negative retry_count: {retry_count}")
                    elif retry_count > 10:
                        self.warnings.append(f"Line {line_number}: Task {task_id} has high retry_count: {retry_count}. Maximum recommended is 10.")
                    elif retry_count == 0:
                        self.warnings.append(f"Line {line_number}: Task {task_id} has retry_count=0. This effectively disables retry.")
                except ValueError:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid retry_count: '{task['retry_count']}'. Must be an integer.")
            
            # Validate retry_delay field
            if has_retry_delay:
                try:
                    retry_delay_resolved = self.resolve_global_variables_for_validation(task['retry_delay'])
                    retry_delay = int(retry_delay_resolved)
                    if retry_delay < 0:
                        self.errors.append(f"Line {line_number}: Task {task_id} has negative retry_delay: {retry_delay}")
                    elif retry_delay > 300:
                        self.warnings.append(f"Line {line_number}: Task {task_id} has high retry_delay: {retry_delay}s. Maximum recommended is 300.")
                except ValueError:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid retry_delay: '{task['retry_delay']}'. Must be an integer.")
            
            # Warn about incomplete retry configuration
            if (has_retry_count or has_retry_delay) and not has_retry_failed:
                self.warnings.append(
                    f"Line {line_number}: Task {task_id} has retry_count/retry_delay but no retry_failed field. "
                    f"These fields are ignored unless retry_failed=true."
                )

    def validate_parallel_task(self, task, task_id, line_number, parallel_tasks):
        """Validate parallel task specific fields."""
        
        # Validate 'type' field
        if 'type' in task:
            task_type = task['type']
            if task_type not in self.valid_task_types:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid type '{task_type}'. Valid types: {', '.join(self.valid_task_types)}")
        
        # Validate 'max_parallel' field
        if 'max_parallel' in task:
            try:
                max_parallel = int(task['max_parallel'])
                if max_parallel < 1:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid max_parallel '{max_parallel}'. Must be >= 1.")
                elif max_parallel > 20:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has high max_parallel '{max_parallel}'. Consider resource limits.")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid max_parallel '{task['max_parallel']}'. Must be an integer.")
        
        # Validate 'tasks' field
        if 'tasks' in task:
            tasks_str = task['tasks']
            if not tasks_str.strip():
                self.errors.append(f"Line {line_number}: Task {task_id} has empty tasks field.")
            else:
                try:
                    # Parse comma-separated task IDs
                    referenced_task_ids = []
                    for task_ref in tasks_str.split(','):
                        task_ref = task_ref.strip()
                        if task_ref:
                            ref_id = int(task_ref)
                            referenced_task_ids.append(ref_id)
                            parallel_tasks.add(ref_id)
                    
                    if len(referenced_task_ids) == 0:
                        self.errors.append(f"Line {line_number}: Task {task_id} has no valid task references in tasks field.")
                    
                    # Check for self-reference
                    if task_id in referenced_task_ids:
                        self.errors.append(f"Line {line_number}: Task {task_id} cannot reference itself in parallel tasks.")
                    
                    # Check max_parallel vs number of tasks
                    if 'max_parallel' in task:
                        max_parallel = int(task['max_parallel'])
                        if len(referenced_task_ids) < max_parallel:
                            self.warnings.append(f"Line {line_number}: Task {task_id} has max_parallel ({max_parallel}) greater than number of tasks ({len(referenced_task_ids)}).")
                            
                except ValueError as e:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid task reference in tasks field: {str(e)}")

    def validate_conditional_task(self, task, task_id, line_number, conditional_tasks):
        """NEW: Validate conditional task specific fields."""
        
        # Validate 'type' field
        if 'type' in task:
            task_type = task['type']
            if task_type not in self.valid_task_types:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid type '{task_type}'. Valid types: {', '.join(self.valid_task_types)}")
        
        # Validate 'condition' field (required for conditional tasks)
        if 'condition' not in task:
            self.errors.append(f"Line {line_number}: Task {task_id} is missing required 'condition' field for conditional task.")
        else:
            # Use existing condition validation
            self.validate_condition_expression(task['condition'], 'condition', task_id, line_number)
        
        # Validate that at least one branch is defined
        has_true_branch = 'if_true_tasks' in task
        has_false_branch = 'if_false_tasks' in task
        
        if not has_true_branch and not has_false_branch:
            self.errors.append(f"Line {line_number}: Task {task_id} has no task branches defined. At least one of 'if_true_tasks' or 'if_false_tasks' is required.")
        
        # Validate 'if_true_tasks' field
        if has_true_branch:
            self.validate_conditional_task_list(task, task_id, line_number, 'if_true_tasks', conditional_tasks)
        
        # Validate 'if_false_tasks' field
        if has_false_branch:
            self.validate_conditional_task_list(task, task_id, line_number, 'if_false_tasks', conditional_tasks)

    def validate_conditional_task_list(self, task, task_id, line_number, field_name, conditional_tasks):
        """Helper method to validate conditional task lists (if_true_tasks, if_false_tasks)."""
        tasks_str = task.get(field_name, '')
        
        if not tasks_str.strip():
            self.warnings.append(f"Line {line_number}: Task {task_id} has empty {field_name} field.")
            return
        
        try:
            # Parse comma-separated task IDs
            referenced_task_ids = []
            for task_ref in tasks_str.split(','):
                task_ref = task_ref.strip()
                if task_ref:
                    ref_id = int(task_ref)
                    referenced_task_ids.append(ref_id)
                    conditional_tasks.add(ref_id)
            
            if len(referenced_task_ids) == 0:
                self.errors.append(f"Line {line_number}: Task {task_id} has no valid task references in {field_name} field.")
            
            # Check for self-reference
            if task_id in referenced_task_ids:
                self.errors.append(f"Line {line_number}: Task {task_id} cannot reference itself in {field_name}.")
                
        except ValueError as e:
            self.errors.append(f"Line {line_number}: Task {task_id} has invalid task reference in {field_name} field: {str(e)}")

    def validate_global_variable_references(self, task, task_id, line_number):
        """Validate that all global variable references (@VARIABLE@) are defined and track usage."""
        
        # Pattern to match @VARIABLE@ but exclude @X_stdout@, @X_stderr@, @X_success@
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'
        task_result_pattern = r'@(\d+)_(stdout|stderr|success)@'
        
        # Check all string fields in the task
        for field_name, field_value in task.items():
            if isinstance(field_value, str) and '@' in field_value:
                
                # Find all potential global variable references
                global_matches = re.findall(global_var_pattern, field_value)
                
                for var_name in global_matches:
                    # Skip if this is actually a task result variable pattern
                    task_var_pattern = r'\d+_(stdout|stderr|success)$'
                    if re.match(task_var_pattern, var_name):
                        continue
                    
                    # Track usage of this global variable
                    self.referenced_global_vars.add(var_name)
                    
                    # Check if the global variable is defined
                    if var_name not in self.global_vars:
                        self.errors.append(
                            f"Line {line_number}: Task {task_id} field '{field_name}' references "
                            f"undefined global variable '@{var_name}@'. "
                            f"Define it as: {var_name}=value"
                        )
                        
                # Also validate that task result references are properly formatted
                task_result_matches = re.findall(task_result_pattern, field_value)
                for task_num, output_type in task_result_matches:
                    try:
                        ref_task = int(task_num)
                        # This will be validated later in collect_referenced_tasks
                    except ValueError:
                        self.errors.append(
                            f"Line {line_number}: Task {task_id} field '{field_name}' has "
                            f"invalid task reference '@{task_num}_{output_type}@'"
                        )

    def check_unused_global_variables(self):
        """Check for global variables that are defined but never used."""
        unused_vars = set(self.global_vars.keys()) - self.referenced_global_vars
        
        if unused_vars:
            unused_list = sorted(unused_vars)
            self.warnings.append(f"Found {len(unused_vars)} unused global variable(s): {', '.join(unused_list)}")
            for var in unused_list:
                self.warnings.append(f"  Unused global variable: {var} = {self.global_vars[var]}")

    def validate_field_values(self, task, task_id, line_number):
        """Validate the values of specific fields in a task."""

        # Check that hostname has a value if it exists (except for local execution, parallel, and conditional tasks)
        if 'hostname' in task:
            # Skip hostname validation for parallel and conditional tasks
            if task.get('type') not in ['parallel', 'conditional']:  # NEW: Skip conditional tasks
                hostname_resolved = self.resolve_global_variables_for_validation(task['hostname'])
                if not hostname_resolved or hostname_resolved == '':
                    # Check if this is not local execution
                    exec_resolved = self.resolve_global_variables_for_validation(task.get('exec', ''))
                    if exec_resolved != 'local':
                        self.errors.append(f"Line {line_number}: Task {task_id} has empty hostname but execution type requires one.")

        # Validate 'next' field - simplified syntax for parallel and conditional tasks
        if 'next' in task:
            next_value = task['next']
            is_parallel_or_conditional = task.get('type') in ['parallel', 'conditional']  # NEW: Include conditional
            
            # Handle direct modifiers (min_success=N, max_failed=N, etc.)
            if '=' in next_value and next_value.split('=')[0] in self.valid_direct_modifiers:
                if not is_parallel_or_conditional:  # NEW: Allow for both parallel and conditional
                    self.errors.append(f"Line {line_number}: Task {task_id} uses parallel/conditional-specific next condition '{next_value}' but is not a parallel or conditional task.")
                else:
                    self.validate_direct_modifier_condition(next_value, task_id, line_number)
            else:
                # Check for standard special values
                special_value_found = None
                for special in self.valid_next_values:
                    if next_value == special:
                        special_value_found = special
                        break
                
                if special_value_found:
                    # Handle backwards compatibility for 'success' in parallel/conditional tasks
                    if special_value_found == 'success' and is_parallel_or_conditional:
                        self.warnings.append(f"Line {line_number}: Task {task_id} uses 'next=success' in {task.get('type', 'parallel/conditional')} task. Consider using 'all_success' for clarity. Will be treated as 'all_success'.")
                    
                    # Parallel/Conditional-specific validations
                    elif special_value_found in ['all_success', 'any_success', 'majority_success'] and not is_parallel_or_conditional:
                        self.errors.append(f"Line {line_number}: Task {task_id} uses parallel/conditional-specific next condition '{special_value_found}' but is not a parallel or conditional task.")
                    
                    # For 'loop', ensure loop field exists
                    elif next_value == 'loop' and 'loop' not in task:
                        self.errors.append(f"Line {line_number}: Task {task_id} uses 'next=loop' but has no 'loop' count defined.")
                else:
                    # Not a special value, validate as condition expression
                    self.validate_condition_expression(next_value, 'next', task_id, line_number)

        # Validate 'success' field
        if 'success' in task:
            success_value = task['success']
            self.validate_condition_expression(success_value, 'success', task_id, line_number)

        # Validate 'condition' field
        if 'condition' in task:
            condition_value = task['condition']
            self.validate_condition_expression(condition_value, 'condition', task_id, line_number)

        # Validate 'loop_break' field
        if 'loop_break' in task:
            loop_break_value = task['loop_break']
            self.validate_condition_expression(loop_break_value, 'loop_break', task_id, line_number)

        # Validate 'command' field (skip for parallel and conditional tasks)
        if 'command' in task and task.get('type') not in ['parallel', 'conditional']:  # NEW: Skip conditional tasks
            command_resolved = self.resolve_global_variables_for_validation(task['command'])
            command_clean = self.clean_field_value(command_resolved)
            if command_clean == '':
                self.errors.append(f"Line {line_number}: Task {task_id} has empty command value.")
            if ' ' in command_clean:
                self.warnings.append(f"Line {line_number}: Task {task_id} has spaces in command: '{command_clean}'. Use the 'arguments' field for arguments")

        # Check that we have either command+hostname OR return OR parallel type OR conditional type
        has_command = 'command' in task and self.resolve_global_variables_for_validation(task['command']).strip()
        has_hostname = 'hostname' in task and self.resolve_global_variables_for_validation(task['hostname']).strip()
        has_return = 'return' in task
        is_parallel = task.get('type') == 'parallel'
        is_conditional = task.get('type') == 'conditional'  # NEW: Check for conditional
        
        # Special case for local execution (doesn't need hostname)
        exec_resolved = self.resolve_global_variables_for_validation(task.get('exec', ''))
        is_local_exec = self.clean_field_value(exec_resolved) == 'local'

        valid_task = (has_return or is_parallel or is_conditional or (has_command and (has_hostname or is_local_exec)))  # NEW: Include conditional

        if not valid_task:
            self.errors.append(f"Line {line_number}: Task {task_id} must have either a command+hostname, a return value, or be a parallel/conditional task.")

        # Validate 'return' field
        if 'return' in task:
            return_resolved = self.resolve_global_variables_for_validation(task['return'])
            return_clean = self.clean_field_value(return_resolved)
            try:
                return_code = int(return_clean)
                if return_code < 0:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has negative return code: {return_code}")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid return code: '{return_clean}'.")

        # Validate 'on_failure' field
        if 'on_failure' in task:
            on_failure_resolved = self.resolve_global_variables_for_validation(task['on_failure'])
            on_failure_clean = self.clean_field_value(on_failure_resolved)
            try:
                on_failure_task = int(on_failure_clean)
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid 'on_failure' task: '{on_failure_clean}'.")

        # Validate 'on_success' field
        if 'on_success' in task:
            on_success_resolved = self.resolve_global_variables_for_validation(task['on_success'])
            on_success_clean = self.clean_field_value(on_success_resolved)
            try:
                on_success_task = int(on_success_clean)
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid 'on_success' task: '{on_success_clean}'.")

        # Validate 'loop' field
        if 'loop' in task:
            loop_resolved = self.resolve_global_variables_for_validation(task['loop'])
            loop_clean = self.clean_field_value(loop_resolved)
            try:
                loop_count = int(loop_clean)
                if loop_count < 0:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has negative loop count: {loop_count}")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid loop count: '{loop_clean}'.")

            # Critical validation: loop parameter requires next=loop to function
            if 'next' not in task or task['next'] != 'loop':
                self.errors.append(f"Line {line_number}: Task {task_id} has 'loop' parameter but missing 'next=loop'. Loops require 'next=loop' to function.")

        # Validate 'sleep' field
        if 'sleep' in task:
            sleep_resolved = self.resolve_global_variables_for_validation(task['sleep'])
            sleep_clean = self.clean_field_value(sleep_resolved)
            try:
                sleep_time = float(sleep_clean)
                if sleep_time < 0:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has negative sleep time: {sleep_time}")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid sleep time: '{sleep_clean}'.")

        # Validate 'timeout' field
        if 'timeout' in task:
            timeout_resolved = self.resolve_global_variables_for_validation(task['timeout'])
            timeout_clean = self.clean_field_value(timeout_resolved)
            try:
                timeout = int(timeout_clean)
                if timeout < 5:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has timeout {timeout} less than minimum (5)")
                elif timeout > 1000:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has timeout {timeout} greater than maximum (1000)")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid timeout: '{timeout_clean}'.")
        
        if 'exec' in task:
            exec_resolved = self.resolve_global_variables_for_validation(task['exec'])
            exec_clean = self.clean_field_value(exec_resolved)
            valid_exec_types = ['pbrun','p7s','local','wwrs']
            if exec_clean not in valid_exec_types:
                self.warnings.append(f"Line {line_number}: Task {task_id} has unknown execution_type: '{exec_clean}'. Valid types are: {','.join(valid_exec_types)}")
        
        # Validate split specifications
        for split_field in ['stdout_split', 'stderr_split']:
            if split_field in task:
                split_resolved = self.resolve_global_variables_for_validation(task[split_field])
                split_clean = self.clean_field_value(split_resolved)
                parts = split_clean.split(',')
                if len(parts) != 2:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid {split_field} format: '{split_clean}'. Should be 'delimiter,index'.")
                else:
                    delimiter, index = parts
                    if delimiter not in self.known_delimiters and not self.is_valid_custom_delimiter(delimiter):
                        self.warnings.append(f"Line {line_number}: Task {task_id} uses unknown delimiter: '{delimiter}' in {split_field}.")
                    try:
                        index_val = int(index)
                        if index_val < 0:
                            self.warnings.append(f"Line {line_number}: Task {task_id} has negative index: {index_val} in {split_field}.")
                    except ValueError:
                        self.errors.append(f"Line {line_number}: Task {task_id} has invalid index: '{index}' in {split_field}.")

    def validate_direct_modifier_condition(self, condition, task_id, line_number):
        """Validate direct modifier condition (min_success=N, max_failed=N, etc.)."""
        # Example: min_success=2, max_failed=1
        
        if '=' not in condition:
            self.errors.append(f"Line {line_number}: Task {task_id} has invalid modifier condition: '{condition}'. Format: 'modifier=value'")
            return
            
        key, value = condition.split('=', 1)
        
        if key not in self.valid_direct_modifiers:
            self.errors.append(f"Line {line_number}: Task {task_id} has unknown modifier: '{key}'. Valid: {self.valid_direct_modifiers}")
            return
            
        try:
            int_value = int(value)
            if int_value < 0:
                self.errors.append(f"Line {line_number}: Task {task_id} has negative value in modifier: '{condition}'")
            elif int_value == 0 and key in ['min_success', 'min_failed']:
                self.warnings.append(f"Line {line_number}: Task {task_id} has zero value for '{key}' - this might always be true")
        except ValueError:
            self.errors.append(f"Line {line_number}: Task {task_id} has invalid integer in modifier: '{condition}'")

    def validate_condition_expression(self, expression, field_name, task_id, line_number):
        """Enhanced condition validation with global variable support."""
        if not expression:
            self.errors.append(f"Line {line_number}: Task {task_id} has empty {field_name} condition.")
            return
            
        # Clean the expression (remove extra whitespace)
        expression_clean = self.clean_field_value(expression)
        
        # Check for balanced parentheses
        if expression_clean.count('(') != expression_clean.count(')'):
            self.errors.append(f"Line {line_number}: Task {task_id} has unbalanced parentheses in {field_name}: '{expression_clean}'")
            return
        
        # Check for basic syntax issues
        if expression_clean.startswith(('&', '|')) or expression_clean.endswith(('&', '|')):
            self.errors.append(f"Line {line_number}: Task {task_id} has invalid {field_name} syntax: '{expression_clean}'")
            return
        
        # Check for double operators
        for op in ['&&', '||']:
            if op in expression_clean:
                self.errors.append(f"Line {line_number}: Task {task_id} has double operator in {field_name}: '{expression_clean}'")
                return
        
        # Validate global variable references in conditions
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'
        global_matches = re.findall(global_var_pattern, expression_clean)
        
        for var_name in global_matches:
            # Skip task result variables
            task_var_pattern = r'\d+_(stdout|stderr|success)$'
            if re.match(task_var_pattern, var_name):
                continue
                
            # Track usage
            self.referenced_global_vars.add(var_name)
            
            # Check if defined
            if var_name not in self.global_vars:
                self.errors.append(
                    f"Line {line_number}: Task {task_id} {field_name} condition references "
                    f"undefined global variable '@{var_name}@'"
                )
        
        # For validation purposes, try to resolve global variables to check syntax
        resolved_expression = self.resolve_global_variables_for_validation(expression_clean)
        
        # Check for valid exit code patterns in the resolved expression
        exit_conditions = re.findall(r'exit_(\d+)', resolved_expression)
        for exit_code in exit_conditions:
            try:
                code = int(exit_code)
                if code > 255:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has unusual exit code in {field_name}: exit_{code}")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid exit code in {field_name}: exit_{exit_code}")

    def is_valid_custom_delimiter(self, delimiter):
        """Check if a custom delimiter is valid."""
        # A valid custom delimiter is a non-empty string
        return delimiter and isinstance(delimiter, str)

    def collect_referenced_tasks(self, task, referenced_tasks):
        """Collect task IDs that are referenced in variables and on_failure/on_success fields."""
        # Check for @X_stdout@, @X_stderr@, or @X_success@ references
        for key, value in task.items():
            if isinstance(value, str):
                for match in re.finditer(r'@(\d+)_(stdout|stderr|success)@', value):
                    try:
                        ref_task = int(match.group(1))  
                        referenced_tasks.add(ref_task)
                    except ValueError:
                        pass
        # Check for on_failure references
        if 'on_failure' in task:
            try:
                on_failure_task = int(task['on_failure'])
                referenced_tasks.add(on_failure_task)
            except ValueError:
                pass

        # Check for on_success references
        if 'on_success' in task:
            try:
                on_success_task = int(task['on_success'])
                referenced_tasks.add(on_success_task)
            except ValueError:
                pass