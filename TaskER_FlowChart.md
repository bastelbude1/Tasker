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
```bash
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
```bash
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
```bash
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
    style B fill:#e0f7fa,stroke:#00acc1,stroke-width:3px
    style C fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sleep` | Integer | ❌ Optional | Sleep duration (0-300 seconds) |

### Example
```bash
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
```bash
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
- Results feed into Multi-Task Success Evaluation Block (see # 11.1)

**CRITICAL Routing Restrictions:**
- **Subtasks CANNOT have routing parameters** (`on_success`, `on_failure`, `next=never/loop`)
- Control MUST return to conditional block for Multi-Task Success Evaluation
- Validation will **FAIL** if subtasks contain routing parameters
- **Use Decision Blocks** instead if individual task routing is needed

**Subtask ID Range Convention (Recommended):**
- Use distinct ID ranges to clearly separate subtasks from main workflow
- Recommended: Task N subtasks in range `[N*100, (N+1)*100-1]`
- Example: Task 2 subtasks → 200-299 (calculation: 2×100=200 to 3×100-1=299)
- Example: Task 1 subtasks → 100-199, Task 5 subtasks → 500-599
- Use `--skip-subtask-range-validation` to suppress warnings

### Next Block
→ Multi-Task Success Evaluation Block (# 11.1)

</td>
</tr>
</table>

## 6. Decision Block

Decision blocks provide lightweight conditional routing without command execution. Two routing patterns available:

### 6.1 Decision Block with next Parameter

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Decision Block<br/>Evaluate Condition] --> B{SUCCESS}
    B -->|next condition met| C[Continue to Next Task]
    B -->|next condition not met| D((END))

    style A fill:#FFE4E1,stroke:#DC143C,stroke-width:3px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:3px
    style C fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style D fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Purpose
Simple pass/fail gate using `next` parameter for routing

### Required Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `type` | String | ✅ Yes | Must be "decision" |
| `success` | String | ✅ Yes* | Success condition to evaluate |
| `next` | String | ⚠️ Optional | Routing: always, never, success (default) |

*Either `success` OR `failure` is required.

### Example
```bash
# Early exit if both ports failed
task=2
type=decision
success=@0_exit@=0|@1_exit@=0
next=success
# If TRUE → continue (next=success evaluates TRUE)
# If FALSE → stop (next=success evaluates FALSE)
```

### Behavior
**Default behavior (`next=success` if missing):**
- Condition TRUE → Continue to next task
- Condition FALSE → **Workflow STOPS**

**Other `next` values:**
- `next=always` → Always continue regardless
- `next=never` → Always stop regardless

### Use Case
Perfect for early exit scenarios where you want to stop if a condition fails.

</td>
</tr>
</table>

### 6.2 Decision Block with on_success/on_failure

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Decision Block<br/>Evaluate Condition] --> B{SUCCESS}
    B -->|Success| C[Jump to on_success Task]
    B -->|Failure| D[Jump to on_failure Task]

    style A fill:#FFE4E1,stroke:#DC143C,stroke-width:3px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:3px
    style C fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style D fill:#ffcdd2,stroke:#c62828,stroke-width:3px
```

</td>
<td width="60%">

### Purpose
Explicit routing to different task paths based on condition result

### Required Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `type` | String | ✅ Yes | Must be "decision" |
| `success` | String | ✅ Yes* | Success condition to evaluate |
| `on_success` | Integer | ⚠️ Optional** | Task ID for TRUE path |
| `on_failure` | Integer | ⚠️ Optional** | Task ID for FALSE path |

*Either `success` OR `failure` is required.
**At least one routing parameter recommended.

### Example
```bash
# Route based on port availability
task=2
type=decision
success=@0_exit@=0|@1_exit@=0
on_success=3
on_failure=99
# If TRUE → jump to task 3 (try downloads)
# If FALSE → jump to task 99 (error handler)
```

### Behavior
**Routing Priority:**
1. Check `on_success` or `on_failure` based on condition result
2. If not defined, falls back to `next` parameter logic

### Use Case
Perfect for branching workflows where different paths handle success vs failure differently.

</td>
</tr>
</table>

### Key Differences from Conditional Block
- No command execution (no `hostname`, `command`, `arguments`)
- No task branches (`if_true_tasks`, `if_false_tasks`)
- Pure routing logic - lighter weight
- Uses familiar success/failure condition syntax

### Next Block
→ Jump to specified task ID or continue/stop based on routing

## 7. Task-Level Conditional Execution

<table>
<tr>
<td width="40%">

```mermaid
graph TB
    %% Task with condition parameter
    Start([Start]) --> C{Evaluate<br/>condition<br/>parameter}

    %% Conditional skip paths
    C -->|FALSE| Skip[Task Skipped<br/>exit_code=-1<br/>Continue to next task]
    C -->|TRUE| Exec[Execute Task<br/>command + arguments]

    Exec --> Success[Store Results<br/>Apply routing]
    Skip --> Next[Next Sequential Task]
    Success --> Routing{Routing?}
    Routing -->|on_success| OS[Jump to<br/>on_success task]
    Routing -->|on_failure| OF[Jump to<br/>on_failure task]
    Routing -->|next| Seq[Continue<br/>Sequentially]

    %% Style
    style C fill:#ede7f6,stroke:#7b1fa2,stroke-width:2px
    style Skip fill:#E0E0E0
    style Exec fill:#E1F5FE
    style Success fill:#C8E6C9
    style Routing fill:#FFE4E1
    style OS fill:#90EE90
    style OF fill:#FFB6C1
    style Seq fill:#E6E6FA
