"""
View Generator
Generates Django REST Framework views and viewsets
"""
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions


class ViewGenerator(BaseGenerator):
    """
    Generates DRF views with:
    - ModelViewSet for CRUD operations
    - Custom actions
    - Filtering and searching
    - Permissions
    - Pagination
    - Throttling
    - Caching
    """

    name = "ViewGenerator"
    description = "Generates Django REST Framework views"
    version = "1.0.0"
    order = 40
    requires = {'ModelGenerator', 'SerializerGenerator'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if REST API is enabled."""
        return schema.get('features', {}).get('api', {}).get('rest_framework', False)

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate view files for all apps."""
        self.generated_files = []

        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_views(app, schema)

        # Generate base viewsets if needed
        if self._needs_base_viewsets(schema):
            self._generate_base_viewsets(schema)

        return self.generated_files

    def _generate_app_views(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate views for a single app."""
        app_name = app['name']
        models = app.get('models', [])

        if not models:
            return

        # Analyze what's needed
        view_config = self._analyze_view_requirements(app, schema)

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'view_config': view_config if view_config else {'viewsets': {}, 'api_views': [], 'mixins': set(), 'decorators': set()},
            'imports': self._get_required_imports(models, schema, view_config),
            'has_custom_actions': any(model.get('api', {}).get('custom_actions') for model in models),
            'has_filters': any(model.get('api', {}).get('filterset_fields') for model in models),
            'has_search': any(model.get('api', {}).get('search_fields') for model in models),
            'has_bulk_operations': any(model.get('api', {}).get('allow_bulk') for model in models),
        }

        # Generate main views.py
        self.create_file_from_template(
            'app/api/views.py.j2',
            f'apps/{app_name}/views.py',
            ctx
        )

        # Generate filters.py if needed
        if ctx['has_filters']:
            self.create_file_from_template(
                'app/api/filters.py.j2',
                f'apps/{app_name}/filters.py',
                ctx
            )

        # Generate permissions.py if custom permissions
        if self._needs_custom_permissions(app):
            self.create_file_from_template(
                'app/api/permissions.py.j2',
                f'apps/{app_name}/permissions.py',
                ctx
            )

        # Generate pagination.py if custom pagination
        if self._needs_custom_pagination(app):
            self.create_file_from_template(
                'app/api/pagination.py.j2',
                f'apps/{app_name}/pagination.py',
                ctx
            )

        # Generate throttling.py if needed
        if self._needs_throttling(app, schema):
            self.create_file_from_template(
                'app/api/throttling.py.j2',
                f'apps/{app_name}/throttling.py',
                ctx
            )

    def _analyze_view_requirements(self, app: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what view features are needed."""
        config = {
            'viewsets': {},
            'api_views': [],
            'mixins': set(),
            'decorators': set(),
        }

        features = schema.get('features', {})

        for model in app.get('models', []):
            model_name = model['name']
            api_config = model.get('api', {})

            viewset_config = {
                'type': 'ModelViewSet',  # Default
                'mixins': [],
                'actions': [],
                'permissions': api_config.get('permissions', []),
                'authentication': api_config.get('authentication', []),
                'filterset_fields': api_config.get('filterset_fields', []),
                'search_fields': api_config.get('search_fields', []),
                'ordering_fields': api_config.get('ordering_fields', []),
                'pagination': api_config.get('pagination'),
                'throttle': api_config.get('throttle'),
                'cache': api_config.get('cache'),
            }

            # Determine viewset type
            if api_config.get('read_only'):
                viewset_config['type'] = 'ReadOnlyModelViewSet'
            elif api_config.get('allowed_methods'):
                # Custom mix of operations
                viewset_config['type'] = 'GenericViewSet'
                methods = api_config['allowed_methods']

                mixin_map = {
                    'GET': ['ListModelMixin', 'RetrieveModelMixin'],
                    'POST': ['CreateModelMixin'],
                    'PUT': ['UpdateModelMixin'],
                    'PATCH': ['UpdateModelMixin'],
                    'DELETE': ['DestroyModelMixin'],
                }

                for method in methods:
                    viewset_config['mixins'].extend(mixin_map.get(method, []))

                # Remove duplicates
                viewset_config['mixins'] = list(set(viewset_config['mixins']))

            # Custom actions
            if api_config.get('custom_actions'):
                for action in api_config['custom_actions']:
                    viewset_config['actions'].append({
                        'name': action['name'],
                        'methods': action.get('methods', ['POST']),
                        'detail': action.get('detail', True),
                        'permission_classes': action.get('permission_classes'),
                        'serializer_class': action.get('serializer_class'),
                        'description': action.get('description'),
                    })
                    config['decorators'].add('action')

            # Features requiring mixins
            if api_config.get('allow_bulk'):
                config['mixins'].add('BulkModelViewSet')

            if api_config.get('soft_delete'):
                config['mixins'].add('SoftDeleteMixin')

            if features.get('performance', {}).get('caching') and api_config.get('cache'):
                config['decorators'].add('cache_page')
                config['decorators'].add('vary_on_headers')

            # Ensure viewsets dict exists
            if 'viewsets' not in config:
                config['viewsets'] = {}
            config['viewsets'][model_name] = viewset_config

        # API views (non-model views)
        if app.get('api', {}).get('custom_views'):
            for view in app['api']['custom_views']:
                config['api_views'].append(view)

        return config

    def _needs_base_viewsets(self, schema: Dict[str, Any]) -> bool:
        """Check if base viewset classes are needed."""
        # Check if any advanced features are used
        features = schema.get('features', {})

        if features.get('enterprise', {}).get('multitenancy'):
            return True

        if features.get('enterprise', {}).get('audit'):
            return True

        # Check for bulk operations
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                if model.get('api', {}).get('allow_bulk'):
                    return True

        return False

    def _generate_base_viewsets(self, schema: Dict[str, Any]) -> None:
        """Generate base viewset classes."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'api/base_viewsets.py.j2',
            'core/api/viewsets.py',
            ctx
        )

    def _needs_custom_permissions(self, app: Dict[str, Any]) -> bool:
        """Check if custom permission classes are needed."""
        for model in app.get('models', []):
            api_config = model.get('api', {})

            # Check for custom permissions
            if api_config.get('permissions'):
                for perm in api_config['permissions']:
                    if isinstance(perm, dict):  # Custom permission config
                        return True

            # Check for action-level permissions
            for action in api_config.get('custom_actions', []):
                if action.get('permission_classes'):
                    return True

        return False

    def _needs_custom_pagination(self, app: Dict[str, Any]) -> bool:
        """Check if custom pagination classes are needed."""
        for model in app.get('models', []):
            pagination = model.get('api', {}).get('pagination')
            if pagination and pagination != 'default':
                return True
        return False

    def _needs_throttling(self, app: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Check if throttling is needed."""
        # Global throttling
        if schema.get('features', {}).get('api', {}).get('throttling'):
            return True

        # Model-specific throttling
        for model in app.get('models', []):
            if model.get('api', {}).get('throttle'):
                return True

        return False

    def _get_required_imports(self, models: List[Dict[str, Any]], schema: Dict[str, Any],
                              view_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Determine required imports for views."""
        imports = {
            'rest_framework': [
                'from rest_framework import viewsets, status',
                'from rest_framework.decorators import action',
                'from rest_framework.response import Response',
            ],
            'django': [
                'from django.shortcuts import get_object_or_404',
                'from django.db.models import Q, Count, Sum, Avg',
            ],
            'app': [
                f"from .models import {', '.join(model['name'] for model in models)}",
                f"from .serializers import {', '.join(model['name'] + 'Serializer' for model in models)}",
            ],
            'project': [],
            'python': [],
        }

        # ViewSet types
        viewset_types = set()
        for vs_config in view_config['viewsets'].values():
            viewset_types.add(vs_config['type'])
            viewset_types.update(vs_config.get('mixins', []))

        if 'GenericViewSet' in viewset_types:
            imports['rest_framework'].append('from rest_framework.viewsets import GenericViewSet')

        # Mixins
        mixins_needed = list(view_config.get('mixins', set()))
        if mixins_needed:
            mixin_imports = ', '.join(m for m in mixins_needed if m.endswith('Mixin'))
            if mixin_imports:
                imports['rest_framework'].append(f'from rest_framework.mixins import {mixin_imports}')

        # Permissions
        imports['rest_framework'].append('from rest_framework.permissions import IsAuthenticated, AllowAny')

        # Filters
        if any(vs.get('filterset_fields') for vs in view_config['viewsets'].values()):
            imports['rest_framework'].append('from django_filters.rest_framework import DjangoFilterBackend')
            imports['rest_framework'].append('from rest_framework.filters import SearchFilter, OrderingFilter')
            imports['app'].append('from .filters import *')

        # Pagination
        if any(vs.get('pagination') for vs in view_config['viewsets'].values()):
            imports['rest_framework'].append('from rest_framework.pagination import PageNumberPagination')

        # Cache
        if 'cache_page' in view_config.get('decorators', set()):
            imports['django'].append('from django.views.decorators.cache import cache_page')
            imports['django'].append('from django.views.decorators.vary import vary_on_headers')

        # Transactions
        imports['django'].append('from django.db import transaction')

        # Features
        features = schema.get('features', {})

        # JWT
        if features.get('authentication', {}).get('jwt'):
            imports['rest_framework'].append('from rest_framework_simplejwt.authentication import JWTAuthentication')

        # Throttling
        if any(vs.get('throttle') for vs in view_config['viewsets'].values()):
            imports['rest_framework'].append('from rest_framework.throttling import UserRateThrottle, AnonRateThrottle')

        # Swagger
        imports['rest_framework'].append('from drf_spectacular.utils import extend_schema, OpenApiParameter')

        return imports