#!/bin/bash

# TASKER Test Coverage Review using Claude Code /review
# Focus: Test completeness, edge cases, verification protocols

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

echo -e "${BLUE}🧪 TASKER Test Coverage Review using Claude Code /review${NC}"
echo "Focus: Test completeness, edge cases, verification protocols"
echo "Timestamp: $(date)"
echo ""

# Change to project root for proper file context
cd "$PROJECT_ROOT"

# Create TASKER-specific test coverage context file
CONTEXT_FILE="$REPORT_DIR/test_coverage_context.md"
cat > "$CONTEXT_FILE" << 'EOF'
# TASKER Test Coverage Review Context

## Test Suite Overview
TASKER has 465 test cases with a 100% success rate requirement (ZERO TOLERANCE policy).

## Test Architecture
1. **Test Cases**: 465 .txt files organized in 13 categories:
   - functional/ - Basic feature tests
   - integration/ - End-to-end workflow tests
   - edge_cases/ - Boundary and error condition tests
   - security/ - Security validation tests
   - streaming/ - Cross-task data flow tests
   - output_json/ - JSON output validation tests
   - performance/ - Performance and timing tests
   - recovery/ - Failure recovery tests
   - resume/ - Workflow resumption tests
   - readme_examples/ - Documentation example tests
   - templates/ - Test templates
2. **Verification Protocol**: test_cases/scripts/intelligent_test_runner.py with metadata-driven validation
3. **Mock Commands**: Test doubles in test_cases/bin/ (pbrun, p7s, wwrs_clir, cleanup verification)
4. **Test Metadata**: TEST_METADATA standard for comprehensive validation
5. **Cleanup Verification**: Temp file lifecycle testing with verify_cleanup_wrapper.sh

## Test Categories
### Functional Tests (functional/)
- Basic task execution (sequential, parallel)
- Conditional logic and flow control
- Retry mechanisms and failure handling
- Timeout management and cancellation
- Variable resolution and global variables
- Host validation and connectivity
- Delimiter functionality (newline, colon, semicolon)

### Integration Tests (integration/)
- Complete workflow scenarios
- Multi-task dependencies
- Complex parallel execution patterns
- Real-world automation workflows
- Global variable propagation
- Comprehensive retry scenarios

### Edge Case Tests (edge_cases/)
- Timeout scenarios and cancellation
- Failure recovery and retry logic
- Invalid input handling
- Resource exhaustion scenarios
- Error condition testing
- Parallel timeout flow control

### Security Tests (security/)
- Parameter validation testing
- Input sanitization verification
- Command injection prevention
- Buffer overflow protection
- Format string attack prevention

### Streaming Tests (streaming/)
- Cross-task variable substitution (@N_stdout@, @N_stderr@)
- Temp file management (@N_stdout_file@, @N_stderr_file@)
- Memory-efficient output handling (1MB threshold)
- Temp file cleanup verification
- Large output handling (100KB cmdline truncation)

### Output JSON Tests (output_json/)
- JSON output format validation
- Execution path tracking
- Task result verification
- Timeout exit code validation
- Conditional block output

### Performance Tests (performance/)
- Execution timing validation
- Sleep functionality testing
- Loop performance
- Resource usage monitoring

### Recovery Tests (recovery/)
- Failure recovery mechanisms
- State preservation
- Critical bug tracking

### Resume Tests (resume/)
- Workflow resumption
- State restoration
- Branch resumption

### README Examples (readme_examples/)
- Documentation examples validation
- Real-world use case testing
- Tutorial verification

## Test Quality Requirements
- **100% Success Rate**: All tests must pass (ZERO TOLERANCE)
- **Complete Coverage**: All features must have test cases
- **Edge Case Coverage**: Error scenarios and boundary conditions
- **State Isolation**: Tests must not interfere with each other
- **Mock Completeness**: All external dependencies mocked
- **Error Detection**: Robust exception and failure detection

## Test Infrastructure
- **Intelligent Test Runner**: test_cases/scripts/intelligent_test_runner.py
  - Metadata-driven validation (TEST_METADATA)
  - Execution path verification (expected_execution_path)
  - Variable resolution validation (expected_variables)
  - Exit code and success criteria validation
  - Performance benchmarking
  - Security test rejection validation
- **Mock Commands**: test_cases/bin/ directory
  - pbrun, p7s, wwrs_clir (execution wrappers)
  - verify_cleanup_wrapper.sh (temp file cleanup verification)
  - verify_temp_cleanup.py (Python cleanup verification)
  - Various test helpers (retry_controller.sh, recovery_helper.sh, etc.)
- **Metadata Standard**: TEST_METADATA in each test file
  - description, test_type, expected_exit_code, expected_success
  - expected_execution_path, expected_variables, security_category
- **Cleanup Verification**: Comprehensive temp file lifecycle testing
- **Test Utilities**:
  - add_missing_metadata.py (auto-add metadata)
  - auto_fix_metadata.py (metadata correction)
  - fix_security_metadata.py (security test metadata)
  - unit_test_non_blocking_sleep.py (unit tests)

