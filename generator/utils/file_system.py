"""
File System Manager
Handles file and directory operations for code generation
"""
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import stat
import json
import yaml
from datetime import datetime
import hashlib
import difflib


class FileSystemManager:
    """
    Manages file system operations for the code generator.

    Features:
    - Safe file writing with backup
    - Directory creation
    - File permissions handling
    - Conflict resolution
    - Dry run support
    """

    def __init__(self, output_dir: str = ".", force: bool = False,
                 backup: bool = True, dry_run: bool = False):
        self.output_dir = Path(output_dir).resolve()
        self.force = force
        self.backup = backup
        self.dry_run = dry_run
        self.written_files: List[Path] = []
        self.backed_up_files: Dict[Path, Path] = {}
        self.conflicts: List[Dict[str, Any]] = []

        # Create output directory if it doesn't exist
        if not self.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_file(self, relative_path: str, content: str,
                   executable: bool = False, append: bool = False) -> Optional[Path]:
        """
        Write content to a file.

        Args:
            relative_path: Path relative to output directory
            content: File content
            executable: Whether to make file executable
            append: Whether to append to existing file

        Returns:
            Path to written file or None if dry run
        """
        file_path = self.output_dir / relative_path

        # Handle dry run
        if self.dry_run:
            print(f"[DRY RUN] Would write: {relative_path}")
            return None

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing file
        if file_path.exists() and not self.force and not append:
            if self._handle_conflict(file_path, content):
                return None

        # Backup existing file
        if file_path.exists() and self.backup and not append:
            self._backup_file(file_path)

        # Write file
        try:
            if append and file_path.exists():
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Set executable permission
            if executable:
                self._make_executable(file_path)

            self.written_files.append(file_path)
            return file_path

        except Exception as e:
            raise IOError(f"Failed to write file {file_path}: {e}")

    def copy_file(self, source: str, dest_relative_path: str) -> Optional[Path]:
        """
        Copy a file to the output directory.

        Args:
            source: Source file path
            dest_relative_path: Destination path relative to output directory

        Returns:
            Path to copied file or None if dry run
        """
        source_path = Path(source)
        dest_path = self.output_dir / dest_relative_path

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        # Handle dry run
        if self.dry_run:
            print(f"[DRY RUN] Would copy: {source} -> {dest_relative_path}")
            return None

        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing file
        if dest_path.exists() and not self.force:
            if self._handle_conflict(dest_path, source_path.read_text()):
                return None

        # Backup existing file
        if dest_path.exists() and self.backup:
            self._backup_file(dest_path)

        # Copy file
        try:
            shutil.copy2(source_path, dest_path)
            self.written_files.append(dest_path)
            return dest_path
        except Exception as e:
            raise IOError(f"Failed to copy file {source} to {dest_path}: {e}")

    def create_directory(self, relative_path: str) -> Optional[Path]:
        """
        Create a directory.

        Args:
            relative_path: Path relative to output directory

        Returns:
            Path to created directory or None if dry run
        """
        dir_path = self.output_dir / relative_path

        # Handle dry run
        if self.dry_run:
            print(f"[DRY RUN] Would create directory: {relative_path}")
            return None

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return dir_path
        except Exception as e:
            raise IOError(f"Failed to create directory {dir_path}: {e}")

    def write_json(self, relative_path: str, data: Dict[str, Any],
                   indent: int = 2) -> Optional[Path]:
        """Write data as JSON file."""
        content = json.dumps(data, indent=indent, sort_keys=True)
        return self.write_file(relative_path, content)

    def write_yaml(self, relative_path: str, data: Dict[str, Any]) -> Optional[Path]:
        """Write data as YAML file."""
        content = yaml.dump(data, default_flow_style=False, sort_keys=True)
        return self.write_file(relative_path, content)

    def _handle_conflict(self, file_path: Path, new_content: str) -> bool:
        """
        Handle file conflict.

        Returns:
            True if conflict should prevent writing, False otherwise
        """
        existing_content = file_path.read_text(encoding='utf-8')

        # Check if content is identical
        if existing_content == new_content:
            return False  # No real conflict, same content

        # Record conflict
        self.conflicts.append({
            'path': file_path,
            'existing_hash': self._hash_content(existing_content),
            'new_hash': self._hash_content(new_content),
            'diff': self._get_diff(existing_content, new_content),
        })

        # In force mode, we overwrite
        if self.force:
            return False

        # Otherwise, skip the file
        print(f"WARNING: File exists and differs: {file_path}")
        print("Use --force to overwrite or --backup to create backups")
        return True

    def _backup_file(self, file_path: Path) -> Path:
        """Create a backup of an existing file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = file_path.with_suffix(f'.{timestamp}.backup')

        # Find unique backup name
        counter = 1
        while backup_path.exists():
            backup_path = file_path.with_suffix(f'.{timestamp}_{counter}.backup')
            counter += 1

        shutil.copy2(file_path, backup_path)
        self.backed_up_files[file_path] = backup_path

        return backup_path

    def _make_executable(self, file_path: Path) -> None:
        """Make a file executable."""
        current_permissions = file_path.stat().st_mode
        file_path.chmod(current_permissions | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _hash_content(self, content: str) -> str:
        """Generate hash of content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _get_diff(self, old_content: str, new_content: str) -> List[str]:
        """Get diff between old and new content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='existing',
            tofile='new',
            n=3
        ))

        return diff[:50]  # Limit diff size

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of file operations."""
        return {
            'output_directory': str(self.output_dir),
            'files_written': len(self.written_files),
            'files_backed_up': len(self.backed_up_files),
            'conflicts': len(self.conflicts),
            'written_files': [str(p.relative_to(self.output_dir)) for p in self.written_files],
            'backed_up_files': {
                str(k.relative_to(self.output_dir)): str(v.relative_to(self.output_dir))
                for k, v in self.backed_up_files.items()
            },
        }

    def restore_backups(self) -> None:
        """Restore all backed up files."""
        for original_path, backup_path in self.backed_up_files.items():
            if backup_path.exists():
                shutil.copy2(backup_path, original_path)
                backup_path.unlink()  # Remove backup

        self.backed_up_files.clear()

    def cleanup_backups(self) -> None:
        """Remove all backup files."""
        for backup_path in self.backed_up_files.values():
            if backup_path.exists():
                backup_path.unlink()

        self.backed_up_files.clear()

    def rollback(self) -> None:
        """Rollback all changes."""
        # Restore backups
        self.restore_backups()

        # Remove newly created files
        for file_path in self.written_files:
            if file_path.exists() and file_path not in self.backed_up_files:
                file_path.unlink()

        self.written_files.clear()


