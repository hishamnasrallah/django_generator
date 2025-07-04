"""
JWT Authentication Generator
Generates JWT authentication using djangorestframework-simplejwt
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class JWTGenerator(BaseGenerator):
    """
    Generates JWT authentication with:
    - Token obtain/refresh views
    - Custom claims
    - Token blacklisting
    - User serializers
    - Authentication backends
    """

    name = "JWTGenerator"
    description = "Generates JWT authentication"
    version = "1.0.0"
    order = 70
    requires = {'RestAPIGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if JWT authentication is enabled."""
        return schema.get('features', {}).get('authentication', {}).get('jwt', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate JWT authentication files."""
        self.generated_files = []

        # Generate JWT configuration
        self._generate_jwt_config(schema)

        # Generate authentication views
        self._generate_auth_views(schema)

        # Generate serializers
        self._generate_auth_serializers(schema)

        # Generate middleware if needed
        if schema.get('features', {}).get('authentication', {}).get('jwt_cookie'):
            self._generate_jwt_middleware(schema)

        # Generate tests
        self._generate_jwt_tests(schema)

        return self.generated_files

    def _generate_jwt_config(self, schema: Dict[str, Any]) -> None:
        """Generate JWT configuration files."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'jwt_config': schema.get('features', {}).get('authentication', {}).get('jwt_config', {}),
        }

        # JWT settings
        self.create_file_from_template(
            'auth/jwt/settings.py.j2',
            'authentication/jwt_settings.py',
            ctx
        )

        # Custom token classes
        self.create_file_from_template(
            'auth/jwt/tokens.py.j2',
            'authentication/tokens.py',
            ctx
        )

        # JWT backends
        self.create_file_from_template(
            'auth/jwt/backends.py.j2',
            'authentication/backends.py',
            ctx
        )

    def _generate_auth_views(self, schema: Dict[str, Any]) -> None:
        """Generate authentication views."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'has_social_auth': bool(schema.get('features', {}).get('authentication', {}).get('oauth2')),
            'has_2fa': schema.get('features', {}).get('authentication', {}).get('two_factor', False),
        }

        # Auth views
        self.create_file_from_template(
            'auth/jwt/views.py.j2',
            'authentication/views.py',
            ctx
        )

        # Auth URLs
        self.create_file_from_template(
            'auth/jwt/urls.py.j2',
            'authentication/urls.py',
            ctx
        )

    def _generate_auth_serializers(self, schema: Dict[str, Any]) -> None:
        """Generate authentication serializers."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'user_model': self._get_user_model(schema),
        }

        self.create_file_from_template(
            'auth/jwt/serializers.py.j2',
            'authentication/serializers.py',
            ctx
        )

    def _generate_jwt_middleware(self, schema: Dict[str, Any]) -> None:
        """Generate JWT middleware for cookie-based auth."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'auth/jwt/middleware.py.j2',
            'authentication/jwt_middleware.py',
            ctx
        )

    def _generate_jwt_tests(self, schema: Dict[str, Any]) -> None:
        """Generate JWT authentication tests."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'auth/jwt/tests.py.j2',
            'authentication/tests/test_jwt.py',
            ctx
        )

    def _get_user_model(self, schema: Dict[str, Any]) -> str:
        """Get the user model name."""
        if schema.get('features', {}).get('authentication', {}).get('custom_user'):
            return 'User'
        return 'django.contrib.auth.models.User'