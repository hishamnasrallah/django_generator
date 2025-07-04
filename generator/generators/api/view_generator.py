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
        """Generate view files for all apps."""
        self.generated_files = []

        # Validate schema
        if not schema:
            return self.generated_files

        apps = schema.get('apps', [])
        if not apps:
            return self.generated_files

        for app in apps:
            if not app:
                continue
            if app.get('models'):
                self._generate_app_views(app, schema)

        # Generate base viewsets if needed
        if self._needs_base_viewsets(schema):
            self._generate_base_viewsets(schema)

        return self.generated_files

    def _generate_app_views(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate views for a single app."""
        if not app:
            return

        app_name = app.get('name', '')
        if not app_name:
            return

        models = app.get('models', [])
        if not models:
            return

        # Filter out None models
        valid_models = [m for m in models if m and m.get('name')]
        if not valid_models:
            return

        # Analyze what's needed
        view_config = self._analyze_view_requirements(app, schema)

        # Ensure view_config is never None and has all required keys
        if view_config is None:
            view_config = {}

        view_config.setdefault('viewsets', {})
        view_config.setdefault('api_views', [])
        view_config.setdefault('mixins', set())
        view_config.setdefault('decorators', set())

        # Prepare context with safe defaults
        ctx = {
            'app_name': app_name or '',
            'models': valid_models or [],
            'project': schema.get('project', {}) or {},
            'features': schema.get('features', {}) or {},
            'view_config': view_config or {},
            'imports': self._get_required_imports(valid_models, schema, view_config) or {},
            'has_custom_actions': False,
            'has_filters': False,
            'has_search': False,
            'has_bulk_operations': False,
        }

        # Check features safely
        for model in valid_models:
            if not model:
                continue
            api_config = model.get('api', {})
            if not api_config:
                continue

            if api_config.get('custom_actions'):
                ctx['has_custom_actions'] = True
            if api_config.get('filterset_fields'):
                ctx['has_filters'] = True
            if api_config.get('search_fields'):
                ctx['has_search'] = True
            if api_config.get('allow_bulk'):
                ctx['has_bulk_operations'] = True

        # Generate main views.py
        self.create_file_from_template(
            'app/api/views.py.j2',
            f'apps/{app_name}/views.py',
            ctx
        )

        # Generate additional files if needed
        if ctx['has_filters']:
            self.create_file_from_template(
                'app/api/filters.py.j2',
                f'apps/{app_name}/filters.py',
                ctx
            )

        if self._needs_custom_permissions(app):
            self.create_file_from_template(
                'app/api/permissions.py.j2',
                f'apps/{app_name}/permissions.py',
                ctx
            )

        if self._needs_custom_pagination(app):
            self.create_file_from_template(
                'app/api/pagination.py.j2',
                f'apps/{app_name}/pagination.py',
                ctx
            )

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

        if not app or not schema:
            return config

        features = schema.get('features', {}) or {}
        models = app.get('models', []) or []

        if not models:
            return config

        for model in models:
            if not model:
                continue

            model_name = model.get('name', '')
            if not model_name:
                continue

            api_config = model.get('api', {})
            if api_config is None:
                api_config = {}

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
                methods = api_config.get('allowed_methods', [])

                mixin_map = {
                    'GET': ['ListModelMixin', 'RetrieveModelMixin'],
                    'POST': ['CreateModelMixin'],
                    'PUT': ['UpdateModelMixin'],
                    'PATCH': ['UpdateModelMixin'],
                    'DELETE': ['DestroyModelMixin'],
                }

                for method in methods:
                    mixins = mixin_map.get(method, [])
                    viewset_config['mixins'].extend(mixins)

                # Remove duplicates
                viewset_config['mixins'] = list(set(viewset_config['mixins']))

            # Custom actions
            custom_actions = api_config.get('custom_actions', [])
            if custom_actions:
                for action in custom_actions:
                    if not action:
                        continue
                    action_config = {
                        'name': action.get('name', ''),
                        'methods': action.get('methods', ['POST']),
                        'detail': action.get('detail', True),
                        'permission_classes': action.get('permission_classes'),
                        'serializer_class': action.get('serializer_class'),
                        'description': action.get('description'),
                    }
                    viewset_config['actions'].append(action_config)
                config['decorators'].add('action')

            # Features requiring mixins
            if api_config.get('allow_bulk'):
                config['mixins'].add('BulkModelViewSet')

            if api_config.get('soft_delete'):
                config['mixins'].add('SoftDeleteMixin')

            # Safe performance config check
            performance_config = features.get('performance', {})
            if performance_config and performance_config.get('caching') and api_config.get('cache'):
                config['decorators'].add('cache_page')
                config['decorators'].add('vary_on_headers')

            # Store viewset config
            config['viewsets'][model_name] = viewset_config

        # API views (non-model views)
        app_api_config = app.get('api', {})
        if app_api_config:
            custom_views = app_api_config.get('custom_views', [])
            if custom_views:
                config['api_views'].extend(custom_views)

        return config

    def _needs_base_viewsets(self, schema: Dict[str, Any]) -> bool:
        """Check if base viewset classes are needed."""
        if not schema:
            return False

        # Check if any advanced features are used
        features = schema.get('features', {})
        if features:
            enterprise = features.get('enterprise', {})
            if enterprise:
                if enterprise.get('multitenancy'):
                    return True
                if enterprise.get('audit'):
                    return True

        # Check for bulk operations
        apps = schema.get('apps', [])
        if apps:
            for app in apps:
                if not app:
                    continue
                models = app.get('models', [])
                if models:
                    for model in models:
                        if not model:
                            continue
                        api_config = model.get('api', {})
                        if api_config and api_config.get('allow_bulk'):
                            return True

        return False

    def _generate_base_viewsets(self, schema: Dict[str, Any]) -> None:
        """Generate base viewset classes."""
        ctx = {
            'project': schema.get('project', {}),
            'features': schema.get('features', {}),
        }

        self.create_file_from_template(
            'api/base_viewsets.py.j2',
            'core/api/viewsets.py',
            ctx
        )

    def _needs_custom_permissions(self, app: Dict[str, Any]) -> bool:
        """Check if custom permission classes are needed."""
        if not app:
            return False

        models = app.get('models', [])
        if not models:
            return False

        for model in models:
            if not model:
                continue
            api_config = model.get('api', {})
            if not api_config:
                continue

            # Check for custom permissions
            permissions = api_config.get('permissions', [])
            if permissions:
                for perm in permissions:
                    if perm and isinstance(perm, dict):  # Custom permission config
                        return True

            # Check for action-level permissions
            custom_actions = api_config.get('custom_actions', [])
            if custom_actions:
                for action in custom_actions:
                    if action and action.get('permission_classes'):
                        return True

        return False

    def _needs_custom_pagination(self, app: Dict[str, Any]) -> bool:
        """Check if custom pagination classes are needed."""
        if not app:
            return False

        models = app.get('models', [])
        if not models:
            return False

        for model in models:
            if not model:
                continue
            api_config = model.get('api', {})
            if api_config:
                pagination = api_config.get('pagination')
                if pagination and pagination != 'default':
                    return True
        return False

    def _needs_throttling(self, app: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Check if throttling is needed."""
        # Global throttling
        if schema:
            features = schema.get('features', {})
            if features:
                api_features = features.get('api', {})
                if api_features and api_features.get('throttling'):
                    return True

        # Model-specific throttling
        if app:
            models = app.get('models', [])
            if models:
                for model in models:
                    if not model:
                        continue
                    api_config = model.get('api', {})
                    if api_config and api_config.get('throttle'):
                        return True

        return False

    def _get_required_imports(self, models: List[Dict[str, Any]], schema: Dict[str, Any],
                              view_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Determine required imports for views."""
        # Filter valid model names
        model_names = []
        for model in models:
            if model and model.get('name'):
                model_names.append(model.get('name'))

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
            'app': [],
            'project': [],
            'python': [],
        }

        # Add model imports only if we have valid models
        if model_names:
            imports['app'].append(f"from .models import {', '.join(model_names)}")
            imports['app'].append(f"from .serializers import {', '.join(name + 'Serializer' for name in model_names)}")

        # Safe view_config access
        if not view_config:
            view_config = {}

        # ViewSet types
        viewset_types = set()
        viewsets = view_config.get('viewsets', {})
        if viewsets:
            for vs_config in viewsets.values():
                if not vs_config:
                    continue
                viewset_type = vs_config.get('type', 'ModelViewSet')
                viewset_types.add(viewset_type)
                mixins = vs_config.get('mixins', [])
                if mixins:
                    viewset_types.update(mixins)

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
        has_filters = False
        if viewsets:
            for vs in viewsets.values():
                if vs and vs.get('filterset_fields'):
                    has_filters = True
                    break

        if has_filters:
            imports['rest_framework'].append('from django_filters.rest_framework import DjangoFilterBackend')
            imports['rest_framework'].append('from rest_framework.filters import SearchFilter, OrderingFilter')
            imports['app'].append('from .filters import *')

        # Pagination
        has_pagination = False
        if viewsets:
            for vs in viewsets.values():
                if vs and vs.get('pagination'):
                    has_pagination = True
                    break

        if has_pagination:
            imports['rest_framework'].append('from rest_framework.pagination import PageNumberPagination')

        # Cache
        decorators = view_config.get('decorators', set())
        if 'cache_page' in decorators:
            imports['django'].append('from django.views.decorators.cache import cache_page')
            imports['django'].append('from django.views.decorators.vary import vary_on_headers')

        # Transactions
        imports['django'].append('from django.db import transaction')

        # Features
        if schema:
            features = schema.get('features', {})
            if features:
                auth_features = features.get('authentication', {})
                if auth_features and auth_features.get('jwt'):
                    imports['rest_framework'].append('from rest_framework_simplejwt.authentication import JWTAuthentication')

        # Throttling
        has_throttle = False
        if viewsets:
            for vs in viewsets.values():
                if vs and vs.get('throttle'):
                    has_throttle = True
                    break

        if has_throttle:
            imports['rest_framework'].append('from rest_framework.throttling import UserRateThrottle, AnonRateThrottle')

        # Swagger
        imports['rest_framework'].append('from drf_spectacular.utils import extend_schema, OpenApiParameter')

        return imports