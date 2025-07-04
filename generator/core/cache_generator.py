"""
Cache Generator
Generates comprehensive caching strategies and implementations
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class CacheGenerator(BaseGenerator):
    """
    Generates caching strategies and implementations.
    
    Features:
    - Model-level caching
    - View caching
    - Template fragment caching
    - Cache invalidation strategies
    - Cache warming
    """
    
    name = "CacheGenerator"
    description = "Generates caching strategies and implementations"
    version = "1.0.0"
    order = 55
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if caching is enabled."""
        return schema.get('features', {}).get('performance', {}).get('caching', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate caching files."""
        self.generated_files = []
        
        # Generate core caching components
        self._generate_cache_core(schema)
        
        # Generate app-specific caching
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_caching(app, schema)
        
        return self.generated_files
    
    def _generate_cache_core(self, schema: Dict[str, Any]) -> None:
        """Generate core caching components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema.get('apps', []),
        }
        
        # Cache configuration
        self.create_file_from_template(
            'performance/cache/cache_config.py.j2',
            'core/cache/config.py',
            ctx
        )
        
        # Cache decorators
        self.create_file_from_template(
            'performance/cache/cache_decorators.py.j2',
            'core/cache/decorators.py',
            ctx
        )
        
        # Cache middleware
        self.create_file_from_template(
            'performance/cache/cache_middleware.py.j2',
            'core/cache/middleware.py',
            ctx
        )
        
        # Cache utilities
        self.create_file_from_template(
            'performance/cache/cache_utils.py.j2',
            'core/cache/utils.py',
            ctx
        )
    
    def _generate_app_caching(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate caching for a single app."""
        app_name = app['name']
        models = app.get('models', [])
        
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'cache_strategies': self._generate_cache_strategies(models),
        }
        
        self.create_file_from_template(
            'performance/cache/app_cache.py.j2',
            f'apps/{app_name}/cache.py',
            ctx
        )
    
    def _generate_cache_strategies(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate cache strategies for models."""
        strategies = []
        
        for model in models:
            if model.get('features', {}).get('cache', True):
                strategy = {
                    'model_name': model['name'],
                    'cache_timeout': model.get('cache_timeout', 3600),
                    'cache_key_prefix': model['name'].lower(),
                    'invalidation_signals': ['post_save', 'post_delete'],
                    'cache_methods': self._get_cache_methods(model),
                }
                
                strategies.append(strategy)
        
        return strategies
    
    def _get_cache_methods(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get cache methods for a model."""
        methods = [
            {
                'name': 'get_cached',
                'description': f"Get cached {model['name']} instance",
                'cache_key': f"{model['name'].lower()}:{{pk}}",
                'timeout': 3600,
            },
            {
                'name': 'get_list_cached',
                'description': f"Get cached {model['name']} list",
                'cache_key': f"{model['name'].lower()}:list:{{filters_hash}}",
                'timeout': 1800,
            },
            {
                'name': 'get_count_cached',
                'description': f"Get cached {model['name']} count",
                'cache_key': f"{model['name'].lower()}:count:{{filters_hash}}",
                'timeout': 900,
            },
        ]
        
        return methods