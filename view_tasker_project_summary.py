#!/usr/bin/env python3
"""
TASKER Project Summary Viewer
------------------------------
View TASKER project summary files (.summary) with proper column alignment.

Usage:
    vtps                    # List last 10 summary files
    vtps test_resume        # List/view files matching 'test_resume'
    vtps path/to/file.summary  # View specific file
    vtps -n 20              # List last 20 files
"""

import os
import sys
import glob
from pathlib import Path
from datetime import datetime


def get_project_dir():
    """Find the project summary directory relative to script location."""
    # Script is in /home/baste/tasker/, project dir is /home/baste/TASKER/project/
    script_dir = Path(__file__).resolve().parent

    # Try multiple possible locations
    possible_dirs = [
        script_dir.parent / 'TASKER' / 'project',  # /home/baste/TASKER/project/
        Path('/home/baste/TASKER/project'),         # Absolute fallback
        script_dir / 'log' / 'project',             # Relative to tasker dir
    ]

    for dir_path in possible_dirs:
        if dir_path.exists() and dir_path.is_dir():
            return dir_path

    # Fallback: current directory
    return Path.cwd()


def format_tsv_aligned(file_path):
    """Read TSV file and display with aligned columns."""
    try:
        with open(file_path, 'r') as f:
            lines = [line.rstrip('\n') for line in f.readlines()]

        if not lines:
            print(f"File is empty: {file_path}")
            return

        # Split lines into columns
        rows = [line.split('\t') for line in lines]

        # Calculate maximum width for each column
        num_cols = max(len(row) for row in rows)
        col_widths = [0] * num_cols

        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # Print aligned rows
        for row in rows:
            # Pad each cell to column width
            padded = []
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    padded.append(cell.ljust(col_widths[i]))
                else:
                    padded.append(cell)
            print('  '.join(padded))

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


def list_summary_files(project_dir, limit=10):
    """List summary files sorted by modification time (newest first)."""
    summary_files = list(project_dir.glob('*.summary'))

    if not summary_files:
        print(f"No summary files found in: {project_dir}")
        return

    # Sort by modification time (newest first)
    summary_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Limit results
    summary_files = summary_files[:limit]

    print(f"Last {len(summary_files)} summary files in {project_dir}:")
    print()

    for f in summary_files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        size = f.stat().st_size

        # Count lines (exclude header)
        try:
            with open(f, 'r') as file:
                line_count = sum(1 for line in file if not line.startswith('#'))
                line_count_str = str(line_count)
        except:
            line_count_str = '?'

        print(f"  {f.name:40s}  {mtime.strftime('%Y-%m-%d %H:%M:%S')}  {size:>6d} bytes  {line_count_str:>4s} entries")


def find_matching_files(project_dir, pattern):
    """Find summary files matching the pattern."""
    # Try exact match first
    exact_match = project_dir / f"{pattern}.summary"
    if exact_match.exists():
        return [exact_match]

    # Try pattern matching
    matches = []
    for f in project_dir.glob('*.summary'):
        if pattern.lower() in f.stem.lower():
            matches.append(f)

    return sorted(matches)


def main():
    """Main entry point."""
    # Parse arguments
    args = sys.argv[1:]

    # Get project directory
    project_dir = get_project_dir()

    # Handle -n flag for listing count
    list_count = 10
    if args and args[0] == '-n':
        if len(args) < 2:
            print("Error: -n requires a number", file=sys.stderr)
            sys.exit(1)
        try:
            list_count = int(args[1])
            args = args[2:]  # Remove -n and count from args
        except ValueError:
            print(f"Error: Invalid number: {args[1]}", file=sys.stderr)
            sys.exit(1)

    # No arguments: list last N files
    if not args:
        list_summary_files(project_dir, list_count)
        return

    pattern_or_path = args[0]

    # Check if it's a file path
    file_path = Path(pattern_or_path)
    if file_path.exists() and file_path.is_file():
        print(f"Viewing: {file_path}")
        print()
        format_tsv_aligned(file_path)
        return

    # Not a file path, treat as pattern
    matches = find_matching_files(project_dir, pattern_or_path)

    if not matches:
        print(f"No summary files found matching: {pattern_or_path}")
        print(f"Searched in: {project_dir}")
        return

    if len(matches) == 1:
        # Single match: display it
        print(f"Viewing: {matches[0]}")
        print()
        format_tsv_aligned(matches[0])
    else:
        # Multiple matches: list them
        print(f"Found {len(matches)} files matching '{pattern_or_path}':")
        print()
        for f in matches:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            size = f.stat().st_size

            # Count entries
            try:
                with open(f, 'r') as file:
                    line_count = sum(1 for line in file if not line.startswith('#'))
                    line_count_str = str(line_count)
            except:
                line_count_str = '?'

            print(f"  {f.name:40s}  {mtime.strftime('%Y-%m-%d %H:%M:%S')}  {size:>6d} bytes  {line_count_str:>4s} entries")

        print()
        print(f"To view a file: vtps <filename>")


if __name__ == '__main__':
    main()
