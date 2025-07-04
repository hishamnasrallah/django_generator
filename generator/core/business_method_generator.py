"""
Business Method Generator
Generates business logic methods for Django models
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
import re

from .base_generator import BaseGenerator, GeneratedFile


class BusinessMethodGenerator(BaseGenerator):
    """
    Generates business logic methods for Django models.
    
    Supports:
    - Discount calculations
    - Status transitions
    - Validation methods
    - Property calculations
    - Custom business logic
    """
    
    name = "BusinessMethodGenerator"
    description = "Generates business logic methods for models"
    version = "1.0.0"
    order = 25
    
    def __init__(self, settings=None):
        super().__init__(settings)
        self.method_templates = {
            'discount_calculation': self._discount_calculation_template,
            'status_transition': self._status_transition_template,
            'validation_method': self._validation_method_template,
            'property_calculation': self._property_calculation_template,
            'custom_logic': self._custom_logic_template,
        }
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if any models have business logic defined."""
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                if model.get('business_logic'):
                    return True
        return False
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate business methods for all models."""
        self.generated_files = []
        
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                business_logic = model.get('business_logic', {})
                if business_logic:
                    self._generate_model_business_methods(model, app['name'], schema)
        
        return self.generated_files
    
    def _generate_model_business_methods(self, model: Dict[str, Any], app_name: str, schema: Dict[str, Any]) -> None:
        """Generate business methods for a single model."""
        model_name = model['name']
        business_logic = model.get('business_logic', {})
        
        # Prepare context
        ctx = {
            'model_name': model_name,
            'app_name': app_name,
            'business_logic': business_logic,
            'methods': self._process_methods(business_logic.get('methods', [])),
            'properties': self._process_properties(business_logic.get('properties', [])),
            'managers': business_logic.get('managers', []),
            'signals': business_logic.get('signals', {}),
            'project': schema['project'],
        }
        
        # Generate business logic file
        self.create_file_from_template(
            'app/models/business_logic.py.j2',
            f'apps/{app_name}/business/{model_name.lower()}_business.py',
            ctx
        )
    
    def _process_methods(self, methods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and generate method implementations."""
        processed_methods = []
        
        for method in methods:
            method_type = method.get('logic_template', 'custom_logic')
            template_func = self.method_templates.get(method_type, self.method_templates['custom_logic'])
            
            processed_method = {
                'name': method['name'],
                'params': method.get('params', []),
                'returns': method.get('returns', 'Any'),
                'description': method.get('description', f"Business method: {method['name']}"),
                'implementation': template_func(method),
                'decorators': method.get('decorators', []),
            }
            
            processed_methods.append(processed_method)
        
        return processed_methods
    
    def _process_properties(self, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and generate property implementations."""
        processed_properties = []
        
        for prop in properties:
            logic = prop.get('logic', {})
            
            processed_prop = {
                'name': prop['name'],
                'returns': prop.get('returns', 'Any'),
                'description': prop.get('description', f"Property: {prop['name']}"),
                'implementation': self._generate_property_logic(logic),
                'cached': prop.get('cached', False),
            }
            
            processed_properties.append(processed_prop)
        
        return processed_properties
    
    def _discount_calculation_template(self, method: Dict[str, Any]) -> str:
        """Generate discount calculation method."""
        return f'''
def {method['name']}(self, percentage):
    """Calculate discount amount based on percentage."""
    if not isinstance(percentage, (int, float, Decimal)):
        raise TypeError("Percentage must be a number")
    
    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100")
    
    discount_amount = self.price * Decimal(str(percentage)) / 100
    return self.price - discount_amount
'''
    
    def _status_transition_template(self, method: Dict[str, Any]) -> str:
        """Generate status transition method."""
        target_status = method.get('target_status', 'active')
        return f'''
def {method['name']}(self, user=None, reason=None):
    """Transition model to {target_status} status."""
    from django.utils import timezone
    from .models import StatusLog
    
    old_status = self.status
    self.status = '{target_status}'
    
    # Validate transition
    if not self._can_transition_to('{target_status}'):
        raise ValueError(f"Cannot transition from {{old_status}} to {target_status}")
    
    self.save()
    
    # Log transition
    StatusLog.objects.create(
        content_type=ContentType.objects.get_for_model(self),
        object_id=self.pk,
        old_status=old_status,
        new_status='{target_status}',
        user=user,
        reason=reason,
        timestamp=timezone.now()
    )
    
    return True
'''
    
    def _validation_method_template(self, method: Dict[str, Any]) -> str:
        """Generate validation method."""
        validation_rules = method.get('validation_rules', [])
        rules_code = []
        
        for rule in validation_rules:
            if rule['type'] == 'required':
                rules_code.append(f'''
        if not self.{rule['field']}:
            raise ValidationError("{rule['field']} is required")''')
            elif rule['type'] == 'min_value':
                rules_code.append(f'''
        if self.{rule['field']} < {rule['value']}:
            raise ValidationError("{rule['field']} must be at least {rule['value']}")''')
            elif rule['type'] == 'max_value':
                rules_code.append(f'''
        if self.{rule['field']} > {rule['value']}:
            raise ValidationError("{rule['field']} must be at most {rule['value']}")''')
        
        return f'''
def {method['name']}(self):
    """Validate business rules for this model."""
    from django.core.exceptions import ValidationError
    
    errors = []
    
    try:
{''.join(rules_code)}
    except ValidationError as e:
        errors.append(str(e))
    
    if errors:
        raise ValidationError(errors)
    
    return True
'''
    
    def _property_calculation_template(self, method: Dict[str, Any]) -> str:
        """Generate property calculation method."""
        calculation = method.get('calculation', {})
        
        return f'''
@property
def {method['name']}(self):
    """Calculate {method['name']} based on business rules."""
    {self._generate_calculation_logic(calculation)}
'''
    
    def _custom_logic_template(self, method: Dict[str, Any]) -> str:
        """Generate custom logic method."""
        implementation = method.get('implementation', 'pass')
        
        return f'''
def {method['name']}(self{', ' + ', '.join(method.get('params', [])) if method.get('params') else ''}):
    """{method.get('description', f'Custom business method: {method["name"]}')}"""
    {implementation}
'''
    
    def _generate_property_logic(self, logic: Dict[str, Any]) -> str:
        """Generate property logic based on configuration."""
        if 'field' in logic and 'operation' in logic:
            field = logic['field']
            operation = logic['operation']
            value = logic.get('value', 0)
            
            if operation == '>':
                return f'return self.{field} > {value}'
            elif operation == '<':
                return f'return self.{field} < {value}'
            elif operation == '>=':
                return f'return self.{field} >= {value}'
            elif operation == '<=':
                return f'return self.{field} <= {value}'
            elif operation == '==':
                return f'return self.{field} == {value}'
            elif operation == '!=':
                return f'return self.{field} != {value}'
        
        return 'return None'
    
    def _generate_calculation_logic(self, calculation: Dict[str, Any]) -> str:
        """Generate calculation logic."""
        if calculation.get('type') == 'sum':
            fields = calculation.get('fields', [])
            return f"return {' + '.join(f'(self.{field} or 0)' for field in fields)}"
        elif calculation.get('type') == 'average':
            fields = calculation.get('fields', [])
            return f"return ({' + '.join(f'(self.{field} or 0)' for field in fields)}) / {len(fields)}"
        elif calculation.get('type') == 'percentage':
            numerator = calculation.get('numerator')
            denominator = calculation.get('denominator')
            return f"return (self.{numerator} / self.{denominator} * 100) if self.{denominator} else 0"
        
        return 'return None'