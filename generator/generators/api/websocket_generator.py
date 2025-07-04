"""
WebSocket Generator
Generates Django Channels WebSocket consumers and routing
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class WebSocketGenerator(BaseGenerator):
    """
    Generates WebSocket support with:
    - Consumers for real-time updates
    - Routing configuration
    - Authentication middleware
    - Message handlers
    - Client JavaScript code
    """

    name = "WebSocketGenerator"
    description = "Generates WebSocket support using Django Channels"
    version = "1.0.0"
    order = 60
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if WebSocket support is enabled."""
        return schema.get('features', {}).get('api', {}).get('websockets', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate WebSocket files."""
        self.generated_files = []

        # Generate WebSocket configuration
        self._generate_websocket_config(schema)

        # Generate app-specific consumers
        for app in schema.get('apps', []):
            if self._needs_websocket(app):
                self._generate_app_websockets(app, schema)

        # Generate client-side code
        self._generate_client_code(schema)

        return self.generated_files

    def _generate_websocket_config(self, schema: Dict[str, Any]) -> None:
        """Generate WebSocket configuration files."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # Middleware
        self.create_file_from_template(
            'websocket/middleware.py.j2',
            'websocket/middleware.py',
            ctx
        )

        # Authentication
        self.create_file_from_template(
            'websocket/auth.py.j2',
            'websocket/auth.py',
            ctx
        )

        # Base consumer
        self.create_file_from_template(
            'websocket/base_consumer.py.j2',
            'websocket/consumers.py',
            ctx
        )

        # Utils
        self.create_file_from_template(
            'websocket/utils.py.j2',
            'websocket/utils.py',
            ctx
        )

    def _generate_app_websockets(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate WebSocket consumers for an app."""
        app_name = app['name']

        # Analyze WebSocket requirements
        ws_config = self._analyze_websocket_requirements(app)

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': app.get('models', []),
            'project': schema['project'],
            'features': schema.get('features', {}),
            'consumers': ws_config['consumers'],
            'has_notifications': ws_config['has_notifications'],
            'has_presence': ws_config['has_presence'],
            'has_collaboration': ws_config['has_collaboration'],
        }

        # Generate consumers
        self.create_file_from_template(
            'app/websocket/consumers.py.j2',
            f'apps/{app_name}/consumers.py',
            ctx
        )

        # Generate routing
        self.create_file_from_template(
            'app/websocket/routing.py.j2',
            f'apps/{app_name}/routing.py',
            ctx
        )

        # Generate middleware if needed
        if ws_config['needs_custom_middleware']:
            self.create_file_from_template(
                'app/websocket/middleware.py.j2',
                f'apps/{app_name}/middleware.py',
                ctx
            )

    def _analyze_websocket_requirements(self, app: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze WebSocket requirements for an app."""
        config = {
            'consumers': [],
            'has_notifications': False,
            'has_presence': False,
            'has_collaboration': False,
            'needs_custom_middleware': False,
        }

        # Check app-level WebSocket config
        app_ws = app.get('websocket', {})
        config['has_notifications'] = app_ws.get('notifications', False)
        config['has_presence'] = app_ws.get('presence', False)
        config['has_collaboration'] = app_ws.get('collaboration', False)

        # Analyze each model
        for model in app.get('models', []):
            model_name = model['name']
            ws_config = model.get('websocket', {})

            if ws_config.get('enabled', False):
                consumer = {
                    'name': f"{model_name}Consumer",
                    'model_name': model_name,
                    'room_name': ws_config.get('room_name', f"{model_name.lower()}_updates"),
                    'events': ws_config.get('events', ['create', 'update', 'delete']),
                    'permissions': ws_config.get('permissions', []),
                    'authentication_required': ws_config.get('authentication_required', True),
                }

                # Add specific event handlers
                if 'create' in consumer['events']:
                    consumer['events'].append(f'{model_name.lower()}_created')
                if 'update' in consumer['events']:
                    consumer['events'].append(f'{model_name.lower()}_updated')
                if 'delete' in consumer['events']:
                    consumer['events'].append(f'{model_name.lower()}_deleted')

                config['consumers'].append(consumer)

        # Check if custom middleware is needed
        if any(c.get('permissions') for c in config['consumers']):
            config['needs_custom_middleware'] = True

        return config

    def _needs_websocket(self, app: Dict[str, Any]) -> bool:
        """Check if app needs WebSocket support."""
        # Check app-level config
        if app.get('websocket', {}).get('enabled', False):
            return True

        # Check model-level config
        for model in app.get('models', []):
            if model.get('websocket', {}).get('enabled', False):
                return True

        return False

    def _generate_client_code(self, schema: Dict[str, Any]) -> None:
        """Generate client-side WebSocket code."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema['apps'],
        }

        # JavaScript WebSocket client
        self.create_file_from_template(
            'websocket/client/websocket.js.j2',
            'static/js/websocket.js',
            ctx
        )

        # TypeScript definitions if needed
        if schema.get('features', {}).get('frontend', {}).get('typescript'):
            self.create_file_from_template(
                'websocket/client/websocket.d.ts.j2',
                'static/js/websocket.d.ts',
                ctx
            )

        # React hooks if React is used
        if schema.get('features', {}).get('frontend', {}).get('framework') == 'react':
            self.create_file_from_template(
                'websocket/client/useWebSocket.js.j2',
                'static/js/hooks/useWebSocket.js',
                ctx
            )

        # Example usage
        self.create_file_from_template(
            'websocket/client/example.html.j2',
            'templates/websocket_example.html',
            ctx
        )