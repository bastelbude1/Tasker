#!/usr/bin/env python
"""
Execution Type Configuration Loader

Loads platform-specific execution type definitions from YAML configuration file.
Supports graceful fallback when config file is missing or invalid.

Config File Location Priority:
1. <tasker.py_dir>/cfg/execution_types.yaml
2. ./cfg/execution_types.yaml

Note: Requires PyYAML library (pip install pyyaml)
      If PyYAML not available, falls back to local/shell-only mode
"""

import os
import sys
import platform
import shlex
import shutil

# Try to import YAML, fall back gracefully if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None


class ExecConfigLoader:
    """
    Loads and manages execution type configuration.

    Provides platform-specific execution type definitions including:
    - Binary names
    - Command templates
    - Validation test specifications
    """

    def __init__(self, config_path=None, debug_callback=None):
        """
        Initialize configuration loader.

        Args:
            config_path: Optional explicit path to config file
            debug_callback: Optional callback for debug messages
        """
        self.debug_callback = debug_callback or (lambda msg: None)
        self.config_path = config_path
        self.config_data = None
        self.platform = self._detect_platform()

        # Load configuration
        self._load_config()

    def set_debug_callback(self, debug_callback):
        """
        Update the debug callback for this loader instance.

        This is useful when using the singleton pattern and a new callback
        needs to be set (e.g., when a new TaskExecutor instance is created).

        Args:
            debug_callback: New debug callback function or None
        """
        self.debug_callback = debug_callback or (lambda msg: None)

    def _detect_platform(self):
        """
        Detect current platform (linux, windows, darwin).

        Returns:
            str: Platform name in lowercase
        """
        system = platform.system().lower()

        # Normalize platform names
        if system == 'linux':
            return 'linux'
        elif system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'darwin'
        else:
            # Default to linux for unknown platforms
            self.debug_callback(f"Unknown platform '{system}', defaulting to linux")
            return 'linux'

    def _find_config_file(self):
        """
        Find configuration file using priority order.

        Priority:
        1. Explicit config_path if provided
        2. <tasker.py_dir>/cfg/execution_types.yaml
        3. ./cfg/execution_types.yaml

        Returns:
            str or None: Path to config file if found
        """
        # If explicit path provided, use it
        if self.config_path:
            if os.path.isfile(self.config_path):
                return self.config_path
            else:
                self.debug_callback(f"Explicit config path not found: {self.config_path}")
                return None

        # Priority 1: Same directory as tasker.py (resolve symlinks to find real script location)
        # Find tasker.py location by checking sys.argv[0] and resolving symlinks
        if len(sys.argv) > 0 and sys.argv[0]:
            script_name = sys.argv[0]

            # If sys.argv[0] is not an absolute path, find it in PATH
            if not os.path.isabs(script_name):
                # Try to find the script in PATH using shutil.which
                found_path = shutil.which(script_name)
                if found_path:
                    script_name = found_path
                    self.debug_callback(f"Found script in PATH: {script_name}")
                else:
                    # Fall back to resolving relative to current directory
                    script_name = os.path.abspath(script_name)

            # Resolve symlinks to get real script path
            script_path = os.path.realpath(script_name)
            script_dir = os.path.dirname(script_path)
            config_path = os.path.join(script_dir, 'cfg', 'execution_types.yaml')

            self.debug_callback(f"Searching for config at: {config_path}")
            if os.path.isfile(config_path):
                self.debug_callback(f"Found config at script location: {config_path}")
                return config_path
            else:
                self.debug_callback(f"Config not found at script location: {config_path}")

        # Priority 2: Current working directory
        config_path = os.path.join('.', 'cfg', 'execution_types.yaml')
        if os.path.isfile(config_path):
            self.debug_callback(f"Found config at current directory: {config_path}")
            return config_path

        self.debug_callback("No configuration file found in priority locations")
        return None

    def _load_config(self):
        """
        Load configuration from YAML file.

        Falls back to empty config if:
        - PyYAML not available
        - Config file not found
        - Config file invalid
        """
        # Check if YAML is available
        if not YAML_AVAILABLE:
            self.debug_callback("WARNING: PyYAML not available. Only exec=local will be supported.")
            self.debug_callback("Install PyYAML: pip install pyyaml")
            self.config_data = {}
            return

        # Find config file
        config_file = self._find_config_file()
        if not config_file:
            self.debug_callback("WARNING: No execution_types.yaml config found. Only exec=local will be supported.")
            self.config_data = {}
            return

        # Load and parse YAML
        try:
            with open(config_file, 'r') as f:
                self.config_data = yaml.safe_load(f)

            # Validate basic structure
            if not isinstance(self.config_data, dict):
                raise ValueError("Config file must contain a dictionary")

            if 'platforms' not in self.config_data:
                raise ValueError("Config file must contain 'platforms' key")

            self.debug_callback(f"Successfully loaded config from: {config_file}")

        except Exception as e:
            self.debug_callback(f"ERROR: Failed to load config file '{config_file}': {e}")
            self.debug_callback("WARNING: Only exec=local will be supported.")
            self.config_data = {}

    def get_execution_types(self):
        """
        Get list of available execution types for current platform.

        Returns:
            list: List of execution type names (e.g., ['shell', 'pbrun', 'p7s'])
        """
        if not self.config_data:
            return []

        platforms = self.config_data.get('platforms', {})
        platform_config = platforms.get(self.platform, {})

        return list(platform_config.keys())

    def get_exec_type_config(self, exec_type):
        """
        Get configuration for a specific execution type.

        Args:
            exec_type: Execution type name (e.g., 'shell', 'pbrun')

        Returns:
            dict or None: Configuration dictionary or None if not found
        """
        if not self.config_data:
            return None

        # Check aliases first
        aliases = self.config_data.get('aliases', {})
        if exec_type in aliases:
            exec_type = aliases[exec_type]

        # Get platform-specific config
        platforms = self.config_data.get('platforms', {})
        platform_config = platforms.get(self.platform, {})

        return platform_config.get(exec_type)

    def get_binary_name(self, exec_type):
        """
        Get binary name for execution type.

        Args:
            exec_type: Execution type name

        Returns:
            str or None: Binary name or None if not found
        """
        config = self.get_exec_type_config(exec_type)
        if config:
            return config.get('binary')
        return None

    def get_validation_test(self, exec_type):
        """
        Get validation test specification for execution type.

        Args:
            exec_type: Execution type name

        Returns:
            dict or None: Validation test config or None if not found/not required
        """
        config = self.get_exec_type_config(exec_type)
        if config:
            return config.get('validation_test')
        return None

    def build_command_array(self, exec_type, hostname, command, arguments):
        """
        Build command array from template for given execution type.

        Args:
            exec_type: Execution type name
            hostname: Target hostname
            command: Command to execute
            arguments: Command arguments (string)

        Returns:
            list or None: Command array or None if exec type not found
        """
        config = self.get_exec_type_config(exec_type)
        if not config:
            return None

        template = config.get('command_template')
        if not template:
            return None

        # Prepare template variables
        expanded_arguments = os.path.expandvars(arguments) if arguments else ""

        # Split arguments for templates that need it
        arguments_split = shlex.split(expanded_arguments) if expanded_arguments else []

        # Build command array from template
        cmd_array = []
        for template_part in template:
            # Handle special case: {arguments_split} expands to multiple elements
            if template_part == "{arguments_split}":
                cmd_array.extend(arguments_split)
            else:
                # Replace template variables
                part = template_part.format(
                    binary=config.get('binary', ''),
                    hostname=hostname,
                    command=command,
                    arguments=expanded_arguments
                )
                cmd_array.append(part)

        return cmd_array

    def is_available(self, exec_type):
        """
        Check if execution type is available/configured.

        Args:
            exec_type: Execution type name

        Returns:
            bool: True if exec type is configured
        """
        return self.get_exec_type_config(exec_type) is not None

    def get_default_exec_type(self):
        """
        Get default execution type from YAML configuration.

        Returns platform-specific default if configured, otherwise None.
        The caller should fall back to 'local' if None is returned.

        Returns:
            str or None: Default execution type name, or None if not configured
        """
        if not self.config_data:
            return None

        # Get platform-specific default
        platforms = self.config_data.get('platforms', {})
        platform_config = platforms.get(self.platform, {})
        default_exec_type = platform_config.get('default_exec_type')

        if default_exec_type:
            self.debug_callback(f"Using default execution type from config: {default_exec_type}")
            return default_exec_type

        return None


# Global singleton instance
_loader_instance = None


def get_loader(config_path=None, debug_callback=None, force_reload=False):
    """
    Get global ExecConfigLoader instance (singleton).

    Args:
        config_path: Optional explicit config file path
        debug_callback: Optional debug callback
        force_reload: Force reload of configuration

    Returns:
        ExecConfigLoader: Global loader instance

    Note:
        If the singleton already exists and a new debug_callback is provided,
        the callback will be updated to avoid holding stale references to
        old TaskExecutor instances (prevents memory leaks).
    """
    global _loader_instance

    if _loader_instance is None or force_reload:
        _loader_instance = ExecConfigLoader(
            config_path=config_path,
            debug_callback=debug_callback
        )
    elif debug_callback is not None:
        # Update callback on existing singleton to avoid holding stale references
        _loader_instance.set_debug_callback(debug_callback)

    return _loader_instance
