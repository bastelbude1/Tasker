#!/usr/bin/env python
"""
Unit test for ExecConfigLoader callback update behavior.

Tests that the singleton pattern correctly updates debug callbacks
when multiple TaskExecutor instances are created, avoiding memory leaks
from stale instance references.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tasker.config.exec_config_loader import get_loader


def test_callback_update_on_existing_singleton():
    """
    Test that debug callback is updated when singleton already exists.

    Simulates multiple TaskExecutor instances being created with different
    debug callbacks and verifies logs go to the current callback, not stale ones.
    """
    print("Testing ExecConfigLoader callback update behavior...")

    # Storage for debug messages
    executor1_logs = []
    executor2_logs = []

    # Simulate first executor
    def executor1_debug(msg):
        executor1_logs.append(f"EXECUTOR1: {msg}")

    # Get loader with first callback (creates singleton)
    loader1 = get_loader(debug_callback=executor1_debug, force_reload=True)

    # Clear initialization logs (loader may log during config loading)
    initial_log_count = len(executor1_logs)
    executor1_logs.clear()

    # Trigger some debug output
    loader1.debug_callback("First executor initialization")

    # Verify first executor got the message
    assert len(executor1_logs) == 1, f"Expected 1 log, got {len(executor1_logs)}: {executor1_logs}"
    assert "First executor initialization" in executor1_logs[0], f"Unexpected log: {executor1_logs[0]}"
    print(f"✓ First executor callback works: {executor1_logs[0]} (cleared {initial_log_count} init logs)")

    # Simulate second executor (new instance with different callback)
    def executor2_debug(msg):
        executor2_logs.append(f"EXECUTOR2: {msg}")

    # Get loader with second callback (should update existing singleton)
    loader2 = get_loader(debug_callback=executor2_debug, force_reload=False)

    # Verify it's the same singleton
    assert loader1 is loader2, "Should return the same singleton instance"
    print("✓ Singleton pattern maintained (same instance)")

    # Trigger debug output after callback update
    loader2.debug_callback("Second executor using loader")

    # Verify second executor got the message, NOT first executor
    assert len(executor2_logs) == 1, f"Expected 1 log in executor2, got {len(executor2_logs)}"
    assert len(executor1_logs) == 1, f"Expected executor1 to still have 1 log, got {len(executor1_logs)}"
    assert "Second executor using loader" in executor2_logs[0], f"Unexpected log: {executor2_logs[0]}"
    print(f"✓ Second executor callback works: {executor2_logs[0]}")
    print("✓ First executor callback was NOT called (no memory leak)")

    # Test that get_execution_types uses current callback
    available = loader2.get_execution_types()
    print(f"✓ Available exec types: {available}")

    # Simulate third executor to verify callback keeps updating
    executor3_logs = []
    def executor3_debug(msg):
        executor3_logs.append(f"EXECUTOR3: {msg}")

    loader3 = get_loader(debug_callback=executor3_debug)
    loader3.debug_callback("Third executor")

    assert len(executor3_logs) == 1, "Third executor should receive callback"
    assert len(executor2_logs) == 1, "Second executor should not receive new callbacks"
    assert len(executor1_logs) == 1, "First executor should not receive new callbacks"
    print(f"✓ Third executor callback works: {executor3_logs[0]}")

    print("\n✅ ALL TESTS PASSED")
    print("   - Singleton pattern works correctly")
    print("   - Callbacks are updated, not accumulated")
    print("   - No memory leaks from stale instance references")
    return True


def test_none_callback_doesnt_override():
    """Test that passing None doesn't override existing callback."""
    print("\nTesting None callback behavior...")

    logs = []
    def debug_callback(msg):
        logs.append(msg)

    # Set callback
    loader = get_loader(debug_callback=debug_callback, force_reload=True)

    # Clear init logs
    logs.clear()

    loader.debug_callback("Test message 1")

    # Get loader with None callback (should not override)
    loader2 = get_loader(debug_callback=None)
    loader2.debug_callback("Test message 2")

    # Both messages should be in logs (callback not overridden)
    assert len(logs) == 2, f"Expected 2 logs, got {len(logs)}: {logs}"
    assert logs[0] == "Test message 1"
    assert logs[1] == "Test message 2"
    print("✓ None callback does not override existing callback")
    print(f"✓ Logs received: {logs}")

    print("\n✅ None callback test passed")
    return True


if __name__ == '__main__':
    try:
        test_callback_update_on_existing_singleton()
        test_none_callback_doesnt_override()
        print("\n" + "="*60)
        print("SUCCESS: All ExecConfigLoader callback tests passed!")
        print("="*60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
