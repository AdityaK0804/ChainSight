from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import Supplier, InventoryItem, Order, RiskAlert
from django.utils import timezone
from datetime import timedelta
import json


class ViewAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password123')

    def test_landing_no_auth_required(self):
        res = self.client.get(reverse('landing'))
        self.assertEqual(res.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 302)

    def test_dashboard_loads_authenticated(self):
        self.client.login(username='testuser', password='password123')
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Operations Overview')

    def test_products_loads(self):
        self.client.login(username='testuser', password='password123')
        res = self.client.get(reverse('products'))
        self.assertEqual(res.status_code, 200)

    def test_alerts_loads(self):
        self.client.login(username='testuser', password='password123')
        res = self.client.get(reverse('alerts'))
        self.assertEqual(res.status_code, 200)

    def test_products_search(self):
        supplier = Supplier.objects.create(name='S', country='IN', contact_email='a@b.com',
                                           lead_time_days=7, on_time_delivery_rate=0.9, average_delay_days=0.5)
        InventoryItem.objects.create(name='Special Widget', sku='SPW-001', category='component',
                                     current_stock=100, reorder_point=20, unit_cost=5.0, supplier=supplier)
        self.client.login(username='testuser', password='password123')
        res = self.client.get(reverse('products') + '?q=Special')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'SPW-001')

    def test_upload_rejects_non_csv(self):
        self.client.login(username='testuser', password='password123')
        from io import BytesIO
        fake_file = BytesIO(b'not a csv')
        fake_file.name = 'data.txt'
        res = self.client.post(reverse('upload'), {'file': fake_file},
                               HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 400)

    def test_run_forecast_requires_post(self):
        self.client.login(username='testuser', password='password123')
        res = self.client.get(reverse('run_forecast'))
        self.assertEqual(res.status_code, 405)
