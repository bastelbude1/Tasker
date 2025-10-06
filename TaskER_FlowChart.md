# TaskER FlowChart Block Inventory

This document provides a visual inventory of TaskER workflow blocks with their corresponding parameters.

## 1. Execution Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Task Execution Block]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `hostname` | String | ✅ Yes | Target server or @HOSTNAME@ |
| `command` | String | ✅ Yes | Command to execute |
| `arguments` | String | ❌ Optional | Command arguments |

### Example
```
task=0
hostname=server01
command=ls
arguments=-la /var/log
```

</td>
</tr>
</table>

## 2. Success Check Block (with next)

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Task Execution Block] --> B{SUCCESS}
    B -->|next condition met| C[Continue to Next Task]
    B -->|next condition not met| D((END))

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:3px
    style C fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style D fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `success` | String | ❌ Optional | Custom success criteria |
| `next` | String | ❌ Optional | Flow control (never, return=X, task ID) |

### Example
```
# Applied to existing task:
success=exit_0&stdout~running
next=success
```

### Entry Point
Follows after Task Execution Block

### Behavior
- Evaluates success criteria
- If `next` condition met → Continue to next sequential task
- If `next` condition not met → End workflow or return with code

</td>
</tr>
</table>

## 3. Success Check Block (with on_success/on_failure)

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Task Execution Block] --> B{SUCCESS}
    B -->|Success| C[Jump to on_success Task]
    B -->|Failure| D[Jump to on_failure Task]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:3px
    style C fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style D fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `success` | String | ❌ Optional | Custom success criteria |
| `on_success` | Integer | ❌ Optional | Task ID to jump to on success |
| `on_failure` | Integer | ❌ Optional | Task ID to jump to on failure |

### Example
```
# Applied to existing task:
success=exit_0&stdout~running
on_success=20
on_failure=99
```

### Entry Point
Follows after Task Execution Block

### Behavior
- Evaluates success criteria
- If success → Jump to `on_success` task ID
- If failure → Jump to `on_failure` task ID
- Allows non-sequential workflow jumps

</td>
</tr>
</table>

