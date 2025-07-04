"""
Business Logic Generators

This module contains generators for business logic components:
- Service layer (service pattern)
- State machines
- Workflows
- Event-driven architecture
- Business rules engine
"""
from .service_generator import ServiceGenerator
from .state_machine_generator import StateMachineGenerator
from .workflow_generator import WorkflowGenerator
from .event_generator import EventGenerator
from .rule_engine_generator import RuleEngineGenerator

__all__ = [
    'ServiceGenerator',
    'StateMachineGenerator',
    'WorkflowGenerator',
    'EventGenerator',
    'RuleEngineGenerator',
]

# Generator metadata
BUSINESS_LOGIC_GENERATORS = [
    ServiceGenerator,
    StateMachineGenerator,
    WorkflowGenerator,
    EventGenerator,
    RuleEngineGenerator,
]

# Category metadata
CATEGORY_INFO = {
    'name': 'business_logic',
    'display_name': 'Business Logic',
    'description': 'Generators for business logic and domain layer components',
    'order': 60,
    'generators': BUSINESS_LOGIC_GENERATORS,
}

def get_business_logic_generators():
    """Get all business logic generators."""
    return BUSINESS_LOGIC_GENERATORS

def get_generator_by_name(name: str):
    """Get a specific business logic generator by name."""
    for generator in BUSINESS_LOGIC_GENERATORS:
        if generator.name == name:
            return generator
    return None

def get_generator_dependencies():
    """Get dependency graph for business logic generators."""
    dependencies = {}

    for generator in BUSINESS_LOGIC_GENERATORS:
        dependencies[generator.name] = {
            'requires': list(generator.requires),
            'provides': list(generator.provides),
            'order': generator.order,
        }

    return dependencies