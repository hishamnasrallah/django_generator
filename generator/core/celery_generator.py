"""
Celery Task Generator
Generates Celery tasks for async processing
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class CeleryTaskGenerator(BaseGenerator):
    """
    Generates Celery tasks for asynchronous processing.
    
    Features:
    - Model-specific tasks
    - Bulk operations
    - Periodic tasks
    - Error handling and retries
    - Task monitoring
    """
    
    name = "CeleryTaskGenerator"
    description = "Generates Celery async tasks"
    version = "1.0.0"
    order = 45
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if Celery is enabled."""
        return schema.get('features', {}).get('performance', {}).get('celery', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate Celery task files for all apps."""
        self.generated_files = []
        
        # Generate main Celery configuration
        self._generate_celery_config(schema)
        
        # Generate app-specific tasks
        for app in schema.get('apps', []):
            if app.get('models'):
                self._generate_app_tasks(app, schema)
        
        # Generate periodic tasks
        self._generate_periodic_tasks(schema)
        
        return self.generated_files
    
    def _generate_celery_config(self, schema: Dict[str, Any]) -> None:
        """Generate main Celery configuration."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema.get('apps', []),
        }
        
        self.create_file_from_template(
            'performance/celery/celery_config.py.j2',
            f"{schema['project']['name']}/celery.py",
            ctx
        )
        
        # Generate beat schedule
        self.create_file_from_template(
            'performance/celery/beat_schedule.py.j2',
            f"{schema['project']['name']}/beat_schedule.py",
            ctx
        )
    
    def _generate_app_tasks(self, app: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Generate Celery tasks for a single app."""
        app_name = app['name']
        models = app.get('models', [])
        
        ctx = {
            'app_name': app_name,
            'models': models,
            'project': schema['project'],
            'features': schema.get('features', {}),
            'tasks': self._generate_tasks(models, app_name),
        }
        
        self.create_file_from_template(
            'performance/celery/tasks.py.j2',
            f'apps/{app_name}/tasks.py',
            ctx
        )
    
    def _generate_periodic_tasks(self, schema: Dict[str, Any]) -> None:
        """Generate periodic tasks configuration."""
        ctx = {
            'project': schema['project'],
            'apps': schema.get('apps', []),
            'features': schema.get('features', {}),
            'periodic_tasks': self._get_periodic_tasks(schema),
        }
        
        self.create_file_from_template(
            'performance/celery/periodic_tasks.py.j2',
            'core/periodic_tasks.py',
            ctx
        )
    
    def _generate_tasks(self, models: List[Dict[str, Any]], app_name: str) -> List[Dict[str, Any]]:
        """Generate task definitions for models."""
        tasks = []
        
        for model in models:
            model_name = model['name']
            
            # Bulk import task
            tasks.append({
                'name': f"process_{model_name.lower()}_import",
                'model_name': model_name,
                'task_type': 'import',
                'description': f"Process bulk import for {model_name}",
                'params': ['file_path'],
                'retry_policy': {
                    'max_retries': 3,
                    'countdown': 60,
                },
            })
            
            # Export task
            tasks.append({
                'name': f"generate_{model_name.lower()}_report",
                'model_name': model_name,
                'task_type': 'export',
                'description': f"Generate report for {model_name}",
                'params': ['filters'],
                'retry_policy': {
                    'max_retries': 2,
                    'countdown': 30,
                },
            })
            
            # Sync task (if external API integration)
            if model.get('integrations', {}).get('external_api'):
                tasks.append({
                    'name': f"sync_{model_name.lower()}_with_external_api",
                    'model_name': model_name,
                    'task_type': 'sync',
                    'description': f"Sync {model_name} with external API",
                    'params': ['instance_id'],
                    'rate_limit': '10/m',
                    'retry_policy': {
                        'max_retries': 5,
                        'countdown': 120,
                    },
                })
            
            # Cleanup task
            if model.get('features', {}).get('soft_delete'):
                tasks.append({
                    'name': f"cleanup_old_{model_name.lower()}_records",
                    'model_name': model_name,
                    'task_type': 'cleanup',
                    'description': f"Clean up old {model_name} records",
                    'params': ['days_old'],
                    'periodic': True,
                    'schedule': 'daily',
                })
        
        return tasks
    
    def _get_periodic_tasks(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get periodic task definitions."""
        periodic_tasks = [
            {
                'name': 'cleanup_old_sessions',
                'task': 'core.tasks.cleanup_old_sessions',
                'schedule': 'daily',
                'description': 'Clean up expired sessions',
            },
            {
                'name': 'update_search_index',
                'task': 'core.tasks.update_search_index',
                'schedule': 'hourly',
                'description': 'Update search index',
            },
            {
                'name': 'generate_daily_reports',
                'task': 'core.tasks.generate_daily_reports',
                'schedule': 'daily',
                'description': 'Generate daily reports',
            },
        ]
        
        # Add model-specific periodic tasks
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                if model.get('features', {}).get('soft_delete'):
                    periodic_tasks.append({
                        'name': f"cleanup_{model['name'].lower()}_records",
                        'task': f"apps.{app['name']}.tasks.cleanup_old_{model['name'].lower()}_records",
                        'schedule': 'weekly',
                        'description': f"Clean up old {model['name']} records",
                    })
        
        return periodic_tasks