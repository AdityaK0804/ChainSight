"""Core API URL configuration (DRF)."""
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics, status
from django.db.models import Count, Sum, F, Q

from .models import Supplier, InventoryItem, Order, RiskAlert
from .serializers import (
    SupplierSerializer, InventoryItemSerializer,
    OrderSerializer, RiskAlertSerializer,
)


class SupplierListView(generics.ListAPIView):
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer


class SupplierDetailView(generics.RetrieveAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class InventoryListView(generics.ListAPIView):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        qs = InventoryItem.objects.select_related('supplier').all()
        if self.request.query_params.get('low_stock') == 'true':
            qs = qs.filter(current_stock__lte=F('reorder_point'))
        return qs


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related('supplier', 'item').all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AlertListView(generics.ListAPIView):
    serializer_class = RiskAlertSerializer

    def get_queryset(self):
        return (
            RiskAlert.objects
            .select_related('related_order', 'related_item', 'related_supplier')
            .all()
        )


@api_view(['POST'])
def resolve_alert_api(request, pk):
    """Mark an alert as resolved."""
    try:
        alert = RiskAlert.objects.get(pk=pk)
    except RiskAlert.DoesNotExist:
        return Response({'error': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)

    alert.is_resolved = True
    alert.save(update_fields=['is_resolved'])
    return Response({'success': True, 'id': alert.id})


@api_view(['GET'])
def dashboard_stats_api(request):
    """Aggregate stats for dashboard charts."""
    total_items = InventoryItem.objects.count()
    low_stock = InventoryItem.objects.filter(current_stock__lte=F('reorder_point')).count()
    total_orders = Order.objects.count()
    delayed_orders = Order.objects.filter(status='delayed').count()
    unresolved_alerts = RiskAlert.objects.filter(is_resolved=False).count()
    total_inventory_value = (
        InventoryItem.objects
        .aggregate(total=Sum(F('current_stock') * F('unit_cost')))['total']
    ) or 0

    alerts_by_severity = dict(
        RiskAlert.objects
        .filter(is_resolved=False)
        .values_list('severity')
        .annotate(count=Count('id'))
        .values_list('severity', 'count')
    )

    return Response({
        'total_items': total_items,
        'low_stock_items': low_stock,
        'total_orders': total_orders,
        'delayed_orders': delayed_orders,
        'unresolved_alerts': unresolved_alerts,
        'total_inventory_value': float(total_inventory_value),
        'alerts_by_severity': alerts_by_severity,
    })


urlpatterns = [
    path('suppliers/', SupplierListView.as_view(), name='api_suppliers'),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view(), name='api_supplier_detail'),
    path('inventory/', InventoryListView.as_view(), name='api_inventory'),
    path('orders/', OrderListView.as_view(), name='api_orders'),
    path('alerts/', AlertListView.as_view(), name='api_alerts'),
    path('alerts/<int:pk>/resolve/', resolve_alert_api, name='api_resolve_alert'),
    path('dashboard/stats/', dashboard_stats_api, name='api_dashboard_stats'),
]
