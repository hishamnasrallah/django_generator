"""
Permission Generator
Generates custom permission classes and role-based access control
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class PermissionGenerator(BaseGenerator):
    """
    Generates permission system with:
    - Custom permission classes
    - Role-based permissions
    - Object-level permissions
    - Permission mixins
    - Permission decorators
    """

    name = "PermissionGenerator"
    description = "Generates permission system"
    version = "1.0.0"
    order = 80
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if custom permissions are needed."""
        # Check if any model has custom permissions
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                if model.get('permissions'):
                    return True

        # Check if role-based permissions are enabled
        return schema.get('features', {}).get('authentication', {}).get('roles', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate permission files."""
        self.generated_files = []

        # Generate base permission classes
        self._generate_base_permissions(schema)

        # Generate role system if enabled
        if schema.get('features', {}).get('authentication', {}).get('roles'):
            self._generate_role_system(schema)

        # Generate app-specific permissions
        for app in schema.get('apps', []):
            if self._needs_permissions(app):
                self._generate_app_permissions(app, schema)

        return self.generated_files

    def _generate_base_permissions(self, schema: Dict[str, Any]) -> None:
        """Generate base permission classes."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # Base permission classes
        self.create_file_from_template(
            'auth/permissions/base.py.j2',
            'core/permissions.py',
            ctx
        )

        # Permission mixins
        self.create_file_from_template(
            'auth/permissions/mixins.py.j2',
            'core/permission_mixins.py',
            ctx
        )

        # Permission decorators
        self.create_file_from_template(
            'auth/permissions/decorators.py.j2',
            'core/permission_decorators.py',
            ctx
        )

    def _generate_role_system(self, schema: Dict[str, Any]) -> None:
        """Generate role-based permission system."""
        role_config = schema.get('features', {}).get('authentication', {}).get('role_config', {})

        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'roles': role_config.get('roles', ['admin', 'user']),
            'role_hierarchy': role_config.get('hierarchy', {}),
        }

        # Role model
        self.create_file_from_template(
            'auth/permissions/role_model.py.j2',
            'authentication/models/role.py',
            ctx
        )

        # Role permissions
        self.create_file_from_template(
            'auth/permissions/role_permissions.py.j2',
            'authentication/role_permissions.py',
            ctx
        )

        # Role admin
        self.create_file_from_template(
            'auth/permissions/role_admin.py.j2',
            'authentication/admin/role_admin.py',
            ctx
        )

    def _generate_app_permissions(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate app-specific permissions."""
        app_name = app['name']

        # Collect all permissions
        permissions = self._collect_permissions(app)

        ctx = {
            'app_name': app_name,
            'models': app.get('models', []),
            'permissions': permissions,
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        # App permissions
        self.create_file_from_template(
            'app/permissions.py.j2',
            f'apps/{app_name}/permissions.py',
            ctx
        )

        # Permission tests
        self.create_file_from_template(
            'app/tests/test_permissions.py.j2',
            f'apps/{app_name}/tests/test_permissions.py',
            ctx
        )

    def _needs_permissions(self, app: Dict[str, Any]) -> bool:
        """Check if app needs custom permissions."""
        for model in app.get('models', []):
            if model.get('permissions') or model.get('api', {}).get('permissions'):
                return True
        return False

    def _collect_permissions(self, app: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all permissions for an app."""
        permissions = []

        for model in app.get('models', []):
            model_name = model['name']

            # Model-level permissions
            for perm in model.get('permissions', []):
                permissions.append({
                    'model': model_name,
                    'codename': perm.get('codename'),
                    'name': perm.get('name'),
                    'type': 'model',
                })

            # API permissions
            api_perms = model.get('api', {}).get('permissions', [])
            if api_perms:
                for perm in api_perms:
                    if isinstance(perm, dict):
                        permissions.append({
                            'model': model_name,
                            'codename': perm.get('codename'),
                            'name': perm.get('name'),
                            'type': 'api',
                        })

        return permissions