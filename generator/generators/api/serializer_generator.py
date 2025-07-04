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
        return schema.get('features', {}).get('api', {}).get('rest_framework', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate serializer files for all apps."""
        self.generated_files = []

        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_serializers(app, schema)

        return self.generated_files

    def _generate_app_serializers(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate serializers for a single app."""
        app_name = app['name']
        models = app.get('models', [])

        if not models:
            return

        # Analyze relationships
        relationships = self._analyze_relationships(models, schema)

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'relationships': relationships,
            'imports': self._get_required_imports(models, schema),
            'has_nested': self._has_nested_serializers(models),
            'has_file_uploads': self._has_file_uploads(models),
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
        if self._needs_custom_fields(models):
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

        # Build model registry
        all_models = {}
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                full_name = f"{app['name']}.{model['name']}"
                all_models[full_name] = model
                all_models[model['name']] = model  # Short name

        # Analyze each model
        for model in models:
            model_name = model['name']
            relationships['forward'][model_name] = []
            relationships['reverse'][model_name] = []
            relationships['many_to_many'][model_name] = []

            # Check fields - ensure fields exist
            fields = model.get('fields')
            if not fields:
                continue
            for field in fields:
                field_type = field['type']

                if field_type in ['ForeignKey', 'OneToOneField']:
                    to_model = field.get('to', '')
                    if to_model and to_model != 'self':
                        relationships['forward'][model_name].append({
                            'field': field['name'],
                            'to_model': to_model,
                            'type': field_type,
                            'related_name': field.get('related_name'),
                        })

                elif field_type == 'ManyToManyField':
                    to_model = field.get('to', '')
                    if to_model and to_model != 'self':
                        relationships['many_to_many'][model_name].append({
                            'field': field['name'],
                            'to_model': to_model,
                            'through': field.get('through'),
                            'related_name': field.get('related_name'),
                        })

        # Find reverse relationships
        for model_name, forwards in relationships['forward'].items():
            for rel in forwards:
                to_model = rel['to_model'].split('.')[-1]  # Get model name
                if to_model in relationships['reverse']:
                    relationships['reverse'][to_model].append({
                        'from_model': model_name,
                        'field': rel['field'],
                        'type': rel['type'],
                        'related_name': rel.get('related_name') or f"{model_name.lower()}_set",
                    })

        # Detect circular dependencies
        relationships['circular'] = self._detect_circular_dependencies(relationships)

        return relationships

    def _detect_circular_dependencies(self, relationships: Dict[str, Any]) -> List[tuple]:
        """Detect circular dependencies between models."""
        circular = []

        def has_path(from_model: str, to_model: str, visited: Set[str]) -> bool:
            if from_model == to_model and len(visited) > 0:
                return True
            if from_model in visited:
                return False

            visited.add(from_model)

            # Check forward relationships
            for rel in relationships['forward'].get(from_model, []):
                related = rel['to_model'].split('.')[-1]
                if has_path(related, to_model, visited.copy()):
                    return True

            return False

        # Check all model pairs
        models = list(relationships['forward'].keys())
        for i, model1 in enumerate(models):
            for model2 in models[i+1:]:
                if has_path(model1, model2, set()) and has_path(model2, model1, set()):
                    circular.append((model1, model2))

        return circular

    def _has_nested_serializers(self, models: List[Dict[str, Any]]) -> bool:
        """Check if nested serializers are needed."""
        for model in models:
            # Check if model has relationships
            fields = model.get('fields')
            if not fields:
                continue
            for field in fields:
                if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    return True

            # Check API configuration
            if model.get('api', {}).get('nested_serializers'):
                return True

        return False

    def _has_file_uploads(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has file upload fields."""
        for model in models:
            fields = model.get('fields')
            if not fields:
                continue
            for field in fields:
                if field['type'] in ['FileField', 'ImageField']:
                    return True
        return False

    def _needs_validators(self, app: Dict[str, Any]) -> bool:
        """Check if custom validators are needed."""
        # Check for custom validation in models
        for model in app.get('models', []):
            if model.get('validation_rules'):
                return True

            # Check for complex validation in fields
            for field in model.get('fields', []):
                if field.get('validators'):
                    return True

        return False

    def _needs_custom_fields(self, models: List[Dict[str, Any]]) -> bool:
        """Check if custom serializer fields are needed."""
        for model in models:
            # Check for fields that need custom serialization
            fields = model.get('fields')
            if not fields:
                continue
            for field in fields:
                # JSON fields often need custom serialization
                if field['type'] == 'JSONField':
                    return True

                # Fields with complex choices
                if field.get('choices') and isinstance(field['choices'], dict):
                    return True

                # Computed fields
                if field.get('computed'):
                    return True

        return False

    def _get_custom_serializers(self, app: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get custom serializer definitions from app config."""
        custom_serializers = []

        # Check for API-specific serializers
        api_config = app.get('api', {})

        # List serializers
        if api_config.get('list_serializers'):
            for model_name in api_config['list_serializers']:
                custom_serializers.append({
                    'name': f"{model_name}ListSerializer",
                    'type': 'list',
                    'model': model_name,
                })

        # Detail serializers
        if api_config.get('detail_serializers'):
            for model_name in api_config['detail_serializers']:
                custom_serializers.append({
                    'name': f"{model_name}DetailSerializer",
                    'type': 'detail',
                    'model': model_name,
                })

        # Create/Update serializers
        if api_config.get('write_serializers'):
            for model_name in api_config['write_serializers']:
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

        # Check for specific field types
        field_types = set()
        for model in models:
            for field in model.get('fields', []):
                field_types.add(field['type'])

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
        # Note: _needs_validators expects app, not schema
        # Skip validator check here since we don't have app context
        imports['django'].append('from django.core.exceptions import ValidationError')
        imports['rest_framework'].append('from rest_framework.validators import UniqueValidator')

        # Transactions
        imports['django'].append('from django.db import transaction')

        # Models import
        imports['app'].append(f"from .models import {', '.join(model['name'] for model in models)}")

        # Custom fields
        if self._needs_custom_fields(models):
            imports['app'].append('from .fields import *')

        # Features
        features = schema.get('features', {})

        # JWT
        if features.get('authentication', {}).get('jwt'):
            imports['rest_framework'].append('from rest_framework_simplejwt.serializers import TokenObtainPairSerializer')

        # Nested serializers
        if self._has_nested_serializers(models):
            imports['rest_framework'].append('from rest_framework.serializers import SerializerMethodField')

        return imports