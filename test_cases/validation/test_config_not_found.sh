#!/bin/bash
# Test script to verify error messages when config file is not found
# This complements config_error_messages_test.txt by testing the "config not found" scenario

set -e

echo "=== Testing 'config file not found' scenario ==="
echo "Temporarily moving config file to simulate not found condition"
echo ""

# Backup config file
BACKUP_PATH="/tmp/execution_types.yaml.backup.$$"
mv /home/baste/tasker/cfg/execution_types.yaml "$BACKUP_PATH"

# Ensure we restore config file even if test fails
trap "mv '$BACKUP_PATH' /home/baste/tasker/cfg/execution_types.yaml" EXIT

# Create test task file that requires config
TEMP_DIR=$(mktemp -d)
cat > "$TEMP_DIR/test_task.txt" <<'EOF'
# Test case requiring config file (pbrun not available without config)
task=0
hostname=localhost
exec=pbrun
command=echo
arguments=This should fail because config file is not found
EOF

echo "Config file moved to: $BACKUP_PATH"
echo "Running tasker without config file..."
echo ""

# Run tasker, which will NOT find config file
# Expected: "Configuration file not found" with searched paths
python /home/baste/tasker/tasker.py --validate-only "$TEMP_DIR/test_task.txt" 2>&1 | tee "$TEMP_DIR/output.log"

echo ""
echo "=== Verifying error message content ==="

# Verify error message shows "Configuration file not found"
if grep -q "ERROR: Configuration file not found" "$TEMP_DIR/output.log"; then
    echo "✅ Shows 'Configuration file not found' message"
else
    echo "❌ Missing 'Configuration file not found' message"
    cat "$TEMP_DIR/output.log"
    exit 1
fi

# Verify error message shows searched locations
if grep -q "Searched locations:" "$TEMP_DIR/output.log"; then
    echo "✅ Shows 'Searched locations:' section"
else
    echo "❌ Missing 'Searched locations:' section"
    exit 1
fi

# Verify searched locations show full absolute paths
if grep -q "/home/baste/tasker/cfg/execution_types.yaml" "$TEMP_DIR/output.log"; then
    echo "✅ Shows full absolute path in searched locations"
else
    echo "❌ Missing full absolute path in searched locations"
    exit 1
fi

# Verify error message shows required exec type
if grep -q "Required exec type" "$TEMP_DIR/output.log"; then
    echo "✅ Shows 'Required exec type' information"
else
    echo "❌ Missing 'Required exec type' information"
    exit 1
fi

# Cleanup temp files
rm -rf "$TEMP_DIR"

echo ""
echo "=== Test passed: Config not found error messages are correct ==="
exit 0
