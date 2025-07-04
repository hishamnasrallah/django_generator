"""
Event Generator
Generates event-driven architecture components
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.base_generator import BaseGenerator, GeneratedFile
from ...utils.naming_conventions import NamingConventions

logger = logging.getLogger(__name__)


class EventGenerator(BaseGenerator):
    """
    Generates event-driven components with:
    - Event definitions
    - Event subscribers/handlers
    - Event publishers
    - Event bus implementation
    """

    name = "EventGenerator"
    description = "Generates event-driven architecture components"
    version = "1.0.0"
    order = 68
    category = "business_logic"
    requires = {'ModelGenerator'}
    provides = {'EventGenerator', 'events'}
    tags = {'events', 'pub_sub', 'architecture'}

    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if schema needs event system."""
        if not schema or not isinstance(schema, dict):
            return False

        # Check if event-driven architecture is enabled
        architecture = schema.get('architecture', {})
        if not architecture.get('patterns', {}).get('event_driven', False):
            return False

        # Check if any model has events
        apps = schema.get('apps', [])
        for app in apps:
            if app and isinstance(app, dict):
                # App-level events
                if app.get('events'):
                    return True

                # Model-level events
                models = app.get('models', [])
                for model in models:
                    if model and isinstance(model, dict):
                        if model.get('events'):
                            return True

        return False

    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate event system files."""
        self.generated_files = []

        if not schema:
            logger.error("Schema is None or empty")
            return self.generated_files

        apps = schema.get('apps', [])
        if not apps:
            logger.warning("No apps found in schema")
            return self.generated_files

        # Generate core event system if needed
        if self._needs_core_event_system(schema):
            self._generate_core_event_system(schema)

        for app in apps:
            if not app or not isinstance(app, dict):
                logger.warning("Skipping invalid app entry")
                continue

            if self._has_events(app):
                self._generate_app_events(app, schema)

        return self.generated_files

    def _needs_core_event_system(self, schema: Dict[str, Any]) -> bool:
        """Check if core event system needs to be generated."""
        architecture = schema.get('architecture', {})
        return architecture.get('patterns', {}).get('event_driven', False)

    def _has_events(self, app: Dict[str, Any]) -> bool:
        """Check if app has events."""
        if app.get('events'):
            return True

        models = app.get('models', [])
        for model in models:
            if model and isinstance(model, dict):
                if model.get('events'):
                    return True

        return False

    def _generate_core_event_system(self, schema: Dict[str, Any]) -> None:
        """Generate core event system infrastructure."""
        # Create core events directory
        self.create_directory('core/events')
        self.create_file('core/events/__init__.py', '')

        ctx = {
            'project_name': schema.get('project', {}).get('name', 'project'),
            'features': schema.get('features', {}),
        }

        # Generate event bus
        self.create_file_from_template(
            'core/events/bus.py.j2',
            'core/events/bus.py',
            ctx
        )

        # Generate base event classes
        self.create_file_from_template(
            'core/events/base.py.j2',
            'core/events/base.py',
            ctx
        )

        # Generate event registry
        self.create_file_from_template(
            'core/events/registry.py.j2',
            'core/events/registry.py',
            ctx
        )

    def _generate_app_events(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate event files for app."""
        app_name = app.get('name')
        if not app_name:
            logger.error("App missing 'name' field")
            return

        # Create events directory
        self.create_directory(f'apps/{app_name}/events')
        self.create_file(f'apps/{app_name}/events/__init__.py', '')

        # Collect all events
        all_events = self._collect_app_events(app)

        if not all_events['model_events'] and not all_events['app_events']:
            return

        # Prepare context
        ctx = {
            'app_name': app_name,
            'models': [m for m in app.get('models', []) if m and isinstance(m, dict) and m.get('events')],
            'app_events': all_events['app_events'],
            'cross_model_events': all_events['cross_model_events'],
            'features': schema.get('features', {}),
            'has_celery': schema.get('features', {}).get('celery', {}).get('enabled', False),
            'has_channels': schema.get('features', {}).get('websocket', {}).get('enabled', False),
        }

        # Generate event definitions
        self.create_file_from_template(
            'business_logic/events/events.py.j2',
            f'apps/{app_name}/events/events.py',
            ctx
        )

        # Generate subscribers
        self.create_file_from_template(
            'business_logic/events/subscribers.py.j2',
            f'apps/{app_name}/events/subscribers.py',
            ctx
        )

        # Generate publishers
        self.create_file_from_template(
            'business_logic/events/publishers.py.j2',
            f'apps/{app_name}/events/publishers.py',
            ctx
        )

        # Generate event handlers if complex logic
        if self._has_complex_event_handlers(all_events):
            self.create_file_from_template(
                'business_logic/events/handlers.py.j2',
                f'apps/{app_name}/events/handlers.py',
                ctx
            )

    def _collect_app_events(self, app: Dict[str, Any]) -> Dict[str, Any]:
        """Collect all events in the app."""
        result = {
            'model_events': [],
            'app_events': [],
            'cross_model_events': [],
        }

        # App-level events
        for event in app.get('events', []):
            enhanced_event = self._enhance_event_config(event, None)

            if enhanced_event.get('cross_model'):
                result['cross_model_events'].append(enhanced_event)
            else:
                result['app_events'].append(enhanced_event)

        # Model-level events
        for model in app.get('models', []):
            if model and isinstance(model, dict):
                for event in model.get('events', []):
                    enhanced_event = self._enhance_event_config(event, model)
                    result['model_events'].append({
                        'model_name': model['name'],
                        'event': enhanced_event
                    })

        return result

    def _enhance_event_config(self, event: Dict[str, Any], model: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhance event configuration."""
        enhanced = event.copy()

        # Default name
        if 'name' not in enhanced and model:
            enhanced['name'] = f"{model['name']}{event.get('type', 'Changed')}"

        # Default signal
        if 'signal' not in enhanced:
            event_type = enhanced.get('type', 'changed').lower()
            if event_type in ['created', 'saved']:
                enhanced['signal'] = 'post_save'
            elif event_type == 'deleted':
                enhanced['signal'] = 'post_delete'
            elif event_type == 'changed':
                enhanced['signal'] = 'post_save'
            else:
                enhanced['signal'] = 'post_save'

        # Default actions
        if 'actions' not in enhanced:
            enhanced['actions'] = []

        # Add default actions based on features
        default_actions = []

        # Always log
        default_actions.append({
            'type': 'log',
            'level': 'info'
        })

        # Cache invalidation
        if model and model.get('features', {}).get('caching'):
            default_actions.append({
                'type': 'cache_invalidate'
            })

        # Broadcasting
        if enhanced.get('broadcast', False):
            default_actions.append({
                'type': 'broadcast'
            })

        # Webhooks
        if enhanced.get('webhook', False):
            default_actions.append({
                'type': 'webhook'
            })

        # Merge with existing actions
        for action in default_actions:
            if not any(a.get('type') == action['type'] for a in enhanced['actions']):
                enhanced['actions'].append(action)

        # Conditions
        if 'conditions' not in enhanced:
            enhanced['conditions'] = []

        # Add created condition for post_save
        if enhanced['signal'] == 'post_save' and event.get('type') == 'created':
            enhanced['conditions'].append('self.created')

        return enhanced

    def _has_complex_event_handlers(self, events: Dict[str, Any]) -> bool:
        """Check if events have complex handlers requiring separate file."""
        for event_list in events.values():
            for event in event_list:
                if isinstance(event, dict):
                    event_data = event.get('event', event)
                    for action in event_data.get('actions', []):
                        if action.get('type') == 'custom' and len(action.get('implementation', '')) > 50:
                            return True
        return False