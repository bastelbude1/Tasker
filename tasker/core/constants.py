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

# Maximum size for command-line variable substitution (100KB)
# CRITICAL: Prevents "Argument list too long" errors (ARG_MAX limits)
# Most OS have ARG_MAX limits between 128KB-2MB, so 100KB is a safe limit.
# Used when substituting large outputs (≥1MB) stored in temp files into command arguments.
MAX_CMDLINE_SUBST = 100 * 1024  # 100KB safe limit
