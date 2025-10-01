#!/bin/bash

# TASKER Performance Review using Claude Code /review
# Focus: Parallel execution, resource usage, optimization opportunities

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

echo -e "${BLUE}⚡ TASKER Performance Review using Claude Code /review${NC}"
echo "Focus: Parallel execution, resource usage, optimization opportunities"
echo "Timestamp: $(date)"
echo ""

# Change to project root for proper file context
cd "$PROJECT_ROOT"

# Create TASKER-specific performance context file
CONTEXT_FILE="$REPORT_DIR/performance_context.md"
cat > "$CONTEXT_FILE" << 'EOF'
# TASKER Performance Review Context

## Performance-Critical Areas
TASKER processes multiple tasks with parallel execution, timeout management, and remote command execution.

## Key Performance Aspects
1. **Parallel Execution**: ThreadPoolExecutor for concurrent task processing
2. **Timeout Management**: Master timeout with task cancellation
3. **Resource Management**: Memory usage with large task workflows
4. **I/O Efficiency**: Remote command execution and output processing
5. **Threading Safety**: Concurrent access to shared state

## Performance Bottlenecks to Analyze
1. **Thread Pool Management**: Optimal thread count, task scheduling
2. **Memory Usage**: Large stdout/stderr handling, variable storage
3. **Timeout Precision**: Cancellation efficiency, resource cleanup
4. **Network I/O**: SSH connection pooling, command execution overhead
5. **Condition Evaluation**: Regex performance in output processing

## Current Implementation Details
- **Python 3.6.8**: Limited to older concurrent.futures implementation
- **ThreadPoolExecutor**: Used for parallel task execution
- **subprocess.Popen**: All command execution (no async/await available)
- **No external libraries**: Standard library performance patterns only
- **Memory constraints**: Must handle large output efficiently

## Performance Requirements
- Support 100+ parallel tasks efficiently
- Handle multi-MB stdout/stderr without memory issues
- Quick timeout response (sub-second cancellation)
- Minimal resource leakage between task executions
- Scalable to enterprise workload sizes

## Critical Performance Files
- parallel_executor.py: Core parallel execution logic
- timeout_manager.py: Timeout and cancellation handling
- condition_evaluator.py: Output processing and regex evaluation
- format_utils.py: Output formatting efficiency
EOF

echo -e "${YELLOW}📋 Performance Review Context:${NC}"
echo "- Parallel execution efficiency with ThreadPoolExecutor"
echo "- Timeout management and task cancellation performance"
echo "- Memory usage optimization for large outputs"
echo "- I/O efficiency in remote command execution"
echo "- Threading safety and resource management"
echo ""

# Performance-focused file list
PERFORMANCE_FILES=(
    "tasker/executors/parallel_executor.py"
    "tasker/core/timeout_manager.py"
    "tasker/executors/sequential_executor.py"
    "tasker/executors/base_executor.py"
    "tasker/core/condition_evaluator.py"
    "tasker/utils/format_utils.py"
    "tasker/core/task_executor_main.py"
)

echo -e "${BLUE}🎯 Files under performance review:${NC}"
for file in "${PERFORMANCE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (not found)"
    fi
done
echo ""

# Generate performance review report
REPORT_FILE="$REPORT_DIR/performance_review_$(date +%Y%m%d_%H%M%S).md"

echo -e "${GREEN}🚀 Starting Claude Code performance review...${NC}"
echo ""

cat > "$REPORT_FILE" << EOF
# TASKER Performance Review Report
**Generated**: $(date)
**Review Type**: Performance Analysis using Claude Code /review
**Focus Areas**: Parallel execution, resource usage, optimization opportunities

## Files Reviewed
$(for file in "${PERFORMANCE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "- ✅ $file"
    else
        echo "- ❌ $file (not found)"
    fi
done)

## Performance Context Applied
- Python 3.6.8 parallel execution with ThreadPoolExecutor
- Timeout management and task cancellation
- Memory efficiency for large stdout/stderr handling
- I/O optimization for remote command execution
- Threading safety and resource cleanup

## Review Command Template
\`\`\`bash
# Manual execution in Claude Code:
/review

# With performance focus on:
# - Parallel execution efficiency
# - Memory usage optimization
# - Threading and concurrency safety
# - I/O and network efficiency
# - Resource management and cleanup
\`\`\`

## Performance Analysis Areas
### 1. Parallel Execution Efficiency
- [ ] ThreadPoolExecutor configuration and sizing
- [ ] Task scheduling and load balancing
- [ ] Future object management and cleanup
- [ ] Exception handling in concurrent context
- [ ] Thread pool shutdown procedures

### 2. Memory Management
- [ ] Large stdout/stderr handling strategies
- [ ] Variable storage and cleanup
- [ ] Memory leaks in long-running workflows
- [ ] Garbage collection considerations
- [ ] Buffer size optimization

### 3. Timeout and Cancellation
- [ ] Master timeout implementation efficiency
- [ ] Task cancellation speed and reliability
- [ ] Resource cleanup after cancellation
- [ ] Timeout precision and overhead
- [ ] Deadlock prevention in cancellation

### 4. I/O and Network Performance
- [ ] subprocess.Popen efficiency patterns
- [ ] Output streaming vs buffering strategies
- [ ] Network connection reuse opportunities
- [ ] Command execution batching potential
- [ ] Error handling performance impact

### 5. Algorithm Efficiency
- [ ] Condition evaluation regex performance
- [ ] Variable replacement algorithm efficiency
- [ ] Loop optimization in task processing
- [ ] Data structure choices (lists vs dicts)
- [ ] String processing optimization

### 6. Resource Management
- [ ] File handle management and cleanup
- [ ] Process lifecycle management
- [ ] Temporary file cleanup
- [ ] Memory usage profiling needs
- [ ] CPU usage optimization

## Python 3.6.8 Performance Constraints
- [ ] Limited concurrent.futures features
- [ ] No async/await syntax available
- [ ] Standard library threading only
- [ ] No modern performance libraries
- [ ] Subprocess limitations vs newer APIs

## Instructions for Manual Review
1. Open Claude Code in the TASKER project directory
2. Use the /review command
3. Focus on performance aspects of the files listed above
4. Apply the performance context from: $CONTEXT_FILE
5. Look for optimization opportunities and bottlenecks

## Expected Findings Areas
- [ ] Thread pool size optimization
- [ ] Memory usage improvements
- [ ] I/O efficiency enhancements
- [ ] Algorithm optimization opportunities
- [ ] Resource cleanup improvements
- [ ] Concurrency safety issues

---
*This report template was generated by the TASKER performance review orchestration script.*
*Complete the review by executing /review in Claude Code with the above performance context.*
EOF

echo -e "${GREEN}✅ Performance review template generated: $REPORT_FILE${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Open Claude Code in this project directory"
echo "2. Execute: /review"
echo "3. Focus on performance aspects of files: ${PERFORMANCE_FILES[*]}"
echo "4. Apply performance context from: $CONTEXT_FILE"
echo "5. Update the report with findings: $REPORT_FILE"
echo ""
echo -e "${BLUE}🎯 Performance Focus Areas:${NC}"
echo "- Parallel execution with ThreadPoolExecutor"
echo "- Memory usage optimization"
echo "- Timeout and cancellation efficiency"
echo "- I/O and network performance"
echo "- Algorithm and data structure optimization"