"""
Plugin System
Extensible plugin architecture for custom generators and functionality
"""
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Callable, Set
from abc import ABC, abstractmethod
import logging

from .base_generator import BaseGenerator
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """
    Base class for all plugins.
    
    Plugins can extend the generator with:
    - Custom generators
    - Template filters and functions
    - Context processors
    - Post-generation hooks
    """
    
    name: str = "BasePlugin"
    version: str = "1.0.0"
    description: str = "Base plugin class"
    author: str = "Unknown"
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.enabled = True
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin."""
        pass
    
    def get_generators(self) -> List[Type[BaseGenerator]]:
        """Return list of generator classes provided by this plugin."""
        return []
    
    def get_template_filters(self) -> Dict[str, Callable]:
        """Return dictionary of template filters provided by this plugin."""
        return {}
    
    def get_template_functions(self) -> Dict[str, Callable]:
        """Return dictionary of template functions provided by this plugin."""
        return {}
    
    def get_context_processors(self) -> List[Callable]:
        """Return list of context processors provided by this plugin."""
        return []
    
    def get_post_generation_hooks(self) -> List[Callable]:
        """Return list of post-generation hooks provided by this plugin."""
        return []
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin with settings."""
        pass
    
    def cleanup(self) -> None:
        """Cleanup resources when plugin is disabled."""
        pass


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.
    
    Features:
    - Plugin discovery from directories
    - Plugin loading and initialization
    - Dependency resolution
    - Plugin configuration
    - Plugin lifecycle management
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.plugin_directories: List[Path] = []
        self._discovered_plugins: Dict[str, Type[Plugin]] = {}
        
        # Set up plugin directories
        self._setup_plugin_directories()
    
    def _setup_plugin_directories(self) -> None:
        """Setup plugin directories from settings."""
        # Default plugin directory
        default_dir = Path(__file__).parent.parent / 'plugins'
        if default_dir.exists():
            self.plugin_directories.append(default_dir)
        
        # Custom plugin directories from settings
        custom_dirs = self.settings.get('plugin_directories', [])
        for dir_path in custom_dirs:
            path = Path(dir_path)
            if path.exists():
                self.plugin_directories.append(path)
    
    def discover_plugins(self) -> None:
        """Discover all available plugins."""
        for plugin_dir in self.plugin_directories:
            self._discover_plugins_in_directory(plugin_dir)
    
    def _discover_plugins_in_directory(self, directory: Path) -> None:
        """Discover plugins in a specific directory."""
        if not directory.exists():
            return
        
        # Add directory to Python path
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
        
        # Look for Python files
        for plugin_file in directory.glob('*.py'):
            if plugin_file.name.startswith('_'):
                continue
            
            try:
                self._load_plugin_module(plugin_file)
            except Exception as e:
                logger.warning(f"Failed to load plugin from {plugin_file}: {e}")
        
        # Look for plugin packages
        for plugin_package in directory.iterdir():
            if plugin_package.is_dir() and not plugin_package.name.startswith('_'):
                init_file = plugin_package / '__init__.py'
                if init_file.exists():
                    try:
                        self._load_plugin_package(plugin_package)
                    except Exception as e:
                        logger.warning(f"Failed to load plugin package {plugin_package}: {e}")
    
    def _load_plugin_module(self, plugin_file: Path) -> None:
        """Load plugin from a Python file."""
        module_name = plugin_file.stem
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin classes in module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj is not Plugin):
                    
                    self._discovered_plugins[obj.name] = obj
                    logger.info(f"Discovered plugin: {obj.name} from {plugin_file}")
                    
        except Exception as e:
            logger.error(f"Error loading plugin module {plugin_file}: {e}")
    
    def _load_plugin_package(self, plugin_package: Path) -> None:
        """Load plugin from a Python package."""
        package_name = plugin_package.name
        
        try:
            module = importlib.import_module(package_name)
            
            # Look for plugin classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj is not Plugin):
                    
                    self._discovered_plugins[obj.name] = obj
                    logger.info(f"Discovered plugin: {obj.name} from package {plugin_package}")
                    
        except Exception as e:
            logger.error(f"Error loading plugin package {plugin_package}: {e}")
    
    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load and initialize a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to load
            config: Plugin configuration
            
        Returns:
            True if plugin was loaded successfully
        """
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} is already loaded")
            return True
        
        if plugin_name not in self._discovered_plugins:
            logger.error(f"Plugin {plugin_name} not found")
            return False
        
        try:
            plugin_class = self._discovered_plugins[plugin_name]
            plugin_instance = plugin_class(self.settings)
            
            # Configure plugin
            if config:
                plugin_instance.configure(config)
                self.plugin_configs[plugin_name] = config
            
            # Initialize plugin
            plugin_instance.initialize()
            
            # Store plugin
            self.plugins[plugin_name] = plugin_instance
            
            logger.info(f"Loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
            
        Returns:
            True if plugin was unloaded successfully
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} is not loaded")
            return False
        
        try:
            plugin = self.plugins[plugin_name]
            plugin.cleanup()
            
            del self.plugins[plugin_name]
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self, plugin_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Load all discovered plugins."""
        plugin_configs = plugin_configs or {}
        
        for plugin_name in self._discovered_plugins:
            config = plugin_configs.get(plugin_name)
            self.load_plugin(plugin_name, config)
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a loaded plugin by name."""
        return self.plugins.get(plugin_name)
    
    def get_loaded_plugins(self) -> List[Plugin]:
        """Get list of all loaded plugins."""
        return list(self.plugins.values())
    
    def get_discovered_plugins(self) -> List[str]:
        """Get list of all discovered plugin names."""
        return list(self._discovered_plugins.keys())
    
    def get_plugin_generators(self) -> List[Type[BaseGenerator]]:
        """Get all generator classes from loaded plugins."""
        generators = []
        for plugin in self.plugins.values():
            generators.extend(plugin.get_generators())
        return generators
    
    def get_plugin_template_filters(self) -> Dict[str, Callable]:
        """Get all template filters from loaded plugins."""
        filters = {}
        for plugin in self.plugins.values():
            filters.update(plugin.get_template_filters())
        return filters
    
    def get_plugin_template_functions(self) -> Dict[str, Callable]:
        """Get all template functions from loaded plugins."""
        functions = {}
        for plugin in self.plugins.values():
            functions.update(plugin.get_template_functions())
        return functions
    
    def get_plugin_context_processors(self) -> List[Callable]:
        """Get all context processors from loaded plugins."""
        processors = []
        for plugin in self.plugins.values():
            processors.extend(plugin.get_context_processors())
        return processors
    
    def get_plugin_post_generation_hooks(self) -> List[Callable]:
        """Get all post-generation hooks from loaded plugins."""
        hooks = []
        for plugin in self.plugins.values():
            hooks.extend(plugin.get_post_generation_hooks())
        return hooks
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded."""
        return plugin_name in self.plugins
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a plugin."""
        if plugin_name in self._discovered_plugins:
            plugin_class = self._discovered_plugins[plugin_name]
            return {
                'name': plugin_class.name,
                'version': plugin_class.version,
                'description': plugin_class.description,
                'author': plugin_class.author,
                'loaded': plugin_name in self.plugins,
                'class': plugin_class.__name__,
                'module': plugin_class.__module__,
            }
        return None
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all discovered plugins with their info."""
        plugins_info = []
        for plugin_name in self._discovered_plugins:
            info = self.get_plugin_info(plugin_name)
            if info:
                plugins_info.append(info)
        return plugins_info


