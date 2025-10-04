#!/usr/bin/env python3
"""
TASKER Intelligent Test Runner - Phase 1
Metadata-driven test execution and validation

Phase 1 Features:
- Basic metadata parsing from TEST_METADATA comments
- Exit code validation
- Simple test type classification
- Basic pass/fail reporting
"""

import os
import sys
import json
import re
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


class TestMetadata:
    """Parse and validate test metadata from task files."""

    def __init__(self, test_file):
        self.test_file = test_file
        self.metadata = self.parse_metadata()
        self.validate_metadata()

    def parse_metadata(self):
        """Extract TEST_METADATA JSON from comments in task file."""
        try:
            with open(self.test_file, 'r') as f:
                content = f.read()
        except Exception as e:
            return {"error": f"Failed to read test file: {e}"}

        # Extract JSON metadata from comments
        # Pattern matches: # TEST_METADATA: { ... }
        pattern = r'#\s*TEST_METADATA:\s*(\{.*?\})'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return {"error": "No TEST_METADATA found in file"}

        try:
            metadata_str = match.group(1)
            # Clean up comment prefixes from multi-line JSON
            cleaned = re.sub(r'\n\s*#\s*', '\n', metadata_str)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in TEST_METADATA: {e}"}

    def validate_metadata(self):
        """Validate that required metadata fields are present."""
        if "error" in self.metadata:
            return False

        required_fields = ["description", "test_type"]
        missing_fields = [field for field in required_fields if field not in self.metadata]

        if missing_fields:
            self.metadata["error"] = f"Missing required fields: {missing_fields}"
            return False

        # Validate test_type
        valid_types = ["positive", "negative", "validation_only", "security_negative", "performance"]
        if self.metadata["test_type"] not in valid_types:
            self.metadata["error"] = f"Invalid test_type. Must be one of: {valid_types}"
            return False

        # Phase 4: Validate security-specific metadata
        if self.metadata["test_type"] == "security_negative":
            security_fields = ["security_category", "risk_level"]
            missing_security_fields = [field for field in security_fields if field not in self.metadata]

            if missing_security_fields:
                self.metadata["error"] = f"Security tests require fields: {missing_security_fields}"
                return False

            # Validate security category
            valid_categories = [
                "command_injection", "path_traversal", "buffer_overflow",
                "format_string", "privilege_escalation", "resource_exhaustion",
                "malformed_input", "null_injection", "code_injection"
            ]
            if self.metadata["security_category"] not in valid_categories:
                self.metadata["error"] = f"Invalid security_category. Must be one of: {valid_categories}"
                return False

            # Validate risk level
            valid_risk_levels = ["low", "medium", "high", "critical"]
            if self.metadata["risk_level"] not in valid_risk_levels:
                self.metadata["error"] = f"Invalid risk_level. Must be one of: {valid_risk_levels}"
                return False

        return True

    def is_valid(self):
        """Check if metadata is valid."""
        return "error" not in self.metadata


