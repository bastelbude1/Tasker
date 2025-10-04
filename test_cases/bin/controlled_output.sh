#!/bin/bash

# controlled_output.sh <exit_code> <stdout> <stderr> [delay_seconds]
#
# Produces exactly controlled output for predictable testing:
# - exit_code: The exit code to return (0-255)
# - stdout: String to output to stdout (use "NONE" for no output)
# - stderr: String to output to stderr (use "NONE" for no output)
# - delay_seconds: Optional delay before exiting (default: 0)
#
# Examples:
#   controlled_output.sh 0 "running" "NONE"           # Success with stdout
#   controlled_output.sh 1 "NONE" "error occurred"    # Failure with stderr
#   controlled_output.sh 0 "completed" "warning" 2    # Success with both outputs and 2s delay

# Validate arguments
if [ $# -lt 3 ]; then
    echo "Usage: controlled_output.sh <exit_code> <stdout> <stderr> [delay_seconds]" >&2
    echo "  exit_code: 0-255" >&2
    echo "  stdout: String for stdout output (use NONE for no output)" >&2
    echo "  stderr: String for stderr output (use NONE for no output)" >&2
    echo "  delay_seconds: Optional delay before exit (default: 0)" >&2
    exit 1
fi

exit_code="$1"
stdout_text="$2"
stderr_text="$3"
delay="${4:-0}"

# Validate exit code
if ! [[ "$exit_code" =~ ^[0-9]+$ ]] || [ "$exit_code" -gt 255 ]; then
    echo "Error: Exit code must be 0-255" >&2
    exit 1
fi

# Validate delay
if ! [[ "$delay" =~ ^[0-9]+$ ]]; then
    echo "Error: Delay must be a non-negative integer" >&2
    exit 1
fi

# Output to stdout if specified
if [ "$stdout_text" != "NONE" ]; then
    echo "$stdout_text"
fi

# Output to stderr if specified
if [ "$stderr_text" != "NONE" ]; then
    echo "$stderr_text" >&2
fi

# Apply delay if specified
if [ "$delay" -gt 0 ]; then
    sleep "$delay"
fi

# Exit with specified code
exit "$exit_code"