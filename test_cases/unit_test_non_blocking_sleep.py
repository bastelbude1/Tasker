#!/usr/bin/env python3
"""
Unit tests for non-blocking sleep implementation.

Tests the non_blocking_sleep utility module to ensure proper timer thread
behavior and thread pool compatibility.
"""

import sys
import os
import time
import threading
import unittest
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasker.utils.non_blocking_sleep import (
    NonBlockingSleep, DelayedExecution,
    get_sleep_manager, sleep_async, create_delayed_execution
)


class TestNonBlockingSleep(unittest.TestCase):
    """Test cases for NonBlockingSleep class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sleep_manager = NonBlockingSleep()
        self.mock_logger = Mock()

    def test_immediate_callback_for_zero_duration(self):
        """Test that zero duration executes callback immediately."""
        callback_executed = threading.Event()

        def test_callback():
            callback_executed.set()

        timer = self.sleep_manager.sleep_async(0, test_callback)

        # Should execute immediately
        self.assertTrue(callback_executed.wait(timeout=0.1))
        self.assertIsNone(timer)  # No timer created for zero duration

    def test_timer_execution(self):
        """Test that timer executes callback after specified duration."""
        callback_executed = threading.Event()
        start_time = time.time()

        def test_callback():
            callback_executed.set()

        timer = self.sleep_manager.sleep_async(0.2, test_callback, "test_task", self.mock_logger)

        # Verify timer was created
        self.assertIsNotNone(timer)

        # Wait for callback execution
        self.assertTrue(callback_executed.wait(timeout=1.0))

        # Verify timing (should be around 0.2 seconds, with some tolerance)
        elapsed = time.time() - start_time
        self.assertGreaterEqual(elapsed, 0.19)  # Allow small timing variance
        self.assertLess(elapsed, 0.5)

    def test_task_tracking(self):
        """Test that tasks are properly tracked and can be cancelled."""
        callback_executed = threading.Event()

        def test_callback():
            callback_executed.set()

        # Start a sleep operation
        timer = self.sleep_manager.sleep_async(1.0, test_callback, "tracked_task")

        # Verify it's being tracked
        self.assertEqual(self.sleep_manager.get_active_count(), 1)

        # Cancel the sleep
        cancelled = self.sleep_manager.cancel_sleep("tracked_task")
        self.assertTrue(cancelled)

        # Verify it's no longer tracked
        self.assertEqual(self.sleep_manager.get_active_count(), 0)

        # Callback should not execute
        time.sleep(0.1)
        self.assertFalse(callback_executed.is_set())

    def test_multiple_concurrent_sleeps(self):
        """Test multiple concurrent sleep operations."""
        callbacks_executed = []

        def make_callback(task_id):
            def callback():
                callbacks_executed.append(task_id)
            return callback

        # Start multiple sleep operations
        durations = [0.1, 0.2, 0.3]
        for i, duration in enumerate(durations):
            self.sleep_manager.sleep_async(
                duration,
                make_callback(f"task_{i}"),
                f"task_{i}"
            )

        # Wait for all to complete
        time.sleep(0.5)

        # All callbacks should have executed
        self.assertEqual(len(callbacks_executed), 3)
        self.assertIn("task_0", callbacks_executed)
        self.assertIn("task_1", callbacks_executed)
        self.assertIn("task_2", callbacks_executed)

    def test_cleanup_all(self):
        """Test cleanup of all active sleep operations."""
        callback_executed = threading.Event()

        def test_callback():
            callback_executed.set()

        # Start multiple sleep operations
        for i in range(3):
            self.sleep_manager.sleep_async(2.0, test_callback, f"task_{i}")

        # Verify they're tracked
        self.assertEqual(self.sleep_manager.get_active_count(), 3)

        # Cleanup all
        self.sleep_manager.cleanup_all()

        # Verify all are cleaned up
        self.assertEqual(self.sleep_manager.get_active_count(), 0)

        # Wait a bit to ensure callbacks don't execute
        time.sleep(0.1)
        self.assertFalse(callback_executed.is_set())

    def test_exception_handling_in_callback(self):
        """Test that exceptions in callbacks don't crash timer threads."""
        exception_raised = threading.Event()

        def failing_callback():
            exception_raised.set()
            raise ValueError("Test exception")

        # This should not crash the timer thread
        timer = self.sleep_manager.sleep_async(0.1, failing_callback, "failing_task", self.mock_logger)

        # Wait for execution
        self.assertTrue(exception_raised.wait(timeout=1.0))

        # Logger should have been called with error message
        self.mock_logger.assert_called()


class TestDelayedExecution(unittest.TestCase):
    """Test cases for DelayedExecution class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sleep_manager = NonBlockingSleep()
        self.delayed_exec = DelayedExecution(self.sleep_manager)

    def test_delayed_function_execution(self):
        """Test delayed execution of a function."""
        result_value = "test_result"

        def test_function():
            return result_value

        # Execute after short delay
        self.delayed_exec.execute_after_delay(0.1, test_function, "test_task")

        # Should not be completed immediately
        self.assertFalse(self.delayed_exec.is_completed())

        # Wait for completion
        result = self.delayed_exec.get_result(timeout=1.0)
        self.assertEqual(result, result_value)
        self.assertTrue(self.delayed_exec.is_completed())

    def test_delayed_execution_with_exception(self):
        """Test delayed execution when function raises exception."""
        def failing_function():
            raise ValueError("Test exception")

        self.delayed_exec.execute_after_delay(0.1, failing_function, "failing_task")

        # Should raise the exception when getting result
        with self.assertRaises(ValueError):
            self.delayed_exec.get_result(timeout=1.0)

    def test_timeout_on_get_result(self):
        """Test timeout when waiting for result."""
        def slow_function():
            time.sleep(1.0)
            return "result"

        self.delayed_exec.execute_after_delay(0.5, slow_function, "slow_task")

        # Should timeout
        with self.assertRaises(TimeoutError):
            self.delayed_exec.get_result(timeout=0.2)


class TestGlobalInterface(unittest.TestCase):
    """Test cases for global interface functions."""

    def test_global_sleep_manager(self):
        """Test global sleep manager access."""
        manager1 = get_sleep_manager()
        manager2 = get_sleep_manager()

        # Should return the same instance
        self.assertIs(manager1, manager2)

    def test_sleep_async_convenience_function(self):
        """Test sleep_async convenience function."""
        callback_executed = threading.Event()

        def test_callback():
            callback_executed.set()

        timer = sleep_async(0.1, test_callback, "convenience_test")
        self.assertIsNotNone(timer)

        # Wait for execution
        self.assertTrue(callback_executed.wait(timeout=1.0))

    def test_create_delayed_execution(self):
        """Test delayed execution factory function."""
        delayed_exec = create_delayed_execution()
        self.assertIsInstance(delayed_exec, DelayedExecution)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)