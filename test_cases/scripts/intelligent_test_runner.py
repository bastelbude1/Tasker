#!/usr/bin/env python
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
import threading
import time
import shutil
from datetime import datetime
from pathlib import Path

# External dependencies are not allowed per CLAUDE.md guidelines
# Python 3.6.8 standard library only - no psutil
PSUTIL_AVAILABLE = False


def _resolve_tasker_path(tasker_path=None):
    """Resolve tasker executable path using PATH discovery with fallbacks."""
    if tasker_path is None:
        # First try to find 'tasker' in PATH
        resolved = shutil.which("tasker")
        if resolved is None:
            # Fallback to tasker.py in current directory if not in PATH
            if os.path.exists("./tasker.py"):
                resolved = "./tasker.py"
            elif os.path.exists("../tasker.py"):
                # Also check parent directory (common when running from test_cases/)
                resolved = "../tasker.py"
            else:
                # Last resort - use ./tasker.py and let it fail with clear error
                resolved = "./tasker.py"
                print("WARNING: Could not find 'tasker' in PATH or './tasker.py'")
                print(f"         Using default: {resolved}")
        return resolved
    return tasker_path


def _collect_test_files(target_path, recursive=False):
    """Collect .txt test files from a directory."""
    test_files = []
    if recursive:
        for root, _dirs, files in os.walk(target_path):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        test_files.append(file_path)
    else:
        for file in os.listdir(target_path):
            file_path = os.path.join(target_path, file)
            if file.endswith('.txt') and os.path.isfile(file_path):
                test_files.append(file_path)
    return test_files


