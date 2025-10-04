#!/bin/bash

# SECURITY TEST RUNNER
# Executes all security tests and validates they fail as expected
# CRITICAL: Security tests MUST fail - success indicates vulnerability

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
EXPECTED_FAILURES=0
UNEXPECTED_SUCCESSES=0
EXECUTION_ERRORS=0

echo -e "${BLUE}=== TASKER SECURITY TEST RUNNER ===${NC}"
echo -e "${BLUE}Testing negative security scenarios${NC}"
echo -e "${BLUE}Expected behavior: ALL tests should FAIL${NC}"
echo ""

# Resolve script directory and repository root for proper path handling
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Set PATH for mock commands and skip host validation
export PATH="$SCRIPT_DIR/../bin:$PATH"

# Function to test a single security test file
test_security_file() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .txt)

    echo -e "${YELLOW}[Testing: $test_name]${NC}"

    # Run the test with timeout and capture both stdout and stderr
    local output
    local exit_code

    output=$(timeout 30s "$REPO_ROOT/tasker.py" "$test_file" -r --skip-host-validation 2>&1)
    exit_code=$?

    # Analyze results
    if [ $exit_code -eq 124 ]; then
        echo -e "  ${RED}TIMEOUT${NC} - Test execution exceeded 30 seconds"
        ((EXECUTION_ERRORS++))
    elif [ $exit_code -eq 0 ]; then
        echo -e "  ${RED}UNEXPECTED SUCCESS${NC} - Security test should have failed!"
        echo -e "  ${RED}This indicates a potential security vulnerability${NC}"
        ((UNEXPECTED_SUCCESSES++))
    else
        echo -e "  ${GREEN}EXPECTED FAILURE${NC} - Exit code: $exit_code"
        ((EXPECTED_FAILURES++))
    fi

    # Check for specific security indicators in output
    if echo "$output" | grep -q "Traceback\|Error\|Exception\|Invalid\|Failed"; then
        echo -e "  ${GREEN}Security validation triggered${NC}"
    elif echo "$output" | grep -q "SUCCESS\|completed successfully"; then
        echo -e "  ${RED}WARNING: Test completed successfully - potential bypass${NC}"
    fi

    ((TOTAL_TESTS++))
    echo ""
}

# Test all security test files
echo -e "${BLUE}Scanning for security test files...${NC}"
security_files=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.txt" -type f | sort)

if [ -z "$security_files" ]; then
    echo -e "${RED}ERROR: No security test files found in security directory${NC}"
    exit 1
fi

echo -e "${BLUE}Found $(echo "$security_files" | wc -l) security test files${NC}"
echo ""

# Execute all security tests
for test_file in $security_files; do
    test_security_file "$test_file"
done

# Summary report
echo -e "${BLUE}=== SECURITY TEST SUMMARY ===${NC}"
echo -e "Total tests executed: $TOTAL_TESTS"
echo -e "${GREEN}Expected failures: $EXPECTED_FAILURES${NC}"
echo -e "${RED}Unexpected successes: $UNEXPECTED_SUCCESSES${NC}"
echo -e "${YELLOW}Execution errors: $EXECUTION_ERRORS${NC}"
echo ""

# Calculate security score
if [ $TOTAL_TESTS -gt 0 ]; then
    security_score=$((EXPECTED_FAILURES * 100 / TOTAL_TESTS))
    echo -e "${BLUE}Security Score: $security_score%${NC}"

    if [ $UNEXPECTED_SUCCESSES -eq 0 ] && [ $EXECUTION_ERRORS -eq 0 ]; then
        echo -e "${GREEN}✅ ALL SECURITY TESTS BEHAVED AS EXPECTED${NC}"
        echo -e "${GREEN}✅ No security vulnerabilities detected${NC}"
        exit 0
    else
        echo -e "${RED}❌ SECURITY ISSUES DETECTED${NC}"
        echo -e "${RED}❌ Review unexpected successes and execution errors${NC}"
        exit 1
    fi
else
    echo -e "${RED}ERROR: No tests were executed${NC}"
    exit 1
fi