## 4. Sleep Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Previous Block] --> B[SLEEP]
    B --> C[Continue]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style C fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sleep` | Integer | ❌ Optional | Sleep duration (0-300 seconds) |

### Example
```
# Applied to existing task:
sleep=5
```

### Entry Point
Can follow any block that executes

### Behavior
- Pauses workflow execution for specified seconds
- Useful for rate limiting or waiting for external processes
- Does not affect task success/failure status

</td>
</tr>
</table>

## 5. Conditional Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A{CONDITION} -->|TRUE| B[Execute if_true_tasks]
    A -->|FALSE| C[Execute if_false_tasks]
    B --> D[Multi-Task Success Evaluation]
    C --> D

    style A fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    style B fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style C fill:#ffcdd2,stroke:#c62828,stroke-width:3px
    style D fill:#ffecb3,stroke:#f57f17,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `type` | String | ✅ Yes | Must be "conditional" |
| `condition` | String | ✅ Yes | Boolean expression to evaluate |
| `if_true_tasks` | String | ✅ Yes* | Task IDs for TRUE branch |
| `if_false_tasks` | String | ✅ Yes* | Task IDs for FALSE branch |

*At least one of `if_true_tasks` or `if_false_tasks` must be specified.

### Example
```
task=2
type=conditional
condition=@0_stdout@=OPEN
if_true_tasks=10,11,12
if_false_tasks=20,21
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Evaluates boolean condition expression
- If TRUE → Execute tasks in `if_true_tasks` list
- If FALSE → Execute tasks in `if_false_tasks` list
- Tasks execute sequentially in specified order (10,11,12)
- Results feed into Multi-Task Success Evaluation Block (see #10.1)

### Next Block
→ Multi-Task Success Evaluation Block (#10.1)

</td>
</tr>
</table>

## 6. Loop Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Task Execution Block] --> B{LOOP?}
    B -->|Counter < Max & Break Condition False| A
    B -->|Counter >= Max OR Break Condition True| C[Continue Workflow]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style C fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loop` | Integer | ✅ Yes | Number of iterations to execute (1-100) |
| `next` | String | ✅ Yes | Must be "loop" |
| `loop_break` | String | ❌ Optional | Condition to break out of loop early |

### Example
```
task=0
hostname=localhost
command=conditional_exit.sh
arguments=3
exec=local
loop=10
next=loop
loop_break=exit_0
```

### Entry Point
Applied to any Execution Block

### Behavior
- Repeats the same task for specified number of iterations
- `loop=3` means task executes exactly 3 times (Task X.1, X.2, X.3)
- `next=loop` is mandatory to enable loop functionality
- `loop_break` condition can terminate loop early if met
- Each iteration gets separate task result storage
- Task IDs are displayed with iteration numbers (e.g., Task 5.1, 5.2, 5.3)
- Useful for retry patterns or periodic checks

</td>
</tr>
</table>

## 7. Parallel Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Parallel Block] --> B[Task 10]
    A --> C[Task 11]
    A --> D[Task 12]
    B --> E[Multi-Task Success Evaluation]
    C --> E
    D --> E

    style A fill:#e8f5e8,stroke:#388e3c,stroke-width:3px
    style B fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style C fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style D fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style E fill:#ffecb3,stroke:#f57f17,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `type` | String | ✅ Yes | Must be "parallel" |
| `tasks` | String | ✅ Yes | Comma-separated task IDs to execute |
| `max_parallel` | Integer | ❌ Optional | Max concurrent tasks (1-50, default: all) |

### Example
```
task=8
type=parallel
tasks=10,11,12
max_parallel=2
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Executes multiple tasks simultaneously with threading
- Results feed into Multi-Task Success Evaluation Block (see #10)
- Faster execution than sequential processing

### Next Block
→ Multi-Task Success Evaluation Block (#10)

</td>
</tr>
</table>

## 8. Parallel Block with Retry

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Parallel Block with Retry] --> B[Task 10]
    A --> C[Task 11]
    A --> D[Task 12]
    B --> E{Retry?}
    C --> F{Retry?}
    D --> G{Retry?}
    E -->|Failed & Retries Left| B
    E -->|Success OR Retries Exhausted| H[Multi-Task Success Evaluation]
    F -->|Failed & Retries Left| C
    F -->|Success OR Retries Exhausted| H
    G -->|Failed & Retries Left| D
    G -->|Success OR Retries Exhausted| H

    style A fill:#e8f5e8,stroke:#388e3c,stroke-width:3px
    style B fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style C fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style D fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style E fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style F fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style G fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style H fill:#ffecb3,stroke:#f57f17,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `type` | String | ✅ Yes | Must be "parallel" |
| `tasks` | String | ✅ Yes | Comma-separated task IDs to execute |
| `max_parallel` | Integer | ❌ Optional | Max concurrent tasks (1-50, default: all) |
| `retry_failed` | Boolean | ✅ Yes | Must be "true" to enable retry |
| `retry_count` | Integer | ❌ Optional | Number of retry attempts (0-10, default: 1) |
| `retry_delay` | Integer | ❌ Optional | Delay between retries (0-300 seconds, default: 1) |

### Example
```
task=8
type=parallel
tasks=10,11,12
max_parallel=2
retry_failed=true
retry_count=3
retry_delay=5
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Executes multiple tasks simultaneously with threading
- Failed tasks are automatically retried up to `retry_count` times
- `retry_delay` seconds between retry attempts
- Results feed into Multi-Task Success Evaluation Block (see #10)
- More resilient than basic parallel execution

### Next Block
→ Multi-Task Success Evaluation Block (#10)

</td>
</tr>
</table>

## 9. Conditional Block with Retry

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A{CONDITION} -->|TRUE| B[Execute if_true_tasks]
    A -->|FALSE| C[Execute if_false_tasks]
    B --> D{Retry?}
    C --> E{Retry?}
    D -->|Failed & Retries Left| B
    D -->|Success OR Retries Exhausted| F[Multi-Task Success Evaluation]
    E -->|Failed & Retries Left| C
    E -->|Success OR Retries Exhausted| F

    style A fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    style B fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style C fill:#ffcdd2,stroke:#c62828,stroke-width:3px
    style D fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style E fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style F fill:#ffecb3,stroke:#f57f17,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `type` | String | ✅ Yes | Must be "conditional" |
| `condition` | String | ✅ Yes | Boolean expression to evaluate |
| `if_true_tasks` | String | ✅ Yes* | Task IDs for TRUE branch |
| `if_false_tasks` | String | ✅ Yes* | Task IDs for FALSE branch |
| `retry_failed` | Boolean | ✅ Yes | Must be "true" to enable retry |
| `retry_count` | Integer | ❌ Optional | Number of retry attempts (0-10, default: 1) |
| `retry_delay` | Integer | ❌ Optional | Delay between retries (0-300 seconds, default: 1) |

*At least one of `if_true_tasks` or `if_false_tasks` must be specified.

### Example
```
task=2
type=conditional
condition=@0_stdout@=OPEN
if_true_tasks=10,11,12
if_false_tasks=20,21
retry_failed=true
retry_count=2
retry_delay=3
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Evaluates boolean condition expression
- If TRUE → Execute tasks in `if_true_tasks` list
- If FALSE → Execute tasks in `if_false_tasks` list
- Failed tasks in chosen branch are automatically retried
- Tasks execute sequentially with retry logic
- Results feed into Multi-Task Success Evaluation Block (see #10.1)

### Next Block
→ Multi-Task Success Evaluation Block (#10.1)

</td>
</tr>
</table>


## 10.1. Multi-Task Success Evaluation Block (next)

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Multiple Tasks Completed] --> B{EVALUATE RESULTS}
    B -->|Condition Met| C[Continue Workflow]
    B -->|Condition Not Met| D((END WORKFLOW))

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:3px
    style C fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style D fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `next` | String | ✅ Yes | Success evaluation condition |

### Available Conditions
| Condition | Logic | Example |
|-----------|-------|---------|
| `min_success=N` | success_count ≥ N | `min_success=3` |
| `max_failed=N` | failed_count ≤ N | `max_failed=1` |
| `all_success` | success_count = total_tasks | `all_success` |
| `any_success` | success_count > 0 | `any_success` |
| `majority_success` | success_count > total_tasks/2 | `majority_success` |

### Example
```
next=min_success=3
```

### Entry Point
Follows after Parallel Block or Conditional Block

### Behavior
- Evaluates success condition against task results
- If condition met → Continue to next sequential task
- If condition not met → End workflow (default behavior)

</td>
</tr>
</table>

## 10.2. Multi-Task Success Evaluation Block (on_success/on_failure)

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Multiple Tasks Completed] --> B{EVALUATE RESULTS}
    B -->|Condition Met| C[Jump to on_success Task]
    B -->|Condition Not Met| D[Jump to on_failure Task]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:3px
    style C fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style D fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `on_success` | Integer | ❌ Optional | Task ID if condition met |
| `on_failure` | Integer | ❌ Optional | Task ID if condition not met |

### Default Behavior (no explicit condition)
- **`on_success`** → `all_success` (100% success required)
- **`on_failure`** → Any failure triggers this path

### Example
```
on_success=20
on_failure=99
```

### Entry Point
Follows after Parallel Block or Conditional Block

### Behavior
- Evaluates default success condition (all_success) against task results
- If condition met → Jump to `on_success` task ID
- If condition not met → Jump to `on_failure` task ID
- Allows non-sequential workflow jumps

</td>
</tr>
</table>

## 11. End Success Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A((END SUCCESS))

    style A fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `next` | String | ❌ Optional | Must be "never" |
| `return` | Integer | ❌ Optional | Exit code 0 |

### Examples

**Stop workflow successfully:**
```
task=99
next=never
```

**Explicit success with exit code:**
```
task=100
return=0
```

### Entry Point
Terminal block - workflow ends successfully

### Behavior
- Workflow terminates with success status
- Default exit code: 0
- Overall workflow result: SUCCESS

</td>
</tr>
</table>

## 12. End Failure Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A((END FAILURE))

    style A fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `next` | String | ❌ Optional | Must be "never" |
| `return` | Integer | ✅ Yes | Exit code 1-255 |

### Examples

**Stop workflow with failure:**
```
task=98
return=1
```

**Stop with specific error code:**
```
task=97
return=14
```

**Explicit failure with never:**
```
task=96
next=never
return=1
```

### Entry Point
Terminal block - workflow ends with failure

### Behavior
- Workflow terminates with failure status
- Exit code: 1-255 (non-zero = failure)
- Overall workflow result: FAILURE

</td>
</tr>
</table>

## 13. Configuration Definition Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[CONFIGURATION PARAMETERS]

    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `timeout` | Integer | ❌ Optional | Override default timeout for this specific task (5-3600 seconds) |
| `exec` | String | ❌ Optional | Override default execution type for this specific task (pbrun, p7s, local, wwrs) |

### Examples
```
# Configuration parameters within a task
task=0
hostname=server1
command=deploy
timeout=60                 # Override default timeout
exec=pbrun                # Override default exec type
```

### Note on Project Parameter
**`project` is NOT a task parameter** - it only works as command-line option:
- ✅ **Command-line**: `tasker -p PROJECT_NAME tasks.txt` (creates shared summary files)
- ❌ **Task parameter**: `project=PROJECT_NAME` (NOT implemented in TASKER)

### Entry Point
Applied to individual tasks to override TASKER defaults

### Behavior
- **Must be part of a task definition** (unlike global variables)
- **timeout**: Overrides default timeout for this specific task
- **exec**: Overrides default execution method for this specific task
- These are **task parameters**, not standalone configurations
- Same functionality as command-line options (-o, -t) but task-specific
- **Key Distinction**: Global variables are standalone KEY=VALUE, these are task parameters

### Task-Level Override Example
```
# Task with configuration overrides
task=1
hostname=server1
command=deploy
timeout=300               # Override default timeout
exec=pbrun               # Override default exec type
```

</td>
</tr>
</table>

## 14. Global Variable Definition Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[GLOBAL VARIABLES]

    style A fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `VARIABLE_NAME` | String | ✅ Yes | Any uppercase variable name |
| `value` | String | ✅ Yes | Variable value or expression |

### Examples
```
ENVIRONMENT=production
DATABASE_HOST=db.company.com
RETRY_COUNT=3
TIMEOUT_SECONDS=30
```

### Entry Point
Must be at the beginning of workflow file

### Behavior
- Defines reusable variables for entire workflow
- Variables are read-only and available throughout file
- Use @VARIABLE_NAME@ syntax to reference in tasks
- Case-sensitive variable names (recommended: UPPERCASE)
- Automatic creation - any KEY=VALUE that's not a task parameter

</td>
</tr>
</table>

## 15. Output Processing Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Task Execution Completed] --> B[SPLIT OUTPUT]
    B --> C[REPLACE Original Output]
    C --> D[Continue Workflow]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#e8f5e8,stroke:#388e3c,stroke-width:3px
    style C fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style D fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `stdout_split` | String | ❌ Optional | Split stdout by delimiter and select element |
| `stderr_split` | String | ❌ Optional | Split stderr by delimiter and select element |

### Supported Delimiters
| Keyword | Splits On | Example |
|---------|-----------|---------|
| `space` | Any whitespace(s) | `stdout_split=space,0` |
| `tab` | Tab character(s) | `stdout_split=tab,1` |
| `comma` | Comma | `stdout_split=comma,2` |
| `semi` | Semicolon | `stdout_split=semi,0` |
| `pipe` | Pipe character | `stdout_split=pipe,1` |

**⚠️ WARNING**: Escape sequences like `\n` are NOT interpreted! Use literal characters only.

### Example
```
# Applied to existing task:
stdout_split=comma,1    # Split by comma, get 2nd element (0-indexed)
stderr_split=space,0    # Split by spaces, get 1st element
```

### Entry Point
Applied to any task that produces output

### Behavior
- Splits stdout/stderr by specified delimiter and selects element by index (0-based)
- Format: `delimiter,index` (e.g., `comma,1` for second element)
- Modified output replaces original for subsequent processing
- **LIMITATION**: Cannot split by newline - escape sequences not supported

</td>
</tr>
</table>
