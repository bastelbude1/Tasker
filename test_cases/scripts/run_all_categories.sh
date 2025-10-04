#!/bin/bash
# Master Test Runner - Runs all test categories
# Comprehensive testing of entire TASKER system

echo "=== TASKER COMPREHENSIVE TEST SUITE ==="
echo "Running all test categories..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set PATH for supporting scripts
export PATH="../bin:$PATH"

# Track overall results
CATEGORY_RESULTS=()
TOTAL_CATEGORIES=0
PASSED_CATEGORIES=0

# Function to run a category and track results
run_category() {
    local display_name="$1"
    local directory="$2"
    local script="$3"
    local description="$4"

    echo -e "${BLUE}=== $display_name ===${NC}"
    echo "$description"
    echo ""

    TOTAL_CATEGORIES=$((TOTAL_CATEGORIES + 1))

    if cd "../$directory" && ./"$script"; then
        echo -e "${GREEN}✅ $display_name PASSED${NC}"
        CATEGORY_RESULTS+=("$display_name: ✅ PASSED")
        PASSED_CATEGORIES=$((PASSED_CATEGORIES + 1))
        cd - >/dev/null
    else
        echo -e "${RED}❌ $display_name FAILED${NC}"
        CATEGORY_RESULTS+=("$display_name: ❌ FAILED")
        cd - >/dev/null
    fi
    echo ""
}

# Run all test categories
echo -e "${YELLOW}Starting comprehensive test suite...${NC}"
echo ""

# 1. Functional Tests
run_category "FUNCTIONAL TESTS" "functional" "run_functional_tests.sh" "Testing core TASKER functionality"

# 2. Edge Cases Tests
run_category "EDGE CASES TESTS" "edge_cases" "run_edge_cases_tests.sh" "Testing boundary conditions and edge cases"

# 3. Integration Tests
run_category "INTEGRATION TESTS" "integration" "run_integration_tests.sh" "Testing system integration and complex workflows"

# 4. Security Tests (negative testing)
echo -e "${BLUE}=== SECURITY TESTS ===${NC}"
echo "Testing security - all tests should FAIL (negative testing)"
echo ""

TOTAL_CATEGORIES=$((TOTAL_CATEGORIES + 1))

if cd "../security" && ./run_security_tests.sh; then
    echo -e "${GREEN}✅ SECURITY TESTS PASSED (correctly rejected malicious inputs)${NC}"
    CATEGORY_RESULTS+=("SECURITY TESTS: ✅ PASSED")
    PASSED_CATEGORIES=$((PASSED_CATEGORIES + 1))
    cd - >/dev/null
else
    echo -e "${RED}❌ SECURITY TESTS FAILED (vulnerability detected)${NC}"
    CATEGORY_RESULTS+=("SECURITY TESTS: ❌ FAILED")
    cd - >/dev/null
fi
echo ""

# Final Summary
echo "=== COMPREHENSIVE TEST SUITE RESULTS ==="
echo ""
for result in "${CATEGORY_RESULTS[@]}"; do
    echo "$result"
done

echo ""
echo "Categories: $PASSED_CATEGORIES/$TOTAL_CATEGORIES passed"

if [ $PASSED_CATEGORIES -eq $TOTAL_CATEGORIES ]; then
    echo -e "${GREEN}🎉 ALL TEST CATEGORIES PASSED${NC}"
    echo -e "${GREEN}✅ TASKER SYSTEM VALIDATION COMPLETE${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TEST CATEGORIES FAILED${NC}"
    echo -e "${RED}🚨 TASKER SYSTEM VALIDATION FAILED${NC}"
    exit 1
fi