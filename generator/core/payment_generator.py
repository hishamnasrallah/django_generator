"""
Payment Gateway Generator
Generates payment processing integration
"""
from typing import Dict, Any, List, Optional

from .base_generator import BaseGenerator, GeneratedFile


class PaymentGatewayGenerator(BaseGenerator):
    """
    Generates payment gateway integration.
    
    Features:
    - Multiple payment providers
    - Payment processing workflows
    - Webhook handling
    - Transaction logging
    - Refund processing
    """
    
    name = "PaymentGatewayGenerator"
    description = "Generates payment gateway integration"
    version = "1.0.0"
    order = 65
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Check if payment integration is enabled."""
        return schema.get('features', {}).get('integrations', {}).get('payment', False)
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate payment integration files."""
        self.generated_files = []
        
        payment_config = schema.get('features', {}).get('integrations', {}).get('payment', {})
        
        # Generate core payment components
        self._generate_payment_core(schema, payment_config)
        
        # Generate provider-specific implementations
        providers = payment_config.get('providers', ['stripe'])
        for provider in providers:
            self._generate_payment_provider(provider, schema)
        
        return self.generated_files
    
    def _generate_payment_core(self, schema: Dict[str, Any], payment_config: Dict[str, Any]) -> None:
        """Generate core payment components."""
        ctx = {
            'project': schema['project'],
            'features': schema.get('features', {}),
            'payment_config': payment_config,
        }
        
        # Payment service interface
        self.create_file_from_template(
            'integrations/payment/payment_service.py.j2',
            'core/payments/service.py',
            ctx
        )
        
        # Payment models
        self.create_file_from_template(
            'integrations/payment/models.py.j2',
            'core/payments/models.py',
            ctx
        )
        
        # Payment serializers
        self.create_file_from_template(
            'integrations/payment/serializers.py.j2',
            'core/payments/serializers.py',
            ctx
        )
        
        # Payment views
        self.create_file_from_template(
            'integrations/payment/views.py.j2',
            'core/payments/views.py',
            ctx
        )
        
        # Webhook handlers
        self.create_file_from_template(
            'integrations/payment/webhooks.py.j2',
            'core/payments/webhooks.py',
            ctx
        )
    
    def _generate_payment_provider(self, provider: str, schema: Dict[str, Any]) -> None:
        """Generate provider-specific payment implementation."""
        ctx = {
            'project': schema['project'],
            'provider': provider,
            'provider_class': f"{provider.title()}Gateway",
        }
        
        if provider == 'stripe':
            self.create_file_from_template(
                'integrations/payment/stripe_gateway.py.j2',
                'core/payments/gateways/stripe.py',
                ctx
            )
        elif provider == 'paypal':
            self.create_file_from_template(
                'integrations/payment/paypal_gateway.py.j2',
                'core/payments/gateways/paypal.py',
                ctx
            )