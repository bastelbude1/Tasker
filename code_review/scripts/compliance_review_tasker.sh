#!/bin/bash

# TASKER Compliance Review using Claude Code /review
# Focus: Python 3.6.8 compatibility, coding standards, CLAUDE.md requirements

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

echo -e "${BLUE}📋 TASKER Compliance Review using Claude Code /review${NC}"
echo "Focus: Python 3.6.8 compatibility, coding standards, CLAUDE.md requirements"
echo "Timestamp: $(date)"
echo ""

# Change to project root for proper file context
cd "$PROJECT_ROOT"

# Create TASKER-specific compliance context file
CONTEXT_FILE="$REPORT_DIR/compliance_context.md"
cat > "$CONTEXT_FILE" << 'EOF'
# TASKER Compliance Review Context

## Python 3.6.8 Compatibility Requirements
TASKER must maintain strict Python 3.6.8 compatibility with NO external dependencies.

## FORBIDDEN Python 3.7+ Features
❌ **subprocess.run(capture_output=True, text=True)** - capture_output added in 3.7
❌ **subprocess.run(text=True)** - text parameter added in 3.7
❌ **f-string = specifier: f"{var=}"** - added in 3.8
❌ **dict.values() with walrus operator :=** - added in 3.8
❌ **Any external dependencies** - standard library only

## REQUIRED Python 3.6.8 Patterns
✅ **subprocess.Popen()** with universal_newlines=True for text mode
✅ **process.communicate(timeout=X)** for output capture with timeout
✅ **Manual process.returncode** checking instead of subprocess.run().returncode
✅ **with subprocess.Popen(...) as process:** for proper resource management

## CLAUDE.md Compliance Requirements
1. **Backup Policy**: All changes must have backup procedures
2. **1:1 Code Copy**: Minimize changes during refactoring
3. **Verification Testing**: 100% test success rate required
4. **ASCII-safe characters**: No Unicode characters in source code
5. **Error handling standards**: Consistent error patterns
6. **No inline comments**: Clean code in test cases
7. **Documentation synchronization**: Keep docs updated with code

## Coding Standards
- **Standard library only**: No pip dependencies allowed
- **Error handling**: Comprehensive exception handling patterns
- **Logging consistency**: Use callback-based logging throughout
- **Resource cleanup**: Proper file/process cleanup
- **Type safety**: Use appropriate type hints where possible (3.6.8 compatible)
- **Documentation**: Clear docstrings and comments
- **Testing**: Complete test coverage for all functionality

## Security Compliance
- **Input validation**: All user input must be validated
- **Command execution**: Safe subprocess patterns only
- **File operations**: Path validation and safe file handling
- **Error messages**: No sensitive information leakage

## Performance Compliance
- **Memory efficiency**: Handle large outputs appropriately
- **Resource limits**: Proper timeout and cancellation
- **Threading safety**: Safe concurrent operations
- **Algorithm efficiency**: Optimal data structures and algorithms
EOF

echo -e "${YELLOW}📋 Compliance Review Context:${NC}"
echo "- Python 3.6.8 strict compatibility (no 3.7+ features)"
echo "- CLAUDE.md guideline adherence"
echo "- Standard library only (no external dependencies)"
echo "- Consistent error handling and logging patterns"
echo "- ASCII-safe character usage"
echo ""

# Compliance-focused file list (all Python files)
COMPLIANCE_FILES=(
    "tasker.py"
    "tasker/core/task_executor_main.py"
    "tasker/core/condition_evaluator.py"
    "tasker/core/execution_context.py"
    "tasker/core/result_collector.py"
    "tasker/core/state_manager.py"
    "tasker/core/streaming_output_handler.py"
    "tasker/core/task_runner.py"
    "tasker/core/utilities.py"
    "tasker/core/workflow_controller.py"
    "tasker/executors/base_executor.py"
    "tasker/executors/conditional_executor.py"
    "tasker/executors/parallel_executor.py"
    "tasker/executors/sequential_executor.py"
    "tasker/validation/host_validator.py"
    "tasker/validation/input_sanitizer.py"
    "tasker/validation/task_validator.py"
    "tasker/utils/non_blocking_sleep.py"
)

echo -e "${BLUE}🎯 Files under compliance review:${NC}"
for file in "${COMPLIANCE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (not found)"
    fi
done
echo ""

# Generate compliance review report
REPORT_FILE="$REPORT_DIR/compliance_review_$(date +%Y%m%d_%H%M%S).md"

echo -e "${GREEN}🚀 Starting Claude Code compliance review...${NC}"
echo ""

