"""
State Machine Generator
Generates Django FSM state machines for models
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class StateMachineGenerator(BaseGenerator):
    """
    Generates state machines for Django models using django-fsm.
    
    Features:
    - State definitions with choices
    - Transition methods with permissions
    - Pre/post transition logic
    - State validation
    - Transition logging
    """
    
    name = "StateMachineGenerator"
    description = "Generates Django FSM state machines"
    version = "1.0.0"
    order = 30
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if any models have state machines defined."""
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                if model.get('state_machine'):
                    return True
        return False
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate state machine files for all models."""
        self.generated_files = []
        
        for app in schema.get('apps', []):
            models_with_state_machines = []
            
            for model in app.get('models', []):
                if model.get('state_machine'):
                    models_with_state_machines.append(model)
            
            if models_with_state_machines:
                self._generate_app_state_machines(app['name'], models_with_state_machines, schema)
        
        return self.generated_files
    
    def _generate_app_state_machines(self, app_name: str, models: List[Dict[str, Any]], schema: Dict[str, Any]) -> None:
        """Generate state machine file for an app."""
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'state_machines': self._process_state_machines(models),
            'features': schema.get('features', {}),
        }
        
        self.create_file_from_template(
            'business_logic/workflows/state_machine.py.j2',
            f'apps/{app_name}/state_machines.py',
            ctx
        )
        
        # Generate transition helpers
        self.create_file_from_template(
            'business_logic/workflows/transitions.py.j2',
            f'apps/{app_name}/transitions.py',
            ctx
        )
    
    def _process_state_machines(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process state machine configurations."""
        processed = []
        
        for model in models:
            state_machine = model.get('state_machine', {})
            if not state_machine:
                continue
            
            processed_sm = {
                'model_name': model['name'],
                'field': state_machine.get('field', 'status'),
                'initial': state_machine.get('initial', 'draft'),
                'states': self._process_states(state_machine.get('states', [])),
                'transitions': self._process_transitions(state_machine.get('transitions', [])),
                'permissions': self._generate_permissions(state_machine.get('transitions', [])),
                'logging': state_machine.get('logging', True),
            }
            
            processed.append(processed_sm)
        
        return processed
    
    def _process_states(self, states: List) -> List[Dict[str, Any]]:
        """Process state definitions."""
        processed_states = []
        
        for state in states:
            if isinstance(state, str):
                processed_states.append({
                    'value': state,
                    'label': self.naming.to_title_case(state),
                    'description': f"{self.naming.to_title_case(state)} state"
                })
            elif isinstance(state, dict):
                processed_states.append({
                    'value': state['value'],
                    'label': state.get('label', self.naming.to_title_case(state['value'])),
                    'description': state.get('description', f"{state['value']} state")
                })
            elif isinstance(state, (list, tuple)) and len(state) >= 2:
                processed_states.append({
                    'value': state[0],
                    'label': state[1],
                    'description': state[2] if len(state) > 2 else f"{state[1]} state"
                })
        
        return processed_states
    
    def _process_transitions(self, transitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process transition definitions."""
        processed_transitions = []
        
        for transition in transitions:
            processed_transition = {
                'name': transition['name'],
                'source': transition.get('source', []),
                'target': transition['target'],
                'permission': transition.get('permission'),
                'condition': transition.get('condition'),
                'pre_logic': transition.get('pre_logic', ''),
                'post_logic': transition.get('post_logic', ''),
                'description': transition.get('description', f"Transition to {transition['target']}"),
                'params': transition.get('params', []),
            }
            
            # Ensure source is a list
            if isinstance(processed_transition['source'], str):
                processed_transition['source'] = [processed_transition['source']]
            
            processed_transitions.append(processed_transition)
        
        return processed_transitions
    
    def _generate_permissions(self, transitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate permissions for transitions."""
        permissions = []
        
        for transition in transitions:
            if transition.get('permission'):
                permissions.append({
                    'codename': transition['permission'],
                    'name': f"Can {transition['name']}",
                    'description': f"Permission to execute {transition['name']} transition"
                })
        
        return permissions