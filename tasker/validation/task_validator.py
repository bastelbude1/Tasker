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
from ..core.constants import MAX_VARIABLE_EXPANSION_DEPTH


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
        self.strict_env_validation = False  # Require TASKER_ prefix for env vars

        # Global variables support
        self.global_vars = {}  # Store global variables for validation
        self.referenced_global_vars = set()  # Track which global variables are used
        
        # Define required and optional fields for tasks
        self.required_fields = ['task']
        self.conditional_fields = {
            'normal': ['hostname', 'command'],
            'return': ['return'],
            'parallel': ['type', 'tasks'],  # Parallel tasks need type and tasks
            'conditional': ['type', 'condition'],  # NEW: Conditional tasks need type and condition
            'decision': ['type']  # Decision blocks only need type (success/failure checked separately)
        }
        self.optional_fields = [
            'arguments', 'next', 'stdout_split', 'stderr_split',
            'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure', 'on_success', 'success', 'failure', 'condition', 'exec', 'timeout',
            'type', 'max_parallel', 'tasks',  # Parallel task fields
            'if_true_tasks', 'if_false_tasks'  # NEW: Conditional task fields
        ]
        
        # NEW: Parallel and Conditional-specific optional fields (including retry)
        self.parallel_conditional_specific_fields = [
            'retry_failed', 'retry_count', 'retry_delay'
        ]

        # Known task field names (used for global variable validation)
        # Defined once here to avoid re-allocation during parsing
        self.known_task_fields = [
            'hostname', 'command', 'arguments', 'next', 'stdout_split', 'stderr_split',
            'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure',
            'on_success', 'success', 'condition', 'exec', 'timeout', 'return',
            'type', 'max_parallel', 'tasks',  # Parallel task fields
            'if_true_tasks', 'if_false_tasks',  # NEW: Conditional task fields
            *self.parallel_conditional_specific_fields  # Add retry fields
        ]

        # Valid values for certain fields - SIMPLIFIED
        self.valid_next_values = [
            'always', 'never', 'loop', 'success',
            # Parallel and Conditional-specific next conditions
            'all_success', 'any_success', 'majority_success'
        ]
        
        # Valid direct modifiers (no partial_success prefix needed)
        self.valid_direct_modifiers = ['min_success', 'max_failed', 'min_failed', 'max_success']
        
        # Valid task types - NEW: Added 'conditional' and 'decision'
        self.valid_task_types = ['parallel', 'conditional', 'decision']
        
        # Known split delimiters (aligned with evaluator)
        self.known_delimiters = ['space', 'tab', 'semi', 'semicolon', 'comma', 'pipe', 'newline', 'colon']
        
        # Enhanced operator support
        self.valid_operators = ['!=', '!~', '<=', '>=', '=', '~', '<', '>']

    @staticmethod
    def parse_global_vars_only(task_file, strict_env_validation=False, log_callback=None, debug_callback=None):
        """
        Parse ONLY global variables from task file with environment variable expansion and sanitization.

        IMPORTANT: This method performs BOTH env var expansion AND security sanitization.
        Malicious global variables are rejected to prevent command injection attacks.

        This method is used by TaskExecutor during parsing phase to centralize
        environment variable expansion and sanitization logic.

        Parameters:
            task_file (str): Path to the task file to parse.
            strict_env_validation (bool): If True, require TASKER_ prefix for env vars.
            log_callback (function): Optional callback for logging expansion messages.
            debug_callback (function): Optional callback for debug logging.

        Returns:
            dict: Parsing result with keys:
                'success' (bool): True if parsing succeeded, False if validation/sanitization failed.
                'errors' (list): List of error messages (strict validation and security errors).
                'global_vars' (dict): Mapping of parsed global variable names to sanitized expanded values.
        """
        global_vars = {}
        errors = []

        if not os.path.exists(task_file):
            errors.append(f"Task file '{task_file}' not found")
            return {'success': False, 'errors': errors, 'global_vars': {}}

        with open(task_file, 'r') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Skip file-defined arguments
            if line.startswith(('-', '--')):
                continue

            # Stop at first task definition
            task_match = re.match(r'^\s*task\s*=\s*(.*)', line)
            if task_match:
                break

            # Parse global variable definitions
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Skip task field names
                known_task_fields = (
                    'task', 'hostname', 'command', 'arguments', 'next', 'stdout_split', 'stderr_split',
                    'stdout_count', 'stderr_count', 'sleep', 'loop', 'loop_break', 'on_failure',
                    'on_success', 'success', 'failure', 'condition', 'exec', 'timeout', 'return',
                    'type', 'max_parallel', 'tasks', 'retry_failed', 'retry_count', 'retry_delay',
                    'if_true_tasks', 'if_false_tasks'
                )
                if key in known_task_fields:
                    continue

                # Store original value for comparison
                original_value = value

                # Expand environment variables
                expanded_value = os.path.expandvars(value)

                # Strict validation: Check for TASKER_ prefix requirement
                if strict_env_validation and '$' in value:
                    # Extract all environment variable references from the value
                    # Match either ${VAR} or $VAR, but not mismatched combinations like ${VAR or $VAR}
                    # Using alternation pattern to ensure proper brace pairing
                    env_var_matches = re.findall(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)', value)
                    # Flatten the tuple results (one group will be empty for each match)
                    env_vars_in_value = [var for match in env_var_matches for var in match if var]

                    for env_var in env_vars_in_value:
                        if not env_var.startswith('TASKER_'):
                            errors.append(
                                f"Line {line_num}: Strict environment variable validation failed for global variable '{key}'. "
                                f"Environment variable '${env_var}' does not start with required prefix 'TASKER_'. "
                                f"Either use TASKER_-prefixed variables or disable --strict-env-validation flag."
                            )
                            # Early return on strict validation failure
                            return {'success': False, 'errors': errors, 'global_vars': {}}

                # Log expansion if value changed (avoid leaking secrets in logs)
                if expanded_value != original_value and log_callback:
                    # Log only that expansion happened, not the actual values
                    log_callback(f"# Global variable {key}: environment variable expansion applied")
                    if debug_callback:
                        debug_callback(f"#   Original length: {len(original_value)}")
                        debug_callback(f"#   Expanded length: {len(expanded_value)}")

                # CRITICAL SECURITY: Sanitize expanded global variable
                # This prevents command injection and other security vulnerabilities
                sanitizer = InputSanitizer()
                sanitize_result = sanitizer.sanitize_global_variable(key, expanded_value)

                # Check for sanitization errors
                if not sanitize_result['valid']:
                    for error in sanitize_result['errors']:
                        errors.append(f"Line {line_num}: Global variable security error: {error}")
                    # Skip this global variable - do not store it
                    continue

                # Store sanitized value (not the raw expanded value)
                global_vars[key] = sanitize_result['value']

        # Return success=False if any errors were accumulated during parsing
        return {
            'success': len(errors) == 0,
            'errors': errors,
            'global_vars': global_vars
        }

    @staticmethod
    def validate_task_file(task_file, debug=False, log_callback=None, debug_callback=None,
                          skip_security_validation=False, skip_subtask_range_validation=False,
                          strict_env_validation=False):
        """
                          Validate the task file at the given path and report parsing and validation results.

                          Parameters:
                              task_file (str): Path to the task file to validate.
                              skip_security_validation (bool): If True, skip pattern-based security checks.
                              skip_subtask_range_validation (bool): If True, suppress recommended subtask ID range warnings.
                              strict_env_validation (bool): If True, require TASKER_ prefix for environment variables in global variable definitions.

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
        validator.skip_subtask_range_validation = skip_subtask_range_validation
        validator.strict_env_validation = strict_env_validation

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
            # Skip task result variables (e.g., @0_stdout@, @0_exit@)
            # CASE INSENSITIVE: Accept @0_STDOUT@, @0_stdout@, etc.
            task_var_pattern = r'\d+_(stdout|stderr|success|exit)$'
            if re.match(task_var_pattern, var_name, re.IGNORECASE):
                return match.group(0)  # Return unchanged
            # Replace with global variable value if defined
            if var_name in self.global_vars:
                return self.global_vars[var_name]
            else:
                return match.group(0)  # Return unchanged if not defined
        
        # Replace global variables
        resolved = re.sub(global_var_pattern, replace_var, text)

        # Handle nested variables (variable chaining) - max iterations to prevent infinite loops
        for _ in range(MAX_VARIABLE_EXPANSION_DEPTH):
            new_resolved = re.sub(global_var_pattern, replace_var, resolved)
            if new_resolved == resolved:
                break  # No more changes
            if '@' not in new_resolved:
                resolved = new_resolved
                break  # No more variables to expand - early exit optimization
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

    def _check_nested_conditional_or_parallel(self, referenced_task_ids, line_number, task_id, parent_type):
        """
        Check if any referenced tasks are conditional or parallel tasks (NOT SUPPORTED).

        TASKER does not support nested conditional/parallel tasks. This method validates
        that all referenced task IDs point to regular execution tasks, not to other
        conditional or parallel tasks.

        Args:
            referenced_task_ids: List of task IDs being referenced
            line_number: Line number in task file for error reporting
            task_id: ID of the task doing the referencing
            parent_type: Type of parent task ('parallel' or 'conditional')

        Side effects:
            Appends errors to self.errors if nested tasks are detected
        """
        for ref_id in referenced_task_ids:
            # Find the referenced task in our parsed tasks (tasks stored as tuples: (task_dict, line_num))
            # Use safe lookup to handle malformed task IDs gracefully
            ref_task = next((t[0] for t in self.tasks if self._safe_task_id_from_entry(t) == ref_id), None)
            if ref_task and 'type' in ref_task:
                ref_type = ref_task.get('type')
                if ref_type in ['conditional', 'parallel']:
                    # Self-contained error with parent type, subtask ID, and subtask type
                    details = f"subtask {ref_id} ({ref_type})"
                    self.errors.append(
                        f"Line {line_number}: Task {task_id} ({parent_type}) references {details}. Nested conditional/parallel tasks are NOT supported."
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
                # Note: next=loop is handled by _check_routing_in_subtasks to avoid duplicate errors
                has_loop = 'loop' in ref_task
                has_loop_break = 'loop_break' in ref_task

                if has_loop or has_loop_break:
                    # Build list of detected loop parameters
                    loop_params = []
                    if has_loop:
                        loop_params.append(f"loop={ref_task['loop']}")
                    if has_loop_break:
                        loop_params.append(f"loop_break={ref_task['loop_break']}")

                    params_str = ", ".join(loop_params)

                    # Self-contained error with subtask ID and parameters
                    details = f"subtask {ref_id} ({params_str})"
                    self.errors.append(
                        f"Line {line_number}: Task {parent_task_id} ({parent_type}) references {details}. Loop control is only available for sequential tasks."
                    )

    def _check_routing_in_subtasks(self, referenced_task_ids, line_number, parent_task_id, parent_type):
        """
        Check if any referenced subtasks have routing parameters (NOT SUPPORTED).

        Routing control (on_success, on_failure, next) is NOT available for subtasks in
        parallel or conditional blocks. These blocks must maintain control flow to aggregate
        results and perform Multi-Task Success Evaluation.

        Args:
            referenced_task_ids: List of task IDs being referenced
            line_number: Line number in task file for error reporting
            parent_task_id: ID of the parent task (parallel/conditional)
            parent_type: Type of parent task ('parallel' or 'conditional')

        Side effects:
            Appends errors to self.errors if routing parameters are detected in subtasks
            Calls self.debug_log with detailed information in DEBUG mode
        """
        for ref_id in referenced_task_ids:
            # Find the referenced task in our parsed tasks
            ref_task = next((t[0] for t in self.tasks if self._safe_task_id_from_entry(t) == ref_id), None)
            if ref_task:
                # Check for routing parameters
                has_on_success = 'on_success' in ref_task
                has_on_failure = 'on_failure' in ref_task
                has_next = 'next' in ref_task

                if has_on_success or has_on_failure or has_next:
                    # Build list of detected routing parameters
                    routing_params = []
                    if has_on_success:
                        routing_params.append(f"on_success={ref_task['on_success']}")
                    if has_on_failure:
                        routing_params.append(f"on_failure={ref_task['on_failure']}")
                    if has_next:
                        routing_params.append(f"next={ref_task['next']}")

                    params_str = ", ".join(routing_params)

                    # Self-contained error with subtask ID and parameters
                    details = f"subtask {ref_id} ({params_str})"
                    self.errors.append(
                        f"Line {line_number}: Task {parent_task_id} ({parent_type}) references {details}. "
                        f"Subtasks cannot have routing parameters - control must return to the {parent_type} block for Multi-Task Success Evaluation. "
                        f"Use decision blocks if individual task routing is needed."
                    )

                    # Provide additional guidance in debug mode
                    self.debug_log(
                        f"Task {ref_id}: Routing parameters break {parent_type} block control flow. "
                        f"The {parent_type} block needs to aggregate all subtask results and evaluate success conditions. "
                        f"If you need individual task routing, use decision blocks instead of {parent_type} blocks."
                    )

    def _check_subtask_id_ranges(self, referenced_task_ids, line_number, parent_task_id, parent_type):
        """
        Check if referenced subtasks follow recommended ID range conventions.

        RECOMMENDATION (not error): Subtasks should be in a distinct ID range to clearly
        separate them from the main sequential workflow. This improves readability and debugging.

        Recommended convention for task N:
        - Subtasks in range [N*100, (N+1)*100-1]
        - Example: Task 1 subtasks should be 100-199
        - Example: Task 2 subtasks should be 200-299

        Alternative: Subtasks should have clear separation (gap of at least 10) from main flow.

        Args:
            referenced_task_ids: List of task IDs being referenced
            line_number: Line number in task file for error reporting
            parent_task_id: ID of the parent task (parallel/conditional)
            parent_type: Type of parent task ('parallel' or 'conditional')

        Side effects:
            Appends warnings to self.warnings if ID ranges don't follow convention
            Can be skipped with --skip-subtask-range-validation flag
        """
        # Skip if validation is disabled
        if hasattr(self, 'skip_subtask_range_validation') and self.skip_subtask_range_validation:
            return

        # Calculate recommended range for this parent task
        recommended_min = parent_task_id * 100
        recommended_max = (parent_task_id + 1) * 100 - 1

        # Skip range validation if it would exceed conventional task ID limits
        if recommended_max > 999:
            self.debug_log(
                f"Task {parent_task_id}: Skipping subtask ID range validation "
                f"(recommended range {recommended_min}-{recommended_max} exceeds conventional limit of 999). "
                f"Consider using lower parent task IDs for blocks with subtasks."
            )
            return

        # Check if all subtasks are in recommended range
        out_of_range_tasks = []
        for ref_id in referenced_task_ids:
            if not (recommended_min <= ref_id <= recommended_max):
                out_of_range_tasks.append(ref_id)

        if out_of_range_tasks:
            # Build helpful warning message
            self.warnings.append(
                f"Line {line_number}: Task {parent_task_id} ({parent_type}) references subtasks {out_of_range_tasks} "
                f"outside recommended range [{recommended_min}-{recommended_max}]. "
                f"Consider using distinct ID ranges to clearly separate subtasks from main workflow. "
                f"Use --skip-subtask-range-validation to suppress this warning."
            )

            # Provide additional guidance in debug mode
            self.debug_log(
                f"Task {parent_task_id}: Subtask ID convention helps distinguish main flow from {parent_type} subtasks. "
                f"Recommended: Task N subtasks in range [N*100, (N+1)*100-1]. "
                f"This makes workflows more readable and easier to debug."
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
            self.errors.append(f"Error reading task file: {type(e).__name__}: {e}")
            return False

        # PHASE 1: Parse global variables (first pass)
        # Delegate to centralized parse_global_vars_only() to avoid code duplication
        self.debug_log("Parsing global variables...")

        # Call the static method that handles env var expansion, strict validation, and sanitization
        parse_result = TaskValidator.parse_global_vars_only(
            self.task_file,
            strict_env_validation=self.strict_env_validation,
            log_callback=self._log_callback,
            debug_callback=self._debug_callback if self.debug else None
        )

        # Handle parsing errors (strict validation or sanitization failures)
        if not parse_result['success']:
            for error in parse_result['errors']:
                self.errors.append(error)

        # Use the sanitized and validated global variables
        self.global_vars = parse_result['global_vars']

        self.debug_log(f"Parsed {len(self.global_vars)} global variables")

        # PHASE 2: Parse tasks (existing logic with minor updates)
        current_task = None
        line_number = 0
        
        for line in lines:
            line_number += 1
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Skip file-defined arguments (lines starting with - or --)
            # These are processed by tasker.py CLI parser, not part of task file content
            if line.startswith(('-', '--')):
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
            elif 'type' in task and task['type'] == 'decision':  # NEW: Decision block detection
                task_type = 'decision'

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
                                  self.conditional_fields['decision'] +  # Add decision fields
                                  self.optional_fields + self.parallel_conditional_specific_fields +
                                  ['line_start', 'field_lines'])
            for field in task:
                if field not in all_known_fields:
                    self.warnings.append(f"Line {line_number}: Task {task_id} has unknown field '{field}'.")

            # Check for retry fields in non-parallel/non-conditional tasks
            self.validate_retry_field_usage(task, task_id, task_type, line_number)

            # Validate specific field values
            self.validate_field_values(task, task_id, line_number)

            # Validate parallel task specific fields
            if task_type == 'parallel':
                self.validate_parallel_task(task, task_id, line_number, parallel_tasks)
                # Validate retry configuration for parallel tasks
                self.validate_retry_configuration(task, task_id, line_number)

            # Validate conditional task specific fields
            if task_type == 'conditional':
                self.validate_conditional_task(task, task_id, line_number, conditional_tasks)
                # Validate retry configuration for conditional tasks
                self.validate_retry_configuration(task, task_id, line_number)

            # Validate decision block specific fields
            if task_type == 'decision':
                self.validate_decision_task(task, task_id, line_number)

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

        # Check for duplicate task IDs (robust detection with normalized IDs)
        id_counts = {}
        for t in self.tasks:
            sid = self._safe_task_id_from_entry(t)
            if sid is not None:
                id_counts[sid] = id_counts.get(sid, 0) + 1
        for id_val, count in id_counts.items():
            if count > 1:
                self.errors.append(f"Task ID {id_val} is defined multiple times.")

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
        
        if retry_fields_found and task_type not in ['parallel', 'conditional']:  # Allow parallel and conditional tasks only
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
        # SIMPLIFIED: retry_failed is now optional - retry_count >= 1 automatically enables retry
        if has_retry_count or has_retry_delay:

            # Validate retry_count field
            if has_retry_count:
                try:
                    retry_count_resolved = self.resolve_global_variables_for_validation(task['retry_count'])
                    retry_count = int(retry_count_resolved)
                    if retry_count < 1:
                        self.errors.append(f"Line {line_number}: Task {task_id} has invalid retry_count: {retry_count}. Must be between 1 and 1000.")
                    elif retry_count > 1000:
                        self.errors.append(f"Line {line_number}: Task {task_id} has a retry_count that exceeds the maximum: {retry_count}. Maximum allowed is 1000.")
                    elif retry_count > 100:
                        self.warnings.append(f"Line {line_number}: Task {task_id} has high retry_count: {retry_count}. Consider if this is intentional.")
                except ValueError:
                    self.errors.append(f"Line {line_number}: Task {task_id} has invalid retry_count: '{task['retry_count']}'. Must be an integer between 1 and 1000.")
            
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

    def validate_parallel_task(self, task, task_id, line_number, parallel_tasks):
        """Validate parallel task specific fields."""

        # Validate 'type' field
        if 'type' in task:
            task_type = task['type']
            if task_type not in self.valid_task_types:
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid type '{task_type}'. Valid types: {', '.join(self.valid_task_types)}")

        # CRITICAL: Parallel blocks cannot use failure parameter (only for sequential tasks)
        # But they CAN use success parameter with aggregate conditions for flexible routing
        if 'failure' in task:
            self.errors.append(
                f"Line {line_number}: Task {task_id} (parallel) cannot use 'failure' parameter. "
                f"Use aggregate conditions like 'max_failed' in 'next' parameter instead."
            )

        # CRITICAL: Parallel blocks cannot use timeout parameter
        # Parallel blocks coordinate execution but don't run commands themselves
        if 'timeout' in task:
            # Concise error for INFO level
            self.errors.append(
                f"Line {line_number}: Task {task_id} (parallel) cannot use 'timeout' parameter."
            )
            # Detailed explanation for DEBUG level
            self.debug_log(
                "Parallel blocks coordinate execution but don't run commands. "
                "Set timeout on individual child tasks instead."
            )

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
                    self._check_nested_conditional_or_parallel(referenced_task_ids, line_number, task_id, 'parallel')

                    # CRITICAL: Check for loop parameters in subtasks (NOT SUPPORTED)
                    self._check_loop_in_subtasks(referenced_task_ids, line_number, task_id, 'parallel')

                    # CRITICAL: Check for routing parameters in subtasks (NOT SUPPORTED)
                    self._check_routing_in_subtasks(referenced_task_ids, line_number, task_id, 'parallel')

                    # RECOMMENDATION: Check subtask ID ranges follow convention
                    self._check_subtask_id_ranges(referenced_task_ids, line_number, task_id, 'parallel')

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

        # CRITICAL: Conditional blocks cannot use failure parameter (only for sequential tasks)
        # But they CAN use success parameter with aggregate conditions for flexible routing
        if 'failure' in task:
            self.errors.append(
                f"Line {line_number}: Task {task_id} (conditional) cannot use 'failure' parameter. "
                f"Use aggregate conditions like 'max_failed' in 'next' parameter instead."
            )

        # CRITICAL: Conditional blocks cannot use timeout parameter
        # Conditional blocks coordinate execution but don't run commands themselves
        if 'timeout' in task:
            # Concise error for INFO level
            self.errors.append(
                f"Line {line_number}: Task {task_id} (conditional) cannot use 'timeout' parameter."
            )
            # Detailed explanation for DEBUG level
            self.debug_log(
                "Conditional blocks coordinate execution but don't run commands. "
                "Set timeout on individual child tasks instead."
            )

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
            self._check_nested_conditional_or_parallel(referenced_task_ids, line_number, task_id, 'conditional')

            # CRITICAL: Check for loop parameters in subtasks (NOT SUPPORTED)
            self._check_loop_in_subtasks(referenced_task_ids, line_number, task_id, 'conditional')

            # CRITICAL: Check for routing parameters in subtasks (NOT SUPPORTED)
            self._check_routing_in_subtasks(referenced_task_ids, line_number, task_id, 'conditional')

            # RECOMMENDATION: Check subtask ID ranges follow convention
            self._check_subtask_id_ranges(referenced_task_ids, line_number, task_id, 'conditional')

        except ValueError as e:
            self.errors.append(f"Line {line_number}: Task {task_id} has invalid task reference in {field_name} field: {str(e)}")

    def validate_decision_task(self, task, task_id, line_number):
        """Validate decision block specific fields."""

        # Validate 'type' field
        if 'type' in task:
            task_type = task['type']
            if task_type != 'decision':
                self.errors.append(f"Line {line_number}: Task {task_id} has invalid type '{task_type}'. Expected 'decision'.")

        # Decision blocks must have at least success= OR failure= defined
        has_success = 'success' in task and task['success'].strip()
        has_failure = 'failure' in task and task['failure'].strip()

        if not has_success and not has_failure:
            self.errors.append(f"Line {line_number}: Task {task_id} is a decision block but has neither 'success' nor 'failure' conditions defined. At least one is required.")

        # Validate mutual exclusion: success and failure cannot coexist (consistent with other blocks)
        if has_success and has_failure:
            self.errors.append(
                f"Line {line_number}: Task {task_id} cannot use 'success' and 'failure' together. "
                "Use either 'success' for positive conditions OR 'failure' for inverse conditions, not both."
            )

        # Validate success condition if present
        if has_success:
            self.validate_condition_expression(task['success'], 'success', task_id, line_number)

        # Validate failure condition if present
        if has_failure:
            self.validate_condition_expression(task['failure'], 'failure', task_id, line_number)

        # Decision blocks should NOT have command or hostname
        if 'command' in task:
            self.errors.append(f"Line {line_number}: Task {task_id} is a decision block and should not have a 'command' field.")

        if 'hostname' in task:
            self.errors.append(f"Line {line_number}: Task {task_id} is a decision block and should not have a 'hostname' field.")

        if 'arguments' in task:
            self.errors.append(f"Line {line_number}: Task {task_id} is a decision block and should not have an 'arguments' field.")

        # Decision blocks must not specify timeout (no execution occurs)
        if 'timeout' in task:
            self.errors.append(f"Line {line_number}: Task {task_id} is a decision block and cannot use 'timeout'.")

        # Exec type is irrelevant for decision blocks; warn to avoid confusion
        if 'exec' in task:
            self.warnings.append(f"Line {line_number}: Task {task_id} is a decision block; 'exec' is ignored.")

        # Output splitting/counting fields are meaningless on decision blocks; warn
        for field in ['stdout_split', 'stderr_split', 'stdout_count', 'stderr_count']:
            if field in task:
                self.warnings.append(f"Line {line_number}: Task {task_id} is a decision block; '{field}' has no effect and will be ignored.")

        # Flow control validation is handled by validate_field_values
        # Just check that at least one flow control field is present
        has_flow_control = any(field in task for field in ['on_success', 'on_failure', 'next'])
        if not has_flow_control:
            self.warnings.append(f"Line {line_number}: Task {task_id} is a decision block without explicit flow control (on_success, on_failure, or next). Will continue to next sequential task.")

    def validate_global_variable_references(self, task, task_id, line_number):
        """Validate that all global variable references (@VARIABLE@) are defined and track usage."""
        
        # Pattern to match @VARIABLE@ but exclude @X_stdout@, @X_stderr@, @X_success@
        # CASE INSENSITIVE: Accept @0_STDOUT@, @0_stdout@, etc.
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'
        task_result_pattern = r'@(\d+)_(stdout|stderr|success|exit)@'

        # Check all string fields in the task
        for field_name, field_value in task.items():
            if isinstance(field_value, str) and '@' in field_value:

                # Find all potential global variable references
                # Note: global_var_pattern already excludes @X_output@ patterns since it requires
                # the variable name to start with a letter or underscore, not a digit
                global_matches = re.findall(global_var_pattern, field_value)

                for var_name in global_matches:
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
                task_result_matches = re.findall(task_result_pattern, field_value, re.IGNORECASE)
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

        # CRITICAL: Validate that 'next' and 'on_success'/'on_failure' are mutually exclusive
        if 'next' in task:
            if 'on_success' in task or 'on_failure' in task:
                conflicting_fields = []
                if 'on_success' in task:
                    conflicting_fields.append('on_success')
                if 'on_failure' in task:
                    conflicting_fields.append('on_failure')
                self.errors.append(
                    f"Line {line_number}: Task {task_id} cannot use 'next' together with {', '.join(conflicting_fields)}. "
                    "Use either 'next' for conditional flow OR 'on_success'/'on_failure' for explicit routing, not both."
                )

        # Flexible routing: on_success and on_failure can be used independently
        # Pattern 1: on_failure ONLY → success continues to next task, failure jumps to handler
        # Pattern 2: on_success ONLY → success jumps to target, failure exits with code 10
        # Pattern 3: BOTH → explicit routing for all outcomes
        has_on_success = 'on_success' in task
        has_on_failure = 'on_failure' in task

        # Validate on_success target if present
        if has_on_success:
            try:
                on_success_target = int(task['on_success'])
                if on_success_target < 0 or on_success_target > 9999:
                    self.errors.append(
                        f"Line {line_number}: Task {task_id} has invalid 'on_success' target: {on_success_target}"
                    )
            except (ValueError, TypeError):
                self.errors.append(
                    f"Line {line_number}: Task {task_id} has invalid 'on_success' value: '{task['on_success']}'"
                )

        # Validate on_failure target if present
        if has_on_failure:
            try:
                on_failure_target = int(task['on_failure'])
                if on_failure_target < 0 or on_failure_target > 9999:
                    self.errors.append(
                        f"Line {line_number}: Task {task_id} has invalid 'on_failure' target: {on_failure_target}"
                    )
            except (ValueError, TypeError):
                self.errors.append(
                    f"Line {line_number}: Task {task_id} has invalid 'on_failure' value: '{task['on_failure']}'"
                )

        # Skip success/failure validation for decision blocks (handled in validate_decision_task)
        if task.get('type') != 'decision':
            # Validate 'success' field
            if 'success' in task:
                success_value = task['success']
                # For parallel/conditional blocks, validate as multi-task condition
                if task.get('type') in ['parallel', 'conditional']:
                    # Check if it's a valid multi-task evaluation condition
                    self.validate_direct_modifier_condition(success_value, task_id, line_number, field_name='success')
                else:
                    # For regular tasks, validate as condition expression
                    self.validate_condition_expression(success_value, 'success', task_id, line_number)

            # Validate 'failure' field
            if 'failure' in task:
                failure_value = task['failure']
                self.validate_condition_expression(failure_value, 'failure', task_id, line_number)

            # Validate mutual exclusion: success and failure cannot coexist
            if 'success' in task and 'failure' in task:
                self.errors.append(
                    f"Line {line_number}: Task {task_id} cannot use 'success' and 'failure' together. "
                    "Use either 'success' for positive conditions OR 'failure' for inverse conditions, not both."
                )

        # Validate 'condition' field
        if 'condition' in task:
            condition_value = task['condition']
            self.validate_condition_expression(condition_value, 'condition', task_id, line_number)

        # Validate 'loop_break' field
        if 'loop_break' in task:
            loop_break_value = task['loop_break']
            self.validate_condition_expression(loop_break_value, 'loop_break', task_id, line_number)

        # Validate 'command' field (skip for parallel, conditional, and decision tasks)
        if 'command' in task and task.get('type') not in ['parallel', 'conditional', 'decision']:  # NEW: Skip decision tasks
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
        is_decision = task.get('type') == 'decision'  # NEW: Check for decision

        # Special case for local execution (doesn't need hostname)
        exec_resolved = self.resolve_global_variables_for_validation(task.get('exec', ''))
        is_local_exec = (self.clean_field_value(exec_resolved) or '').lower() == 'local'

        valid_task = (has_return or is_parallel or is_conditional or is_decision or (has_command and (has_hostname or is_local_exec)))  # NEW: Include decision

        if not valid_task:
            self.errors.append(f"Line {line_number}: Task {task_id} must have either a command+hostname, a return value, or be a parallel/conditional/decision task.")

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
            # Skip timeout validation for parallel/conditional/decision tasks - they have their own specific validation
            is_parallel = task.get('type') == 'parallel'
            is_conditional = task.get('type') == 'conditional'
            is_decision = task.get('type') == 'decision'

            if not is_parallel and not is_conditional and not is_decision:
                # CRITICAL: Timeout can only be used on tasks that execute commands
                # Tasks without commands (return) don't execute anything
                has_command = 'command' in task
                is_return_task = 'return' in task

                if not has_command or is_return_task:
                    # Concise error for INFO level
                    self.errors.append(
                        f"Line {line_number}: Task {task_id} cannot use 'timeout' parameter."
                    )
                    # Detailed explanation for DEBUG level
                    self.debug_log(
                        "Timeout only applies to tasks that execute commands. "
                        "Tasks with 'return' don't execute commands."
                    )
                else:
                    # Validate timeout value if task has command
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

    def validate_direct_modifier_condition(self, condition, task_id, line_number, field_name='next'):
        """Validate direct modifier condition (min_success=N, max_failed=N, etc.) or simple multi-task conditions."""
        # Examples: min_success=2, max_failed=1, all_success, any_success

        # Check for simple multi-task conditions (no '=' sign)
        simple_conditions = ['all_success', 'any_success', 'majority_success']
        if condition in simple_conditions:
            return  # These are valid

        if '=' not in condition:
            self.errors.append(f"Line {line_number}: Task {task_id} has invalid {field_name} condition: '{condition}'. "
                             f"Valid formats: 'modifier=value' or one of {simple_conditions}")
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
            # CASE INSENSITIVE: Accept @0_STDOUT@, @0_stdout@, etc.
            task_var_pattern = r'\d+_(stdout|stderr|success|exit)$'
            if re.match(task_var_pattern, var_name, re.IGNORECASE):
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

        # CRITICAL: Check for operators inside parentheses (not supported)
        # Parentheses can only wrap simple conditions, not complex expressions
        if self._check_operators_inside_parentheses(resolved_expression, field_name, task_id, line_number):
            return  # Don't continue validation if this error exists

        # CRITICAL: Validate individual condition parts after splitting on operators
        # This catches malformed conditions like "stdout~FAILED,exit_2"
        self.validate_condition_parts(resolved_expression, field_name, task_id, line_number)

    def validate_condition_parts(self, expression, field_name, task_id, line_number):
        """
        Validate individual condition parts after splitting on boolean operators.
        This ensures each part is a valid simple condition.
        """
        # Split on operators while preserving the structure
        # Handle ONLY |, & operators (not word operators)
        parts = []

        # Split only on symbol operators (& and |)
        sub_parts = re.split(r'([|&])', expression)
        for sub_part in sub_parts:
            # Skip empty parts and operator symbols
            if sub_part.strip() and sub_part not in ['|', '&']:
                parts.append(sub_part.strip())

        # Validate each part is a valid simple condition
        for part in parts:
            if not part:
                continue

            # Strip outer matching parentheses to support grouped conditions like '(stdout~OK)'
            # This allows validation of the inner condition while preserving grouping semantics
            stripped_part = part.strip()

            # Strip all leading '(' and trailing ')' characters
            # This handles both complete groups like '(stdout~OK)' and split fragments like '(exit_0'
            while stripped_part.startswith('('):
                stripped_part = stripped_part[1:].strip()
            while stripped_part.endswith(')'):
                stripped_part = stripped_part[:-1].strip()

            # Skip empty results after stripping
            if not stripped_part:
                continue

            # Validate that the part matches known condition patterns
            self.validate_simple_condition_syntax(stripped_part, field_name, task_id, line_number)

    def validate_simple_condition_syntax(self, condition, field_name, task_id, line_number):
        """
        Validate that a simple condition (no boolean operators) follows valid syntax.
        Valid patterns:
        - exit_N (exit code check)
        - exit_not_0
        - stdout/stderr with operators (~, !~, =, !=, <, <=, >, >=)
        - stdout/stderr_count with operators
        - variable comparisons with operators
        - boolean literals (true, false)
        - success keyword
        """
        condition = condition.strip()

        # Skip empty conditions
        if not condition:
            return

        # Valid patterns
        # CASE INSENSITIVE: Accept both @0_stdout@ and @0_STDOUT@, stdout~ and STDOUT~, etc.
        valid_patterns = [
            r'^exit_\d+$',                           # exit_0, exit_1, etc.
            r'^exit_not_0$',                         # exit_not_0
            r'^stdout~',                             # stdout pattern matching
            r'^stdout!~',                            # stdout pattern not matching
            r'^stdout(=|!=)',                        # stdout equality/inequality
            r'^stdout(<|<=|>|>=)',                   # stdout numeric comparison
            r'^stdout_count[=<>]',                   # stdout_count with operators
            r'^stderr~',                             # stderr pattern matching
            r'^stderr!~',                            # stderr pattern not matching
            r'^stderr(=|!=)',                        # stderr equality/inequality
            r'^stderr(<|<=|>|>=)',                   # stderr numeric comparison
            r'^stderr_count[=<>]',                   # stderr_count with operators
            r'^(true|false)$',                       # boolean literals
            r'^success$',                            # success keyword
            r'^[a-zA-Z_]\w*[=!<>~]',                # variable comparisons
            r'^exit[=!<>]',                          # exit comparisons (current task)
            r'^@\d+_(stdout|stderr|success|exit)@$',  # standalone task result placeholders
            r'^@\d+_(stdout|stderr|success|exit)@[=!<>~]',  # task result comparisons
            r'^contains:',                           # legacy contains
            r'^not_contains:',                       # legacy not_contains
        ]

        # Check if condition matches any valid pattern (case-insensitive)
        is_valid = any(re.match(pattern, condition, re.IGNORECASE) for pattern in valid_patterns)

        if not is_valid:
            # Provide helpful error message
            if re.match(r'^\w+,', condition):
                self.errors.append(
                    f"Line {line_number}: Task {task_id} has invalid {field_name} condition: '{condition}'. "
                    f"Did you mean to use '|' (OR) instead of ',' (comma)?"
                )
            else:
                self.errors.append(
                    f"Line {line_number}: Task {task_id} has unrecognized {field_name}: '{condition}'. "
                    f"Valid patterns: exit_N, stdout/stderr operators (~, =, !=, <, >, etc.), task result placeholders (@N_stdout@, @N_stderr@, @N_success@, @N_exit@), variable comparisons, boolean literals (true/false)."
                )

    def _check_operators_inside_parentheses(self, condition, field_name, task_id, line_number):
        """
        Check if operators (&, |) exist inside parentheses and reject them.
        Parentheses should only wrap simple conditions, not complex expressions.

        Supported:   (exit_0), (stdout~OK), (exit_0)&(stdout~OK)
        Unsupported: (exit_0&stdout~OK), (exit_0|exit_1)

        Returns True if error found, False otherwise.
        """
        import re

        depth = 0
        inside_parens = False
        paren_start = -1

        for i, char in enumerate(condition):
            if char == '(':
                if depth == 0:
                    paren_start = i
                depth += 1
                inside_parens = True
            elif char == ')':
                depth -= 1
                if depth == 0:
                    inside_parens = False
                    paren_start = -1
            elif inside_parens and char in ['&', '|']:
                # Extract context around the error for better error message
                start = max(0, i - 20)
                end = min(len(condition), i + 20)
                context = condition[start:end]

                self.errors.append(
                    f"Line {line_number}: Task {task_id} has operators inside parentheses in '{field_name}' condition. "
                    f"Context: '...{context}...' "
                    f"Parentheses can only wrap simple conditions, not complex expressions. "
                    f"Use operators OUTSIDE parentheses: '(exit_0)&(stdout~OK)' instead of '(exit_0&stdout~OK)'. "
                    f"For complex grouping, wait for JSON/YAML support (see Future Features)."
                )
                return True  # Found error

        return False  # No error

    def is_valid_custom_delimiter(self, delimiter):
        """Check if a custom delimiter is valid."""
        # A valid custom delimiter is a non-empty string
        return delimiter and isinstance(delimiter, str)

    def collect_referenced_tasks(self, task, referenced_tasks):
        """Collect task IDs that are referenced in variables and on_failure/on_success fields."""
        # Check for @X_stdout@, @X_stderr@, @X_success@, or @X_exit@ references
        for _, value in task.items():
            if isinstance(value, str):
                for match in re.finditer(r'@(\d+)_(stdout|stderr|success|exit)@', value, re.IGNORECASE):
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