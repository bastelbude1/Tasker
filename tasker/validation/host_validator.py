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
import threading
from ..core.condition_evaluator import ConditionEvaluator
from ..core.utilities import ExitCodes


class HostValidator:
    """
    Handles host validation and connectivity testing for TASKER tasks.
    
    This class provides stateless host validation by accepting required
    data (global_vars, task_results, tasks) as parameters rather than storing state.
    """
    
    @staticmethod
    def validate_hosts(tasks, global_vars, task_results, exec_type=None, default_exec_type='pbrun', check_connectivity=False, debug_callback=None, log_callback=None):
        """
        Enhanced host validation with automatic connectivity testing for remote hosts.
        Returns a dict mapping original hostnames to validated FQDNs if successful,
        or a dict with error information if validation failed.
        
        Args:
            tasks: Dictionary of task definitions
            global_vars: Dictionary of global variables
            task_results: Dictionary of task results
            exec_type: Override execution type
            default_exec_type: Default execution type to use
            check_connectivity: Whether to test actual connectivity (ignored - always True for remote hosts)
            debug_callback: Optional function for debug logging
            log_callback: Optional function for main logging
            
        Returns:
            Dict mapping hostnames to validated FQDNs, or dict with 'error' and 'exit_code' if validation failed
        """
        # First check if remote execution commands exist
        exec_commands = {
            'pbrun': 'pbrun',
            'p7s': 'p7s', 
            'wwrs': 'wwrs_clir'
        }
        
        # Collect unique host+exec_type combinations
        host_exec_combinations = {}  # {hostname: set(exec_types)}
        
        for task in tasks.values():
            if 'hostname' in task and task['hostname']:
                hostname, resolved = ConditionEvaluator.replace_variables(
                    task['hostname'], global_vars, task_results, debug_callback)
                
                if resolved and hostname:
                    # Determine exec type for this task
                    task_exec = HostValidator._determine_task_exec_type(
                        task, exec_type, default_exec_type)
                    
                    # Skip local execution from validation
                    if task_exec == 'local':
                        continue
                        
                    if hostname not in host_exec_combinations:
                        host_exec_combinations[hostname] = set()
                    host_exec_combinations[hostname].add(task_exec)
        
        # Check if required execution commands exist
        missing_commands = set()
        for exec_types in host_exec_combinations.values():
            for exec_type in exec_types:
                if exec_type in exec_commands:
                    cmd = exec_commands[exec_type]
                    if not HostValidator._check_command_exists(cmd):
                        missing_commands.add(f"{exec_type} ({cmd})")
        
        if missing_commands:
            if log_callback:
                log_callback(f"# ERROR: Required remote execution commands not found: {', '.join(missing_commands)}")
            return {'error': 'missing_commands', 'exit_code': ExitCodes.CONNECTION_FAILED}
        
        # Validate each unique host+exec_type combination
        failed_validations = []
        validated_hosts = {}
        total_tests = sum(len(exec_types) for exec_types in host_exec_combinations.values())
        
        if log_callback and total_tests > 0:
            log_callback(f"# Validating {len(host_exec_combinations)} unique hosts with {total_tests} connection tests...")
        
        for hostname, exec_types in host_exec_combinations.items():
            # DNS resolution
            resolved, resolved_name = HostValidator.resolve_hostname(hostname, debug_callback)
            if not resolved:
                failed_validations.append({
                    'host': hostname,
                    'error': 'dns_resolution_failed',
                    'exit_code': ExitCodes.HOST_UNREACHABLE
                })
                continue
                
            validated_hosts[hostname] = resolved_name
            
            # Ping test
            if not HostValidator.check_host_alive(resolved_name, debug_callback):
                failed_validations.append({
                    'host': hostname,
                    'resolved': resolved_name,
                    'error': 'host_unreachable',
                    'exit_code': ExitCodes.HOST_UNREACHABLE
                })
                del validated_hosts[hostname]
                continue
            
            # Test each exec_type for this host
            for exec_type in exec_types:
                if not HostValidator._test_remote_access(exec_type, resolved_name, debug_callback):
                    failed_validations.append({
                        'host': hostname,
                        'resolved': resolved_name,
                        'exec_type': exec_type,
                        'error': f'{exec_type}_connection_failed',
                        'exit_code': ExitCodes.CONNECTION_FAILED
                    })
                    if hostname in validated_hosts:
                        del validated_hosts[hostname]
                    break
        
        # Handle failures
        if failed_validations:
            return HostValidator._handle_validation_failures(
                failed_validations, log_callback, debug_callback)
        
        if log_callback and total_tests > 0:
            log_callback(f"# All {total_tests} host connectivity tests passed successfully.")
        
        return validated_hosts

    @staticmethod
    def _dns_lookup_with_timeout(hostname, timeout=5):
        """
        Perform DNS lookup with timeout using threading.
        Python 3.6 compatible - socket.gethostbyname has no timeout parameter.

        Returns:
            (success: bool, result: str or None, error: Exception or None)
        """
        result = [None]  # Use list to allow modification from thread
        exception = [None]

        def dns_lookup():
            try:
                result[0] = socket.gethostbyname(hostname)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=dns_lookup)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Thread is still running - timeout occurred
            return False, None, TimeoutError(f"DNS lookup timed out after {timeout}s")

        if exception[0] is not None:
            # DNS lookup failed with exception
            return False, None, exception[0]

        # DNS lookup succeeded
        return True, result[0], None

    @staticmethod
    def resolve_hostname(hostname, debug_callback=None):
        """Try to resolve hostname - optimized for WSL2 environment with fast /etc/hosts lookup."""
        try:
            # Fast path: check /etc/hosts directly to avoid WSL2 DNS delays
            try:
                with open('/etc/hosts', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 2 and hostname in parts[1:]:
                                if debug_callback:
                                    debug_callback(f"Hostname '{hostname}' found in /etc/hosts")
                                return True, hostname
            except (IOError, OSError):
                pass  # Fall back to DNS resolution

            # Fallback to DNS resolution with timeout (prevents WSL2 long delays)
            success, ip_address, error = HostValidator._dns_lookup_with_timeout(hostname, timeout=5)
            if success:
                if debug_callback:
                    debug_callback(f"Hostname '{hostname}' resolved via DNS to {ip_address}")
                return True, hostname
            elif isinstance(error, TimeoutError):
                if debug_callback:
                    debug_callback(f"DNS lookup for '{hostname}' timed out after 5s")
                raise socket.gaierror("DNS timeout")
            else:
                # Re-raise the original exception
                raise error

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
    
    @staticmethod
    def _determine_task_exec_type(task, exec_type, default_exec_type):
        """Determine execution type for a task."""
        if 'exec' in task:
            return task['exec']
        elif exec_type:
            return exec_type
        elif 'TASK_EXECUTOR_TYPE' in os.environ:
            return os.environ['TASK_EXECUTOR_TYPE']
        else:
            return default_exec_type
    
    @staticmethod
    def _check_command_exists(command):
        """Check if a command exists and is executable."""
        try:
            # Use 'which' command to check if command exists (Python 3.6 compatible)
            with subprocess.Popen(['which', command], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                universal_newlines=True) as process:
                try:
                    stdout, stderr = process.communicate(timeout=5)
                    return process.returncode == 0
                except subprocess.TimeoutExpired:
                    process.kill()
                    return False
        except:
            return False
    
    @staticmethod
    def _test_remote_access(exec_type, hostname, debug_callback=None):
        """Enhanced remote access test expecting exit 0 and stdout containing OK."""
        if exec_type not in ['pbrun', 'p7s', 'wwrs']:
            return True
            
        # Build test command
        if exec_type == 'pbrun':
            cmd_array = ["pbrun", "-n", "-h", hostname, "pbtest"]
        elif exec_type == 'p7s':
            cmd_array = ["p7s", hostname, "pbtest"]
        elif exec_type == 'wwrs':
            cmd_array = ["wwrs_clir", hostname, "wwrs_test"]
        
        if debug_callback:
            debug_callback(f"Testing {exec_type} connection to '{hostname}': {' '.join(cmd_array)}")
        
        try:
            # Use process group to ensure child processes are killed on timeout
            # This is important for shell scripts that spawn subprocesses (like sleep)
            with subprocess.Popen(cmd_array,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                preexec_fn=os.setsid if sys.platform != 'win32' else None) as process:
                try:
                    stdout, stderr = process.communicate(timeout=10)
                    exit_code = process.returncode

                    # Check for exit code 0 AND stdout containing "OK"
                    success = (exit_code == 0 and "OK" in stdout)

                    if debug_callback:
                        if success:
                            debug_callback(f"{exec_type} connection to '{hostname}' successful")
                        else:
                            debug_callback(f"{exec_type} connection to '{hostname}' failed:")
                            debug_callback(f"  Exit code: {exit_code}")
                            debug_callback(f"  Stdout: {stdout.strip()}")
                            debug_callback(f"  Stderr: {stderr.strip()}")

                    return success

                except subprocess.TimeoutExpired:
                    # Kill entire process group to clean up child processes
                    try:
                        if sys.platform != 'win32':
                            os.killpg(os.getpgid(process.pid), 9)  # SIGKILL
                        else:
                            process.kill()
                    except:
                        process.kill()  # Fallback
                    stdout, stderr = process.communicate()
                    if debug_callback:
                        debug_callback(f"ERROR: {exec_type} connection to '{hostname}' timed out")
                    return False
            
        except subprocess.TimeoutExpired:
            if debug_callback:
                debug_callback(f"ERROR: {exec_type} connection to '{hostname}' timed out")
            return False
        except Exception as e:
            if debug_callback:
                debug_callback(f"ERROR: {exec_type} test failed: {str(e)}")
            return False
    
    @staticmethod
    def _handle_validation_failures(failures, log_callback, debug_callback):
        """Handle validation failures with appropriate error reporting."""
        # Group failures by type
        dns_failures = [f for f in failures if f['error'] == 'dns_resolution_failed']
        unreachable = [f for f in failures if f['error'] == 'host_unreachable']
        connection_failures = [f for f in failures if 'connection_failed' in f['error']]
        
        # Determine primary exit code
        if connection_failures:
            primary_exit_code = ExitCodes.CONNECTION_FAILED
        elif unreachable:
            primary_exit_code = ExitCodes.HOST_UNREACHABLE
        else:
            primary_exit_code = ExitCodes.HOST_VALIDATION_FAILED
        
        # Build error message
        if log_callback:
            log_callback(f"# ERROR: Host validation failed ({len(failures)} failures)")
            
            if debug_callback:
                # Detailed output in debug mode
                if dns_failures:
                    debug_callback(f"DNS resolution failed for: {', '.join(f['host'] for f in dns_failures)}")
                if unreachable:
                    debug_callback(f"Hosts unreachable: {', '.join(f['host'] for f in unreachable)}")
                if connection_failures:
                    for failure in connection_failures:
                        debug_callback(f"{failure['exec_type']} connection failed: {failure['host']}")
            else:
                # Brief output in normal mode
                if connection_failures:
                    exec_types = set(f['exec_type'] for f in connection_failures)
                    log_callback(f"# Remote access validation failed for: {', '.join(exec_types)}")
        
        return {'error': 'validation_failed', 'exit_code': primary_exit_code}