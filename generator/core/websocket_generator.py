"""
WebSocket Generator
Generates Django Channels WebSocket consumers and routing
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class WebSocketGenerator(BaseGenerator):
    """
    Generates WebSocket implementation using Django Channels.
    
    Features:
    - WebSocket consumers for real-time updates
    - Channel routing configuration
    - Authentication middleware
    - Group management
    - Message broadcasting
    """
    
    name = "WebSocketGenerator"
    description = "Generates Django Channels WebSocket consumers"
    version = "1.0.0"
    order = 40
    requires = {'ModelGenerator'}
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if WebSockets are enabled."""
        return schema.get('features', {}).get('api', {}).get('websockets', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate WebSocket files for all apps."""
        self.generated_files = []
        
        # Generate main routing
        self._generate_main_routing(schema)
        
        # Generate app-specific WebSocket files
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_websockets(app, schema)
        
        return self.generated_files
    
    def _generate_main_routing(self, schema: Dict[str, Any]) -> None:
        """Generate main WebSocket routing file."""
        ctx = {
            'project': schema['project'],
            'apps': schema.get('apps', []),
            'features': schema.get('features', {}),
        }
        
        self.create_file_from_template(
            'app/websocket/routing.py.j2',
            f"{schema['project']['name']}/routing.py",
            ctx
        )
        
        # Generate middleware
        self.create_file_from_template(
            'app/websocket/middleware.py.j2',
            f"{schema['project']['name']}/websocket_middleware.py",
            ctx
        )
    
    def _generate_app_websockets(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate WebSocket files for a single app."""
        app_name = app['name']
        models = app.get('models', [])
        
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'consumers': self._generate_consumers(models),
            'events': self._generate_events(models),
        }
        
        # Generate consumers
        self.create_file_from_template(
            'app/websocket/consumers.py.j2',
            f'apps/{app_name}/consumers.py',
            ctx
        )
        
        # Generate routing for app
        self.create_file_from_template(
            'app/websocket/routing.py.j2',
            f'apps/{app_name}/routing.py',
            ctx
        )
    
    def _generate_consumers(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate WebSocket consumers for models."""
        consumers = []
        
        for model in models:
            if model.get('api', {}).get('websockets', True):
                consumer = {
                    'name': f"{model['name']}Consumer",
                    'model_name': model['name'],
                    'room_name': f"{model['name'].lower()}_updates",
                    'events': [
                        'model_created',
                        'model_updated',
                        'model_deleted',
                    ],
                    'permissions': model.get('api', {}).get('permissions', []),
                    'authentication_required': True,
                }
                
                consumers.append(consumer)
        
        return consumers
    
    def _generate_events(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate WebSocket events for models."""
        events = []
        
        for model in models:
            if model.get('api', {}).get('websockets', True):
                model_events = [
                    {
                        'name': f"{model['name'].lower()}_created",
                        'model_name': model['name'],
                        'event_type': 'create',
                        'data_fields': ['id', 'created_at'],
                    },
                    {
                        'name': f"{model['name'].lower()}_updated",
                        'model_name': model['name'],
                        'event_type': 'update',
                        'data_fields': ['id', 'updated_at'],
                    },
                    {
                        'name': f"{model['name'].lower()}_deleted",
                        'model_name': model['name'],
                        'event_type': 'delete',
                        'data_fields': ['id'],
                    },
                ]
                
                events.extend(model_events)
        
        return events