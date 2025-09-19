# TaskER FlowChart Block Inventory

This document provides a visual inventory of TaskER workflow blocks with their corresponding parameters.

## 1. Execution Block

<table>
<tr>
<td width="40%">

```mermaid
flowchart TD
    A[Task Execution Block]

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:2px
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
| `exec` | String | ❌ Optional | Execution type (pbrun, p7s, local, wwrs) |
| `timeout` | Integer | ❌ Optional | Command timeout (5-3600 seconds) |
| `sleep` | Integer | ❌ Optional | Sleep after execution (0-300 seconds) |

### Example
```
task=0
hostname=server01
command=ls
arguments=-la /var/log
exec=pbrun
timeout=30
sleep=5
```

</td>
</tr>
</table>

## 2. Success Check Block

<table>
<tr>
<td width="40%">

```mermaid
flowchart TD
    A[Task Execution Block] --> B{SUCCESS}

    style A fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style B fill:#ffecb3,stroke:#f57f17,stroke-width:2px
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
next=never
```

### Entry Point
Follows after Task Execution Block

</td>
</tr>
</table>

## 3. Condition Block

<table>
<tr>
<td width="40%">

```mermaid
flowchart TD
    A{CONDITION}

    style A fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier |
| `condition` | String | ✅ Yes | Pre-execution condition |
| `on_success` | String | ❌ Optional | Task ID for true condition |
| `on_failure` | String | ❌ Optional | Task ID for false condition |

### Example
```
task=2
condition=@DEPLOY_ENV@=production
on_success=10
on_failure=20
```

### Entry Point
Can be entry point or follow any block

</td>
</tr>
</table>

## 4. End Block

<table>
<tr>
<td width="40%">

```mermaid
flowchart TD
    A((END))

    style A fill:#ffcdd2,stroke:#c62828,stroke-width:2px
```

</td>
<td width="60%">

### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `next` | String | ✅ Yes | Must be "never" |
| `return` | Integer | ❌ Optional | Exit code (0-255) |

### Example
```
next=never
```
or
```
return=0
```

### Entry Point
Terminal block - workflow ends here

</td>
</tr>
</table>