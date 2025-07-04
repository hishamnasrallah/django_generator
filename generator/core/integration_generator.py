"""
Integration Generator
Generates external service integrations
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class IntegrationGenerator(BaseGenerator):
    """
    Generates external service integrations.
    
    Features:
    - Email service integration
    - SMS service integration
    - Storage service integration
    - Analytics integration
    - Social media integration
    """
    
    name = "IntegrationGenerator"
    description = "Generates external service integrations"
    version = "1.0.0"
    order = 75
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if any integrations are enabled."""
        return bool(schema.get('features', {}).get('integrations'))
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate integration files."""
        self.generated_files = []
        
        integrations = schema.get('features', {}).get('integrations', {})
        
        # Generate email integration
        if integrations.get('email'):
            self._generate_email_integration(schema, integrations['email'])
        
        # Generate SMS integration
        if integrations.get('sms'):
            self._generate_sms_integration(schema, integrations['sms'])
        
        # Generate storage integration
        if integrations.get('storage'):
            self._generate_storage_integration(schema, integrations['storage'])
        
        # Generate analytics integration
        if integrations.get('analytics'):
            self._generate_analytics_integration(schema, integrations['analytics'])
        
        return self.generated_files
    
    def _generate_email_integration(self, schema: Dict[str, Any], email_config: Dict[str, Any]) -> None:
        """Generate email service integration."""
        ctx = {
            'project': schema['project'],
            'email_config': email_config,
        }
        
        self.create_file_from_template(
            'integrations/communication/email_service.py.j2',
            'core/integrations/email.py',
            ctx
        )
    
    def _generate_sms_integration(self, schema: Dict[str, Any], sms_config: Dict[str, Any]) -> None:
        """Generate SMS service integration."""
        ctx = {
            'project': schema['project'],
            'sms_config': sms_config,
        }
        
        self.create_file_from_template(
            'integrations/communication/sms_service.py.j2',
            'core/integrations/sms.py',
            ctx
        )
    
    def _generate_storage_integration(self, schema: Dict[str, Any], storage_config: Dict[str, Any]) -> None:
        """Generate storage service integration."""
        ctx = {
            'project': schema['project'],
            'storage_config': storage_config,
        }
        
        if storage_config.get('provider') == 's3':
            self.create_file_from_template(
                'integrations/storage/s3_storage.py.j2',
                'core/integrations/storage/s3.py',
                ctx
            )
        elif storage_config.get('provider') == 'gcs':
            self.create_file_from_template(
                'integrations/storage/gcs_storage.py.j2',
                'core/integrations/storage/gcs.py',
                ctx
            )
        
        # Generate storage service interface
        self.create_file_from_template(
            'integrations/storage/storage_service.py.j2',
            'core/integrations/storage/service.py',
            ctx
        )
    
    def _generate_analytics_integration(self, schema: Dict[str, Any], analytics_config: Dict[str, Any]) -> None:
        """Generate analytics integration."""
        ctx = {
            'project': schema['project'],
            'analytics_config': analytics_config,
        }
        
        self.create_file_from_template(
            'integrations/analytics/analytics_service.py.j2',
            'core/integrations/analytics.py',
            ctx
        )