"""
Generator modules for Django Enhanced Generator.
This file imports and registers all available generators.
"""

# Import all generators to make them discoverable

# Project generators
from .project.structure_generator import ProjectStructureGenerator

# App generators
from .app.model_generator import ModelGenerator
from .app.admin_generator import AdminGenerator
from .app.form_generator import FormGenerator
from .app.signal_generator import SignalGenerator

# API generators
from .api.serializer_generator import SerializerGenerator
from .api.view_generator import ViewGenerator
from .api.url_generator import URLGenerator
from .api.rest_generator import RestGenerator
from .api.graphql_generator import GraphQLGenerator
from .api.websocket_generator import WebSocketGenerator
from .api.documentation_generator import DocumentationGenerator

# Auth generators
from .auth.jwt_generator import JWTGenerator
from .auth.oauth_generator import OAuthGenerator
from .auth.permission_generator import PermissionGenerator
from .auth.two_factor_generator import TwoFactorGenerator

# Database generators
from .database.migration_generator import MigrationGenerator
from .database.seed_generator import SeedGenerator
from .database.index_generator import IndexGenerator
from .database.optimization_generator import OptimizationGenerator

# Testing generators
from .testing.unit_test_generator import UnitTestGenerator
from .testing.integration_test_generator import IntegrationTestGenerator
from .testing.factory_generator import FactoryGenerator
from .testing.fixture_generator import FixtureGenerator
from .testing.performance_test_generator import PerformanceTestGenerator

# Business logic generators
from .business_logic.service_generator import ServiceGenerator
from .business_logic.event_generator import EventGenerator
from .business_logic.rule_engine_generator import RuleEngineGenerator
from .business_logic.state_machine_generator import StateMachineGenerator
from .business_logic.workflow_generator import WorkflowGenerator

# Enterprise generators
from .enterprise.audit_generator import AuditGenerator
from .enterprise.multitenancy_generator import MultitenancyGenerator
from .enterprise.compliance_generator import ComplianceGenerator
from .enterprise.backup_generator import BackupGenerator

# Integration generators
from .integration.email_generator import EmailGenerator
from .integration.sms_generator import SMSGenerator
from .integration.payment_generator import PaymentGenerator
from .integration.storage_generator import StorageGenerator
from .integration.search_generator import SearchGenerator
from .integration.analytics_generator import AnalyticsGenerator

# Performance generators
from .performance.cache_generator import CacheGenerator
from .performance.celery_generator import CeleryGenerator
from .performance.monitoring_generator import MonitoringGenerator
from .performance.optimization_generator import OptimizationGenerator

# Export all generators
__all__ = [
    # Project generators
    'ProjectStructureGenerator',
    
    # App generators
    'ModelGenerator',
    'AdminGenerator',
    'FormGenerator',
    'SignalGenerator',
    
    # API generators
    'SerializerGenerator',
    'ViewGenerator',
    'URLGenerator',
    'RestGenerator',
    'GraphQLGenerator',
    'WebSocketGenerator',
    'DocumentationGenerator',
    
    # Auth generators
    'JWTGenerator',
    'OAuthGenerator',
    'PermissionGenerator',
    'TwoFactorGenerator',
    
    # Database generators
    'MigrationGenerator',
    'SeedGenerator',
    'IndexGenerator',
    'OptimizationGenerator',
    
    # Testing generators
    'UnitTestGenerator',
    'IntegrationTestGenerator',
    'FactoryGenerator',
    'FixtureGenerator',
    'PerformanceTestGenerator',
    
    # Business logic generators
    'ServiceGenerator',
    'EventGenerator',
    'RuleEngineGenerator',
    'StateMachineGenerator',
    'WorkflowGenerator',
    
    # Enterprise generators
    'AuditGenerator',
    'MultitenancyGenerator',
    'ComplianceGenerator',
    'BackupGenerator',
    
    # Integration generators
    'EmailGenerator',
    'SMSGenerator',
    'PaymentGenerator',
    'StorageGenerator',
    'SearchGenerator',
    'AnalyticsGenerator',
    
    # Performance generators
    'CacheGenerator',
    'CeleryGenerator',
    'MonitoringGenerator',
    'OptimizationGenerator',
]