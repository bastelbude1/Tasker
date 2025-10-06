#!/bin/bash
set -euo pipefail

# increment_counter.sh [init_value]
#
# If init_value is provided, initialize the stored counter to that value (without incrementing).
# If not provided, increment the stored counter value from previous runs.
# This allows for reproducible test results and counter initialization when needed.

# Define the counter file
counter_file="$HOME/.my_counter"

# Check if an init value argument was provided
if [ $# -gt 0 ]; then
    # Initialize mode: set counter to the provided value
    init_value="$1"

    # Validate that it's a number
    if ! [[ "$init_value" =~ ^[0-9]+$ ]]; then
        echo "Error: Init value must be a positive integer" >&2
        exit 1
    fi

    # Set counter to init value (no incrementing in init mode)
    counter="$init_value"

    # Store the initialized value
    echo "$counter" > "$counter_file"
else
    # Normal mode: increment from stored value
    # Ensure the counter file exists with a starting value of 0
    [ -f "$counter_file" ] || echo 0 > "$counter_file"

    # Read the current value of the counter
    counter=$(<"$counter_file")

    # Increment the counter
    counter=$((counter + 1))

    # Reset the counter to 1 if it exceeds 3
    if [ "$counter" -gt 3 ]; then
      counter=1
    fi

    # Store the new incremented value
    echo "$counter" > "$counter_file"
fi

# Print the current counter value
echo "$counter"
