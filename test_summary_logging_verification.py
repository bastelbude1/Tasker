#!/usr/bin/env python3
"""
Integration test to verify that ResultCollector.setup_summary_logging is properly called
and the ResultCollector has access to the summary log file handle.
"""

import os
import sys
import tempfile

# Add the current directory to the path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the core modules
from tasker.core.task_executor_main import TaskExecutor
from tasker.core.result_collector import ResultCollector

def test_summary_logging_setup():
    """Test that ResultCollector.setup_summary_logging is properly called."""

    print("Testing ResultCollector summary logging setup...")

    # Create a temporary task file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("""task=1
hostname=localhost
exec=local
command=echo
arguments=test
success=exit_0""")
        temp_task_file = temp_file.name

    try:
        # Create a temporary log directory
        with tempfile.TemporaryDirectory() as temp_log_dir:

            # Initialize TaskExecutor with project name (which triggers summary logging)
            with TaskExecutor(
                task_file=temp_task_file,
                log_dir=temp_log_dir,
                dry_run=True,  # Use dry run to avoid actual execution
                project="test_project",  # This triggers summary logging
                log_level="DEBUG",
                validate_only=True  # Only validate, don't execute
            ) as executor:

                # Verify that ResultCollector was set up with summary logging
                result_collector = executor._result_collector

                # Test 1: Verify summary_log is set
                assert hasattr(result_collector, 'summary_log'), "ResultCollector should have summary_log attribute"
                assert result_collector.summary_log is not None, "ResultCollector.summary_log should not be None"

                # Test 2: Verify log_file_path is set
                assert hasattr(result_collector, 'log_file_path'), "ResultCollector should have log_file_path attribute"
                assert result_collector.log_file_path is not None, "ResultCollector.log_file_path should not be None"

                # Test 3: Verify summary log file handle is writable
                assert hasattr(result_collector.summary_log, 'write'), "summary_log should have write method"
                assert not result_collector.summary_log.closed, "summary_log should not be closed"

                # Test 4: Verify log_file_path is a string
                assert isinstance(result_collector.log_file_path, str), "log_file_path should be a string"
                assert len(result_collector.log_file_path) > 0, "log_file_path should not be empty"

                print("✅ All tests passed!")
                print(f"   - summary_log: {type(result_collector.summary_log).__name__}")
                print(f"   - log_file_path: {result_collector.log_file_path}")
                print(f"   - summary_log closed: {result_collector.summary_log.closed}")

                return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    finally:
        # Clean up temp task file
        if os.path.exists(temp_task_file):
            os.unlink(temp_task_file)

def test_summary_logging_validation():
    """Test the validation in setup_summary_logging method."""

    print("\nTesting ResultCollector.setup_summary_logging validation...")

    result_collector = ResultCollector("test.txt", "test_project")

    # Test 1: None file handle should raise ValueError
    try:
        result_collector.setup_summary_logging(None, "/path/to/log.log")
        print("❌ Expected ValueError for None file handle")
        return False
    except ValueError as e:
        print(f"✅ Correctly raised ValueError for None file handle: {e}")

    # Test 2: Empty log path should raise ValueError
    with tempfile.NamedTemporaryFile(mode='w') as temp_file:
        try:
            result_collector.setup_summary_logging(temp_file, "")
            print("❌ Expected ValueError for empty log path")
            return False
        except ValueError as e:
            print(f"✅ Correctly raised ValueError for empty log path: {e}")

    # Test 3: Valid setup should work
    with tempfile.NamedTemporaryFile(mode='w') as temp_file:
        try:
            result_collector.setup_summary_logging(temp_file, "/path/to/log.log")
            print("✅ Valid setup completed successfully")
            assert result_collector.summary_log == temp_file, "summary_log should be set correctly"
            assert result_collector.log_file_path == "/path/to/log.log", "log_file_path should be set correctly"
        except Exception as e:
            print(f"❌ Valid setup failed: {e}")
            return False

    return True

if __name__ == "__main__":
    print("TASKER 2.1 - ResultCollector Summary Logging Integration Test")
    print("=" * 65)

    success1 = test_summary_logging_setup()
    success2 = test_summary_logging_validation()

    if success1 and success2:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)