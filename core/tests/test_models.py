from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from core.models import Supplier, InventoryItem, Order, RiskAlert


class SupplierRiskLevelTest(TestCase):
    def _make(self, rate, delay):
        return Supplier(name='S', country='India', contact_email='a@b.com',
                        on_time_delivery_rate=rate, average_delay_days=delay,
                        lead_time_days=7)

    def test_low_risk(self):
        self.assertEqual(self._make(0.95, 0.5).risk_level, 'low')

    def test_medium_risk(self):
        self.assertEqual(self._make(0.80, 2.0).risk_level, 'medium')

    def test_high_risk(self):
        self.assertEqual(self._make(0.60, 5.0).risk_level, 'high')


class InventoryItemStatusTest(TestCase):
    def _make(self, stock, reorder):
        return InventoryItem(name='X', sku='X-001', category='component',
                             current_stock=stock, reorder_point=reorder, unit_cost=1.0)

    def test_out_of_stock(self):
        self.assertEqual(self._make(0, 50).stock_status, 'out_of_stock')

    def test_low_stock(self):
        self.assertEqual(self._make(30, 50).stock_status, 'low')

    def test_ok_stock(self):
        self.assertEqual(self._make(100, 50).stock_status, 'ok')

    def test_stock_value(self):
        item = InventoryItem(current_stock=100, unit_cost=5.0, name='T', sku='T-001',
                             category='component', reorder_point=10)
        self.assertEqual(item.stock_value, 500.0)


class OrderPropertiesTest(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(
            name='Test Supplier', country='India', contact_email='t@t.com',
            lead_time_days=7, on_time_delivery_rate=0.9, average_delay_days=0.5)
        self.item = InventoryItem.objects.create(
            name='Widget', sku='WID-001', category='component',
            current_stock=100, reorder_point=20, unit_cost=5.00)

    def test_total_value(self):
        order = Order(quantity=10, unit_price=5.00, supplier=self.supplier,
                      item=self.item, order_number='PO-001',
                      expected_delivery=timezone.now().date() + timedelta(days=7))
        self.assertEqual(float(order.total_value), 50.0)

    def test_is_overdue_true(self):
        order = Order(supplier=self.supplier, item=self.item, order_number='PO-002',
                      quantity=1, unit_price=1.0, status='in_transit',
                      expected_delivery=timezone.now().date() - timedelta(days=3))
        self.assertTrue(order.is_overdue)

    def test_is_overdue_false_if_delivered(self):
        order = Order(supplier=self.supplier, item=self.item, order_number='PO-003',
                      quantity=1, unit_price=1.0, status='delivered',
                      expected_delivery=timezone.now().date() - timedelta(days=3))
        self.assertFalse(order.is_overdue)

    def test_delay_days_overdue(self):
        order = Order(supplier=self.supplier, item=self.item, order_number='PO-004',
                      quantity=1, unit_price=1.0, status='in_transit',
                      expected_delivery=timezone.now().date() - timedelta(days=5))
        self.assertEqual(order.delay_days, 5)
