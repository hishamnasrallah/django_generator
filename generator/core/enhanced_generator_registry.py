"""
Enhanced Generator Registry
Advanced registry with dependency resolution, caching, and plugin integration
"""
from typing import Dict, List, Set, Type, Optional, Any, Callable
from pathlib import Path
import importlib
import inspect
from collections import defaultdict, deque
import graphlib
import logging

from .base_generator import BaseGenerator
from .plugin_system import PluginManager, get_plugin_manager
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class GeneratorMetadata:
    """Metadata for a generator."""
    
    def __init__(self, generator_class: Type[BaseGenerator]):
        self.generator_class = generator_class
        self.name = generator_class.name
        self.description = generator_class.description
        self.version = generator_class.version
        self.order = generator_class.order
        self.requires = generator_class.requires
        self.provides = generator_class.provides
        self.module = generator_class.__module__
        self.file_path = inspect.getfile(generator_class)
        self.tags = getattr(generator_class, 'tags', set())
        self.category = getattr(generator_class, 'category', 'general')


class EnhancedGeneratorRegistry:
    """
    Enhanced generator registry with advanced features.
    
    Features:
    - Automatic generator discovery
    - Dependency resolution with topological sorting
    - Plugin integration
    - Generator caching and lazy loading
    - Category and tag-based filtering
    - Performance optimization
    - Conflict detection
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.plugin_manager = get_plugin_manager(settings)
        
        # Generator storage
        self.generators: Dict[str, GeneratorMetadata] = {}
        self.instances: Dict[str, BaseGenerator] = {}
        self.categories: Dict[str, List[str]] = defaultdict(list)
        self.tags: Dict[str, List[str]] = defaultdict(list)
        
        # Discovery and caching
        self._discovered = False
        self._dependency_graph: Optional[Dict[str, Set[str]]] = None
        self._sorted_generators: Optional[List[str]] = None
        
        # Performance tracking
        self.stats = {
            'generators_discovered': 0,
            'generators_loaded': 0,
            'dependency_resolutions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
    
    def discover_generators(self, additional_paths: Optional[List[str]] = None) -> None:
        """
        Discover all available generators.
        
        Args:
            additional_paths: Additional paths to search for generators
        """
        if self._discovered:
            return
        
        logger.info("Starting generator discovery...")
        
        # Discover built-in generators
        self._discover_builtin_generators()
        
        # Discover plugin generators
        self._discover_plugin_generators()
        
        # Discover generators in additional paths
        if additional_paths:
            for path in additional_paths:
                self._discover_generators_in_path(path)
        
        # Build metadata structures
        self._build_metadata_structures()
        
        # Validate dependencies
        self._validate_dependencies()
        
        self._discovered = True
        self.stats['generators_discovered'] = len(self.generators)
        
        logger.info(f"Discovered {len(self.generators)} generators")
    
    def _discover_builtin_generators(self) -> None:
        """Discover built-in generators."""
        # Generator modules to search
        generator_modules = [
            'generator.generators.project',
            'generator.generators.app',
            'generator.generators.api',
            'generator.generators.auth',
            'generator.generators.database',
            'generator.generators.testing',
            'generator.generators.deployment',
            'generator.generators.enterprise',
            'generator.generators.integration',
            'generator.generators.performance',
            'generator.generators.business_logic',
        ]
        
        for module_path in generator_modules:
            try:
                self._discover_generators_in_module(module_path)
            except ImportError as e:
                logger.debug(f"Could not import {module_path}: {e}")
    
    def _discover_plugin_generators(self) -> None:
        """Discover generators from plugins."""
        plugin_generators = self.plugin_manager.get_plugin_generators()
        
        for generator_class in plugin_generators:
            self._register_generator_class(generator_class)
    
    def _discover_generators_in_module(self, module_path: str) -> None:
        """Discover generators in a specific module."""
        try:
            module = importlib.import_module(module_path)
            
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseGenerator) and
                    obj is not BaseGenerator and
                    not name.startswith('_')):
                    
                    self._register_generator_class(obj)
                    
        except ImportError as e:
            logger.debug(f"Could not import {module_path}: {e}")
    
    def _discover_generators_in_path(self, path: str) -> None:
        """Discover generators in a file system path."""
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"Generator path does not exist: {path}")
            return
        
        # Add path to Python path
        import sys
        if str(path_obj) not in sys.path:
            sys.path.insert(0, str(path_obj))
        
        # Search for Python files
        for py_file in path_obj.rglob("*_generator.py"):
            try:
                # Import module
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find generator classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BaseGenerator) and
                        obj is not BaseGenerator):
                        
                        self._register_generator_class(obj)
                        
            except Exception as e:
                logger.warning(f"Failed to load generators from {py_file}: {e}")
    
    def _register_generator_class(self, generator_class: Type[BaseGenerator]) -> None:
        """Register a generator class."""
        metadata = GeneratorMetadata(generator_class)
        
        # Check for name conflicts
        if metadata.name in self.generators:
            existing = self.generators[metadata.name]
            logger.warning(
                f"Generator name conflict: {metadata.name} "
                f"(existing: {existing.module}, new: {metadata.module})"
            )
            return
        
        self.generators[metadata.name] = metadata
        logger.debug(f"Registered generator: {metadata.name}")
    
    def _build_metadata_structures(self) -> None:
        """Build category and tag indexes."""
        self.categories.clear()
        self.tags.clear()
        
        for name, metadata in self.generators.items():
            # Index by category
            self.categories[metadata.category].append(name)
            
            # Index by tags
            for tag in metadata.tags:
                self.tags[tag].append(name)
    
    def _validate_dependencies(self) -> None:
        """Validate generator dependencies."""
        errors = []
        
        for name, metadata in self.generators.items():
            for requirement in metadata.requires:
                # Check if requirement is satisfied by any generator
                satisfied = False
                
                for other_name, other_metadata in self.generators.items():
                    if requirement in other_metadata.provides:
                        satisfied = True
                        break
                
                if not satisfied:
                    errors.append(f"Generator '{name}' requires '{requirement}' but no generator provides it")
        
        if errors:
            logger.warning("Dependency validation errors:")
            for error in errors:
                logger.warning(f"  - {error}")
    
    def get_generator(self, name: str) -> Optional[BaseGenerator]:
        """
        Get a generator instance by name.
        
        Args:
            name: Generator name
            
        Returns:
            Generator instance or None if not found
        """
        if name not in self.generators:
            return None
        
        # Check cache
        if name in self.instances:
            self.stats['cache_hits'] += 1
            return self.instances[name]
        
        # Create new instance
        self.stats['cache_misses'] += 1
        metadata = self.generators[name]
        
        try:
            instance = metadata.generator_class(self.settings)
            self.instances[name] = instance
            self.stats['generators_loaded'] += 1
            return instance
        except Exception as e:
            logger.error(f"Failed to create generator instance '{name}': {e}")
            return None
    
    def get_generators_by_category(self, category: str) -> List[BaseGenerator]:
        """Get all generators in a category."""
        generator_names = self.categories.get(category, [])
        generators = []
        
        for name in generator_names:
            generator = self.get_generator(name)
            if generator:
                generators.append(generator)
        
        return generators
    
    def get_generators_by_tag(self, tag: str) -> List[BaseGenerator]:
        """Get all generators with a specific tag."""
        generator_names = self.tags.get(tag, [])
        generators = []
        
        for name in generator_names:
            generator = self.get_generator(name)
            if generator:
                generators.append(generator)
        
        return generators
    
    def get_generators_for_schema(self, schema: Dict[str, Any]) -> List[BaseGenerator]:
        """
        Get generators that can handle the given schema.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            List of applicable generators
        """
        applicable = []
        
        for name, metadata in self.generators.items():
            generator = self.get_generator(name)
            if generator and generator.can_generate(schema):
                applicable.append(generator)
        
        return applicable
    
    def get_generator_chain(self, schema: Dict[str, Any], 
                          selected_generators: Optional[List[str]] = None) -> List[BaseGenerator]:
        """
        Get ordered list of generators based on dependencies.
        
        Args:
            schema: Schema dictionary
            selected_generators: Optional list of specific generators to use
            
        Returns:
            Ordered list of generators
        """
        self.stats['dependency_resolutions'] += 1
        
        # Get applicable generators
        if selected_generators:
            applicable = []
            for name in selected_generators:
                generator = self.get_generator(name)
                if generator and generator.can_generate(schema):
                    applicable.append(generator)
        else:
            applicable = self.get_generators_for_schema(schema)
        
        if not applicable:
            return []
        
        # Build dependency graph
        graph = {}
        generator_map = {g.name: g for g in applicable}
        
        for generator in applicable:
            graph[generator.name] = set()
            
            # Add dependencies
            for requirement in generator.requires:
                # Find generators that provide this requirement
                for other_name, other_generator in generator_map.items():
                    if requirement in other_generator.provides:
                        graph[generator.name].add(other_name)
                        break
        
        # Topological sort
        try:
            sorter = graphlib.TopologicalSorter(graph)
            ordered_names = list(sorter.static_order())
            
            # Convert to generator instances and sort by order attribute
            ordered_generators = []
            for name in ordered_names:
                if name in generator_map:
                    ordered_generators.append(generator_map[name])
            
            # Secondary sort by order attribute
            ordered_generators.sort(key=lambda g: (g.order, g.name))
            
            return ordered_generators
            
        except graphlib.CycleError as e:
            logger.error(f"Circular dependency detected: {e}")
            # Return generators sorted by order as fallback
            return sorted(applicable, key=lambda g: (g.order, g.name))
    
    def validate_generator_chain(self, generators: List[str]) -> List[str]:
        """
        Validate a list of generator names for dependency issues.
        
        Args:
            generators: List of generator names
            
        Returns:
            List of validation errors
        """
        errors = []
        generator_set = set(generators)
        
        # Check if all generators exist
        for name in generators:
            if name not in self.generators:
                errors.append(f"Generator '{name}' not found")
        
        # Check dependencies
        for name in generators:
            if name not in self.generators:
                continue
            
            metadata = self.generators[name]
            for requirement in metadata.requires:
                # Check if requirement is satisfied
                satisfied = False
                
                for other_name in generator_set:
                    if other_name in self.generators:
                        other_metadata = self.generators[other_name]
                        if requirement in other_metadata.provides:
                            satisfied = True
                            break
                
                if not satisfied:
                    errors.append(f"Generator '{name}' requires '{requirement}' but it's not provided by selected generators")
        
        return errors
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """Get the complete dependency graph."""
        if self._dependency_graph is None:
            self._dependency_graph = {}
            
            for name, metadata in self.generators.items():
                self._dependency_graph[name] = set()
                
                for requirement in metadata.requires:
                    # Find generators that provide this requirement
                    for other_name, other_metadata in self.generators.items():
                        if requirement in other_metadata.provides:
                            self._dependency_graph[name].add(other_name)
        
        return self._dependency_graph
    
    def get_reverse_dependencies(self, generator_name: str) -> List[str]:
        """Get generators that depend on the given generator."""
        dependents = []
        
        if generator_name not in self.generators:
            return dependents
        
        target_metadata = self.generators[generator_name]
        
        for name, metadata in self.generators.items():
            if name == generator_name:
                continue
            
            # Check if this generator requires something that target provides
            for requirement in metadata.requires:
                if requirement in target_metadata.provides:
                    dependents.append(name)
                    break
        
        return dependents
    
    def get_generator_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a generator."""
        if name not in self.generators:
            return None
        
        metadata = self.generators[name]
        
        return {
            'name': metadata.name,
            'description': metadata.description,
            'version': metadata.version,
            'order': metadata.order,
            'category': metadata.category,
            'tags': list(metadata.tags),
            'requires': list(metadata.requires),
            'provides': list(metadata.provides),
            'module': metadata.module,
            'file_path': metadata.file_path,
            'loaded': name in self.instances,
            'dependencies': list(self.get_dependency_graph().get(name, set())),
            'dependents': self.get_reverse_dependencies(name),
        }
    
    def list_generators(self, category: Optional[str] = None, 
                       tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List generators with optional filtering.
        
        Args:
            category: Filter by category
            tag: Filter by tag
            
        Returns:
            List of generator information
        """
        generators = []
        
        for name in self.generators:
            if category and self.generators[name].category != category:
                continue
            
            if tag and tag not in self.generators[name].tags:
                continue
            
            info = self.get_generator_info(name)
            if info:
                generators.append(info)
        
        return sorted(generators, key=lambda x: (x['category'], x['order'], x['name']))
    
    def get_categories(self) -> List[str]:
        """Get list of all generator categories."""
        return sorted(self.categories.keys())
    
    def get_tags(self) -> List[str]:
        """Get list of all generator tags."""
        return sorted(self.tags.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            **self.stats,
            'total_generators': len(self.generators),
            'loaded_generators': len(self.instances),
            'categories': len(self.categories),
            'tags': len(self.tags),
        }
    
    def clear_cache(self) -> None:
        """Clear the generator instance cache."""
        self.instances.clear()
        self._dependency_graph = None
        self._sorted_generators = None
    
    def reload_generator(self, name: str) -> bool:
        """
        Reload a generator (useful for development).
        
        Args:
            name: Generator name
            
        Returns:
            True if reloaded successfully
        """
        if name not in self.generators:
            return False
        
        try:
            # Remove from cache
            if name in self.instances:
                del self.instances[name]
            
            # Reload module
            metadata = self.generators[name]
            module = importlib.import_module(metadata.module)
            importlib.reload(module)
            
            # Re-register
            generator_class = getattr(module, metadata.generator_class.__name__)
            self._register_generator_class(generator_class)
            
            logger.info(f"Reloaded generator: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload generator {name}: {e}")
            return False


# Global registry instance
_registry: Optional[EnhancedGeneratorRegistry] = None


def get_registry(settings: Optional[Settings] = None) -> EnhancedGeneratorRegistry:
    """Get global generator registry instance."""
    global _registry
    
    if _registry is None:
        _registry = EnhancedGeneratorRegistry(settings)
        _registry.discover_generators()
    
    return _registry


def register_generator(generator_class: Type[BaseGenerator]) -> None:
    """Register a generator with the global registry."""
    registry = get_registry()
    registry._register_generator_class(generator_class)


def discover_generators(additional_paths: Optional[List[str]] = None) -> None:
    """Discover all available generators."""
    registry = get_registry()
    registry.discover_generators(additional_paths)