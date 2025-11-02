# TASKER Quick Reference Handout

**One-Page Cheat Sheet for IT Professionals**

---

## Installation (30 seconds)

```bash
git clone https://github.com/bastelbude1/Tasker.git
cd Tasker
./tasker --version  # Ready to go!
```

**No dependencies, no installation, no configuration required**

---

## Basic Usage

```bash
# Validate workflow (dry run)
tasker tasks.txt

# Execute workflow
tasker -r tasks.txt

# Execute with project tracking
tasker -r -p PROJECT_NAME tasks.txt

# Debug mode
tasker -r -d tasks.txt

# Validation only (skip execution)
tasker --validate-only tasks.txt
```

---

## Essential Task Parameters

### Required (Every Task Needs These)
```
task=N              # Task ID (unique number: 0, 1, 2, ...)
hostname=X          # Target server (localhost, server1, or server1,server2,server3)
command=X           # Command to execute
exec=TYPE           # Execution type: local|shell|pbrun|p7s|wwrs
```

### Flow Control
```
on_success=N        # Jump to task N if success criteria met
on_failure=N        # Jump to task N if success criteria not met
next=N              # Continue to task N (default: next sequential task)
next=never          # Stop here (firewall - don't continue)
condition=EXPR      # Execute only if condition evaluates to true
```

### Success Criteria
```
success=exit_0                    # Exit code is 0
success=exit_0&stdout~pattern     # Exit 0 AND stdout contains pattern
success=exit_0|stdout~pattern     # Exit 0 OR stdout contains pattern
success=!stderr                   # No stderr output
success=exit_1                    # Custom exit code
```

### Parallel Execution
```
hostname=srv1,srv2,srv3           # Execute on multiple hosts
max_parallel=N                    # Max concurrent executions (default: all)
timeout=N                         # Per-task timeout in seconds
```

### Error Handling
```
retry_failed=true                 # Retry failed tasks
retry_count=N                     # Maximum retry attempts
loop=N                            # Repeat task N times
return=N                          # Workflow exit code override
```

### Variables
```
# Global variables (top of file)
MY_VAR=value

# Reference global variables
hostname=@MY_VAR@

# Reference task output
arguments=--data @0_stdout@       # Use task 0 stdout
env_PASSWORD=@1_stdout@           # Task 1 output as environment variable

# Task metadata
@TaskID_exit_code@                # Exit code from task
@TaskID_stderr@                   # Stderr from task
@TaskID_success@                  # Boolean success state
```

### Advanced Conditions
```
condition=@0_all_success@                    # All task 0 instances succeeded
condition=@0_any_success@                    # At least one succeeded
condition=@0_majority_success@=75            # 75%+ succeeded
condition=@0_min_success@=5                  # At least 5 succeeded
condition=@0_max_failed@=3                   # No more than 3 failed
condition=@0_exit_code@=0                    # Task 0 exit code is 0
condition=@VARIABLE@=value                   # Variable comparison
```

---

## Common Workflow Patterns

### 1. Simple Sequential
```
task=0
hostname=localhost
command=echo
arguments=Step 1
exec=local

task=1
hostname=localhost
command=echo
arguments=Step 2
exec=local
```

### 2. Conditional Branching
```
task=0
hostname=localhost
command=health_check.sh
exec=local
success=exit_0
on_success=1
on_failure=2

task=1
hostname=localhost
command=echo
arguments=Healthy
exec=local
next=never

task=2
hostname=localhost
command=alert.sh
exec=local
```

### 3. Parallel Execution
```
task=0
hostname=web1,web2,web3,web4,web5
command=deploy.sh
exec=pbrun
max_parallel=2
timeout=300
retry_failed=true
retry_count=3
```

### 4. Loop Execution
```
task=0
hostname=localhost
command=process_batch.sh
exec=local
loop=10
timeout=600
```

### 5. Conditional Continuation
```
task=0
hostname=server1,server2,server3,server4,server5
command=health_check.sh
exec=local
max_parallel=5

task=1
hostname=localhost
command=echo
arguments=Majority healthy - proceeding
exec=local
condition=@0_majority_success@=60
on_success=10
on_failure=99

task=10
hostname=localhost
command=deploy.sh
exec=local

task=99
hostname=localhost
command=alert.sh
arguments=Too many servers unhealthy
exec=local
return=1
```

---

## Execution Types

| Type | Description | Use Case |
|------|-------------|----------|
| `local` | Direct subprocess execution | Local commands, strict security |
| `shell` | Shell execution (allows pipes, redirects) | Complex shell syntax needed |
| `pbrun` | PowerBroker privilege escalation | Enterprise privilege management |
| `p7s` | Password-based privilege escalation | Sudo-like with passwords |
| `wwrs` | Specific enterprise tool | Custom enterprise requirement |

---

## Security Features

✅ **Pre-execution validation** - Catches errors before running
✅ **Command injection protection** - Sanitizes dangerous input
✅ **Execution context awareness** - Different rules for shell vs. direct
✅ **Privilege escalation controls** - Enterprise tool integration
✅ **Command existence validation** - Verify commands exist before execution
✅ **Comprehensive audit logging** - Track all executions

---

## Logging & Project Tracking

