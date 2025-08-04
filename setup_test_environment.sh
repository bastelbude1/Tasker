#!/bin/bash

echo "=== TASKER Test Environment Setup ==="
echo "This script ensures all required commands and paths are available for TASKER testing"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    local status="$1"
    local message="$2"
    case "$status" in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPTS_DIR="$SCRIPT_DIR/test_scripts"

print_status "INFO" "TASKER directory: $SCRIPT_DIR"
print_status "INFO" "Test scripts directory: $TEST_SCRIPTS_DIR"

echo ""
echo "=== 1. Checking Test Scripts Directory ==="

if [ -d "$TEST_SCRIPTS_DIR" ]; then
    print_status "OK" "Test scripts directory exists"
else
    print_status "ERROR" "Test scripts directory not found: $TEST_SCRIPTS_DIR"
    exit 1
fi

# Check if test scripts exist and are executable
declare -a test_commands=("pbrun" "p7s" "wwrs_clir")
for cmd in "${test_commands[@]}"; do
    script_path="$TEST_SCRIPTS_DIR/$cmd"
    if [ -f "$script_path" ]; then
        if [ -x "$script_path" ]; then
            print_status "OK" "Test script $cmd is executable"
        else
            print_status "WARN" "Making $cmd executable"
            chmod +x "$script_path"
            if [ -x "$script_path" ]; then
                print_status "OK" "Successfully made $cmd executable"
            else
                print_status "ERROR" "Failed to make $cmd executable"
            fi
        fi
    else
        print_status "ERROR" "Test script not found: $script_path"
    fi
done

echo ""
echo "=== 2. Setting up PATH for Test Commands ==="

# Add test_scripts directory to PATH if not already there
if [[ ":$PATH:" != *":$TEST_SCRIPTS_DIR:"* ]]; then
    export PATH="$TEST_SCRIPTS_DIR:$PATH"
    print_status "OK" "Added test_scripts directory to PATH"
else
    print_status "OK" "Test scripts directory already in PATH"
fi

# Verify commands are now available
for cmd in "${test_commands[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        cmd_path=$(which "$cmd")
        print_status "OK" "$cmd found at: $cmd_path"
    else
        print_status "ERROR" "$cmd not found in PATH"
    fi
done

echo ""
echo "=== 3. Testing Command Functionality ==="

# Test each command with a simple test case
test_hostnames=("validation-pass-server" "validation-fail-server")

for cmd in "${test_commands[@]}"; do
    print_status "INFO" "Testing $cmd command..."
    
    case "$cmd" in
        "pbrun")
            # Test pbrun with success case
            if timeout 5 pbrun -n -h validation-pass-server pbtest >/dev/null 2>&1; then
                print_status "OK" "pbrun test command works"
            else
                print_status "ERROR" "pbrun test command failed"
            fi
            ;;
        "p7s")
            # Test p7s with success case
            if timeout 5 p7s validation-pass-server pbtest >/dev/null 2>&1; then
                print_status "OK" "p7s test command works"
            else
                print_status "ERROR" "p7s test command failed"
            fi
            ;;
        "wwrs_clir")
            # Test wwrs_clir with success case
            if timeout 5 wwrs_clir validation-pass-server wwrs_test >/dev/null 2>&1; then
                print_status "OK" "wwrs_clir test command works"
            else
                print_status "ERROR" "wwrs_clir test command failed"
            fi
            ;;
    esac
done

echo ""
echo "=== 4. Checking /etc/hosts Entries ==="

hosts_file="/etc/hosts"
hosts_entries_file="$hosts_file"

if [ -f "$hosts_entries_file" ]; then
    print_status "OK" "Found /etc/hosts entries file: $hosts_entries_file"
    
    # Check if test hostnames are resolvable
    declare -a check_hosts=("pbrun-success-host" "p7s-success-host" "wwrs-success-host" "validation-pass-server")
    
    missing_hosts=()
    for hostname in "${check_hosts[@]}"; do
        if getent hosts "$hostname" >/dev/null 2>&1; then
            print_status "OK" "$hostname resolves correctly"
        else
            print_status "WARN" "$hostname not found in /etc/hosts"
            missing_hosts+=("$hostname")
        fi
    done
    
    if [ ${#missing_hosts[@]} -gt 0 ]; then
        echo ""
        print_status "WARN" "Some test hostnames are not in /etc/hosts"
        print_status "INFO" "To add missing entries, run as root:"
        print_status "INFO" "  sudo cat $hosts_entries_file >> /etc/hosts"
        echo ""
        print_status "INFO" "Or manually add these entries to /etc/hosts:"
        for hostname in "${missing_hosts[@]}"; do
            echo "  127.0.0.1    $hostname"
        done
    else
        print_status "OK" "All test hostnames resolve correctly"
    fi
else
    print_status "ERROR" "/etc/hosts entries file not found: $hosts_entries_file"
fi

echo ""
echo "=== 5. Environment Summary ==="

# Show current PATH
print_status "INFO" "Current PATH includes test_scripts directory"

# Show available commands
print_status "INFO" "Available test commands:"
for cmd in "${test_commands[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "  - $cmd: $(which "$cmd")"
    else
        echo "  - $cmd: NOT FOUND"
    fi
done

echo ""
echo "=== 6. Usage Instructions ==="
echo ""
echo "To use this environment in your current shell session:"
echo "  source $0"
echo ""
echo "To permanently add test commands to your PATH, add this to ~/.bashrc:"
echo "  export PATH=\"$TEST_SCRIPTS_DIR:\$PATH\""
echo ""
echo "To test host validation:"
echo "  ./tasker.py test_cases/host_validation_test.txt"
echo ""
echo "To run validation tests without host connectivity:"
echo "  ./tasker.py test_cases/host_validation_test.txt --skip-host-validation"
echo ""

# If script is sourced, update the caller's PATH
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    print_status "OK" "Environment setup complete - PATH updated for current session"
else
    print_status "INFO" "To apply PATH changes to current session, run: source $0"
fi

echo ""
print_status "OK" "TASKER test environment setup complete!"