class TaskerTestExecutor:
    """Execute TASKER test cases and capture results."""

    def __init__(self, tasker_path="./tasker.py"):
        self.tasker_path = tasker_path
        self.results = {}

    def parse_execution_path(self, stdout_content):
        """Parse task execution path from TASKER output."""
        executed_tasks = []
        skipped_tasks = []
        final_task = None
        variables = {}
        output_patterns = {"stdout": [], "stderr": []}

        # Parse task execution lines
        for line in stdout_content.split('\n'):
            # Look for task execution patterns
            if re.search(r'Task \d+: Executing', line):
                match = re.search(r'Task (\d+):', line)
                if match:
                    task_id = int(match.group(1))
                    executed_tasks.append(task_id)
                    final_task = task_id

            # Look for return task patterns
            elif re.search(r'Task \d+: Returning with exit code', line):
                match = re.search(r'Task (\d+):', line)
                if match:
                    task_id = int(match.group(1))
                    if task_id not in executed_tasks:
                        executed_tasks.append(task_id)
                    final_task = task_id

            # Look for task skipping patterns
            elif re.search(r'Task \d+:.*skipping task', line):
                match = re.search(r'Task (\d+):', line)
                if match:
                    task_id = int(match.group(1))
                    skipped_tasks.append(task_id)

            # Look for jumping patterns to infer skipped tasks
            elif re.search(r'jumping to Task \d+', line):
                match = re.search(r'jumping to Task (\d+)', line)
                if match:
                    target_task = int(match.group(1))
                    # Find the task that's doing the jumping
                    jump_line_match = re.search(r'Task (\d+):', line)
                    if jump_line_match:
                        current_task = int(jump_line_match.group(1))
                        # Infer skipped tasks between current and target
                        for skip_task in range(current_task + 1, target_task):
                            if skip_task not in skipped_tasks:
                                skipped_tasks.append(skip_task)

            # Capture task output for variable validation (Phase 3)
            elif re.search(r'Task \d+: STDOUT:', line):
                match = re.search(r'Task (\d+): STDOUT: (.+)', line)
                if match:
                    task_id = match.group(1)
                    stdout_value = match.group(2)
                    variables[f"{task_id}_stdout"] = stdout_value
                    # Add to output patterns for pattern matching
                    output_patterns["stdout"].append(stdout_value)

            elif re.search(r'Task \d+: STDERR:', line):
                match = re.search(r'Task (\d+): STDERR: (.+)', line)
                if match:
                    task_id = match.group(1)
                    stderr_value = match.group(2)
                    variables[f"{task_id}_stderr"] = stderr_value
                    # Add to output patterns for pattern matching
                    output_patterns["stderr"].append(stderr_value)

        return {
            "executed_tasks": executed_tasks,
            "skipped_tasks": skipped_tasks,
            "final_task": final_task,
            "variables": variables,
            "output_patterns": output_patterns
        }

    def execute_test(self, test_file, metadata):
        """Execute a single test case and capture results."""
        test_name = os.path.basename(test_file)

        # Prepare command arguments based on test type
        cmd_args = [self.tasker_path, test_file]

        if metadata.get("validation_only", False):
            cmd_args.append("--validate-only")
        else:
            cmd_args.append("-r")  # Run mode

        # Always skip host validation for test execution
        cmd_args.append("--skip-host-validation")

        # Set environment for supporting scripts
        env = os.environ.copy()
        test_dir = os.path.dirname(os.path.abspath(test_file))
        bin_dir = os.path.join(os.path.dirname(test_dir), "bin")
        if os.path.exists(bin_dir):
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        # Execute the test
        start_time = datetime.now()
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                env=env,
                timeout=60  # 60 second timeout for tests
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # Parse execution path from output
            execution_path_data = self.parse_execution_path(result.stdout)

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "timed_out": False,
                "error": None,
                "execution_path": execution_path_data
            }

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": "Test execution timeout",
                "execution_time": execution_time,
                "timed_out": True,
                "error": "Timeout after 60 seconds",
                "execution_path": {"executed_tasks": [], "skipped_tasks": [], "final_task": None}
            }
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": execution_time,
                "timed_out": False,
                "error": f"Execution error: {e}",
                "execution_path": {"executed_tasks": [], "skipped_tasks": [], "final_task": None}
            }