## Critical Test Areas
1. **Cross-Task Data Flow (streaming/)**:
   - Variable substitution (@N_stdout@, @N_stderr@, @N_stdout_file@, @N_stderr_file@)
   - 1MB memory threshold for streaming
   - 100KB command-line truncation for ARG_MAX safety
   - Temp file lifecycle and cleanup verification
2. **Metadata-Driven Testing**:
   - TEST_METADATA standard compliance
   - Execution path validation
   - Variable resolution verification
3. **Delimiter Functionality**: New delimiter keywords (newline, colon, semicolon)
4. **Parallel Execution**: ThreadPoolExecutor with timeout management
5. **Retry Logic**: Complex retry scenarios with various conditions
6. **Condition Evaluation**: Success/failure condition processing
7. **Variable Resolution**: Global and task variable handling
8. **Error Handling**: Exception propagation and recovery
9. **JSON Output Validation (output_json/)**: Format and execution tracking
10. **Security Testing**: Command injection, buffer overflow, format string attacks
EOF

echo -e "${YELLOW}📋 Test Coverage Review Context:${NC}"
echo "- 465 test cases with 100% success rate requirement (ZERO TOLERANCE)"
echo "- 13 test categories (functional, integration, edge_cases, security, streaming, etc.)"
echo "- Intelligent test runner with metadata-driven validation"
echo "- Mock command infrastructure with cleanup verification"
echo "- Cross-task data flow testing (streaming output handler)"
echo "- JSON output validation and execution path tracking"
echo ""

# Test-focused file list - Representative samples from each category
TEST_FILES=(
    # Test Infrastructure & Scripts
    "test_cases/scripts/intelligent_test_runner.py"
    "test_cases/scripts/add_missing_metadata.py"
    "test_cases/scripts/verify_show_plan_routing.py"
    "test_cases/scripts/unit_test_non_blocking_sleep.py"

    # Mock Commands
    "test_cases/bin/pbrun"
    "test_cases/bin/p7s"
    "test_cases/bin/wwrs_clir"
    "test_cases/bin/verify_cleanup_wrapper.sh"
    "test_cases/bin/verify_temp_cleanup.py"

    # Functional Tests
    "test_cases/functional/hello.txt"
    "test_cases/functional/retry_test_1_basic.txt"
    "test_cases/functional/delimiter_test.txt"

    # Integration Tests
    "test_cases/integration/comprehensive_globals_test.txt"
    "test_cases/integration/comprehensive_retry_test_case.txt"

    # Edge Case Tests
    "test_cases/edge_cases/comprehensive_timeout_summary_test.txt"
    "test_cases/edge_cases/comprehensive_retry_validation_test.txt"

    # Security Tests
    "test_cases/security/buffer_overflow_format_string_test.txt"

    # Streaming/Cross-task Data Flow Tests
    "test_cases/streaming/test_cross_task_comprehensive.txt"
    "test_cases/streaming/test_cleanup_verification.txt"
    "test_cases/streaming/README_CLEANUP_VERIFICATION.md"

    # JSON Output Tests
    "test_cases/output_json/test_output_conditional_block.txt"
    "test_cases/output_json/test_output_timeout.txt"

    # Performance Tests
    "test_cases/performance/sleep_decimal_test.txt"
    "test_cases/performance/test_loop_with_sleep.txt"

    # Resume/Recovery Tests
    "test_cases/resume/test_resume_before_branch.txt"
    "test_cases/recovery/CRITICAL_BUGS_FOUND.md"

    # README Examples
    "test_cases/readme_examples/readme_01_service_health_check.txt"
    "test_cases/readme_examples/readme_02_hello_world.txt"
)

echo -e "${BLUE}🎯 Test files under coverage review:${NC}"
for file in "${TEST_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (not found)"
    fi
done

# Count total test cases
TEST_COUNT=$(find test_cases/ -name "*.txt" -not -name "*validation*" | wc -l)
echo ""
echo -e "${BLUE}📊 Test Statistics:${NC}"
echo "  Total test cases: $TEST_COUNT"
echo "  Mock commands: $(ls test_scripts/ 2>/dev/null | wc -l)"
echo "  Verification scripts: $(find test_cases/ -name "*.sh" | wc -l)"
echo ""

# Generate test coverage review report
REPORT_FILE="$REPORT_DIR/test_coverage_review_$(date +%Y%m%d_%H%M%S).md"

echo -e "${GREEN}🚀 Starting Claude Code test coverage review...${NC}"
echo ""

cat > "$REPORT_FILE" << EOF
# TASKER Test Coverage Review Report
**Generated**: $(date)
**Review Type**: Test Coverage Analysis using Claude Code /review
**Focus Areas**: Test completeness, edge cases, verification protocols

## Test Files Reviewed
$(for file in "${TEST_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "- ✅ $file"
    else
        echo "- ❌ $file (not found)"
    fi
done)

