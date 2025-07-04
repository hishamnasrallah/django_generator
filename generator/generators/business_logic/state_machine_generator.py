"""
State Machine Generator
Generates state machine implementations for models
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class StateMachineGenerator(BaseGenerator):
    """
    Generates state machine implementations with:
    - FSM field definitions
    - State transitions
    - Transition conditions and actions
    - State change logging
    """

    name = "StateMachineGenerator"
    description = "Generates state machine implementations"
    version = "1.0.0"
    order = 65
    category = "business_logic"
    requires = {'ModelGenerator'}
    provides = {'StateMachineGenerator', 'state_machines'}
    tags = {'state_machines', 'fsm', 'transitions'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema has state machines."""
        if not schema or not isinstance(schema, dict):
            return False

        # Check if any model has state machine
        apps = schema.get('apps', [])
        for app in apps:
            if app and isinstance(app, dict):
                models = app.get('models', [])
                for model in models:
                    if model and isinstance(model, dict):
                        if model.get('state_machine'):
                            return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate state machine files."""
        self.generated_files = []

        if not schema:
            logger.error("Schema is None or empty")
            return self.generated_files

        apps = schema.get('apps', [])
        if not apps:
            logger.warning("No apps found in schema")
            return self.generated_files

        for app in apps:
            if not app or not isinstance(app, dict):
                logger.warning("Skipping invalid app entry")
                continue

            if self._has_state_machines(app):
                self._generate_app_state_machines(app, schema)

        return self.generated_files

    def _has_state_machines(self, app: Dict[str, Any]) -> bool:
        """Check if app has models with state machines."""
        models = app.get('models', [])
        for model in models:
            if model and isinstance(model, dict):
                if model.get('state_machine'):
                    return True
        return False

    def _generate_app_state_machines(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate state machine files for app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        # Collect all state machines
        state_machines = []
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                sm_config = model.get('state_machine')
                if sm_config:
                    state_machines.append({
                        'model_name': model['name'],
                        'model': model,
                        **self._enhance_state_machine(sm_config, model)
                    })

        if not state_machines:
            return

        # Create directories
        self.create_directory(f'apps/{app_name}/state_machines')
        self.create_file(f'apps/{app_name}/workflows/__init__.py', '')

        # Prepare context
        ctx = {
            'app_name': app_name,
            'state_machines': state_machines,
            'features': schema.get('features', {}),
            'has_celery': schema.get('features', {}).get('celery', {}).get('enabled', False),
            'has_signals': True,  # Always use signals for state machines
        }

        # Generate main state machine file
        self.create_file_from_template(
            'business_logic/workflows/machines.py.j2',
            f'apps/{app_name}/workflows/machines.py',
            ctx
        )

        # Generate transition handlers
        self.create_file_from_template(
            'business_logic/workflows/handlers.py.j2',
            f'apps/{app_name}/workflows/handlers.py',
            ctx
        )

        # Generate state machine mixins
        self.create_file_from_template(
            'business_logic/workflows/mixins.py.j2',
            f'apps/{app_name}/workflows/mixins.py',
            ctx
        )

        # Update model to include state machine mixin
        self._update_model_config(app, state_machines)

    def _enhance_state_machine(self, sm_config: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance state machine configuration."""
        enhanced = sm_config.copy()

        # Default field
        if 'field' not in enhanced:
            enhanced['field'] = 'status'

        # Default initial state
        if 'initial' not in enhanced:
            states = enhanced.get('states', [])
            if states:
                enhanced['initial'] = states[0] if isinstance(states[0], str) else states[0].get('value')

        # Enhance states
        states = []
        for state in enhanced.get('states', []):
            if isinstance(state, str):
                states.append({
                    'value': state,
                    'label': NamingConventions.to_title_case(state),
                    'description': f'{state} state'
                })
            else:
                states.append(state)
        enhanced['states'] = states

        # Enhance transitions
        transitions = []
        for trans in enhanced.get('transitions', []):
            if isinstance(trans, dict):
                transition = trans.copy()

                # Ensure name
                if 'name' not in transition:
                    transition['name'] = f"transition_to_{transition.get('target', 'unknown')}"

                # Ensure source is list
                if isinstance(transition.get('source'), str):
                    transition['source'] = [transition['source']]
                elif transition.get('source') == '*':
                    # All states except target
                    transition['source'] = [s['value'] for s in states if s['value'] != transition.get('target')]

                # Add permission
                if 'permission' not in transition and model:
                    transition['permission'] = f"{app_name}.{model['name'].lower()}_transition_{transition['name']}"

                # Add conditions
                if 'conditions' not in transition:
                    transition['conditions'] = []

                # Add hooks
                if 'pre_transition' not in transition:
                    transition['pre_transition'] = []
                if 'post_transition' not in transition:
                    transition['post_transition'] = []

                transitions.append(transition)

        enhanced['transitions'] = transitions

        # Add features
        enhanced['features'] = {
            'logging': enhanced.get('logging', True),
            'signals': enhanced.get('signals', True),
            'permissions': enhanced.get('permissions', True),
            'validation': enhanced.get('validation', True),
            'notifications': enhanced.get('notifications', False),
        }

        return enhanced

    def _update_model_config(self, app: Dict[str, Any], state_machines: List[Dict[str, Any]]) -> None:
        """Update model configuration to include state machine."""
        for sm in state_machines:
            model_name = sm['model_name']

            # Find model in app
            for model in app.get('models', []):
                if model and isinstance(model, dict) and model.get('name') == model_name:
                    # Add state machine mixin
                    if 'mixins' not in model:
                        model['mixins'] = []

                    mixin_name = f"{model_name}StateMachineMixin"
                    if mixin_name not in model['mixins']:
                        model['mixins'].append(mixin_name)

                    # Add state field to fields if not exists
                    field_name = sm['field']
                    field_exists = any(
                        f.get('name') == field_name
                        for f in model.get('fields', [])
                        if f and isinstance(f, dict)
                    )

                    if not field_exists:
                        if 'fields' not in model:
                            model['fields'] = []

                        model['fields'].append({
                            'name': field_name,
                            'type': 'CharField',
                            'max_length': 50,
                            'choices': [(s['value'], s['label']) for s in sm['states']],
                            'default': sm['initial'],
                            'help_text': 'Current state'
                        })