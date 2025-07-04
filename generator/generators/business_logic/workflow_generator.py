"""
Workflow Generator
Generates workflow and state machine implementations
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class WorkflowGenerator(BaseGenerator):
    """
    Generates workflow implementations with:
    - State machines
    - Workflow definitions
    - Transition logic
    - Workflow execution engine
    """

    name = "WorkflowGenerator"
    description = "Generates workflow and state machine implementations"
    version = "1.0.0"
    order = 70
    category = "business_logic"
    requires = {'ModelGenerator'}
    provides = {'WorkflowGenerator', 'workflows'}
    tags = {'workflows', 'state_machines', 'business_logic'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema needs workflows."""
        if not schema or not isinstance(schema, dict):
            return False

        # Check if any app has workflows or state machines
        apps = schema.get('apps', [])
        for app in apps:
            if app and isinstance(app, dict):
                # Check for app-level workflows
                if app.get('workflows'):
                    return True

                # Check for model state machines
                models = app.get('models', [])
                for model in models:
                    if model and isinstance(model, dict):
                        if model.get('state_machine'):
                            return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate workflow files."""
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

            if self._should_generate_workflows(app):
                self._generate_app_workflows(app, schema)

        return self.generated_files

    def _should_generate_workflows(self, app: Dict[str, Any]) -> bool:
        """Check if workflows should be generated for this app."""
        # Check for workflows
        if app.get('workflows'):
            return True

        # Check for state machines in models
        models = app.get('models', [])
        for model in models:
            if model and isinstance(model, dict):
                if model.get('state_machine'):
                    return True

        return False

    def _generate_app_workflows(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate workflow files for a single app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        # Create workflow directories
        workflow_dirs = [
            f'apps/{app_name}/workflows',
        ]

        for dir_path in workflow_dirs:
            self.create_directory(dir_path)
            self.create_file(f"{dir_path}/__init__.py", "")

        # Collect state machines from models
        state_machines = []
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                state_machine = model.get('state_machine')
                if state_machine:
                    state_machines.append({
                        'model_name': model['name'],
                        **self._enhance_state_machine_config(state_machine, model)
                    })

        # Prepare context
        ctx = {
            'app_name': app_name,
            'state_machines': state_machines,
            'workflows': self._enhance_workflows(app.get('workflows', [])),
            'features': schema.get('features', {}),
        }

        # Generate state machine file if needed
        if state_machines:
            self.create_file_from_template(
                'business_logic/workflows/state_machine.py.j2',
                f'apps/{app_name}/workflows/state_machine.py',
                ctx
            )

        # Generate transitions helper
        if state_machines or ctx['workflows']:
            self.create_file_from_template(
                'business_logic/workflows/transitions.py.j2',
                f'apps/{app_name}/workflows/transitions.py',
                ctx
            )

        # Generate workflow definitions
        if ctx['workflows']:
            self.create_file_from_template(
                'business_logic/workflows/workflow.py.j2',
                f'apps/{app_name}/workflows/workflow.py',
                ctx
            )

    def _enhance_state_machine_config(self, state_machine: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance state machine configuration."""
        enhanced = state_machine.copy()

        # Default field name
        if 'field' not in enhanced:
            enhanced['field'] = 'status'

        # Ensure states have proper structure
        states = enhanced.get('states', [])
        enhanced_states = []
        for state in states:
            if isinstance(state, str):
                enhanced_states.append({
                    'value': state,
                    'label': NamingConventions.to_title_case(state)
                })
            else:
                enhanced_states.append(state)
        enhanced['states'] = enhanced_states

        # Enhance transitions
        transitions = enhanced.get('transitions', [])
        enhanced_transitions = []
        for transition in transitions:
            if isinstance(transition, dict):
                trans = transition.copy()

                # Ensure source is a list
                if isinstance(trans.get('source'), str):
                    trans['source'] = [trans['source']]

                # Add default permission if not specified
                if 'permission' not in trans:
                    trans['permission'] = f"{model['name'].lower()}.transition_{trans['name']}"

                enhanced_transitions.append(trans)
        enhanced['transitions'] = enhanced_transitions

        # Add logging flag
        if 'logging' not in enhanced:
            enhanced['logging'] = True

        return enhanced

    def _enhance_workflows(self, workflows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance workflow configurations."""
        enhanced = []

        for workflow in workflows:
            if isinstance(workflow, dict):
                wf = workflow.copy()

                # Enhance steps
                steps = wf.get('steps', [])
                enhanced_steps = []

                for i, step in enumerate(steps):
                    if isinstance(step, dict):
                        s = step.copy()

                        # Mark first step as initial
                        if i == 0 and 'initial' not in s:
                            s['initial'] = True

                        # Default on_success and on_failure
                        if 'on_success' not in s:
                            # Link to next step or END
                            if i < len(steps) - 1:
                                s['on_success'] = [steps[i + 1].get('name', f'step_{i+1}')]
                            else:
                                s['on_success'] = ['END']

                        if 'on_failure' not in s:
                            s['on_failure'] = ['END']

                        enhanced_steps.append(s)

                wf['steps'] = enhanced_steps
                enhanced.append(wf)

        return enhanced