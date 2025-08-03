#!/bin/bash

# Define the counter file
counter_file="$HOME/.my_counter"

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

# Write the new value back to the counter file
echo "$counter" > "$counter_file"

# Print the current counter value
echo "$counter"
