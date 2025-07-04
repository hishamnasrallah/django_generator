"""
GraphQL Generator
Generates GraphQL schema, types, queries, and mutations
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class GraphQLGenerator(BaseGenerator):
    """
    Generates GraphQL implementation using Graphene-Django.
    
    Features:
    - Object types for models
    - Query resolvers
    - Mutation resolvers
    - Filtering and pagination
    - Authentication integration
    - Subscription support
    """
    
    name = "GraphQLGenerator"
    description = "Generates GraphQL schema and resolvers"
    version = "1.0.0"
    order = 35
    requires = {'ModelGenerator'}
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if GraphQL is enabled."""
        return schema.get('features', {}).get('api', {}).get('graphql', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate GraphQL files for all apps."""
        self.generated_files = []
        
        # Generate main schema
        self._generate_main_schema(schema)
        
        # Generate app-specific GraphQL files
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_graphql(app, schema)
        
        return self.generated_files
    
    def _generate_main_schema(self, schema: Dict[str, Any]) -> None:
        """Generate main GraphQL schema file."""
        ctx = {
            'project': schema['project'],
            'apps': schema.get('apps', []),
            'features': schema.get('features', {}),
        }
        
        self.create_file_from_template(
            'app/graphql/schema.py.j2',
            f"{schema['project']['name']}/schema.py",
            ctx
        )
    
    def _generate_app_graphql(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate GraphQL files for a single app."""
        app_name = app['name']
        models = app.get('models', [])
        
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'types': self._generate_types(models),
            'queries': self._generate_queries(models),
            'mutations': self._generate_mutations(models),
            'subscriptions': self._generate_subscriptions(models),
        }
        
        # Generate types
        self.create_file_from_template(
            'app/graphql/types.py.j2',
            f'apps/{app_name}/graphql/types.py',
            ctx
        )
        
        # Generate queries
        self.create_file_from_template(
            'app/graphql/queries.py.j2',
            f'apps/{app_name}/graphql/queries.py',
            ctx
        )
        
        # Generate mutations
        self.create_file_from_template(
            'app/graphql/mutations.py.j2',
            f'apps/{app_name}/graphql/mutations.py',
            ctx
        )
        
        # Generate schema for app
        self.create_file_from_template(
            'app/graphql/schema.py.j2',
            f'apps/{app_name}/graphql/schema.py',
            ctx
        )
    
    def _generate_types(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate GraphQL types for models."""
        types = []
        
        for model in models:
            model_type = {
                'name': f"{model['name']}Type",
                'model_name': model['name'],
                'fields': self._get_graphql_fields(model.get('fields', [])),
                'filters': self._get_filter_fields(model.get('fields', [])),
                'interfaces': ['relay.Node'] if model.get('api', {}).get('relay', True) else [],
            }
            
            types.append(model_type)
        
        return types
    
    def _generate_queries(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate GraphQL queries for models."""
        queries = []
        
        for model in models:
            # Single object query
            queries.append({
                'name': f"{model['name'].lower()}",
                'type': f"{model['name']}Type",
                'model_name': model['name'],
                'description': f"Get a single {model['name']}",
                'args': ['id: ID!'],
                'resolver': f"resolve_{model['name'].lower()}",
            })
            
            # List query
            queries.append({
                'name': f"all_{model['name'].lower()}s",
                'type': f"DjangoFilterConnectionField({model['name']}Type)",
                'model_name': model['name'],
                'description': f"Get all {model['name']}s",
                'args': [],
                'resolver': None,  # Uses default resolver
            })
        
        return queries
    
    def _generate_mutations(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate GraphQL mutations for models."""
        mutations = []
        
        for model in models:
            model_name = model['name']
            
            # Create mutation
            mutations.append({
                'name': f"Create{model_name}",
                'model_name': model_name,
                'operation': 'create',
                'input_fields': self._get_input_fields(model.get('fields', []), 'create'),
                'description': f"Create a new {model_name}",
            })
            
            # Update mutation
            mutations.append({
                'name': f"Update{model_name}",
                'model_name': model_name,
                'operation': 'update',
                'input_fields': self._get_input_fields(model.get('fields', []), 'update'),
                'description': f"Update an existing {model_name}",
            })
            
            # Delete mutation
            mutations.append({
                'name': f"Delete{model_name}",
                'model_name': model_name,
                'operation': 'delete',
                'input_fields': [{'name': 'id', 'type': 'ID', 'required': True}],
                'description': f"Delete a {model_name}",
            })
        
        return mutations
    
    def _generate_subscriptions(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate GraphQL subscriptions for models."""
        subscriptions = []
        
        for model in models:
            if model.get('api', {}).get('subscriptions', True):
                subscriptions.append({
                    'name': f"{model['name'].lower()}_updated",
                    'type': f"{model['name']}Type",
                    'model_name': model['name'],
                    'description': f"Subscribe to {model['name']} updates",
                })
        
        return subscriptions
    
    def _get_graphql_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Django fields to GraphQL field definitions."""
        graphql_fields = []
        
        for field in fields:
            graphql_type = self._django_to_graphql_type(field['type'])
            
            graphql_field = {
                'name': field['name'],
                'type': graphql_type,
                'required': not field.get('null', True) and not field.get('blank', True),
                'description': field.get('help_text', f"{field['name']} field"),
            }
            
            graphql_fields.append(graphql_field)
        
        return graphql_fields
    
    def _get_filter_fields(self, fields: List[Dict[str, Any]]) -> List[str]:
        """Get filterable fields for GraphQL."""
        filter_fields = []
        
        for field in fields:
            if field['type'] in ['CharField', 'TextField']:
                filter_fields.extend([
                    field['name'],
                    f"{field['name']}__icontains",
                    f"{field['name']}__istartswith",
                ])
            elif field['type'] in ['IntegerField', 'DecimalField', 'FloatField']:
                filter_fields.extend([
                    field['name'],
                    f"{field['name']}__gt",
                    f"{field['name']}__lt",
                ])
            elif field['type'] in ['DateField', 'DateTimeField']:
                filter_fields.extend([
                    field['name'],
                    f"{field['name']}__year",
                    f"{field['name']}__month",
                ])
            else:
                filter_fields.append(field['name'])
        
        return filter_fields
    
    def _get_input_fields(self, fields: List[Dict[str, Any]], operation: str) -> List[Dict[str, Any]]:
        """Get input fields for mutations."""
        input_fields = []
        
        if operation == 'update':
            input_fields.append({
                'name': 'id',
                'type': 'ID',
                'required': True,
                'description': 'ID of the object to update'
            })
        
        for field in fields:
            # Skip auto fields
            if field.get('auto_now') or field.get('auto_now_add'):
                continue
            
            # Skip primary key for create
            if operation == 'create' and field.get('primary_key'):
                continue
            
            graphql_type = self._django_to_graphql_type(field['type'])
            required = (operation == 'create' and 
                       not field.get('null', True) and 
                       not field.get('blank', True) and
                       field.get('default') is None)
            
            input_fields.append({
                'name': field['name'],
                'type': graphql_type,
                'required': required,
                'description': field.get('help_text', f"{field['name']} field"),
            })
        
        return input_fields
    
    def _django_to_graphql_type(self, django_type: str) -> str:
        """Convert Django field type to GraphQL type."""
        type_mapping = {
            'CharField': 'String',
            'TextField': 'String',
            'EmailField': 'String',
            'URLField': 'String',
            'SlugField': 'String',
            'IntegerField': 'Int',
            'BigIntegerField': 'Int',
            'SmallIntegerField': 'Int',
            'PositiveIntegerField': 'Int',
            'FloatField': 'Float',
            'DecimalField': 'Decimal',
            'BooleanField': 'Boolean',
            'DateField': 'Date',
            'DateTimeField': 'DateTime',
            'TimeField': 'Time',
            'JSONField': 'JSONString',
            'UUIDField': 'UUID',
            'ForeignKey': 'ID',
            'OneToOneField': 'ID',
            'ManyToManyField': '[ID]',
        }
        
        return type_mapping.get(django_type, 'String')