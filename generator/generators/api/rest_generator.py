"""
REST API Generator
Generates Django REST Framework API components
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class RestAPIGenerator(BaseGenerator):
    """
    Generates REST API with:
    - ViewSets and Views
    - Serializers
    - URL patterns
    - Permissions
    - Filters
    - Pagination
    """

    name = "RestAPIGenerator"
    description = "Generates Django REST Framework API"
    version = "1.0.0"
    order = 25
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if REST API is enabled."""
        return schema.get('features', {}).get('api', {}).get('rest_framework', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate REST API files."""
        self.generated_files = []

        # Generate main API configuration
        self._generate_api_config(schema)

        # Generate versioning if enabled
        if schema.get('features', {}).get('api', {}).get('versioning'):
            self._generate_api_versioning(schema)

        # Generate common API components
        self._generate_common_components(schema)

        # Main API URLs
        self._generate_main_urls(schema)

        return self.generated_files

    def _generate_api_config(self, schema: Dict[str, Any]) -> None:
        """Generate API configuration files."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # API app __init__.py
        self.create_file_from_template(
            'api/__init__.py.j2',
            'api/__init__.py',
            ctx
        )

        # API settings
        self.create_file_from_template(
            'api/settings.py.j2',
            'api/settings.py',
            ctx
        )

        # Exception handlers
        self.create_file_from_template(
            'api/exceptions.py.j2',
            'api/exceptions.py',
            ctx
        )

        # Response formatters
        self.create_file_from_template(
            'api/responses.py.j2',
            'api/responses.py',
            ctx
        )

    def _generate_api_versioning(self, schema: Dict[str, Any]) -> None:
        """Generate API versioning structure."""
        versioning_scheme = schema.get('features', {}).get('api', {}).get('versioning', 'URLPathVersioning')
        versions = ['v1']  # Default to v1

        ctx = {
            'project': schema['project'],
            'versions': versions,
            'versioning_scheme': versioning_scheme,
            'apps': schema['apps'],
        }

        for version in versions:
            # Version __init__.py
            self.create_file_from_template(
                'api/version/__init__.py.j2',
                f'api/{version}/__init__.py',
                {'version': version}
            )

            # Version URLs
            self.create_file_from_template(
                'api/version/urls.py.j2',
                f'api/{version}/urls.py',
                {**ctx, 'version': version}
            )

    def _generate_common_components(self, schema: Dict[str, Any]) -> None:
        """Generate common API components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # Base permissions
        self.create_file_from_template(
            'api/permissions.py.j2',
            'api/permissions.py',
            ctx
        )

        # Base pagination
        self.create_file_from_template(
            'api/pagination.py.j2',
            'api/pagination.py',
            ctx
        )

        # Base filters
        self.create_file_from_template(
            'api/filters.py.j2',
            'api/filters.py',
            ctx
        )

        # Base serializers
        self.create_file_from_template(
            'api/serializers.py.j2',
            'api/base_serializers.py',
            ctx
        )

        # Throttling
        self.create_file_from_template(
            'api/throttling.py.j2',
            'api/throttling.py',
            ctx
        )

        # Mixins
        self.create_file_from_template(
            'api/mixins.py.j2',
            'api/mixins.py',
            ctx
        )

    def _generate_main_urls(self, schema: Dict[str, Any]) -> None:
        """Generate main API URL configuration."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema['apps'],
            'has_versioning': schema.get('features', {}).get('api', {}).get('versioning', False),
        }

        self.create_file_from_template(
            'api/urls.py.j2',
            'api/urls.py',
            ctx
        )