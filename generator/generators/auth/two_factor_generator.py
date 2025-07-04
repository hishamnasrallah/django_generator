"""
Two-Factor Authentication Generator
Generates 2FA support using django-two-factor-auth
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class TwoFactorGenerator(BaseGenerator):
    """
    Generates two-factor authentication with:
    - TOTP support
    - SMS authentication
    - Backup codes
    - QR code generation
    - Recovery flows
    """

    name = "TwoFactorGenerator"
    description = "Generates two-factor authentication"
    version = "1.0.0"
    order = 85
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if 2FA is enabled."""
        return schema.get('features', {}).get('authentication', {}).get('two_factor', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate 2FA files."""
        self.generated_files = []

        two_fa_config = schema.get('features', {}).get('authentication', {}).get('two_factor_config', {})

        # Generate 2FA configuration
        self._generate_2fa_config(schema, two_fa_config)

        # Generate views and forms
        self._generate_2fa_views(schema, two_fa_config)

        # Generate templates
        self._generate_2fa_templates(schema, two_fa_config)

        # Generate middleware if needed
        if two_fa_config.get('enforce_for_staff'):
            self._generate_2fa_middleware(schema, two_fa_config)

        return self.generated_files

    def _generate_2fa_config(self, schema: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Generate 2FA configuration files."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'methods': config.get('methods', ['totp']),
            'backup_codes': config.get('backup_codes', True),
            'remember_device': config.get('remember_device', True),
        }

        # 2FA settings
        self.create_file_from_template(
            'auth/2fa/settings.py.j2',
            'authentication/two_factor_settings.py',
            ctx
        )

        # 2FA models
        if config.get('custom_models'):
            self.create_file_from_template(
                'auth/2fa/models.py.j2',
                'authentication/two_factor_models.py',
                ctx
            )

    def _generate_2fa_views(self, schema: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Generate 2FA views and forms."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'methods': config.get('methods', ['totp']),
            'has_sms': 'sms' in config.get('methods', []),
            'has_email': 'email' in config.get('methods', []),
        }

        # 2FA views
        self.create_file_from_template(
            'auth/2fa/views.py.j2',
            'authentication/two_factor_views.py',
            ctx
        )

        # 2FA forms
        self.create_file_from_template(
            'auth/2fa/forms.py.j2',
            'authentication/two_factor_forms.py',
            ctx
        )

        # 2FA URLs
        self.create_file_from_template(
            'auth/2fa/urls.py.j2',
            'authentication/two_factor_urls.py',
            ctx
        )

    def _generate_2fa_templates(self, schema: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Generate 2FA templates."""
        ctx = {
            'project': schema['project'],
            'methods': config.get('methods', ['totp']),
        }

        templates = [
            ('setup.html', 'Setup 2FA'),
            ('verify.html', 'Verify 2FA'),
            ('backup_codes.html', 'Backup Codes'),
            ('disable.html', 'Disable 2FA'),
        ]

        for template_name, title in templates:
            self.create_file_from_template(
                f'auth/2fa/templates/{template_name}.j2',
                f'templates/two_factor/{template_name}',
                {**ctx, 'title': title}
            )

    def _generate_2fa_middleware(self, schema: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Generate 2FA enforcement middleware."""
        ctx = {
            'project': schema['project'],
            'enforce_for_staff': config.get('enforce_for_staff', False),
            'enforce_for_superuser': config.get('enforce_for_superuser', True),
            'grace_period': config.get('grace_period', 30),
        }

        self.create_file_from_template(
            'auth/2fa/middleware.py.j2',
            'authentication/two_factor_middleware.py',
            ctx
        )