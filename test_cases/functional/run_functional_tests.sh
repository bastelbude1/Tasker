#!/bin/bash
# Functional Test Runner - Tests core TASKER functionality
# Runs all tests in functional/ directory

echo "=== FUNCTIONAL TESTS ==="
echo "Testing core TASKER functionality..."
echo ""

# Get script directory for absolute path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$TEST_ROOT")"

# Change to script directory to ensure consistent behavior
cd "$SCRIPT_DIR"

# Set PATH for supporting scripts using script-relative path
export PATH="$TEST_ROOT/bin:$PATH"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a single test
run_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file")

    echo -n "Testing $test_name... "
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if timeout 60 "$REPO_ROOT/tasker.py" "$test_file" -r --skip-host-validation >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        local exit_code=$?
        echo -e "${RED}❌ FAIL (exit code: $exit_code)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Run all functional tests
echo -e "${BLUE}--- Running functional tests ---${NC}"
for test_file in *.txt; do
    if [ -f "$test_file" ]; then
        run_test "$test_file"
    fi
done

echo ""
echo "=== FUNCTIONAL TEST SUMMARY ==="
echo "Total tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL FUNCTIONAL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME FUNCTIONAL TESTS FAILED${NC}"
    exit 1
fi