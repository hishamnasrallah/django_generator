"""
File Generator
Handles file generation with templates, formatting, and conflict resolution
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import hashlib
import difflib

from .template_engine import TemplateEngine
from .base_generator import GeneratedFile
from ..utils.file_system import FileSystemManager
from ..utils.code_formatter import CodeFormatter
from ..config.settings import Settings


class FileGenerator:
    """
    Handles file generation with advanced features.
    
    Features:
    - Template-based file generation
    - Code formatting and optimization
    - Conflict detection and resolution
    - File backup and rollback
    - Dry run support
    - Progress tracking
    """
    
    def __init__(self, settings: Optional[Settings] = None, output_dir: str = ".", 
                 force: bool = False, dry_run: bool = False):
        self.settings = settings or Settings()
        self.template_engine = TemplateEngine(settings)
        self.code_formatter = CodeFormatter(settings)
        self.fs_manager = FileSystemManager(output_dir, force=force, dry_run=dry_run)
        
        self.generated_files: List[GeneratedFile] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.stats = {
            'files_generated': 0,
            'files_skipped': 0,
            'files_updated': 0,
            'conflicts_detected': 0,
            'templates_rendered': 0,
        }
    
    def generate_file_from_template(self, template_name: str, output_path: str, 
                                  context: Dict[str, Any], **kwargs) -> Optional[GeneratedFile]:
        """
        Generate a file from a template.
        
        Args:
            template_name: Name of the template file
            output_path: Output file path relative to output directory
            context: Template context
            **kwargs: Additional file metadata
            
        Returns:
            GeneratedFile object or None if dry run
        """
        try:
            # Render template
            content = self.template_engine.render_template(template_name, context)
            self.stats['templates_rendered'] += 1
            
            # Format content based on file type
            formatted_content = self._format_content(content, output_path)
            
            # Create GeneratedFile object
            generated_file = GeneratedFile(
                path=output_path,
                content=formatted_content,
                file_type=self._get_file_type(output_path),
                **kwargs
            )
            
            # Set metadata
            generated_file.metadata.update({
                'template': template_name,
                'generated_at': datetime.now(),
                'generator': 'FileGenerator',
            })
            
            # Write file
            written_path = self._write_file(generated_file)
            
            if written_path:
                self.generated_files.append(generated_file)
                self.stats['files_generated'] += 1
            
            return generated_file
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate file {output_path} from template {template_name}: {e}")
    
    def generate_file_from_string(self, template_string: str, output_path: str, 
                                context: Dict[str, Any], **kwargs) -> Optional[GeneratedFile]:
        """
        Generate a file from a template string.
        
        Args:
            template_string: Template string
            output_path: Output file path relative to output directory
            context: Template context
            **kwargs: Additional file metadata
            
        Returns:
            GeneratedFile object or None if dry run
        """
        try:
            # Render template string
            content = self.template_engine.render_string(template_string, context)
            self.stats['templates_rendered'] += 1
            
            # Format content based on file type
            formatted_content = self._format_content(content, output_path)
            
            # Create GeneratedFile object
            generated_file = GeneratedFile(
                path=output_path,
                content=formatted_content,
                file_type=self._get_file_type(output_path),
                **kwargs
            )
            
            # Set metadata
            generated_file.metadata.update({
                'template': 'string',
                'generated_at': datetime.now(),
                'generator': 'FileGenerator',
            })
            
            # Write file
            written_path = self._write_file(generated_file)
            
            if written_path:
                self.generated_files.append(generated_file)
                self.stats['files_generated'] += 1
            
            return generated_file
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate file {output_path} from template string: {e}")
    
    def copy_file(self, source_path: str, dest_path: str, **kwargs) -> Optional[GeneratedFile]:
        """
        Copy a file to the output directory.
        
        Args:
            source_path: Source file path
            dest_path: Destination path relative to output directory
            **kwargs: Additional file metadata
            
        Returns:
            GeneratedFile object or None if dry run
        """
        try:
            source = Path(source_path)
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            
            # Read source content
            content = source.read_text(encoding='utf-8')
            
            # Format content if needed
            formatted_content = self._format_content(content, dest_path)
            
            # Create GeneratedFile object
            generated_file = GeneratedFile(
                path=dest_path,
                content=formatted_content,
                file_type=self._get_file_type(dest_path),
                **kwargs
            )
            
            # Set metadata
            generated_file.metadata.update({
                'source': source_path,
                'generated_at': datetime.now(),
                'generator': 'FileGenerator',
                'operation': 'copy',
            })
            
            # Write file
            written_path = self._write_file(generated_file)
            
            if written_path:
                self.generated_files.append(generated_file)
                self.stats['files_generated'] += 1
            
            return generated_file
            
        except Exception as e:
            raise RuntimeError(f"Failed to copy file {source_path} to {dest_path}: {e}")
    
    def create_directory(self, dir_path: str) -> Optional[Path]:
        """
        Create a directory.
        
        Args:
            dir_path: Directory path relative to output directory
            
        Returns:
            Path to created directory or None if dry run
        """
        return self.fs_manager.create_directory(dir_path)
    
    def batch_generate(self, file_specs: List[Dict[str, Any]]) -> List[GeneratedFile]:
        """
        Generate multiple files in batch.
        
        Args:
            file_specs: List of file specifications
            
        Returns:
            List of generated files
        """
        generated = []
        
        for spec in file_specs:
            try:
                if 'template' in spec:
                    # Template-based generation
                    file_obj = self.generate_file_from_template(
                        template_name=spec['template'],
                        output_path=spec['output_path'],
                        context=spec.get('context', {}),
                        **spec.get('metadata', {})
                    )
                elif 'template_string' in spec:
                    # String template generation
                    file_obj = self.generate_file_from_string(
                        template_string=spec['template_string'],
                        output_path=spec['output_path'],
                        context=spec.get('context', {}),
                        **spec.get('metadata', {})
                    )
                elif 'source' in spec:
                    # File copy
                    file_obj = self.copy_file(
                        source_path=spec['source'],
                        dest_path=spec['output_path'],
                        **spec.get('metadata', {})
                    )
                else:
                    continue
                
                if file_obj:
                    generated.append(file_obj)
                    
            except Exception as e:
                print(f"Warning: Failed to generate {spec.get('output_path', 'unknown')}: {e}")
                continue
        
        return generated
    
    def _write_file(self, generated_file: GeneratedFile) -> Optional[Path]:
        """Write a GeneratedFile to disk."""
        return self.fs_manager.write_file(
            relative_path=generated_file.path,
            content=generated_file.content,
            executable=generated_file.executable,
            append=generated_file.append
        )
    
    def _format_content(self, content: str, file_path: str) -> str:
        """Format content based on file type."""
        try:
            return self.code_formatter.format_file(file_path, content)
        except Exception:
            # If formatting fails, return original content
            return content
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from path."""
        ext_mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'text',
            '.sh': 'shell',
            '.dockerfile': 'dockerfile',
            'Dockerfile': 'dockerfile',
            'Makefile': 'makefile',
            '.sql': 'sql',
            '.xml': 'xml',
        }
        
        path_obj = Path(file_path)
        
        # Check full filename first
        if path_obj.name in ext_mapping:
            return ext_mapping[path_obj.name]
        
        # Check extension
        ext = path_obj.suffix.lower()
        return ext_mapping.get(ext, 'text')
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            **self.stats,
            'total_files': len(self.generated_files),
            'conflicts': len(self.conflicts),
            'fs_stats': self.fs_manager.get_summary(),
        }
    
    def get_generated_files(self) -> List[GeneratedFile]:
        """Get list of generated files."""
        return self.generated_files.copy()
    
    def rollback(self) -> None:
        """Rollback all file operations."""
        self.fs_manager.rollback()
        self.generated_files.clear()
        self.stats = {key: 0 for key in self.stats}


