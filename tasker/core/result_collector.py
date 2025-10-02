# tasker/core/result_collector.py
"""
TASKER 2.1 - Result Collection and Reporting Component
-----------------------------------------------------
Handles result aggregation, categorization, and summary generation.

Responsibilities:
- Result categorization and analysis
- Summary generation and formatting
- Statistics collection and reporting
- Thread-safe file operations for summary logs
"""

import os
import errno
import time
import threading
import fcntl
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from .utilities import sanitize_for_tsv


class ResultCollector:
    """
    Collects, categorizes, and reports task execution results.

    Manages summary generation, statistics, and final reporting with
    thread-safe file operations.
    """

    def __init__(self, task_file: str, project: Optional[str] = None):
        """
        Initialize result collector.

        Args:
            task_file: Path to task file being executed
            project: Optional project name for summary logging
        """
        self.task_file = task_file
        self.project = project

        # Result tracking
        self.final_task_id = None
        self.final_hostname = ""
        self.final_command = ""
        self.final_exit_code = None
        self.final_success = False

        # Summary logging
        self.summary_log = None
        self.log_file_path = None
        self._summary_written = False
        self.summary_lock_timeout = 20  # seconds

        # Thread safety
        self.log_lock = threading.RLock()

    # ===== RESULT CATEGORIZATION =====

    def categorize_task_result(self, result: Dict[str, Any]) -> str:
        """
        Categorize task result for retry logic and reporting.

        Args:
            result: Task execution result dictionary

        Returns:
            Category string: 'TIMEOUT', 'SUCCESS', or 'FAILED'
        """
        if result['exit_code'] == 124:
            return 'TIMEOUT'     # Master timeout reached - don't retry
        elif result['success']:
            return 'SUCCESS'     # Success condition met - don't retry
        else:
            return 'FAILED'      # Real failure - eligible for retry

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analyze multiple results and return statistics.

        Args:
            results: List of task execution results

        Returns:
            Dictionary with counts for each category
        """
        stats = {'SUCCESS': 0, 'FAILED': 0, 'TIMEOUT': 0}

        for result in results:
            category = self.categorize_task_result(result)
            stats[category] += 1

        return stats

    # ===== FINAL STATE TRACKING =====

    def set_final_state(self, task_id: int, hostname: str, command: str,
                       exit_code: int, success: bool) -> None:
        """
        Set final execution state for summary reporting.

        Args:
            task_id: Final task ID executed
            hostname: Final hostname used
            command: Final command executed
            exit_code: Final exit code
            success: Final success status
        """
        self.final_task_id = task_id
        self.final_hostname = hostname
        self.final_command = command
        self.final_exit_code = exit_code
        self.final_success = success

    def get_final_state(self) -> Dict[str, Any]:
        """
        Get final execution state.

        Returns:
            Dictionary with final state information
        """
        return {
            'task_id': self.final_task_id,
            'hostname': self.final_hostname,
            'command': self.final_command,
            'exit_code': self.final_exit_code,
            'success': self.final_success
        }

    # ===== SUMMARY LOGGING SETUP =====

    def setup_summary_logging(self, summary_log_file, log_file_path: str) -> None:
        """
        Setup summary logging configuration with validation.

        Args:
            summary_log_file: Open file handle for summary logging
            log_file_path: Path to main log file

        Raises:
            ValueError: If summary_log_file is None or invalid
            IOError: If file handle is closed or not writable
        """
        if summary_log_file is None:
            raise ValueError("summary_log_file cannot be None")

        if hasattr(summary_log_file, 'closed') and summary_log_file.closed:
            raise IOError("summary_log_file is already closed")

        if not hasattr(summary_log_file, 'write'):
            raise ValueError("summary_log_file must have a write method")

        if not log_file_path or not isinstance(log_file_path, str):
            raise ValueError("log_file_path must be a non-empty string")

        # Test write capability
        try:
            summary_log_file.tell()  # This will fail if file is not open for writing
        except (OSError, IOError) as e:
            raise IOError(f"summary_log_file is not accessible for writing: {e}")

        self.summary_log = summary_log_file
        self.log_file_path = log_file_path

    # ===== ATOMIC FILE OPERATIONS =====

    def _acquire_file_lock_atomically(self, timeout_seconds: int = 5) -> Tuple[Optional[int], bool]:
        """
        Acquire exclusive file lock with timeout and proper error handling.

        Args:
            timeout_seconds: Maximum time to wait for lock

        Returns:
            Tuple of (file_descriptor, lock_acquired_successfully)

        Raises:
            OSError: For non-transient file locking errors
            IOError: For file descriptor access errors
        """
        if not self.summary_log:
            return None, False

        try:
            # Get file descriptor - may raise OSError/IOError if file is invalid
            file_no = self.summary_log.fileno()
        except (OSError, IOError) as e:
            # Re-raise file descriptor access errors - these are fatal
            raise IOError(f"Cannot get file descriptor from summary log: {e}")

        # Retry loop with timeout for transient lock conflicts
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                fcntl.flock(file_no, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return file_no, True
            except (OSError, IOError) as e:
                # Check if this is a transient error that should be retried
                if e.errno in (errno.EAGAIN, errno.EACCES):
                    # Transient error - another process has the lock, retry
                    time.sleep(0.1)  # Wait 100ms before retry
                    continue
                else:
                    # Fatal error - re-raise for proper handling
                    raise OSError(f"Fatal file locking error (errno {e.errno}): {e}")

        # Timeout reached - return failure without raising exception
        return file_no, False

    # ===== SUMMARY GENERATION =====

    def write_final_summary_with_timeout(self, timeout_seconds: int = 5) -> None:
        """
        Thread-based timeout wrapper for summary writing.

        Args:
            timeout_seconds: Maximum time to wait for summary write

        Raises:
            TimeoutError: If summary write takes too long
            RuntimeError: If summary write fails unexpectedly
        """
        import threading

        result = {'completed': False, 'error': None}

        def write_worker():
            try:
                self.write_final_summary()
                result['completed'] = True
            except Exception as e:
                result['error'] = e

        # Start write operation in separate thread
        worker_thread = threading.Thread(target=write_worker, daemon=True)
        worker_thread.start()

        # Wait with timeout
        worker_thread.join(timeout=timeout_seconds)

        if worker_thread.is_alive():
            # Thread still running - timeout reached
            raise TimeoutError(f"write_final_summary timeout after {timeout_seconds}s")

        if result['error']:
            # Exception in worker thread
            raise result['error']

        if not result['completed']:
            # Unexpected state
            raise RuntimeError("write_final_summary completed unexpectedly")

    def write_final_summary(self) -> None:
        """
        Write final execution summary to project summary file.

        Race-condition-free summary write with retry logic and atomic operations.
        """
        # Quick validation and exit
        if (not hasattr(self, 'summary_log') or not self.summary_log or
            self.final_task_id is None):
            return

        # Prevent duplicate writes
        if self._summary_written:
            return
        self._summary_written = True

        # Message preparation outside critical section
        timestamp = datetime.now().strftime('%d%b%y %H:%M:%S')
        status = "SUCCESS" if self.final_success else "FAILURE"
        log_file = os.path.basename(self.log_file_path) if self.log_file_path else 'unknown.log'

        fields = [
            timestamp,
            sanitize_for_tsv(os.path.basename(self.task_file)),
            sanitize_for_tsv(str(self.final_task_id)),
            sanitize_for_tsv(self.final_hostname),
            sanitize_for_tsv(self.final_command),
            sanitize_for_tsv(str(self.final_exit_code)),
            status,
            log_file
        ]
        message = '\t'.join(fields)

        # Atomic lock acquisition and write with retry
        with self.log_lock:
            file_no, lock_acquired = self._acquire_file_lock_atomically(self.summary_lock_timeout)

            if not lock_acquired:
                # Detailed error message
                project_name = self.project or 'unknown'
                raise TimeoutError(
                    f"Could not acquire lock on shared summary file '{project_name}.summary' "
                    f"within {self.summary_lock_timeout} seconds. Another tasker instance "
                    f"is currently writing to the summary file."
                )

            try:
                # Final validation after lock (defense in depth)
                if self.summary_log.closed:
                    raise ValueError("Summary log unexpectedly closed after lock acquisition")

                # Atomic write operations
                self.summary_log.seek(0, 2)  # End of file
                self.summary_log.write(f"{message}\n")
                self.summary_log.flush()

                # Verification
                current_pos = self.summary_log.tell()
                if current_pos == 0:
                    raise IOError("Write verification failed - file position is 0")

            finally:
                # Guaranteed lock release
                if file_no is not None:
                    try:
                        fcntl.flock(file_no, fcntl.LOCK_UN)
                    except Exception:
                        # Lock will be automatically released on process exit
                        pass

    # ===== STATISTICS AND REPORTING =====

    def generate_execution_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive execution summary.

        Args:
            results: List of all task execution results

        Returns:
            Dictionary with execution statistics and summary
        """
        stats = self.analyze_results(results)

        total_tasks = len(results)
        success_rate = (stats['SUCCESS'] / total_tasks * 100) if total_tasks > 0 else 0

        return {
            'total_tasks': total_tasks,
            'successful': stats['SUCCESS'],
            'failed': stats['FAILED'],
            'timeouts': stats['TIMEOUT'],
            'success_rate': round(success_rate, 2),
            'final_state': self.get_final_state(),
            'overall_success': self.final_success
        }

    def format_summary_report(self, summary: Dict[str, Any]) -> str:
        """
        Format execution summary for display.

        Args:
            summary: Summary dictionary from generate_execution_summary

        Returns:
            Formatted summary string
        """
        lines = [
            "=" * 50,
            "TASKER EXECUTION SUMMARY",
            "=" * 50,
            f"Total Tasks: {summary['total_tasks']}",
            f"Successful: {summary['successful']}",
            f"Failed: {summary['failed']}",
            f"Timeouts: {summary['timeouts']}",
            f"Success Rate: {summary['success_rate']}%",
            "",
            f"Final Task ID: {summary['final_state']['task_id']}",
            f"Final Status: {'SUCCESS' if summary['overall_success'] else 'FAILURE'}",
            f"Final Exit Code: {summary['final_state']['exit_code']}",
            "=" * 50
        ]

        return "\n".join(lines)

    # ===== CLEANUP =====

    def cleanup(self) -> None:
        """Clean up result collector resources."""
        # Summary log is managed externally, don't close here
        pass