```bash
# Execute with project tracking
tasker -r -p DEPLOYMENT_2024Q1 deploy.txt
```

**Log Location:** `/var/log/tasker/project_DEPLOYMENT_2024Q1/`

**Generated Files:**
- `TIMESTAMP_deploy.txt.log` - Full execution log
- `TIMESTAMP_deploy.txt.summary.log` - Executive summary

**Summary Includes:**
- Execution timeline
- Task statistics (succeeded/failed/retried/skipped)
- Server statistics
- Exit code and overall status

---

## Task File Syntax Rules

### ✅ ALLOWED:
```
# Full-line comments
task=0
hostname=localhost
# Another comment
command=echo
arguments=Hello TASKER
exec=local
```

### ❌ FORBIDDEN:
```
task=0
hostname=localhost
command=echo
arguments=test  # Inline comments NOT ALLOWED
exec=local
```

**Reason:** Inline comments cause parsing and security validation errors

---

## Example Workflows

### Health Check with Remediation
```
task=0
hostname=localhost
command=ping
arguments=-c 1 service.example.com
exec=local
success=exit_0
on_success=1
on_failure=2

task=1
hostname=localhost
command=echo
arguments=Service healthy
exec=local
next=never

task=2
hostname=localhost
command=systemctl
arguments=restart myservice
exec=local
```

### Rolling Deployment
```
# Global configuration
DEPLOY_VERSION=2.1.0
APP_PATH=/opt/myapp

task=0
hostname=web1,web2,web3,web4,web5
command=remove_from_lb.sh
arguments=--host @hostname@
exec=local

task=1
hostname=web1,web2,web3,web4,web5
command=deploy.sh
arguments=--version @DEPLOY_VERSION@ --path @APP_PATH@
exec=pbrun
timeout=600
retry_failed=true
retry_count=2

task=2
hostname=web1,web2,web3,web4,web5
command=health_check.sh
exec=local
success=exit_0&stdout~healthy
loop=3
timeout=30

task=3
hostname=web1,web2,web3,web4,web5
command=add_to_lb.sh
arguments=--host @hostname@
exec=local
```

---

## Debugging Tips

### 1. Dry Run First
```bash
tasker tasks.txt  # Validation only, no execution
```

### 2. Enable Debug Mode
```bash
tasker -r -d tasks.txt  # Detailed logging
```

### 3. Check Logs
```bash
# View latest log
ls -lt /var/log/tasker/ | head -5

# Check summary
cat /var/log/tasker/project_NAME/TIMESTAMP.summary.log
```

### 4. Validate Only
```bash
tasker --validate-only tasks.txt  # Skip host validation
```

### 5. Start Simple
- Test with one server first
- Add parallelism once working
- Build flow control incrementally

---

## Common Errors & Solutions

### Error: "Validation failed: Missing required parameter"
**Solution:** Ensure every task has: task, hostname, command, exec

### Error: "Security validation failed"
**Solution:** Check for command injection attempts, inline comments

### Error: "Command not found"
**Solution:** Use full path to command or add to PATH

### Error: "Circular dependency detected"
**Solution:** Check on_success/on_failure routing for loops

### Error: "Undefined variable"
**Solution:** Ensure global variables are declared before use

### Error: "Host validation failed"
**Solution:** Use `--skip-host-validation` or ensure connectivity

---

## When to Use TASKER

### ✅ Perfect For:
- Operational workflows (deployments, maintenance)
- Multi-server task orchestration
- Complex flow control with error handling
- Standardized runbooks
- Repeatable processes with audit trails

### ⚠️ Consider Alternatives:
- **Ansible** for configuration management
- **Terraform** for infrastructure provisioning
- **Jenkins** for CI/CD pipelines
- **Python** for complex business logic

---

## Resources

**Repository:** https://github.com/bastelbude1/Tasker
**Documentation:** README.md (2000+ lines, comprehensive)
**Examples:** `test_cases/functional/` (100+ working examples)
**Tests:** 487+ test cases covering all features
**License:** AGPL-3.0 (Free for internal use)

---

## Support

**Issues:** GitHub Issues (https://github.com/bastelbude1/Tasker/issues)
**Questions:** GitHub Discussions
**Contributions:** Pull requests welcome

---

## Quick Start Challenge

**Build your first workflow in 5 minutes:**

1. Create file: `my_workflow.txt`
2. Add tasks:
   ```
   task=0
   hostname=localhost
   command=echo
   arguments=My first TASKER workflow!
   exec=local

   task=1
   hostname=localhost
   command=date
   exec=local
   ```
3. Run: `tasker -r my_workflow.txt`
4. Celebrate! 🎉

---

## Pro Tips

💡 **Use project tracking** - Makes logs searchable
💡 **Validate before execution** - Catches 80% of errors
💡 **Start sequential, add parallel later** - Build incrementally
💡 **Use descriptive task IDs** - 0, 10, 20, 30 (easier to insert tasks)
💡 **Document with comments** - Future you will thank you
💡 **Version control task files** - Git is your friend
💡 **Test in dev first** - Never test in production
💡 **Use global variables** - Easier to update configurations

---

*TASKER 2.1 - Professional Task Automation for Enterprise Environments*

*Simple things stay simple. Complex things become possible. Everything remains readable.*
