from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from core.models import Supplier, InventoryItem, Order, RiskAlert
from django.utils import timezone
from datetime import timedelta


class APIEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('apiuser', 'api@test.com', 'password123')
        self.client.force_authenticate(user=self.user)

        self.supplier = Supplier.objects.create(
            name='Test Co', country='Germany', contact_email='t@t.de',
            lead_time_days=10, on_time_delivery_rate=0.95, average_delay_days=0.3)
        self.item = InventoryItem.objects.create(
            name='Test Part', sku='TST-001', category='component',
            current_stock=200, reorder_point=50, unit_cost=12.50, supplier=self.supplier)

    def test_suppliers_list(self):
        res = self.client.get('/api/suppliers/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('results', res.data)

    def test_inventory_list(self):
        res = self.client.get('/api/inventory/')
        self.assertEqual(res.status_code, 200)

    def test_inventory_low_stock_filter(self):
        InventoryItem.objects.create(name='Low', sku='LOW-001', category='component',
                                     current_stock=10, reorder_point=100, unit_cost=1.0)
        res = self.client.get('/api/inventory/?low_stock=true')
        self.assertEqual(res.status_code, 200)
        skus = [i['sku'] for i in res.data['results']]
        self.assertIn('LOW-001', skus)

    def test_orders_list(self):
        res = self.client.get('/api/orders/')
        self.assertEqual(res.status_code, 200)

    def test_alerts_list(self):
        res = self.client.get('/api/alerts/')
        self.assertEqual(res.status_code, 200)

    def test_dashboard_stats(self):
        res = self.client.get('/api/dashboard/stats/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('total_items', res.data)
        self.assertIn('unresolved_alerts', res.data)

    def test_resolve_alert(self):
        alert = RiskAlert.objects.create(
            alert_type='stockout', severity='warning',
            title='Test Alert', message='Test message')
        self.assertFalse(alert.is_resolved)
        res = self.client.post(f'/api/alerts/{alert.id}/resolve/')
        self.assertEqual(res.status_code, 200)
        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)

    def test_resolve_nonexistent_alert(self):
        res = self.client.post('/api/alerts/99999/resolve/')
        self.assertEqual(res.status_code, 404)
