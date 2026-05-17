"""
Management command: seed_data
Populates the database with realistic demo data for ChainSight.
Idempotent — uses get_or_create.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Supplier, InventoryItem, Order, RiskAlert
from core.ml_engine import run_risk_analysis_for_all


SUPPLIERS = [
    {'name': 'Shenzhen Electronics Co.', 'country': 'China', 'contact_email': 'sales@shenzhen-elec.cn',
     'reliability_rating': 'high', 'lead_time_days': 14, 'on_time_delivery_rate': 0.92, 'average_delay_days': 0.8},
    {'name': 'Deutsche Precision GmbH', 'country': 'Germany', 'contact_email': 'info@deutsche-precision.de',
     'reliability_rating': 'high', 'lead_time_days': 10, 'on_time_delivery_rate': 0.96, 'average_delay_days': 0.3},
    {'name': 'Mumbai Materials Ltd.', 'country': 'India', 'contact_email': 'procurement@mumbai-mat.in',
     'reliability_rating': 'medium', 'lead_time_days': 12, 'on_time_delivery_rate': 0.78, 'average_delay_days': 2.5},
    {'name': 'Pacific Coast Components', 'country': 'USA', 'contact_email': 'orders@paccoast.com',
     'reliability_rating': 'high', 'lead_time_days': 5, 'on_time_delivery_rate': 0.94, 'average_delay_days': 0.4},
    {'name': 'Hanoi Manufacturing JSC', 'country': 'Vietnam', 'contact_email': 'export@hanoi-mfg.vn',
     'reliability_rating': 'low', 'lead_time_days': 18, 'on_time_delivery_rate': 0.68, 'average_delay_days': 4.2},
]

ITEMS = [
    {'name': 'Lithium-Ion Cell 3.7V', 'sku': 'BAT-001', 'category': 'component', 'current_stock': 320, 'reorder_point': 100, 'unit_cost': 2.85, 'supplier_idx': 0},
    {'name': 'OLED Display Module 6.1"', 'sku': 'DSP-042', 'category': 'component', 'current_stock': 45, 'reorder_point': 80, 'unit_cost': 28.50, 'supplier_idx': 0},
    {'name': 'Stainless Steel Frame', 'sku': 'FRM-103', 'category': 'raw_material', 'current_stock': 0, 'reorder_point': 50, 'unit_cost': 12.30, 'supplier_idx': 1},
    {'name': 'PCB Main Board v4', 'sku': 'PCB-204', 'category': 'component', 'current_stock': 180, 'reorder_point': 60, 'unit_cost': 45.00, 'supplier_idx': 1},
    {'name': 'Copper Wire Spool 500m', 'sku': 'COP-055', 'category': 'raw_material', 'current_stock': 25, 'reorder_point': 30, 'unit_cost': 18.75, 'supplier_idx': 2},
    {'name': 'Capacitor Ceramic 100µF', 'sku': 'CAP-312', 'category': 'component', 'current_stock': 4200, 'reorder_point': 1000, 'unit_cost': 0.12, 'supplier_idx': 0},
    {'name': 'Wireless Earbuds Pro', 'sku': 'WEP-099', 'category': 'finished_good', 'current_stock': 150, 'reorder_point': 200, 'unit_cost': 34.99, 'supplier_idx': 3},
    {'name': 'Smart Watch Band', 'sku': 'SWB-445', 'category': 'component', 'current_stock': 800, 'reorder_point': 300, 'unit_cost': 3.25, 'supplier_idx': 4},
    {'name': 'Recycled Cardboard Box', 'sku': 'PKG-001', 'category': 'packaging', 'current_stock': 2500, 'reorder_point': 500, 'unit_cost': 0.45, 'supplier_idx': 2},
    {'name': 'Foam Insert Tray', 'sku': 'PKG-022', 'category': 'packaging', 'current_stock': 1800, 'reorder_point': 400, 'unit_cost': 0.85, 'supplier_idx': 2},
    {'name': 'USB-C Connector', 'sku': 'CON-188', 'category': 'component', 'current_stock': 12, 'reorder_point': 200, 'unit_cost': 0.55, 'supplier_idx': 0},
    {'name': 'Tempered Glass Screen', 'sku': 'SCR-067', 'category': 'component', 'current_stock': 90, 'reorder_point': 100, 'unit_cost': 8.20, 'supplier_idx': 4},
    {'name': 'Bluetooth Module BT5.3', 'sku': 'BLU-331', 'category': 'component', 'current_stock': 350, 'reorder_point': 150, 'unit_cost': 6.10, 'supplier_idx': 3},
    {'name': 'Premium Gift Box Set', 'sku': 'PKG-088', 'category': 'packaging', 'current_stock': 30, 'reorder_point': 100, 'unit_cost': 2.90, 'supplier_idx': 2},
    {'name': 'Silicone Gasket Ring', 'sku': 'GAS-205', 'category': 'raw_material', 'current_stock': 5000, 'reorder_point': 800, 'unit_cost': 0.08, 'supplier_idx': 1},
]

ORDERS_TEMPLATE = [
    {'item_idx': 1, 'supplier_idx': 0, 'qty': 200, 'price': 28.50, 'status': 'in_transit', 'days_ago': 8, 'delivery_in': 4},
    {'item_idx': 2, 'supplier_idx': 1, 'qty': 150, 'price': 12.30, 'status': 'delayed', 'days_ago': 15, 'delivery_in': -3},
    {'item_idx': 4, 'supplier_idx': 2, 'qty': 100, 'price': 18.75, 'status': 'pending', 'days_ago': 2, 'delivery_in': 10},
    {'item_idx': 6, 'supplier_idx': 3, 'qty': 500, 'price': 34.99, 'status': 'confirmed', 'days_ago': 5, 'delivery_in': 3},
    {'item_idx': 7, 'supplier_idx': 4, 'qty': 1000, 'price': 3.25, 'status': 'in_transit', 'days_ago': 12, 'delivery_in': 5},
    {'item_idx': 10, 'supplier_idx': 0, 'qty': 800, 'price': 0.55, 'status': 'pending', 'days_ago': 1, 'delivery_in': 13},
    {'item_idx': 11, 'supplier_idx': 4, 'qty': 300, 'price': 8.20, 'status': 'delayed', 'days_ago': 20, 'delivery_in': -5},
    {'item_idx': 3, 'supplier_idx': 1, 'qty': 100, 'price': 45.00, 'status': 'delivered', 'days_ago': 30, 'delivery_in': -12},
    {'item_idx': 0, 'supplier_idx': 0, 'qty': 2000, 'price': 2.85, 'status': 'delivered', 'days_ago': 25, 'delivery_in': -8},
    {'item_idx': 5, 'supplier_idx': 0, 'qty': 5000, 'price': 0.12, 'status': 'confirmed', 'days_ago': 3, 'delivery_in': 11},
    {'item_idx': 8, 'supplier_idx': 2, 'qty': 3000, 'price': 0.45, 'status': 'in_transit', 'days_ago': 6, 'delivery_in': 6},
    {'item_idx': 9, 'supplier_idx': 2, 'qty': 2000, 'price': 0.85, 'status': 'pending', 'days_ago': 1, 'delivery_in': 11},
    {'item_idx': 12, 'supplier_idx': 3, 'qty': 400, 'price': 6.10, 'status': 'in_transit', 'days_ago': 7, 'delivery_in': 2},
    {'item_idx': 13, 'supplier_idx': 2, 'qty': 500, 'price': 2.90, 'status': 'delayed', 'days_ago': 18, 'delivery_in': -2},
    {'item_idx': 14, 'supplier_idx': 1, 'qty': 3000, 'price': 0.08, 'status': 'confirmed', 'days_ago': 4, 'delivery_in': 6},
    {'item_idx': 6, 'supplier_idx': 3, 'qty': 250, 'price': 34.99, 'status': 'cancelled', 'days_ago': 35, 'delivery_in': -15},
    {'item_idx': 1, 'supplier_idx': 0, 'qty': 100, 'price': 28.50, 'status': 'pending', 'days_ago': 0, 'delivery_in': 14},
    {'item_idx': 4, 'supplier_idx': 2, 'qty': 50, 'price': 18.75, 'status': 'in_transit', 'days_ago': 10, 'delivery_in': 1},
    {'item_idx': 7, 'supplier_idx': 4, 'qty': 600, 'price': 3.25, 'status': 'delayed', 'days_ago': 22, 'delivery_in': -4},
    {'item_idx': 3, 'supplier_idx': 1, 'qty': 80, 'price': 45.00, 'status': 'confirmed', 'days_ago': 6, 'delivery_in': 4},
]


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data for ChainSight.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # ── Suppliers ────────────────────────────────────────────────────
        self.stdout.write("Seeding suppliers...")
        suppliers = []
        for s_data in SUPPLIERS:
            supplier, created = Supplier.objects.get_or_create(
                name=s_data['name'],
                defaults=s_data,
            )
            suppliers.append(supplier)
            action = "Created" if created else "Exists"
            self.stdout.write(f"  {action}: {supplier}")

        # ── Inventory Items ──────────────────────────────────────────────
        self.stdout.write("\nSeeding inventory items...")
        items = []
        for i_data in ITEMS:
            supplier_idx = i_data.pop('supplier_idx')
            item, created = InventoryItem.objects.get_or_create(
                sku=i_data['sku'],
                defaults={**i_data, 'supplier': suppliers[supplier_idx]},
            )
            items.append(item)
            action = "Created" if created else "Exists"
            self.stdout.write(f"  {action}: {item}")
            i_data['supplier_idx'] = supplier_idx  # restore for idempotency

        # ── Orders ───────────────────────────────────────────────────────
        self.stdout.write("\nSeeding orders...")
        for idx, o_data in enumerate(ORDERS_TEMPLATE):
            order_number = f"PO-2025-{idx + 1:04d}"
            order_date = today - timedelta(days=o_data['days_ago'])
            expected_delivery = today + timedelta(days=o_data['delivery_in'])
            actual_delivery = None
            if o_data['status'] == 'delivered':
                actual_delivery = expected_delivery + timedelta(days=max(0, -o_data['delivery_in']))

            order, created = Order.objects.get_or_create(
                order_number=order_number,
                defaults={
                    'supplier': suppliers[o_data['supplier_idx']],
                    'item': items[o_data['item_idx']],
                    'quantity': o_data['qty'],
                    'unit_price': o_data['price'],
                    'status': o_data['status'],
                    'order_date': order_date,
                    'expected_delivery': expected_delivery,
                    'actual_delivery': actual_delivery,
                }
            )
            action = "Created" if created else "Exists"
            self.stdout.write(f"  {action}: {order}")

        # ── Run ML Analysis ──────────────────────────────────────────────
        self.stdout.write("\nRunning ML risk analysis...")
        result = run_risk_analysis_for_all()
        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Seeded {len(SUPPLIERS)} suppliers, {len(ITEMS)} items, "
            f"{len(ORDERS_TEMPLATE)} orders.\n"
            f"Risk analysis: {result['orders_scored']} orders scored, "
            f"{result['items_scored']} items scored, "
            f"{result['alerts_created']} alerts created."
        ))
