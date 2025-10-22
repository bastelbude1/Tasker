#!/bin/bash
# Script to update shebang from python to python3 for Python 3.6.8 environments
# This is needed on servers where 'python' doesn't point to Python 3.6.8

echo "==================================="
echo "TASKER Shebang Update Script"
echo "==================================="
echo ""
echo "This script updates shebang lines from 'python' to 'python3'"
echo "for servers where Python 3.6.8 is accessed via 'python3' command."
echo ""

# Files to update
FILES=(
    "tasker.py"
    "view_tasker_project_summary.py"
    "test_cases/scripts/intelligent_test_runner.py"
)

# Counter for changes
UPDATED=0
SKIPPED=0

# Process each file
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        # Check current shebang
        CURRENT_SHEBANG=$(head -n1 "$file")

        if [[ "$CURRENT_SHEBANG" == "#!/usr/bin/env python" ]]; then
            echo "Updating: $file"
            echo "  Current: $CURRENT_SHEBANG"

            # Create backup
            cp "$file" "$file.shebang_backup"

            # Update shebang
            sed -i '1s|#!/usr/bin/env python|#!/usr/bin/env python3|' "$file"

            NEW_SHEBANG=$(head -n1 "$file")
            echo "  Updated: $NEW_SHEBANG"
            echo ""

            ((UPDATED++))

        elif [[ "$CURRENT_SHEBANG" == "#!/usr/bin/env python3" ]]; then
            echo "Skipping: $file (already uses python3)"
            echo "  Current: $CURRENT_SHEBANG"
            echo ""
            ((SKIPPED++))

        elif [[ "$CURRENT_SHEBANG" == "#!/usr/bin/python" ]]; then
            echo "Updating: $file"
            echo "  Current: $CURRENT_SHEBANG"

            # Create backup
            cp "$file" "$file.shebang_backup"

            # Update shebang
            sed -i '1s|#!/usr/bin/python|#!/usr/bin/python3|' "$file"

            NEW_SHEBANG=$(head -n1 "$file")
            echo "  Updated: $NEW_SHEBANG"
            echo ""

            ((UPDATED++))

        elif [[ "$CURRENT_SHEBANG" == "#!/usr/bin/python3" ]]; then
            echo "Skipping: $file (already uses python3)"
            echo "  Current: $CURRENT_SHEBANG"
            echo ""
            ((SKIPPED++))

        else
            echo "Warning: $file has non-standard shebang"
            echo "  Current: $CURRENT_SHEBANG"
            echo "  Manual review recommended"
            echo ""
        fi
    else
        echo "Error: $file not found!"
        echo ""
    fi
done

echo "==================================="
echo "Summary:"
echo "  Files updated: $UPDATED"
echo "  Files skipped: $SKIPPED"
if [ $UPDATED -gt 0 ]; then
    echo ""
    echo "Backups created with .shebang_backup extension"
    echo "To restore: mv file.shebang_backup file"
fi
echo "==================================="

# Rename mock test commands to avoid conflicts with production commands
echo ""
echo "Renaming mock test commands to avoid conflicts..."
MOCK_RENAMED=0

# Define mock commands to rename
MOCK_COMMANDS=(
    "test_cases/bin/pbrun:test_cases/bin/pbrun_test"
    "test_cases/bin/p7s:test_cases/bin/p7s_test"
    "test_cases/bin/wwrs_clir:test_cases/bin/wwrs_clir_test"
)

for mapping in "${MOCK_COMMANDS[@]}"; do
    OLD_NAME="${mapping%:*}"
    NEW_NAME="${mapping#*:}"

    if [ -f "$OLD_NAME" ]; then
        if [ ! -f "$NEW_NAME" ]; then
            mv "$OLD_NAME" "$NEW_NAME"
            echo "  Renamed: $OLD_NAME -> $NEW_NAME"
            ((MOCK_RENAMED++))
        else
            echo "  Skipping: $NEW_NAME already exists"
        fi
    elif [ -f "$NEW_NAME" ]; then
        echo "  Already renamed: $NEW_NAME exists"
    fi
done

if [ $MOCK_RENAMED -gt 0 ]; then
    echo ""
    echo "Note: Test cases will need PATH adjustment to use renamed commands"
    echo "Add test_cases/bin to PATH for testing with mock commands"
fi

echo "==================================="

# Create bin directory and symlink for tasker
echo ""
echo "Setting up bin directory for tasker..."
if [ ! -d "bin" ]; then
    mkdir -p bin
    echo "  Created: bin directory"
fi

if [ ! -L "bin/tasker" ]; then
    ln -s ../tasker.py bin/tasker
    echo "  Created: bin/tasker -> ../tasker.py symlink"
    chmod +x bin/tasker
elif [ -L "bin/tasker" ]; then
    echo "  Already exists: bin/tasker symlink"
fi

echo "==================================="

# Test Python version
echo ""
echo "Python version check:"
echo -n "  python3: "
python3 --version 2>&1 || echo "Not found"
echo -n "  python: "
python --version 2>&1 || echo "Not found"
echo ""

# Verify Python 3.6.8 or compatible
PYTHON3_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "")
if [[ "$PYTHON3_VERSION" == "3.6."* ]]; then
    echo "✓ Python 3.6.x detected - shebang update appropriate"
else
    echo "⚠ Warning: Python version is $PYTHON3_VERSION"
    echo "  This script is intended for Python 3.6.8 environments"
fi