cat > "$REPORT_FILE" << EOF
# TASKER Compliance Review Report
**Generated**: $(date)
**Review Type**: Compliance Analysis using Claude Code /review
**Focus Areas**: Python 3.6.8 compatibility, CLAUDE.md requirements, coding standards

## Files Reviewed
$(for file in "${COMPLIANCE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "- ✅ $file"
    else
        echo "- ❌ $file (not found)"
    fi
done)

## Compliance Context Applied
- Strict Python 3.6.8 compatibility enforcement
- CLAUDE.md guideline compliance verification
- Standard library only requirement
- Consistent error handling and logging patterns
- ASCII-safe character usage validation

## Review Command Template
\`\`\`bash
# Manual execution in Claude Code:
/review

# With compliance focus on:
# - Python 3.6.8 compatibility violations
# - CLAUDE.md requirement adherence
# - Coding standard consistency
# - Error handling patterns
# - Documentation quality
\`\`\`

## Compliance Analysis Areas
### 1. Python 3.6.8 Compatibility
- [ ] No subprocess.run() with capture_output or text parameters
- [ ] No f-string = specifier usage
- [ ] No walrus operator (:=) usage
- [ ] No Python 3.7+ syntax or features
- [ ] Proper subprocess.Popen() usage patterns
- [ ] Universal_newlines=True instead of text=True

### 2. CLAUDE.md Requirement Compliance
- [ ] Backup procedures documented and followed
- [ ] 1:1 code copy policy adherence during refactoring
- [ ] 100% test success rate maintenance
- [ ] ASCII-safe character usage (no Unicode)
- [ ] Consistent error handling patterns
- [ ] No inline comments in test cases
- [ ] Documentation synchronization with code changes

### 3. Dependency Compliance
- [ ] Standard library imports only
- [ ] No external pip dependencies
- [ ] No import statements for non-standard modules
- [ ] Proper use of available 3.6.8 standard library features

### 4. Error Handling Standards
- [ ] Consistent exception handling patterns
- [ ] Proper error message formatting
- [ ] No sensitive information in error messages
- [ ] Appropriate logging levels and callback usage
- [ ] Resource cleanup in error scenarios

### 5. Code Quality Standards
- [ ] Clear and consistent naming conventions
- [ ] Appropriate docstring documentation
- [ ] Type hints where beneficial (3.6.8 compatible)
- [ ] Consistent formatting and style
- [ ] Proper module organization

### 6. Security Compliance
- [ ] Input validation completeness
- [ ] Safe subprocess execution patterns
- [ ] Secure file handling procedures
- [ ] No hardcoded credentials or sensitive data
- [ ] Proper privilege handling

### 7. Testing Compliance
- [ ] Test case coverage for all functionality
- [ ] Test isolation and cleanup
- [ ] Mock usage appropriateness
- [ ] Test documentation clarity
- [ ] 100% success rate achievement

## Critical Compliance Violations to Check
- ❌ subprocess.run() usage (should be subprocess.Popen())
- ❌ Python 3.7+ syntax features
- ❌ External library imports
- ❌ Unicode characters in source code
- ❌ Inconsistent error handling patterns
- ❌ Missing input validation
- ❌ Inadequate resource cleanup

## Instructions for Manual Review
1. Open Claude Code in the TASKER project directory
2. Use the /review command
3. Focus on compliance aspects of the files listed above
4. Apply the compliance context from: $CONTEXT_FILE
5. Check each compliance area systematically

## Expected Findings Areas
- [ ] Python 3.6.8 compatibility violations
- [ ] CLAUDE.md guideline non-compliance
- [ ] Coding standard inconsistencies
- [ ] Error handling pattern deviations
- [ ] Documentation quality issues
- [ ] Security compliance gaps

---
*This report template was generated by the TASKER compliance review orchestration script.*
*Complete the review by executing /review in Claude Code with the above compliance context.*
EOF

echo -e "${GREEN}✅ Compliance review template generated: $REPORT_FILE${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Open Claude Code in this project directory"
echo "2. Execute: /review"
echo "3. Focus on compliance aspects of files: ${COMPLIANCE_FILES[*]}"
echo "4. Apply compliance context from: $CONTEXT_FILE"
echo "5. Update the report with findings: $REPORT_FILE"
echo ""
echo -e "${BLUE}🎯 Compliance Focus Areas:${NC}"
echo "- Python 3.6.8 compatibility enforcement"
echo "- CLAUDE.md guideline adherence"
echo "- Standard library only requirement"
echo "- Consistent error handling patterns"
echo "- ASCII-safe character validation"