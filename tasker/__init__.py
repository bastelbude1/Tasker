"""
TaskExecutor Library - Modular task execution framework
"""

__version__ = "2.1.4"

# Core components
from .core.utilities import (
    sanitize_filename,
    get_log_directory
)


# Public API
__all__ = [
    # Core
    'sanitize_filename',
    'get_log_directory'
]
