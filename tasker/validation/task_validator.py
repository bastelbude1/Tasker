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
from .input_sanitizer import InputSanitizer


class TaskValidator:
    def __init__(self):
        """
        Initialize a TaskValidator with default validation state, schemas, and helpers.
        
        Sets up internal state used across parsing and validation, including:
        - debug: Flag to enable debug logging.
        - task_file: Path to the tasks file being validated.
        - tasks: Parsed list of task dictionaries.
        - errors: Collected error messages with context.
        - warnings: Collected warning messages with context.
        - sanitizer: InputSanitizer instance used for security-related checks.
        - skip_security_validation: When True, skip sanitizer checks during validation.
        - global_vars: Mapping of defined global variables (name -> value).
        - referenced_global_vars: Set of global variable names referenced by tasks.
        - required_fields: Fields that every task must include (default: ['task']).
        - conditional_fields: Required fields per task category ('normal', 'return', 'parallel', 'conditional').
        - optional_fields: Fields permitted but not required for tasks.
        - parallel_conditional_specific_fields: Optional fields specific to parallel/conditional tasks (retry-related).
        - valid_next_values: Allowed values for the `next` field, including parallel/conditional-specific semantics.
        - valid_direct_modifiers: Allowed direct modifier names (e.g., min_success).
        - valid_task_types: Recognized composite task types (parallel, conditional).
        - known_delimiters: Supported named delimiters for stdout/stderr splitting.
        - valid_operators: Supported operators for condition expressions.
        """
        self.debug = False # For validation purpose
        self.task_file = None
        self.tasks = []
        self.errors = []
        self.warnings = []

        # Security hardening: Initialize input sanitizer
        self.sanitizer = InputSanitizer()

        # Validation control flags
        self.skip_security_validation = False

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
    def validate_task_file(task_file, debug=False, log_callback=None, debug_callback=None,
                          skip_security_validation=False):
        """
                          Validate the task file at the given path and report parsing and validation results.
                          
                          Parameters:
                              task_file (str): Path to the task file to validate.
                              skip_security_validation (bool): If True, skip pattern-based security checks during validation; other flags control logging/debug output.
                          
                          Returns:
                              dict: Validation summary with keys:
                                  'success' (bool): True if no errors were found, False otherwise.
                                  'errors' (list): List of error messages collected during parsing/validation.
                                  'warnings' (list): List of warning messages collected during parsing/validation.
                                  'global_vars' (dict): Mapping of parsed global variable names to their values.
                                  'tasks' (int): Number of tasks parsed from the file.
                          """
        validator = TaskValidator()
        validator.task_file = task_file
        validator.debug = debug
        validator._log_callback = log_callback
        validator._debug_callback = debug_callback
        validator.skip_security_validation = skip_security_validation

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
            print(f"# DEBUG: TaskValidator: {message}")

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

    def _safe_task_id_from_entry(self, task_entry):
        """
        Safely extract task ID from a task entry tuple.

        Tasks are stored as tuples: (task_dict, line_number)
        This method safely extracts and converts the task ID to an integer,
        handling malformed or non-numeric task IDs gracefully.

        Args:
            task_entry: Tuple of (task_dict, line_number)

        Returns:
            Integer task ID if valid, None otherwise.
        """
        try:
            task_dict = task_entry[0]
            task_id_str = task_dict.get('task', '')

            # Handle task ID already being an int
            if isinstance(task_id_str, int):
                return task_id_str
            # Handle string task IDs - check if numeric before conversion
            elif isinstance(task_id_str, str) and task_id_str.isdigit():
                return int(task_id_str)
            else:
                # Non-numeric or invalid task ID - return None
                return None
        except (ValueError, KeyError, IndexError, TypeError):
            # Handle any unexpected errors gracefully
            return None

    def _check_nested_conditional_or_parallel(self, referenced_task_ids, line_number, task_id):
        """
        Check if any referenced tasks are conditional or parallel tasks (NOT SUPPORTED).

        TASKER does not support nested conditional/parallel tasks. This method validates
        that all referenced task IDs point to regular execution tasks, not to other
        conditional or parallel tasks.

        Args:
            referenced_task_ids: List of task IDs being referenced
            line_number: Line number in task file for error reporting
            task_id: ID of the task doing the referencing

        Side effects:
            Appends errors to self.errors if nested tasks are detected
            Calls self.debug_log with detailed information in DEBUG mode
        """
        for ref_id in referenced_task_ids:
            # Find the referenced task in our parsed tasks (tasks stored as tuples: (task_dict, line_num))
            # Use safe lookup to handle malformed task IDs gracefully
            ref_task = next((t[0] for t in self.tasks if self._safe_task_id_from_entry(t) == ref_id), None)
            if ref_task and 'type' in ref_task:
                ref_type = ref_task.get('type')
                if ref_type in ['conditional', 'parallel']:
                    # Simple error for INFO mode
                    self.errors.append(
                        f"Line {line_number}: Nested conditional/parallel tasks are NOT supported."
                    )
                    # Detailed info for DEBUG mode
                    self.debug_log(
                        f"Task {task_id} references task {ref_id} which is a '{ref_type}' task."
                    )

    def _check_loop_in_subtasks(self, referenced_task_ids, line_number, parent_task_id, parent_type):
        """
        Check if any referenced subtasks have loop parameters (NOT SUPPORTED).

        Loop control (loop, loop_break, next=loop) is ONLY available for sequential tasks.
        Parallel and conditional subtasks cannot use loop parameters - they execute once.

        Args:
            referenced_task_ids: List of task IDs being referenced
            line_number: Line number in task file for error reporting
            parent_task_id: ID of the parent task (parallel/conditional)
            parent_type: Type of parent task ('parallel' or 'conditional')

        Side effects:
            Appends errors to self.errors if loop parameters are detected in subtasks
            Calls self.debug_log with detailed information in DEBUG mode
        """
        for ref_id in referenced_task_ids:
            # Find the referenced task in our parsed tasks
            ref_task = next((t[0] for t in self.tasks if self._safe_task_id_from_entry(t) == ref_id), None)
            if ref_task:
                # Check for any loop-related parameters
                has_loop = 'loop' in ref_task
                has_loop_break = 'loop_break' in ref_task
                has_loop_next = ref_task.get('next') == 'loop'

                if has_loop or has_loop_break or has_loop_next:
                    # Build list of detected loop parameters
                    loop_params = []
                    if has_loop:
                        loop_params.append(f"loop={ref_task['loop']}")
                    if has_loop_break:
                        loop_params.append(f"loop_break={ref_task['loop_break']}")
                    if has_loop_next:
                        loop_params.append("next=loop")

                    params_str = ", ".join(loop_params)

                    # Self-contained error with subtask ID and parameters
                    details = f"subtask {ref_id} ({params_str})"
                    self.errors.append(
                        f"Line {line_number}: Task {parent_task_id} ({parent_type}) references {details}. Loop control is only available for sequential tasks."
                    )

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

                        # SECURITY HARDENING: Sanitize global variable
                        sanitize_result = self.sanitizer.sanitize_global_variable(key, value)

                        # Add any sanitization errors/warnings
                        for error in sanitize_result['errors']:
                            self.errors.append(f"Line {line_number}: Global variable security error")
                            self.debug_log(f"Security validation failed: {error}")
                        for warning in sanitize_result['warnings']:
                            self.warnings.append(f"Line {line_number}: Global variable security warning")
                            self.debug_log(f"Security warning: {warning}")

                        # Only add if sanitization passed
                        if sanitize_result['valid']:
                            self.global_vars[sanitize_result['name']] = sanitize_result['value']
                            global_count += 1
                            self.debug_log(f"Found global variable: {sanitize_result['name']} = {sanitize_result['value']}")
                        else:
                            self.debug_log(f"Rejected global variable due to security validation: {key}")
                            
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

                        # SECURITY HARDENING: Sanitize task ID field
                        sanitize_result = self.sanitizer.sanitize_field('task', value)

                        # Add any sanitization errors/warnings for task ID
                        for error in sanitize_result['errors']:
                            self.errors.append(f"Line {line_number}: Task ID security error")
                            self.debug_log(f"Security validation failed: {error}")
                        for warning in sanitize_result['warnings']:
                            self.warnings.append(f"Line {line_number}: Task ID security warning")
                            self.debug_log(f"Security warning: {warning}")

                        # Start a new task with sanitized or original value
                        task_value = sanitize_result['value'] if sanitize_result['valid'] else value
                        current_task = {'task': task_value, 'line_start': line_number}
                    else:
                        # Add to current task (only if it's a known task field)
                        if current_task is not None:
                            # Check for inline comments in task fields
                            if self.check_for_inline_comments(key, value, line_number):
                                continue  # Skip this field if it has inline comments

                            # Store field first, security validation happens later
                            # This allows exec=shell to be checked before validating command/arguments
                            current_task[key] = value

                            # Store line number for later security validation
                            if 'field_lines' not in current_task:
                                current_task['field_lines'] = {}
                            current_task['field_lines'][key] = line_number

                            self.debug_log(f"{key} = {value}")
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
        """
        Validate all parsed tasks for correctness, references, and structure.
        
        Performs comprehensive validation across all parsed tasks: ensures task IDs are valid and unique, enforces required fields per task type (normal, return, parallel, conditional), performs context-aware security sanitization (unless skip_security_validation is set), validates retry/parallel/conditional-specific configurations, checks global variable references, detects unknown fields, collects task references, performs gap and reachability analysis, and runs final structure-level security checks. Validation results are recorded in self.errors and self.warnings and relevant tracking sets (e.g., referenced tasks, parallel/conditional task sets, referenced_global_vars) are updated.
        
        Returns:
            True if no validation errors were recorded, False otherwise.
        """
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

            # SECURITY VALIDATION: Now that all fields are parsed, validate them
            # Context-aware validation: exec_type determines validation strictness
            if not self.skip_security_validation:
                # Resolve exec placeholders before sanitizing commands
                raw_exec = task.get('exec', 'local')
                resolved_exec = self.resolve_global_variables_for_validation(raw_exec) if raw_exec else ''
                exec_type = (self.clean_field_value(resolved_exec) or 'local').lower()

                # Map common aliases to standard values
                alias_map = {
                    'sh': 'shell',
                    'bash': 'shell',
                    '/bin/sh': 'shell',
                    '/bin/bash': 'shell'
                }
                exec_type = alias_map.get(exec_type, exec_type)

                field_lines = task.get('field_lines', {})

                for field_name in ['command', 'arguments', 'hostname']:
                    if field_name in task:
                        field_value = task[field_name]
                        field_line = field_lines.get(field_name, line_number)

                        # Context-aware security validation
                        # - exec=shell: Allow shell syntax, warn about dangerous patterns
                        # - exec=local: Strict validation (block shell metacharacters)
                        sanitize_result = self.sanitizer.sanitize_field(field_name, field_value, exec_type=exec_type)

                        # Add any sanitization errors/warnings
                        for error in sanitize_result['errors']:
                            self.errors.append(f"Line {field_line}: Task field security error")
                            self.debug_log(f"Security validation failed: {error}")
                        for warning in sanitize_result['warnings']:
                            self.warnings.append(f"Line {field_line}: Task field security warning")
                            self.debug_log(f"Security warning: {warning}")

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
                                  self.optional_fields + self.parallel_conditional_specific_fields +
                                  ['line_start', 'field_lines'])
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

            # SECURITY HARDENING: Validate overall task structure for security issues
            structure_result = self.sanitizer.validate_task_structure(task)
            for error in structure_result['errors']:
                self.errors.append(f"Line {line_number}: Task {task_id} structure error - {error}")
            for warning in structure_result['warnings']:
                self.warnings.append(f"Line {line_number}: Task {task_id} structure warning - {warning}")

        # Check for duplicate task IDs
        duplicate_ids = [id for id in task_ids if list(t[0].get('task') for t in self.tasks).count(str(id)) > 1]
        for id in duplicate_ids:
            self.errors.append(f"Task ID {id} is defined multiple times.")

        # Smart gap validation with hybrid approach
        sorted_task_ids = sorted(task_ids)
        if sorted_task_ids:
            # Build set of all explicitly reachable tasks
            # (via on_success, on_failure, parallel tasks, conditional branch tasks)
            explicitly_reachable = set()
            explicitly_reachable.update(referenced_tasks)
            explicitly_reachable.update(parallel_tasks)
            explicitly_reachable.update(conditional_tasks)

            # Define special task ranges (e.g., cleanup handlers, parallel groups)
            # These are commonly used patterns that shouldn't trigger gap warnings
            special_ranges = [
                (90, 99),    # Common range for cleanup/error handlers
                (100, 999),  # Common range for parallel task groups and special handlers
            ]

            # Check for gaps in the sequence
            for i in range(len(sorted_task_ids) - 1):
                current_id = sorted_task_ids[i]
                next_id = sorted_task_ids[i + 1]

                # If there's a gap between consecutive tasks
                if next_id - current_id > 1:
                    # Check if the next task after the gap is explicitly reachable
                    gap_is_reachable = next_id in explicitly_reachable

                    # Check if current task has explicit routing (breaks sequential flow intentionally)
                    current_task = None
                    for task, _ in self.tasks:
                        if task.get('task') == str(current_id):
                            current_task = task
                            break

                    has_explicit_routing = False
                    if current_task:
                        has_explicit_routing = (
                            'on_success' in current_task or
                            'on_failure' in current_task or
                            'next' in current_task or
                            'return' in current_task
                        )

                    # Check if next task is in a special range
                    in_special_range = any(start <= next_id <= end for start, end in special_ranges)

                    # Only flag gap if:
                    # 1. Next task is NOT explicitly reachable, AND
                    # 2. Current task does NOT have explicit routing, AND
                    # 3. Next task is NOT in special ranges
                    if not gap_is_reachable and not has_explicit_routing and not in_special_range:
                        missing_ids = list(range(current_id + 1, next_id))
                        # Always add concise error message
                        self.errors.append("Task sequence has gaps")
                        # Add detailed debug information
                        self.debug_log(
                            f"Task sequence has gap: Task {current_id} is followed by Task {next_id}. "
                            f"Missing task(s): {missing_ids}. Sequential execution will stop at Task {current_id}."
                        )

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

        # Perform reachability analysis to find orphaned tasks
        self.check_task_reachability(task_ids, referenced_tasks, parallel_tasks, conditional_tasks)

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

                    # CRITICAL: Check for nested conditional/parallel tasks (NOT SUPPORTED)
                    self._check_nested_conditional_or_parallel(referenced_task_ids, line_number, task_id)

                    # CRITICAL: Check for loop parameters in subtasks (NOT SUPPORTED)
                    self._check_loop_in_subtasks(referenced_task_ids, line_number, task_id, 'parallel')

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
        
        # CRITICAL: Both branches MUST be defined for conditional blocks
        # A conditional without both branches defeats the purpose of conditional execution
        has_true_branch = 'if_true_tasks' in task
        has_false_branch = 'if_false_tasks' in task

        # Require BOTH branches to be present
        if not has_true_branch:
            self.errors.append(f"Line {line_number}: Task {task_id} is missing required 'if_true_tasks' field. Conditional blocks must define both true and false branches.")
        if not has_false_branch:
            self.errors.append(f"Line {line_number}: Task {task_id} is missing required 'if_false_tasks' field. Conditional blocks must define both true and false branches.")

        # Validate 'if_true_tasks' field (must be non-empty)
        if has_true_branch:
            self.validate_conditional_task_list(task, task_id, line_number, 'if_true_tasks', conditional_tasks, require_non_empty=True)

        # Validate 'if_false_tasks' field (must be non-empty)
        if has_false_branch:
            self.validate_conditional_task_list(task, task_id, line_number, 'if_false_tasks', conditional_tasks, require_non_empty=True)

    def validate_conditional_task_list(self, task, task_id, line_number, field_name, conditional_tasks, require_non_empty=False):
        """Helper method to validate conditional task lists (if_true_tasks, if_false_tasks)."""
        tasks_str = task.get(field_name, '')

        if not tasks_str.strip():
            # CRITICAL: Empty branches in conditional blocks are now ERRORS, not warnings
            if require_non_empty:
                self.errors.append(f"Line {line_number}: Task {task_id} has empty {field_name} field. Conditional blocks must have at least one task in each branch.")
            else:
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

            # CRITICAL: Check for nested conditional/parallel tasks (NOT SUPPORTED)
            self._check_nested_conditional_or_parallel(referenced_task_ids, line_number, task_id)

            # CRITICAL: Check for loop parameters in subtasks (NOT SUPPORTED)
            self._check_loop_in_subtasks(referenced_task_ids, line_number, task_id, 'conditional')

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

    def check_task_reachability(self, task_ids, referenced_tasks, parallel_tasks, conditional_tasks):
        """Check for unreachable/orphaned tasks using graph traversal."""
        if not task_ids:
            return

        # Build task graph (who can reach whom)
        task_graph = {}
        for task, _ in self.tasks:
            try:
                task_id = int(task.get('task'))
                task_graph[task_id] = set()

                # Add sequential progression (task_id -> task_id + 1)
                # unless task has explicit routing or is special type
                if (task_id + 1 in task_ids and
                    'on_success' not in task and
                    'on_failure' not in task and
                    'return' not in task and
                    task.get('type') not in ['parallel', 'conditional']):
                    task_graph[task_id].add(task_id + 1)

                # Add on_success/on_failure jumps
                if 'on_success' in task:
                    try:
                        target = int(task['on_success'])
                        if target in task_ids:
                            task_graph[task_id].add(target)
                    except ValueError:
                        pass

                if 'on_failure' in task:
                    try:
                        target = int(task['on_failure'])
                        if target in task_ids:
                            task_graph[task_id].add(target)
                    except ValueError:
                        pass

                # Add parallel task references
                if task.get('type') == 'parallel' and 'tasks' in task:
                    tasks_str = task['tasks']
                    for task_ref in tasks_str.split(','):
                        try:
                            ref_id = int(task_ref.strip())
                            if ref_id in task_ids:
                                task_graph[task_id].add(ref_id)
                        except ValueError:
                            pass

                # Add conditional task references
                if task.get('type') == 'conditional':
                    for field in ['if_true_tasks', 'if_false_tasks']:
                        if field in task:
                            tasks_str = task[field]
                            for task_ref in tasks_str.split(','):
                                try:
                                    ref_id = int(task_ref.strip())
                                    if ref_id in task_ids:
                                        task_graph[task_id].add(ref_id)
                                except ValueError:
                                    pass

            except (ValueError, TypeError):
                continue

        # Find starting task (usually task 0, or lowest task ID)
        start_task = min(task_ids) if task_ids else 0

        # Perform breadth-first traversal to find all reachable tasks
        reachable = set()
        queue = [start_task]
        reachable.add(start_task)

        while queue:
            current = queue.pop(0)
            if current in task_graph:
                for next_task in task_graph[current]:
                    if next_task not in reachable:
                        reachable.add(next_task)
                        queue.append(next_task)

        # Find unreachable tasks
        unreachable = task_ids - reachable

        # Special handling: Tasks in special ranges might be intentionally unreachable
        # (e.g., error handlers that are only jumped to via on_failure)
        special_ranges = [(90, 99), (100, 999)]

        for task_id in sorted(unreachable):
            # Check if this task is explicitly referenced somewhere
            is_referenced = (task_id in referenced_tasks or
                           task_id in parallel_tasks or
                           task_id in conditional_tasks)

            # Check if in special range
            in_special_range = any(start <= task_id <= end for start, end in special_ranges)

            if is_referenced:
                # Task is referenced but not reachable from start - this is often intentional
                # (e.g., error handlers)
                if not in_special_range:
                    self.warnings.append(
                        f"Task {task_id} is referenced but not reachable from starting task {start_task}. "
                        f"This may be intentional (e.g., error handler)."
                    )
            else:
                # Task is neither referenced nor reachable - likely an orphan
                self.warnings.append(
                    f"Task {task_id} is unreachable and never referenced. "
                    f"It will never execute. Consider removing it or adding a reference."
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
        """
        Validate the semantic correctness of field values for a single parsed task and record any errors or warnings.
        
        Performs checks and appends human-readable messages to self.errors and self.warnings for issues including:
        - hostname presence (required except for local execution, parallel, or conditional tasks).
        - next field semantics, including special next values, direct modifiers (min_success/max_failed/etc.), loop handling, and condition expressions.
        - condition-style fields: `success`, `condition`, and `loop_break` are validated as condition expressions.
        - command presence and formatting (commands are skipped for parallel and conditional tasks); warns if command contains spaces.
        - task completeness: requires either command+hostname, a `return` value, or being a parallel/conditional task (local exec allowed without hostname).
        - numeric fields: `return`, `loop`, `sleep`, and `timeout` are validated for type and sensible ranges (timeout min/max warnings).
        - on_failure and on_success: must be forward-only numeric task references (no backward jumps).
        - exec: resolves and normalizes execution type and emits a warning for unknown types or unrecognized aliases.
        - stdout_split/stderr_split: must be "delimiter,index"; validates delimiter against known delimiters and index as a non-negative integer.
        
        Parameters:
            task (dict): Parsed task fields mapped to their raw string values.
            task_id (int): Numeric identifier of the task (used for validation context and forward/backward checks).
            line_number (int): Line number in the source file for generating location-aware error/warning messages.
        """

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
                    # Check for invalid numeric next values (task jumping)
                    if next_value.isdigit():
                        self.errors.append(f"Line {line_number}: Task {task_id} has invalid 'next={next_value}'. Direct task jumping is not supported.")
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
                # Forward-only validation: prevent backward jumps to avoid infinite loops
                if on_failure_task <= task_id:
                    self.errors.append(f"Line {line_number}: Task {task_id} 'on_failure' cannot jump backwards to task {on_failure_task} (forward-only rule to prevent infinite loops).")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid 'on_failure' task: '{on_failure_clean}'.")

        # Validate 'on_success' field
        if 'on_success' in task:
            on_success_resolved = self.resolve_global_variables_for_validation(task['on_success'])
            on_success_clean = self.clean_field_value(on_success_resolved)
            try:
                on_success_task = int(on_success_clean)
                # Forward-only validation: prevent backward jumps to avoid infinite loops
                if on_success_task <= task_id:
                    self.errors.append(f"Line {line_number}: Task {task_id} 'on_success' cannot jump backwards to task {on_success_task} (forward-only rule to prevent infinite loops).")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid 'on_success' task: '{on_success_clean}'.")

        # Validate 'loop' field
        if 'loop' in task:
            loop_resolved = self.resolve_global_variables_for_validation(task['loop'])
            loop_clean = self.clean_field_value(loop_resolved)
            try:
                loop_count = int(loop_clean)
                if loop_count < 1:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid loop count: {loop_count}. Must be between 1 and 1000.")
                elif loop_count > 1000:
                    self.errors.append(f"Line {line_number}: Task {task_id} has a loop count that exceeds the maximum: {loop_count}. Maximum allowed is 1000.")
                elif loop_count > 100:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has high loop count: {loop_count}. Consider if this is intentional.")
            except ValueError:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid loop count: '{loop_clean}'. Must be an integer between 1 and 1000.")

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
            # Resolve placeholders and validate exec type
            exec_resolved = self.resolve_global_variables_for_validation(task['exec'])
            exec_clean = self.clean_field_value(exec_resolved).lower()
            valid_exec_types = ['pbrun','p7s','local','wwrs','shell']

            # Common aliases that map to shell (don't warn for these)
            known_aliases = ['sh', 'bash', '/bin/sh', '/bin/bash']

            if exec_clean not in valid_exec_types and exec_clean not in known_aliases:
                self.warnings.append(f"Line {line_number}: Task {task_id} has unknown execution_type: '{exec_clean}'. Valid types are: {','.join(valid_exec_types)} (aliases: sh, bash)")
        
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

        # Check for common invalid condition syntax patterns
        # Pattern 1: exit=X instead of exit_X (equals instead of underscore)
        invalid_exit_equals = re.findall(r'exit=(\d+)', resolved_expression)
        if invalid_exit_equals:
            for code in invalid_exit_equals:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid syntax in {field_name}: 'exit={code}'. Use 'exit_{code}' instead.")

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