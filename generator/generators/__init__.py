"""
Generator modules for Django Enhanced Generator.
This file imports and registers all available generators.
"""

# Import all generators to make them discoverable
# Core generators
from ..core.business_method_generator import BusinessMethodGenerator
from ..core.cache_generator import CacheGenerator
from ..core.celery_generator import CeleryTaskGenerator
from ..core.custom_manager_generator import CustomManagerGenerator
from ..core.elasticsearch_generator import ElasticsearchGenerator
from ..core.enhanced_project_generator import EnhancedProjectGenerator
from ..core.graphql_generator import GraphQLGenerator
from ..core.integration_generator import IntegrationGenerator
from ..core.monitoring_generator import MonitoringGenerator
from ..core.payment_generator import PaymentGatewayGenerator
from ..core.rule_engine_generator import RuleEngineGenerator
from ..core.state_machine_generator import StateMachineGenerator
from ..core.websocket_generator import WebSocketGenerator

# App generators
from .api.serializer_generator import SerializerGenerator
from .api.view_generator import ViewGenerator
from .app.model_generator import ModelGenerator
from .project.structure_generator import ProjectStructureGenerator

# Export all generators
__all__ = [
    # Core generators
    'BusinessMethodGenerator',
    'CacheGenerator',
    'CeleryTaskGenerator',
    'CustomManagerGenerator',
    'ElasticsearchGenerator',
    'EnhancedProjectGenerator',
    'GraphQLGenerator',
    'IntegrationGenerator',
    'MonitoringGenerator',
    'PaymentGatewayGenerator',
    'RuleEngineGenerator',
    'StateMachineGenerator',
    'WebSocketGenerator',
    
    # App generators
    'SerializerGenerator',
    'ViewGenerator',
    'ModelGenerator',
    'ProjectStructureGenerator',
]