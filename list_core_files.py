#!/usr/bin/env python3
"""
Script to list Python files in the generator/core directory.
This replaces the failed shell command: find generator/core -name "*.py" -type f | head -10
"""

import os
from pathlib import Path

def list_python_files(directory, limit=10):
    """List Python files in the specified directory, limited to the first 'limit' files."""
    try:
        core_path = Path(directory)
        if not core_path.exists():
            print(f"Directory '{directory}' does not exist")
            return
        
        python_files = []
        for file_path in core_path.rglob("*.py"):
            if file_path.is_file():
                python_files.append(str(file_path))
                if len(python_files) >= limit:
                    break
        
        if python_files:
            print(f"Found {len(python_files)} Python files in {directory}:")
            for file_path in python_files:
                print(file_path)
        else:
            print(f"No Python files found in {directory}")
            
    except Exception as e:
        print(f"Error listing files: {e}")

if __name__ == "__main__":
    list_python_files("generator/core", 10)