"""
Documentation Generator
Generates API documentation using drf-spectacular and other tools
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class DocumentationGenerator(BaseGenerator):
    """
    Generates API documentation including:
    - OpenAPI/Swagger configuration
    - API documentation templates
    - Postman collections
    - API versioning docs
    """

    name = "DocumentationGenerator"
    description = "Generates API documentation"
    version = "1.0.0"
    order = 50
    requires = {'RestAPIGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if API documentation is needed."""
        return (
                schema.get('features', {}).get('api', {}).get('rest_framework', False) or
                schema.get('features', {}).get('api', {}).get('graphql', False)
        )

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate API documentation files."""
        self.generated_files = []

        features = schema.get('features', {})

        if features.get('api', {}).get('rest_framework'):
            self._generate_rest_api_docs(schema)

        if features.get('api', {}).get('graphql'):
            self._generate_graphql_docs(schema)

        # Generate general API documentation
        self._generate_api_readme(schema)
        self._generate_api_examples(schema)

        return self.generated_files

    def _generate_rest_api_docs(self, schema: Dict[str, Any]) -> None:
        """Generate REST API documentation."""
        ctx = {
            'project': schema['project'],
            'apps': schema['apps'],
            'features': schema.get('features', {}),
            'api_version': schema.get('features', {}).get('api', {}).get('version', 'v1'),
        }

        # Generate OpenAPI schema customization
        self.create_file_from_template(
            'api/openapi_schema.py.j2',
            'core/api/schema.py',
            ctx
        )

        # Generate API documentation templates
        self.create_file_from_template(
            'api/docs/index.md.j2',
            'docs/api/index.md',
            ctx
        )

        # Generate Postman collection
        self.create_file_from_template(
            'api/postman_collection.json.j2',
            'docs/api/postman_collection.json',
            ctx
        )

        # Generate API client examples
        for language in ['python', 'javascript', 'curl']:
            self.create_file_from_template(
                f'api/examples/{language}_client.j2',
                f'docs/api/examples/{language}_client.{self._get_extension(language)}',
                ctx
            )

    def _generate_graphql_docs(self, schema: Dict[str, Any]) -> None:
        """Generate GraphQL documentation."""
        ctx = {
            'project': schema['project'],
            'apps': schema['apps'],
            'features': schema.get('features', {}),
        }

        # Generate GraphQL schema documentation
        self.create_file_from_template(
            'graphql/schema_docs.md.j2',
            'docs/graphql/schema.md',
            ctx
        )

        # Generate GraphQL query examples
        self.create_file_from_template(
            'graphql/query_examples.graphql.j2',
            'docs/graphql/examples.graphql',
            ctx
        )

    def _generate_api_readme(self, schema: Dict[str, Any]) -> None:
        """Generate main API README."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema['apps'],
        }

        self.create_file_from_template(
            'api/README.md.j2',
            'docs/api/README.md',
            ctx
        )

    def _generate_api_examples(self, schema: Dict[str, Any]) -> None:
        """Generate API usage examples."""
        for app in schema.get('apps', []):
            if not app.get('models'):
                continue

            ctx = {
                'app': app,
                'project': schema['project'],
                'features': schema.get('features', {}),
            }

            self.create_file_from_template(
                'api/app_examples.md.j2',
                f'docs/api/{app["name"]}_examples.md',
                ctx
            )

    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            'python': 'py',
            'javascript': 'js',
            'curl': 'sh',
        }
        return extensions.get(language, 'txt')