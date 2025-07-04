"""
Admin Generator
Generates Django admin configurations
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class AdminGenerator(BaseGenerator):
    """
    Generates Django admin configurations with:
    - ModelAdmin classes
    - Custom filters
    - Inline admin classes
    - Actions
    - Import/Export support
    """

    name = "AdminGenerator"
    description = "Generates Django admin configurations"
    version = "1.0.0"
    order = 30
    category = "app"
    requires = {'ModelGenerator'}
    provides = {'AdminGenerator', 'admin'}
    tags = {'admin', 'interface', 'ui'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema has admin configuration."""
        if not schema or not isinstance(schema, dict):
            return False

        # Check if admin is enabled
        features = schema.get('features', {})
        if not features.get('admin', {}).get('enabled', True):
            return False

        # Check if any app has models with admin config
        apps = schema.get('apps', [])
        for app in apps:
            if app and isinstance(app, dict):
                models = app.get('models', [])
                for model in models:
                    if model and isinstance(model, dict):
                        # Check if model has admin config or is not explicitly disabled
                        admin_config = model.get('admin', {})
                        if admin_config is None or admin_config.get('enabled', True):
                            return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate admin files for all apps."""
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

            if self._should_generate_admin(app, schema):
                self._generate_app_admin(app, schema)

        return self.generated_files

    def _should_generate_admin(self, app: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Check if admin should be generated for this app."""
        # Check if app has models
        models = app.get('models', [])
        if not models:
            return False

        # Check if any model needs admin
        for model in models:
            if model and isinstance(model, dict):
                admin_config = model.get('admin', {})
                if admin_config is None or admin_config.get('enabled', True):
                    return True

        return False

    def _generate_app_admin(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate admin files for a single app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        models = app.get('models', [])
        if not models:
            return

        # Filter models that need admin
        admin_models = []
        for model in models:
            if model and isinstance(model, dict):
                admin_config = model.get('admin', {})
                if admin_config is None or admin_config.get('enabled', True):
                    # Enhance admin config with defaults
                    model['admin'] = self._enhance_admin_config(model, admin_config or {})
                    admin_models.append(model)

        if not admin_models:
            return

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': admin_models,
            'features': schema.get('features', {}),
            'project': schema.get('project', {}),
            'has_custom_filters': self._has_custom_filters(admin_models),
            'has_inlines': self._has_inlines(admin_models),
            'custom_filters': self._get_custom_filters(admin_models),
            'inlines': self._get_inlines(admin_models),
            'relationship_fields': self._get_relationship_fields(admin_models),
        }

        # Generate main admin.py
        self.create_file_from_template(
            'app/admin/admin.py.j2',
            f'apps/{app_name}/admin.py',
            ctx
        )

        # Generate filters.py if needed
        if ctx['has_custom_filters']:
            self.create_file_from_template(
                'app/admin/filters.py.j2',
                f'apps/{app_name}/admin/filters.py',
                ctx
            )

        # Generate inline.py if needed
        if ctx['has_inlines']:
            self.create_file_from_template(
                'app/admin/inline.py.j2',
                f'apps/{app_name}/admin/inline.py',
                ctx
            )

    def _enhance_admin_config(self, model: Dict[str, Any], admin_config: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance admin configuration with intelligent defaults."""
        enhanced = admin_config.copy()

        # Default list_display
        if 'list_display' not in enhanced:
            list_display = ['id']

            # Add common field names
            field_names = [f.get('name') for f in model.get('fields', []) if f and isinstance(f, dict)]
            for field_name in ['name', 'title', 'label', 'code', 'status']:
                if field_name in field_names:
                    list_display.append(field_name)
                    break

            # Add date fields
            for field in model.get('fields', []):
                if field and isinstance(field, dict):
                    if field.get('type') in ['DateField', 'DateTimeField'] and len(list_display) < 5:
                        list_display.append(field['name'])

            enhanced['list_display'] = list_display[:7]  # Limit to 7 columns

        # Default search_fields
        if 'search_fields' not in enhanced:
            search_fields = []
            for field in model.get('fields', []):
                if field and isinstance(field, dict):
                    if field.get('type') in ['CharField', 'TextField'] and field.get('name') not in ['id', 'password']:
                        search_fields.append(field['name'])
            enhanced['search_fields'] = search_fields[:5]  # Limit to 5 fields

        # Default list_filter
        if 'list_filter' not in enhanced:
            list_filter = []
            for field in model.get('fields', []):
                if field and isinstance(field, dict):
                    if field.get('type') in ['BooleanField', 'DateField', 'DateTimeField', 'ForeignKey']:
                        list_filter.append({'field': field['name'], 'type': 'standard'})
                    elif field.get('choices'):
                        list_filter.append({'field': field['name'], 'type': 'standard'})
            enhanced['list_filter'] = list_filter[:5]  # Limit to 5 filters

        # Default ordering
        if 'ordering' not in enhanced:
            # Try to find a date field
            for field in model.get('fields', []):
                if field and isinstance(field, dict):
                    if field.get('name') == 'created_at':
                        enhanced['ordering'] = ['-created_at']
                        break
            else:
                enhanced['ordering'] = ['-id']

        # Import/Export configuration
        features = model.get('features', {})
        if features.get('import_export'):
            enhanced['import_export'] = {
                'enabled': True,
                'fields': enhanced.get('import_export', {}).get('fields'),
                'exclude': enhanced.get('import_export', {}).get('exclude', ['id', 'created_at', 'updated_at']),
            }

        return enhanced

    def _has_custom_filters(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has custom filters."""
        for model in models:
            if model and isinstance(model, dict):
                admin_config = model.get('admin', {})
                list_filter = admin_config.get('list_filter', [])
                for filter_item in list_filter:
                    if isinstance(filter_item, dict) and filter_item.get('type') == 'custom':
                        return True
        return False

    def _has_inlines(self, models: List[Dict[str, Any]]) -> bool:
        """Check if any model has inline admin."""
        for model in models:
            if model and isinstance(model, dict):
                admin_config = model.get('admin', {})
                if admin_config.get('inlines'):
                    return True
        return False

    def _get_custom_filters(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all custom filters."""
        filters = []
        for model in models:
            if model and isinstance(model, dict):
                admin_config = model.get('admin', {})
                list_filter = admin_config.get('list_filter', [])
                for filter_item in list_filter:
                    if isinstance(filter_item, dict) and filter_item.get('type') == 'custom':
                        filters.append({
                            'name': filter_item.get('class', f"{model['name']}{filter_item['field'].title()}Filter"),
                            'model': model['name'],
                            'field': filter_item['field'],
                            'title': filter_item.get('title', filter_item['field'].replace('_', ' ').title()),
                        })
        return filters

    def _get_inlines(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all inline configurations."""
        inlines = []
        for model in models:
            if model and isinstance(model, dict):
                admin_config = model.get('admin', {})
                for inline in admin_config.get('inlines', []):
                    if isinstance(inline, str):
                        # Simple inline reference
                        inlines.append({
                            'name': inline,
                            'type': 'TabularInline',
                        })
                    elif isinstance(inline, dict):
                        # Detailed inline config
                        inlines.append(inline)
        return inlines

    def _get_relationship_fields(self, models: List[Dict[str, Any]]) -> List[str]:
        """Get all relationship field names."""
        fields = set()
        for model in models:
            if model and isinstance(model, dict):
                for field in model.get('fields', []):
                    if field and isinstance(field, dict):
                        if field.get('type') in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                            fields.add(field['name'])
        return list(fields)