class PerformanceMonitor:
    """Monitor system performance and resource usage during test execution."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.peak_memory_mb = 0
        self.peak_cpu_percent = 0
        self.monitoring = False
        self.monitor_thread = None
        self.process = None
        self.task_timings = {}

    def start_monitoring(self, process):
        """Start monitoring system resources for a process."""
        self.process = process
        self.start_time = time.time()
        self.monitoring = True
        self.peak_memory_mb = 0
        self.peak_cpu_percent = 0

        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring and return performance metrics."""
        self.monitoring = False
        self.end_time = time.time()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        return {
            "execution_time": self.end_time - self.start_time,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "task_timings": self.task_timings.copy()
        }

    def _monitor_resources(self):
        """Monitor resources in background thread - inspired by parallelr.py patterns."""
        if not PSUTIL_AVAILABLE:
            return

        try:
            # Monitor the TASKER subprocess process, not the test runner process
            if self.process:
                target_process = psutil.Process(self.process.pid)
            else:
                return

            while self.monitoring:
                try:
                    # Monitor subprocess resources (following parallelr.py pattern)
                    memory_mb = target_process.memory_info().rss / (1024 * 1024)
                    cpu_percent = target_process.cpu_percent(interval=0)  # Non-blocking

                    # Update peaks (parallelr.py pattern)
                    if memory_mb > self.peak_memory_mb:
                        self.peak_memory_mb = memory_mb
                    if cpu_percent > self.peak_cpu_percent:
                        self.peak_cpu_percent = cpu_percent

                    time.sleep(0.1)  # Sample every 100ms

                except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                    # Process ended or no permission (parallelr.py pattern)
                    break
                except Exception:
                    # Unexpected error - graceful degradation
                    break

        except Exception:
            # Monitoring setup failed - graceful degradation
            pass

    def parse_task_timings(self, stdout_content):
        """Parse individual task execution times from TASKER output."""
        task_timings = {}
        current_task = None
        task_start_time = None

        for line in stdout_content.split('\n'):
            # Look for task execution start
            task_match = re.search(r'\[(\d{2}\w{3}\d{2} \d{2}:\d{2}:\d{2})\] Task (\d+): Executing', line)
            if task_match:
                timestamp_str = task_match.group(1)
                task_id = int(task_match.group(2))

                try:
                    # Parse timestamp (format: 04Oct25 18:30:45)
                    task_start_time = datetime.strptime(timestamp_str, '%d%b%y %H:%M:%S')
                    current_task = task_id
                except ValueError:
                    continue

            # Look for task completion
            if current_task is not None and task_start_time:
                completion_match = re.search(r'\[(\d{2}\w{3}\d{2} \d{2}:\d{2}:\d{2})\] Task ' + str(current_task) + r': Exit code:', line)
                if completion_match:
                    timestamp_str = completion_match.group(1)
                    try:
                        task_end_time = datetime.strptime(timestamp_str, '%d%b%y %H:%M:%S')
                        duration = (task_end_time - task_start_time).total_seconds()
                        task_timings[current_task] = duration
                        current_task = None
                        task_start_time = None
                    except ValueError:
                        continue

        return task_timings


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
        # Pattern matches: # TEST_METADATA: { ... } on single line
        pattern = r'#\s*TEST_METADATA:\s*(\{[^}]*\}(?:\s*[^#\n]*[^#\n])*)'
        for line in content.split('\n'):
            if 'TEST_METADATA:' in line:
                # Find the JSON part of the line
                start_idx = line.find('{')
                if start_idx != -1:
                    json_str = line[start_idx:]
                    # Find the end of the JSON object
                    brace_count = 0
                    end_idx = -1
                    for i, char in enumerate(json_str):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    if end_idx != -1:
                        metadata_str = json_str[:end_idx]
                        try:
                            return json.loads(metadata_str)
                        except json.JSONDecodeError as e:
                            return {"error": f"Invalid JSON in TEST_METADATA: {e}"}

        return {"error": "No TEST_METADATA found in file"}

    def validate_metadata(self):
        """Validate that required metadata fields are present."""
        if "error" in self.metadata:
            return False

        required_fields = ["description", "test_type", "expected_exit_code", "expected_success"]
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

        # Validate logical consistency between test_type and expected results
        if "expected_success" in self.metadata and "expected_exit_code" in self.metadata:
            test_type = self.metadata["test_type"]
            expected_success = self.metadata["expected_success"]
            expected_exit_code = self.metadata["expected_exit_code"]

            # Positive tests should expect success (exit 0)
            if test_type == "positive":
                if not expected_success:
                    self.metadata["error"] = f"Inconsistent metadata: test_type='positive' but expected_success=false"
                    return False
                if expected_exit_code != 0:
                    self.metadata["error"] = f"Inconsistent metadata: test_type='positive' but expected_exit_code={expected_exit_code} (should be 0)"
                    return False

            # Negative tests should expect failure (non-zero exit)
            elif test_type == "negative":
                if expected_success:
                    self.metadata["error"] = f"Inconsistent metadata: test_type='negative' but expected_success=true"
                    return False
                if expected_exit_code == 0:
                    self.metadata["error"] = f"Inconsistent metadata: test_type='negative' but expected_exit_code=0 (should be non-zero)"
                    return False

            # Security negative tests should expect failure with exit code 20
            elif test_type == "security_negative":
                if expected_success:
                    self.metadata["error"] = f"Inconsistent metadata: test_type='security_negative' but expected_success=true"
                    return False
                if expected_exit_code != 20:
                    self.metadata["error"] = f"Inconsistent metadata: security_negative must use expected_exit_code=20 (validation failure)"
                    return False

        # Phase 5: Validate performance-specific metadata
        if self.metadata["test_type"] == "performance":
            # Validate performance benchmarks
            if "performance_benchmarks" in self.metadata:
                benchmarks = self.metadata["performance_benchmarks"]
                required_benchmarks = ["max_execution_time"]
                missing_benchmarks = [field for field in required_benchmarks if field not in benchmarks]

                if missing_benchmarks:
                    self.metadata["error"] = f"Performance tests require benchmarks: {missing_benchmarks}"
                    return False

                # Validate benchmark values
                for key, value in benchmarks.items():
                    if not isinstance(value, (int, float)) or value <= 0:
                        self.metadata["error"] = f"Performance benchmark '{key}' must be a positive number"
                        return False

        return True

    def is_valid(self):
        """Check if metadata is valid."""
        return "error" not in self.metadata


