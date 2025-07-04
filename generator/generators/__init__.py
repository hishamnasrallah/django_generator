"""
Generator modules for Django Enhanced Generator.
This file imports and registers all available generators.
"""

# Import all generators to make them discoverable
# Core generators
from generator.core.business_method_generator import BusinessMethodGenerator
from generator.core.cache_generator import CacheGenerator
from generator.core.celery_generator import CeleryTaskGenerator
from generator.core.custom_manager_generator import CustomManagerGenerator
from generator.core.elasticsearch_generator import ElasticsearchGenerator
from generator.core.enhanced_project_generator import EnhancedProjectGenerator
from generator.core.graphql_generator import GraphQLGenerator
from generator.core.integration_generator import IntegrationGenerator
from generator.core.monitoring_generator import MonitoringGenerator
from generator.core.payment_generator import PaymentGatewayGenerator
from generator.core.rule_engine_generator import RuleEngineGenerator
from generator.core.state_machine_generator import StateMachineGenerator
from generator.core.websocket_generator import WebSocketGenerator

# App generators
from generator.generators.api.serializer_generator import SerializerGenerator
from generator.generators.api.view_generator import ViewGenerator
from generator.generators.app.model_generator import ModelGenerator
from generator.generators.project.structure_generator import ProjectStructureGenerator

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