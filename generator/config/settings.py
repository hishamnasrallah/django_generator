"""
Settings Module
Configuration management for Django Enhanced Generator
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import yaml
import json
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class GeneratorSettings:
    """Generator configuration settings."""

    # Python settings
    python_version: str = "3.11"
    python_formatter: str = "black"

    # Django settings
    django_version: str = "4.2"
    django_settings_module: str = "settings"

    # Database settings
    default_database: str = "postgresql"
    database_settings: Dict[str, Any] = field(default_factory=lambda: {
        "postgresql": {
            "ENGINE": "django.db.backends.postgresql",
            "PORT": 5432,
        },
        "mysql": {
            "ENGINE": "django.db.backends.mysql",
            "PORT": 3306,
        },
        "sqlite": {
            "ENGINE": "django.db.backends.sqlite3",
        }
    })

    # API settings
    api_framework: str = "rest_framework"
    api_version_format: str = "v{version}"
    default_pagination_size: int = 20

    # Code generation settings
    line_length: int = 88
    indent_size: int = 4
    use_tabs: bool = False
    trailing_comma: bool = True
    quote_style: str = "double"  # single or double

    # File naming
    use_src_layout: bool = False
    apps_directory: str = "apps"

    # Template settings
    template_engine: str = "jinja2"
    template_dirs: List[str] = field(default_factory=list)

    # Feature defaults
    default_features: Dict[str, Any] = field(default_factory=lambda: {
        "api": {
            "rest_framework": True,
            "graphql": False,
            "websockets": False,
        },
        "authentication": {
            "jwt": True,
            "oauth2": False,
            "two_factor": False,
        },
        "database": {
            "migrations": True,
            "seeds": True,
        },
        "testing": {
            "framework": "pytest",
            "coverage": True,
            "factories": True,
        },
        "deployment": {
            "docker": True,
            "kubernetes": False,
            "ci_cd": "github_actions",
        }
    })

    # Security settings
    security_middleware: List[str] = field(default_factory=lambda: [
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ])

    # Performance settings
    enable_caching: bool = True
    cache_backend: str = "redis"
    enable_compression: bool = True

    # Development settings
    debug_toolbar: bool = True
    silk_profiling: bool = False

    # Documentation settings
    generate_docs: bool = True
    docs_format: str = "markdown"
    api_docs_tool: str = "swagger"

    # Third-party integrations
    integrations: Dict[str, Any] = field(default_factory=dict)

    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)


class Settings:
    """
    Settings manager for Django Enhanced Generator.

    Loads settings from:
    1. Default settings
    2. Environment variables
    3. Configuration files
    4. Command line arguments
    """

    def __init__(self, config_file: Optional[str] = None):
        self._settings = GeneratorSettings()
        self._config_file = config_file
        self._env_prefix = "DJANGO_GEN_"

        # Load settings in order of precedence
        self._load_defaults()
        self._load_from_file()
        self._load_from_env()

    def _load_defaults(self) -> None:
        """Load default settings."""
        # Default settings are already in GeneratorSettings dataclass
        pass

    def _load_from_file(self) -> None:
        """Load settings from configuration file."""
        if not self._config_file:
            # Look for default config files
            for config_name in ['.django-gen.yml', '.django-gen.yaml', '.django-gen.json', 'pyproject.toml']:
                if Path(config_name).exists():
                    self._config_file = config_name
                    break

        if not self._config_file or not Path(self._config_file).exists():
            return

        config_path = Path(self._config_file)

        try:
            if config_path.suffix in ['.yml', '.yaml']:
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                with open(config_path) as f:
                    config_data = json.load(f)
            elif config_path.suffix == '.toml':
                import toml
                with open(config_path) as f:
                    toml_data = toml.load(f)
                    config_data = toml_data.get('tool', {}).get('django-gen', {})
            else:
                return

            # Update settings
            self._update_settings(config_data)

        except Exception as e:
            print(f"Warning: Failed to load config file {config_path}: {e}")

    def _load_from_env(self) -> None:
        """Load settings from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                setting_name = key[len(self._env_prefix):].lower()

                # Convert environment variable to appropriate type
                if value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif ',' in value:
                    value = [v.strip() for v in value.split(',')]

                # Handle nested settings (using __ as separator)
                if '__' in setting_name:
                    parts = setting_name.split('__')
                    self._set_nested(parts, value)
                else:
                    if hasattr(self._settings, setting_name):
                        setattr(self._settings, setting_name, value)

    def _update_settings(self, config_data: Dict[str, Any]) -> None:
        """Update settings from configuration data."""
        for key, value in config_data.items():
            if hasattr(self._settings, key):
                current_value = getattr(self._settings, key)

                # Merge dictionaries
                if isinstance(current_value, dict) and isinstance(value, dict):
                    current_value.update(value)
                # Replace lists
                elif isinstance(current_value, list) and isinstance(value, list):
                    setattr(self._settings, key, value)
                # Set other values
                else:
                    setattr(self._settings, key, value)
            else:
                # Store unknown settings in custom
                self._settings.custom[key] = value

    def _set_nested(self, parts: List[str], value: Any) -> None:
        """Set nested setting value."""
        obj = self._settings

        # Navigate to parent
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return

        # Set value
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
        elif isinstance(obj, dict):
            obj[parts[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value.

        Supports dot notation for nested values.
        Example: settings.get('default_features.api.rest_framework')
        """
        parts = key.split('.')
        obj = self._settings

        try:
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj[part]
                else:
                    obj = getattr(obj, part)
            return obj
        except (AttributeError, KeyError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set setting value.

        Supports dot notation for nested values.
        """
        parts = key.split('.')

        if len(parts) == 1:
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
            else:
                self._settings.custom[key] = value
        else:
            self._set_nested(parts, value)

    def update(self, settings_dict: Dict[str, Any]) -> None:
        """Update multiple settings at once."""
        self._update_settings(settings_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            k: v for k, v in self._settings.__dict__.items()
            if not k.startswith('_')
        }

    def save(self, file_path: str) -> None:
        """Save current settings to file."""
        path = Path(file_path)
        settings_dict = self.to_dict()

        if path.suffix in ['.yml', '.yaml']:
            with open(path, 'w') as f:
                yaml.dump(settings_dict, f, default_flow_style=False)
        elif path.suffix == '.json':
            with open(path, 'w') as f:
                json.dump(settings_dict, f, indent=2)

    @property
    def python_version(self) -> str:
        return self._settings.python_version

    @property
    def django_version(self) -> str:
        return self._settings.django_version

    @property
    def default_database(self) -> str:
        return self._settings.default_database

    @property
    def apps_directory(self) -> str:
        return self._settings.apps_directory

    @property
    def template_dirs(self) -> List[str]:
        return self._settings.template_dirs

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to settings object."""
        return getattr(self._settings, name)


class TemplateSettings:
    """Settings specific to template rendering."""

    def __init__(self, base_settings: Settings):
        self.base_settings = base_settings

    def get_context(self) -> Dict[str, Any]:
        """Get template context with all settings."""
        return {
            'settings': self.base_settings.to_dict(),
            'python_version': self.base_settings.python_version,
            'django_version': self.base_settings.django_version,
            'database_engine': self.base_settings.default_database,
            'api_framework': self.base_settings.api_framework,
            'use_docker': self.base_settings.get('default_features.deployment.docker', True),
            'use_kubernetes': self.base_settings.get('default_features.deployment.kubernetes', False),
        }


@lru_cache(maxsize=1)
def get_default_settings() -> Settings:
    """Get default settings instance (cached)."""
    return Settings()


def create_project_config(project_name: str, output_path: str = '.django-gen.yml') -> None:
    """
    Create a project-specific configuration file.

    Args:
        project_name: Name of the Django project
        output_path: Path to save configuration file
    """
    config = {
        'project_name': project_name,
        'python_version': '3.11',
        'django_version': '4.2',
        'default_database': 'postgresql',
        'apps_directory': 'apps',
        'default_features': {
            'api': {
                'rest_framework': True,
                'graphql': False,
                'websockets': False,
            },
            'authentication': {
                'jwt': True,
                'oauth2': False,
            },
            'deployment': {
                'docker': True,
                'kubernetes': False,
            }
        },
        'custom': {
            'company_name': 'Your Company',
            'support_email': 'support@example.com',
        }
    }

    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"Created configuration file: {output_path}")