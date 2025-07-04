"""
Serializer Generator
Generates Django REST Framework serializers with advanced features
"""
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class SerializerGenerator(BaseGenerator):
    """
    Generates DRF serializers with:
    - ModelSerializer for CRUD operations
    - Nested serializers for relationships
    - Custom field serializers
    - Validation methods
    - Dynamic fields
    - Read/Write serializers
    """

    name = "SerializerGenerator"
    description = "Generates Django REST Framework serializers"
    version = "1.0.0"
    order = 30
    requires = {'ModelGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if REST API is enabled."""
        if not schema:
            return False
        features = schema.get('features', {})
        if not features:
            return False
        api_config = features.get('api', {})
        if not api_config:
            return False
        return api_config.get('rest_framework', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate serializer files for all apps."""
        self.generated_files = []

        if not schema:
            return self.generated_files

        apps = schema.get('apps', [])
        if not apps:
            return self.generated_files

        for app in apps:
            if not app:
                continue
            if app.get('models'):
                self._generate_app_serializers(app, schema)

        return self.generated_files

    def _generate_app_serializers(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate serializers for a single app."""
        if not app:
            return

        app_name = app.get('name', '')
        if not app_name:
            return

        models = app.get('models', [])
        if not models:
            return

        # Filter out None or invalid models
        valid_models = [m for m in models if m and m.get('name')]
        if not valid_models:
            return

        # Analyze relationships
        relationships = self._analyze_relationships(valid_models, schema)

        # Prepare context with safe defaults
        ctx = {
            'app_name': app_name,
            'models': valid_models,
            'project': schema.get('project', {}),
            'features': schema.get('features', {}),
            'relationships': relationships,
            'imports': self._get_required_imports(valid_models, schema),
            'has_nested': self._has_nested_serializers(valid_models),
            'has_file_uploads': self._has_file_uploads(valid_models),
            'custom_serializers': self._get_custom_serializers(app),
        }

        # Generate main serializers.py
        self.create_file_from_template(
            'app/api/serializers.py.j2',
            f'apps/{app_name}/serializers.py',
            ctx
        )

        # Generate validators.py if needed
        if self._needs_validators(app):
            self.create_file_from_template(
                'app/api/validators.py.j2',
                f'apps/{app_name}/validators.py',
                ctx
            )

        # Generate fields.py for custom fields if needed
        if self._needs_custom_fields(valid_models):
            self.create_file_from_template(
                'app/api/fields.py.j2',
                f'apps/{app_name}/fields.py',
                ctx
            )

    def _analyze_relationships(self, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze model relationships for serializer generation."""
        relationships = {
            'forward': {},  # ForeignKey, OneToOne
            'reverse': {},  # Reverse FK, reverse OneToOne
            'many_to_many': {},
            'circular': [],  # Circular dependencies
        }

        if not models or not schema:
            return relationships

        # Build model registry
        all_models = {}
        all_apps = schema.get('apps', [])
        if all_apps:
            for app in all_apps:
                if not app:
                    continue
                app_name = app.get('name', '')
                if not app_name:
                    continue
                app_models = app.get('models', [])
                if not app_models:
                    continue

                for model in app_models:
                    if not model:
                        continue
                    model_name = model.get('name', '')
                    if not model_name:
                        continue
                    full_name = f"{app_name}.{model_name}"
                    all_models[full_name] = model
                    all_models[model_name] = model  # Short name

        # Analyze each model
        for model in models:
            if not model:
                continue

            model_name = model.get('name', '')
            if not model_name:
                continue

            relationships['forward'][model_name] = []
            relationships['reverse'][model_name] = []
            relationships['many_to_many'][model_name] = []

            # Check fields - ensure fields exist
            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field:
                    continue

                field_type = field.get('type', '')
                field_name = field.get('name', '')

                if not field_type or not field_name:
                    continue

                if field_type in ['ForeignKey', 'OneToOneField']:
                    to_model = field.get('to', '')
                    if to_model and to_model != 'self':
                        relationships['forward'][model_name].append({
                            'field': field_name,
                            'to_model': to_model,
                            'type': field_type,
                            'related_name': field.get('related_name'),
                        })

                elif field_type == 'ManyToManyField':
                    to_model = field.get('to', '')
                    if to_model and to_model != 'self':
                        relationships['many_to_many'][model_name].append({
                            'field': field_name,
                            'to_model': to_model,
                            'through': field.get('through'),
                            'related_name': field.get('related_name'),
                        })

        # Find reverse relationships
        forward_rels = relationships.get('forward', {})
        if forward_rels:
            for model_name, forwards in forward_rels.items():
                if not forwards:
                    continue
                for rel in forwards:
                    if not rel:
                        continue
                    to_model = rel.get('to_model', '')
                    if not to_model:
                        continue
                    to_model_name = to_model.split('.')[-1]  # Get model name
                    if to_model_name in relationships['reverse']:
                        relationships['reverse'][to_model_name].append({
                            'from_model': model_name,
                            'field': rel.get('field', ''),
                            'type': rel.get('type', ''),
                            'related_name': rel.get('related_name') or f"{model_name.lower()}_set",
                        })

        # Detect circular dependencies
        relationships['circular'] = self._detect_circular_dependencies(relationships)

        return relationships

    def _detect_circular_dependencies(self, relationships: Dict[str, Any]) -> List[tuple]:
        """Detect circular dependencies between models."""
        circular = []

        if not relationships:
            return circular

        def has_path(from_model: str, to_model: str, visited: Set[str]) -> bool:
            if from_model == to_model and len(visited) > 0:
                return True
            if from_model in visited:
                return False

            visited.add(from_model)

            # Check forward relationships
            forward_rels = relationships.get('forward', {})
            if forward_rels:
                model_rels = forward_rels.get(from_model, [])
                if model_rels:
                    for rel in model_rels:
                        if not rel:
                            continue
                        related = rel.get('to_model', '')
                        if not related:
                            continue
                        related_name = related.split('.')[-1]
                        if has_path(related_name, to_model, visited.copy()):
                            return True

            return False

        # Check all model pairs
        forward_keys = list(relationships.get('forward', {}).keys())
        for i, model1 in enumerate(forward_keys):
            for model2 in forward_keys[i+1:]:
                if has_path(model1, model2, set()) and has_path(model2, model1, set()):
                    circular.append((model1, model2))

        return circular

    def _has_nested_serializers(self, models: List[Dict[str, Any]]) -> bool:
        """Check if nested serializers are needed."""
        if not models:
            return False

        for model in models:
            if not model:
                continue

            # Check if model has relationships
            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field:
                    continue
                field_type = field.get('type', '')
                if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    return True

            # Check API configuration
            api_config = model.get('api', {})
            if api_config and api_config.get('nested_serializers'):
                return True

        return False

    def _has_file_uploads(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has file upload fields."""
        if not models:
            return False

        for model in models:
            if not model:
                continue
            fields = model.get('fields', [])
            if not fields:
                continue
            for field in fields:
                if not field:
                    continue
                field_type = field.get('type', '')
                if field_type in ['FileField', 'ImageField']:
                    return True
        return False

    def _needs_validators(self, app: Dict[str, Any]) -> bool:
        """Check if custom validators are needed."""
        if not app:
            return False

        # Check for custom validation in models
        models = app.get('models', [])
        if not models:
            return False

        for model in models:
            if not model:
                continue

            if model.get('validation_rules'):
                return True

            # Check for complex validation in fields
            fields = model.get('fields', [])
            if fields:
                for field in fields:
                    if field and field.get('validators'):
                        return True

        return False

    def _needs_custom_fields(self, models: List[Dict[str, Any]]) -> bool:
        """Check if custom serializer fields are needed."""
        if not models:
            return False

        for model in models:
            if not model:
                continue

            # Check for fields that need custom serialization
            fields = model.get('fields', [])
            if not fields:
                continue

            for field in fields:
                if not field:
                    continue

                field_type = field.get('type', '')

                # JSON fields often need custom serialization
                if field_type == 'JSONField':
                    return True

                # Fields with complex choices
                choices = field.get('choices')
                if choices and isinstance(choices, dict):
                    return True

                # Computed fields
                if field.get('computed'):
                    return True

        return False

    def _get_custom_serializers(self, app: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get custom serializer definitions from app config."""
        custom_serializers = []

        if not app:
            return custom_serializers

        # Check for API-specific serializers
        api_config = app.get('api', {})
        if not api_config:
            return custom_serializers

        # List serializers
        list_serializers = api_config.get('list_serializers', [])
        if list_serializers:
            for model_name in list_serializers:
                custom_serializers.append({
                    'name': f"{model_name}ListSerializer",
                    'type': 'list',
                    'model': model_name,
                })

        # Detail serializers
        detail_serializers = api_config.get('detail_serializers', [])
        if detail_serializers:
            for model_name in detail_serializers:
                custom_serializers.append({
                    'name': f"{model_name}DetailSerializer",
                    'type': 'detail',
                    'model': model_name,
                })

        # Create/Update serializers
        write_serializers = api_config.get('write_serializers', [])
        if write_serializers:
            for model_name in write_serializers:
                custom_serializers.append({
                    'name': f"{model_name}WriteSerializer",
                    'type': 'write',
                    'model': model_name,
                })

        return custom_serializers

    def _get_required_imports(self, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Determine required imports for serializers."""
        imports = {
            'rest_framework': [
                'from rest_framework import serializers',
            ],
            'django': [],
            'app': [],
            'project': [],
            'python': [],
        }

        if not models:
            return imports

        # Check for specific field types
        field_types = set()
        for model in models:
            if not model:
                continue
            fields = model.get('fields', [])
            if not fields:
                continue
            for field in fields:
                if field:
                    field_type = field.get('type', '')
                    if field_type:
                        field_types.add(field_type)

        # File uploads
        if any(ft in field_types for ft in ['FileField', 'ImageField']):
            imports['rest_framework'].append('from rest_framework.fields import FileField, ImageField')

        # Decimal fields
        if 'DecimalField' in field_types:
            imports['python'].append('from decimal import Decimal')

        # JSON fields
        if 'JSONField' in field_types:
            imports['rest_framework'].append('from rest_framework.fields import JSONField')

        # Validators
        imports['django'].append('from django.core.exceptions import ValidationError')
        imports['rest_framework'].append('from rest_framework.validators import UniqueValidator')

        # Transactions
        imports['django'].append('from django.db import transaction')

        # Models import - only include valid model names
        model_names = []
        for model in models:
            if model and model.get('name'):
                model_names.append(model.get('name'))

        if model_names:
            imports['app'].append(f"from .models import {', '.join(model_names)}")

        # Custom fields
        if self._needs_custom_fields(models):
            imports['app'].append('from .fields import *')

        # Features
        if schema:
            features = schema.get('features', {})
            if features:
                auth = features.get('authentication', {})
                if auth and auth.get('jwt'):
                    imports['rest_framework'].append('from rest_framework_simplejwt.serializers import TokenObtainPairSerializer')

        # Nested serializers
        if self._has_nested_serializers(models):
            imports['rest_framework'].append('from rest_framework.serializers import SerializerMethodField')

        return imports