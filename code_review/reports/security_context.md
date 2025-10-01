# TASKER Security Review Context

## System Overview
TASKER is a Python 3.6.8 task automation system that executes commands on remote hosts via subprocess calls.

## Critical Security Areas
1. **Command Injection**: User-provided commands executed via subprocess.Popen()
2. **Input Validation**: Task file parameters, hostnames, arguments
3. **File Handling**: Reading task files, writing logs, temporary files
4. **Privilege Escalation**: Remote command execution via pbrun/sudo
5. **Path Traversal**: File operations with user-controlled paths

## Key Files to Analyze
- tasker.py: Main execution engine
- tasker/core/: Core task processing logic
- tasker/executors/: Command execution handlers
- tasker/validation/: Input validation modules

## Python 3.6.8 Security Constraints
- Must use subprocess.Popen() instead of subprocess.run()
- Limited to standard library only
- No modern security libraries available

## Security Requirements
- No external dependencies allowed
- All user input must be validated
- Command execution must prevent injection
- File operations must be path-safe
- Error messages must not leak sensitive information
