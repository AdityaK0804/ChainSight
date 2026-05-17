"""
ChainSight DRF Serializers
"""

from rest_framework import serializers
from .models import Supplier, InventoryItem, Order, RiskAlert


class SupplierSerializer(serializers.ModelSerializer):
    risk_level = serializers.CharField(read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'country', 'contact_email', 'reliability_rating',
            'lead_time_days', 'on_time_delivery_rate', 'average_delay_days',
            'is_active', 'risk_level', 'created_at',
        ]


class InventoryItemSerializer(serializers.ModelSerializer):
    stock_status = serializers.CharField(read_only=True)
    stock_value = serializers.FloatField(read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default=None)

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'sku', 'category', 'supplier', 'supplier_name',
            'current_stock', 'reorder_point', 'reorder_quantity',
            'unit_cost', 'stockout_risk_score', 'stock_status', 'stock_value',
            'last_risk_updated', 'updated_at',
        ]


class OrderSerializer(serializers.ModelSerializer):
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    delay_days = serializers.IntegerField(read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'supplier', 'supplier_name',
            'item', 'item_sku', 'quantity', 'unit_price', 'total_value',
            'status', 'order_date', 'expected_delivery', 'actual_delivery',
            'delay_risk_score', 'is_overdue', 'delay_days', 'notes', 'created_at',
        ]


class RiskAlertSerializer(serializers.ModelSerializer):
    related_order_number = serializers.CharField(
        source='related_order.order_number', read_only=True, default=None
    )
    related_item_sku = serializers.CharField(
        source='related_item.sku', read_only=True, default=None
    )

    class Meta:
        model = RiskAlert
        fields = [
            'id', 'alert_type', 'severity', 'title', 'message',
            'related_order', 'related_order_number',
            'related_item', 'related_item_sku',
            'related_supplier', 'is_resolved', 'created_at',
        ]
