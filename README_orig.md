[[_TOC_]]

# TASK ExecutoR - TASKER

A flexible Python-based task execution system for running commands on remote or local servers with powerful flow control.

## Overview

The TASKER reads task definitions from a configuration file and executes them according to specified flow control rules. It supports various features including:

- Running commands on remote servers with multiple execution types
- Complex flow control based on exit codes and output patterns
- Variable substitution from previous task outputs
- Output splitting and processing
- Looping and conditional branching
- Error handling with goto functionality
- Command timeouts with customizable durations
- Host validation and connectivity testing
- Project-based execution summary logs

### Workflow
<details><summary>Workflow example - click to expand</summary>


```
# echo hello
task=0
hostname=localhost
command=echo
arguments=hello
exec=local
next=exit_0

# echo hello world
task=1
hostname=localhost
command=echo
arguments=@0_stdout@ world
exec=local
next=stdout~world

# count from 1 .. 3 (loop as long as stdout does NOT contain 2)
task=2
hostname=localhost
command=./increment_counter.sh
exec=local
sleep=1
next=loop&stdout!~2
loop=3

# toggle between exit 0 and exit (exit 1 = echo 1 to stderr, otherwise to stdout)
task=3
hostname=localhost
command=./toggle_exit.sh
exec=local
next=exit_0|stderr~
goto=6

# if task 4 was next TRUE, then echo hello world
task=4
hostname=localhost
command=echo
arguments=@1_stdout@
exec=local

# and show exit code from task 3 and stop successfully with return code = 0
task=5
hostname=localhost
command=echo
arguments=task3 exit code = @3_stderr@
exec=local
next=never
return 0

# if task 4 was next FALSE, then echo FAILED
task=6
hostname=localhost
command=echo
arguments=FAILED
exec=local
next=always

# and show exit code from task 3  and stop successfully with return code = 1
task=7
hostname=localhost
command=echo
arguments=task3 exit code = @3_stderr@
exec=local
next=never
return 1
```

</details>

![workflow](tasker_workflow.png)

#### Flow Control Logic

![flow_control_logic](flow_control_logic.png)

## Installation

Command is available on ALL WMPC **jumphosts** as **tasker**, which is an symbolic link to task_executor.py 

No special installation is required beyond Python 3.6.8 or higher. Simply download the `task_executor.py` and `task_validator.py` scripts and make them executable.

```bash
chmod +x task_executor.py task_validator.py
 ln -s /<path>/bin/task_executor.py /usr/bin/tasker
```

## Usage

### Basic Usage

