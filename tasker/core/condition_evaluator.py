# tasker/core/condition_evaluator.py
"""
Condition Evaluation and Variable Replacement
---------------------------------------------
Handles variable replacement (@VARIABLE@ syntax) and condition evaluation logic.
Provides modular, testable components for the TASKER system.
"""

import re
from typing import ClassVar
from .utilities import convert_value, convert_to_number
from .constants import MAX_VARIABLE_EXPANSION_DEPTH


class ConditionEvaluator:
    """
    Handles condition evaluation and variable replacement for TASKER tasks.

    This class provides stateless condition evaluation by accepting required
    data (global_vars, task_results) as parameters rather than storing state.
    """

    # Simple cache to reduce debug logging repetition (class-level)
    _logged_replacements: ClassVar[set] = set()

    @classmethod
    def clear_debug_cache(cls):
        """Clear the debug logging cache for a new execution session."""
        cls._logged_replacements.clear()

    @staticmethod
    def should_mask_variable(var_name):
        """
        Check if a variable should be masked based on naming convention.

        Auto-masked prefixes (case-insensitive):
        - SECRET_*, MASK_*, HIDE_* - explicit marking
        - PASSWORD_*, TOKEN_* - common sensitive data types
        - *_PASSWORD, *_TOKEN, *_SECRET, *_KEY - suffix-based detection

        Args:
            var_name: Variable name to check

        Returns:
            True if variable should be masked, False otherwise

        Examples:
            should_mask_variable('SECRET_API_KEY') -> True
            should_mask_variable('DB_PASSWORD') -> True
            should_mask_variable('HOSTNAME') -> False
            should_mask_variable('USERNAME') -> False
        """
        if not var_name:
            return False

        var_upper = var_name.upper()

        # Prefix-based masking
        prefix_masks = ('SECRET_', 'MASK_', 'HIDE_', 'PASSWORD_', 'TOKEN_')
        if var_upper.startswith(prefix_masks):
            return True

        # Suffix-based masking
        suffix_masks = ('_PASSWORD', '_TOKEN', '_SECRET', '_KEY')
        if var_upper.endswith(suffix_masks):
            return True

        return False

    @staticmethod
    def mask_value(value):
        """
        Format a masked value showing only length.

        Args:
            value: Value to mask

        Returns:
            Masked string in format "<masked len=N>" or "<masked len=?>" if length cannot be determined

        Example:
            mask_value('super_secret_123') -> '<masked len=16>'
            mask_value(unprintable_object) -> '<masked len=?>'
        """
        try:
            value_len = len(str(value))
        except (TypeError, AttributeError):
            value_len = "?"
        return f"<masked len={value_len}>"

    @staticmethod
    def replace_variables(text, global_vars, task_results, debug_callback=None):
        """
        Replace variables like @task_number_stdout@, @task_number_stderr@, @task_number_success@,
        @task_number_exit@, or @GLOBAL_VAR@ with actual values. Supports variable chaining like @PATH@/@SUBDIR@.

        Args:
            text: Text containing variables to replace
            global_vars: Dictionary of global variables
            task_results: Dictionary of task results
            debug_callback: Optional function for debug logging

        Returns:
            Tuple of (replaced_text, resolution_success)
        """
        if not text:
            return text, True  # Return text and resolution status

        # Enhanced pattern to match both task result variables and global variables
        # CASE INSENSITIVE: Accept @0_stdout@, @0_STDOUT@, @0_StdOut@, etc.
        task_result_pattern = r'@(\d+)_(stdout|stderr|success|exit)@'
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'

        replaced_text = text
        unresolved_variables = []
        original_text = text

        # First, handle task result variables (@X_stdout@, etc.) - THREAD SAFE
        # Use case-insensitive matching
        task_matches = re.findall(task_result_pattern, text, re.IGNORECASE)
        for task_num, output_type in task_matches:
            task_num = int(task_num)
            output_type_lower = output_type.lower()

            # CRITICAL: Thread-safe access to task_results
            task_result = task_results.get(task_num)
            if task_result is not None:
                if output_type_lower == 'stdout':
                    # CRITICAL: Prioritize stored stdout over temp file
                    # Stored stdout contains split results (when stdout_split is used)
                    # Only read temp file if stdout was truncated (≥1MB raw output without split)
                    if task_result.get('stdout_truncated', False) and 'stdout_file' in task_result and task_result['stdout_file']:
                        # Output was truncated - read full output from temp file
                        try:
                            with open(task_result['stdout_file'], 'r') as f:
                                value = f.read().rstrip('\n')
                        except (IOError, OSError, FileNotFoundError):
                            # Temp file unavailable, use preview
                            value = task_result.get('stdout', '').rstrip('\n')
                    else:
                        # Use stored stdout (contains split result if splitting was applied, or full output if <1MB)
                        value = task_result.get('stdout', '').rstrip('\n')
                elif output_type_lower == 'stderr':
                    # CRITICAL: Prioritize stored stderr over temp file
                    # Stored stderr contains split results (when stderr_split is used)
                    # Only read temp file if stderr was truncated (≥1MB raw output without split)
                    if task_result.get('stderr_truncated', False) and 'stderr_file' in task_result and task_result['stderr_file']:
                        # Output was truncated - read full output from temp file
                        try:
                            with open(task_result['stderr_file'], 'r') as f:
                                value = f.read().rstrip('\n')
                        except (IOError, OSError, FileNotFoundError):
                            # Temp file unavailable, use preview
                            value = task_result.get('stderr', '').rstrip('\n')
                    else:
                        # Use stored stderr (contains split result if splitting was applied, or full output if <1MB)
                        value = task_result.get('stderr', '').rstrip('\n')
                elif output_type_lower == 'success':
                    value = str(task_result.get('success', False))
                elif output_type_lower == 'exit':
                    value = str(task_result.get('exit_code', ''))
                else:
                    value = ''
                # Use original case from the text for replacement
                pattern_replace = f"@{task_num}_{output_type}@"
                replaced_text = replaced_text.replace(pattern_replace, value)
                if debug_callback:
                    debug_callback(f"Replaced task variable {pattern_replace} with '{value}'")
            else:
                unresolved_variables.append(f"@{task_num}_{output_type}@")
        
        # Second, handle global variables (@VARIABLE_NAME@) - supports chaining
        global_matches = re.findall(global_var_pattern, replaced_text)
        for var_name in global_matches:
            # Skip if this is a task result variable (already handled above)
            # CASE INSENSITIVE: Check with case-insensitive regex
            if re.match(r'\d+_(stdout|stderr|success|exit)$', var_name, re.IGNORECASE):
                continue
                
            # Check if it's a defined global variable
            if var_name in global_vars:
                value = global_vars[var_name]
                pattern_replace = f"@{var_name}@"
                replaced_text = replaced_text.replace(pattern_replace, value)
                # Only log if we haven't seen this replacement before
                replacement_key = f"{var_name}={value}"
                if debug_callback and replacement_key not in ConditionEvaluator._logged_replacements:
                    if ConditionEvaluator.should_mask_variable(var_name):
                        masked = ConditionEvaluator.mask_value(value)
                        debug_callback(f"Replaced global variable @{var_name}@ with '{masked}'")
                    else:
                        debug_callback(f"Replaced global variable @{var_name}@ with '{value}'")
                    ConditionEvaluator._logged_replacements.add(replacement_key)
            else:
                unresolved_variables.append(f"@{var_name}@")
        
        # Handle nested global variables (variable chaining support)
        # Keep replacing until no more global variables are found or max iterations reached
        max_iterations = MAX_VARIABLE_EXPANSION_DEPTH  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            nested_matches = re.findall(global_var_pattern, replaced_text)
            nested_replaced = False
            
            for var_name in nested_matches:
                # Skip task result variables
                # CASE INSENSITIVE: Check with case-insensitive regex
                if re.match(r'\d+_(stdout|stderr|success|exit)$', var_name, re.IGNORECASE):
                    continue
                    
                if var_name in global_vars:
                    value = global_vars[var_name]
                    pattern_replace = f"@{var_name}@"
                    replaced_text = replaced_text.replace(pattern_replace, value)
                    # Only log nested replacements if we haven't seen this replacement before
                    replacement_key = f"{var_name}={value}"
                    if debug_callback and replacement_key not in ConditionEvaluator._logged_replacements:
                        debug_callback(f"Replaced nested global variable @{var_name}@ with '{value}' (iteration {iteration})")
                        ConditionEvaluator._logged_replacements.add(replacement_key)
                    nested_replaced = True
            
            # If no nested replacements were made, we're done
            if not nested_replaced:
                break
        
        # Final check for any remaining unresolved variables
        final_matches = re.findall(global_var_pattern, replaced_text)
        for var_name in final_matches:
            # CASE INSENSITIVE: Check with case-insensitive regex
            if not re.match(r'\d+_(stdout|stderr|success|exit)$', var_name, re.IGNORECASE):
                if var_name not in global_vars:
                    unresolved_variables.append(f"@{var_name}@")
                
        if unresolved_variables:
            if debug_callback:
                debug_callback(f"Unresolved variables in '{original_text}': {', '.join(set(unresolved_variables))}")
            return replaced_text, False
        
        # Only log overall replacement for complex cases (multiple variables or chaining)
        if original_text != replaced_text and (len(re.findall(r'@[^@]+@', original_text)) > 1 or iteration > 1):
            if debug_callback:
                debug_callback(f"Variable replacement (complex): '{original_text}' -> '{replaced_text}'")
        
        return replaced_text, True

    @staticmethod
    def split_output(output, split_spec):
        """Split the output based on the specification and return the selected part."""
        if not output or not split_spec:
            return output
            
        parts = split_spec.split(',')
        if len(parts) != 2:
            # Note: In a static method context, we cannot call self.log
            # This should be handled by the calling code if logging is needed
            return output
            
        delimiter, index = parts
        try:
            index = int(index)
        except ValueError:
            # Note: In a static method context, we cannot call self.log
            # This should be handled by the calling code if logging is needed
            return output
            
        # Convert delimiter keywords to actual regex patterns
        delimiter_map = {
            'space': r' +',          # FIXED: Only literal space characters (not tabs/newlines)
            'whitespace': r'\s+',    # NEW: All whitespace (spaces, tabs, newlines, etc.)
            'tab': r'\t+',
            'newline': r'\n+',       # Split by one or more line breaks
            'colon': ':',            # Common in config files (/etc/passwd, etc)
            'semicolon': ';',        # Better naming than 'semi'
            'semi': ';',             # Keep for backward compatibility
            'comma': ',',
            'pipe': r'\|'            # Pipe needs escaping in regex
        }
        
        delimiter_pattern = delimiter_map.get(delimiter, delimiter)
        
        # Split the output
        split_output = re.split(delimiter_pattern, output)
        
        # Return the selected part if index is valid
        if 0 <= index < len(split_output):
            return split_output[index]
        else:
            # Note: In a static method context, we cannot call self.log
            # This should be handled by the calling code if logging is needed
            return output

    @staticmethod
    def _extract_pattern_from_condition(condition_part, debug_callback=None):
        """
        Extract pattern from condition part (after ~ operator), handling quotes.

        Args:
            condition_part: The part after the ~ operator (e.g., "pattern" or pattern)
            debug_callback: Optional function for debug logging

        Returns:
            Tuple of (pattern, is_quoted)

        Note: This helper reduces code duplication between stdout~ and stderr~ handling.
        Limitation: Does not handle escaped backslashes before quotes (e.g., foo\\").
        This is an acceptable limitation as such patterns are rare in command output.
        """
        pattern = condition_part.strip()
        is_quoted = False

        if pattern and (pattern[0] == '"' or pattern[0] == "'"):
            quote_char = pattern[0]
            if len(pattern) > 1 and pattern.endswith(quote_char):
                # Remove quotes
                pattern = pattern[1:-1]
                is_quoted = True
                if debug_callback:
                    debug_callback(f"Extracted quoted pattern: '{pattern}'")
            else:
                # Unclosed quote: strip leading quote and warn (permissive fallback)
                original_pattern = pattern
                pattern = pattern[1:]  # Strip leading quote
                if debug_callback:
                    debug_callback(f"WARNING: Unclosed quote in pattern '{original_pattern}' - treating as unquoted pattern '{pattern}'")

        # Warn if unquoted pattern contains operators
        if not is_quoted and any(op in pattern for op in ['!~', '<=', '>=', '!=', '~', '=', '<', '>']):
            if debug_callback:
                debug_callback(f"WARNING: Unquoted pattern '{pattern}' contains operators. Consider using quotes: ~\"{pattern}\"")

        return pattern, is_quoted

    @staticmethod
    def evaluate_condition(condition, exit_code, stdout, stderr, global_vars, task_results, debug_callback=None, current_task_success=None):
        """
        Evaluate a complex condition that may contain boolean operators (AND, OR, NOT)
        and nested parentheses. Supports both simple conditions and complex expressions.
        """
        if not condition:
            return False
            
        # Replace variables in the condition first
        condition, resolved = ConditionEvaluator.replace_variables(condition, global_vars, task_results, debug_callback)
        
        if debug_callback:
            debug_callback(f"Condition after variable replacement: '{condition}'")
        
        # Handle simple conditions without boolean operators (check for | and &)
        if not any(op in condition for op in ['|', '&']):
            return ConditionEvaluator.evaluate_simple_condition(condition, exit_code, stdout, stderr, debug_callback, current_task_success)
        
        # For complex conditions with boolean operators, we need to parse them
        # This is a simplified implementation that handles basic cases
        # More complex parsing would require a proper expression parser

        condition = condition.strip()
        
        # Handle | operator (OR - pipe symbol)
        if '|' in condition:
            parts = condition.split('|')
            results = []
            for part in parts:
                part_result = ConditionEvaluator.evaluate_simple_condition(part.strip(), exit_code, stdout, stderr, debug_callback, current_task_success)
                results.append(part_result)
                if debug_callback:
                    debug_callback(f"OR (|) part '{part.strip()}' evaluated to: {part_result}")
            result = any(results)
            if debug_callback:
                debug_callback(f"OR (|) condition overall result: {result}")
            return result
        
        # Handle & operator (AND - ampersand symbol)  
        if '&' in condition:
            parts = condition.split('&')
            results = []
            for part in parts:
                part_result = ConditionEvaluator.evaluate_simple_condition(part.strip(), exit_code, stdout, stderr, debug_callback, current_task_success)
                results.append(part_result)
                if debug_callback:
                    debug_callback(f"AND (&) part '{part.strip()}' evaluated to: {part_result}")
            result = all(results)
            if debug_callback:
                debug_callback(f"AND (&) condition overall result: {result}")
            return result
        
        # If no boolean operators found, treat as simple condition
        return ConditionEvaluator.evaluate_simple_condition(condition, exit_code, stdout, stderr, debug_callback, current_task_success)

    @staticmethod
    def evaluate_simple_condition(condition, exit_code, stdout, stderr, debug_callback=None, current_task_success=None):
        """Evaluate a simple condition without boolean operators."""
        condition = condition.strip()

        # Strip outer matching parentheses from simple conditions
        # This supports patterns like (exit_0), (stdout~OK), ((exit_0))
        # Note: Operators INSIDE parentheses like (exit_0&stdout~OK) are NOT supported
        # and will be caught by validation
        while condition.startswith('(') and condition.endswith(')'):
            # Check if the outer parentheses are matching
            depth = 0
            matching = True
            for i, char in enumerate(condition):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                # If depth hits 0 before the end, outer parens don't match the whole expression
                if depth == 0 and i < len(condition) - 1:
                    matching = False
                    break

            if matching:
                # Strip outer parentheses and continue checking for more
                condition = condition[1:-1].strip()
                if debug_callback:
                    debug_callback(f"Stripped outer parentheses, condition is now: '{condition}'")
            else:
                # Outer parentheses don't match the whole expression, stop stripping
                break

        # Built-in exit code conditions
        if condition == 'exit_0':
            result = exit_code == 0
            if debug_callback:
                debug_callback(f"Exit code condition 'exit_0': expected 0, actual {exit_code}, result {result}")
            return result
        elif condition == 'exit_not_0':
            result = exit_code != 0
            if debug_callback:
                debug_callback(f"Exit code condition 'exit_not_0': expected not 0, actual {exit_code}, result {result}")
            return result
        elif condition.startswith('exit_'):
            try:
                expected_code = int(condition[5:])
                result = exit_code == expected_code
                if debug_callback:
                    debug_callback(f"Exit code condition '{condition}': expected {expected_code}, actual {exit_code}, result {result}")
                return result
            except ValueError:
                if debug_callback:
                    debug_callback(f"Invalid exit code condition '{condition}', treating as False")
                return False
        
        # Check for success condition - use the current task success value
        if condition.lower() == "success":
            if current_task_success is not None:
                if debug_callback:
                    debug_callback(f"Success condition: {current_task_success}")
                return current_task_success
            else:
                # If no success value provided, default to exit_code == 0
                success_value = (exit_code == 0)
                if debug_callback:
                    debug_callback(f"Success condition (default): {success_value}")
                return success_value
        
        # Check for stdout/stderr conditions (only specific patterns like ~, !~, and _count, not general comparison operators)
        # Note: General patterns with =, !=, <, <=, >, >= (but not _count patterns) are handled by evaluate_operator_comparison below
        #
        # OPERATOR PRECEDENCE & PRIORITY ORDER:
        # The condition below implements a careful precedence order to handle edge cases correctly:
        #   1. _count patterns (e.g., stdout_count=3) - uses = as part of syntax, not as comparison
        #   2. ~ and !~ patterns (e.g., stdout~pattern) - string matching takes priority
        #   3. Comparison operators (=, !=, <, etc.) - handled by evaluate_operator_comparison
        #
        # This priority order ensures that:
        #   - 'stdout~WMPC Migrated = ubsos_sssd' correctly uses ~ (pattern match), not = (comparison)
        #   - 'stdout_count=3' correctly uses = as part of _count syntax
        #   - 'stdout=value' correctly delegates to evaluate_operator_comparison
        #
        # CASE INSENSITIVE: Accept both 'stdout' and 'STDOUT' for user convenience
        if condition.lower().startswith('stdout') and ('_count' in condition.lower() or '~' in condition or not any(op in condition for op in ['=', '!=', '<', '<=', '>', '>='])):
            stdout_stripped = stdout.rstrip('\n')
            condition_lower = condition.lower()
            if condition_lower == 'stdout~':
                result = stdout.strip() == ''
                if debug_callback:
                    debug_callback(f"Stdout empty check: '{stdout.strip()}' is {'empty' if result else 'not empty'}")
                return result
            elif condition_lower == 'stdout!~':
                result = stdout.strip() != ''
                if debug_callback:
                    debug_callback(f"Stdout not empty check: '{stdout.strip()}' is {'not empty' if result else 'empty'}")
                return result
            elif '~' in condition:
                # Extract pattern using helper method (reduces code duplication)
                condition_part = condition.split('~', 1)[1]
                pattern, is_quoted = ConditionEvaluator._extract_pattern_from_condition(
                    condition_part, debug_callback
                )

                if condition_lower.startswith('stdout!~'):
                    result = pattern not in stdout_stripped
                    if debug_callback:
                        debug_callback(f"Stdout pattern not match: '{pattern}' is {'absent' if result else 'present'} in '{stdout_stripped}'")
                    return result
                else:
                    result = pattern in stdout_stripped
                    if debug_callback:
                        debug_callback(f"Stdout pattern match: '{pattern}' is {'present' if result else 'absent'} in '{stdout_stripped}'")
                    return result
            elif '_count' in condition:
                try:
                    count_parts = condition.split('_count')
                    operator = count_parts[1][0] if len(count_parts[1]) > 0 else '='
                    expected_count = int(count_parts[1][1:])

                    # Fix: Handle empty stdout correctly
                    # Empty string after strip() should be 0 lines, not 1
                    stdout_stripped = stdout.strip()
                    if stdout_stripped == '':
                        actual_count = 0
                    else:
                        actual_count = len(stdout_stripped.split('\n'))

                    if operator == '=':
                        return actual_count == expected_count
                    elif operator == '<':
                        return actual_count < expected_count
                    elif operator == '>':
                        return actual_count > expected_count
                    else:
                        # Note: Cannot call self.log in static method, using debug_callback
                        if debug_callback:
                            debug_callback(f"Warning: Invalid operator in count condition: {condition}")
                        return False
                except (ValueError, IndexError):
                    # Note: Cannot call self.log in static method, using debug_callback
                    if debug_callback:
                        debug_callback(f"Warning: Invalid count specification in condition: {condition}")
                    return False

        # Check for stderr conditions (only specific patterns like ~, !~, and _count, not general comparison operators)
        # Note: General patterns with =, !=, <, <=, >, >= (but not _count patterns) are handled by evaluate_operator_comparison below
        # IMPORTANT: _count patterns use operators as part of their syntax (e.g., stderr_count=0, stderr_count<5)
        # so we must check for _count BEFORE blocking based on operators
        # CRITICAL FIX: Check for ~ and !~ operators FIRST before checking for other operators
        # This allows patterns like 'stderr~Error code = 404' to work correctly
        # CASE INSENSITIVE: Accept both 'stderr' and 'STDERR' for user convenience
        if condition.lower().startswith('stderr') and ('_count' in condition.lower() or '~' in condition or not any(op in condition for op in ['=', '!=', '<', '<=', '>', '>='])):
            stderr_stripped = stderr.rstrip('\n')
            condition_lower = condition.lower()
            if condition_lower == 'stderr~':
                result = stderr_stripped == ''
                if debug_callback:
                    debug_callback(f"Stderr empty check: '{stderr_stripped}' is {'empty' if result else 'not empty'}")
                return result
            elif condition_lower == 'stderr!~':
                result = stderr_stripped != ''
                if debug_callback:
                    debug_callback(f"Stderr not empty check: '{stderr_stripped}' is {'not empty' if result else 'empty'}")
                return result
            elif '~' in condition:
                # Extract pattern using helper method (reduces code duplication)
                condition_part = condition.split('~', 1)[1]
                pattern, is_quoted = ConditionEvaluator._extract_pattern_from_condition(
                    condition_part, debug_callback
                )

                if condition_lower.startswith('stderr!~'):
                    result = pattern not in stderr_stripped
                    if debug_callback:
                        debug_callback(f"Stderr pattern not match: '{pattern}' is {'absent' if result else 'present'} in '{stderr_stripped}'")
                    return result
                else:
                    result = pattern in stderr_stripped
                    if debug_callback:
                        debug_callback(f"Stderr pattern match: '{pattern}' is {'present' if result else 'absent'} in '{stderr_stripped}'")
                    return result
            elif '_count' in condition:
                try:
                    count_parts = condition.split('_count')
                    operator = count_parts[1][0] if len(count_parts[1]) > 0 else '='
                    expected_count = int(count_parts[1][1:])

                    # Fix: Handle empty stderr correctly
                    # Empty string after strip() should be 0 lines, not 1
                    # Use already-computed stderr_stripped from line 486
                    if stderr_stripped == '':
                        actual_count = 0
                    else:
                        actual_count = len(stderr_stripped.split('\n'))

                    if operator == '=':
                        return actual_count == expected_count
                    elif operator == '<':
                        return actual_count < expected_count
                    elif operator == '>':
                        return actual_count > expected_count
                    else:
                        # Note: Cannot call self.log in static method, using debug_callback
                        if debug_callback:
                            debug_callback(f"Warning: Invalid operator in count condition: {condition}")
                        return False
                except (ValueError, IndexError):
                    # Note: Cannot call self.log in static method, using debug_callback
                    if debug_callback:
                        debug_callback(f"Warning: Invalid count specification in condition: {condition}")
                    return False

        # Advanced conditions with operators
        elif any(op in condition for op in ['=', '!=', '~', '!~', '<', '<=', '>', '>=']):
            return ConditionEvaluator.evaluate_operator_comparison(condition, exit_code, stdout, stderr, debug_callback)
        
        # Boolean value conditions
        elif condition.lower() == 'true':
            if debug_callback:
                debug_callback(f"Boolean condition 'true' evaluated to: True")
            return True
        elif condition.lower() == 'false':
            if debug_callback:
                debug_callback(f"Boolean condition 'false' evaluated to: False")
            return False
        
        # String contains conditions (legacy support)
        elif condition.startswith('contains:'):
            search_term = condition[9:]
            result = search_term in stdout
            if debug_callback:
                debug_callback(f"Contains condition '{search_term}' in stdout: {result}")
            return result
        elif condition.startswith('not_contains:'):
            search_term = condition[13:]
            result = search_term not in stdout
            if debug_callback:
                debug_callback(f"Not contains condition '{search_term}' in stdout: {result}")
            return result
        
        # If no recognizable condition pattern, treat as False
        else:
            if debug_callback:
                debug_callback(f"Unrecognized condition '{condition}', treating as False")
            return False

    @staticmethod
    def parse_operator_condition(condition, debug_callback=None):
        """
        Parse a condition with operators, supporting quoted patterns.

        Quoted patterns (recommended for patterns with special characters):
            stdout~"WMPC Migrated = ubsos_sssd"  → pattern can contain =, ~, etc.
            stderr!~'error: code = 404'           → single quotes also supported

        Unquoted patterns (backward compatibility):
            stdout~simple_pattern                  → no special characters
            exit=0                                 → simple comparisons

        Returns:
            Tuple of (operator, left, right) or (None, None, None) if parsing fails
        """
        # Operators to check (order matters - check longer operators first)
        operators = ['!~', '<=', '>=', '!=', '~', '=', '<', '>']

        # First pass: Try to find quoted patterns with any operator
        # This takes priority because quoted patterns can contain any characters
        for op in operators:
            if op not in condition:
                continue

            # Find the operator position
            op_idx = condition.find(op)
            if op_idx == -1:
                continue

            left = condition[:op_idx].strip()
            right_raw = condition[op_idx + len(op):].strip()

            # Check if right side starts with a quote
            if right_raw and (right_raw[0] == '"' or right_raw[0] == "'"):
                quote_char = right_raw[0]
                # Find matching closing quote, allowing backslash-escaped quotes
                close_idx = -1
                i = 1
                while i < len(right_raw):
                    if right_raw[i] == quote_char and (i == 1 or right_raw[i-1] != '\\'):
                        close_idx = i
                        break
                    i += 1

                if close_idx > 0:
                    # Found closing quote - extract and unescape the quoted value
                    raw_content = right_raw[1:close_idx]
                    # Unescape escaped quotes
                    right = raw_content.replace('\\' + quote_char, quote_char)

                    # Validate that nothing comes after the closing quote (except whitespace)
                    remainder = right_raw[close_idx + 1:].strip()
                    if remainder:
                        if debug_callback:
                            debug_callback(f"WARNING: Unexpected text after closing quote in '{condition}': '{remainder}'")
                        # Don't fail, just warn - continue to try other operators
                        continue

                    if debug_callback:
                        debug_callback(f"Parsed quoted condition: operator='{op}', left='{left}', right='{right}'")

                    return (op, left, right)
                else:
                    # Unclosed quote
                    if debug_callback:
                        debug_callback(f"ERROR: Unclosed quote in condition: '{condition}'")
                    return (None, None, None)

        # Second pass: No quoted patterns found, try unquoted parsing
        # Use the original operator priority order
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()

                    # Check if right side looks like it should have been quoted
                    # (contains other operators that might cause ambiguity)
                    other_ops = [o for o in operators if o != op]
                    if any(other_op in right for other_op in other_ops):
                        if debug_callback:
                            debug_callback(f"WARNING: Unquoted pattern '{right}' contains operators. Consider using quotes: {op}\"{right}\"")

                    return (op, left, right)

        # No operator found
        return (None, None, None)

    @staticmethod
    def evaluate_operator_comparison(condition, exit_code, stdout, stderr, debug_callback=None):
        """Evaluate conditions with comparison operators (=, !=, ~, !~, <, <=, >, >=)."""

        # Parse the condition with quote support
        operator, left, right = ConditionEvaluator.parse_operator_condition(condition, debug_callback)

        if operator is None or left is None or right is None:
            if debug_callback:
                debug_callback(f"Could not parse operator condition '{condition}'")
            return False
        
        # Handle output splitting in left operand
        # CASE INSENSITIVE: Accept both 'stdout'/'STDOUT' and 'stderr'/'STDERR'
        left_lower = left.lower()
        if ':' in left and left_lower not in ['stdout', 'stderr']:
            split_parts = left.split(':', 1)
            if split_parts[0].lower() in ['stdout', 'stderr']:
                base_output = stdout if split_parts[0].lower() == 'stdout' else stderr
                left_val = ConditionEvaluator.split_output(base_output, split_parts[1])
            else:
                left_val = convert_value(left)
        elif left_lower == 'exit':
            left_val = exit_code
        elif left_lower == 'stdout':
            left_val = stdout.rstrip('\n')
        elif left_lower == 'stderr':
            left_val = stderr.rstrip('\n')
        else:
            left_val = convert_value(left)
        
        right_val = convert_value(right)
        
        try:
            if operator == '=':
                result = left_val == right_val
                if debug_callback:
                    debug_callback(f"Equality comparison '{left}' = '{right}': '{left_val}' = '{right_val}' = {result}")
                return result
            elif operator == '!=':
                result = left_val != right_val
                if debug_callback:
                    debug_callback(f"Inequality comparison '{left}' != '{right}': '{left_val}' != '{right_val}' = {result}")
                return result
            elif operator == '~':
                # Contains operation
                left_str = str(left_val)
                right_str = str(right_val)
                result = right_str in left_str
                if debug_callback:
                    debug_callback(f"Contains comparison '{left}' ~ '{right}': '{right_str}' in '{left_str}' = {result}")
                return result
            elif operator == '!~':
                # Not contains operation
                left_str = str(left_val)
                right_str = str(right_val)
                result = right_str not in left_str
                if debug_callback:
                    debug_callback(f"Not-contains comparison '{left}' !~ '{right}': '{right_str}' not in '{left_str}' = {result}")
                return result
            elif operator in ['<', '<=', '>', '>=']:
                # Numerical comparisons
                left_num = convert_to_number(left_val)
                right_num = convert_to_number(right_val)
                
                if left_num is None or right_num is None:
                    if debug_callback:
                        debug_callback(f"Non-numerical comparison '{left}' {operator} '{right}' - treating as False")
                    return False
                
                if operator == '<':
                    result = left_num < right_num
                elif operator == '<=':
                    result = left_num <= right_num
                elif operator == '>':
                    result = left_num > right_num
                elif operator == '>=':
                    result = left_num >= right_num
                
                if debug_callback:
                    debug_callback(f"Numerical comparison '{left}' {operator} '{right}': {left_num} {operator} {right_num} = {result}")
                return result
            else:
                if debug_callback:
                    debug_callback(f"Unknown operator '{operator}' in condition '{condition}'")
                return False
                
        except Exception as e:
            if debug_callback:
                debug_callback(f"Error evaluating condition '{condition}': {str(e)}")
            return False