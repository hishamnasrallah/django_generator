"""
GraphQL Generator
Generates GraphQL schema, types, queries, and mutations
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class GraphQLGenerator(BaseGenerator):
    """
    Generates GraphQL API with:
    - Schema definition
    - Object types
    - Query and mutation resolvers
    - Subscriptions
    - Custom scalars
    - DataLoader integration
    """

    name = "GraphQLGenerator"
    description = "Generates GraphQL API"
    version = "1.0.0"
    order = 35
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if GraphQL is enabled."""
        return schema.get('features', {}).get('api', {}).get('graphql', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate GraphQL files."""
        self.generated_files = []

        # Generate main schema
        self._generate_main_schema(schema)

        # Generate app-specific GraphQL files
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_graphql(app, schema)

        # Generate GraphQL utilities
        self._generate_graphql_utils(schema)

        return self.generated_files

    def _generate_main_schema(self, schema: Dict[str, Any]) -> None:
        """Generate main GraphQL schema."""
        ctx = {
            'project': schema['project'],
            'apps': schema['apps'],
            'features': schema.get('features', {}),
        }

        # Main schema file
        self.create_file_from_template(
            'graphql/main_schema.py.j2',
            f'{schema["project"]["name"]}/schema.py',
            ctx
        )

        # GraphQL URLs
        self.create_file_from_template(
            'graphql/urls.py.j2',
            'graphql/urls.py',
            ctx
        )

        # Custom scalars
        if self._needs_custom_scalars(schema):
            self.create_file_from_template(
                'graphql/scalars.py.j2',
                'graphql/scalars.py',
                ctx
            )

        # Middleware
        self.create_file_from_template(
            'graphql/middleware.py.j2',
            'graphql/middleware.py',
            ctx
        )

    def _generate_app_graphql(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate GraphQL files for an app."""
        app_name = app['name']

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': app.get('models', []),
            'project': schema['project'],
            'features': schema.get('features', {}),
            'types': self._generate_type_definitions(app['models']),
            'has_subscriptions': self._has_subscriptions(app),
            'has_file_uploads': self._has_file_uploads(app['models']),
        }

        # Generate GraphQL module files
        self.create_file_from_template(
            'app/graphql/__init__.py.j2',
            f'apps/{app_name}/graphql/__init__.py',
            {'app_name': app_name}
        )

        # Types
        self.create_file_from_template(
            'app/graphql/types.py.j2',
            f'apps/{app_name}/graphql/types.py',
            ctx
        )

        # Queries
        self.create_file_from_template(
            'app/graphql/queries.py.j2',
            f'apps/{app_name}/graphql/queries.py',
            ctx
        )

        # Mutations
        self.create_file_from_template(
            'app/graphql/mutations.py.j2',
            f'apps/{app_name}/graphql/mutations.py',
            ctx
        )

        # Schema
        self.create_file_from_template(
            'app/graphql/schema.py.j2',
            f'apps/{app_name}/graphql/schema.py',
            ctx
        )

        # Subscriptions if needed
        if ctx['has_subscriptions']:
            self.create_file_from_template(
                'app/graphql/subscriptions.py.j2',
                f'apps/{app_name}/graphql/subscriptions.py',
                ctx
            )

        # DataLoaders for optimization
        if self._needs_dataloaders(app['models']):
            self.create_file_from_template(
                'app/graphql/dataloaders.py.j2',
                f'apps/{app_name}/graphql/dataloaders.py',
                ctx
            )

    def _generate_graphql_utils(self, schema: Dict[str, Any]) -> None:
        """Generate GraphQL utility files."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # Authentication
        if schema.get('features', {}).get('authentication', {}).get('jwt'):
            self.create_file_from_template(
                'graphql/auth.py.j2',
                'graphql/auth.py',
                ctx
            )

        # Permissions
        self.create_file_from_template(
            'graphql/permissions.py.j2',
            'graphql/permissions.py',
            ctx
        )

        # Error handling
        self.create_file_from_template(
            'graphql/errors.py.j2',
            'graphql/errors.py',
            ctx
        )

        # Testing utilities
        self.create_file_from_template(
            'graphql/test_utils.py.j2',
            'graphql/test_utils.py',
            ctx
        )

    def _generate_type_definitions(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate type definitions for models."""
        types = []

        for model in models:
            type_def = {
                'name': f"{model['name']}Type",
                'model_name': model['name'],
                'fields': model.get('fields', []),
                'filters': self._get_filterable_fields(model),
                'interfaces': [],
            }

            # Add interfaces
            if model.get('features', {}).get('timestamps'):
                type_def['interfaces'].append('graphene.relay.Node')

            types.append(type_def)

        return types

    def _get_filterable_fields(self, model: Dict[str, Any]) -> List[str]:
        """Get fields that can be filtered."""
        filterable_types = ['CharField', 'IntegerField', 'BooleanField', 'DateTimeField']
        fields = []

        for field in model.get('fields', []):
            if field and field.get('type') in filterable_types and not field.get('auto_now_add'):
                field_name = field.get('name')
                if field_name:
                    fields.append(field_name)

        return fields

    def _has_subscriptions(self, app: Dict[str, Any]) -> bool:
        """Check if app needs subscriptions."""
        return (
                (app and app.get('graphql', {}).get('subscriptions', False)) or
                (app and any(model and model.get('graphql', {}).get('subscriptions', False)
                             for model in app.get('models', [])))
        )

    def _has_file_uploads(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has file upload fields."""
        for model in models:
            for field in model.get('fields', []):
                if field['type'] in ['FileField', 'ImageField']:
                    return True
        return False

    def _needs_dataloaders(self, models: List[Dict[str, Any]]) -> bool:
        """Check if DataLoaders are needed."""
        # Need DataLoaders if there are relationships
        for model in models:
            for field in model.get('fields', []):
                if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    return True
        return False

    def _needs_custom_scalars(self, schema: Dict[str, Any]) -> bool:
        """Check if custom scalars are needed."""
        # Check for special field types across all models
        special_types = ['JSONField', 'DecimalField', 'UUIDField']

        for app in schema.get('apps', []):
            for model in app.get('models', []):
                for field in model.get('fields', []):
                    if field['type'] in special_types:
                        return True

        return False