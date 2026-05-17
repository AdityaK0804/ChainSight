"""
Context processor to inject alert count into all templates.
"""
from .models import RiskAlert


def alert_count(request):
    """Add unresolved alert count to template context."""
    if request.user.is_authenticated:
        return {
            'unresolved_alert_count': RiskAlert.objects.filter(is_resolved=False).count()
        }
    return {}
