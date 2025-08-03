#!/bin/bash

# RETRY VALIDATION TEST SCRIPT
# Tests the enhanced task_validator.py with comprehensive retry validation

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
VALIDATOR_SCRIPT="./task_validator.py"
TEST_FILE="comprehensive_retry_validation_test.txt"
LOG_FILE="retry_validation_test.log"

echo -e "${BLUE}=== RETRY VALIDATION TEST ===${NC}"
echo "Testing enhanced task_validator.py with comprehensive retry scenarios"
echo ""

# Check if validator script exists
if [ ! -f "$VALIDATOR_SCRIPT" ]; then
    echo -e "${RED}ERROR: $VALIDATOR_SCRIPT not found${NC}"
    exit 1
fi

# Check if test file exists
if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}ERROR: $TEST_FILE not found${NC}"
    echo "Please create the test file first"
    exit 1
fi

# Run the validation and capture output
echo -e "${BLUE}Running validation test...${NC}"
echo "Command: python3 $VALIDATOR_SCRIPT $TEST_FILE"
echo ""

# Run validation (will exit with error code if validation fails, but we want to continue)
if python3 "$VALIDATOR_SCRIPT" "$TEST_FILE" > "$LOG_FILE" 2>&1; then
    echo -e "${YELLOW}Validation completed (exit code 0 - no errors found)${NC}"
else
    echo -e "${YELLOW}Validation completed (exit code 1 - errors found as expected)${NC}"
fi

echo ""
echo -e "${BLUE}=== VALIDATION RESULTS ===${NC}"
cat "$LOG_FILE"
echo ""

# Analyze results
echo -e "${BLUE}=== ANALYSIS ===${NC}"

# Count errors and warnings
ERROR_COUNT=$(grep -c "ERROR:" "$LOG_FILE" 2>/dev/null || echo "0")
WARNING_COUNT=$(grep -c "WARNING:" "$LOG_FILE" 2>/dev/null || echo "0")

echo -e "${RED}Errors found: $ERROR_COUNT${NC}"
echo -e "${YELLOW}Warnings found: $WARNING_COUNT${NC}"

echo ""
echo -e "${BLUE}=== EXPECTED vs ACTUAL ===${NC}"

# Expected results based on test case design
EXPECTED_ERRORS=7
EXPECTED_WARNINGS=14  # Approximate, may vary based on implementation

echo "Expected errors: $EXPECTED_ERRORS"
echo "Actual errors: $ERROR_COUNT"

echo "Expected warnings: ~$EXPECTED_WARNINGS" 
echo "Actual warnings: $WARNING_COUNT"

echo ""

# Check specific error patterns
echo -e "${BLUE}=== SPECIFIC ERROR CHECKS ===${NC}"

# Check for invalid retry_failed values
if grep -q "invalid retry_failed value" "$LOG_FILE"; then
    echo -e "${GREEN}✓ Invalid retry_failed values detected${NC}"
else
    echo -e "${RED}✗ Invalid retry_failed values NOT detected${NC}"
fi

# Check for negative values
if grep -q "negative.*retry" "$LOG_FILE"; then
    echo -e "${GREEN}✓ Negative retry values detected${NC}"
else
    echo -e "${RED}✗ Negative retry values NOT detected${NC}"
fi

# Check for retry fields in non-parallel tasks
if grep -q "retry.*not a parallel task" "$LOG_FILE"; then
    echo -e "${GREEN}✓ Retry fields in non-parallel tasks detected${NC}"
else
    echo -e "${RED}✗ Retry fields in non-parallel tasks NOT detected${NC}"
fi

# Check for high values warnings
if grep -q "high retry" "$LOG_FILE"; then
    echo -e "${GREEN}✓ High retry values warnings detected${NC}"
else
    echo -e "${RED}✗ High retry values warnings NOT detected${NC}"
fi

# Check for missing retry configuration warnings
if grep -q "retry_failed=true but no" "$LOG_FILE"; then
    echo -e "${GREEN}✓ Incomplete retry configuration warnings detected${NC}"
else
    echo -e "${RED}✗ Incomplete retry configuration warnings NOT detected${NC}"
fi

echo ""
echo -e "${BLUE}=== SUMMARY ===${NC}"

if [ "$ERROR_COUNT" -gt 0 ] && [ "$WARNING_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Test completed successfully - Both errors and warnings were detected as expected${NC}"
    echo -e "${GREEN}✓ The retry validation logic appears to be working correctly${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected results - Please review the validation output${NC}"
fi

echo ""
echo "Full validation log saved to: $LOG_FILE"
echo ""
echo -e "${BLUE}=== TEST SECTIONS COVERED ===${NC}"
echo "1. Valid retry configurations (should pass)"
echo "2. Retry fields in non-parallel tasks (warnings expected)"
echo "3. Invalid retry values (errors expected)"
echo "4. Inconsistent retry configurations (warnings expected)"
echo "5. Extreme values (warnings expected)"
echo "6. Edge cases (specific warnings expected)"
echo "7. Mixed scenarios (various errors/warnings expected)"

echo ""
echo -e "${BLUE}To run individual tests:${NC}"
echo "  python3 $VALIDATOR_SCRIPT $TEST_FILE"
echo "  python3 $VALIDATOR_SCRIPT -d $TEST_FILE  # Debug mode"

# Optional: Show specific error/warning lines
echo ""
echo -e "${BLUE}=== DETAILED ERROR/WARNING BREAKDOWN ===${NC}"
echo -e "${RED}ERRORS:${NC}"
grep "ERROR:" "$LOG_FILE" | head -10 || echo "No errors found"

echo ""
echo -e "${YELLOW}WARNINGS:${NC}"
grep "WARNING:" "$LOG_FILE" | head -15 || echo "No warnings found"
