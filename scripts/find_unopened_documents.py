#!/usr/bin/env python3
"""
Script to find unopened FCStd files in directories of open FreeCAD documents.

Usage: Copy and paste into FreeCAD Python terminal.

File responsibility: Script to find unopened FCStd files in directories of open documents.
"""

from pathlib import Path

import FreeCAD


# Get all open documents and their file paths
opened_paths = set()

# listDocuments() returns a dict: {doc_name: doc_object}
for doc in FreeCAD.listDocuments().values():
    if doc.FileName:
        opened_paths.add(Path(doc.FileName).resolve())

# Collect unique parent directories from open documents
# Using a set ensures we don't check the same directory multiple times
check_dirs = set()
for path in opened_paths:
    check_dirs.add(path.parent)

# Find all FCStd files in these directories (recursively)
all_fcstd_files = set()
for check_dir in check_dirs:
    if check_dir.exists():
        for fcstd_file in check_dir.rglob("*.FCStd"):
            all_fcstd_files.add(fcstd_file.resolve())

# Find files that are not opened
unopened_files = all_fcstd_files - opened_paths

# Display results
print(f"Found {len(unopened_files)} unopened FCStd file(s):")
print("=" * 60)

if unopened_files:
    for i, filepath in enumerate(sorted(unopened_files), 1):
        print(f"{i}. {filepath}")
else:
    print("No unopened FCStd files found in the directories of open documents.")

print("=" * 60)