```

</td>
<td width="60%">

### Purpose
Skip individual tasks based on runtime conditions (regular task parameter)

### Required Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `condition` | String | ✅ Yes | Condition to evaluate before execution |
| `command` | String | ✅ Yes | Command to execute if condition TRUE |
| `hostname` | String | ✅ Yes | Target host |

### Example
```bash
task=1
hostname=web-server
command=restart_service
# Skip if previous task failed
condition=@0_exit@=0
on_success=10
on_failure=99
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Evaluates `condition` **before** executing task
- If `condition` FALSE → Task **skipped**, continue to next sequential task
- If `condition` TRUE → Task executes normally
- Skipped tasks store: `exit_code=-1`, `stderr='Task skipped due to condition'`
- Can be combined with routing (`on_success`, `on_failure`, `next`)

**Key Distinctions:**

| Mechanism | Skip Logic | Routing | Use Case |
|-----------|------------|---------|----------|
| Task Condition | Individual task | ✅ Allowed | Skip specific tasks in sequence |
| Decision Block | No execution | ✅ Purpose | Pure routing based on data |
| Conditional Block | Task groups | ❌ Not allowed | Execute groups of tasks |

### Next Block
- If skipped → Continue to next sequential task
- If executed → Apply routing (`on_success`, `on_failure`) or continue sequentially

</td>
</tr>
</table>

## 8. Loop Block

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
    style B fill:#fff8e1,stroke:#f57c00,stroke-width:3px
    style C fill:#e1f5fe,stroke:#01579b,stroke-width:3px
```

</td>
<td width="60%">

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loop` | Integer | ✅ Yes | Number of iterations to execute (1-1000) |
| `next` | String | ✅ Yes | Must be "loop" |
| `loop_break` | String | ❌ Optional | Condition to break out of loop early |

### Example
```bash
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
- **Loop vs Retry**: Loops execute ALL iterations regardless of success/failure (unless `loop_break` is met). This differs from retry logic (Section 8-9), which ONLY retries tasks that fail.
- **Only the LAST iteration result is stored** - `@X_stdout@` references get final iteration output
- Task IDs are displayed with iteration numbers (e.g., Task 5.1, 5.2, 5.3)
- Useful for retry patterns or periodic checks

</td>
</tr>
</table>

## 9. Parallel Block

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

    style A fill:#e0f2f1,stroke:#00897b,stroke-width:3px
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
```bash
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

**CRITICAL Routing Restrictions:**
- **Subtasks CANNOT have routing parameters** (`on_success`, `on_failure`, `next=never/loop`)
- Control MUST return to parallel block for Multi-Task Success Evaluation
- Validation will **FAIL** if subtasks contain routing parameters
- **Use Decision Blocks** instead if individual task routing is needed

**Subtask ID Range Convention (Recommended):**
- Use distinct ID ranges to clearly separate subtasks from main workflow
- Recommended: Task N subtasks in range `[N*100, (N+1)*100-1]`
- Example: Task 2 subtasks → 200-299 (calculation: 2×100=200 to 3×100-1=299)
- Example: Task 1 subtasks → 100-199, Task 5 subtasks → 500-599
- Use `--skip-subtask-range-validation` to suppress warnings

