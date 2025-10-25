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
            Masked string in format "<masked len=N>"

        Example:
            mask_value('super_secret_123') -> '<masked len=16>'
        """
        try:
            value_len = len(str(value))
        except Exception:
            value_len = -1
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
                    value = task_result.get('stdout', '').rstrip('\n')
                elif output_type_lower == 'stderr':
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
            'space': r'\s+',
            'tab': r'\t+',
            'newline': r'\n+',       # NEW - CRITICAL! Split by one or more line breaks (consistent with space/tab)
            'colon': ':',            # NEW - Common in config files (/etc/passwd, etc)
            'semicolon': ';',        # NEW - Better naming than 'semi'
            'semi': ';',             # Keep for backward compatibility
            'comma': ',',
            'pipe': r'\|'            # FIXED: Pipe needs escaping in regex
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
        # IMPORTANT: _count patterns use operators as part of their syntax (e.g., stdout_count=3, stdout_count<5)
        # so we must check for _count BEFORE blocking based on operators
        # CASE INSENSITIVE: Accept both 'stdout' and 'STDOUT' for user convenience
        if condition.lower().startswith('stdout') and ('_count' in condition.lower() or not any(op in condition for op in ['=', '!=', '<', '<=', '>', '>='])):
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
                pattern = condition.split('~', 1)[1]
                if condition_lower.startswith('stdout!~'):
                    result = pattern not in stdout
                    if debug_callback:
                        debug_callback(f"Stdout pattern not match: '{pattern}' is {'absent' if result else 'present'} in '{stdout_stripped}'")
                    return result
                else:
                    result = pattern in stdout
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
        # CASE INSENSITIVE: Accept both 'stderr' and 'STDERR' for user convenience
        if condition.lower().startswith('stderr') and ('_count' in condition.lower() or not any(op in condition for op in ['=', '!=', '<', '<=', '>', '>='])):
            stderr_stripped = stderr.rstrip('\n')
            condition_lower = condition.lower()
            if condition_lower == 'stderr~':
                result = stderr.strip() == ''
                if debug_callback:
                    debug_callback(f"Stderr empty check: '{stderr.strip()}' is {'empty' if result else 'not empty'}")
                return result
            elif condition_lower == 'stderr!~':
                result = stderr.strip() != ''
                if debug_callback:
                    debug_callback(f"Stderr not empty check: '{stderr.strip()}' is {'not empty' if result else 'empty'}")
                return result
            elif '~' in condition:
                pattern = condition.split('~', 1)[1]
                if condition_lower.startswith('stderr!~'):
                    result = pattern not in stderr
                    if debug_callback:
                        debug_callback(f"Stderr pattern not match: '{pattern}' is {'absent' if result else 'present'} in '{stderr_stripped}'")
                    return result
                else:
                    result = pattern in stderr
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
                    stderr_stripped = stderr.strip()
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
    def evaluate_operator_comparison(condition, exit_code, stdout, stderr, debug_callback=None):
        """Evaluate conditions with comparison operators (=, !=, ~, !~, <, <=, >, >=)."""
        # Split on operators (order matters - check longer operators first)
        operators = ['!=', '!~', '<=', '>=', '=', '~', '<', '>']
        
        operator = None
        left = None
        right = None
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    operator = op
                    break
        
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