## Test Statistics
- **Total Test Cases**: $TEST_COUNT functional tests
- **Mock Commands**: $(ls test_scripts/ 2>/dev/null | wc -l) test doubles
- **Verification Scripts**: $(find test_cases/ -name "*.sh" | wc -l) automation scripts
- **Success Rate Requirement**: 100% (ZERO TOLERANCE)

## Test Coverage Context Applied
- 465 test cases with comprehensive scenario coverage across 13 categories
- 100% success rate requirement enforcement (ZERO TOLERANCE)
- Intelligent test runner with metadata-driven validation
- Mock command infrastructure with cleanup verification
- Cross-task data flow testing (streaming output handler)
- JSON output validation and execution path tracking
- Temp file lifecycle and cleanup verification

## Review Command Template
\`\`\`bash
# Manual execution in Claude Code:
/review

# With test coverage focus on:
# - Test case completeness and coverage gaps
# - Edge case and error scenario testing
# - Test quality and maintainability
# - Mock infrastructure adequacy
# - Verification protocol robustness
\`\`\`

## Test Coverage Analysis Areas
### 1. Functional Coverage
- [ ] All core features have corresponding test cases
- [ ] Sequential task execution testing
- [ ] Parallel task execution with various configurations
- [ ] Conditional logic and flow control scenarios
- [ ] Variable resolution and global variable usage
- [ ] Retry mechanisms and failure recovery

### 2. Edge Case Coverage
- [ ] Timeout scenarios and cancellation testing
- [ ] Resource exhaustion and memory limits
- [ ] Invalid input and malformed task files
- [ ] Network failures and connectivity issues
- [ ] Boundary conditions (max tasks, large outputs)
- [ ] Race conditions in parallel execution

### 3. Error Scenario Testing
- [ ] Exception handling and error propagation
- [ ] Failed command execution scenarios
- [ ] Validation failures and error messages
- [ ] Recovery from partial failures
- [ ] Graceful degradation testing

### 4. Integration Testing
- [ ] End-to-end workflow scenarios
- [ ] Multi-task dependency chains
- [ ] Complex parallel execution patterns
- [ ] Real-world automation use cases
- [ ] Cross-module interaction testing

### 5. Test Infrastructure Quality
- [ ] Mock command completeness and accuracy
- [ ] State isolation between tests
- [ ] Test execution reliability (no flaky tests)
- [ ] Exception detection robustness
- [ ] Timeout management effectiveness

### 6. New Feature Testing
- [ ] Delimiter enhancement testing (newline, colon, semicolon)
- [ ] Recent architecture changes coverage
- [ ] Regression prevention for fixed bugs
- [ ] Backward compatibility verification

### 7. Test Maintainability
- [ ] Clear test case documentation
- [ ] Easy addition of new test cases
- [ ] Debugging support for test failures
- [ ] Test execution performance
- [ ] Test result reporting clarity

## Critical Coverage Gaps to Identify
- [ ] Missing test cases for core functionality
- [ ] Insufficient edge case coverage
- [ ] Inadequate error scenario testing
- [ ] Missing integration test scenarios
- [ ] Incomplete mock coverage
- [ ] Insufficient regression testing

## Test Quality Assessment
- [ ] Test case clarity and documentation
- [ ] Appropriate test data and scenarios
- [ ] Mock realism and completeness
- [ ] Test execution reliability
- [ ] Result verification accuracy
- [ ] Maintenance burden evaluation

## Instructions for Manual Review
1. Open Claude Code in the TASKER project directory
2. Use the /review command
3. Focus on test coverage aspects of the files listed above
4. Apply the test coverage context from: $CONTEXT_FILE
5. Evaluate completeness, quality, and maintainability

## Expected Findings Areas
- [ ] Test coverage gaps for specific features
- [ ] Missing edge case scenarios
- [ ] Inadequate error condition testing
- [ ] Test infrastructure improvements needed
- [ ] Test maintainability issues
- [ ] Verification protocol enhancements

---
*This report template was generated by the TASKER test coverage review orchestration script.*
*Complete the review by executing /review in Claude Code with the above test coverage context.*
EOF

echo -e "${GREEN}✅ Test coverage review template generated: $REPORT_FILE${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Open Claude Code in this project directory"
echo "2. Execute: /review"
echo "3. Focus on test coverage aspects of files: ${TEST_FILES[*]}"
echo "4. Apply test coverage context from: $CONTEXT_FILE"
echo "5. Update the report with findings: $REPORT_FILE"
echo ""
echo -e "${BLUE}🎯 Test Coverage Focus Areas:${NC}"
echo "- Functional test completeness ($TEST_COUNT test cases across 13 categories)"
echo "- Cross-task data flow (streaming output handler, temp file management)"
echo "- Metadata-driven validation (intelligent test runner)"
echo "- JSON output validation and execution path tracking"
echo "- Edge case and error scenario coverage"
echo "- Security testing (command injection, buffer overflow, format string)"
echo "- Mock infrastructure adequacy and cleanup verification"
echo "- Test quality and maintainability"
echo "- 100% success rate verification protocol (ZERO TOLERANCE)"