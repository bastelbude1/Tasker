#!/bin/bash

# TASKER Comprehensive Code Review Orchestrator
# Coordinates all 5 specialized review scripts using Claude Code's native capabilities

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
REPORTS_DIR="$SCRIPT_DIR/reports"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Create reports directory if it doesn't exist
mkdir -p "$REPORTS_DIR"

echo -e "${PURPLE}🔍 TASKER 2.0 Comprehensive Code Review${NC}"
echo -e "${BLUE}Using Claude Code's native /review and /security-review capabilities${NC}"
echo "Timestamp: $(date)"
echo "Project: $PROJECT_ROOT"
echo ""

# Verify all review scripts exist
REVIEW_SCRIPTS=(
    "security_review_tasker.sh"
    "architecture_review_tasker.sh"
    "performance_review_tasker.sh"
    "compliance_review_tasker.sh"
    "test_coverage_review_tasker.sh"
)

echo -e "${YELLOW}📋 Verifying review scripts...${NC}"
for script in "${REVIEW_SCRIPTS[@]}"; do
    if [[ -x "$SCRIPTS_DIR/$script" ]]; then
        echo "  ✅ $script"
    else
        echo "  ❌ $script (missing or not executable)"
        exit 1
    fi
done
echo ""

# Change to project root for proper file context
cd "$PROJECT_ROOT"

# Generate unique timestamp for this review session
REVIEW_SESSION=$(date +%Y%m%d_%H%M%S)
SESSION_DIR="$REPORTS_DIR/session_$REVIEW_SESSION"
mkdir -p "$SESSION_DIR"

echo -e "${BLUE}📁 Review session: $REVIEW_SESSION${NC}"
echo "Reports will be saved to: $SESSION_DIR"
echo ""

# Execute each specialized review script
echo -e "${PURPLE}🚀 Starting comprehensive review process...${NC}"
echo ""

# Step 1: Security Review
echo -e "${RED}Step 1/5: Security Analysis (/security-review)${NC}"
echo "Focus: Input validation, command injection, subprocess safety"
if "$SCRIPTS_DIR/security_review_tasker.sh" 2>&1 | tee "$SESSION_DIR/01_security_review.log"; then
    echo -e "${GREEN}✅ Security review completed${NC}"
else
    echo -e "${RED}❌ Security review failed${NC}"
fi
echo ""

# Step 2: Architecture Review
echo -e "${BLUE}Step 2/5: Architecture Analysis (/review)${NC}"
echo "Focus: Modular design, coupling, interfaces, extensibility"
if "$SCRIPTS_DIR/architecture_review_tasker.sh" 2>&1 | tee "$SESSION_DIR/02_architecture_review.log"; then
    echo -e "${GREEN}✅ Architecture review completed${NC}"
else
    echo -e "${RED}❌ Architecture review failed${NC}"
fi
echo ""

# Step 3: Performance Review
echo -e "${YELLOW}Step 3/5: Performance Analysis (/review)${NC}"
echo "Focus: Parallel execution, resource usage, optimization"
if "$SCRIPTS_DIR/performance_review_tasker.sh" 2>&1 | tee "$SESSION_DIR/03_performance_review.log"; then
    echo -e "${GREEN}✅ Performance review completed${NC}"
else
    echo -e "${RED}❌ Performance review failed${NC}"
fi
echo ""

# Step 4: Compliance Review
echo -e "${PURPLE}Step 4/5: Compliance Analysis (/review)${NC}"
echo "Focus: Python 3.6.8 compatibility, CLAUDE.md requirements"
if "$SCRIPTS_DIR/compliance_review_tasker.sh" 2>&1 | tee "$SESSION_DIR/04_compliance_review.log"; then
    echo -e "${GREEN}✅ Compliance review completed${NC}"
else
    echo -e "${RED}❌ Compliance review failed${NC}"
fi
echo ""

# Step 5: Test Coverage Review
echo -e "${CYAN}Step 5/5: Test Coverage Analysis (/review)${NC}"
echo "Focus: Test completeness, edge cases, verification protocols"
if "$SCRIPTS_DIR/test_coverage_review_tasker.sh" 2>&1 | tee "$SESSION_DIR/05_test_coverage_review.log"; then
    echo -e "${GREEN}✅ Test coverage review completed${NC}"
else
    echo -e "${RED}❌ Test coverage review failed${NC}"
fi
echo ""

# Generate unified review summary
echo -e "${PURPLE}📋 Generating comprehensive review summary...${NC}"

SUMMARY_FILE="$SESSION_DIR/COMPREHENSIVE_REVIEW_SUMMARY.md"
cat > "$SUMMARY_FILE" << EOF
# TASKER 2.0 Comprehensive Code Review Summary

**Review Session**: $REVIEW_SESSION
**Generated**: $(date)
**Project Root**: $PROJECT_ROOT
**Review Method**: Claude Code native /review and /security-review capabilities

## Review Overview
This comprehensive review leverages Claude Code's built-in review capabilities with TASKER-specific context and focus areas.