class TemplateFileManager:
    """
    Manages template files for the generator.
    """

    def __init__(self, template_dirs: List[str]):
        self.template_dirs = [Path(d) for d in template_dirs]
        self._template_cache: Dict[str, str] = {}

    def get_template_path(self, template_name: str) -> Optional[Path]:
        """Find template file in template directories."""
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                return template_path
        return None

    def read_template(self, template_name: str, cache: bool = True) -> str:
        """Read template content."""
        # Check cache
        if cache and template_name in self._template_cache:
            return self._template_cache[template_name]

        # Find template
        template_path = self.get_template_path(template_name)
        if not template_path:
            raise FileNotFoundError(f"Template not found: {template_name}")

        # Read content
        content = template_path.read_text(encoding='utf-8')

        # Cache if requested
        if cache:
            self._template_cache[template_name] = content

        return content

    def list_templates(self, pattern: str = "*.j2") -> List[str]:
        """List all available templates."""
        templates = []

        for template_dir in self.template_dirs:
            if template_dir.exists():
                for template_path in template_dir.rglob(pattern):
                    relative_path = template_path.relative_to(template_dir)
                    templates.append(str(relative_path))

        return sorted(set(templates))

    def clear_cache(self) -> None:
        """Clear template cache."""
        self._template_cache.clear()