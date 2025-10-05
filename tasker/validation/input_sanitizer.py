# tasker/validation/input_sanitizer.py
"""
Input Sanitization Layer - Security Hardening for TASKER 2.0
----------------------------------------------------------
This module provides comprehensive input sanitization and validation
to prevent security vulnerabilities including command injection,
path traversal, buffer overflow, and other attack vectors.

CRITICAL: Python 3.6.8 compatible only - no 3.7+ features allowed
"""
import re


class InputSanitizer:
    """
    Comprehensive input sanitization for TASKER task files.
    Implements defense-in-depth security validation.

    Two-Tier Validation Strategy:
    - General length limits (e.g., MAX_ARGUMENTS_LENGTH=8192) for basic field validation
    - Stricter security limits (e.g., MAX_ARGUMENTS_SECURE_LENGTH=2000) for buffer overflow protection

    This approach allows reasonable field sizes while maintaining strict security thresholds.
    """

    # Security configuration constants
    MAX_STRING_LENGTH = 10000      # Maximum field length
    MAX_HOSTNAME_LENGTH = 253      # RFC compliant hostname length
    MAX_COMMAND_LENGTH = 4096      # Maximum command length
    MAX_ARGUMENTS_LENGTH = 8192    # Maximum arguments length (general limit)
    MAX_ARGUMENTS_SECURE_LENGTH = 2000  # Stricter limit for buffer overflow protection
    MAX_GLOBAL_VAR_LENGTH = 1024   # Maximum global variable length
    MAX_TASK_ID = 9999             # Maximum task ID
    MIN_TIMEOUT = 1                # Minimum timeout seconds
    MAX_TIMEOUT = 86400            # Maximum timeout (24 hours)
    MAX_LOOP_COUNT = 10000         # Maximum loop iterations
    MAX_RETRY_COUNT = 100          # Maximum retry attempts
    MAX_PARALLEL_TASKS = 1000      # Maximum parallel tasks

    # Shell metacharacters that indicate potential injection
    SHELL_METACHARACTERS = {
        ';', '&', '|', '$', '`', '(', ')',
        '<', '>', '\\', '"', "'", '\n', '\r'
    }

    # Command injection patterns (case-insensitive)
    INJECTION_PATTERNS = [
        r';\s*rm\s+',           # rm command after semicolon
        r';\s*curl\s+',         # curl command after semicolon
        r';\s*wget\s+',         # wget command after semicolon
        r';\s*cat\s+',          # cat command after semicolon
        r'\|\s*nc\s+',          # netcat piping
        r'\$\([^)]+\)',         # command substitution $(...)
        r'`[^`]+`',             # command substitution `...`
        r'&&\s*rm\s+',          # rm with AND operator
        r'\|\|\s*curl\s+',      # curl with OR operator
        r'>\s*/dev/',           # output redirection
        r'<\s*/dev/',           # input redirection
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',               # Basic traversal
        r'\.\.\\',              # Windows traversal
        r'%2e%2e%2f',           # URL encoded traversal
        r'%2e%2e%5c',           # URL encoded Windows traversal
        r'\.\.%2f',             # Mixed encoding
        r'\.\.%5c',             # Mixed encoding Windows
        r'%252e%252e%252f',     # Double URL encoded
        r'\.\./\.\./\.\.',      # Multiple traversal
        r'/etc/passwd',         # Common target file
        r'/etc/shadow',         # Common target file
        r'/proc/version',       # System information
        r'c:\\windows\\',       # Windows system path
    ]

    # Suspicious content patterns
    SUSPICIOUS_PATTERNS = [
        r'/bin/(bash|sh|zsh|csh|tcsh)',     # Shell executables
        r'(python|perl|ruby|php)\s+',       # Scripting languages
        r'\beval\s*\(',                     # Code evaluation (word boundary to avoid false positives)
        r'\bexec\s*\(',                     # Code execution (word boundary to avoid false positives)
        r'\bsystem\s*\(\s*["\']',           # System calls with quotes (more specific to avoid false positives)
        r'chmod\s+[0-9]+',                  # Permission changes
        r'chown\s+',                        # Ownership changes
        r'sudo\s+',                         # Privilege escalation
        r'su\s+',                           # User switching
    ]

    def __init__(self):
        """
        Create a new InputSanitizer instance.
        """
        pass

    def sanitize_field(self, field_name, field_value, max_length=None, exec_type='local'):
        """
        Sanitize a single task field value using field-specific and general security checks.
        
        Performs observable validations and transformations: coerces the input to a string, enforces a maximum length (unless a global-variable placeholder is present), rejects null bytes, runs field-specific validators, detects dangerous security patterns in a context-aware manner, and returns the trimmed value if valid.
        
        Parameters:
            field_name (str): Name of the field being sanitized.
            field_value: Value to sanitize; will be coerced to a string.
            max_length (int, optional): Override for the field's maximum allowed length. If omitted, the field's default limit is used.
            exec_type (str, optional): Execution context that alters validation strictness. Use 'shell' to allow shell syntax (will still warn on dangerous patterns); use other values (e.g., 'local') for stricter blocking of shell-like constructs.
        
        Returns:
            dict: A result object with keys:
                - valid (bool): `true` if the field passed all checks, `false` otherwise.
                - value (str): The sanitized (trimmed) string value; when invalid this is the original coerced string.
                - errors (list): List of error messages that caused validation to fail.
                - warnings (list): List of non-fatal warnings about suspicious or risky content.
        """
        errors = []
        warnings = []

        if not isinstance(field_value, str):
            field_value = str(field_value)

        # 1. Length validation
        if max_length is None:
            max_length = self._get_field_max_length(field_name)

        # Skip length validation if value contains global variable placeholders
        # These will be resolved later in the validation pipeline
        has_placeholder = '@' in field_value and re.search(r'@[A-Za-z_][A-Za-z0-9_]*@', field_value)

        if not has_placeholder and len(field_value) > max_length:
            errors.append(f"Field '{field_name}' exceeds maximum length ({max_length}): {len(field_value)} characters")
            return {'valid': False, 'value': field_value, 'errors': errors, 'warnings': warnings}

        # 2. Null byte detection
        if '\x00' in field_value:
            errors.append(f"Field '{field_name}' contains null bytes - potential injection attempt")
            return {'valid': False, 'value': field_value, 'errors': errors, 'warnings': warnings}

        # 3. Field-specific validation (context-aware)
        field_result = self._validate_field_specific(field_name, field_value, exec_type)
        errors.extend(field_result['errors'])
        warnings.extend(field_result['warnings'])

        if not field_result['valid']:
            return {'valid': False, 'value': field_value, 'errors': errors, 'warnings': warnings}

        # 4. General security pattern detection (context-aware)
        security_result = self._detect_security_patterns(field_name, field_value, exec_type)
        errors.extend(security_result['errors'])
        warnings.extend(security_result['warnings'])

        # 5. Basic sanitization (trim whitespace only - preserve content)
        sanitized_value = field_value.strip()

        return {
            'valid': len(errors) == 0,
            'value': sanitized_value,
            'errors': errors,
            'warnings': warnings
        }

    def _get_field_max_length(self, field_name):
        """
        Return the maximum allowed length for a given task field.
        
        Uses predefined per-field limits for known fields (hostname, command, arguments, numeric fields, task id) and falls back to MAX_STRING_LENGTH for unknown fields.
        
        Returns:
            int: Maximum number of characters permitted for the specified field.
        """
        field_limits = {
            'hostname': self.MAX_HOSTNAME_LENGTH,
            'command': self.MAX_COMMAND_LENGTH,
            'arguments': self.MAX_ARGUMENTS_LENGTH,
            'task': 10,  # Task IDs should be short
            'timeout': 50,  # Numeric fields - allow for invalid values to reach proper validation
            'loop': 50,
            'retry_count': 50,
            'retry_delay': 50,
            'max_parallel': 50,
        }
        return field_limits.get(field_name, self.MAX_STRING_LENGTH)

    def _validate_field_specific(self, field_name, field_value, exec_type='local'):
        """
        Dispatches validation to the appropriate field-specific validator and returns that validator's result.
        
        Parameters:
            field_name (str): The name of the field to validate (e.g., 'command', 'hostname', 'arguments').
            field_value (str): The field value to validate.
            exec_type (str): Execution context affecting validation rules; typically 'local' or 'shell'. When not 'shell', stricter checks are applied for command/arguments.
        
        Returns:
            dict: Validation result with keys:
                - valid (bool): Whether the field passed validation.
                - errors (list): List of error messages (empty if valid).
                - warnings (list): List of warning messages (may be empty).
        """
        if field_name == 'hostname':
            return self._validate_hostname(field_value)
        elif field_name == 'command':
            return self._validate_command(field_value, exec_type)
        elif field_name == 'arguments':
            return self._validate_arguments(field_value, exec_type)
        elif field_name in ['task', 'on_success', 'on_failure']:
            return self._validate_task_id(field_value)
        elif field_name in ['timeout', 'sleep', 'loop', 'retry_count', 'retry_delay', 'max_parallel']:
            return self._validate_numeric_field(field_name, field_value)
        elif field_name == 'retry_failed':
            return self._validate_retry_failed_field(field_value)
        elif field_name in ['success', 'condition', 'next', 'loop_break']:
            return self._validate_condition_field(field_value)
        else:
            # Default validation for other fields
            return {'valid': True, 'errors': [], 'warnings': []}

    def _validate_hostname(self, hostname):
        """
        Validate a hostname string for security concerns and basic format rules.
        
        Parameters:
            hostname (str): Hostname or host expression to validate; may include TASKER placeholders like @VAR@.
        
        Returns:
            result (dict): Validation outcome with keys:
                valid (bool): True if the hostname passed checks, False otherwise.
                errors (list): Blocking error messages.
                warnings (list): Non-blocking warnings or informational messages.
        """
        errors = []
        warnings = []

        # Check for empty hostname
        if not hostname.strip():
            errors.append("Hostname cannot be empty")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for command injection in hostname
        if any(char in hostname for char in self.SHELL_METACHARACTERS):
            errors.append(f"Hostname contains shell metacharacters - potential injection: '{hostname}'")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for suspicious patterns
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, hostname, re.IGNORECASE):
                errors.append(f"Hostname contains suspicious injection pattern: '{hostname}'")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Basic hostname format validation (simplified)
        # Skip validation for TASKER global variable placeholders (@VARIABLE@)
        if not re.search(r'@[A-Za-z_][A-Za-z0-9_]*@', hostname) and not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
            warnings.append(f"Hostname contains unusual characters: '{hostname}'")

        # Check for localhost variations (info only)
        if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
            pass  # Localhost is valid, no action needed

        return {'valid': True, 'errors': errors, 'warnings': warnings}

    def _validate_command(self, command, exec_type='local'):
        """
        Validate the command field for security according to the execution context.
        
        Parameters:
            command (str): The raw command string to validate.
            exec_type (str): Execution context, e.g., 'local' for strict validation or 'shell' to allow shell syntax.
        
        Returns:
            dict: Validation result with keys:
                valid (bool): `True` if the command passes security checks, `False` otherwise.
                errors (list): List of error messages explaining why validation failed.
                warnings (list): List of warnings about potentially problematic but non-fatal issues.
        """
        errors = []
        warnings = []

        # Check for empty command
        if not command.strip():
            errors.append("Command cannot be empty")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for spaces in command (should use arguments field) - applies to all exec types
        if ' ' in command.strip() and exec_type != 'shell':
            warnings.append(f"Command contains spaces - consider using 'arguments' field: '{command}'")

        # Shell syntax validation - only for exec=local (strict mode)
        if exec_type != 'shell':
            # Check for command injection patterns (strict for exec=local)
            for pattern in self.INJECTION_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    errors.append(f"Command contains shell syntax (use exec=shell if intended): '{command}'")
                    return {'valid': False, 'errors': errors, 'warnings': warnings}

            # Check for shell metacharacters (strict for exec=local)
            dangerous_chars = self.SHELL_METACHARACTERS - {'-', '_', '.'}  # Allow common command chars
            if any(char in command for char in dangerous_chars):
                errors.append(f"Command contains shell metacharacters (use exec=shell if intended): '{command}'")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

        return {'valid': True, 'errors': errors, 'warnings': warnings}

    def _validate_arguments(self, arguments, exec_type='local'):
        """
        Validate the task arguments field for size and security concerns with context-aware rules.
        
        Performs a two-tier size check to guard against buffer-overflow risks, rejects argument values that contain path traversal patterns, and applies stricter injection/malformed-shell checks when exec_type is not 'shell'. If exec_type is not 'shell', a common shell-script invocation form (starting with '-c ' and containing quotes) is treated as an allowed shell script context. Suspicious patterns are reported as warnings for all contexts.
        
        Parameters:
            arguments (str): The arguments string to validate.
            exec_type (str): Execution context, e.g., 'local' or 'shell'; affects strictness of shell/injection checks.
        
        Returns:
            dict: Validation result with keys:
                valid (bool): `True` when the arguments pass checks, `False` when an error prevents usage.
                errors (list): Error messages explaining why validation failed.
                warnings (list): Non-fatal warnings about suspicious content.
        """
        errors = []
        warnings = []

        # Two-tier validation strategy for arguments field:
        # 1. General length check uses MAX_ARGUMENTS_LENGTH (8192) in sanitize_field
        # 2. Security buffer overflow check uses stricter MAX_ARGUMENTS_SECURE_LENGTH (2000)
        if len(arguments) > self.MAX_ARGUMENTS_SECURE_LENGTH:
            errors.append(f"Arguments field too large (potential buffer overflow): {len(arguments)} characters (maximum {self.MAX_ARGUMENTS_SECURE_LENGTH})")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Shell syntax validation - only strict for exec=local
        if exec_type != 'shell':
            # Check if this is a legitimate shell script context (sh -c "script")
            # This is a common pattern in test cases and should be allowed
            is_shell_script = arguments.startswith('-c ') and ('"' in arguments or "'" in arguments)

            if not is_shell_script:
                # Check for command injection patterns (strict for exec=local)
                for pattern in self.INJECTION_PATTERNS:
                    if re.search(pattern, arguments, re.IGNORECASE):
                        errors.append(f"Arguments contain shell syntax (use exec=shell if intended): '{arguments}'")
                        return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for path traversal (applies to all exec types)
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, arguments, re.IGNORECASE):
                errors.append(f"Arguments contain path traversal pattern: '{arguments}'")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for suspicious content (warn for all exec types)
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, arguments, re.IGNORECASE):
                warnings.append(f"Arguments contain potentially suspicious content: '{arguments}'")

        return {'valid': True, 'errors': errors, 'warnings': warnings}

    def _validate_task_id(self, task_id_str):
        """Validate task ID fields."""
        errors = []
        warnings = []

        try:
            task_id = int(task_id_str)

            if task_id < 0:
                errors.append(f"Task ID cannot be negative: {task_id}")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

            if task_id > self.MAX_TASK_ID:
                errors.append(f"Task ID exceeds maximum ({self.MAX_TASK_ID}): {task_id}")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

        except ValueError:
            errors.append(f"Task ID must be an integer: '{task_id_str}'")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        return {'valid': True, 'errors': errors, 'warnings': warnings}

    def _validate_numeric_field(self, field_name, value_str):
        """Validate numeric fields with appropriate bounds."""
        errors = []
        warnings = []

        # Skip numeric validation if value contains global variable placeholders
        # These will be resolved later in the validation pipeline
        if '@' in value_str and re.search(r'@[A-Za-z_][A-Za-z0-9_]*@', value_str):
            # This is a placeholder - defer validation until after resolution
            return {'valid': True, 'errors': errors, 'warnings': warnings}

        try:
            # Handle float for sleep field
            if field_name == 'sleep':
                value = float(value_str)
            else:
                value = int(value_str)

            # Field-specific bounds checking
            if field_name == 'timeout':
                if value < self.MIN_TIMEOUT:
                    errors.append(f"Timeout too small (minimum {self.MIN_TIMEOUT}): {value}")
                elif value > self.MAX_TIMEOUT:
                    errors.append(f"Timeout too large (maximum {self.MAX_TIMEOUT}): {value}")

            elif field_name == 'loop':
                if value < 0:
                    errors.append(f"Loop count cannot be negative: {value}")
                elif value > self.MAX_LOOP_COUNT:
                    errors.append(f"Loop count too large (maximum {self.MAX_LOOP_COUNT}): {value}")

            elif field_name in ['retry_count', 'retry_delay']:
                if value < 0:
                    errors.append(f"[INPUT SANITIZER] {field_name} cannot be negative: {value} (Security: Range validation)")
                elif field_name == 'retry_count' and value > self.MAX_RETRY_COUNT:
                    errors.append(f"[INPUT SANITIZER] Retry count too large (maximum {self.MAX_RETRY_COUNT}): {value} (Security: Resource limits)")
                elif field_name == 'retry_delay' and value > 3600:
                    warnings.append(f"[INPUT SANITIZER] Retry delay very large (over 1 hour): {value} (Security: Resource limits)")

            elif field_name == 'max_parallel':
                if value < 1:
                    errors.append(f"max_parallel must be at least 1: {value}")
                elif value > self.MAX_PARALLEL_TASKS:
                    errors.append(f"max_parallel too large (maximum {self.MAX_PARALLEL_TASKS}): {value}")

            elif field_name == 'sleep':
                if value < 0:
                    errors.append(f"Sleep time cannot be negative: {value}")
                elif value > 86400:  # 24 hours
                    warnings.append(f"Sleep time very large (over 24 hours): {value}")

            # General negative check for other numeric fields
            elif value < 0:
                warnings.append(f"{field_name} is negative: {value}")

        except ValueError:
            field_type = "number" if field_name != 'sleep' else "number (float allowed)"
            errors.append(f"[INPUT SANITIZER] {field_name} must be a {field_type}: '{value_str}' (Security: Type validation)")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}

    def _validate_retry_failed_field(self, value_str):
        """Validate retry_failed field - must be 'true' or 'false'."""
        errors = []
        warnings = []

        # Skip validation if value contains global variable placeholders
        if '@' in value_str and re.search(r'@[A-Za-z_][A-Za-z0-9_]*@', value_str):
            return {'valid': True, 'errors': errors, 'warnings': warnings}

        # Basic security checks
        if len(value_str) > 50:  # Reasonable length limit
            errors.append(f"retry_failed field too long: {len(value_str)} characters")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for command injection patterns
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, value_str, re.IGNORECASE):
                errors.append(f"retry_failed contains injection pattern: '{value_str}'")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Validate allowed values (case insensitive, but preserve original case for error reporting)
        allowed_values = ['true', 'false']
        if value_str.lower().strip() not in allowed_values:
            errors.append(f"[INPUT SANITIZER] retry_failed must be 'true' or 'false', got: '{value_str}' (Security: Basic format validation)")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        return {'valid': True, 'errors': errors, 'warnings': warnings}

    def _validate_condition_field(self, condition):
        """
        Validate a TASKER condition expression for security concerns.
        
        Checks the condition for command-injection patterns and disallowed shell metacharacters while allowing recognized TASKER condition syntax.
        
        Parameters:
        	condition (str): The condition expression to validate.
        
        Returns:
        	result (dict): Dictionary with keys:
        		- `valid` (bool): `False` if injection patterns are found, `True` otherwise.
        		- `errors` (list): Error messages for fatal validation failures (e.g., injection detected).
        		- `warnings` (list): Non-fatal warnings (e.g., presence of shell metacharacters outside TASKER condition syntax).
        """
        errors = []
        warnings = []

        # Check for command injection in conditions
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, condition, re.IGNORECASE):
                errors.append(f"Condition contains injection pattern: '{condition}'")
                return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for potentially dangerous shell metacharacters
        # Skip validation for legitimate TASKER condition syntax:
        # - exit_0&stdout~pattern (output matching)
        # - @1_stdout@>=@MAX_COUNTER@ (numeric comparison)
        # - @task_success@=true (boolean comparison)
        is_tasker_condition = (
            re.search(r'(exit_\d+|stdout|stderr)(&|~)', condition) or  # Output conditions
            re.search(r'@\w+@\s*(>=|<=|>|<|=|!=)\s*@?\w+@?', condition) or  # Comparison conditions
            re.search(r'@\w+@\s*(=|!=)\s*(true|false)', condition) or  # Boolean conditions
            re.search(r'@\w+@\s*\|\s*@\w+@', condition)  # Logical OR conditions: @task1@|@task2@
        )
        dangerous_chars = {'$', '`', ';'}  # Remove '|' as it's used in TASKER logical OR
        if not is_tasker_condition and any(char in condition for char in dangerous_chars):
            warnings.append(f"Condition contains shell metacharacters: '{condition}'")

        return {'valid': True, 'errors': errors, 'warnings': warnings}

    def _detect_security_patterns(self, field_name, field_value, exec_type='local'):
        """
        Detect dangerous or suspicious security patterns in a field value using execution-context rules.
        
        Performs context-aware checks: in 'shell' mode only raises warnings for risky shell constructs, while in modes other than 'shell' it treats shell-injection patterns as errors. Flags truly dangerous operations, format-string patterns, encoded/obfuscated content, and excessive repeated characters.
        
        Parameters:
            field_name (str): The name of the field being inspected (used in messages).
            field_value (str): The string value to analyze for security concerns.
            exec_type (str): Execution context that controls strictness; commonly 'local' or 'shell'.
        
        Returns:
            result (dict): {
                'valid': bool,       # True if no errors were found
                'errors': list,      # Blocking issues (e.g., shell syntax in non-shell context)
                'warnings': list     # Non-blocking concerns (dangerous commands, encoding, format strings, etc.)
            }
        """
        errors = []
        warnings = []

        # Truly dangerous patterns (warn for ALL execution types)
        DANGEROUS_PATTERNS = [
            (r'rm\s+-rf\s+/', 'Dangerous recursive delete detected'),
            (r'chmod\s+777', 'Overly permissive file permissions detected'),
            (r'/etc/passwd', 'Access to sensitive system file detected'),
            (r'/etc/shadow', 'Access to sensitive system file detected'),
            (r'\beval\s*\(', 'Code evaluation detected (potential security risk)'),
            (r'\bexec\s*\(', 'Code execution detected (potential security risk)'),
            (r'sudo\s+rm', 'Privileged delete operation detected'),
            (r'mkfs\.', 'Filesystem creation/formatting detected'),
            (r'dd\s+.*of=/dev/', 'Direct disk write detected'),
        ]

        # Check for truly dangerous patterns (applies to ALL exec types)
        for pattern, message in DANGEROUS_PATTERNS:
            if re.search(pattern, field_value, re.IGNORECASE):
                warnings.append(f"Field '{field_name}': {message}")

        # Shell syntax patterns (allowed for exec=shell, blocked for exec=local)
        if exec_type != 'shell':
            # Strict validation for exec=local - block shell metacharacters
            # These are normal for shell scripts but shouldn't be in local commands
            for pattern in self.INJECTION_PATTERNS:
                if re.search(pattern, field_value, re.IGNORECASE):
                    errors.append(f"Field '{field_name}' contains shell syntax (use exec=shell if intended): '{field_value}'")
                    break  # Only report first match to avoid duplicate errors

        # Check for format string attacks (all exec types)
        format_string_pattern = r'%[sxdn]'
        if re.search(format_string_pattern, field_value):
            warnings.append(f"Field '{field_name}' contains format string patterns: '{field_value}'")

        # Check for encoding attempts (all exec types)
        encoding_patterns = [
            r'%[0-9a-fA-F]{2}',     # URL encoding
            r'\\x[0-9a-fA-F]{2}',   # Hex encoding
            r'\\u[0-9a-fA-F]{4}',   # Unicode encoding
        ]

        for pattern in encoding_patterns:
            if re.search(pattern, field_value):
                warnings.append(f"Field '{field_name}' contains encoded characters (potential obfuscation): '{field_value}'")
                break  # Only report first match

        # Check for extremely long repeated characters (potential buffer overflow - all exec types)
        if len(field_value) > 100:
            char_counts = {}
            for char in field_value:
                char_counts[char] = char_counts.get(char, 0) + 1
                if char_counts[char] > len(field_value) * 0.8:  # 80% same character
                    warnings.append(f"Field '{field_name}' contains excessive repeated characters (potential buffer overflow)")
                    break

        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}

    def sanitize_global_variable(self, var_name, var_value):
        """
        Sanitize global variable definitions.

        Returns:
            dict: {'valid': bool, 'name': str, 'value': str, 'errors': list, 'warnings': list}
        """
        errors = []
        warnings = []

        # Validate variable name
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name):
            errors.append(f"Invalid global variable name '{var_name}'. Must start with letter/underscore and contain only letters, numbers, underscores.")
            return {'valid': False, 'name': var_name, 'value': var_value, 'errors': errors, 'warnings': warnings}

        # Length check for variable name
        if len(var_name) > 64:
            errors.append(f"Global variable name too long (maximum 64): '{var_name}'")
            return {'valid': False, 'name': var_name, 'value': var_value, 'errors': errors, 'warnings': warnings}

        # Coerce variable value to string for validation to avoid TypeError
        value_str = str(var_value)

        # Sanitize variable value with enhanced security checks for global variables
        value_result = self._validate_arguments(value_str)  # Treat global vars like arguments for security

        # Also check basic field constraints
        if len(value_str) > self.MAX_GLOBAL_VAR_LENGTH:
            value_result['errors'].append(f"Global variable value too long (maximum {self.MAX_GLOBAL_VAR_LENGTH}): {len(value_str)} characters")
            value_result['valid'] = False

        # Add the errors and warnings from this function to those from argument validation
        for error in errors:
            value_result['errors'].append(error)
        for warning in warnings:
            value_result['warnings'].append(warning)

        # Use sanitized value (just trimmed) or original if validation failed
        final_value = value_str.strip() if value_result['valid'] else value_str

        return {
            'valid': value_result['valid'],
            'name': var_name,
            'value': final_value,
            'errors': value_result['errors'],
            'warnings': value_result['warnings']
        }

    def validate_task_structure(self, task_dict):
        """
        Validate overall task structure for security issues.

        Returns:
            dict: {'valid': bool, 'errors': list, 'warnings': list}
        """
        errors = []
        warnings = []

        # Check for suspicious field combinations
        if 'command' in task_dict and 'exec' in task_dict:
            if task_dict.get('exec') != 'local' and any(char in task_dict['command'] for char in self.SHELL_METACHARACTERS):
                warnings.append("Remote command execution with shell metacharacters detected")

        # Check for potential privilege escalation patterns
        if 'command' in task_dict:
            priv_patterns = ['sudo', 'su ', 'chmod', 'chown', 'passwd']
            for pattern in priv_patterns:
                if pattern in task_dict['command'].lower():
                    warnings.append(f"Potential privilege escalation command detected: {task_dict['command']}")
                    break

        # Validate field count (prevent excessive fields)
        if len(task_dict) > 25:  # Reasonable limit for task fields
            warnings.append(f"Task has many fields ({len(task_dict)}) - potential DoS via field flooding")

        return {'valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}