class TestValidator:
    """Validate test execution results against metadata expectations."""

    def validate_execution_results(self, metadata, actual_results):
        """Compare expected vs actual results."""
        validation_results = {
            "passed": True,
            "failures": [],
            "warnings": []
        }

        # Skip validation if there was an execution error
        if actual_results.get("error"):
            validation_results["passed"] = False
            validation_results["failures"].append(f"Execution error: {actual_results['error']}")
            return validation_results

        # Validate exit code
        if "expected_exit_code" in metadata:
            expected_exit = metadata["expected_exit_code"]
            actual_exit = actual_results["exit_code"]

            if actual_exit != expected_exit:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Exit code mismatch: expected {expected_exit}, got {actual_exit}"
                )

        # Validate success expectation
        if "expected_success" in metadata:
            expected_success = metadata["expected_success"]
            actual_success = (actual_results["exit_code"] == 0)

            if actual_success != expected_success:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Success expectation mismatch: expected {expected_success}, got {actual_success}"
                )

        # Validate execution path (Phase 2 feature)
        execution_path = actual_results.get("execution_path", {})

        if "expected_execution_path" in metadata:
            expected_path = metadata["expected_execution_path"]
            actual_path = execution_path.get("executed_tasks", [])

            if actual_path != expected_path:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Execution path mismatch: expected {expected_path}, got {actual_path}"
                )

        if "expected_skipped_tasks" in metadata:
            expected_skipped = metadata["expected_skipped_tasks"]
            actual_skipped = execution_path.get("skipped_tasks", [])

            if actual_skipped != expected_skipped:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Skipped tasks mismatch: expected {expected_skipped}, got {actual_skipped}"
                )

        if "expected_final_task" in metadata:
            expected_final = metadata["expected_final_task"]
            actual_final = execution_path.get("final_task")

            if actual_final != expected_final:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Final task mismatch: expected {expected_final}, got {actual_final}"
                )

        # Validate timeout expectation
        if "timeout_expected" in metadata:
            expected_timeout = metadata["timeout_expected"]
            actual_timeout = actual_results["timed_out"]

            if actual_timeout != expected_timeout:
                if expected_timeout:
                    validation_results["passed"] = False
                    validation_results["failures"].append("Expected timeout but test completed")
                else:
                    validation_results["passed"] = False
                    validation_results["failures"].append("Unexpected timeout occurred")

        # Validate variables (Phase 3 feature)
        if "expected_variables" in metadata:
            expected_variables = metadata["expected_variables"]
            actual_variables = execution_path.get("variables", {})

            for var_name, expected_value in expected_variables.items():
                if var_name not in actual_variables:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Variable '{var_name}' not found in execution results"
                    )
                elif actual_variables[var_name] != expected_value:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Variable '{var_name}' mismatch: expected '{expected_value}', got '{actual_variables[var_name]}'"
                    )

        # Validate output patterns (enhanced Phase 3 implementation)
        if "expected_output_patterns" in metadata:
            patterns = metadata["expected_output_patterns"]
            actual_patterns = execution_path.get("output_patterns", {"stdout": [], "stderr": []})

            if "stdout" in patterns:
                for pattern in patterns["stdout"]:
                    # Check both in raw output and captured patterns
                    found_in_raw = pattern in actual_results["stdout"]
                    found_in_patterns = any(pattern in output for output in actual_patterns["stdout"])

                    if not found_in_raw and not found_in_patterns:
                        validation_results["warnings"].append(
                            f"Expected stdout pattern '{pattern}' not found"
                        )

            if "stderr" in patterns:
                for pattern in patterns["stderr"]:
                    # Check both in raw output and captured patterns
                    found_in_raw = pattern in actual_results["stderr"]
                    found_in_patterns = any(pattern in output for output in actual_patterns["stderr"])

                    if not found_in_raw and not found_in_patterns:
                        validation_results["warnings"].append(
                            f"Expected stderr pattern '{pattern}' not found"
                        )

        # Special handling for negative tests
        if metadata.get("test_type") == "negative":
            if actual_results["exit_code"] == 0:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    "Negative test should fail but succeeded (exit code 0)"
                )

        # Phase 4: Advanced security test validation
        if metadata.get("test_type") == "security_negative":
            # Basic security validation
            if actual_results["exit_code"] == 0:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    "Security test should be rejected but was accepted"
                )

            # Validate rejection phase
            if "expected_rejection_phase" in metadata:
                expected_phase = metadata["expected_rejection_phase"]
                if expected_phase == "validation":
                    # Should fail during validation (before execution)
                    if "Task validation FAILED" not in actual_results["stdout"]:
                        validation_results["warnings"].append(
                            "Expected validation phase rejection but may have failed during execution"
                        )

            # Validate security error patterns
            if "expected_error_patterns" in metadata:
                error_patterns = metadata["expected_error_patterns"]
                combined_output = actual_results["stdout"] + " " + actual_results["stderr"]

                for pattern in error_patterns:
                    if pattern.lower() not in combined_output.lower():
                        validation_results["warnings"].append(
                            f"Expected security error pattern '{pattern}' not found in output"
                        )

            # Security category-specific validation
            security_category = metadata.get("security_category", "")
            risk_level = metadata.get("risk_level", "")

            if security_category == "command_injection":
                # Should reject shell metacharacters
                dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
                if actual_results["exit_code"] == 0:
                    validation_results["failures"].append(
                        f"Command injection attempt with dangerous characters should be rejected"
                    )

            elif security_category == "path_traversal":
                # Should reject path traversal attempts
                traversal_patterns = ["../", "..\\", "%2e%2e", "..%2f"]
                if actual_results["exit_code"] == 0:
                    validation_results["failures"].append(
                        f"Path traversal attempt should be rejected"
                    )

            # Risk level validation (critical/high should always fail immediately)
            if risk_level in ["critical", "high"] and actual_results["exit_code"] == 0:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Critical/High risk security test must be rejected (risk_level: {risk_level})"
                )

        return validation_results


