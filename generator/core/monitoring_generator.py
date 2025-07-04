"""
Monitoring Generator
Generates monitoring and analytics integration
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class MonitoringGenerator(BaseGenerator):
    """
    Generates monitoring and analytics integration.
    
    Features:
    - Prometheus metrics
    - Health checks
    - Performance monitoring
    - Error tracking
    - Custom dashboards
    """
    
    name = "MonitoringGenerator"
    description = "Generates monitoring and analytics integration"
    version = "1.0.0"
    order = 70
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if monitoring is enabled."""
        return schema.get('features', {}).get('performance', {}).get('monitoring', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate monitoring files."""
        self.generated_files = []
        
        # Generate core monitoring components
        self._generate_monitoring_core(schema)
        
        # Generate health checks
        self._generate_health_checks(schema)
        
        # Generate metrics
        self._generate_metrics(schema)
        
        return self.generated_files
    
    def _generate_monitoring_core(self, schema: Dict[str, Any]) -> None:
        """Generate core monitoring components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema.get('apps', []),
        }
        
        # Prometheus configuration
        self.create_file_from_template(
            'performance/monitoring/prometheus.py.j2',
            'core/monitoring/prometheus.py',
            ctx
        )
        
        # Sentry configuration
        self.create_file_from_template(
            'performance/monitoring/sentry_config.py.j2',
            'core/monitoring/sentry.py',
            ctx
        )
        
        # Monitoring middleware
        self.create_file_from_template(
            'performance/monitoring/middleware.py.j2',
            'core/monitoring/middleware.py',
            ctx
        )
    
    def _generate_health_checks(self, schema: Dict[str, Any]) -> None:
        """Generate health check components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema.get('apps', []),
        }
        
        self.create_file_from_template(
            'performance/monitoring/health_checks.py.j2',
            'core/monitoring/health.py',
            ctx
        )
    
    def _generate_metrics(self, schema: Dict[str, Any]) -> None:
        """Generate custom metrics."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'apps': schema.get('apps', []),
            'metrics': self._get_custom_metrics(schema),
        }
        
        self.create_file_from_template(
            'performance/monitoring/metrics.py.j2',
            'core/monitoring/metrics.py',
            ctx
        )
    
    def _get_custom_metrics(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get custom metrics definitions."""
        metrics = []
        
        # Add model-specific metrics
        for app in schema.get('apps', []):
            for model in app.get('models', []):
                metrics.extend([
                    {
                        'name': f"{model['name'].lower()}_total",
                        'type': 'Counter',
                        'description': f"Total number of {model['name']} objects",
                        'labels': ['status'],
                    },
                    {
                        'name': f"{model['name'].lower()}_operations",
                        'type': 'Counter',
                        'description': f"{model['name']} operations",
                        'labels': ['operation', 'status'],
                    },
                ])
        
        return metrics