class TaskerTestExecutor:
    """Execute TASKER test cases and capture results."""

    def __init__(self, tasker_path=None):
        self.tasker_path = _resolve_tasker_path(tasker_path)
        self.results = {}
        self.performance_monitor = PerformanceMonitor()

    def parse_execution_path(self, stdout_content):
        """Parse task execution path from TASKER output."""
        executed_tasks = []
        loop_execution_path = []  # Track loop iterations like "0.1", "0.2", "0.3"
        executed_subtasks = []  # Track conditional/parallel subtasks separately
        retry_execution_path = []  # Track retry attempts like "1-10.1", "1-10.2", "1-11.1"
        skipped_tasks = []
        final_task = None
        variables = {}
        output_patterns = {"stdout": [], "stderr": []}

        # Parse task execution lines
        for line in stdout_content.split('\n'):
            # Look for retry attempt patterns (Task 1-10.1, Task 1-10.2 format) - HIGHEST PRIORITY
            # Match patterns like "Task 1-10.1: Executing" or "Task 1-10.2: FAILED"
            # Must check before subtask pattern to avoid false matches
            retry_match = re.search(r'Task (\d+-\d+\.\d+): (?:Executing|FAILED|SUCCESS)', line)
            if retry_match:
                retry_id = retry_match.group(1)
                # Only add if not already in the list (avoid duplicates)
                if retry_id not in retry_execution_path:
                    retry_execution_path.append(retry_id)
                continue

            # Look for loop iteration patterns (Task X.Y format) - only count execution start lines
            # Match patterns like "Task 1.1: [DRY RUN] Would execute" or "Task 1.1: Executing"
            loop_match = re.search(r'Task (\d+)\.(\d+): (?:\[DRY RUN\] Would execute|Executing)', line)
            if loop_match:
                task_id = int(loop_match.group(1))
                iteration = int(loop_match.group(2))
                iteration_id = f"{task_id}.{iteration}"
                # Only add if not already in the list (avoid duplicates)
                if iteration_id not in loop_execution_path:
                    loop_execution_path.append(iteration_id)
                # Add base task_id to executed_tasks if not already there
                if task_id not in executed_tasks:
                    executed_tasks.append(task_id)
                final_task = task_id
                continue

            # Look for conditional/parallel subtask execution (e.g., Task 1-20:, Task 2-30:)
            if re.search(r'Task \d+-\d+: Executing', line):
                match = re.search(r'Task (\d+-\d+):', line)
                if match:
                    task_id = match.group(1)
                    executed_subtasks.append(task_id)

            # Look for task execution patterns (regular tasks, parallel, conditional)
            elif re.search(r'Task \d+: Executing', line) or \
               re.search(r'Task \d+: Starting parallel execution', line) or \
               re.search(r'Task \d+: Executing (TRUE|FALSE) branch', line):
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
            # Support both regular tasks (Task 1:) and subtasks (Task 1-20:)
            elif re.search(r'Task (\d+|\d+-\d+): STDOUT:', line):
                match = re.search(r'Task (\d+|\d+-\d+): STDOUT: (.+)', line)
                if match:
                    task_id = match.group(1)
                    stdout_value = match.group(2)
                    variables[f"{task_id}_stdout"] = stdout_value
                    # Add to output patterns for pattern matching
                    output_patterns["stdout"].append(stdout_value)

            elif re.search(r'Task (\d+|\d+-\d+): STDERR:', line):
                match = re.search(r'Task (\d+|\d+-\d+): STDERR: (.+)', line)
                if match:
                    task_id = match.group(1)
                    stderr_value = match.group(2)
                    variables[f"{task_id}_stderr"] = stderr_value
                    # Add to output patterns for pattern matching
                    output_patterns["stderr"].append(stderr_value)

            # Capture task exit codes (Phase 3 enhancement)
            # Matches both regular tasks (Task 0:) and subtasks (Task 0-1:)
            elif re.search(r'Task (\d+|\d+-\d+): Exit code: (\d+)', line):
                match = re.search(r'Task (\d+|\d+-\d+): Exit code: (\d+)', line)
                if match:
                    task_id = match.group(1)
                    exit_code = match.group(2)
                    variables[f"{task_id}_exit"] = exit_code
                    # Infer success status from exit code (0 = True, non-zero = False)
                    # Note: This is a simplification - actual success may depend on success/failure conditions
                    variables[f"{task_id}_success"] = "True" if exit_code == "0" else "False"

            # Capture explicit task success status (Phase 3 enhancement)
            # This overrides the inferred success from exit code if explicitly logged
            elif re.search(r'Task (\d+|\d+-\d+): Completed - Success: (True|False)', line):
                match = re.search(r'Task (\d+|\d+-\d+): Completed - Success: (True|False)', line)
                if match:
                    task_id = match.group(1)
                    success_status = match.group(2)
                    variables[f"{task_id}_success"] = success_status

        return {
            "executed_tasks": executed_tasks,
            "loop_execution_path": loop_execution_path,
            "executed_subtasks": executed_subtasks,
            "retry_execution_path": retry_execution_path,
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

        # Respect both explicit flag and test_type="validation_only"
        if (metadata.get("test_type") == "validation_only") or metadata.get("validation_only", False):
            cmd_args.append("--validate-only")
        else:
            cmd_args.append("-r")  # Run mode

        # Add skip flags from metadata
        if metadata.get("skip_host_validation", False):
            cmd_args.append("--skip-host-validation")
        if metadata.get("skip_task_validation", False):
            cmd_args.append("--skip-task-validation")
        if metadata.get("skip_command_validation", False):
            cmd_args.append("--skip-command-validation")
        if metadata.get("skip_security_validation", False):
            cmd_args.append("--skip-security-validation")
        if metadata.get("skip_validation", False):
            cmd_args.append("--skip-validation")

        # Add fire-and-forget flag from metadata
        if metadata.get("fire_and_forget", False):
            cmd_args.append("--fire-and-forget")

        # Set environment for supporting scripts
        env = os.environ.copy()

        # Build PATH with multiple fallback locations for helper scripts
        path_additions = []

        # 1. Absolute path to test_cases/bin (primary location)
        script_dir = Path(__file__).resolve().parent  # scripts directory
        test_cases_dir = script_dir.parent  # test_cases directory
        main_bin_dir = test_cases_dir / "bin"
        if main_bin_dir.exists():
            path_additions.append(str(main_bin_dir))

        # 2. Relative to test file's parent directory (for backward compatibility)
        test_dir = os.path.dirname(os.path.abspath(test_file))
        relative_bin_dir = os.path.join(os.path.dirname(test_dir), "bin")
        if os.path.exists(relative_bin_dir) and relative_bin_dir not in path_additions:
            path_additions.append(relative_bin_dir)

        # 3. Relative to test file's directory (for tests with local bin)
        local_bin_dir = os.path.join(test_dir, "bin")
        if os.path.exists(local_bin_dir) and local_bin_dir not in path_additions:
            path_additions.append(local_bin_dir)

        # Prepend all bin directories to PATH
        if path_additions:
            existing_path = env.get('PATH', '')
            env["PATH"] = ":".join(path_additions) + ":" + existing_path

        # Execute the test with performance monitoring
        start_time = datetime.now()
        performance_metrics = None

        try:
            # Start subprocess - Python 3.6.8 compatible pattern
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env
            )

            try:
                # Start performance monitoring for performance tests
                if metadata.get("test_type") == "performance":
                    self.performance_monitor.start_monitoring(process)

                try:
                    # Increased timeout to 120s to accommodate multi-host validation tests
                    # Host validation: 3 hosts × ~25s per host (DNS 10s + ping 5s + remote 10s) = 75s+
                    stdout, stderr = process.communicate(timeout=120)
                    exit_code = process.returncode

                    # Stop performance monitoring
                    if metadata.get("test_type") == "performance":
                        performance_metrics = self.performance_monitor.stop_monitoring()
                        # Parse task timings from output
                        task_timings = self.performance_monitor.parse_task_timings(stdout)
                        performance_metrics["task_timings"] = task_timings

                except subprocess.TimeoutExpired:
                    # Terminate the process on timeout
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # Give process 5 seconds to terminate gracefully
                    except subprocess.TimeoutExpired:
                        process.kill()  # Force kill if it doesn't terminate

                    # Capture any output before termination
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                    except subprocess.TimeoutExpired:
                        stdout, stderr = "", "Process killed due to timeout"

                    exit_code = 124
                    if metadata.get("test_type") == "performance":
                        performance_metrics = self.performance_monitor.stop_monitoring()

            finally:
                # Ensure process cleanup - avoid zombies
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()

            execution_time = (datetime.now() - start_time).total_seconds()

            # Parse execution path from output
            execution_path_data = self.parse_execution_path(stdout)

            result_data = {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": execution_time,
                "timed_out": (exit_code == 124),
                "error": None,
                "execution_path": execution_path_data
            }

            # Add performance metrics for performance tests
            if performance_metrics:
                # Use the main execution time instead of monitor's internal timing
                performance_metrics["execution_time"] = execution_time
                result_data["performance_metrics"] = performance_metrics

            return result_data

        except subprocess.TimeoutExpired:
            # Handle top-level timeout (shouldn't normally occur with the new pattern)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Try to clean up any remaining process
            try:
                if 'process' in locals() and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
            except:
                pass

            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": "Test execution timeout",
                "execution_time": execution_time,
                "timed_out": True,
                "error": "Timeout after 120 seconds",
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

        # CRITICAL: Detect Python tracebacks/exceptions (indicates internal bug/crash)
        # These indicate code failures, not clean validation errors
        combined_output = actual_results.get("stdout", "") + "\n" + actual_results.get("stderr", "")

        # Check for Python traceback
        if "Traceback (most recent call last):" in combined_output:
            validation_results["passed"] = False
            validation_results["failures"].append(
                "INTERNAL ERROR: Python traceback detected (code crash, not clean validation failure)"
            )
            # Extract traceback for debugging (show first 10 lines)
            traceback_lines = []
            capture = False
            for line in combined_output.split('\n'):
                if "Traceback (most recent call last):" in line:
                    capture = True
                if capture:
                    traceback_lines.append(line)
                    if len(traceback_lines) >= 10:
                        break
            for tb_line in traceback_lines:
                validation_results["failures"].append(f"  {tb_line}")

        # Check for common Python exception types (not preceded by "Task X:" logging)
        # These indicate unhandled exceptions
        # Skip this check if we already detected a traceback (avoid duplicate reports)
        # Only check when exit code is non-zero to avoid false positives from user output
        traceback_detected = any("Python traceback detected" in f for f in validation_results["failures"])
        nonzero_exit = actual_results.get("exit_code", 1) != 0

        if not traceback_detected and nonzero_exit:
            exception_patterns = [
                "AttributeError:", "KeyError:", "TypeError:", "NameError:",
                "IndexError:", "ImportError:", "RuntimeError:", "OSError:",
                "FileNotFoundError:", "PermissionError:"
            ]

            for line in combined_output.split('\n'):
                # Skip if it's part of TASKER's normal logging (Task X: output)
                if re.match(r'^\[\d{2}\w{3}\d{2} \d{2}:\d{2}:\d{2}\] Task \d+:', line):
                    continue

                # Check for exception patterns
                for exception_pattern in exception_patterns:
                    if exception_pattern in line:
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"INTERNAL ERROR: Unhandled Python exception detected: {line.strip()}"
                        )
                        break

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

        # Validate loop execution path (NEW)
        if "expected_loop_execution_path" in metadata:
            expected_loop_path = metadata["expected_loop_execution_path"]
            actual_loop_path = execution_path.get("loop_execution_path", [])

            if actual_loop_path != expected_loop_path:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Loop execution path mismatch: expected {expected_loop_path}, got {actual_loop_path}"
                )

        # Validate retry execution path (NEW)
        if "expected_retry_attempts" in metadata:
            expected_retry_path = metadata["expected_retry_attempts"]
            actual_retry_path = execution_path.get("retry_execution_path", [])
            retry_ordered = metadata.get("retry_execution_ordered", False)

            if retry_ordered:
                # Ordered validation - exact sequence must match (conditional/sequential retry)
                if actual_retry_path != expected_retry_path:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Retry execution order mismatch: expected {expected_retry_path}, got {actual_retry_path}"
                    )
            else:
                # Unordered validation - only presence matters (parallel retry)
                if set(actual_retry_path) != set(expected_retry_path):
                    validation_results["passed"] = False
                    missing = set(expected_retry_path) - set(actual_retry_path)
                    extra = set(actual_retry_path) - set(expected_retry_path)
                    msg = f"Retry attempts mismatch: expected {expected_retry_path}, got {actual_retry_path}"
                    if missing:
                        msg += f" (missing: {list(missing)})"
                    if extra:
                        msg += f" (extra: {list(extra)})"
                    validation_results["failures"].append(msg)

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

        # Phase 5: Duration validation (for any test type with min/max duration benchmarks)
        if "performance_benchmarks" in metadata:
            benchmarks = metadata["performance_benchmarks"]
            actual_time = actual_results.get("execution_time", 0)

            # Validate minimum duration
            if "min_duration" in benchmarks:
                min_duration = benchmarks["min_duration"]
                if actual_time < min_duration:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Execution time below minimum: {actual_time:.2f}s < {min_duration}s"
                    )

            # Validate maximum duration
            if "max_duration" in benchmarks:
                max_duration = benchmarks["max_duration"]
                if actual_time > max_duration:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Execution time exceeded maximum: {actual_time:.2f}s > {max_duration}s"
                    )

        # Phase 6: Performance test validation
        if metadata.get("test_type") == "performance":
            performance_metrics = actual_results.get("performance_metrics", {})

            # Validate performance benchmarks
            if "performance_benchmarks" in metadata:
                benchmarks = metadata["performance_benchmarks"]

                # Execution time validation
                if "max_execution_time" in benchmarks:
                    max_time = benchmarks["max_execution_time"]
                    actual_time = performance_metrics.get("execution_time", actual_results["execution_time"])

                    if actual_time > max_time:
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"Execution time exceeded benchmark: {actual_time:.2f}s > {max_time}s"
                        )

                # Memory usage validation
                if "max_memory_usage_mb" in benchmarks:
                    max_memory = benchmarks["max_memory_usage_mb"]
                    actual_memory = performance_metrics.get("peak_memory_mb", 0)

                    if actual_memory > max_memory:
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"Memory usage exceeded benchmark: {actual_memory:.1f}MB > {max_memory}MB"
                        )

                # Throughput validation
                if "min_throughput_tasks_per_second" in benchmarks:
                    min_throughput = benchmarks["min_throughput_tasks_per_second"]
                    execution_path = actual_results.get("execution_path", {})
                    executed_tasks = len(execution_path.get("executed_tasks", []))
                    actual_time = performance_metrics.get("execution_time", actual_results["execution_time"])

                    if actual_time > 0:
                        actual_throughput = executed_tasks / actual_time
                        if actual_throughput < min_throughput:
                            validation_results["passed"] = False
                            validation_results["failures"].append(
                                f"Throughput below benchmark: {actual_throughput:.2f} < {min_throughput} tasks/second"
                            )

            # Validate resource limits
            if "resource_limits" in metadata:
                limits = metadata["resource_limits"]

                # CPU threshold validation
                if "cpu_threshold_percent" in limits:
                    cpu_threshold = limits["cpu_threshold_percent"]
                    actual_cpu = performance_metrics.get("peak_cpu_percent", 0)

                    if actual_cpu > cpu_threshold:
                        validation_results["warnings"].append(
                            f"CPU usage above threshold: {actual_cpu:.1f}% > {cpu_threshold}%"
                        )

                # Memory threshold validation
                if "memory_threshold_mb" in limits:
                    memory_threshold = limits["memory_threshold_mb"]
                    actual_memory = performance_metrics.get("peak_memory_mb", 0)

                    if actual_memory > memory_threshold:
                        validation_results["warnings"].append(
                            f"Memory usage above threshold: {actual_memory:.1f}MB > {memory_threshold}MB"
                        )

            # Validate individual task timing
            if "timing_validation" in metadata:
                timing_config = metadata["timing_validation"]
                task_timings = performance_metrics.get("task_timings", {})

                # Individual task duration validation
                if "expected_task_duration" in timing_config:
                    expected_durations = timing_config["expected_task_duration"]
                    for task_id_str, expected_duration in expected_durations.items():
                        task_id = int(task_id_str)
                        actual_duration = task_timings.get(task_id, 0)

                        if actual_duration > expected_duration * 1.5:  # 50% tolerance
                            validation_results["warnings"].append(
                                f"Task {task_id} duration exceeded expectation: {actual_duration:.2f}s > {expected_duration}s"
                            )

                # Total duration validation
                if "max_total_duration" in timing_config:
                    max_total = timing_config["max_total_duration"]
                    actual_total = performance_metrics.get("execution_time", actual_results["execution_time"])

                    if actual_total > max_total:
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"Total execution time exceeded limit: {actual_total:.2f}s > {max_total}s"
                        )

        # Validate warning count and detect unexpected warnings
        # Only count actual TASKER warnings with timestamp format: [DDMmmYY HH:MM:SS] WARN:
        # This excludes task output that happens to contain "WARNING:" text
        # Pattern: [08Oct25 23:46:06] WARN: or [08Oct25 23:46:06] WARNING:
        warning_pattern = re.compile(r'^\[\d{2}\w{3}\d{2} \d{2}:\d{2}:\d{2}\] (WARN:|WARNING:)')
        warning_lines = [line for line in actual_results["stdout"].split('\n')
                       if warning_pattern.match(line)]
        actual_warning_count = len(warning_lines)

        if "expected_warnings" in metadata:
            expected_warning_count = metadata["expected_warnings"]
            if actual_warning_count != expected_warning_count:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Warning count mismatch: expected {expected_warning_count}, got {actual_warning_count}"
                )
        else:
            # If expected_warnings not specified, default to 0 - fail on any warnings
            if actual_warning_count > 0:
                validation_results["passed"] = False
                validation_results["failures"].append(
                    f"Unexpected warnings detected ({actual_warning_count} warnings found). Add 'expected_warnings': {actual_warning_count} to metadata if warnings are expected."
                )
                # Show the actual warning messages for debugging
                for warning_line in warning_lines[:5]:  # Show first 5 warnings
                    validation_results["failures"].append(f"  {warning_line.strip()}")

        # Validate stdout patterns per task
        if "expected_stdout" in metadata:
            expected_stdout = metadata["expected_stdout"]
            actual_variables = execution_path.get("variables", {})

            for task_id, expected_pattern in expected_stdout.items():
                stdout_var = f"{task_id}_stdout"
                if stdout_var not in actual_variables:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Task {task_id} stdout not found in execution results"
                    )
                else:
                    actual_stdout = actual_variables[stdout_var]
                    if expected_pattern not in actual_stdout:
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"Task {task_id} stdout pattern mismatch: expected '{expected_pattern}' in '{actual_stdout}'"
                        )

        # Validate conditional task execution
        if "expected_conditional_tasks" in metadata:
            expected_conditional = metadata["expected_conditional_tasks"]
            actual_subtasks = execution_path.get("executed_subtasks", [])

            for parent_task, config in expected_conditional.items():
                # Support both shorthand array syntax and explicit object syntax
                if isinstance(config, list):
                    expected_tasks = config
                    match_mode = "exact"  # default
                elif isinstance(config, dict):
                    expected_tasks = config.get("expected", [])
                    match_mode = config.get("match_mode", "exact")
                else:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Invalid expected_conditional_tasks format for task {parent_task}"
                    )
                    continue

                # Convert task IDs to strings for comparison
                expected_tasks = [str(t) for t in expected_tasks]
                actual_subtasks_str = [str(t) for t in actual_subtasks]

                # Find all conditional subtasks that executed for this parent task
                # TASKER uses hyphen format: 1-20, 1-21, not dot format: 1.20, 1.21
                executed_subtasks = [
                    t.split('-')[1] if '-' in t else t
                    for t in actual_subtasks_str
                    if t.startswith(f"{parent_task}-")
                ]

                # Validate based on match_mode
                if match_mode == "exact":
                    if executed_subtasks != expected_tasks:
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"Conditional task {parent_task}: expected exact execution {expected_tasks}, got {executed_subtasks}"
                        )
                elif match_mode == "parallel":
                    # All expected tasks must execute, order doesn't matter
                    if set(executed_subtasks) != set(expected_tasks):
                        validation_results["passed"] = False
                        validation_results["failures"].append(
                            f"Parallel task {parent_task}: expected {expected_tasks} (any order), got {executed_subtasks}"
                        )
                else:
                    validation_results["passed"] = False
                    validation_results["failures"].append(
                        f"Invalid match_mode '{match_mode}' for task {parent_task}"
                    )

        return validation_results


