"""
Model Generator
Generates Django models with advanced features
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions
logger = logging.getLogger(__name__)


class ModelGenerator(BaseGenerator):
    """
    Generates Django models with:
    - Field definitions
    - Model methods and properties
    - Managers and QuerySets
    - State machines
    - Mixins and inheritance
    - Meta options
    """

    name = "ModelGenerator"
    description = "Generates Django models"
    version = "1.0.0"
    order = 20
    category = "app"
    provides = {'ModelGenerator', 'models'}
    tags = {'models', 'database', 'orm'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema has apps with models."""
        if not schema or not isinstance(schema, dict):
            return False

        apps = schema.get('apps', [])
        if not apps:
            return False

        # Check if any app has models
        for app in apps:
            if app and isinstance(app, dict) and app.get('models'):
                return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate model files for all apps."""
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

            if app.get('models'):
                self._generate_app_models(app, schema)

        return self.generated_files

    def _generate_app_models(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate models for a single app."""
        if not app:
            logger.error("App is None")
            return

        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        models = app.get('models', [])
        if not models:
            logger.warning(f"No models found for app '{app_name}'")
            return

        # Ensure schema has required structure
        if not schema:
            schema = {}

        # Prepare context with safe defaults
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema.get('project', {}),
            'features': schema.get('features', {}),
            'has_file_fields': self._has_file_fields(models),
            'has_json_fields': self._has_json_fields(models),
            'has_relationships': self._has_relationships(models),
            'imports': self._get_required_imports(models, schema),
        }

        # Generate main models.py
        self.create_file_from_template(
            'app/models/models.py.j2',
            f'apps/{app_name}/models.py',
            ctx
        )

        # Generate managers.py if needed
        if self._needs_custom_managers(models):
            self.create_file_from_template(
                'app/models/managers.py.j2',
                f'apps/{app_name}/managers.py',
                ctx
            )

        # Generate mixins.py if needed
        if self._needs_mixins(models, schema):
            self.create_file_from_template(
                'app/models/mixins.py.j2',
                f'apps/{app_name}/mixins.py',
                ctx
            )

        # Generate signals.py if needed
        if self._needs_signals(app):
            self.create_file_from_template(
                'app/models/signals.py.j2',
                f'apps/{app_name}/signals.py',
                ctx
            )

    def _has_file_fields(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has file/image fields."""
        if not models:
            return False

        for model in models:
            if not model or not isinstance(model, dict):
                continue

            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field or not isinstance(field, dict):
                    continue

                field_type = field.get('type', '')
                if field_type in ['FileField', 'ImageField']:
                    return True
        return False

    def _has_json_fields(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has JSON fields."""
        if not models:
            return False

        for model in models:
            if not model or not isinstance(model, dict):
                continue

            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field or not isinstance(field, dict):
                    continue

                if field.get('type') == 'JSONField':
                    return True
        return False

    def _has_relationships(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has relationship fields."""
        if not models:
            return False

        for model in models:
            if not model or not isinstance(model, dict):
                continue

            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field or not isinstance(field, dict):
                    continue

                field_type = field.get('type', '')
                if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    return True
        return False

    def _needs_custom_managers(self, models: List[Dict[str, Any]]) -> bool:
        """Check if custom managers are needed."""
        if not models:
            return False

        for model in models:
            if not model or not isinstance(model, dict):
                continue

            # Check for soft delete
            features = model.get('features', {})
            if features and features.get('soft_delete'):
                return True

            # Check for custom manager definitions
            if model.get('managers'):
                return True

            # Check for complex queries that benefit from custom manager
            fields = model.get('fields', [])
            if fields and len(fields) > 10:
                return True

        return False

    def _needs_mixins(self, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> bool:
        """Check if mixins file is needed."""
        if not schema:
            schema = {}

        features = schema.get('features', {})
        if not features:
            features = {}

        # Global features that require mixins
        enterprise = features.get('enterprise', {})
        if enterprise:
            if enterprise.get('audit'):
                return True
            if enterprise.get('soft_delete'):
                return True
            if enterprise.get('multitenancy'):
                return True

        # Model-specific features
        if models:
            for model in models:
                if not model or not isinstance(model, dict):
                    continue

                if model.get('mixins'):
                    return True
                if model.get('features'):
                    return True

        return False

    def _needs_signals(self, app: Dict[str, Any]) -> bool:
        """Check if signals are needed."""
        if not app or not isinstance(app, dict):
            return False

        # Check if app defines signals
        if app.get('signals'):
            return True

        # Check if any model needs signals
        models = app.get('models', [])
        if models:
            for model in models:
                if not model or not isinstance(model, dict):
                    continue

                # State machines often need signals
                if model.get('state_machine'):
                    return True

                # Audit features need signals
                features = model.get('features', {})
                if features and features.get('audit'):
                    return True

        return False

    def _get_required_imports(self, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Determine required imports based on models and features."""
        imports = {
            'django': ['from django.db import models'],
            'django_contrib': [],
            'third_party': [],
            'project': [],
            'python': [],
        }

        if not models:
            return imports

        # Check field types for special imports
        field_types = set()
        for model in models:
            if not model or not isinstance(model, dict):
                continue

            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field or not isinstance(field, dict):
                    continue

                field_type = field.get('type', '')
                if field_type:
                    field_types.add(field_type)

        # UUID fields
        if 'UUIDField' in field_types:
            imports['python'].append('import uuid')

        # Decimal fields
        if 'DecimalField' in field_types:
            imports['python'].append('from decimal import Decimal')

        # JSON fields
        if 'JSONField' in field_types:
            imports['django'].append('from django.contrib.postgres.fields import JSONField')

        # File fields
        if any(ft in field_types for ft in ['FileField', 'ImageField']):
            imports['django'].append('from django.core.files.storage import default_storage')

        # Validators
        imports['django'].append('from django.core.validators import MinValueValidator, MaxValueValidator')

        # User model
        if self._references_user_model(models):
            imports['django_contrib'].append('from django.contrib.auth import get_user_model')

        # Features
        if not schema:
            schema = {}

        features = schema.get('features', {})
        if not features:
            features = {}

        # State machines
        if any(model.get('state_machine') for model in models if model and isinstance(model, dict)):
            imports['third_party'].append('from django_fsm import FSMField, transition')

        # Enterprise features
        enterprise = features.get('enterprise', {})
        if enterprise:
            # Soft delete
            if enterprise.get('soft_delete'):
                imports['third_party'].append('from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE')

            # Audit
            if enterprise.get('audit'):
                imports['third_party'].append('from simple_history.models import HistoricalRecords')

            # Multi-tenancy
            if enterprise.get('multitenancy'):
                imports['third_party'].append('from django_tenants.models import TenantMixin')

        # Timezone support
        imports['django'].append('from django.utils import timezone')

        # Translation
        imports['django'].append('from django.utils.translation import gettext_lazy as _')

        return imports

    def _references_user_model(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model references the User model."""
        if not models:
            return False

        for model in models:
            if not model or not isinstance(model, dict):
                continue

            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field or not isinstance(field, dict):
                    continue

                field_type = field.get('type', '')
                if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    to_model = field.get('to', '')
                    if to_model and ('user' in to_model.lower() or to_model == 'auth.User'):
                        return True
        return False