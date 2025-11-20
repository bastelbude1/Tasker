#!/bin/bash
# Test script to verify error messages when config file is not found
# This complements config_error_messages_test.txt by testing the "config not found" scenario

set -e

echo "=== Testing 'config file not found' scenario ==="
echo "Temporarily moving config file to simulate not found condition"
echo ""

# Discover paths dynamically based on script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TASKER_DIR="${TASKER_HOME:-$SCRIPT_DIR}"
CONFIG_FILE="$TASKER_DIR/cfg/execution_types.yaml"
TASKER_SCRIPT="$TASKER_DIR/tasker.py"

# Verify tasker installation
if [[ ! -f "$TASKER_SCRIPT" ]]; then
    echo "ERROR: tasker.py not found at $TASKER_SCRIPT"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: Config file not found at $CONFIG_FILE (test requires config to exist first)"
    exit 1
fi

# Backup config file
BACKUP_PATH="/tmp/execution_types.yaml.backup.$$"
mv "$CONFIG_FILE" "$BACKUP_PATH"

# Create temp directory for test files
TEMP_DIR=$(mktemp -d)

# Ensure cleanup happens even if test fails
cleanup() {
    mv "$BACKUP_PATH" "$CONFIG_FILE"
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Create test task file that requires config
cat > "$TEMP_DIR/test_task.txt" <<'EOF'
# Test case requiring config file (pbrun not available without config)
task=0
hostname=localhost
exec=pbrun
command=echo
arguments=This should fail because config file is not found
EOF

echo "Config file moved to: $BACKUP_PATH"
echo "Tasker directory: $TASKER_DIR"
echo "Running tasker without config file..."
echo ""

# Run tasker, capturing exit status before piping to tee
# Expected: "Configuration file not found" with searched paths
# Note: Disable set -e temporarily to capture exit code without exiting
set +e
python "$TASKER_SCRIPT" --validate-only "$TEMP_DIR/test_task.txt" > "$TEMP_DIR/output.log" 2>&1
PYTHON_EXIT=$?
set -e

# Display output for visibility
cat "$TEMP_DIR/output.log"

echo ""
echo "=== Verifying error message content ==="

# Verify python exited with validation failure code (20)
if [[ $PYTHON_EXIT -ne 20 ]]; then
    echo "❌ Expected exit code 20 (validation failed), got $PYTHON_EXIT"
    exit 1
fi

# Verify error message shows "Configuration file not found"
if grep -q "ERROR: Configuration file not found" "$TEMP_DIR/output.log"; then
    echo "✅ Shows 'Configuration file not found' message"
else
    echo "❌ Missing 'Configuration file not found' message"
    exit 1
fi

# Verify error message shows searched locations
if grep -q "Searched locations:" "$TEMP_DIR/output.log"; then
    echo "✅ Shows 'Searched locations:' section"
else
    echo "❌ Missing 'Searched locations:' section"
    exit 1
fi

# Verify searched locations show full absolute paths (dynamic check)
if grep -q "$CONFIG_FILE" "$TEMP_DIR/output.log"; then
    echo "✅ Shows full absolute path in searched locations: $CONFIG_FILE"
else
    echo "❌ Missing full absolute path in searched locations (expected: $CONFIG_FILE)"
    exit 1
fi

# Verify error message shows required exec type
if grep -q "Required exec type" "$TEMP_DIR/output.log"; then
    echo "✅ Shows 'Required exec type' information"
else
    echo "❌ Missing 'Required exec type' information"
    exit 1
fi

echo ""
echo "=== Test passed: Config not found error messages are correct ==="
exit 0
