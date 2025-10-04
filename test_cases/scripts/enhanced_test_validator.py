#!/usr/bin/env python
"""
Enhanced Test Validator for TASKER
==================================

Provides comprehensive validation beyond exit codes:
- Variable resolution validation
- Execution path validation
- Log content analysis
- Expected vs actual behavior comparison
- Pattern-based regression detection

This catches issues that simple exit code checking misses.
"""

import re
import os
import sys
import json
import subprocess
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class TestExpectation:
    """Expected behavior for a test case."""

    def __init__(self, expected_exec_type="local", expected_exit_code=0, expected_hostname="localhost",
                 variables_must_resolve=None, tasks_should_execute=None, tasks_should_skip=None,
                 forbidden_patterns=None, required_patterns=None, expected_commands=None, expected_outputs=None):
        # Variable resolution expectations
        self.expected_exec_type = expected_exec_type
        self.expected_exit_code = expected_exit_code
        self.expected_hostname = expected_hostname
        self.variables_must_resolve = variables_must_resolve or []

        # Execution expectations
        self.tasks_should_execute = tasks_should_execute or []
        self.tasks_should_skip = tasks_should_skip or []

        # Pattern expectations
        self.forbidden_patterns = forbidden_patterns or [
            "Unknown execution type",
            "Unresolved variables",
            "[Errno 2] No such file or directory",
            "evaluated to FALSE, skipping task"
        ]
        self.required_patterns = required_patterns or []

        # Output expectations
        self.expected_commands = expected_commands or []
        self.expected_outputs = expected_outputs or []


