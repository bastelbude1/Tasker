# TaskER FlowChart Documentation

This document provides visual representations of TaskER workflow blocks using Mermaid diagrams.

## Simple Execution Block

The basic building block of any TaskER workflow is the execution block, which contains the core parameters needed to execute a command on a target system.

```mermaid
flowchart TD
    A[Task Execution Block] --> B{Task Parameters}

    B --> C["task: Integer ID (0, 1, 2, ...)"]
    B --> D["hostname: Target server or @HOSTNAME@"]
    B --> E["command: Command to execute"]
    B --> F["arguments: Command arguments (optional)"]

    C --> G[Execute Command]
    D --> G
    E --> G
    F --> G

    G --> H[Command Result]

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#f1f8e9
    style G fill:#ffebee
    style H fill:#e8f5e8
```

### Parameter Details

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | Integer | ✅ Yes | Unique task identifier (0, 1, 2, ...) |
| `hostname` | String | ✅ Yes | Target server name or @HOSTNAME@ placeholder |
| `command` | String | ✅ Yes | Command to execute on the target system |
| `arguments` | String | ❌ Optional | Additional arguments for the command |

### Example Usage

```
task=0
hostname=server01
command=ls
arguments=-la /var/log
```

This creates a simple execution block that will run `ls -la /var/log` on server01.

## Post-Action Success Check Block

After command execution, you can define success criteria and control flow based on the result.

```mermaid
flowchart TD
    A[Command Executed] --> B{Success Check}

    B --> C["success: Custom success criteria"]
    B --> D["next: Flow control condition"]

    C --> E{Evaluate Success}
    D --> E

    E -->|Success = True| F[Continue to Next Task]
    E -->|Success = False| G{Check Next Parameter}

    G -->|next = never| H[END - Stop Workflow]
    G -->|return = X| I[END - Exit with Code X]
    G -->|Other next value| J[Jump to Specified Task]

    F --> K[Next Task Block]
    J --> K

    style A fill:#e8f5e8
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#ffecb3
    style F fill:#c8e6c9
    style G fill:#ffecb3
    style H fill:#ffcdd2
    style I fill:#ffcdd2
    style J fill:#bbdefb
    style K fill:#e1f5fe
```

## Traditional Condition Block

Pre-execution condition checking with branching logic based on evaluation results.

```mermaid
flowchart TD
    A[Task Entry] --> B{Condition Block}

    B --> C["condition: Pre-execution condition"]
    B --> D["on_success: Task ID for true condition"]
    B --> E["on_failure: Task ID for false condition"]

    C --> F{Evaluate Condition}
    D --> F
    E --> F

    F -->|Condition = True| G[Execute on_success Path]
    F -->|Condition = False| H[Execute on_failure Path]

    G --> I{on_success Target}
    H --> J{on_failure Target}

    I -->|Task ID| K[Jump to Success Task]
    I -->|never/return| L[END - Success Path]

    J -->|Task ID| M[Jump to Failure Task]
    J -->|never/return| N[END - Failure Path]

    K --> O[Continue Workflow]
    M --> O

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#ffecb3
    style G fill:#c8e6c9
    style H fill:#ffab91
    style I fill:#ffecb3
    style J fill:#ffecb3
    style K fill:#bbdefb
    style L fill:#ffcdd2
    style M fill:#bbdefb
    style N fill:#ffcdd2
    style O fill:#e1f5fe
```

### Parameter Details for Conditional Blocks

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `success` | String | ❌ Optional | Custom success criteria for post-execution check |
| `next` | String | ❌ Optional | Flow control (never, return=X, or task ID) |
| `condition` | String | ❌ Optional | Pre-execution condition to evaluate |
| `on_success` | String | ❌ Optional | Task ID to execute when condition is true |
| `on_failure` | String | ❌ Optional | Task ID to execute when condition is false |

### Example Usage

**Post-Action Success Check:**
```
task=1
hostname=server01
command=service
arguments=nginx status
success=@1_exit_code@=0&@1_stdout@~running
next=never
```

**Traditional Condition Block:**
```
task=2
condition=@DEPLOY_ENV@=production
on_success=10
on_failure=20
```