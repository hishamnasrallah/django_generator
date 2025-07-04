"""
Elasticsearch Generator
Generates Elasticsearch integration for advanced search capabilities
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class ElasticsearchGenerator(BaseGenerator):
    """
    Generates Elasticsearch integration for Django models.
    
    Features:
    - Document definitions
    - Search views and serializers
    - Index management
    - Advanced search queries
    - Aggregations and analytics
    """
    
    name = "ElasticsearchGenerator"
    description = "Generates Elasticsearch search integration"
    version = "1.0.0"
    order = 60
    requires = {'ModelGenerator'}
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if Elasticsearch is enabled."""
        return schema.get('features', {}).get('performance', {}).get('elasticsearch', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate Elasticsearch files for all apps."""
        self.generated_files = []
        
        # Generate search configuration
        self._generate_search_config(schema)
        
        # Generate app-specific search files
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_search(app, schema)
        
        return self.generated_files
    
    def _generate_search_config(self, schema: Dict[str, Any]) -> None:
        """Generate main search configuration."""
        ctx = {
            'project': schema['project'],
            'apps': schema.get('apps', []),
            'features': schema.get('features', {}),
        }
        
        self.create_file_from_template(
            'integrations/search/search_service.py.j2',
            'core/search/service.py',
            ctx
        )
        
        # Generate search utilities
        self.create_file_from_template(
            'integrations/search/elasticsearch.py.j2',
            'core/search/elasticsearch.py',
            ctx
        )
    
    def _generate_app_search(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate search files for a single app."""
        app_name = app['name']
        models = app.get('models', [])
        
        # Filter models that need search
        searchable_models = [m for m in models if self._is_searchable(m)]
        
        if not searchable_models:
            return
        
        ctx = {
            'app_name': app_name,
            'models': searchable_models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'documents': self._generate_documents(searchable_models),
            'search_views': self._generate_search_views(searchable_models),
        }
        
        # Generate documents
        self.create_file_from_template(
            'integrations/search/documents.py.j2',
            f'apps/{app_name}/search/documents.py',
            ctx
        )
        
        # Generate search views
        self.create_file_from_template(
            'integrations/search/views.py.j2',
            f'apps/{app_name}/search/views.py',
            ctx
        )
        
        # Generate search serializers
        self.create_file_from_template(
            'integrations/search/serializers.py.j2',
            f'apps/{app_name}/search/serializers.py',
            ctx
        )
    
    def _is_searchable(self, model: Dict[str, Any]) -> bool:
        """Check if model should be searchable."""
        # Check if model has text fields
        text_fields = [f for f in model.get('fields', []) 
                      if f['type'] in ['CharField', 'TextField']]
        
        # Check if search is explicitly enabled
        search_enabled = model.get('features', {}).get('search', len(text_fields) > 0)
        
        return search_enabled and len(text_fields) > 0
    
    def _generate_documents(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Elasticsearch document definitions."""
        documents = []
        
        for model in models:
            doc = {
                'name': f"{model['name']}Document",
                'model_name': model['name'],
                'index_name': model['name'].lower(),
                'fields': self._get_search_fields(model.get('fields', [])),
                'analyzers': self._get_analyzers(model),
                'settings': self._get_index_settings(model),
            }
            
            documents.append(doc)
        
        return documents
    
    def _generate_search_views(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate search view definitions."""
        views = []
        
        for model in models:
            view = {
                'name': f"{model['name']}SearchView",
                'model_name': model['name'],
                'document_name': f"{model['name']}Document",
                'search_fields': self._get_search_fields(model.get('fields', [])),
                'filter_fields': self._get_filter_fields(model.get('fields', [])),
                'aggregations': self._get_aggregations(model),
            }
            
            views.append(view)
        
        return views
    
    def _get_search_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get searchable fields for Elasticsearch."""
        search_fields = []
        
        for field in fields:
            if field['type'] in ['CharField', 'TextField']:
                es_field = {
                    'name': field['name'],
                    'type': 'text',
                    'analyzer': 'standard',
                    'boost': 1.0,
                }
                
                # Boost important fields
                if field['name'] in ['title', 'name']:
                    es_field['boost'] = 3.0
                elif field['name'] in ['description', 'summary']:
                    es_field['boost'] = 2.0
                
                search_fields.append(es_field)
            
            elif field['type'] in ['IntegerField', 'DecimalField']:
                search_fields.append({
                    'name': field['name'],
                    'type': 'number',
                })
            
            elif field['type'] in ['DateField', 'DateTimeField']:
                search_fields.append({
                    'name': field['name'],
                    'type': 'date',
                })
            
            elif field['type'] == 'BooleanField':
                search_fields.append({
                    'name': field['name'],
                    'type': 'boolean',
                })
        
        return search_fields
    
    def _get_filter_fields(self, fields: List[Dict[str, Any]]) -> List[str]:
        """Get filterable fields."""
        filter_fields = []
        
        for field in fields:
            if field['type'] in ['CharField', 'IntegerField', 'BooleanField', 'DateField']:
                filter_fields.append(field['name'])
        
        return filter_fields
    
    def _get_analyzers(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Get custom analyzers for the model."""
        return {
            'custom_analyzer': {
                'type': 'custom',
                'tokenizer': 'standard',
                'filter': ['lowercase', 'stop', 'snowball']
            }
        }
    
    def _get_index_settings(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Get index settings for the model."""
        return {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': self._get_analyzers(model)
            }
        }
    
    def _get_aggregations(self, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get aggregation definitions for the model."""
        aggregations = []
        
        for field in model.get('fields', []):
            if field['type'] in ['CharField', 'BooleanField']:
                aggregations.append({
                    'name': f"by_{field['name']}",
                    'type': 'terms',
                    'field': field['name'],
                })
            elif field['type'] in ['DateField', 'DateTimeField']:
                aggregations.append({
                    'name': f"by_{field['name']}_histogram",
                    'type': 'date_histogram',
                    'field': field['name'],
                    'interval': 'month',
                })
        
        return aggregations