class TestValidator:
    """Comprehensive test validation system."""

    def __init__(self, test_scripts_path: Optional[str] = None, tasker_path: Optional[str] = None):
        script_dir = Path(__file__).resolve().parent
        if test_scripts_path is None:
            test_scripts_path = str((script_dir.parent / "bin").resolve())
        if tasker_path is None:
            tasker_path = str((script_dir.parent.parent / "tasker.py").resolve())
        self.test_scripts_path = test_scripts_path
        self.tasker_path = tasker_path
        self.failed_validations = []

    def validate_test(self, test_file: str, expectation: TestExpectation = None) -> Tuple[bool, Dict]:
        """
        Run comprehensive validation on a test case.

        Returns:
            (success, validation_results)
        """
        if expectation is None:
            expectation = self._get_default_expectation(test_file)

        print(f"🔍 COMPREHENSIVE VALIDATION: {test_file}")

        # Run the test and capture full output
        success, log_content, exit_code = self._run_test(test_file)

        results = {
            "test_file": test_file,
            "exit_code": exit_code,
            "basic_success": success,
            "validations": {}
        }

        # Layer 1: Variable Resolution Validation
        results["validations"]["variable_resolution"] = self._validate_variable_resolution(
            log_content, expectation
        )

        # Layer 2: Execution Type Validation
        results["validations"]["execution_type"] = self._validate_execution_type(
            log_content, expectation
        )

        # Layer 3: Task Execution Validation
        results["validations"]["task_execution"] = self._validate_task_execution(
            log_content, expectation
        )

        # Layer 4: Pattern Validation
        results["validations"]["patterns"] = self._validate_patterns(
            log_content, expectation
        )

        # Layer 5: Content Validation
        results["validations"]["content"] = self._validate_content(
            log_content, expectation
        )

        # Overall validation result
        all_validations_passed = all(
            v.get("passed", False) for v in results["validations"].values()
        )

        results["comprehensive_success"] = all_validations_passed

        # Report results
        self._report_results(test_file, results)

        return all_validations_passed, results

    def _run_test(self, test_file: str) -> Tuple[bool, str, int]:
        """Run test and capture complete output."""
        env = os.environ.copy()
        env["PATH"] = f"{self.test_scripts_path}:{env.get('PATH', '')}"

        cmd = [
            self.tasker_path,
            test_file,
            "-r",
            "--skip-host-validation",
            "--log-level=DEBUG"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )

            log_content = result.stdout + result.stderr
            return result.returncode == 0, log_content, result.returncode

        except subprocess.TimeoutExpired:
            return False, "TEST TIMEOUT", 124
        except Exception as e:
            return False, f"TEST ERROR: {e}", 1

    def _validate_variable_resolution(self, log_content: str, expectation: TestExpectation) -> Dict:
        """Validate that variables are properly resolved."""
        issues = []

        # Check for unresolved variables
        unresolved_pattern = r"Unresolved variables.*?(@\w+@)"
        unresolved_matches = re.findall(unresolved_pattern, log_content)

        if unresolved_matches:
            issues.append(f"Unresolved variables found: {set(unresolved_matches)}")

        # Check for @ symbols in final command execution (shouldn't be there)
        execution_pattern = r"Task \d+: Executing.*?(@\w+@)"
        execution_matches = re.findall(execution_pattern, log_content)

        if execution_matches:
            issues.append(f"Variables not resolved in execution: {set(execution_matches)}")

        # Check specific variables that must resolve
        for var in expectation.variables_must_resolve:
            if f"@{var}@" in log_content:
                # Check if it appears in final execution (bad) vs just parsing (ok)
                if re.search(rf"Task \d+: Executing.*@{var}@", log_content):
                    issues.append(f"Variable @{var}@ not resolved in execution")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "type": "Variable Resolution"
        }

    def _validate_execution_type(self, log_content: str, expectation: TestExpectation) -> Dict:
        """Validate execution type is correct."""
        issues = []

        # Check for wrong execution type warnings
        if f"Unknown execution type" in log_content:
            issues.append("Unknown execution type detected - variables not resolved")

        # Check actual execution commands match expected type
        execution_pattern = r"Task \d+: Executing \[(\w+)\]:"
        exec_types = re.findall(execution_pattern, log_content)

        if exec_types and expectation.expected_exec_type:
            wrong_types = [t for t in exec_types if t != expectation.expected_exec_type]
            if wrong_types:
                issues.append(f"Wrong execution types: {wrong_types}, expected: {expectation.expected_exec_type}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "found_types": exec_types,
            "type": "Execution Type"
        }

    def _validate_task_execution(self, log_content: str, expectation: TestExpectation) -> Dict:
        """Validate task execution sequence."""
        issues = []

        # Find executed tasks
        executed_pattern = r"Task (\d+): Executing"
        executed_tasks = [int(t) for t in re.findall(executed_pattern, log_content)]

        # Find skipped tasks
        skipped_pattern = r"Task (\d+): Condition.*evaluated to FALSE, skipping task"
        skipped_tasks = [int(t) for t in re.findall(skipped_pattern, log_content)]

        # Validate expected executions
        for task_id in expectation.tasks_should_execute:
            if task_id not in executed_tasks:
                issues.append(f"Task {task_id} should have executed but didn't")

        # Validate expected skips
        for task_id in expectation.tasks_should_skip:
            if task_id not in skipped_tasks:
                issues.append(f"Task {task_id} should have been skipped but executed")

        # Check for unexpected skips
        unexpected_skips = [t for t in skipped_tasks if t not in expectation.tasks_should_skip]
        if unexpected_skips:
            issues.append(f"Unexpected task skips: {unexpected_skips}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "executed_tasks": executed_tasks,
            "skipped_tasks": skipped_tasks,
            "type": "Task Execution"
        }

    def _validate_patterns(self, log_content: str, expectation: TestExpectation) -> Dict:
        """Validate forbidden and required patterns."""
        issues = []

        # Check forbidden patterns
        for pattern in expectation.forbidden_patterns:
            if re.search(pattern, log_content, re.IGNORECASE):
                issues.append(f"Forbidden pattern found: '{pattern}'")

        # Check required patterns
        for pattern in expectation.required_patterns:
            if not re.search(pattern, log_content, re.IGNORECASE):
                issues.append(f"Required pattern missing: '{pattern}'")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "type": "Pattern Validation"
        }

    def _validate_content(self, log_content: str, expectation: TestExpectation) -> Dict:
        """Validate expected content and outputs."""
        issues = []

        # Check for expected commands
        for expected_cmd in expectation.expected_commands:
            if expected_cmd not in log_content:
                issues.append(f"Expected command not found: '{expected_cmd}'")

        # Check for expected outputs
        for expected_output in expectation.expected_outputs:
            if expected_output not in log_content:
                issues.append(f"Expected output not found: '{expected_output}'")

        # Check for error indicators
        error_patterns = [
            r"Error executing command",
            r"STDERR:.*Errno",
            r"Exit code: [^0]\d*",  # Non-zero exit codes
        ]

        for pattern in error_patterns:
            matches = re.findall(pattern, log_content)
            if matches:
                issues.append(f"Error indicator found: {matches}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "type": "Content Validation"
        }

    def _get_default_expectation(self, test_file: str) -> TestExpectation:
        """Get default expectations based on test file name/content."""

        # Default expectations for simple_test.txt
        if "simple_test" in test_file:
            return TestExpectation(
                expected_exec_type="local",
                expected_hostname="localhost",
                variables_must_resolve=["EXEC", "HOSTNAME", "PATH_BASE", "SUBDIR"],
                tasks_should_execute=[0, 1],
                tasks_should_skip=[],
                expected_commands=[
                    "echo Testing /tmp/test/data",
                    "mkdir -p /tmp/test/data"
                ],
                required_patterns=[
                    r"Task 0: Executing \[local\]:",
                    r"Task 1: Executing \[local\]:",
                    r"SUCCESS: Task execution completed"
                ]
            )

        # Default for comprehensive globals test
        elif "comprehensive_globals" in test_file:
            return TestExpectation(
                expected_exec_type="local",
                variables_must_resolve=["EXEC", "HOSTNAME", "VERSION", "BUILD_NUMBER"],
                tasks_should_execute=list(range(5)),
                required_patterns=[
                    r"Starting test version .* build .* with user",
                    r"All tests passed for .* version"
                ]
            )

        # Generic default
        return TestExpectation()

    def _report_results(self, test_file: str, results: Dict):
        """Report validation results."""
        basic_success = results["basic_success"]
        comprehensive_success = results["comprehensive_success"]

        if comprehensive_success:
            print(f"  ✅ COMPREHENSIVE PASS: All validations passed")
        else:
            print(f"  ❌ COMPREHENSIVE FAIL: Validation issues detected")
            if basic_success:
                print(f"  ⚠️  EXIT CODE PASS but BEHAVIOR FAIL - This is a FALSE POSITIVE!")

            # Report each validation layer
            for layer, validation in results["validations"].items():
                if not validation["passed"]:
                    print(f"    ❌ {validation['type']}: {len(validation['issues'])} issues")
                    for issue in validation["issues"]:
                        print(f"       • {issue}")

def main():
    """Run enhanced validation on test cases."""
    validator = TestValidator()

    # Test representative files from organized structure
    script_dir = Path(__file__).resolve().parent
    test_root = script_dir.parent
    test_files = [
        str((test_root / "functional" / "simple_test.txt").resolve()),
        str((test_root / "integration" / "comprehensive_globals_test.txt").resolve()),
        str((test_root / "functional" / "clean_parallel_test.txt").resolve()),
        str((test_root / "edge_cases" / "simple_sleep_test.txt").resolve()),
        str((test_root / "integration" / "conditional_comprehensive_test.txt").resolve())
    ]

    print("🔬 ENHANCED TEST VALIDATION")
    print("=" * 50)

    all_passed = True

    for test_file in test_files:
        if os.path.exists(test_file):
            passed, results = validator.validate_test(test_file)
            all_passed = all_passed and passed
            print()
        else:
            print(f"⚠️  Test file not found: {test_file}")

    print("=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED COMPREHENSIVE VALIDATION")
    else:
        print("❌ SOME TESTS FAILED COMPREHENSIVE VALIDATION")
        print("   This would have caught the global variable regression!")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())