# tasker/validation/host_validator.py
"""
Host Validation and Connectivity Testing
----------------------------------------
Handles hostname resolution, connectivity testing, and validation of all hosts
in TASKER task definitions. Provides comprehensive validation capabilities
including DNS resolution, ping tests, and execution type specific connectivity tests.
"""

import os
import sys
import socket
import subprocess
from ..core.condition_evaluator import ConditionEvaluator


class HostValidator:
    """
    Handles host validation and connectivity testing for TASKER tasks.
    
    This class provides stateless host validation by accepting required
    data (global_vars, task_results, tasks) as parameters rather than storing state.
    """
    
    @staticmethod
    def validate_hosts(tasks, global_vars, task_results, exec_type=None, default_exec_type='pbrun', check_connectivity=False, debug_callback=None, log_callback=None):
        """
        Validate all unique hostnames in the task list.
        Returns a dict mapping original hostnames to validated FQDNs if successful,
        or False if validation failed.
        
        Args:
            tasks: Dictionary of task definitions
            global_vars: Dictionary of global variables
            task_results: Dictionary of task results
            exec_type: Override execution type
            default_exec_type: Default execution type to use
            check_connectivity: Whether to test actual connectivity
            debug_callback: Optional function for debug logging
            log_callback: Optional function for main logging
            
        Returns:
            Dict mapping hostnames to validated FQDNs, or False if validation failed
        """

        # Collect unique hostnames from all tasks
        hostnames = set()
        host_exec_types = {}

        for task in tasks.values():  # Changed to iterate over values
            if 'hostname' in task and task['hostname']:
                # Replace variables in hostname before validation
                hostname, resolved = ConditionEvaluator.replace_variables(task['hostname'], global_vars, task_results, debug_callback)
                if resolved and hostname:  # Only validate if variable resolution succeeded
                    hostnames.add(hostname)

                    # Track execution type for each hostname
                    if 'exec' in task:
                        task_exec_type = task['exec']
                    elif exec_type:
                        task_exec_type = exec_type
                    elif 'TASK_EXECUTOR_TYPE' in os.environ:
                        task_exec_type = os.environ['TASK_EXECUTOR_TYPE']
                    else:
                        task_exec_type = default_exec_type

                    # Store the exec type for this hostname
                    if hostname not in host_exec_types:
                        host_exec_types[hostname] = set()

                    host_exec_types[hostname].add(task_exec_type)

        # Check each unique hostname
        failed_hosts = []
        validated_hosts = {} # will map original hostnames to validated FQDNs

        if log_callback:
            log_callback(f"# Validating {len(hostnames)} unique hostnames...")

        for hostname in hostnames:
            # Try to resolve hostname
            resolved, resolved_name = HostValidator.resolve_hostname(hostname, debug_callback)

            if not resolved:
                #debug_callback(f"WARNING: Could not resolve hostname '{hostname}'")
                failed_hosts.append(hostname)
                continue

            # Store the resolved hostname
            validated_hosts[hostname] = resolved_name

            # Check if host is alive
            if not HostValidator.check_host_alive(resolved_name, debug_callback):
                if debug_callback:
                    debug_callback(f"WARNING: Host '{hostname}' ({resolved_name}) is not reachable")
                failed_hosts.append(hostname)
                continue

            # If requested, check specific connection type
            if check_connectivity:
                conn_failed = False
                for task_exec_type in host_exec_types[hostname]:
                    if task_exec_type in ['pbrun', 'p7s', 'wwrs']:
                        if not HostValidator.check_exec_connection(task_exec_type, resolved_name, debug_callback):
                            if debug_callback:
                                debug_callback(f"WARNING: Connection test failed for {task_exec_type} to '{hostname}' ({resolved_name})")
                            failed_hosts.append(f"{hostname} ({task_exec_type})")
                            conn_failed = True

                # if any connection test failed, don't consider this as an validated host 
                if conn_failed:
                    if hostname in validated_hosts:
                        del validated_hosts[hostname]

        # If any hosts failed validation, abort execution
        if failed_hosts:
            if log_callback:
                log_callback(f"# ERROR: {len(failed_hosts)} host(s) failed validation: {', '.join(failed_hosts)}")
            return False

        if log_callback:
            log_callback(f"# All {len(hostnames)} hosts passed successfully.")
        return validated_hosts

    @staticmethod
    def resolve_hostname(hostname, debug_callback=None):
        """Try to resolve hostname using DNS or op mc_isac if needed."""
        try:
            # Try direct DNS resolution first
            socket.gethostbyname(hostname)
            if debug_callback:
                debug_callback(f"Hostname '{hostname}' resolved via DNS")
            return True, hostname

        except socket.gaierror:
            if debug_callback:
                debug_callback(f"Hostname '{hostname}' not found in DNS, trying op mc_isac")
            try:
                # Try using op mc_isac to get FQDN
                with subprocess.Popen(
                    ["op", "mc_isac", "-f", hostname],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                ) as process:

                    try:
                        stdout, stderr = process.communicate(timeout=10)
                        if process.returncode == 0 and stdout.strip():
                            fqdn = stdout.strip()
                            if debug_callback:
                                debug_callback(f"Resolved '{hostname}' to FQDN '{fqdn}' using op mc_isac")
                            return True, fqdn
                        else:
                            if debug_callback:
                                debug_callback(f"ERROR: Could not resolve hostname '{hostname}' with op mc_isac: {stderr.strip()}")
                            return False, hostname

                    except subprocess.TimeoutExpired:
                        process.kill()
                        stdout, stderr = process.communicate()
                        if debug_callback:
                            debug_callback(f"ERROR: op mc_isac for hostname '{hostname}' timed out")
                        return False, hostname

            except Exception as e:
                if debug_callback:
                    debug_callback(f"ERROR: op mc_isac for hostname '{hostname}' failed: {str(e)}")
                return False, hostname

    @staticmethod
    def check_host_alive(hostname, debug_callback=None):
        """Check if host is reachable via ping."""
        try:
            # Use ping to check if host is alive
            if sys.platform == "win32":
                # Windows ping command
                ping_cmd = ["ping", "-n", "1", "-w", "1000", hostname]
            else:
                # Linux/Unix ping command
                ping_cmd = ["ping", "-c", "1", "-W", "1", hostname]

            with subprocess.Popen(
                ping_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            ) as process:

                try:
                    stdout, stderr = process.communicate(timeout=5)
                    if debug_callback:
                        debug_callback(f"ping '{hostname}' is alive")
                    return process.returncode == 0
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    if debug_callback:
                        debug_callback(f"ERROR: ping to '{hostname}' timed out")
                    return False

        except Exception as e:
            if debug_callback:
                debug_callback(f"ERROR: pinging host '{hostname}': {str(e)}")
            return False

    @staticmethod
    def check_exec_connection(exec_type, hostname, debug_callback=None):
        """Test connectivity for specific execution type."""
        if exec_type not in ['pbrun', 'p7s', 'wwrs']:
            # For local or unknown exec types, just return True
            return True

        # Build command array based on exec_type
        if exec_type == 'pbrun':
            cmd_array = ["pbrun", "-n", "-h", hostname, "pbtest"]
        elif exec_type == 'p7s':
            cmd_array = ["p7s", hostname, "pbtest"]
        elif exec_type == 'wwrs':
            cmd_array = ["wwrs_clir", hostname, "wwrs_test"]

        if debug_callback:
            debug_callback(f"Testing {exec_type} connection to '{hostname}' with: {' '.join(cmd_array)}")

        try:
            with subprocess.Popen(
                cmd_array,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            ) as process:

                try:
                    stdout, stderr = process.communicate(timeout=10)
                    success = process.returncode == 0 and "OK" in stdout
                    if success:
                        if debug_callback:
                            debug_callback(f"{exec_type} connection to '{hostname}' successful")
                    else:
                        if debug_callback:
                            debug_callback(f"ERROR: {exec_type} connection to '{hostname}' failed: {stderr.strip()}")
                    return success

                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    if debug_callback:
                        debug_callback(f"ERROR: {exec_type} connection to '{hostname}' timed out")
                    return False

        except Exception as e:
            if debug_callback:
                debug_callback(f"ERROR: testing {exec_type} connection to '{hostname}': {str(e)}")
            return False