## Review Components Executed

### 🔒 1. Security Review (/security-review)
**Focus**: Input validation, command injection, subprocess safety
**Log**: [01_security_review.log](./01_security_review.log)
**Context**: Python 3.6.8 task automation with subprocess execution
**Key Areas**: Command injection prevention, input validation, file handling security

### 🏗️ 2. Architecture Review (/review)
**Focus**: Modular design, coupling, interfaces, extensibility
**Log**: [02_architecture_review.log](./02_architecture_review.log)
**Context**: Executor pattern with callback architecture
**Key Areas**: Module separation, interface consistency, design patterns

### ⚡ 3. Performance Review (/review)
**Focus**: Parallel execution, resource usage, optimization
**Log**: [03_performance_review.log](./03_performance_review.log)
**Context**: ThreadPoolExecutor with timeout management
**Key Areas**: Concurrency efficiency, memory usage, I/O optimization

### 📋 4. Compliance Review (/review)
**Focus**: Python 3.6.8 compatibility, CLAUDE.md requirements
**Log**: [04_compliance_review.log](./04_compliance_review.log)
**Context**: Strict 3.6.8 compatibility, standard library only
**Key Areas**: Feature compatibility, coding standards, guideline adherence

### 🧪 5. Test Coverage Review (/review)
**Focus**: Test completeness, edge cases, verification protocols
**Log**: [05_test_coverage_review.log](./05_test_coverage_review.log)
**Context**: Comprehensive test suite with 100% success rate requirement
**Key Areas**: Functional coverage, edge cases, mock infrastructure

## Files Analyzed
- **Core CLI**: tasker.py (main command line interface)
- **Modular Core**: tasker/core/ (task_executor_main.py, condition_evaluator.py, utilities.py, etc.)
- **Executors**: tasker/executors/ (parallel_executor.py, conditional_executor.py, sequential_executor.py)
- **Validation**: tasker/validation/ (task_validator.py, host_validator.py)
- **Utilities**: tasker/utils/ (non_blocking_sleep.py)
- **Test Suite**: test_cases/ (organized by category: functional/, integration/, edge_cases/, security/)
- **Test Infrastructure**: test_cases/scripts/ (focused_verification.sh, run_all_categories.sh), test_cases/bin/ (mock commands)
- **Documentation**: CLAUDE.md, README.md, TaskER_FlowChart.md

## Next Steps
1. **Complete Manual Reviews**: Execute /security-review and /review commands in Claude Code
2. **Apply Context**: Use the specialized context files generated for each review area
3. **Document Findings**: Update the individual review report templates with findings
4. **Address Issues**: Prioritize and implement recommended improvements
5. **Verify Fixes**: Re-run reviews after implementing changes

## Review Session Files
\`\`\`
session_$REVIEW_SESSION/
├── 01_security_review.log
├── 02_architecture_review.log
├── 03_performance_review.log
├── 04_compliance_review.log
├── 05_test_coverage_review.log
└── COMPREHENSIVE_REVIEW_SUMMARY.md (this file)
\`\`\`

## Benefits of This Approach
- ✅ **Leverages proven capabilities**: Uses Claude Code's battle-tested review logic
- ✅ **TASKER-specific context**: Provides relevant focus areas and constraints
- ✅ **Comprehensive coverage**: 5 specialized review areas
- ✅ **Automated orchestration**: One command triggers complete review
- ✅ **Structured reporting**: Clear documentation and tracking

---
*Generated by TASKER Comprehensive Code Review Orchestrator*
EOF

echo -e "${GREEN}✅ Comprehensive review summary generated: $SUMMARY_FILE${NC}"
echo ""

# Display final summary
echo -e "${PURPLE}🎉 COMPREHENSIVE REVIEW COMPLETED${NC}"
echo ""
echo -e "${BLUE}📊 Review Statistics:${NC}"
echo "  Review session: $REVIEW_SESSION"
echo "  Review scripts executed: ${#REVIEW_SCRIPTS[@]}"
echo "  Log files generated: $(ls "$SESSION_DIR"/*.log 2>/dev/null | wc -l)"
echo "  Reports directory: $SESSION_DIR"
echo ""
echo -e "${YELLOW}📋 Next Actions Required:${NC}"
echo "1. Execute the manual review commands in Claude Code:"
echo "   - /security-review (for security analysis)"
echo "   - /review (for architecture, performance, compliance, test coverage)"
echo ""
echo "2. Apply the specialized context from each review script"
echo ""
echo "3. Update the report templates with your findings"
echo ""
echo "4. Review the comprehensive summary: $SUMMARY_FILE"
echo ""
echo -e "${GREEN}🔗 Quick Access:${NC}"
echo "cd $SESSION_DIR && ls -la"
echo ""
echo -e "${BLUE}🎯 This orchestration system leverages Claude Code's native capabilities${NC}"
echo -e "${BLUE}   with TASKER-specific intelligence for comprehensive code review.${NC}"