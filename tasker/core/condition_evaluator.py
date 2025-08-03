# tasker/core/condition_evaluator.py
"""
Condition Evaluation and Variable Replacement
---------------------------------------------
Handles variable replacement (@VARIABLE@ syntax) and condition evaluation logic.
Provides modular, testable components for the TASKER system.
"""

import re
from .utilities import convert_value, convert_to_number


class ConditionEvaluator:
    """
    Handles condition evaluation and variable replacement for TASKER tasks.
    
    This class provides stateless condition evaluation by accepting required
    data (global_vars, task_results) as parameters rather than storing state.
    """
    
    @staticmethod
    def replace_variables(text, global_vars, task_results, debug_callback=None):
        """
        Replace variables like @task_number_stdout@, @task_number_stderr@, @task_number_success@, 
        or @GLOBAL_VAR@ with actual values. Supports variable chaining like @PATH@/@SUBDIR@.
        
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
        task_result_pattern = r'@(\d+)_(stdout|stderr|success)@'
        global_var_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*)@'
        
        replaced_text = text
        unresolved_variables = []
        original_text = text
        
        # First, handle task result variables (@X_stdout@, etc.) - THREAD SAFE
        task_matches = re.findall(task_result_pattern, text)
        for task_num, output_type in task_matches:
            task_num = int(task_num)
            
            # CRITICAL: Thread-safe access to task_results
            task_result = task_results.get(task_num)
            if task_result is not None:
                if output_type == 'stdout':
                    value = task_result.get('stdout', '').rstrip('\n')
                elif output_type == 'stderr':
                    value = task_result.get('stderr', '').rstrip('\n')
                elif output_type == 'success':
                    value = str(task_result.get('success', False))
                else:
                    value = ''
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
            if re.match(r'\d+_(stdout|stderr|success)$', var_name):
                continue
                
            # Check if it's a defined global variable
            if var_name in global_vars:
                value = global_vars[var_name]
                pattern_replace = f"@{var_name}@"
                replaced_text = replaced_text.replace(pattern_replace, value)
                if debug_callback:
                    debug_callback(f"Replaced global variable @{var_name}@ with '{value}'")
            else:
                unresolved_variables.append(f"@{var_name}@")
        
        # Handle nested global variables (variable chaining support)
        # Keep replacing until no more global variables are found or max iterations reached
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            nested_matches = re.findall(global_var_pattern, replaced_text)
            nested_replaced = False
            
            for var_name in nested_matches:
                # Skip task result variables
                if re.match(r'\d+_(stdout|stderr|success)$', var_name):
                    continue
                    
                if var_name in global_vars:
                    value = global_vars[var_name]
                    pattern_replace = f"@{var_name}@"
                    replaced_text = replaced_text.replace(pattern_replace, value)
                    if debug_callback:
                        debug_callback(f"Replaced nested global variable @{var_name}@ with '{value}' (iteration {iteration})")
                    nested_replaced = True
            
            # If no nested replacements were made, we're done
            if not nested_replaced:
                break
        
        # Final check for any remaining unresolved variables
        final_matches = re.findall(global_var_pattern, replaced_text)
        for var_name in final_matches:
            if not re.match(r'\d+_(stdout|stderr|success)$', var_name):
                if var_name not in global_vars:
                    unresolved_variables.append(f"@{var_name}@")
                
        if unresolved_variables:
            if debug_callback:
                debug_callback(f"Unresolved variables in '{original_text}': {', '.join(set(unresolved_variables))}")
            return replaced_text, False
        
        if original_text != replaced_text:
            if debug_callback:
                debug_callback(f"Variable replacement: '{original_text}' -> '{replaced_text}'")
        
        return replaced_text, True

    @staticmethod
    def split_output(output, split_spec):
        """Split the output based on the specification and return the selected part."""
        if not output or not split_spec:
            return output
            
        try:
            parts = split_spec.split(':')
            if len(parts) != 2:
                return output
                
            split_type, split_value = parts
            
            if split_type == 'line':
                lines = output.split('\n')
                line_num = int(split_value)
                if 1 <= line_num <= len(lines):
                    return lines[line_num - 1]  # Convert to 0-based index
                else:
                    return ''
            elif split_type == 'word':
                words = output.split()
                word_num = int(split_value)
                if 1 <= word_num <= len(words):
                    return words[word_num - 1]  # Convert to 0-based index
                else:
                    return ''
            elif split_type == 'char':
                char_ranges = split_value.split('-')
                if len(char_ranges) == 2:
                    start = int(char_ranges[0]) - 1  # Convert to 0-based
                    end = int(char_ranges[1])
                    return output[start:end] if start >= 0 else ''
                else:
                    char_num = int(split_value)
                    if 1 <= char_num <= len(output):
                        return output[char_num - 1]  # Convert to 0-based index
                    else:
                        return ''
            else:
                return output
        except (ValueError, IndexError):
            return output

    @staticmethod
    def evaluate_condition(condition, exit_code, stdout, stderr, global_vars, task_results, debug_callback=None):
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
        
        # Handle simple conditions without boolean operators (check for |, &, AND, OR, NOT)
        if not any(op in condition for op in ['|', '&']) and not any(op in condition.upper() for op in [' AND ', ' OR ', ' NOT ']):
            return ConditionEvaluator.evaluate_simple_condition(condition, exit_code, stdout, stderr, debug_callback)
        
        # For complex conditions with boolean operators, we need to parse them
        # This is a simplified implementation that handles basic cases
        # More complex parsing would require a proper expression parser
        
        # Handle NOT operator first (highest precedence)
        condition = condition.strip()
        if condition.upper().startswith('NOT '):
            inner_condition = condition[4:].strip()
            result = not ConditionEvaluator.evaluate_simple_condition(inner_condition, exit_code, stdout, stderr, debug_callback)
            if debug_callback:
                debug_callback(f"NOT condition '{inner_condition}' evaluated to: {result}")
            return result
        
        # Handle AND operator (higher precedence than OR)
        if ' AND ' in condition.upper():
            parts = re.split(r'\s+AND\s+', condition, flags=re.IGNORECASE)
            results = []
            for part in parts:
                part_result = ConditionEvaluator.evaluate_simple_condition(part.strip(), exit_code, stdout, stderr, debug_callback)
                results.append(part_result)
                if debug_callback:
                    debug_callback(f"AND part '{part.strip()}' evaluated to: {part_result}")
            result = all(results)
            if debug_callback:
                debug_callback(f"AND condition overall result: {result}")
            return result
        
        # Handle OR operator (lowest precedence)
        if ' OR ' in condition.upper():
            parts = re.split(r'\s+OR\s+', condition, flags=re.IGNORECASE)
            results = []
            for part in parts:
                part_result = ConditionEvaluator.evaluate_simple_condition(part.strip(), exit_code, stdout, stderr, debug_callback)
                results.append(part_result)
                if debug_callback:
                    debug_callback(f"OR part '{part.strip()}' evaluated to: {part_result}")
            result = any(results)
            if debug_callback:
                debug_callback(f"OR condition overall result: {result}")
            return result
        
        # Handle | operator (OR - pipe symbol)
        if '|' in condition:
            parts = condition.split('|')
            results = []
            for part in parts:
                part_result = ConditionEvaluator.evaluate_simple_condition(part.strip(), exit_code, stdout, stderr, debug_callback)
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
                part_result = ConditionEvaluator.evaluate_simple_condition(part.strip(), exit_code, stdout, stderr, debug_callback)
                results.append(part_result)
                if debug_callback:
                    debug_callback(f"AND (&) part '{part.strip()}' evaluated to: {part_result}")
            result = all(results)
            if debug_callback:
                debug_callback(f"AND (&) condition overall result: {result}")
            return result
        
        # If no boolean operators found, treat as simple condition
        return ConditionEvaluator.evaluate_simple_condition(condition, exit_code, stdout, stderr, debug_callback)

    @staticmethod
    def evaluate_simple_condition(condition, exit_code, stdout, stderr, debug_callback=None):
        """Evaluate a simple condition without boolean operators."""
        condition = condition.strip()
        
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
        
        # Built-in string conditions
        elif condition == 'stdout_empty':
            result = not stdout.strip()
            if debug_callback:
                debug_callback(f"Stdout empty condition: stdout='{stdout.strip()}', result {result}")
            return result
        elif condition == 'stdout_not_empty':
            result = bool(stdout.strip())
            if debug_callback:
                debug_callback(f"Stdout not empty condition: stdout='{stdout.strip()}', result {result}")
            return result
        elif condition == 'stderr_empty':
            result = not stderr.strip()
            if debug_callback:
                debug_callback(f"Stderr empty condition: stderr='{stderr.strip()}', result {result}")
            return result
        elif condition == 'stderr_not_empty':
            result = bool(stderr.strip())
            if debug_callback:
                debug_callback(f"Stderr not empty condition: stderr='{stderr.strip()}', result {result}")
            return result
        
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
        if ':' in left and left not in ['stdout', 'stderr']:
            split_parts = left.split(':', 1)
            if split_parts[0] in ['stdout', 'stderr']:
                base_output = stdout if split_parts[0] == 'stdout' else stderr
                left_val = ConditionEvaluator.split_output(base_output, split_parts[1])
            else:
                left_val = convert_value(left)
        elif left == 'exit_code':
            left_val = exit_code
        elif left == 'stdout':
            left_val = stdout.rstrip('\n')
        elif left == 'stderr':
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