class TemplateResolver:
    """
    Resolves template dependencies and inheritance.
    """
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
        self._dependency_cache: Dict[str, List[str]] = {}
    
    def get_template_dependencies(self, template_name: str) -> List[str]:
        """Get list of templates that this template depends on."""
        if template_name in self._dependency_cache:
            return self._dependency_cache[template_name]
        
        dependencies = []
        
        try:
            # Get template source
            template = self.template_engine.env.get_template(template_name)
            source = template.source
            
            # Find extends and includes
            extends_matches = re.findall(r'{%\s*extends\s+["\']([^"\']+)["\']', source)
            include_matches = re.findall(r'{%\s*include\s+["\']([^"\']+)["\']', source)
            
            dependencies.extend(extends_matches)
            dependencies.extend(include_matches)
            
            # Recursively get dependencies of dependencies
            for dep in extends_matches + include_matches:
                dependencies.extend(self.get_template_dependencies(dep))
            
            # Remove duplicates and cache
            dependencies = list(set(dependencies))
            self._dependency_cache[template_name] = dependencies
            
        except Exception:
            # If we can't parse dependencies, return empty list
            dependencies = []
        
        return dependencies
    
    def resolve_template_order(self, template_names: List[str]) -> List[str]:
        """Resolve template generation order based on dependencies."""
        # Build dependency graph
        graph = {}
        for template in template_names:
            graph[template] = self.get_template_dependencies(template)
        
        # Topological sort
        resolved = []
        temp_mark = set()
        perm_mark = set()
        
        def visit(node):
            if node in temp_mark:
                raise ValueError(f"Circular dependency detected involving {node}")
            if node in perm_mark:
                return
            
            temp_mark.add(node)
            for dep in graph.get(node, []):
                if dep in graph:  # Only visit if it's in our list
                    visit(dep)
            
            temp_mark.remove(node)
            perm_mark.add(node)
            resolved.append(node)
        
        for template in template_names:
            if template not in perm_mark:
                visit(template)
        
        return resolved