class IntelligentTestRunner:
    """Main test runner orchestrator."""

    def __init__(self, tasker_path=None):
        self.tasker_path = _resolve_tasker_path(tasker_path)
        self.executor = TaskerTestExecutor(self.tasker_path)
        self.validator = TestValidator()
        self.results = []

    def run_single_test(self, test_file):
        """Run a single test file and validate results."""
        test_name = os.path.basename(test_file)
        print(f"Running test: {test_name}")

        # Parse metadata
        metadata_parser = TestMetadata(test_file)
        if not metadata_parser.is_valid():
            result = {
                "test_name": test_name,
                "test_file": test_file,
                "status": "SKIPPED",
                "skip_reason": metadata_parser.metadata.get("error"),
                "execution_time": 0
            }
            self.results.append(result)
            return result

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
        test_files = _collect_test_files(directory, recursive)
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

        if status == "PASSED":
            status_icon = "✅"
        elif status == "SKIPPED":
            status_icon = "⊘"
        else:
            status_icon = "❌"
        print(f"{status_icon} {name} ({status}) - {time:.2f}s")

        # Show execution path info for passed tests (if available)
        if status == "PASSED" and "execution_results" in result:
            execution_path = result["execution_results"].get("execution_path", {})
            executed_tasks = execution_path.get("executed_tasks", [])
            loop_execution_path = execution_path.get("loop_execution_path", [])
            executed_subtasks = execution_path.get("executed_subtasks", [])

            if executed_tasks:
                print(f"    EXECUTION PATH: {executed_tasks}")

            if loop_execution_path:
                print(f"    LOOP ITERATIONS: {loop_execution_path}")

            if executed_subtasks:
                print(f"    SUBTASKS: {executed_subtasks}")

            # Show retry attempts if captured (NEW)
            retry_execution_path = execution_path.get("retry_execution_path", [])
            if retry_execution_path:
                retry_ordered = result.get("metadata", {}).get("retry_execution_ordered", False)
                order_label = "ordered" if retry_ordered else "unordered"
                print(f"    RETRY ATTEMPTS: {retry_execution_path} ({order_label})")

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

        # Show performance information for performance tests (Phase 5)
        if "metadata" in result and result["metadata"].get("test_type") == "performance":
            metadata = result["metadata"]
            performance_metrics = result.get("execution_results", {}).get("performance_metrics", {})

            # Show performance metrics
            execution_time = performance_metrics.get("execution_time", result.get("execution_time", 0))
            peak_memory = performance_metrics.get("peak_memory_mb", 0)
            peak_cpu = performance_metrics.get("peak_cpu_percent", 0)

            print(f"    PERFORMANCE: ⏱️  {execution_time:.2f}s | 🧠 {peak_memory:.1f}MB | ⚡ {peak_cpu:.1f}% CPU")

            # Show benchmark status
            if "performance_benchmarks" in metadata:
                benchmarks = metadata["performance_benchmarks"]
                max_time = benchmarks.get("max_execution_time", float('inf'))
                max_memory = benchmarks.get("max_memory_usage_mb", float('inf'))

                time_status = "✅" if execution_time <= max_time else "⚠️"
                memory_status = "✅" if peak_memory <= max_memory else "⚠️"

                print(f"    BENCHMARKS: {time_status} Time: {execution_time:.2f}s/{max_time}s | {memory_status} Memory: {peak_memory:.1f}/{max_memory}MB")

            # Show task timings if available
            task_timings = performance_metrics.get("task_timings", {})
            if task_timings:
                timing_display = ", ".join([f"T{k}: {v:.2f}s" for k, v in sorted(task_timings.items())])
                print(f"    TASK TIMING: {timing_display}")

        if status == "FAILED":
            failures = result["validation_results"]["failures"]
            for failure in failures:
                print(f"    FAILURE: {failure}")

        if status == "SKIPPED":
            print(f"    REASON: {result.get('skip_reason', 'Unknown reason')}")

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
        skipped_tests = len([r for r in self.results if r["status"] == "SKIPPED"])

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
        print(f"⊘ SKIPPED: {skipped_tests}/{total_tests} tests (missing metadata)")
        print()

        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAILED":
                    print(f"  • {result['test_name']}")
                    for failure in result["validation_results"]["failures"]:
                        print(f"    - {failure}")
            print()

        if skipped_tests > 0:
            print("SKIPPED TESTS (Need TEST_METADATA):")
            for result in self.results:
                if result["status"] == "SKIPPED":
                    print(f"  • {result['test_name']}: {result.get('skip_reason', 'No metadata')}")
            print()

        # Overall result
        if failed_tests == 0:
            if skipped_tests > 0:
                print(f"✅ ALL EXECUTABLE TESTS PASSED! ({skipped_tests} tests skipped)")
            else:
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
        "targets",
        nargs="+",
        help="Test file(s) or directory to run"
    )
    parser.add_argument(
        "--tasker-path",
        default=None,
        help="Path to tasker executable (default: auto-detect using shutil.which)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Recursively search for test files in subdirectories"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = IntelligentTestRunner(args.tasker_path)

    # Handle multiple targets
    test_files_set = set()

    for target in args.targets:
        if os.path.isfile(target):
            # Single file - add to set with absolute path
            test_files_set.add(os.path.abspath(target))
        elif os.path.isdir(target):
            # Directory - collect all .txt files using helper
            collected = _collect_test_files(target, args.recursive)
            for test_file in collected:
                test_files_set.add(os.path.abspath(test_file))
        else:
            print(f"Warning: '{target}' is not a valid file or directory - skipping")

    test_files = sorted(test_files_set)

    if not test_files:
        print("Error: No valid test files found")
        return 1

    # Run all collected test files
    print(f"Running {len(test_files)} individual test files")
    print("=" * 60)

    for test_file in test_files:
        result = runner.run_single_test(test_file)
        runner.print_result_summary(result)
        print("-" * 60)

    # Generate summary report
    exit_code = runner.generate_summary_report()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())