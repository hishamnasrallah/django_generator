"""
URL Generator
Generates URL patterns for Django REST Framework APIs
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class URLGenerator(BaseGenerator):
    """
    Generates URL patterns with:
    - Router configuration
    - Nested routes
    - Custom action URLs
    - API versioning URLs
    - WebSocket routing
    """

    name = "URLGenerator"
    description = "Generates URL patterns for APIs"
    version = "1.0.0"
    order = 45
    requires = {'ViewGenerator'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.naming = NamingConventions()

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if URL generation is needed."""
        return (
                schema.get('features', {}).get('api', {}).get('rest_framework', False) or
                schema.get('features', {}).get('api', {}).get('graphql', False) or
                schema.get('features', {}).get('api', {}).get('websockets', False)
        )

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate URL pattern files."""
        self.generated_files = []

        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_urls(app, schema)

        # Generate WebSocket routing if needed
        if schema.get('features', {}).get('api', {}).get('websockets'):
            self._generate_websocket_routing(schema)

        return self.generated_files

    def _generate_app_urls(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate URL patterns for an app."""
        app_name = app['name']
        models = app.get('models', [])

        # Analyze URL patterns needed
        url_config = self._analyze_url_requirements(app, schema)

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'url_config': url_config,
            'has_viewsets': any(model.get('api', {}).get('viewset', True) for model in models),
            'has_api_views': any(model.get('api', {}).get('api_views') for model in models),
            'has_nested_routes': self._has_nested_routes(models),
            'has_custom_actions': any(
                model.get('api', {}).get('custom_actions') for model in models
            ),
        }

        # Generate URLs
        self.create_file_from_template(
            'app/api/urls.py.j2',
            f'apps/{app_name}/urls.py',
            ctx
        )

        # Generate API URLs if REST framework is enabled
        if schema.get('features', {}).get('api', {}).get('rest_framework'):
            self.create_file_from_template(
                'app/api/api_urls.py.j2',
                f'apps/{app_name}/api_urls.py',
                ctx
            )

    def _analyze_url_requirements(self, app: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what URL patterns are needed."""
        config = {
            'routes': [],
            'custom_patterns': [],
            'nested_routes': [],
        }

        for model in app.get('models', []):
            model_name = model['name']
            api_config = model.get('api', {})

            # Standard ViewSet route
            if api_config.get('viewset', True):
                route = {
                    'url': self.naming.to_url_pattern(model_name),
                    'viewset': f"{model_name}ViewSet",
                    'basename': model_name.lower(),
                }
                config['routes'].append(route)

            # Custom API views
            if api_config.get('api_views'):
                for view in api_config['api_views']:
                    pattern = {
                        'url': view.get('url', f"{model_name.lower()}/{view['name']}"),
                        'view': view['view_class'],
                        'name': view.get('name', f"{model_name.lower()}-{view['name']}"),
                    }
                    config['custom_patterns'].append(pattern)

            # Nested routes
            if api_config.get('nested_routes'):
                for nested in api_config['nested_routes']:
                    nested_route = {
                        'parent': model_name,
                        'parent_lookup': nested.get('parent_lookup', 'pk'),
                        'child': nested['model'],
                        'url': nested.get('url', self.naming.to_url_pattern(nested['model'])),
                    }
                    config['nested_routes'].append(nested_route)

        return config

    def _has_nested_routes(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has nested routes."""
        for model in models:
            if model.get('api', {}).get('nested_routes'):
                return True
        return False

    def _generate_websocket_routing(self, schema: Dict[str, Any]) -> None:
        """Generate WebSocket routing configuration."""
        ctx = {
            'project': schema['project'],
            'apps': schema['apps'],
            'features': schema.get('features', {}),
        }

        # Main routing file
        self.create_file_from_template(
            'websocket/routing.py.j2',
            f'{schema["project"]["name"]}/routing.py',
            ctx
        )

        # ASGI configuration
        self.create_file_from_template(
            'websocket/asgi.py.j2',
            f'{schema["project"]["name"]}/asgi.py',
            ctx
        )