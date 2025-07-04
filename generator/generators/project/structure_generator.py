"""
Project Structure Generator
Creates the base Django project structure with all necessary files and directories
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import secrets

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class ProjectStructureGenerator(BaseGenerator):
    """
    Generates the complete Django project structure.

    Creates:
    - Project root files (README, requirements, etc.)
    - Django project directory with settings
    - Static and media directories
    - Docker configuration
    - CI/CD configuration
    - Documentation structure
    """

    name = "ProjectStructureGenerator"
    description = "Creates Django project structure"
    version = "1.0.0"
    order = 10  # Run first
    category = "project"
    provides = {'ProjectStructureGenerator', 'project_structure'}
    tags = {'project', 'structure', 'base'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """This generator always runs for any valid schema."""
        return 'project' in schema

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate project structure files."""
        self.generated_files = []
        project = schema.get('project', {})
        features = schema.get('features', {})

        # Validate project data
        if not project or not project.get('name'):
            raise ValueError("Project must have a 'name' field")

        # Generate project name variations
        project_name = project['name']
        project_title = NamingConventions().to_title_case(project_name)

        # Build context - ensure all nested dictionaries exist with safe defaults
        ctx = {
            'project': project,
            'project_name': project_name,
            'project_title': project_title,
            'features': self._ensure_features_structure(features),
            'apps': schema.get('apps', []),
            'python_version': project.get('python_version', '3.11'),
            'django_version': project.get('django_version', '4.2'),
            'secret_key': self._generate_secret_key(),
            'database_url': self._get_database_url(features.get('database', {}), project_name),
            'redis_url': 'redis://localhost:6379/0',
        }

        # Generate files
        self._generate_root_files(ctx)
        self._generate_requirements(ctx)
        self._generate_project_directory(ctx)
        self._generate_config_directory(ctx)
        self._generate_static_directories(ctx)

        # Optional components based on features
        if ctx['features'].get('deployment', {}).get('docker'):
            self._generate_docker_files(ctx)

        if ctx['features'].get('deployment', {}).get('ci_cd'):
            self._generate_ci_cd_files(ctx)

        if ctx['features'].get('docs', True):  # Default to including docs
            self._generate_documentation_structure(ctx)

        return self.generated_files

    def _ensure_features_structure(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all expected feature keys exist with proper defaults."""
        default_features = {
            'api': {
                'rest_framework': False,
                'graphql': False,
                'websockets': False,
                'versioning': None,
            },
            'authentication': {
                'jwt': False,
                'oauth2': {
                    'enabled': False,
                    'providers': []
                },
                'two_factor': False,
                'api_keys': False,
                'custom_user': False,
            },
            'database': {
                'engine': 'postgresql',
                'read_replica': False,
            },
            'performance': {
                'caching': {
                    'enabled': False,
                    'backend': 'redis'
                },
                'celery': False,
                'elasticsearch': False,
                'monitoring': False,
                'redis': False,
            },
            'deployment': {
                'docker': False,
                'kubernetes': False,
                'ci_cd': None,
                'hosting': None,
                'monitoring': False,
            },
            'enterprise': {
                'audit': False,
                'soft_delete': False,
                'multitenancy': False,
                'versioning': False,
            },
            'integrations': {
                'payment': None,
                'email': None,
                'sms': None,
                'storage': None,
                'aws': False,
                'sentry': False,
                'image_processing': False,
            },
            'testing': {
                'e2e': False,
            },
            'build': {
                'makefile': True,
            },
            'docs': True,
        }

        # Deep merge features with defaults
        return self._deep_merge(default_features, features)

    def _deep_merge(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = default.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _get_database_url(self, db_config: Dict[str, Any], project_name: str) -> str:
        """Generate appropriate database URL based on engine."""
        engine = db_config.get('engine', 'postgresql')

        if engine == 'postgresql':
            return f'postgresql://postgres:password@localhost:5432/{project_name}_db'
        elif engine == 'mysql':
            return f'mysql://root:password@localhost:3306/{project_name}_db'
        else:
            return 'sqlite:///db.sqlite3'

    def _generate_root_files(self, ctx: Dict[str, Any]) -> None:
        """Generate root project files."""
        # README.md
        self.create_file_from_template(
            'project/root/README.md.j2',
            'README.md',
            ctx
        )

        # .gitignore
        self.create_file_from_template(
            'project/root/gitignore.j2',
            '.gitignore',
            ctx
        )

        # .env.example
        self.create_file_from_template(
            'project/root/env.example.j2',
            '.env.example',
            ctx
        )

        # manage.py
        self.create_file_from_template(
            'project/root/manage.py.j2',
            'manage.py',
            ctx,
            executable=True
        )

        # Makefile - check feature safely
        if ctx.get('features', {}).get('build', {}).get('makefile', True):
            self.create_file_from_template(
                'project/root/Makefile.j2',
                'Makefile',
                ctx
            )

        # pyproject.toml
        self.create_file_from_template(
            'project/root/pyproject.toml.j2',
            'pyproject.toml',
            ctx
        )

        # setup.cfg
        self.create_file_from_template(
            'project/root/setup.cfg.j2',
            'setup.cfg',
            ctx
        )

        # .pre-commit-config.yaml
        self.create_file_from_template(
            'project/root/pre-commit-config.yaml.j2',
            '.pre-commit-config.yaml',
            ctx
        )

    def _generate_requirements(self, ctx: Dict[str, Any]) -> None:
        """Generate requirements files."""
        # Create requirements directory
        reqs_dir = 'requirements'

        # Base requirements
        self.create_file_from_template(
            'project/requirements/base.txt.j2',
            f'{reqs_dir}/base.txt',
            ctx
        )

        # Development requirements - fix the typo in template name
        self.create_file_from_template(
            'project/requirements/development.txt.j2',  # Fixed from development.text.j2
            f'{reqs_dir}/development.txt',
            ctx
        )

        # Production requirements
        self.create_file_from_template(
            'project/requirements/production.txt.j2',
            f'{reqs_dir}/production.txt',
            ctx
        )

        # Testing requirements
        self.create_file_from_template(
            'project/requirements/testing.txt.j2',
            f'{reqs_dir}/testing.txt',
            ctx
        )

    def _generate_project_directory(self, ctx: Dict[str, Any]) -> None:
        """Generate main Django project directory."""
        project_name = ctx['project_name']

        # __init__.py
        self.create_file(
            f'{project_name}/__init__.py',
            ''
        )

        # urls.py
        self.create_file_from_template(
            'project/django/urls.py.j2',
            f'{project_name}/urls.py',
            ctx
        )

        # wsgi.py
        self.create_file_from_template(
            'project/django/wsgi.py.j2',
            f'{project_name}/wsgi.py',
            ctx
        )

        # asgi.py
        if ctx['features'].get('api', {}).get('websockets'):
            self.create_file_from_template(
                'project/django/asgi.py.j2',
                f'{project_name}/asgi.py',
                ctx
            )

        # celery.py
        if ctx['features'].get('performance', {}).get('celery'):
            self.create_file_from_template(
                'project/django/celery.py.j2',
                f'{project_name}/celery.py',
                ctx
            )

    def _generate_config_directory(self, ctx: Dict[str, Any]) -> None:
        """Generate settings configuration."""
        project_name = ctx['project_name']
        config_dir = f'{project_name}/settings'

        # Settings __init__.py
        self.create_file_from_template(
            'project/settings/__init__.py.j2',
            f'{config_dir}/__init__.py',
            ctx
        )

        # Base settings
        self.create_file_from_template(
            'project/settings/base.py.j2',
            f'{config_dir}/base.py',
            ctx
        )

        # Development settings
        self.create_file_from_template(
            'project/settings/development.py.j2',
            f'{config_dir}/development.py',
            ctx
        )

        # Staging settings
        self.create_file_from_template(
            'project/settings/staging.py.j2',
            f'{config_dir}/staging.py',
            ctx
        )

        # Production settings
        self.create_file_from_template(
            'project/settings/production.py.j2',
            f'{config_dir}/production.py',
            ctx
        )

        # Testing settings
        self.create_file_from_template(
            'project/settings/testing.py.j2',
            f'{config_dir}/testing.py',
            ctx
        )

        # Logging configuration
        self.create_file_from_template(
            'project/settings/logging.py.j2',
            f'{config_dir}/logging.py',
            ctx
        )

    def _generate_static_directories(self, ctx: Dict[str, Any]) -> None:
        """Generate static and media directories."""
        # Static files
        static_dirs = [
            'static/css',
            'static/js',
            'static/images',
            'static/fonts',
        ]

        for dir_path in static_dirs:
            # Create .gitkeep to preserve empty directories
            self.create_file(
                f'{dir_path}/.gitkeep',
                ''
            )

        # Media files
        self.create_file(
            'media/.gitkeep',
            ''
        )

        # Templates
        self.create_file(
            'templates/base.html',
            self._get_base_template()
        )

    def _generate_docker_files(self, ctx: Dict[str, Any]) -> None:
        """Generate Docker configuration files."""
        # Dockerfile
        self.create_file_from_template(
            'project/docker/Dockerfile.j2',
            'Dockerfile',
            ctx
        )

        # docker-compose.yml
        self.create_file_from_template(
            'project/docker/docker-compose.yml.j2',
            'docker-compose.yml',
            ctx
        )

        # docker-compose.prod.yml
        self.create_file_from_template(
            'project/docker/docker-compose.prod.yml.j2',
            'docker-compose.prod.yml',
            ctx
        )

        # .dockerignore
        self.create_file_from_template(
            'project/docker/.dockerignore.j2',
            '.dockerignore',
            ctx
        )

        # Docker scripts
        docker_scripts = [
            ('docker/scripts/entrypoint.sh', 'project/docker/scripts/entrypoint.sh.j2'),
            ('docker/scripts/wait-for-it.sh', 'project/docker/scripts/wait-for-it.sh.j2'),
        ]

        for output_path, template_path in docker_scripts:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx,
                executable=True
            )

    def _generate_ci_cd_files(self, ctx: Dict[str, Any]) -> None:
        """Generate CI/CD configuration files."""
        ci_cd_type = ctx['features'].get('deployment', {}).get('ci_cd', 'github_actions')

        if ci_cd_type == 'github_actions':
            # GitHub Actions workflows
            workflows = [
                ('test.yml', 'Run Tests'),
                ('deploy.yml', 'Deploy to Production'),
                ('security.yml', 'Security Scan'),
            ]

            for filename, workflow_name in workflows:
                workflow_ctx = {**ctx, 'workflow_name': workflow_name}
                self.create_file_from_template(
                    f'project/ci_cd/github/{filename}.j2',
                    f'.github/workflows/{filename}',
                    workflow_ctx
                )

            # Dependabot config
            self.create_file_from_template(
                'project/ci_cd/github/dependabot.yml.j2',
                '.github/dependabot.yml',
                ctx
            )

        elif ci_cd_type == 'gitlab':
            # GitLab CI
            self.create_file_from_template(
                'project/ci_cd/gitlab-ci.yml.j2',
                '.gitlab-ci.yml',
                ctx
            )

        elif ci_cd_type == 'jenkins':
            # Jenkinsfile
            self.create_file_from_template(
                'project/ci_cd/Jenkinsfile.j2',
                'Jenkinsfile',
                ctx
            )

    def _generate_documentation_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate documentation structure."""
        docs_files = [
            ('docs/README.md', 'project/docs/README.md.j2'),
            ('docs/ARCHITECTURE.md', 'project/docs/ARCHITECTURE.md.j2'),
            ('docs/API.md', 'project/docs/API.md.j2'),
            ('docs/DEPLOYMENT.md', 'project/docs/DEPLOYMENT.md.j2'),
            ('docs/CONTRIBUTING.md', 'project/docs/CONTRIBUTING.md.j2'),
        ]

        for output_path, template_path in docs_files:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx
            )

        # API documentation config (if using DRF)
        if ctx['features'].get('api', {}).get('rest_framework'):
            self.create_file_from_template(
                'project/docs/swagger.yml.j2',
                'docs/api/swagger.yml',
                ctx
            )

    def _generate_secret_key(self) -> str:
        """Generate a secure Django secret key."""
        return secrets.token_urlsafe(50)

    def _get_base_template(self) -> str:
        """Get basic HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ project_title }}{% endblock %}</title>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    {% block extra_js %}{% endblock %}
</body>
</html>
'''