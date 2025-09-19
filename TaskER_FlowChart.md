# TaskER FlowChart Block Inventory

This document provides a visual inventory of TaskER workflow blocks with their corresponding parameters.

<style>
.mermaid {
  text-align: center;
}
.mermaid svg {
  max-width: 100% !important;
  height: auto !important;
}
</style>

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
success=@1_exit_code@=0&@1_stdout@~running
next=@1_stdout@~completed
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
success=@1_exit_code@=0&@1_stdout@~running
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

## 5. Condition Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A{CONDITION} -->|TRUE| B[Execute if_true_tasks]
    A -->|FALSE| C[Execute if_false_tasks]

    style A fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    style B fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style C fill:#ffcdd2,stroke:#c62828,stroke-width:3px
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
- Tasks execute in specified order (10,11,12)

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
    A[Task Execution Block] --> B{LOOP}
    B -->|Continue| C[Repeat Task]
    B -->|Complete| D[Continue Workflow]
    C --> A

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style B fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style C fill:#fff3e0,stroke:#ef6c00,stroke-width:3px
    style D fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loop` | Integer | ✅ Yes | Number of additional iterations (1-100) |

### Example
```
task=5
hostname=server01
command=ping
arguments=-c 1 google.com
loop=3
```

### Entry Point
Applied to any Execution Block

### Behavior
- Repeats the same task for specified number of iterations
- `loop=3` means task executes 4 times total (original + 3 loops)
- Each iteration gets separate task result storage
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
    B --> E[Aggregate Results]
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
| `success` | String | ❌ Optional | Success criteria for individual tasks |
| `next` | String | ❌ Optional | Success evaluation condition |
| `on_success` | Integer | ❌ Optional | Task ID if next condition met |
| `on_failure` | Integer | ❌ Optional | Task ID if next condition not met |

### Example
```
task=8
type=parallel
tasks=10,11,12
success=@exit_code@=0
next=min_success=2
on_success=20
on_failure=99
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Executes multiple tasks simultaneously with threading
- Aggregates results based on `next` condition
- Supports all Multi-Task Success Evaluation Conditions
- Faster execution than sequential processing

</td>
</tr>
</table>

## 8. End Success Block

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
| `next` | String | ❌ Optional | Must be "never" |
| `return` | Integer | ❌ Optional | Exit code 0 |

### Examples

**Stop workflow successfully:**
```
next=never
```

**Explicit success with exit code:**
```
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

## 9. End Failure Block

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
| `next` | String | ❌ Optional | Must be "never" |
| `return` | Integer | ✅ Yes | Exit code 1-255 |

### Examples

**Stop workflow with failure:**
```
return=1
```

**Stop with specific error code:**
```
return=14
```

**Explicit failure with never:**
```
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