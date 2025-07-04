"""
Generator Registry
Manages all generators and their dependencies
"""
from typing import Dict, List, Set, Type, Optional, Any
from pathlib import Path
import importlib
import inspect
from collections import defaultdict
import graphlib

from .base_generator import BaseGenerator
from ..config.settings import Settings


class GeneratorRegistry:
    """
    Registry for all code generators.

    Features:
    - Auto-discovery of generators
    - Dependency resolution
    - Generator ordering
    - Plugin support
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.generators: Dict[str, Type[BaseGenerator]] = {}
        self.instances: Dict[str, BaseGenerator] = {}
        self._discovered = False

    def discover_generators(self, additional_paths: Optional[List[str]] = None) -> None:
        """
        Discover all available generators.

        Args:
            additional_paths: Additional paths to search for generators
        """
        if self._discovered:
            return

        # Default generator paths
        generator_paths = [
            'generators.project',
            'generators.app',
            'generators.api',
            'generators.auth',
            'generators.database',
            'generators.testing',
            'generators.deployment',
            'generators.enterprise',
            'generators.integration',
            'generators.performance',
        ]

        # Add additional paths
        if additional_paths:
            generator_paths.extend(additional_paths)

        # Discover generators in each module
        for module_path in generator_paths:
            self._discover_in_module(module_path)

        # Discover plugin generators
        self._discover_plugins()

        self._discovered = True

    def _discover_in_module(self, module_path: str) -> None:
        """Discover generators in a specific module."""
        try:
            # Try to import the module
            module = importlib.import_module(f"django_enhanced_generator.{module_path}")

            # Look for generator classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                        issubclass(obj, BaseGenerator) and
                        obj is not BaseGenerator and
                        not name.startswith('_')):

                    self.register(obj)

        except ImportError as e:
            # Module might not exist or have issues
            if self.settings.get('debug'):
                print(f"Warning: Could not import {module_path}: {e}")

    def _discover_plugins(self) -> None:
        """Discover plugin generators."""
        plugin_dir = self.settings.get('plugin_directory', 'plugins')
        plugin_path = Path(plugin_dir)

        if not plugin_path.exists():
            return

        # Add plugin directory to Python path
        import sys
        sys.path.insert(0, str(plugin_path))

        # Discover generators in plugins
        for plugin_file in plugin_path.glob('*_generator.py'):
            module_name = plugin_file.stem

            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                            issubclass(obj, BaseGenerator) and
                            obj is not BaseGenerator):

                        self.register(obj)

            except Exception as e:
                if self.settings.get('debug'):
                    print(f"Warning: Could not load plugin {module_name}: {e}")

    def register(self, generator_class: Type[BaseGenerator]) -> None:
        """
        Register a generator class.

        Args:
            generator_class: Generator class to register
        """
        name = generator_class.name

        if name in self.generators:
            # Check if it's the same class
            if self.generators[name] is generator_class:
                return

            # Warn about duplicate
            if self.settings.get('debug'):
                print(f"Warning: Duplicate generator name '{name}', replacing with {generator_class}")

        self.generators[name] = generator_class

    def unregister(self, name: str) -> None:
        """Unregister a generator."""
        self.generators.pop(name, None)
        self.instances.pop(name, None)

    def get_generator(self, name: str) -> Optional[BaseGenerator]:
        """
        Get a generator instance by name.

        Args:
            name: Generator name

        Returns:
            Generator instance or None
        """
        if name not in self.generators:
            return None

        # Create instance if not exists
        if name not in self.instances:
            generator_class = self.generators[name]
            self.instances[name] = generator_class(self.settings)

        return self.instances[name]

    def get_all_generators(self) -> List[BaseGenerator]:
        """Get all generator instances."""
        return [self.get_generator(name) for name in self.generators]

    def get_generators_for_schema(self, schema: Dict[str, Any]) -> List[BaseGenerator]:
        """
        Get generators that can handle the given schema.

        Args:
            schema: Schema dictionary

        Returns:
            List of applicable generators
        """
        applicable = []

        for name, generator_class in self.generators.items():
            generator = self.get_generator(name)
            if generator and generator.can_generate(schema):
                applicable.append(generator)

        return applicable

    def get_generator_chain(self, schema: Dict[str, Any]) -> List[BaseGenerator]:
        """
        Get ordered list of generators based on dependencies.

        Args:
            schema: Schema dictionary

        Returns:
            Ordered list of generators
        """
        # Get applicable generators
        applicable = self.get_generators_for_schema(schema)

        if not applicable:
            return []

        # Build dependency graph
        graph = defaultdict(set)
        generator_map = {g.name: g for g in applicable}

        for generator in applicable:
            # Add generator to graph
            if generator.name not in graph:
                graph[generator.name] = set()

            # Add dependencies
            for dep in generator.requires:
                if dep in generator_map:
                    graph[generator.name].add(dep)

        # Topological sort
        try:
            sorter = graphlib.TopologicalSorter(graph)
            ordered_names = list(sorter.static_order())

            # Filter to only applicable generators and reverse
            # (dependencies should run before dependents)
            ordered_generators = []
            for name in reversed(ordered_names):
                if name in generator_map:
                    ordered_generators.append(generator_map[name])

            # Sort by order attribute within dependency groups
            def sort_key(gen):
                # Count dependencies
                dep_count = len([d for d in gen.requires if d in generator_map])
                return (dep_count, gen.order, gen.name)

            ordered_generators.sort(key=sort_key)

            return ordered_generators

        except graphlib.CycleError as e:
            raise ValueError(f"Circular dependency detected: {e}")

    def get_provides(self) -> Dict[str, List[str]]:
        """
        Get mapping of what each generator provides.

        Returns:
            Dict mapping feature to list of generator names
        """
        provides_map = defaultdict(list)

        for name, generator_class in self.generators.items():
            generator = self.get_generator(name)
            if generator:
                for feature in generator.provides:
                    provides_map[feature].append(name)

        return dict(provides_map)

    def get_requirements(self) -> Dict[str, Set[str]]:
        """
        Get requirements for each generator.

        Returns:
            Dict mapping generator name to set of requirements
        """
        requirements = {}

        for name in self.generators:
            generator = self.get_generator(name)
            if generator:
                requirements[name] = generator.requires

        return requirements

    def validate_dependencies(self, selected_generators: List[str]) -> List[str]:
        """
        Validate that all dependencies are satisfied.

        Args:
            selected_generators: List of selected generator names

        Returns:
            List of missing dependencies

        Raises:
            ValueError: If dependencies cannot be resolved
        """
        selected_set = set(selected_generators)
        missing = []

        for gen_name in selected_generators:
            generator = self.get_generator(gen_name)
            if not generator:
                missing.append(f"Generator '{gen_name}' not found")
                continue

            for requirement in generator.requires:
                if requirement not in selected_set:
                    # Check if any selected generator provides this
                    provided = False
                    for other_name in selected_set:
                        other = self.get_generator(other_name)
                        if other and requirement in other.provides:
                            provided = True
                            break

                    if not provided:
                        missing.append(f"'{gen_name}' requires '{requirement}'")

        return missing

    def get_generator_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific generator."""
        generator = self.get_generator(name)
        if not generator:
            return None

        return {
            'name': generator.name,
            'description': generator.description,
            'version': generator.version,
            'order': generator.order,
            'requires': list(generator.requires),
            'provides': list(generator.provides),
            'class': generator.__class__.__name__,
            'module': generator.__class__.__module__,
        }

    def list_generators(self) -> List[Dict[str, Any]]:
        """List all available generators with their info."""
        return [
            self.get_generator_info(name)
            for name in sorted(self.generators.keys())
        ]

    def check_conflicts(self, selected_generators: List[str]) -> List[str]:
        """
        Check for conflicts between selected generators.

        Args:
            selected_generators: List of generator names

        Returns:
            List of conflict descriptions
        """
        conflicts = []

        # Check for multiple generators providing same feature
        provides_count = defaultdict(list)

        for gen_name in selected_generators:
            generator = self.get_generator(gen_name)
            if generator:
                for feature in generator.provides:
                    provides_count[feature].append(gen_name)

        for feature, providers in provides_count.items():
            if len(providers) > 1:
                conflicts.append(
                    f"Feature '{feature}' is provided by multiple generators: {', '.join(providers)}"
                )

        return conflicts


# Global registry instance
_registry: Optional[GeneratorRegistry] = None


def get_registry(settings: Optional[Settings] = None) -> GeneratorRegistry:
    """Get global generator registry instance."""
    global _registry

    if _registry is None:
        _registry = GeneratorRegistry(settings)
        _registry.discover_generators()

    return _registry


def register_generator(generator_class: Type[BaseGenerator]) -> None:
    """Register a generator with the global registry."""
    registry = get_registry()
    registry.register(generator_class)


def discover_generators(additional_paths: Optional[List[str]] = None) -> None:
    """Discover all available generators."""
    registry = get_registry()
    registry.discover_generators(additional_paths)