"""
Business Rule Engine Generator
Generates business rule engine for complex business logic
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class RuleEngineGenerator(BaseGenerator):
    """
    Generates business rule engine for complex business logic.
    
    Features:
    - Rule definitions and conditions
    - Rule execution engine
    - Rule validation
    - Rule chaining
    - Dynamic rule loading
    """
    
    name = "RuleEngineGenerator"
    description = "Generates business rule engine"
    version = "1.0.0"
    order = 50
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if any models have business rules defined."""
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                if model.get('business_rules'):
                    return True
        return False
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate rule engine files."""
        self.generated_files = []
        
        # Generate core rule engine
        self._generate_core_rule_engine(schema)
        
        # Generate app-specific rules
        for app in schema.get('apps', []):
            models_with_rules = [m for m in app.get('models', []) if m.get('business_rules')]
            if models_with_rules:
                self._generate_app_rules(app['name'], models_with_rules, schema)
        
        return self.generated_files
    
    def _generate_core_rule_engine(self, schema: Dict[str, Any]) -> None:
        """Generate core rule engine components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
        }
        
        # Rule engine base
        self.create_file_from_template(
            'business_logic/rules/rule_engine.py.j2',
            'core/rules/engine.py',
            ctx
        )
        
        # Rule conditions
        self.create_file_from_template(
            'business_logic/rules/conditions.py.j2',
            'core/rules/conditions.py',
            ctx
        )
        
        # Rule validators
        self.create_file_from_template(
            'business_logic/rules/validators.py.j2',
            'core/rules/validators.py',
            ctx
        )
    
    def _generate_app_rules(self, app_name: str, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> None:
        """Generate rules for a single app."""
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'rules': self._process_rules(models),
        }
        
        self.create_file_from_template(
            'business_logic/rules/app_rules.py.j2',
            f'apps/{app_name}/rules.py',
            ctx
        )
    
    def _process_rules(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process business rules for models."""
        processed_rules = []
        
        for model in models:
            business_rules = model.get('business_rules', [])
            
            for rule in business_rules:
                processed_rule = {
                    'name': rule['name'],
                    'model_name': model['name'],
                    'description': rule.get('description', f"Business rule: {rule['name']}"),
                    'conditions': rule.get('conditions', []),
                    'actions': rule.get('actions', []),
                    'priority': rule.get('priority', 100),
                    'enabled': rule.get('enabled', True),
                    'rule_type': rule.get('type', 'validation'),
                }
                
                processed_rules.append(processed_rule)
        
        return processed_rules