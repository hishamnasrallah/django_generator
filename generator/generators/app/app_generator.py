"""
App Generator
Generates Django app structure and configuration
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class AppGenerator(BaseGenerator):
    """
    Generates Django app structure with:
    - App configuration (apps.py)
    - Init files
    - URL configuration
    - App-specific settings
    - Management commands structure
    """

    name = "AppGenerator"
    description = "Generates Django app structure"
    version = "1.0.0"
    order = 10
    category = "app"
    provides = {'AppGenerator', 'app_structure'}
    tags = {'app', 'structure', 'configuration'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema has apps to generate."""
        if not schema or not isinstance(schema, dict):
            return False

        apps = schema.get('apps', [])
        return bool(apps) and any(app and isinstance(app, dict) for app in apps)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate app structure for all apps."""
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

            self._generate_app_structure(app, schema)

        # Generate project-level app configurations
        self._generate_project_app_config(apps, schema)

        return self.generated_files

    def _generate_app_structure(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate structure for a single app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        # Create app directories
        app_dirs = [
            f'apps/{app_name}',
            f'apps/{app_name}/migrations',
            f'apps/{app_name}/management',
            f'apps/{app_name}/management/commands',
            f'apps/{app_name}/templatetags',
            f'apps/{app_name}/static/{app_name}',
            f'apps/{app_name}/static/{app_name}/css',
            f'apps/{app_name}/static/{app_name}/js',
            f'apps/{app_name}/static/{app_name}/img',
            f'apps/{app_name}/templates/{app_name}',
            f'apps/{app_name}/fixtures',
            f'apps/{app_name}/tests',
        ]

        # Add additional directories based on features
        features = schema.get('features', {})
        if features.get('api', {}).get('enabled'):
            app_dirs.extend([
                f'apps/{app_name}/api',
                f'apps/{app_name}/api/v1',
            ])

        if features.get('graphql', {}).get('enabled'):
            app_dirs.append(f'apps/{app_name}/graphql')

        if features.get('websocket', {}).get('enabled'):
            app_dirs.append(f'apps/{app_name}/consumers')

        # Create directories
        for dir_path in app_dirs:
            self.create_directory(dir_path)

        # Generate files
        self._generate_init_files(app_name, app_dirs)
        self._generate_apps_py(app, schema)
        self._generate_app_urls(app, schema)
        self._generate_app_config(app, schema)

    def _generate_init_files(self, app_name: str, directories: List[str]) -> None:
        """Generate __init__.py files for all directories."""
        for directory in directories:
            # Skip static and templates directories
            if 'static' in directory or 'templates' in directory or 'fixtures' in directory:
                continue

            init_path = f"{directory}/__init__.py"

            # Special content for certain __init__ files
            if directory.endswith('templatetags'):
                content = '"""Template tags for {} app."""\n'.format(app_name)
            elif directory.endswith('tests'):
                content = '"""Tests for {} app."""\n'.format(app_name)
            else:
                content = ''

            self.create_file(init_path, content)

    def _generate_apps_py(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate apps.py configuration."""
        app_name = app.get('name')

        ctx = {
            'app_name': app_name,
            'app_config': app.get('config', {}),
            'verbose_name': app.get('verbose_name', NamingConventions.to_title_case(app_name)),
            'features': schema.get('features', {}),
            'has_signals': self._has_signals(app),
            'has_checks': app.get('checks', False),
            'has_middleware': self._has_middleware(app, schema),
        }

        self.create_file_from_template(
            'app/apps.py.j2',
            f'apps/{app_name}/apps.py',
            ctx
        )

    def _generate_app_urls(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate URL configuration for app."""
        app_name = app.get('name')
        features = schema.get('features', {})

        # Check what URL patterns are needed
        has_views = bool(app.get('views', []))
        has_api = features.get('api', {}).get('enabled') and bool(app.get('models', []))
        has_graphql = features.get('graphql', {}).get('enabled')
        has_webhooks = features.get('webhooks', {}).get('enabled')

        if not (has_views or has_api or has_graphql or has_webhooks):
            # No URLs needed
            return

        ctx = {
            'app_name': app_name,
            'views': app.get('views', []),
            'has_api': has_api,
            'has_graphql': has_graphql,
            'has_webhooks': has_webhooks,
            'api_version': features.get('api', {}).get('version', 'v1'),
            'models': app.get('models', []),
        }

        self.create_file_from_template(
            'app/urls.py.j2',
            f'apps/{app_name}/urls.py',
            ctx
        )

    def _generate_app_config(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate app-specific configuration files."""
        app_name = app.get('name')

        # Generate constants.py if app has constants
        if app.get('constants'):
            ctx = {
                'app_name': app_name,
                'constants': app['constants'],
            }
            self.create_file_from_template(
                'app/constants.py.j2',
                f'apps/{app_name}/constants.py',
                ctx
            )

        # Generate middleware.py if app has middleware
        if self._has_middleware(app, schema):
            ctx = {
                'app_name': app_name,
                'middleware': app.get('middleware', []),
                'features': schema.get('features', {}),
            }
            self.create_file_from_template(
                'app/middleware.py.j2',
                f'apps/{app_name}/middleware.py',
                ctx
            )

        # Generate context_processors.py if needed
        if app.get('context_processors'):
            ctx = {
                'app_name': app_name,
                'processors': app['context_processors'],
            }
            self.create_file_from_template(
                'app/context_processors.py.j2',
                f'apps/{app_name}/context_processors.py',
                ctx
            )

    def _generate_project_app_config(self, apps: List[Dict[str, Any]], schema: Dict[str, Any]) -> None:
        """Generate project-level app configuration."""
        # Generate apps/__init__.py with app registry
        ctx = {
            'apps': [app['name'] for app in apps if app and isinstance(app, dict) and app.get('name')],
            'project_name': schema.get('project', {}).get('name', 'project'),
        }

        self.create_file_from_template(
            'project/apps_init.py.j2',
            'apps/__init__.py',
            ctx
        )

    def _has_signals(self, app: Dict[str, Any]) -> bool:
        """Check if app uses signals."""
        if app.get('signals'):
            return True

        # Check if any model has signals
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                if model.get('signals'):
                    return True

        return False

    def _has_middleware(self, app: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Check if app has middleware."""
        if app.get('middleware'):
            return True

        # Check features that might need middleware
        features = schema.get('features', {})
        if features.get('multitenancy', {}).get('enabled'):
            return True

        return False