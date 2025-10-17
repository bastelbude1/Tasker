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
    vtps --dir /path/to/project  # Use specific project directory
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def discover_project_dir(override_dir=None):
    """
    Discover project summary directory using a flexible search strategy.

    Search order:
    1. CLI --dir argument (if provided)
    2. VTPS_PROJECT_DIR environment variable
    3. Upward search from script dir for logs/project or project directories
    4. Common relative locations from script dir

    Args:
        override_dir: Optional directory path from CLI argument

    Returns:
        Path object to project directory

    Raises:
        SystemExit if no valid directory found
    """
    script_dir = Path(__file__).resolve().parent
    checked_paths = []

    # 1. CLI argument override (highest priority)
    if override_dir:
        path = Path(override_dir).resolve()
        checked_paths.append(("--dir argument", path))
        if path.exists() and path.is_dir():
            return path

    # 2. Environment variable override
    env_dir = os.environ.get('VTPS_PROJECT_DIR')
    if env_dir:
        path = Path(env_dir).resolve()
        checked_paths.append(("VTPS_PROJECT_DIR env var", path))
        if path.exists() and path.is_dir():
            return path

    # 3. Upward search from script directory
    current = script_dir
    max_depth = 5  # Limit upward search to prevent infinite loops

    for _ in range(max_depth):
        # Check for logs/project subdirectory
        logs_project = current / 'logs' / 'project'
        checked_paths.append(("upward search (logs/project)", logs_project))
        if logs_project.exists() and logs_project.is_dir():
            return logs_project

        # Check for TASKER/log/project subdirectory (legacy layout)
        tasker_log = current / 'TASKER' / 'log' / 'project'
        checked_paths.append(("upward search (TASKER/log/project)", tasker_log))
        if tasker_log.exists() and tasker_log.is_dir():
            return tasker_log

        # Check for TASKER/project subdirectory (common layout)
        tasker_project = current / 'TASKER' / 'project'
        checked_paths.append(("upward search (TASKER/project)", tasker_project))
        if tasker_project.exists() and tasker_project.is_dir():
            return tasker_project

        # Check for project subdirectory
        project = current / 'project'
        checked_paths.append(("upward search (project)", project))
        if project.exists() and project.is_dir():
            return project

        # Move up one directory
        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent

    # 4. Common relative locations from script directory
    relative_locations = [
        script_dir / 'logs' / 'project',
        script_dir / 'log' / 'project',
        script_dir / 'TASKER' / 'log' / 'project',
        script_dir / 'TASKER' / 'project',
        script_dir / 'project',
    ]

    for location in relative_locations:
        checked_paths.append(("relative location", location))
        if location.exists() and location.is_dir():
            return location

    # No valid directory found - provide helpful error message
    print("ERROR: Could not find project summary directory", file=sys.stderr)
    print("\nSearched the following locations:", file=sys.stderr)
    for source, path in checked_paths:
        exists_marker = "[EXISTS]" if path.exists() else "[NOT FOUND]"
        is_dir_marker = "[DIR]" if path.is_dir() else "[NOT DIR]" if path.exists() else ""
        print(f"  {exists_marker} {is_dir_marker} {source}: {path}", file=sys.stderr)

    print("\nTo specify a custom directory:", file=sys.stderr)
    print("  vtps --dir /path/to/project/directory", file=sys.stderr)
    print("  export VTPS_PROJECT_DIR=/path/to/project/directory", file=sys.stderr)
    sys.exit(1)


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
    # Parse arguments with argparse for better CLI handling
    parser = argparse.ArgumentParser(
        description='TASKER Project Summary Viewer - View and analyze project summary files',
        epilog='Examples:\n'
               '  vtps                        List last 10 summary files\n'
               '  vtps test_resume            List/view files matching "test_resume"\n'
               '  vtps -n 20                  List last 20 files\n'
               '  vtps --dir /custom/path     Use custom project directory\n'
               '  vtps path/to/file.summary   View specific file',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'pattern',
        nargs='?',
        help='Pattern to match summary files, or path to specific file'
    )
    parser.add_argument(
        '-n', '--count',
        type=int,
        default=10,
        metavar='N',
        help='Number of files to list (default: 10)'
    )
    parser.add_argument(
        '--dir',
        dest='project_dir',
        metavar='PATH',
        help='Project directory path (overrides auto-discovery and VTPS_PROJECT_DIR)'
    )

    args = parser.parse_args()

    # Discover project directory with override support
    project_dir = discover_project_dir(override_dir=args.project_dir)

    # No pattern: list last N files
    if not args.pattern:
        list_summary_files(project_dir, args.count)
        return

    pattern_or_path = args.pattern

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
