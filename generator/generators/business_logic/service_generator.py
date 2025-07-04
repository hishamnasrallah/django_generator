"""
Service Generator
Generates business logic service layer
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class ServiceGenerator(BaseGenerator):
    """
    Generates service layer with:
    - Service classes
    - DTOs (Data Transfer Objects)
    - Repository pattern
    - Business logic encapsulation
    """

    name = "ServiceGenerator"
    description = "Generates business logic service layer"
    version = "1.0.0"
    order = 60
    category = "business_logic"
    requires = {'ModelGenerator'}
    provides = {'ServiceGenerator', 'services'}
    tags = {'services', 'business_logic', 'architecture'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema needs service layer."""
        if not schema or not isinstance(schema, dict):
            return False

        # Check if service layer is enabled
        architecture = schema.get('architecture', {})
        if not architecture.get('patterns', {}).get('service_layer', True):
            return False

        # Check if any app has models that need services
        apps = schema.get('apps', [])
        for app in apps:
            if app and isinstance(app, dict):
                models = app.get('models', [])
                for model in models:
                    if model and isinstance(model, dict):
                        if model.get('services', {}).get('enabled', True):
                            return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate service layer files."""
        self.generated_files = []

        if not schema:
            logger.error("Schema is None or empty")
            return self.generated_files

        apps = schema.get('apps', [])
        if not apps:
            logger.warning("No apps found in schema")
            return self.generated_files

        for app in apps:
            if not app or not isinstance(app, dict):
                logger.warning("Skipping invalid app entry")
                continue

            if self._should_generate_services(app, schema):
                self._generate_app_services(app, schema)

        return self.generated_files

    def _should_generate_services(self, app: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Check if services should be generated for this app."""
        models = app.get('models', [])
        if not models:
            return False

        # Check if any model needs services
        for model in models:
            if model and isinstance(model, dict):
                services_config = model.get('services', {})
                if services_config.get('enabled', True):
                    return True

        return False

    def _generate_app_services(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate service layer for a single app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        # Create service directories
        service_dirs = [
            f'apps/{app_name}/services',
            f'apps/{app_name}/dto',
            f'apps/{app_name}/repositories',
        ]

        for dir_path in service_dirs:
            self.create_directory(dir_path)
            self.create_file(f"{dir_path}/__init__.py", "")

        # Get models that need services
        service_models = []
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                services_config = model.get('services', {})
                if services_config.get('enabled', True):
                    # Enhance service config
                    model['services'] = self._enhance_service_config(model, services_config)
                    service_models.append(model)

        if not service_models:
            return

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': service_models,
            'features': schema.get('features', {}),
            'imports': self._get_required_imports(service_models, schema),
        }

        # Generate DTOs
        self.create_file_from_template(
            'business_logic/services/dto.py.j2',
            f'apps/{app_name}/dto/dto.py',
            ctx
        )

        # Generate Repositories
        ctx['repository_models'] = [m for m in service_models if m.get('repository', {}).get('enabled', True)]
        if ctx['repository_models']:
            self.create_file_from_template(
                'business_logic/services/repository.py.j2',
                f'apps/{app_name}/repositories/repository.py',
                ctx
            )

        # Generate Services
        self.create_file_from_template(
            'business_logic/services/service.py.j2',
            f'apps/{app_name}/services/service.py',
            ctx
        )

        # Generate service __init__.py with exports
        self._generate_service_init(app_name, service_models)

    def _enhance_service_config(self, model: Dict[str, Any], services_config: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance service configuration with defaults."""
        enhanced = services_config.copy()

        # Default custom methods
        if 'custom_methods' not in enhanced:
            enhanced['custom_methods'] = []

        # Add common service methods based on model features
        if model.get('features', {}).get('soft_delete'):
            enhanced['custom_methods'].append({
                'name': 'restore',
                'params': ['id: int'],
                'return_type': 'bool',
                'description': f'Restore soft-deleted {model["name"]}',
                'implementation': 'return self.repository.restore(id)'
            })

        if model.get('features', {}).get('versioning'):
            enhanced['custom_methods'].append({
                'name': 'get_version_history',
                'params': ['id: int'],
                'return_type': 'List[Dict[str, Any]]',
                'description': f'Get version history for {model["name"]}',
                'implementation': 'return self.repository.get_version_history(id)'
            })

        # Default bulk operations
        if 'bulk_operations' not in enhanced:
            enhanced['bulk_operations'] = True

        # Default repository config
        if 'repository' not in model:
            model['repository'] = {
                'enabled': True,
                'cache_enabled': model.get('features', {}).get('caching', False),
                'custom_methods': []
            }

        # Add model-specific configurations
        enhanced['list_display_fields'] = enhanced.get('list_display_fields', self._get_list_fields(model))
        enhanced['filterable_fields'] = enhanced.get('filterable_fields', self._get_filterable_fields(model))

        return enhanced

    def _get_list_fields(self, model: Dict[str, Any]) -> List[str]:
        """Get fields suitable for list display."""
        fields = ['id']

        # Add common display fields
        field_names = [f.get('name') for f in model.get('fields', []) if f and isinstance(f, dict)]
        for field_name in ['name', 'title', 'code', 'status', 'created_at']:
            if field_name in field_names:
                fields.append(field_name)

        return fields[:5]  # Limit to 5 fields

    def _get_filterable_fields(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get fields suitable for filtering."""
        filterable = []

        for field in model.get('fields', []):
            if field and isinstance(field, dict):
                field_type = field.get('type')
                field_name = field.get('name')

                if field_type in ['CharField', 'TextField', 'EmailField']:
                    filterable.append({
                        'name': field_name,
                        'type': field_type,
                        'lookups': ['exact', 'icontains']
                    })
                elif field_type in ['IntegerField', 'DecimalField', 'FloatField']:
                    filterable.append({
                        'name': field_name,
                        'type': field_type,
                        'lookups': ['exact', 'gte', 'lte']
                    })
                elif field_type in ['DateField', 'DateTimeField']:
                    filterable.append({
                        'name': field_name,
                        'type': field_type,
                        'lookups': ['exact', 'gte', 'lte']
                    })
                elif field_type == 'BooleanField':
                    filterable.append({
                        'name': field_name,
                        'type': field_type,
                        'lookups': ['exact']
                    })

        return filterable

    def _get_required_imports(self, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get required imports for service layer."""
        imports = {
            'django': [],
            'third_party': [],
            'project': [],
            'python': ['from typing import Optional, List, Dict, Any, Tuple'],
        }

        features = schema.get('features', {})

        if features.get('celery', {}).get('enabled'):
            imports['third_party'].append('from celery import shared_task')

        if features.get('notifications', {}).get('enabled'):
            imports['project'].append('from ..notifications import NotificationService')

        if features.get('audit', {}).get('enabled'):
            imports['project'].append('from ..audit import AuditService')

        return imports

    def _generate_service_init(self, app_name: str, models: List[Dict[str, Any]]) -> None:
        """Generate __init__.py for services module."""
        content = f'"""Services for {app_name} app."""\n\n'

        # Import statements
        content += 'from .service import (\n'
        for model in models:
            content += f'    {model["name"]}Service,\n'
        content += f'    {NamingConventions.to_pascal_case(app_name)}ServiceFacade,\n'
        content += ')\n\n'

        # Export list
        content += '__all__ = [\n'
        for model in models:
            content += f'    \'{model["name"]}Service\',\n'
        content += f'    \'{NamingConventions.to_pascal_case(app_name)}ServiceFacade\',\n'
        content += ']\n'

        self.create_file(f'apps/{app_name}/services/__init__.py', content)