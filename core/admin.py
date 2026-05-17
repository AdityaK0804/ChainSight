"""
ChainSight Admin Configuration
"""

from django.contrib import admin
from .models import Supplier, InventoryItem, Order, RiskAlert


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'reliability_rating', 'on_time_delivery_rate', 'is_active']
    list_filter = ['reliability_rating', 'is_active', 'country']
    search_fields = ['name', 'country']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'current_stock', 'reorder_point', 'stock_status', 'stockout_risk_score']
    list_filter = ['category']
    search_fields = ['sku', 'name']

    @admin.display(description='Status')
    def stock_status(self, obj):
        return obj.stock_status


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'item', 'supplier', 'status', 'quantity', 'expected_delivery', 'delay_risk_score']
    list_filter = ['status']
    search_fields = ['order_number', 'item__sku']
    date_hierarchy = 'order_date'


@admin.register(RiskAlert)
class RiskAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'severity', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_resolved']
    actions = ['mark_resolved']

    @admin.action(description='Mark selected alerts as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