### Next Block
→ Multi-Task Success Evaluation Block (#10)

</td>
</tr>
</table>

## 10. Parallel Block with Retry

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

    style A fill:#e0f2f1,stroke:#00897b,stroke-width:3px
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
| `retry_count` | Integer | ❌ Optional | Number of retry attempts (1-1000, default: 1, enables retry) |
| `retry_delay` | Integer | ❌ Optional | Delay between retries (0-300 seconds, default: 1) |

### Example
```bash
task=8
type=parallel
tasks=10,11,12
max_parallel=2
retry_count=3
retry_delay=5
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Executes multiple tasks simultaneously with threading
- **Retry vs Loop**: Failed tasks are automatically retried up to `retry_count` times. This differs from loop logic (Section 6), which executes ALL iterations regardless of success/failure.
- `retry_delay` seconds between retry attempts
- Results feed into Multi-Task Success Evaluation Block (see #10)
- More resilient than basic parallel execution

### Next Block
→ Multi-Task Success Evaluation Block (#10)

</td>
</tr>
</table>

## 11. Conditional Block with Retry

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
| `retry_count` | Integer | ❌ Optional | Number of retry attempts (1-1000, default: 1, enables retry) |
| `retry_delay` | Integer | ❌ Optional | Delay between retries (0-300 seconds, default: 1) |

*At least one of `if_true_tasks` or `if_false_tasks` must be specified.

### Example
```bash
task=2
type=conditional
condition=@0_stdout@=OPEN
if_true_tasks=10,11,12
if_false_tasks=20,21
retry_count=2
retry_delay=3
```

### Entry Point
Can be entry point or follow any block

### Behavior
- Evaluates boolean condition expression
- If TRUE → Execute tasks in `if_true_tasks` list
- If FALSE → Execute tasks in `if_false_tasks` list
- **Retry vs Loop**: Failed tasks in chosen branch are automatically retried up to `retry_count` times. This differs from loop logic (Section 6), which executes ALL iterations regardless of success/failure.
- Tasks execute sequentially with retry logic
- Results feed into Multi-Task Success Evaluation Block (see # 11.1)

### Next Block
→ Multi-Task Success Evaluation Block (# 11.1)

</td>
</tr>
</table>


## 12. Multi-Task Success Evaluation Block (next)

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
    style B fill:#ffe0b2,stroke:#f57f17,stroke-width:3px
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
```bash
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

## 13. Multi-Task Success Evaluation Block (on_success/on_failure)

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
    style B fill:#ffe0b2,stroke:#f57f17,stroke-width:3px
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
```bash
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

## 14. End Success Block

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
```bash
task=99
next=never
```

**Explicit success with exit code:**
```bash
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

## 15. End Failure Block

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
```bash
task=98
return=1
```

**Stop with specific error code:**
```bash
task=97
return=14
```

**Explicit failure with never:**
```bash
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

## 16. Configuration Definition Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[CONFIGURATION PARAMETERS]

    style A fill:#f5f5f5,stroke:#757575,stroke-width:3px
```

</td>
<td width="60%">

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `timeout` | Integer | ❌ Optional | Override default timeout for this specific task (5-3600 seconds) |
| `exec` | String | ❌ Optional | Override default execution type for this specific task (pbrun, p7s, local, wwrs) |

### Examples
```bash
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
```bash
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

## 17. File-Defined Arguments Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[FILE-DEFINED ARGUMENTS]

    style A fill:#eeeeee,stroke:#616161,stroke-width:3px
```

</td>
<td width="60%">

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| CLI argument | String | ✅ Yes | Any valid TASKER CLI argument |

### Examples
```bash
# File-defined arguments (must be first!)
--auto-recovery
--skip-host-validation
--log-level=DEBUG
--timeout=60
```

### Entry Point
**MUST be at the very beginning of the task file** - before global variables and tasks

### Behavior
- Defines TASKER command-line arguments directly in task files
- Self-documenting workflows - requirements visible in file
- Parser stops at first line with `=` not starting with `-` or `--`
- Arguments appear BEFORE global variables and tasks
- Use exact CLI syntax: `--flag` or `--option=value`
- Boolean flags: additive (file OR cli)
- Value options: CLI overrides file defaults
- Security controls: CLI-only flags blocked (`--help`, `--version`)
- Security warnings: Sensitive flags warned (`--skip-security-validation`)

### Placement Rules
```bash
# ✅ CORRECT ORDER
# File-defined arguments (FIRST!)
--auto-recovery

# Global variables (SECOND)
ENVIRONMENT=production

# Tasks (LAST)
task=0
```

```bash
# ❌ WRONG - Arguments IGNORED
# Global variables first
ENVIRONMENT=production

# Arguments come too late - IGNORED!
--auto-recovery
```

### Supported Arguments
| Argument | Type | Notes |
|----------|------|-------|
| `--run` / `-r` | Boolean | Execute tasks |
| `--debug` / `-d` | Boolean | Debug logging |
| `--log-level=LEVEL` | Value | Set log level |
| `--timeout=N` | Value | Set timeout |
| `--start-from=N` | Value | Resume from task |
| `--auto-recovery` | Boolean | Enable recovery |
| `--skip-host-validation` | Boolean | Skip host checks |
| `--skip-task-validation` | Boolean | Skip task validation |
| `--skip-command-validation` | Boolean | Skip command checks |
| `--skip-security-validation` | Boolean | Skip security (⚠️ warns) |
| `--skip-validation` | Boolean | Skip all validation (⚠️ warns) |
| `--fire-and-forget` | Boolean | Continue on failure (⚠️ warns) |
| `--show-plan` | Boolean | Show execution plan |
| `--validate-only` | Boolean | Validate only |
| `--no-task-backup` | Boolean | Disable backups |

### CLI-Only Flags (Blocked)
| Argument | Reason |
|----------|--------|
| `--help` / `-h` | Interactive only |
| `--version` | Interactive only |

### Common Patterns
```bash
# Recovery workflow
--auto-recovery
--skip-host-validation

# Development testing
--log-level=DEBUG
--skip-host-validation
--no-task-backup

# Production deployment
--auto-recovery
--log-level=INFO
--show-plan
```

</td>
</tr>
</table>

## 18. Global Variable Definition Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[GLOBAL VARIABLES]

    style A fill:#e8e8e8,stroke:#616161,stroke-width:3px
```

</td>
<td width="60%">

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `VARIABLE_NAME` | String | ✅ Yes | Any uppercase variable name |
| `value` | String | ✅ Yes | Variable value or expression |

### Examples
```bash
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

## 19. Output Processing Block

<table>
<tr>
<td width="40%">

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#ffffff'}}}%%
flowchart TD
    A[Task Execution Completed] --> B[SPLIT OUTPUT]
    B --> C[REPLACE Original Output]
    C --> D[Continue Workflow]

    style A fill:#f0f0f0,stroke:#757575,stroke-width:3px
    style B fill:#f0f0f0,stroke:#757575,stroke-width:3px
    style C fill:#f0f0f0,stroke:#757575,stroke-width:3px
    style D fill:#f0f0f0,stroke:#757575,stroke-width:3px
```

</td>
<td width="60%">

### Parameters

| Parameter | Type | Required | Description | Format |
|-----------|------|----------|-------------|--------|
| `stdout_split` | String | ❌ Optional | Split stdout by delimiter and select element at index | `DELIMITER,INDEX` |
| `stderr_split` | String | ❌ Optional | Split stderr by delimiter and select element at index | `DELIMITER,INDEX` |

### Supported Delimiter Keywords
| Keyword | Splits On | Example | Input → Output |
|---------|-----------|---------|----------------|
| `space` | Any whitespace(s) | `stdout_split=space,1` | `"alpha beta gamma"` → `"beta"` |
| `tab` | Tab character(s) | `stdout_split=tab,2` | `"A\tB\tC\tD"` → `"C"` |
| `comma` | Comma | `stdout_split=comma,0` | `"red,green,blue"` → `"red"` |
| `semicolon` | Semicolon | `stdout_split=semicolon,1` | `"foo;bar;baz"` → `"bar"` |
| `semi` | Semicolon (alias) | `stdout_split=semi,2` | `"a;b;c;d"` → `"c"` |
| `colon` | Colon | `stdout_split=colon,2` | `"user:x:1000:1000"` → `"1000"` |
| `pipe` | Pipe character | `stdout_split=pipe,1` | `"cmd1|cmd2|cmd3"` → `"cmd2"` |
| `newline` | Line break(s) | `stdout_split=newline,0` | `"line1\nline2\nline3"` → `"line1"` |

**Important Notes:**
- Index is zero-based (0 = first element, 1 = second element, etc.)
- If index is out of bounds, the original output is returned unchanged
- The split operation occurs AFTER command execution but BEFORE placeholder storage

### Example
```bash
# Applied to existing task:
stdout_split=comma,1    # Split by comma, get 2nd element (0-indexed)
stderr_split=space,0    # Split by spaces, get 1st element
```

### Entry Point
Applied to any task that produces output

### Behavior
- Splits stdout/stderr by specified delimiter keyword and selects element by index (0-based)
- Format: `DELIMITER,INDEX` where DELIMITER is one of the supported keywords
- Modified output replaces original for subsequent processing and placeholder storage
- Split results are what gets stored in `@TASK_stdout@` and `@TASK_stderr@` placeholders
- Useful for parsing structured output like CSV data, log files, configuration files, etc.

</td>
</tr>
</table>
