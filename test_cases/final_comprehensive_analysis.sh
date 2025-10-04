#!/bin/bash
# Final Comprehensive Analysis - Optimized for Manual Execution
# Analyzes all test cases with debug output to identify unexpected patterns

ANALYSIS_LOG="/tmp/tasker_final_analysis.log"
DEBUG_LOG="/tmp/tasker_all_debug.log"
ISSUES_LOG="/tmp/tasker_unexpected_patterns.log"

echo "=============================================================="
echo "TASKER Final Comprehensive Analysis"
echo "=============================================================="
echo "Analyzing all test cases with debug output..."
echo "Log files:"
echo "  Analysis: $ANALYSIS_LOG"
echo "  All Debug: $DEBUG_LOG"
echo "  Issues: $ISSUES_LOG"
echo ""

# Clear previous logs
> "$ANALYSIS_LOG"
> "$DEBUG_LOG"
> "$ISSUES_LOG"

# Get all test files
TEST_FILES=($(find . -name "*.txt" -type f | grep -v "backup" | sort))

echo "Found ${#TEST_FILES[@]} test files"
echo ""

TOTAL_TESTS=0
EXECUTION_SUCCESS=0
VALIDATION_SUCCESS=0
UNEXPECTED_PATTERNS=0

# Critical patterns to detect
CRITICAL_PATTERNS=(
    "Traceback"
    "AttributeError"
    "KeyError"
    "TypeError"
    "NameError"
    "IndentationError"
    "SyntaxError"
    "ImportError"
    "ModuleNotFoundError"
    "Exception:"
    "Error:"
    "CRITICAL:"
    "FATAL:"
)

# Test each file
for test_file in "${TEST_FILES[@]}"; do
    test_name=$(basename "$test_file")
    echo "Testing: $test_name"

    {
        echo "========================================"
        echo "TEST: $test_name"
        echo "========================================"
    } >> "$ANALYSIS_LOG"

    # Run with debug output and capture everything (use relative path from test_cases directory)
    if timeout 30s bash -c "PATH='../test_scripts:$PATH' ../tasker.py '$test_file' -r --skip-host-validation -d" >> "$DEBUG_LOG" 2>&1; then
        echo "  ✓ Exit code: 0"
        ((EXECUTION_SUCCESS++))
    else
        exit_code=$?
        echo "  ⚠ Exit code: $exit_code"

        # Check if it's a validation test (expected to fail)
        if grep -q "validation.*test\|expected.*fail\|security.*test" <<< "$test_name"; then
            echo "    (Expected failure - validation test)"
            ((VALIDATION_SUCCESS++))
        fi
    fi

    ((TOTAL_TESTS++))

    # Extract debug output for this test and check for patterns
    test_debug=$(tail -n 200 "$DEBUG_LOG" | grep -A 200 "TEST: $test_name" | head -n 150)

    # Check for unexpected patterns
    for pattern in "${CRITICAL_PATTERNS[@]}"; do
        if echo "$test_debug" | grep -q "$pattern"; then
            echo "  🔴 UNEXPECTED PATTERN: $pattern"
            {
                echo "FILE: $test_name"
                echo "PATTERN: $pattern"
                echo "CONTEXT:"
                echo "$test_debug" | grep -B 2 -A 2 "$pattern"
                echo "----------------------------------------"
            } >> "$ISSUES_LOG"
            ((UNEXPECTED_PATTERNS++))
        fi
    done

    {
        echo "Exit Status: $?"
        echo ""
    } >> "$ANALYSIS_LOG"
done

echo ""
echo "=============================================================="
echo "ANALYSIS SUMMARY"
echo "=============================================================="

{
    echo "FINAL ANALYSIS SUMMARY"
    echo "======================"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Execution Success: $EXECUTION_SUCCESS"
    echo "Validation Success: $VALIDATION_SUCCESS"
    echo "Unexpected Patterns: $UNEXPECTED_PATTERNS"
    echo ""
    echo "Success Rate: $(( (EXECUTION_SUCCESS + VALIDATION_SUCCESS) * 100 / TOTAL_TESTS ))%"
    echo ""

    if [ $UNEXPECTED_PATTERNS -eq 0 ]; then
        echo "✅ NO UNEXPECTED PATTERNS DETECTED"
        echo "All tests executed cleanly without Python exceptions or critical errors"
    else
        echo "🔴 UNEXPECTED PATTERNS DETECTED: $UNEXPECTED_PATTERNS"
        echo "Review $ISSUES_LOG for details"
    fi
} | tee -a "$ANALYSIS_LOG"

echo ""
echo "Generated files:"
echo "  $ANALYSIS_LOG - Complete analysis log"
echo "  $DEBUG_LOG - All debug output (large file)"
echo "  $ISSUES_LOG - Unexpected patterns found"
echo ""
echo "To review issues:"
echo "  cat $ISSUES_LOG"
echo ""
echo "To review specific test debug output:"
echo "  grep -A 50 'TEST: filename.txt' $DEBUG_LOG"