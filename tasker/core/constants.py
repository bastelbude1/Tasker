# tasker/core/constants.py
"""
TASKER Core Constants
---------------------
Shared constants used across multiple modules.
"""

# Maximum depth for nested variable expansion (@VAR1@ referencing @VAR2@, etc.)
# This prevents infinite loops in circular references while allowing reasonable chaining depth.
# Used in both validation phase and runtime execution for consistent behavior.
MAX_VARIABLE_EXPANSION_DEPTH = 10