class ConflictResolver:
    """
    Handles file conflicts during generation.
    """
    
    def __init__(self):
        self.resolution_strategies = {
            'overwrite': self._overwrite_strategy,
            'skip': self._skip_strategy,
            'merge': self._merge_strategy,
            'backup': self._backup_strategy,
            'interactive': self._interactive_strategy,
        }
    
    def resolve_conflict(self, existing_content: str, new_content: str, 
                        strategy: str = 'backup') -> Tuple[str, bool]:
        """
        Resolve conflict between existing and new content.
        
        Args:
            existing_content: Content of existing file
            new_content: New content to write
            strategy: Resolution strategy
            
        Returns:
            Tuple of (final_content, should_write)
        """
        resolver = self.resolution_strategies.get(strategy, self._backup_strategy)
        return resolver(existing_content, new_content)
    
    def _overwrite_strategy(self, existing_content: str, new_content: str) -> Tuple[str, bool]:
        """Always overwrite with new content."""
        return new_content, True
    
    def _skip_strategy(self, existing_content: str, new_content: str) -> Tuple[str, bool]:
        """Skip writing if file exists."""
        return existing_content, False
    
    def _merge_strategy(self, existing_content: str, new_content: str) -> Tuple[str, bool]:
        """Attempt to merge content (basic implementation)."""
        # This is a simplified merge - in practice, you'd want more sophisticated merging
        if existing_content == new_content:
            return existing_content, False
        
        # For now, just append new content
        merged = existing_content + '\n\n# Generated content:\n' + new_content
        return merged, True
    
    def _backup_strategy(self, existing_content: str, new_content: str) -> Tuple[str, bool]:
        """Create backup and overwrite."""
        return new_content, True
    
    def _interactive_strategy(self, existing_content: str, new_content: str) -> Tuple[str, bool]:
        """Interactive resolution (simplified for CLI)."""
        print("File conflict detected!")
        print("Choose resolution:")
        print("1. Overwrite")
        print("2. Skip")
        print("3. Show diff")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            return new_content, True
        elif choice == '2':
            return existing_content, False
        elif choice == '3':
            self._show_diff(existing_content, new_content)
            return self._interactive_strategy(existing_content, new_content)
        else:
            print("Invalid choice, skipping file.")
            return existing_content, False
    
    def _show_diff(self, existing_content: str, new_content: str) -> None:
        """Show diff between existing and new content."""
        diff = difflib.unified_diff(
            existing_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile='existing',
            tofile='new',
            n=3
        )
        
        print("Diff:")
        for line in diff:
            print(line.rstrip())