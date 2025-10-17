#!/usr/bin/env python
"""
TASKER Recovery State Management
---------------------------------
Manages automatic error recovery state for TASKER workflows.

This module provides functionality to:
- Save execution state after each task
- Load and validate recovery state
- Resume execution from failed tasks
- Validate dependencies for safe resume

Recovery files are stored in ~/TASKER/recovery/ with hash-based naming
to avoid conflicts and permission issues.
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class RecoveryStateManager:
    """Manages recovery state for automatic error recovery."""

    RECOVERY_VERSION = "1.0"

    def __init__(self, task_file: str, log_dir: str):
        """
        Initialize RecoveryStateManager.

        Args:
            task_file: Absolute path to task file
            log_dir: Base log directory (e.g., ~/TASKER/log/)
        """
        self.task_file = os.path.abspath(task_file)
        self.log_dir = log_dir
        self.recovery_file = self._get_recovery_file_path()

    def _get_recovery_file_path(self) -> str:
        """
        Generate recovery file path with hash-based naming.

        Format: {basename}_{hash}.recovery.json
        Hash: First 8 characters of SHA-256(absolute_task_file_path)

        Returns:
            Absolute path to recovery file
        """
        # Calculate hash from absolute path
        path_hash = hashlib.sha256(self.task_file.encode()).hexdigest()[:8]

        # Get basename without extension
        basename = os.path.basename(self.task_file)
        if basename.endswith('.txt'):
            basename = basename[:-4]

        # Construct recovery filename
        recovery_filename = "{}_{}{}".format(basename, path_hash, '.recovery.json')

        # Create recovery directory if it doesn't exist
        recovery_dir = os.path.join(self.log_dir, 'recovery')
        os.makedirs(recovery_dir, exist_ok=True)

        return os.path.join(recovery_dir, recovery_filename)

    def _calculate_file_hash(self) -> str:
        """
        Calculate SHA-256 hash of task file content.

        Returns:
            Hex digest of file content hash
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(self.task_file, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except (IOError, OSError) as e:
            raise RuntimeError("Failed to calculate task file hash: {}".format(e))

    def recovery_file_exists(self) -> bool:
        """
        Check if recovery file exists.

        Returns:
            True if recovery file exists, False otherwise
        """
        return os.path.exists(self.recovery_file)

    def save_state(self, execution_path: list, state_manager, log_file: str,
                   failure_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Save current execution state to recovery file.

        Args:
            execution_path: List of task IDs executed so far (can be None, will be calculated)
            state_manager: StateManager instance with current state
            log_file: Path to log file
            failure_info: Optional failure information (task_id, exit_code, error)
        """
        # Calculate task file hash for integrity verification
        task_file_hash = self._calculate_file_hash()

        # Get current state from StateManager
        task_results = state_manager.get_all_task_results()
        global_vars = state_manager.get_global_vars()
        current_task = state_manager.get_current_task()

        # Build execution_path from successful tasks if not provided
        if not execution_path:
            execution_path = []
            for task_id in sorted(task_results.keys()):
                result = task_results.get(task_id, {})
                if result.get('success', False):
                    execution_path.append(task_id)

        # Build recovery state
        recovery_data = {
            'version': self.RECOVERY_VERSION,
            'task_file_path': self.task_file,
            'task_file_hash': task_file_hash,
            'recovery_file': os.path.basename(self.recovery_file),
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'log_file': log_file,
            'execution_path': execution_path,
            'last_successful_task': execution_path[-1] if execution_path else None,
            'current_task': current_task,
            'task_results': task_results,
            'global_vars': global_vars,
            'loop_state': {},  # TODO: Add loop state tracking if needed
            'failure_info': failure_info
        }

        # If recovery file exists, preserve created timestamp
        if os.path.exists(self.recovery_file):
            try:
                with open(self.recovery_file, 'r') as f:
                    existing_data = json.load(f)
                    recovery_data['created'] = existing_data.get('created', recovery_data['created'])
            except (IOError, json.JSONDecodeError):
                pass  # Use new timestamp if can't read existing file

        # Write recovery state to file
        try:
            with open(self.recovery_file, 'w') as f:
                json.dump(recovery_data, f, indent=2)
        except (IOError, OSError) as e:
            raise RuntimeError("Failed to save recovery state: {}".format(e))

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load recovery state from file.

        Returns:
            Recovery state dictionary or None if file doesn't exist/invalid
        """
        if not os.path.exists(self.recovery_file):
            return None

        try:
            with open(self.recovery_file, 'r') as f:
                recovery_data = json.load(f)
            return recovery_data
        except (IOError, OSError, json.JSONDecodeError) as e:
            print("Warning: Failed to load recovery state: {}".format(e))
            return None

    def validate_state(self, recovery_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate recovery state for safe resume.

        Checks:
        1. Task file still exists
        2. Task file hasn't changed (hash verification)
        3. Recovery data format is valid

        Args:
            recovery_data: Recovery state dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check task file exists
        if not os.path.exists(self.task_file):
            return False, "Task file no longer exists: {}".format(self.task_file)

        # Verify task file hash
        current_hash = self._calculate_file_hash()
        saved_hash = recovery_data.get('task_file_hash', '')

        if current_hash != saved_hash:
            return False, "Task file has been modified since recovery state was saved"

        # Verify required fields
        required_fields = ['version', 'execution_path', 'task_results', 'global_vars']
        for field in required_fields:
            if field not in recovery_data:
                return False, "Invalid recovery state: missing field '{}'".format(field)

        # Verify version compatibility
        if recovery_data.get('version') != self.RECOVERY_VERSION:
            return False, "Incompatible recovery state version: {} (expected {})".format(
                recovery_data.get('version'), self.RECOVERY_VERSION)

        return True, ""

    def delete_recovery_file(self) -> None:
        """
        Delete recovery file (called on successful completion).
        """
        if os.path.exists(self.recovery_file):
            try:
                os.remove(self.recovery_file)
            except (IOError, OSError) as e:
                print("Warning: Failed to delete recovery file: {}".format(e))

    def get_recovery_info(self) -> Optional[Dict[str, Any]]:
        """
        Get recovery information for display (used by --show-recovery-info).

        Returns:
            Dictionary with recovery info or None if no recovery file
        """
        recovery_data = self.load_state()
        if not recovery_data:
            return None

        # Validate state
        is_valid, error_msg = self.validate_state(recovery_data)

        info = {
            'recovery_file': self.recovery_file,
            'task_file': recovery_data.get('task_file_path'),
            'is_valid': is_valid,
            'validation_error': error_msg if not is_valid else None,
            'created': recovery_data.get('created'),
            'updated': recovery_data.get('updated'),
            'log_file': recovery_data.get('log_file'),
            'execution_path': recovery_data.get('execution_path', []),
            'last_successful_task': recovery_data.get('last_successful_task'),
            'failure_info': recovery_data.get('failure_info')
        }

        return info