To execute tasks in a file (dry run mode, doesn't actually execute commands):

```bash
tasker tasks.txt
```

To execute tasks for real:

```bash
tasker -r tasks.txt
```

### Command Line Options

```
usage: tasker [-h] [-r] [-l LOG_DIR] [-d] [-t {pbrun,p7s,local,wwrs}]
                        [-o TIMEOUT] [-c] [-p PROJECT] task_file

Execute tasks on remote servers.

positional arguments:
  task_file             Path to the task file

optional arguments:
  -h, --help            show this help message and exit
  -r, --run             Actually run the commands (not dry run)
  -l LOG_DIR, --log-dir LOG_DIR
                        Directory to store log files (default: ~/TASKER/logs)
  -d, --debug           Enable debug logging
  -t {pbrun,p7s,local,wwrs}, --type {pbrun,p7s,local,wwrs}
                        Execution type (overridden by task-specific settings)
  -o TIMEOUT, --timeout TIMEOUT
                        Default command timeout in seconds (5-1000, default: 30)
  -c, --check-connectivity
                        Check connectivity for pbrun/p7s/wwrs commands
  -p PROJECT, --project PROJECT
                        Project name for summary logging
```

### Environment Variables

You can use a few environment variable instead of arguments or instructions in the task file
This might be usefull in wrapper scripts

- `TASK_EXECUTOR_TYPE`: Sets the execution type (`pbrun`, `p7s`, `local`, or `wwrs`)
- `TASK_EXECUTOR_LOG`: Sets the custom log directory (default is ~/TASKER/)
- `TASK_EXECUTOR_TIMEOUT`: Sets the custoom command timeout in seconds (default 30)

Note: instructins override arguments and arguments overwrite environment variables

## Default LOG Directory Structure

The task executor creates and uses the following directory structure by default:

```
~/TASKER/
```

Each task file execution creates:
1. A timestamped log file in the logs directory
2. A timestamped copy of the task file in the tasks directory

if used with `-p <project>`, you will find as well

- a poject summary file of all tasks which are run under this project id (append)

## Task File Format

Task files use a simple key-value format with comments starting with `#`.

### Basic Example

```
# Basic example
task=0
hostname=serverA
command=ls
arguments=-la

task=1
hostname=serverB
command=date
```

### Task Definition

Each task must have at least:
- `task`: unique numerical ID
- `hostname`: target server (except for return tasks)
- `command`: the command to execute

Optional parameters include:
- `arguments`: command arguments
- `next`: condition for proceeding to next task
- `exec`: execution type for this specific task
- `timeout`: command timeout in seconds

### Flow Control

The `next` parameter controls whether to proceed to the next task:

```
# Proceed only if exit code is 0
next=exit_0

# Proceed only if stdout contains "Success"
next=stdout~Success

# Proceed if exit is 0 AND stdout contains "Success"
next=exit_0&stdout~Success

# Proceed if exit is 0 AND (stdout contains "Success" OR stderr is empty)
next=exit_0&(stdout~Success|stderr~)

# Never proceed (end of execution)
next=never

# Always proceed regardless of result
next=always
```

The `next=loop` parameter defines, that the same task will be repeated `loop=X` additional times:
`next=loop&exit_0` is an loop break definition, If exit == 0, then we will end the loop!

Note: loop=2 does mean that the task will be executed overall 3 times!

```
# Loop this task
next=loop
loop=3

# Loop with condition (exit if condition not met)
next=loop&exit_0
loop=5
```

### Special Features

#### Variable Substitution

Use output from previous tasks:

```
task=0
hostname=serverA
command=echo
arguments="Hello World"

task=1
hostname=serverB
command=echo
arguments="Previous output: @0_stdout@"
```

#### Output Splitting

Split and process task output:

```
task=0
hostname=serverA
command=echo
arguments="value1 value2 value3"
stdout_split=space,1

# Now @0_stdout@ will be "value2"
```

Supported delimiters:
- `space`: Split by whitespace
- `tab`: Split by tabs
- `comma`: Split by commas
- `semi`: Split by semicolons
- `pipe`: Split by pipes

#### Error Handling with Goto

Jump to a specific task on failure:

```
task=0
hostname=serverA
command=risky_command
next=exit_0
goto=2

task=1
hostname=serverA
command=success_command

task=2
hostname=serverA
command=error_handler
```

Note: If `next=never` is specified, it takes precedence over any `goto` instruction.

#### Return Codes

Exit the execution with a specific code:

```
task=0
hostname=serverA
command=check_condition
next=exit_0
goto=1

# Success path
return=0

task=1
# Error path
return=1
```

#### Sleep

Pause between tasks:

```
task=0
hostname=serverA
command=echo
arguments="Starting"
sleep=5  # Sleep for 5 seconds
```

#### Command Timeouts

Set a timeout for command execution:

```
task=0
hostname=serverA
command=long_running_process
timeout=120  # Wait up to 120 seconds before killing the process
```

#### Customizable Execution Types

Specify different command execution formats:

```
task=0
hostname=serverA
command=ls
arguments=-la
exec=pbrun  # Use pbrun execution type

task=1
hostname=serverB
command=1234
exec=wwrs  # Use wwrs execution type
```

Available execution types:
- `pbrun`: `pbrun -n -h {hostname} {command} {arguments}`
- `p7s`: `p7s {hostname} {command} {arguments}`
- `local`: `{command} {arguments}`
- `wwrs`: `wwrs_cli {hostname} "{command} {arguments}"`

## Condition Syntax

### Exit Code Conditions
- `exit_0`: Exit code equals 0
- `exit_1`: Exit code equals 1
- `exit_N`: Exit code equals N

### Output Pattern Matching (same for stderr)
- `stdout~pattern`: stdout contains "pattern"
- `stdout!~pattern`: stdout does NOT contain "pattern"
- `stdout~`: stdout is empty
- `stdout!~`: stdout is NOT empty

### Line Count Conditions (same for stderr)
- `stdout_count=N`: stdout has exactly N lines
- `stdout_count>N`: stdout has more than N lines
- `stdout_count<N`: stdout has fewer than N lines

### Combined Conditions
- `&`: AND operator
- `|`: OR operator
- `()`: Grouping
- Example: `exit_0&(stdout~Success|stderr~)`

## Validation

By default, Task Executor validates that all hostnames:
1. Can be resolved to an IP address (via DNS or op mc_isac)
2. Are reachable (via ping)

With the `-c` option, it also checks connectivity for the specific execution type:
- For `pbrun`: Tests `pbrun -n -h {hostname} pbtest`
- For `p7s`: Tests `p7s {hostname} pbtest`
- For `wwrs`: Tests `wwrs_clir {hostname} wwrs_test`

And the task files will be validated as well (see also task_validator)

Following checks will be done for the task file:

- Required fields
- Syntax errors
- Referenced but undefined tasks
- Invalid conditions
- Command formatting
- And more

**If there is any issue, the TASKER will not execute any task**

## Project Summary Logging

When the `-p` option is used, Task Executor creates a tab delimited project summary log file containing:

- A header row with column names
- One entry per task file execution showing:
  - Timestamp
  - Task filename
  - Final task ID
  - Final hostname
  - Final command
  - Exit code
  - Success/failure status
  - Log file reference

This is useful for tracking multiple task executions across a project.


## Logging

Execution logs are stored in the specified log directory (default: `~/TASKER/logs/`). Each execution creates a timestamped log file with detailed information about:
- Commands executed
- Exit codes
- Standard output and error
- Flow control decisions

## Examples

### Simple Sequential Tasks

```
task=0
hostname=server1
command=echo
arguments="Step 1"

task=1
hostname=server1
command=echo
arguments="Step 2"
```

### Conditional Execution

```
task=0
hostname=server1
command=check_status
next=exit_0&stdout~running
goto=2

task=1
hostname=server1
command=echo
arguments="Service is running"
next=never

task=2
hostname=server1
command=echo
arguments="Service is not running"
command=start_service
```

### Loop Example

```
task=0
hostname=server1
command=setup
arguments="initialization"

task=1
hostname=server1
command=process_item
arguments="item_@0_stdout@"
next=loop
loop=5

task=2
hostname=server1
command=echo
arguments="Processing complete"
```

### Project Execution

To execute tasks as part of a named project:

```bash
tasker -r -p myproject tasks.txt
```

This creates a summary log `~/TASKER/logs/project_myproject_summary.log` that tracks all executions for this project.

## Troubleshooting

If you encounter issues:

1. Run with debug option: `tasker -d -r tasks.txt`
2. Validate your task file: `tasker tasks.txt`
3. Check the log files in your log directory
4. Run with connectivity checks: `tasker -r -c tasks.txt`
5. Ensure your execution type is supported in your environment

## Single Task File Validation

Use the task validator to check your task file before execution:

```bash
tasker tasks.txt
```

The validator checks:
- Required fields
- Syntax errors
- Referenced but undefined tasks
- Invalid conditions
- Command formatting
- And more


# Parallel task executoR - parallelr

A flexible Python-based script to execute file based tasks in parallel, for example tasker files


## Usage

```
usage: parallelr [-h] [-m MAX] [-t TIMEOUT] [-w WAIT] [-T TASKSDIR]
                 [-C COMMAND] [-r] [-d] [--enable-stop-limits]
                 [--list-workers] [-k [PID]] [--validate-config]
                 [--show-config] [--log-task-output]

Parallel Task Executor - Python 3.6.8 Compatible

optional arguments:
  -h, --help            show this help message and exit
  -m MAX, --max MAX     Maximum parallel tasks (overrides config)
  -t TIMEOUT, --timeout TIMEOUT
                        Task timeout in seconds (overrides config)
  -w WAIT, --wait WAIT  Wait time before checking for free slots (overrides
                        config)
  -T TASKSDIR, --TasksDir TASKSDIR
                        Directory containing task files
  -C COMMAND, --Command COMMAND
                        Command template with @TASK@ pattern to execute
  -r, --run             Execute tasks (default is dry-run)
  -d, --daemon          Run as background daemon (detached from user session)
  --enable-stop-limits  Enable auto-stop on consecutive failures or high
                        failure rate
  --list-workers        List running parallel-tasker processes (safe)
  -k [PID], --kill [PID]
                        Kill processes: -k (all) or -k PID (specific) -
                        DANGEROUS!
  --validate-config     Validate configuration file and exit
  --show-config         Show current configuration and recommended location
  --log-task-output     Enable detailed task output logging to TaskResults
                        file
```


## Examples

  ### Execute tasks (foreground)
  `parallelr -T ./tasks -C "python3 @TASK@" -r`

  ### Execute tasks (background/detached)
  `parallelr -T ./tasks -C "python3 @TASK@" -r -d`

  ### List running workers (safe)
  `parallelr --list-workers`

  ### Kill all running instances (dangerous)
  `parallelr -k`

