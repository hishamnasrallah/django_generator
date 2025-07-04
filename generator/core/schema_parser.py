"""
Schema Parser and Validator
Parses and validates schema files for code generation
"""
from typing import Dict, Any, List, Optional, Set, Union
from pathlib import Path
import re
from pydantic import BaseModel, Field, validator, ValidationError
from pydantic.types import constr

from ..config.settings import Settings


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    pass


# Pydantic models for schema validation

class FieldOptions(BaseModel):
    """Field options that can be specified."""
    max_length: Optional[int] = None
    max_digits: Optional[int] = None
    decimal_places: Optional[int] = None
    null: bool = False
    blank: bool = False
    default: Optional[Union[str, int, float, bool, list, dict]] = None
    unique: bool = False
    db_index: bool = False
    primary_key: bool = False
    editable: bool = True
    verbose_name: Optional[str] = None
    help_text: Optional[str] = None
    choices: Optional[List[Union[tuple, list]]] = None
    upload_to: Optional[str] = None
    on_delete: Optional[str] = "CASCADE"
    related_name: Optional[str] = None
    related_query_name: Optional[str] = None
    auto_now: bool = False
    auto_now_add: bool = False

    class Config:
        extra = 'allow'  # Allow additional options


class FieldDefinition(BaseModel):
    """Model field definition."""
    name: constr(pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    type: str
    to: Optional[str] = None  # For relationship fields
    through: Optional[str] = None  # For M2M with through model

    # Flatten options into field definition
    max_length: Optional[int] = None
    max_digits: Optional[int] = None
    decimal_places: Optional[int] = None
    null: bool = False
    blank: bool = False
    default: Optional[Union[str, int, float, bool, list, dict]] = None
    unique: bool = False
    db_index: bool = False
    primary_key: bool = False
    editable: bool = True
    verbose_name: Optional[str] = None
    help_text: Optional[str] = None
    choices: Optional[List[Union[tuple, list]]] = None
    upload_to: Optional[str] = None
    on_delete: Optional[str] = "CASCADE"
    related_name: Optional[str] = None
    related_query_name: Optional[str] = None
    auto_now: bool = False
    auto_now_add: bool = False

    @validator('type')
    def validate_field_type(cls, v):
        """Validate field type is supported."""
        valid_types = {
            # Text types
            'CharField', 'TextField', 'SlugField',
            # Numeric types
            'IntegerField', 'BigIntegerField', 'SmallIntegerField',
            'PositiveIntegerField', 'PositiveSmallIntegerField',
            'FloatField', 'DecimalField',
            # Boolean
            'BooleanField', 'NullBooleanField',
            # Date/Time
            'DateField', 'DateTimeField', 'TimeField', 'DurationField',
            # File
            'FileField', 'ImageField', 'FilePathField',
            # Email/URL
            'EmailField', 'URLField',
            # Other
            'GenericIPAddressField', 'JSONField', 'UUIDField',
            'BinaryField', 'ArrayField', 'HStoreField',
            # Relationships
            'ForeignKey', 'OneToOneField', 'ManyToManyField',
            # Special
            'AutoField', 'BigAutoField'
        }

        if v not in valid_types:
            raise ValueError(f"Invalid field type: {v}")
        return v

    @validator('on_delete')
    def validate_on_delete(cls, v, values):
        """Validate on_delete option for relationship fields."""
        if values.get('type') in ['ForeignKey', 'OneToOneField']:
            valid_options = {'CASCADE', 'PROTECT', 'SET_NULL', 'SET_DEFAULT', 'SET', 'DO_NOTHING'}
            if v.upper() not in valid_options:
                raise ValueError(f"Invalid on_delete option: {v}")
        return v.upper()

    class Config:
        extra = 'allow'


class ModelMeta(BaseModel):
    """Model Meta options."""
    db_table: Optional[str] = None
    ordering: Optional[List[str]] = None
    verbose_name: Optional[str] = None
    verbose_name_plural: Optional[str] = None
    abstract: bool = False
    proxy: bool = False
    managed: bool = True
    unique_together: Optional[List[List[str]]] = None
    constraints: Optional[List[dict]] = None
    indexes: Optional[List[dict]] = None
    permissions: Optional[List[tuple]] = None
    default_permissions: Optional[List[str]] = None

    class Config:
        extra = 'allow'


class BusinessMethod(BaseModel):
    """Business logic method definition."""
    name: constr(pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    description: Optional[str] = None
    params: List[str] = ()
    returns: Optional[str] = None
    implementation: str
    decorator: Optional[str] = None  # e.g., @property, @cached_property

    class Config:
        extra = 'allow'


class StateTransition(BaseModel):
    """State machine transition definition."""
    name: constr(pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    source: Union[str, List[str]]  # Source state(s)
    target: str  # Target state
    permission: Optional[str] = None
    condition: Optional[str] = None
    on_success: Optional[str] = None
    on_error: Optional[str] = None

    class Config:
        extra = 'allow'


class StateMachine(BaseModel):
    """State machine configuration."""
    field: str = "status"
    states: List[Union[str, tuple]]
    initial: str
    transitions: List[StateTransition]

    class Config:
        extra = 'allow'


class ModelFeatures(BaseModel):
    """Model-specific features."""
    audit: bool = False
    soft_delete: bool = False
    versioning: bool = False
    multitenancy: bool = False
    cache: bool = False
    search: bool = False

    class Config:
        extra = 'allow'


class ModelDefinition(BaseModel):
    """Complete model definition."""
    name: constr(pattern=r'^[A-Z][a-zA-Z0-9]*$')  # PascalCase
    description: Optional[str] = None
    fields: List[FieldDefinition]
    meta: Optional[ModelMeta] = None
    methods: Optional[List[BusinessMethod]] = None
    properties: Optional[List[BusinessMethod]] = None
    state_machine: Optional[StateMachine] = None
    features: Optional[ModelFeatures] = None
    abstract: bool = False
    extends: Optional[str] = None  # Parent model
    mixins: Optional[List[str]] = None

    @validator('name')
    def validate_model_name(cls, v):
        """Ensure model name follows Django conventions."""
        if v.lower() in ['model', 'object', 'none', 'true', 'false']:
            raise ValueError(f"'{v}' is a reserved name")
        return v

    class Config:
        extra = 'allow'


class AppDefinition(BaseModel):
    """Django app definition."""
    name: constr(pattern=r'^[a-z][a-z0-9_]*$')  # snake_case
    description: Optional[str] = None
    models: List[ModelDefinition]
    services: Optional[List[dict]] = None
    api: Optional[dict] = None
    admin: Optional[dict] = None
    signals: Optional[List[dict]] = None
    tasks: Optional[List[dict]] = None

    @validator('name')
    def validate_app_name(cls, v):
        """Ensure app name is valid Python module name."""
        if v in ['test', 'tests', 'django', 'admin', 'static', 'media']:
            raise ValueError(f"'{v}' is a reserved app name")
        return v

    class Config:
        extra = 'allow'


class ProjectSettings(BaseModel):
    """Project configuration settings."""
    name: constr(pattern=r'^[a-z][a-z0-9_]*$')
    description: Optional[str] = None
    version: str = "1.0.0"
    python_version: str = "3.11"
    django_version: str = "4.2"

    class Config:
        extra = 'allow'


class FeatureConfig(BaseModel):
    """Feature configuration."""
    # Authentication
    authentication: Optional[dict] = None

    # API
    api: Optional[dict] = None

    # Database
    database: Optional[dict] = None

    # Performance
    performance: Optional[dict] = None

    # Deployment
    deployment: Optional[dict] = None

    # Enterprise
    enterprise: Optional[dict] = None

    class Config:
        extra = 'allow'


class SchemaDefinition(BaseModel):
    """Complete schema definition."""
    project: ProjectSettings
    features: Optional[FeatureConfig] = None
    apps: List[AppDefinition]
    integrations: Optional[dict] = None

    class Config:
        extra = 'allow'


class SchemaParser:
    """
    Parses and validates schema files.

    Handles:
    - Schema validation
    - Default value injection
    - Reference resolution
    - Feature detection
    """

    def __init__(self, settings: Optional[Settings] = None, strict_mode: bool = False):
        self.settings = settings or Settings()
        self.strict_mode = strict_mode
        self._validators = self._setup_validators()

    def _setup_validators(self) -> Dict[str, Any]:
        """Setup custom validators."""
        return {
            'field_name': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),
            'model_name': re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
            'app_name': re.compile(r'^[a-z][a-z0-9_]*$'),
        }

    def parse(self, schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate schema dictionary.

        Args:
            schema_dict: Raw schema dictionary

        Returns:
            Validated and normalized schema

        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            # Validate using Pydantic
            schema = SchemaDefinition(**schema_dict)

            # Convert to dictionary
            parsed = schema.dict()

            # Post-process
            parsed = self._normalize_schema(parsed)
            parsed = self._inject_defaults(parsed)
            parsed = self._resolve_references(parsed)
            parsed = self._detect_features(parsed)

            # Additional validation
            if self.strict_mode:
                self._strict_validation(parsed)

            return parsed

        except ValidationError as e:
            errors = []
            for error in e.errors():
                location = ' -> '.join(str(loc) for loc in error['loc'])
                errors.append(f"{location}: {error['msg']}")

            raise SchemaValidationError(
                f"Schema validation failed:\n" + '\n'.join(errors)
            )
        except Exception as e:
            raise SchemaValidationError(f"Schema parsing failed: {str(e)}")

    def validate(self, schema_dict: Dict[str, Any], return_warnings: bool = False) -> Union[bool, Dict[str, Any]]:
        """
        Validate schema without full parsing.

        Args:
            schema_dict: Schema to validate
            return_warnings: Whether to return detailed results

        Returns:
            True if valid (or dict with results if return_warnings=True)
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            # Basic validation
            SchemaDefinition(**schema_dict)

            # Check for warnings
            warnings = self._check_warnings(schema_dict)
            result['warnings'] = warnings

        except ValidationError as e:
            result['valid'] = False
            for error in e.errors():
                location = ' -> '.join(str(loc) for loc in error['loc'])
                result['errors'].append(f"{location}: {error['msg']}")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(str(e))

        if return_warnings:
            return result
        return result['valid']

    def _normalize_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize schema structure."""
        # Ensure consistent structure
        if 'features' not in schema:
            schema['features'] = {}

        # Normalize feature flags
        features = schema['features']

        # Convert simple boolean features to dict
        for key in list(features.keys()):
            if isinstance(features[key], bool):
                features[key] = {'enabled': features[key]}

        # Normalize app structure
        for app in schema['apps']:
            if 'models' not in app:
                app['models'] = []

            # Normalize model fields
            for model in app['models']:
                for field in model['fields']:
                    # Ensure relationship fields have 'to'
                    if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                        if 'to' not in field and 'related_model' in field:
                            field['to'] = field.pop('related_model')

        return schema

    def _inject_defaults(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Inject default values where not specified."""
        project = schema['project']

        # Project defaults
        project.setdefault('python_version', self.settings.get('python_version', '3.11'))
        project.setdefault('django_version', self.settings.get('django_version', '4.2'))

        # Feature defaults
        features = schema.get('features', {})

        # Database defaults
        if 'database' in features:
            db = features['database']
            if isinstance(db, dict):
                db.setdefault('engine', 'postgresql')
                db.setdefault('name', schema['project']['name'])

        # API defaults
        if 'api' in features:
            api = features['api']
            if isinstance(api, dict):
                if api.get('rest_framework'):
                    api.setdefault('authentication', 'token')
                    api.setdefault('pagination', 'page_number')
                    api.setdefault('versioning', None)

        # Model defaults
        for app in schema['apps']:
            for model in app['models']:
                # Add timestamps if not disabled
                if not model.get('no_timestamps'):
                    has_created_at = any(f['name'] == 'created_at' for f in model['fields'])
                    has_updated_at = any(f['name'] == 'updated_at' for f in model['fields'])

                    if not has_created_at:
                        model['fields'].append({
                            'name': 'created_at',
                            'type': 'DateTimeField',
                            'auto_now_add': True
                        })

                    if not has_updated_at:
                        model['fields'].append({
                            'name': 'updated_at',
                            'type': 'DateTimeField',
                            'auto_now': True
                        })

                # Default Meta options
                if not model.get('meta'):
                    model['meta'] = {}

                meta = model['meta']
                if not meta.get('ordering'):
                    meta['ordering'] = ['-created_at']

        return schema

    def _resolve_references(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve references between models."""
        # Build model registry
        model_registry = {}

        for app in schema['apps']:
            app_name = app['name']
            for model in app['models']:
                model_name = model['name']
                full_name = f"{app_name}.{model_name}"
                model_registry[model_name] = full_name
                model_registry[full_name] = full_name

        # Resolve references in fields
        for app in schema['apps']:
            for model in app['models']:
                for field in model['fields']:
                    if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                        if 'to' in field:
                            to_model = field['to']

                            # Handle special cases
                            if to_model == 'self':
                                continue
                            elif to_model.startswith('auth.'):
                                continue
                            elif '.' not in to_model:
                                # Try to resolve to full path
                                if to_model in model_registry:
                                    field['to'] = model_registry[to_model]
                                else:
                                    # Assume same app
                                    field['to'] = f"{app['name']}.{to_model}"

        return schema

    def _detect_features(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-detect features based on schema content."""
        detected = set()

        # Check models for feature indicators
        for app in schema['apps']:
            for model in app['models']:
                # Check for file uploads
                for field in model['fields']:
                    if field['type'] in ['FileField', 'ImageField']:
                        detected.add('file_upload')
                        if field['type'] == 'ImageField':
                            detected.add('image_processing')

                # Check for state machines
                if model.get('state_machine'):
                    detected.add('state_machine')

                # Check for features
                if model.get('features'):
                    features = model['features']
                    if features.get('audit'):
                        detected.add('audit_log')
                    if features.get('soft_delete'):
                        detected.add('soft_delete')
                    if features.get('versioning'):
                        detected.add('versioning')
                    if features.get('multitenancy'):
                        detected.add('multitenancy')

        # Add detected features to schema
        if 'detected_features' not in schema:
            schema['detected_features'] = list(detected)

        return schema

    def _strict_validation(self, schema: Dict[str, Any]) -> None:
        """Perform strict validation checks."""
        errors = []

        # Check for duplicate model names
        model_names = []
        for app in schema['apps']:
            for model in app['models']:
                full_name = f"{app['name']}.{model['name']}"
                if full_name in model_names:
                    errors.append(f"Duplicate model: {full_name}")
                model_names.append(full_name)

        # Check for circular dependencies
        # TODO: Implement circular dependency detection

        # Check for missing related models
        for app in schema['apps']:
            for model in app['models']:
                for field in model['fields']:
                    if field['type'] in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                        to_model = field.get('to')
                        if to_model and to_model != 'self' and not to_model.startswith('auth.'):
                            if to_model not in model_names:
                                errors.append(
                                    f"Related model not found: {to_model} "
                                    f"(referenced by {app['name']}.{model['name']}.{field['name']})"
                                )

        if errors:
            raise SchemaValidationError(
                f"Strict validation failed:\n" + '\n'.join(errors)
            )

    def _check_warnings(self, schema_dict: Dict[str, Any]) -> List[str]:
        """Check for potential issues that don't prevent generation."""
        warnings = []

        # Check for missing descriptions
        if not schema_dict.get('project', {}).get('description'):
            warnings.append("Project description is missing")

        # Check for very large models
        for app in schema_dict.get('apps', []):
            for model in app.get('models', []):
                field_count = len(model.get('fields', []))
                if field_count > 30:
                    warnings.append(
                        f"Model {app['name']}.{model['name']} has {field_count} fields. "
                        "Consider splitting into multiple models."
                    )

        # Check for missing indexes on foreign keys
        for app in schema_dict.get('apps', []):
            for model in app.get('models', []):
                for field in model.get('fields', []):
                    if field.get('type') == 'ForeignKey' and field.get('db_index') is False:
                        warnings.append(
                            f"Foreign key {app['name']}.{model['name']}.{field['name']} "
                            "has db_index=False. This may impact performance."
                        )

        # Check for deprecated features
        if schema_dict.get('features', {}).get('api', {}).get('rest_framework_version') == '2':
            warnings.append("REST Framework 2.x is deprecated. Consider upgrading to 3.x")

        return warnings