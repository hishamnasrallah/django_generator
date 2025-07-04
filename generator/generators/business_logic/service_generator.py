"""
Service Layer Generator
Generates service layer with business logic
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class ServiceGenerator(BaseGenerator):
    """
    Generates service layer with:
    - Service classes for business logic
    - Repository pattern implementation
    - Domain events
    - Business rule validation
    - Transaction management
    """

    name = "ServiceGenerator"
    description = "Generates service layer components"
    version = "1.0.0"
    order = 65
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if service layer is needed."""
        return schema.get('features', {}).get('service_layer', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate service layer files."""
        self.generated_files = []

        # Create service directories
        self._create_service_directories(schema)

        # Generate base service components
        self._generate_base_services(schema)

        # Generate app-specific services
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_services(app, schema)

        # Generate domain events if needed
        if schema.get('features', {}).get('service_layer', {}).get('domain_events'):
            self._generate_domain_events(schema)

        return self.generated_files

    def _create_service_directories(self, schema: Dict[str, Any]) -> None:
        """Create service layer directory structure."""
        directories = [
            'core/services',
            'core/repositories',
            'core/domain',
            'core/domain/events',
            'core/domain/exceptions',
        ]

        for directory in directories:
            # Create __init__.py file in each directory
            self.create_file_from_template(
                'services/__init__.py.j2',
                f'{directory}/__init__.py',
                {}
            )

    def _generate_base_services(self, schema: Dict[str, Any]) -> None:
        """Generate base service components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # Base service class
        self.create_file_from_template(
            'services/base_service.py.j2',
            'core/services/base.py',
            ctx
        )

        # Base repository
        self.create_file_from_template(
            'services/base_repository.py.j2',
            'core/repositories/base.py',
            ctx
        )

        # Service exceptions
        self.create_file_from_template(
            'services/exceptions.py.j2',
            'core/domain/exceptions/__init__.py',
            ctx
        )

        # Service decorators
        self.create_file_from_template(
            'services/decorators.py.j2',
            'core/services/decorators.py',
            ctx
        )

        # Transaction manager
        self.create_file_from_template(
            'services/transaction.py.j2',
            'core/services/transaction.py',
            ctx
        )

    def _generate_app_services(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate services for an app."""
        app_name = app['name']

        # Create app service directory
        self.create_file_from_template(
            'services/__init__.py.j2',
            f'apps/{app_name}/services/__init__.py',
            {'app_name': app_name}
        )

        # Create app repository directory
        self.create_file_from_template(
            'services/__init__.py.j2',
            f'apps/{app_name}/repositories/__init__.py',
            {'app_name': app_name}
        )

        # Generate service for each model
        for model in app.get('models', []):
            self._generate_model_service(model, app, schema)
            self._generate_model_repository(model, app, schema)

        # Generate app-level service
        self._generate_app_level_service(app, schema)

    def _generate_model_service(self, model: Dict[str, Any], app: Dict[str, Any],
                                schema: Dict[str, Any]) -> None:
        """Generate service class for a model."""
        ctx = {
            'app_name': app['name'],
            'model': model,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'service_config': self._get_service_config(model),
        }

        self.create_file_from_template(
            'services/model_service.py.j2',
            f'apps/{app["name"]}/services/{model["name"].lower()}_service.py',
            ctx
        )

    def _generate_model_repository(self, model: Dict[str, Any], app: Dict[str, Any],
                                   schema: Dict[str, Any]) -> None:
        """Generate repository class for a model."""
        ctx = {
            'app_name': app['name'],
            'model': model,
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'services/model_repository.py.j2',
            f'apps/{app["name"]}/repositories/{model["name"].lower()}_repository.py',
            ctx
        )

    def _generate_app_level_service(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate app-level service orchestrating multiple model services."""
        ctx = {
            'app': app,
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'services/app_service.py.j2',
            f'apps/{app["name"]}/services/{app["name"]}_service.py',
            ctx
        )

    def _generate_domain_events(self, schema: Dict[str, Any]) -> None:
        """Generate domain event infrastructure."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema['apps'],
        }

        # Base event class
        self.create_file_from_template(
            'services/domain/base_event.py.j2',
            'core/domain/events/base.py',
            ctx
        )

        # Event dispatcher
        self.create_file_from_template(
            'services/domain/event_dispatcher.py.j2',
            'core/domain/events/dispatcher.py',
            ctx
        )

        # Event handlers
        self.create_file_from_template(
            'services/domain/event_handlers.py.j2',
            'core/domain/events/handlers.py',
            ctx
        )

        # Generate events for each app
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_events(app, schema)

    def _generate_app_events(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate domain events for an app."""
        ctx = {
            'app': app,
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'services/domain/app_events.py.j2',
            f'apps/{app["name"]}/events.py',
            ctx
        )

    def _get_service_config(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Get service configuration for a model."""
        config = {
            'use_repository': True,
            'use_events': False,
            'use_cache': False,
            'business_rules': [],
        }

        # Check model configuration
        if model.get('service'):
            config.update(model['service'])

        # Extract business rules from model
        if model.get('validation_rules'):
            config['business_rules'].extend(model['validation_rules'])

        return config