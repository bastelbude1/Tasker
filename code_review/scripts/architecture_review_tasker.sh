#!/bin/bash

# TASKER Architecture Review using Claude Code /review
# Focus: Modular design, dependencies, coupling, interfaces

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORT_DIR="$SCRIPT_DIR/../reports"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🏗️ TASKER Architecture Review using Claude Code /review${NC}"
echo "Focus: Modular design, dependencies, coupling, interfaces"
echo "Timestamp: $(date)"
echo ""

# Change to project root for proper file context
cd "$PROJECT_ROOT"

# Create TASKER-specific architecture context file
CONTEXT_FILE="$REPORT_DIR/architecture_context.md"
cat > "$CONTEXT_FILE" << 'EOF'
# TASKER Architecture Review Context

## Architecture Overview
TASKER 2.0 uses a modular architecture with the Executor pattern for task processing.

## Key Architectural Patterns
1. **Executor Pattern**: Separate executors for sequential and parallel task processing
2. **Callback Architecture**: Logging and debugging via callback functions
3. **Validation Layer**: Separate task validation logic
4. **Condition Evaluation**: Centralized success/failure condition processing
5. **Modular Design**: Clear separation of concerns across modules

## Module Structure
```
tasker/
├── core/              # Core execution logic
│   ├── task_executor_main.py
│   ├── condition_evaluator.py
│   └── timeout_manager.py
├── executors/         # Task execution strategies
│   ├── base_executor.py
│   ├── sequential_executor.py
│   └── parallel_executor.py
├── validation/        # Input validation
│   └── task_validator.py
└── utils/            # Utility functions
    └── format_utils.py
```

## Architecture Principles
- **Single Responsibility**: Each module has one clear purpose
- **Open/Closed**: Extensible via new executors without modification
- **Dependency Inversion**: Main logic depends on abstractions (callbacks)
- **Interface Segregation**: Clean interfaces between modules
- **DRY**: Shared functionality in base classes and utilities

## Critical Interfaces
- **Executor Interface**: Base class with execute() method
- **Callback Interface**: log_callback, debug_callback parameters
- **Validation Interface**: Task parameter validation
- **Condition Interface**: Success/failure evaluation

## Design Goals
- Easy addition of new task execution strategies
- Clean separation between parsing, validation, and execution
- Consistent error handling and logging across modules
- Minimal coupling between components
- Clear data flow and state management
EOF

echo -e "${YELLOW}📋 Architecture Review Context:${NC}"
echo "- Modular design with Executor pattern"
echo "- Callback-based logging and debugging architecture"
echo "- Clear separation between validation, execution, and condition evaluation"
echo "- Interface consistency across modules"
echo "- Extensibility for new execution strategies"
echo ""

# Architecture-focused file list
ARCHITECTURE_FILES=(
    "tasker/core/task_executor_main.py"
    "tasker/executors/base_executor.py"
    "tasker/executors/sequential_executor.py"
    "tasker/executors/parallel_executor.py"
    "tasker/validation/task_validator.py"
    "tasker/core/condition_evaluator.py"
    "tasker/utils/format_utils.py"
    "tasker.py"
)

echo -e "${BLUE}🎯 Files under architecture review:${NC}"
for file in "${ARCHITECTURE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (not found)"
    fi
done
echo ""

# Generate architecture review report
REPORT_FILE="$REPORT_DIR/architecture_review_$(date +%Y%m%d_%H%M%S).md"

echo -e "${GREEN}🚀 Starting Claude Code architecture review...${NC}"
echo ""

cat > "$REPORT_FILE" << EOF
# TASKER Architecture Review Report
**Generated**: $(date)
**Review Type**: Architecture Analysis using Claude Code /review
**Focus Areas**: Modular design, coupling, interfaces, extensibility

## Files Reviewed
$(for file in "${ARCHITECTURE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "- ✅ $file"
    else
        echo "- ❌ $file (not found)"
    fi
done)

## Architecture Context Applied
- Modular architecture with Executor pattern
- Callback-based logging and debugging
- Clear separation of concerns (validation, execution, evaluation)
- Interface consistency and extensibility focus
- Minimal coupling between components

## Review Command Template
\`\`\`bash
# Manual execution in Claude Code:
/review

# With architecture focus on:
# - Module separation and responsibilities
# - Interface design and consistency
# - Coupling and cohesion analysis
# - Extensibility and maintainability
# - Design pattern implementation
\`\`\`

## Architecture Analysis Areas
### 1. Module Separation
- [ ] Clear boundaries between core, executors, validation, and utils
- [ ] Single responsibility principle adherence
- [ ] Appropriate abstraction levels

### 2. Interface Design
- [ ] Consistent callback interface (log_callback, debug_callback)
- [ ] Clean executor base class design
- [ ] Validation interface clarity
- [ ] Condition evaluation interface

### 3. Coupling Analysis
- [ ] Low coupling between modules
- [ ] Dependency direction correctness
- [ ] Circular dependency avoidance
- [ ] Appropriate use of dependency injection

### 4. Extensibility
- [ ] Easy addition of new executors
- [ ] Plugin-style architecture for new features
- [ ] Configuration-driven behavior
- [ ] Backward compatibility considerations

### 5. Design Patterns
- [ ] Executor pattern implementation quality
- [ ] Callback pattern effectiveness
- [ ] Factory pattern usage (if applicable)
- [ ] Strategy pattern for different execution types

## Instructions for Manual Review
1. Open Claude Code in the TASKER project directory
2. Use the /review command
3. Focus on architectural aspects of the files listed above
4. Apply the architecture context from: $CONTEXT_FILE
5. Evaluate design patterns, coupling, and extensibility

## Expected Findings Areas
- [ ] Module boundary violations
- [ ] Interface inconsistencies
- [ ] Tight coupling issues
- [ ] Extensibility limitations
- [ ] Design pattern misuse
- [ ] Abstraction level problems

---
*This report template was generated by the TASKER architecture review orchestration script.*
*Complete the review by executing /review in Claude Code with the above architectural context.*
EOF

echo -e "${GREEN}✅ Architecture review template generated: $REPORT_FILE${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Open Claude Code in this project directory"
echo "2. Execute: /review"
echo "3. Focus on architectural aspects of files: ${ARCHITECTURE_FILES[*]}"
echo "4. Apply architecture context from: $CONTEXT_FILE"
echo "5. Update the report with findings: $REPORT_FILE"
echo ""
echo -e "${BLUE}🎯 Architecture Focus Areas:${NC}"
echo "- Executor pattern implementation"
echo "- Module coupling and cohesion"
echo "- Interface design consistency"
echo "- Extensibility and maintainability"
echo "- Design pattern usage"