class IntelligentTestRunner:
    """Main test runner orchestrator."""

    def __init__(self, tasker_path="./tasker.py"):
        self.tasker_path = tasker_path
        self.executor = TaskerTestExecutor(tasker_path)
        self.validator = TestValidator()
        self.results = []

    def run_single_test(self, test_file):
        """Run a single test file and validate results."""
        test_name = os.path.basename(test_file)
        print(f"Running test: {test_name}")

        # Parse metadata
        metadata_parser = TestMetadata(test_file)
        if not metadata_parser.is_valid():
            return {
                "test_name": test_name,
                "test_file": test_file,
                "status": "METADATA_ERROR",
                "error": metadata_parser.metadata.get("error"),
                "execution_time": 0
            }

        metadata = metadata_parser.metadata
        print(f"  Description: {metadata.get('description', 'N/A')}")
        print(f"  Test Type: {metadata.get('test_type', 'N/A')}")

        # Execute test
        execution_results = self.executor.execute_test(test_file, metadata)

        # Validate results
        validation_results = self.validator.validate_execution_results(metadata, execution_results)

        # Compile final result
        result = {
            "test_name": test_name,
            "test_file": test_file,
            "metadata": metadata,
            "execution_results": execution_results,
            "validation_results": validation_results,
            "status": "PASSED" if validation_results["passed"] else "FAILED",
            "execution_time": execution_results.get("execution_time", 0)
        }

        self.results.append(result)
        return result

    def run_tests_in_directory(self, directory, recursive=False):
        """Run all test files in a directory."""
        test_files = []

        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.txt'):
                        test_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if file.endswith('.txt'):
                    test_files.append(os.path.join(directory, file))

        test_files.sort()

        print(f"Found {len(test_files)} test files")
        print("=" * 60)

        for test_file in test_files:
            result = self.run_single_test(test_file)
            self.print_result_summary(result)
            print("-" * 60)

    def print_result_summary(self, result):
        """Print a summary of test result."""
        status = result["status"]
        name = result["test_name"]
        time = result["execution_time"]

        status_icon = "✅" if status == "PASSED" else "❌"
        print(f"{status_icon} {name} ({status}) - {time:.2f}s")

        # Show execution path info for passed tests (if available)
        if status == "PASSED" and "execution_results" in result:
            execution_path = result["execution_results"].get("execution_path", {})
            executed_tasks = execution_path.get("executed_tasks", [])
            if executed_tasks:
                print(f"    EXECUTION PATH: {executed_tasks}")

            # Show variables if captured (Phase 3)
            variables = execution_path.get("variables", {})
            if variables:
                var_display = ", ".join([f"{k}='{v}'" for k, v in list(variables.items())[:3]])
                if len(variables) > 3:
                    var_display += f" (+{len(variables)-3} more)"
                print(f"    VARIABLES: {var_display}")

        # Show security information for security tests (Phase 4)
        if "metadata" in result and result["metadata"].get("test_type") == "security_negative":
            metadata = result["metadata"]
            security_category = metadata.get("security_category", "N/A")
            risk_level = metadata.get("risk_level", "N/A")

            # Risk level with color coding
            risk_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(risk_level, "⚫")
            print(f"    SECURITY: {security_category.upper()} {risk_icon} {risk_level.upper()}")

            if status == "PASSED":
                print(f"    RESULT: ✅ Correctly rejected malicious input")

        if status == "FAILED":
            failures = result["validation_results"]["failures"]
            for failure in failures:
                print(f"    FAILURE: {failure}")

        if status == "METADATA_ERROR":
            print(f"    ERROR: {result['error']}")

        warnings = result.get("validation_results", {}).get("warnings", [])
        for warning in warnings:
            print(f"    WARNING: {warning}")

    def generate_summary_report(self):
        """Generate and print summary report."""
        if not self.results:
            print("No tests executed.")
            return

        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASSED"])
        failed_tests = len([r for r in self.results if r["status"] == "FAILED"])
        error_tests = len([r for r in self.results if r["status"] == "METADATA_ERROR"])

        total_time = sum(r["execution_time"] for r in self.results)

        print("\n" + "=" * 60)
        print("TASKER INTELLIGENT TEST RUNNER - SUMMARY REPORT")
        print("=" * 60)
        print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {total_time:.2f} seconds")
        print()
        print("RESULTS:")
        print(f"✅ PASSED: {passed_tests}/{total_tests} tests")
        print(f"❌ FAILED: {failed_tests}/{total_tests} tests")
        print(f"🚫 ERRORS: {error_tests}/{total_tests} tests")
        print()

        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAILED":
                    print(f"  • {result['test_name']}")
                    for failure in result["validation_results"]["failures"]:
                        print(f"    - {failure}")
            print()

        if error_tests > 0:
            print("ERROR TESTS:")
            for result in self.results:
                if result["status"] == "METADATA_ERROR":
                    print(f"  • {result['test_name']}: {result['error']}")
            print()

        # Overall result
        if failed_tests == 0 and error_tests == 0:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("❌ SOME TESTS FAILED!")
            return 1


def main():
    """Main entry point for the intelligent test runner."""
    parser = argparse.ArgumentParser(
        description="TASKER Intelligent Test Runner - Metadata-driven test validation"
    )
    parser.add_argument(
        "target",
        help="Test file or directory to run"
    )
    parser.add_argument(
        "--tasker-path",
        default="./tasker.py",
        help="Path to tasker.py executable (default: ./tasker.py)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Recursively search for test files in subdirectories"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = IntelligentTestRunner(args.tasker_path)

    # Check if target is file or directory
    if os.path.isfile(args.target):
        result = runner.run_single_test(args.target)
        runner.print_result_summary(result)
    elif os.path.isdir(args.target):
        runner.run_tests_in_directory(args.target, args.recursive)
    else:
        print(f"Error: '{args.target}' is not a valid file or directory")
        return 1

    # Generate summary report
    exit_code = runner.generate_summary_report()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())