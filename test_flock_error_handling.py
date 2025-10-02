#!/usr/bin/env python3
"""
Test the improved flock error handling in ResultCollector._acquire_file_lock_atomically

This test verifies that:
1. Transient errors (EAGAIN/EACCES) are properly retried
2. Fatal errors are re-raised instead of swallowed
3. Timeout returns (file_no, False) without exception
4. File descriptor errors are properly handled
"""

import os
import sys
import errno
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add the current directory to the path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the core modules
from tasker.core.result_collector import ResultCollector


class TestFlockErrorHandling(unittest.TestCase):
    """Test cases for improved flock error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.result_collector = ResultCollector("test.txt", "test_project")

    def test_transient_eagain_error_retry(self):
        """Test that EAGAIN errors are retried properly."""
        print("Testing EAGAIN transient error retry...")

        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            self.result_collector.summary_log = temp_file

            # Mock fcntl.flock to raise EAGAIN twice, then succeed
            call_count = 0
            def mock_flock(fd, operation):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    # First two calls: simulate transient lock conflict
                    error = OSError("Resource temporarily unavailable")
                    error.errno = errno.EAGAIN
                    raise error
                # Third call: succeed
                return None

            with patch('fcntl.flock', side_effect=mock_flock):
                file_no, success = self.result_collector._acquire_file_lock_atomically(timeout_seconds=2)

            self.assertTrue(success, "Should succeed after retrying EAGAIN errors")
            self.assertIsNotNone(file_no, "Should return valid file descriptor")
            self.assertEqual(call_count, 3, "Should retry EAGAIN errors twice then succeed")
            print("✅ EAGAIN retry test passed")

    def test_transient_eacces_error_retry(self):
        """Test that EACCES errors are retried properly."""
        print("Testing EACCES transient error retry...")

        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            self.result_collector.summary_log = temp_file

            # Mock fcntl.flock to raise EACCES twice, then succeed
            call_count = 0
            def mock_flock(fd, operation):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    # First two calls: simulate permission-based lock conflict
                    error = OSError("Permission denied")
                    error.errno = errno.EACCES
                    raise error
                # Third call: succeed
                return None

            with patch('fcntl.flock', side_effect=mock_flock):
                file_no, success = self.result_collector._acquire_file_lock_atomically(timeout_seconds=2)

            self.assertTrue(success, "Should succeed after retrying EACCES errors")
            self.assertIsNotNone(file_no, "Should return valid file descriptor")
            self.assertEqual(call_count, 3, "Should retry EACCES errors twice then succeed")
            print("✅ EACCES retry test passed")

    def test_fatal_error_reraise(self):
        """Test that non-transient errors are re-raised."""
        print("Testing fatal error re-raise...")

        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            self.result_collector.summary_log = temp_file

            # Mock fcntl.flock to raise a fatal error (not EAGAIN/EACCES)
            def mock_flock(fd, operation):
                error = OSError("Invalid file descriptor")
                error.errno = errno.EBADF  # Fatal error - not EAGAIN/EACCES
                raise error

            with patch('fcntl.flock', side_effect=mock_flock):
                with self.assertRaises(OSError) as context:
                    self.result_collector._acquire_file_lock_atomically(timeout_seconds=1)

            self.assertIn("Fatal file locking error", str(context.exception))
            self.assertIn(str(errno.EBADF), str(context.exception))
            print("✅ Fatal error re-raise test passed")

    def test_timeout_returns_false(self):
        """Test that timeout returns (file_no, False) without exception."""
        print("Testing timeout behavior...")

        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            self.result_collector.summary_log = temp_file

            # Mock fcntl.flock to always raise EAGAIN (simulating persistent lock)
            def mock_flock(fd, operation):
                error = OSError("Resource temporarily unavailable")
                error.errno = errno.EAGAIN
                raise error

            with patch('fcntl.flock', side_effect=mock_flock):
                file_no, success = self.result_collector._acquire_file_lock_atomically(timeout_seconds=0.5)

            self.assertFalse(success, "Should return False on timeout")
            self.assertIsNotNone(file_no, "Should return valid file descriptor even on timeout")
            print("✅ Timeout behavior test passed")

    def test_file_descriptor_error_handling(self):
        """Test that file descriptor errors are properly handled."""
        print("Testing file descriptor error handling...")

        # Mock a summary_log that raises an error on fileno()
        mock_log = MagicMock()
        mock_log.fileno.side_effect = OSError("Bad file descriptor")
        self.result_collector.summary_log = mock_log

        with self.assertRaises(IOError) as context:
            self.result_collector._acquire_file_lock_atomically(timeout_seconds=1)

        self.assertIn("Cannot get file descriptor", str(context.exception))
        print("✅ File descriptor error handling test passed")

    def test_none_summary_log_handling(self):
        """Test that None summary_log is handled gracefully."""
        print("Testing None summary_log handling...")

        self.result_collector.summary_log = None

        file_no, success = self.result_collector._acquire_file_lock_atomically(timeout_seconds=1)

        self.assertIsNone(file_no, "Should return None for file descriptor")
        self.assertFalse(success, "Should return False for success")
        print("✅ None summary_log handling test passed")


def run_comprehensive_test():
    """Run all flock error handling tests."""
    print("TASKER 2.1 - Flock Error Handling Test Suite")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFlockErrorHandling)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)

    # Report results
    if result.wasSuccessful():
        print("\n🎉 All flock error handling tests passed!")
        return True
    else:
        print(f"\n💥 {len(result.failures)} test(s) failed!")
        for test, traceback in result.failures:
            print(f"FAILED: {test}")
            print(traceback)
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)