class PluginHookManager:
    """
    Manages plugin hooks and events.
    """
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register a callback for a hook."""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(callback)
    
    def unregister_hook(self, hook_name: str, callback: Callable) -> None:
        """Unregister a callback from a hook."""
        if hook_name in self.hooks:
            try:
                self.hooks[hook_name].remove(callback)
            except ValueError:
                pass
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Trigger all callbacks for a hook."""
        results = []
        if hook_name in self.hooks:
            for callback in self.hooks[hook_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error in hook {hook_name}: {e}")
        return results
    
    def has_hook(self, hook_name: str) -> bool:
        """Check if a hook has any callbacks."""
        return hook_name in self.hooks and len(self.hooks[hook_name]) > 0


# Example plugin implementations

class ExamplePlugin(Plugin):
    """Example plugin implementation."""
    
    name = "ExamplePlugin"
    version = "1.0.0"
    description = "Example plugin for demonstration"
    author = "Django Enhanced Generator"
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name}")
    
    def get_template_filters(self) -> Dict[str, Callable]:
        """Return custom template filters."""
        return {
            'example_filter': lambda x: f"Example: {x}",
            'reverse_string': lambda x: x[::-1] if isinstance(x, str) else x,
        }
    
    def get_template_functions(self) -> Dict[str, Callable]:
        """Return custom template functions."""
        return {
            'example_function': lambda: "Hello from plugin!",
            'get_timestamp': lambda: datetime.now().isoformat(),
        }


class CustomGeneratorPlugin(Plugin):
    """Plugin that provides custom generators."""
    
    name = "CustomGeneratorPlugin"
    version = "1.0.0"
    description = "Plugin with custom generators"
    author = "Django Enhanced Generator"
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name}")
    
    def get_generators(self) -> List[Type[BaseGenerator]]:
        """Return custom generator classes."""
        # This would return actual generator classes
        return []


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager(settings: Optional[Settings] = None) -> PluginManager:
    """Get global plugin manager instance."""
    global _plugin_manager
    
    if _plugin_manager is None:
        _plugin_manager = PluginManager(settings)
        _plugin_manager.discover_plugins()
    
    return _plugin_manager


def register_plugin(plugin_class: Type[Plugin]) -> None:
    """Register a plugin class with the global plugin manager."""
    manager = get_plugin_manager()
    manager._discovered_plugins[plugin_class.name] = plugin_class


def load_plugin(plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """Load a plugin with the global plugin manager."""
    manager = get_plugin_manager()
    return manager.load_plugin(plugin_name, config)