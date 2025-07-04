"""
Custom Manager Generator
Generates Django model managers with custom querysets
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class CustomManagerGenerator(BaseGenerator):
    """
    Generates custom Django model managers and querysets.
    
    Features:
    - Custom filtering methods
    - Optimized querysets
    - Soft delete support
    - Caching integration
    - Performance optimizations
    """
    
    name = "CustomManagerGenerator"
    description = "Generates custom Django model managers"
    version = "1.0.0"
    order = 22
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if any models need custom managers."""
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                business_logic = model.get('business_logic', {})
                if business_logic.get('managers') or model.get('features', {}).get('soft_delete'):
                    return True
        return False
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate custom managers for all apps."""
        self.generated_files = []
        
        for app in schema.get('apps', []):
            models_with_managers = []
            
            for model in app.get('models', []):
                if self._needs_custom_manager(model):
                    models_with_managers.append(model)
            
            if models_with_managers:
                self._generate_app_managers(app['name'], models_with_managers, schema)
        
        return self.generated_files
    
    def _needs_custom_manager(self, model: Dict[str, Any]) -> bool:
        """Check if model needs custom manager."""
        business_logic = model.get('business_logic', {})
        features = model.get('features', {})
        
        return (
            business_logic.get('managers') or
            features.get('soft_delete') or
            features.get('cache') or
            len(model.get('fields', [])) > 10  # Complex models benefit from custom managers
        )
    
    def _generate_app_managers(self, app_name: str, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> None:
        """Generate managers file for an app."""
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'managers': self._process_managers(models),
            'querysets': self._process_querysets(models),
            'features': schema.get('features', {}),
        }
        
        self.create_file_from_template(
            'app/models/managers.py.j2',
            f'apps/{app_name}/managers.py',
            ctx
        )
    
    def _process_managers(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process manager configurations for models."""
        processed_managers = []
        
        for model in models:
            model_name = model['name']
            business_logic = model.get('business_logic', {})
            features = model.get('features', {})
            
            # Base manager
            manager_config = {
                'model_name': model_name,
                'class_name': f'{model_name}Manager',
                'queryset_class': f'{model_name}QuerySet',
                'methods': [],
                'features': features,
            }
            
            # Add custom managers from business logic
            for manager in business_logic.get('managers', []):
                custom_manager = {
                    'model_name': model_name,
                    'class_name': f'{model_name}{manager["name"].title()}Manager',
                    'queryset_class': f'{model_name}QuerySet',
                    'filters': manager.get('filters', {}),
                    'name': manager['name'],
                    'methods': self._generate_manager_methods(manager),
                }
                processed_managers.append(custom_manager)
            
            # Add default manager
            processed_managers.append(manager_config)
        
        return processed_managers
    
    def _process_querysets(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process queryset configurations for models."""
        processed_querysets = []
        
        for model in models:
            model_name = model['name']
            features = model.get('features', {})
            fields = model.get('fields', [])
            
            queryset_config = {
                'model_name': model_name,
                'class_name': f'{model_name}QuerySet',
                'methods': self._generate_queryset_methods(model),
                'optimizations': self._generate_optimizations(fields),
                'features': features,
            }
            
            processed_querysets.append(queryset_config)
        
        return processed_querysets
    
    def _generate_manager_methods(self, manager_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate methods for custom managers."""
        methods = []
        filters = manager_config.get('filters', {})
        
        # Generate filter method
        if filters:
            filter_conditions = []
            for field, value in filters.items():
                if isinstance(value, str):
                    filter_conditions.append(f"{field}='{value}'")
                else:
                    filter_conditions.append(f"{field}={value}")
            
            methods.append({
                'name': 'get_queryset',
                'implementation': f'''
def get_queryset(self):
    """Return filtered queryset."""
    return super().get_queryset().filter({', '.join(filter_conditions)})
'''
            })
        
        return methods
    
    def _generate_queryset_methods(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate methods for custom querysets."""
        methods = []
        features = model.get('features', {})
        fields = model.get('fields', [])
        
        # Active/inactive methods for soft delete
        if features.get('soft_delete'):
            methods.extend([
                {
                    'name': 'active',
                    'implementation': '''
def active(self):
    """Return only non-deleted records."""
    return self.filter(deleted_at__isnull=True)
'''
                },
                {
                    'name': 'deleted',
                    'implementation': '''
def deleted(self):
    """Return only deleted records."""
    return self.filter(deleted_at__isnull=False)
'''
                }
            ])
        
        # Recent method for models with created_at
        if any(f['name'] == 'created_at' for f in fields):
            methods.append({
                'name': 'recent',
                'implementation': '''
def recent(self, days=7):
    """Return records created in the last N days."""
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(days=days)
    return self.filter(created_at__gte=cutoff)
'''
            })
        
        # Search method for models with searchable fields
        searchable_fields = [f['name'] for f in fields if f['type'] in ['CharField', 'TextField']]
        if searchable_fields:
            search_conditions = ' | '.join([f'Q({field}__icontains=query)' for field in searchable_fields[:3]])
            methods.append({
                'name': 'search',
                'implementation': f'''
def search(self, query):
    """Search across multiple fields."""
    from django.db.models import Q
    
    if not query:
        return self.none()
    
    return self.filter({search_conditions})
'''
            })
        
        # Bulk operations
        methods.extend([
            {
                'name': 'bulk_update_status',
                'implementation': '''
def bulk_update_status(self, status, ids=None):
    """Bulk update status for multiple records."""
    from django.utils import timezone
    
    queryset = self
    if ids:
        queryset = queryset.filter(id__in=ids)
    
    return queryset.update(
        status=status,
        updated_at=timezone.now()
    )
'''
            },
            {
                'name': 'with_related',
                'implementation': '''
def with_related(self):
    """Optimize queryset with select_related and prefetch_related."""
    qs = self.select_related()
    
    # Add common prefetch_related optimizations
    prefetch_fields = []
    for field in self.model._meta.get_fields():
        if field.many_to_many or field.one_to_many:
            prefetch_fields.append(field.name)
    
    if prefetch_fields:
        qs = qs.prefetch_related(*prefetch_fields[:5])  # Limit to avoid over-fetching
    
    return qs
'''
            }
        ])
        
        return methods
    
    def _generate_optimizations(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate optimization configurations."""
        optimizations = {
            'select_related_fields': [],
            'prefetch_related_fields': [],
            'only_fields': [],
            'defer_fields': [],
        }
        
        for field in fields:
            # Foreign keys for select_related
            if field['type'] in ['ForeignKey', 'OneToOneField']:
                optimizations['select_related_fields'].append(field['name'])
            
            # Large text fields for defer
            if field['type'] == 'TextField':
                optimizations['defer_fields'].append(field['name'])
            
            # Essential fields for only
            if field['name'] in ['id', 'name', 'title', 'status', 'created_at']:
                optimizations['only_fields'].append(field['name'])
        
        return optimizations