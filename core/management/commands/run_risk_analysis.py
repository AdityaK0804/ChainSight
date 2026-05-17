"""
Management command: run_risk_analysis
Triggers ML risk scoring on all orders and inventory items.
"""

from django.core.management.base import BaseCommand
from core.ml_engine import run_risk_analysis_for_all


class Command(BaseCommand):
    help = 'Run ML risk scoring on all orders and inventory'

    def handle(self, *args, **kwargs):
        result = run_risk_analysis_for_all()
        self.stdout.write(self.style.SUCCESS(
            f"Done. Orders scored: {result['orders_scored']}, "
            f"Items scored: {result['items_scored']}, "
            f"Alerts created: {result['alerts_created']}"
        ))
