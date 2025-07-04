"""
OAuth Generator
Generates OAuth2 authentication using django-allauth
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class OAuthGenerator(BaseGenerator):
    """
    Generates OAuth2 authentication with:
    - Social authentication providers
    - OAuth2 callbacks
    - User profile integration
    - Custom adapters
    """

    name = "OAuthGenerator"
    description = "Generates OAuth2 authentication"
    version = "1.0.0"
    order = 75
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if OAuth2 authentication is enabled."""
        return bool(schema.get('features', {}).get('authentication', {}).get('oauth2'))

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate OAuth2 authentication files."""
        self.generated_files = []

        oauth_config = schema.get('features', {}).get('authentication', {}).get('oauth2', {})

        if oauth_config:
            # Generate OAuth configuration
            self._generate_oauth_config(schema, oauth_config)

            # Generate adapters for each provider
            self._generate_provider_adapters(schema, oauth_config)

            # Generate views and URLs
            self._generate_oauth_views(schema, oauth_config)

            # Generate templates
            self._generate_oauth_templates(schema, oauth_config)

        return self.generated_files

    def _generate_oauth_config(self, schema: Dict[str, Any], oauth_config: Dict[str, Any]) -> None:
        """Generate OAuth configuration files."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'providers': oauth_config.get('providers', []),
            'oauth_settings': oauth_config.get('settings', {}),
        }

        # OAuth settings
        self.create_file_from_template(
            'auth/oauth/settings.py.j2',
            'authentication/oauth_settings.py',
            ctx
        )

        # Social auth pipeline
        self.create_file_from_template(
            'auth/oauth/pipeline.py.j2',
            'authentication/oauth_pipeline.py',
            ctx
        )

    def _generate_provider_adapters(self, schema: Dict[str, Any], oauth_config: Dict[str, Any]) -> None:
        """Generate adapters for each OAuth provider."""
        providers = oauth_config.get('providers', [])

        for provider in providers:
            ctx = {
                'project': schema['project'],
                'provider': provider,
                'provider_name': provider.title(),
                'features': schema.get('features', {}),
            }

            # Provider adapter
            self.create_file_from_template(
                'auth/oauth/provider_adapter.py.j2',
                f'authentication/adapters/{provider}_adapter.py',
                ctx
            )

        # Generate base adapter
        ctx = {
            'project': schema['project'],
            'providers': providers,
        }

        self.create_file_from_template(
            'auth/oauth/base_adapter.py.j2',
            'authentication/adapters/base.py',
            ctx
        )

    def _generate_oauth_views(self, schema: Dict[str, Any], oauth_config: Dict[str, Any]) -> None:
        """Generate OAuth views and URLs."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'providers': oauth_config.get('providers', []),
        }

        # OAuth views
        self.create_file_from_template(
            'auth/oauth/views.py.j2',
            'authentication/oauth_views.py',
            ctx
        )

        # OAuth URLs
        self.create_file_from_template(
            'auth/oauth/urls.py.j2',
            'authentication/oauth_urls.py',
            ctx
        )

    def _generate_oauth_templates(self, schema: Dict[str, Any], oauth_config: Dict[str, Any]) -> None:
        """Generate OAuth templates."""
        ctx = {
            'project': schema['project'],
            'providers': oauth_config.get('providers', []),
        }

        # Login template
        self.create_file_from_template(
            'auth/oauth/templates/login.html.j2',
            'templates/authentication/oauth_login.html',
            ctx
        )

        # Connection template
        self.create_file_from_template(
            'auth/oauth/templates/connections.html.j2',
            'templates/authentication/social_connections.html',
            ctx
        )