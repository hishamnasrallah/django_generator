"""
Generation Engine
Orchestrates the entire code generation process
"""
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .enhanced_generator_registry import get_registry
from .file_generator import FileGenerator
from .template_engine import TemplateEngine
from .plugin_system import get_plugin_manager
from .schema_parser import SchemaParser
from ..config.settings import Settings
from ..utils.file_system import FileSystemManager

logger = logging.getLogger(__name__)


class GenerationContext:
    """Context object passed through the generation process."""
    
    def __init__(self, schema: Dict[str, Any], settings: Settings):
        self.schema = schema
        self.settings = settings
        self.start_time = datetime.now()
        self.generated_files: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats = {
            'generators_executed': 0,
            'files_generated': 0,
            'templates_rendered': 0,
            'execution_time': 0,
        }
        self.metadata: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_generated_file(self, file_path: str) -> None:
        """Thread-safe method to add a generated file."""
        with self._lock:
            self.generated_files.append(file_path)
            self.stats['files_generated'] += 1
    
    def add_error(self, error: str) -> None:
        """Thread-safe method to add an error."""
        with self._lock:
            self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Thread-safe method to add a warning."""
        with self._lock:
            self.warnings.append(warning)
    
    def increment_stat(self, stat_name: str, value: int = 1) -> None:
        """Thread-safe method to increment a statistic."""
        with self._lock:
            self.stats[stat_name] = self.stats.get(stat_name, 0) + value


class GenerationEngine:
    """
    Main generation engine that orchestrates the entire process.
    
    Features:
    - Schema validation and parsing
    - Generator discovery and dependency resolution
    - Parallel generation execution
    - Progress tracking and reporting
    - Error handling and recovery
    - Plugin integration
    - Post-generation hooks
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.registry = get_registry(settings)
        self.plugin_manager = get_plugin_manager(settings)
        self.schema_parser = SchemaParser(settings)
        
        # Generation state
        self.context: Optional[GenerationContext] = None
        self.progress_callbacks: List[Callable] = []
        self.pre_generation_hooks: List[Callable] = []
        self.post_generation_hooks: List[Callable] = []
        
        # Configuration
        self.parallel_execution = self.settings.get('parallel_execution', True)
        self.max_workers = self.settings.get('max_workers', 4)
        self.continue_on_error = self.settings.get('continue_on_error', True)
    
    def generate(self, schema: Dict[str, Any], output_dir: str = ".", 
                force: bool = False, dry_run: bool = False,
                selected_generators: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate code from schema.
        
        Args:
            schema: Schema dictionary
            output_dir: Output directory
            force: Force overwrite existing files
            dry_run: Perform dry run without writing files
            selected_generators: Optional list of specific generators to use
            
        Returns:
            Generation results
        """
        start_time = time.time()
        
        try:
            # Parse and validate schema
            parsed_schema = self._parse_schema(schema)
            
            # Create generation context
            self.context = GenerationContext(parsed_schema, self.settings)
            
            # Execute pre-generation hooks
            self._execute_pre_generation_hooks()
            
            # Get generator chain
            generators = self._get_generator_chain(parsed_schema, selected_generators)
            
            if not generators:
                return {
                    'success': False,
                    'error': 'No applicable generators found',
                    'stats': self.context.stats,
                }
            
            # Execute generators
            self._execute_generators(generators, output_dir, force, dry_run)
            
            # Execute post-generation hooks
            self._execute_post_generation_hooks()
            
            # Calculate final stats
            execution_time = time.time() - start_time
            self.context.stats['execution_time'] = execution_time
            
            # Return results
            return {
                'success': len(self.context.errors) == 0,
                'generated_files': self.context.generated_files,
                'errors': self.context.errors,
                'warnings': self.context.warnings,
                'stats': self.context.stats,
                'execution_time': execution_time,
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.context.stats if self.context else {},
                'execution_time': time.time() - start_time,
            }
    
    def _parse_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate schema."""
        try:
            return self.schema_parser.parse(schema)
        except Exception as e:
            raise ValueError(f"Schema validation failed: {e}")
    
    def _get_generator_chain(self, schema: Dict[str, Any], 
                           selected_generators: Optional[List[str]]) -> List:
        """Get ordered list of generators."""
        try:
            generators = self.registry.get_generator_chain(schema, selected_generators)
            
            if selected_generators:
                # Validate selected generators
                errors = self.registry.validate_generator_chain(selected_generators)
                if errors:
                    raise ValueError(f"Generator validation failed: {'; '.join(errors)}")
            
            logger.info(f"Generator chain: {[g.name for g in generators]}")
            return generators
            
        except Exception as e:
            raise ValueError(f"Failed to build generator chain: {e}")
    
    def _execute_generators(self, generators: List, output_dir: str, 
                          force: bool, dry_run: bool) -> None:
        """Execute generators in order."""
        if self.parallel_execution and len(generators) > 1:
            self._execute_generators_parallel(generators, output_dir, force, dry_run)
        else:
            self._execute_generators_sequential(generators, output_dir, force, dry_run)
    
    def _execute_generators_sequential(self, generators: List, output_dir: str,
                                     force: bool, dry_run: bool) -> None:
        """Execute generators sequentially."""
        for i, generator in enumerate(generators):
            try:
                self._notify_progress(f"Executing {generator.name}", i, len(generators))
                
                # Create file generator for this generator
                file_generator = FileGenerator(
                    settings=self.settings,
                    output_dir=output_dir,
                    force=force,
                    dry_run=dry_run
                )
                
                # Execute generator
                generated_files = generator.generate(self.context.schema, {
                    'file_generator': file_generator,
                    'context': self.context,
                })
                
                # Update context
                for generated_file in generated_files:
                    self.context.add_generated_file(generated_file.path)
                
                self.context.increment_stat('generators_executed')
                
                logger.info(f"Generator {generator.name} completed successfully")
                
            except Exception as e:
                error_msg = f"Generator {generator.name} failed: {e}"
                logger.error(error_msg)
                self.context.add_error(error_msg)
                
                if not self.continue_on_error:
                    raise
    
    def _execute_generators_parallel(self, generators: List, output_dir: str,
                                   force: bool, dry_run: bool) -> None:
        """Execute generators in parallel where possible."""
        # Group generators by dependency level
        dependency_levels = self._group_by_dependency_level(generators)
        
        # Execute each level sequentially, but generators within a level in parallel
        for level, level_generators in enumerate(dependency_levels):
            if len(level_generators) == 1:
                # Single generator, execute directly
                self._execute_generator(level_generators[0], output_dir, force, dry_run)
            else:
                # Multiple generators, execute in parallel
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(level_generators))) as executor:
                    futures = []
                    
                    for generator in level_generators:
                        future = executor.submit(
                            self._execute_generator, generator, output_dir, force, dry_run
                        )
                        futures.append((future, generator))
                    
                    # Wait for all generators in this level to complete
                    for future, generator in futures:
                        try:
                            future.result()
                            logger.info(f"Generator {generator.name} completed successfully")
                        except Exception as e:
                            error_msg = f"Generator {generator.name} failed: {e}"
                            logger.error(error_msg)
                            self.context.add_error(error_msg)
                            
                            if not self.continue_on_error:
                                # Cancel remaining futures
                                for f, _ in futures:
                                    f.cancel()
                                raise
    
    def _execute_generator(self, generator, output_dir: str, force: bool, dry_run: bool) -> None:
        """Execute a single generator."""
        try:
            # Create file generator for this generator
            file_generator = FileGenerator(
                settings=self.settings,
                output_dir=output_dir,
                force=force,
                dry_run=dry_run
            )
            
            # Execute generator
            generated_files = generator.generate(self.context.schema, {
                'file_generator': file_generator,
                'context': self.context,
            })
            
            # Update context
            for generated_file in generated_files:
                self.context.add_generated_file(generated_file.path)
            
            self.context.increment_stat('generators_executed')
            
        except Exception as e:
            raise RuntimeError(f"Generator execution failed: {e}")
    
    def _group_by_dependency_level(self, generators: List) -> List[List]:
        """Group generators by dependency level for parallel execution."""
        # Build dependency graph
        graph = {}
        generator_map = {g.name: g for g in generators}
        
        for generator in generators:
            graph[generator.name] = set()
            
            # Add dependencies that are in our generator list
            for requirement in generator.requires:
                for other_generator in generators:
                    if requirement in other_generator.provides:
                        graph[generator.name].add(other_generator.name)
                        break
        
        # Group by dependency level
        levels = []
        remaining = set(generator_map.keys())
        
        while remaining:
            # Find generators with no dependencies in remaining set
            current_level = []
            for name in list(remaining):
                dependencies = graph[name] & remaining
                if not dependencies:
                    current_level.append(generator_map[name])
                    remaining.remove(name)
            
            if not current_level:
                # Circular dependency or other issue
                # Add all remaining generators to avoid infinite loop
                current_level = [generator_map[name] for name in remaining]
                remaining.clear()
            
            levels.append(current_level)
        
        return levels
    
    def _execute_pre_generation_hooks(self) -> None:
        """Execute pre-generation hooks."""
        hooks = self.pre_generation_hooks + self.plugin_manager.get_plugin_post_generation_hooks()
        
        for hook in hooks:
            try:
                hook(self.context)
            except Exception as e:
                logger.warning(f"Pre-generation hook failed: {e}")
    
    def _execute_post_generation_hooks(self) -> None:
        """Execute post-generation hooks."""
        hooks = self.post_generation_hooks + self.plugin_manager.get_plugin_post_generation_hooks()
        
        for hook in hooks:
            try:
                hook(self.context)
            except Exception as e:
                logger.warning(f"Post-generation hook failed: {e}")
    
    def _notify_progress(self, message: str, current: int, total: int) -> None:
        """Notify progress callbacks."""
        progress_data = {
            'message': message,
            'current': current,
            'total': total,
            'percentage': (current / total) * 100 if total > 0 else 0,
            'context': self.context,
        }
        
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def add_progress_callback(self, callback: Callable) -> None:
        """Add a progress callback."""
        self.progress_callbacks.append(callback)
    
    def add_pre_generation_hook(self, hook: Callable) -> None:
        """Add a pre-generation hook."""
        self.pre_generation_hooks.append(hook)
    
    def add_post_generation_hook(self, hook: Callable) -> None:
        """Add a post-generation hook."""
        self.post_generation_hooks.append(hook)
    
    def validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema without generating code.
        
        Args:
            schema: Schema to validate
            
        Returns:
            Validation results
        """
        try:
            parsed_schema = self._parse_schema(schema)
            
            return {
                'valid': True,
                'schema': parsed_schema,
                'warnings': [],
                'errors': [],
            }
            
        except Exception as e:
            return {
                'valid': False,
                'schema': None,
                'warnings': [],
                'errors': [str(e)],
            }
    
    def get_generation_plan(self, schema: Dict[str, Any], 
                          selected_generators: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get generation plan without executing.
        
        Args:
            schema: Schema dictionary
            selected_generators: Optional list of specific generators
            
        Returns:
            Generation plan
        """
        try:
            parsed_schema = self._parse_schema(schema)
            generators = self._get_generator_chain(parsed_schema, selected_generators)
            
            plan = {
                'valid': True,
                'generators': [
                    {
                        'name': g.name,
                        'description': g.description,
                        'order': g.order,
                        'requires': list(g.requires),
                        'provides': list(g.provides),
                    }
                    for g in generators
                ],
                'execution_order': [g.name for g in generators],
                'estimated_files': self._estimate_file_count(generators, parsed_schema),
            }
            
            return plan
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'generators': [],
                'execution_order': [],
                'estimated_files': 0,
            }
    
    def _estimate_file_count(self, generators: List, schema: Dict[str, Any]) -> int:
        """Estimate number of files that will be generated."""
        # This is a rough estimation
        estimated_count = 0
        
        # Base project files
        estimated_count += 10
        
        # Files per app
        app_count = len(schema.get('apps', []))
        estimated_count += app_count * 5  # models, views, urls, admin, tests
        
        # API files if enabled
        if schema.get('features', {}).get('api', {}).get('rest_framework'):
            estimated_count += app_count * 3  # serializers, viewsets, urls
        
        # Additional files based on features
        features = schema.get('features', {})
        if features.get('deployment', {}).get('docker'):
            estimated_count += 3  # Dockerfile, docker-compose, etc.
        
        if features.get('deployment', {}).get('kubernetes'):
            estimated_count += 5  # Various k8s manifests
        
        return estimated_count


# Global engine instance
_engine: Optional[GenerationEngine] = None


def get_engine(settings: Optional[Settings] = None) -> GenerationEngine:
    """Get global generation engine instance."""
    global _engine
    
    if _engine is None:
        _engine = GenerationEngine(settings)
    
    return _engine


def generate_code(schema: Dict[str, Any], output_dir: str = ".", 
                 force: bool = False, dry_run: bool = False,
                 selected_generators: Optional[List[str]] = None,
                 settings: Optional[Settings] = None) -> Dict[str, Any]:
    """
    Convenience function to generate code.
    
    Args:
        schema: Schema dictionary
        output_dir: Output directory
        force: Force overwrite existing files
        dry_run: Perform dry run without writing files
        selected_generators: Optional list of specific generators to use
        settings: Optional settings
        
    Returns:
        Generation results
    """
    engine = get_engine(settings)
    return engine.generate(schema, output_dir, force, dry_run, selected_generators)