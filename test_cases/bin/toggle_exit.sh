#!/bin/bash

# Define the file to store the toggle value
TOGGLE_FILE="$HOME/.toggle_value"

# Check if the file exists, if not, create it with initial value 0
if [ ! -f "$TOGGLE_FILE" ]; then
    echo 0 > "$TOGGLE_FILE"
fi

# Read the current value from the file
current_value=$(cat "$TOGGLE_FILE")

# Toggle the value between 0 and 1
if [ "$current_value" -eq 0 ]; then
    new_value=1
else
    new_value=0
fi

# Save the new value back to the file
echo "$new_value" > "$TOGGLE_FILE"

# Print the new value
echo "$new_value" >&2

exit "$new_value"
