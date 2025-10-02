#!/usr/bin/env python3
"""
Non-blocking sleep utilities for TASKER.

This module provides non-blocking sleep implementations that don't starve
thread pools during sleep operations. Uses timer threads instead of blocking
the current thread.

Python 3.6.8 compatible implementation.
"""

import threading
import time
from typing import Callable, Optional, Any


class NonBlockingSleep:
    """
    Non-blocking sleep implementation using timer threads.

    This class provides sleep functionality that doesn't block the calling thread,
    preventing thread pool starvation during parallel execution.
    """

    def __init__(self):
        """Initialize the non-blocking sleep manager."""
        self._active_timers = {}  # Track active timers for cleanup
        self._timer_lock = threading.Lock()

    def sleep_async(self, duration: float, callback: Callable[[], Any],
                   task_id: str = None, logger_callback: Callable[[str], None] = None) -> threading.Timer:
        """
        Start a non-blocking sleep operation.

        Args:
            duration: Sleep duration in seconds
            callback: Function to call after sleep completes
            task_id: Optional task identifier for tracking
            logger_callback: Optional logging function

        Returns:
            Timer object that can be cancelled if needed
        """
        if duration <= 0:
            # No sleep needed, execute callback immediately
            callback()
            return None

        def sleep_completed():
            """Internal callback when sleep timer expires."""
            try:
                # Remove from active timers
                with self._timer_lock:
                    if task_id and task_id in self._active_timers:
                        del self._active_timers[task_id]

                # Log completion
                if logger_callback:
                    logger_callback(f"Sleep completed for task {task_id or 'unknown'}")

                # Execute the actual callback
                callback()

            except Exception as e:
                # Robust error handling - don't let timer thread crashes affect main execution
                if logger_callback:
                    logger_callback(f"Error in sleep completion callback: {e}")

        # Create and start the timer
        timer = threading.Timer(duration, sleep_completed)
        timer.daemon = True  # Ensure timer threads don't prevent program exit

        # Track the timer
        if task_id:
            with self._timer_lock:
                self._active_timers[task_id] = timer

        # Log start
        if logger_callback:
            logger_callback(f"Starting non-blocking sleep for {duration}s (task: {task_id or 'unknown'})")

        timer.start()
        return timer

    def cancel_sleep(self, task_id: str) -> bool:
        """
        Cancel an active sleep operation.

        Args:
            task_id: Task identifier

        Returns:
            True if sleep was cancelled, False if not found
        """
        with self._timer_lock:
            if task_id in self._active_timers:
                timer = self._active_timers[task_id]
                timer.cancel()
                del self._active_timers[task_id]
                return True
        return False

    def cleanup_all(self):
        """Cancel all active sleep operations."""
        with self._timer_lock:
            for timer in self._active_timers.values():
                timer.cancel()
            self._active_timers.clear()

    def get_active_count(self) -> int:
        """Get count of active sleep operations."""
        with self._timer_lock:
            return len(self._active_timers)


class DelayedExecution:
    """
    High-level interface for delayed task execution.

    Provides a Future-like interface for delayed execution that integrates
    cleanly with existing TASKER architecture.
    """

    def __init__(self, non_blocking_sleep: NonBlockingSleep):
        """
        Initialize delayed execution manager.

        Args:
            non_blocking_sleep: NonBlockingSleep instance to use
        """
        self.sleep_manager = non_blocking_sleep
        self._completion_lock = threading.Lock()
        self._completed = False
        self._result = None
        self._exception = None

    def execute_after_delay(self, delay: float, task_func: Callable[[], Any],
                          task_id: str = None, logger_callback: Callable[[str], None] = None):
        """
        Execute a function after a specified delay.

        Args:
            delay: Delay in seconds
            task_func: Function to execute after delay
            task_id: Optional task identifier
            logger_callback: Optional logging function

        Returns:
            Self for chaining
        """
        def delayed_callback():
            """Execute the task function and store result."""
            try:
                result = task_func()
                with self._completion_lock:
                    self._result = result
                    self._completed = True
            except Exception as e:
                with self._completion_lock:
                    self._exception = e
                    self._completed = True

        self.sleep_manager.sleep_async(delay, delayed_callback, task_id, logger_callback)
        return self

    def is_completed(self) -> bool:
        """Check if delayed execution has completed."""
        with self._completion_lock:
            return self._completed

    def get_result(self, timeout: Optional[float] = None):
        """
        Get the result of delayed execution.

        Args:
            timeout: Maximum time to wait for completion

        Returns:
            Result of the delayed function

        Raises:
            Exception: If the delayed function raised an exception
            TimeoutError: If timeout expired before completion
        """
        start_time = time.time()

        while not self.is_completed():
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Delayed execution did not complete within {timeout}s")
            time.sleep(0.1)  # Small sleep to avoid busy waiting

        with self._completion_lock:
            if self._exception:
                raise self._exception
            return self._result


# Global instance for use throughout TASKER
_global_sleep_manager = NonBlockingSleep()


def get_sleep_manager() -> NonBlockingSleep:
    """Get the global non-blocking sleep manager instance."""
    return _global_sleep_manager


def sleep_async(duration: float, callback: Callable[[], Any],
               task_id: str = None, logger_callback: Callable[[str], None] = None) -> threading.Timer:
    """
    Convenience function for non-blocking sleep.

    Args:
        duration: Sleep duration in seconds
        callback: Function to call after sleep completes
        task_id: Optional task identifier for tracking
        logger_callback: Optional logging function

    Returns:
        Timer object that can be cancelled if needed
    """
    return _global_sleep_manager.sleep_async(duration, callback, task_id, logger_callback)


def create_delayed_execution() -> DelayedExecution:
    """Create a new DelayedExecution instance."""
    return DelayedExecution(_global_sleep_manager)