"""
Model Generator
Generates Django models with advanced features
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


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

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema has apps with models."""
        return bool(schema.get('apps'))

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate model files for all apps."""
        self.generated_files = []

        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_models(app, schema)

        return self.generated_files

    def _generate_app_models(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate models for a single app."""
        app_name = app['name']
        models = app.get('models', [])

        if not models:
            return

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
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
        for model in models:
            for field in model.get('fields', []):
                if field['type'] in ['FileField', 'ImageField']:
                    return True
        return False

    def _has_json_fields(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has JSON fields."""
        for model in models:
            for field in model.get('fields', []):
                if field['type'] == 'JSONField':
                    return True
        return False

    def _has_relationships(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has relationship fields."""
        for model in models:
            for field in model.get('fields', []):
                if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    return True
        return False

    def _needs_custom_managers(self, models: List[Dict[str, Any]]) -> bool:
        """Check if custom managers are needed."""
        for model in models:
            # Check for soft delete
            if model.get('features', {}).get('soft_delete'):
                return True
            # Check for custom manager definitions
            if model.get('managers'):
                return True
            # Check for complex queries that benefit from custom manager
            if len(model.get('fields', [])) > 10:
                return True
        return False

    def _needs_mixins(self, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> bool:
        """Check if mixins file is needed."""
        features = schema.get('features', {})

        # Global features that require mixins
        if features.get('enterprise', {}).get('audit'):
            return True
        if features.get('enterprise', {}).get('soft_delete'):
            return True
        if features.get('enterprise', {}).get('multitenancy'):
            return True

        # Model-specific features
        for model in models:
            if model.get('mixins'):
                return True
            if model.get('features'):
                return True

        return False

    def _needs_signals(self, app: Dict[str, Any]) -> bool:
        """Check if signals are needed."""
        # Check if app defines signals
        if app.get('signals'):
            return True

        # Check if any model needs signals
        for model in app.get('models', []):
            # State machines often need signals
            if model.get('state_machine'):
                return True
            # Audit features need signals
            if model.get('features', {}).get('audit'):
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

        # Check field types for special imports
        field_types = set()
        for model in models:
            for field in model.get('fields', []):
                field_types.add(field['type'])

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
        features = schema.get('features', {})

        # State machines
        if any(model.get('state_machine') for model in models):
            imports['third_party'].append('from django_fsm import FSMField, transition')

        # Soft delete
        if features.get('enterprise', {}).get('soft_delete'):
            imports['third_party'].append('from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE')

        # Audit
        if features.get('enterprise', {}).get('audit'):
            imports['third_party'].append('from simple_history.models import HistoricalRecords')

        # Multi-tenancy
        if features.get('enterprise', {}).get('multitenancy'):
            imports['third_party'].append('from django_tenants.models import TenantMixin')

        # Timezone support
        imports['django'].append('from django.utils import timezone')

        # Translation
        imports['django'].append('from django.utils.translation import gettext_lazy as _')

        return imports

    def _references_user_model(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model references the User model."""
        for model in models:
            for field in model.get('fields', []):
                if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    to_model = field.get('to', '')
                    if 'user' in to_model.lower() or to_model == 'auth.User':
                        return True
        return False