"""
Rule Engine Generator
Generates business rules engine implementation
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class RuleEngineGenerator(BaseGenerator):
    """
    Generates rule engine with:
    - Rule definitions
    - Condition evaluators
    - Rule validators
    - Rule execution engine
    """

    name = "RuleEngineGenerator"
    description = "Generates business rules engine"
    version = "1.0.0"
    order = 69
    category = "business_logic"
    requires = {'ModelGenerator'}
    provides = {'RuleEngineGenerator', 'rules'}
    tags = {'rules', 'business_logic', 'validation'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema needs rule engine."""
        if not schema or not isinstance(schema, dict):
            return False

        # Check if rule engine is enabled
        architecture = schema.get('architecture', {})
        if not architecture.get('patterns', {}).get('rule_engine', False):
            return False

        # Check if any model has rules
        apps = schema.get('apps', [])
        for app in apps:
            if app and isinstance(app, dict):
                # App-level rules
                if app.get('rules'):
                    return True

                # Model-level rules
                models = app.get('models', [])
                for model in models:
                    if model and isinstance(model, dict):
                        if model.get('rules') or model.get('validators'):
                            return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate rule engine files."""
        self.generated_files = []

        if not schema:
            logger.error("Schema is None or empty")
            return self.generated_files

        apps = schema.get('apps', [])
        if not apps:
            logger.warning("No apps found in schema")
            return self.generated_files

        # Generate core rule engine if needed
        if self._needs_core_rule_engine(schema):
            self._generate_core_rule_engine(schema)

        for app in apps:
            if not app or not isinstance(app, dict):
                logger.warning("Skipping invalid app entry")
                continue

            if self._has_rules(app):
                self._generate_app_rules(app, schema)

        return self.generated_files

    def _needs_core_rule_engine(self, schema: Dict[str, Any]) -> bool:
        """Check if core rule engine needs to be generated."""
        architecture = schema.get('architecture', {})
        return architecture.get('patterns', {}).get('rule_engine', False)

    def _has_rules(self, app: Dict[str, Any]) -> bool:
        """Check if app has rules."""
        if app.get('rules'):
            return True

        models = app.get('models', [])
        for model in models:
            if model and isinstance(model, dict):
                if model.get('rules') or model.get('validators'):
                    return True

        return False

    def _generate_core_rule_engine(self, schema: Dict[str, Any]) -> None:
        """Generate core rule engine infrastructure."""
        # Create core rules directory
        self.create_directory('core/rules')
        self.create_file('core/rules/__init__.py', '')

        ctx = {
            'project_name': schema.get('project', {}).get('name', 'project'),
            'features': schema.get('features', {}),
        }

        # Generate rule engine core
        self.create_file_from_template(
            'core/rules/engine.py.j2',
            'core/rules/engine.py',
            ctx
        )

        # Generate base rule classes
        self.create_file_from_template(
            'core/rules/base.py.j2',
            'core/rules/base.py',
            ctx
        )

        # Generate rule registry
        self.create_file_from_template(
            'core/rules/registry.py.j2',
            'core/rules/registry.py',
            ctx
        )

    def _generate_app_rules(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate rule files for app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        # Create rules directory
        self.create_directory(f'apps/{app_name}/rules')
        self.create_file(f'apps/{app_name}/rules/__init__.py', '')

        # Collect all rules and validators
        all_rules = self._collect_app_rules(app)
        all_validators = self._collect_app_validators(app)

        if not all_rules and not all_validators:
            return

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': app.get('models', []),
            'app_rules': all_rules['app_rules'],
            'model_rules': all_rules['model_rules'],
            'validators': all_validators,
            'features': schema.get('features', {}),
            'has_celery': schema.get('features', {}).get('celery', {}).get('enabled', False),
        }

        # Generate conditions
        self.create_file_from_template(
            'business_logic/rules/conditions.py.j2',
            f'apps/{app_name}/rules/conditions.py',
            ctx
        )

        # Generate validators
        if all_validators:
            self.create_file_from_template(
                'business_logic/rules/validators.py.j2',
                f'apps/{app_name}/rules/validators.py',
                ctx
            )

        # Generate rule engine
        self.create_file_from_template(
            'business_logic/rules/rule_engine.py.j2',
            f'apps/{app_name}/rules/rule_engine.py',
            ctx
        )

        # Generate rule sets if complex rules
        if self._has_complex_rules(all_rules):
            self.create_file_from_template(
                'business_logic/rules/rule_sets.py.j2',
                f'apps/{app_name}/rules/rule_sets.py',
                ctx
            )

    def _collect_app_rules(self, app: Dict[str, Any]) -> Dict[str, Any]:
        """Collect all rules in the app."""
        result = {
            'app_rules': [],
            'model_rules': [],
        }

        # App-level rules
        for rule in app.get('rules', []):
            result['app_rules'].append(self._enhance_rule_config(rule, None))

        # Model-level rules
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                model_rules = []
                for rule in model.get('rules', []):
                    model_rules.append(self._enhance_rule_config(rule, model))

                if model_rules:
                    result['model_rules'].append({
                        'model_name': model['name'],
                        'rules': model_rules
                    })

        return result

    def _collect_app_validators(self, app: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all validators in the app."""
        validators = []

        # Model validators
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                for validator in model.get('validators', []):
                    validators.append({
                        'model_name': model['name'],
                        **self._enhance_validator_config(validator, model)
                    })

        return validators

    def _enhance_rule_config(self, rule: Dict[str, Any], model: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhance rule configuration."""
        enhanced = rule.copy()

        # Default type
        if 'type' not in enhanced:
            if any(action.get('type') == 'validate' for action in enhanced.get('actions', [])):
                enhanced['type'] = 'validation'
            elif any(action.get('type') == 'calculate' for action in enhanced.get('actions', [])):
                enhanced['type'] = 'calculation'
            else:
                enhanced['type'] = 'constraint'

        # Default priority
        if 'priority' not in enhanced:
            if enhanced['type'] == 'validation':
                enhanced['priority'] = 'high'
            else:
                enhanced['priority'] = 'normal'

        # Default mode
        if 'mode' not in enhanced:
            enhanced['mode'] = 'sync'

        # Default enabled
        if 'enabled' not in enhanced:
            enhanced['enabled'] = True

        # Enhance conditions
        conditions = []
        for cond in enhanced.get('conditions', []):
            if isinstance(cond, dict):
                condition = cond.copy()

                # Default operator
                if 'operator' not in condition:
                    condition['operator'] = 'equals'

                conditions.append(condition)
        enhanced['conditions'] = conditions

        # Enhance actions
        actions = []
        for action in enhanced.get('actions', []):
            if isinstance(action, dict):
                act = action.copy()

                # Add default params
                if 'params' not in act:
                    act['params'] = {}

                actions.append(act)
        enhanced['actions'] = actions

        return enhanced

    def _enhance_validator_config(self, validator: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance validator configuration."""
        enhanced = validator.copy()

        # Default implementation
        if 'implementation' not in enhanced and 'type' in enhanced:
            validator_type = enhanced['type']

            if validator_type == 'required':
                enhanced['implementation'] = '''
if not value:
    raise ValidationError(f"{field_name} is required")
'''
            elif validator_type == 'unique':
                enhanced['implementation'] = f'''
if {model['name']}.objects.filter({enhanced.get('field', 'value')}=value).exclude(pk=instance.pk if instance.pk else None).exists():
    raise ValidationError(f"{{{enhanced.get('field', 'value')}}} must be unique")
'''
            elif validator_type == 'custom':
                enhanced['implementation'] = '''
# Custom validation logic here
pass
'''

        return enhanced

    def _has_complex_rules(self, rules: Dict[str, Any]) -> bool:
        """Check if rules are complex enough to need separate rule sets."""
        total_rules = len(rules.get('app_rules', [])) + sum(
            len(mr['rules']) for mr in rules.get('model_rules', [])
        )

        if total_rules > 10:
            return True

        # Check for complex conditions
        for rule_list in [rules.get('app_rules', [])] + [mr['rules'] for mr in rules.get('model_rules', [])]:
            for rule in rule_list:
                if len(rule.get('conditions', [])) > 3:
                    return True
                if len(rule.get('actions', [])) > 2:
                    return True

        return False