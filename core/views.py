"""
ChainSight Core Views
All dashboard views require @login_required.
"""

import json
import random

import pandas as pd
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import SignupStep1Form, SignupStep2Form, CSVUploadForm
from .models import Supplier, InventoryItem, Order, RiskAlert
from .ml_engine import run_risk_analysis_for_all


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC VIEWS
# ═══════════════════════════════════════════════════════════════════════════

def landing_view(request):
    """Marketing landing page."""
    return render(request, 'landing.html')


def signup_step1_view(request):
    """Signup step 1: credentials."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignupStep1Form(request.POST)
        if form.is_valid():
            request.session['signup_data'] = {
                'full_name': form.cleaned_data['full_name'],
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password'],
            }
            return redirect('signup_step2')
    else:
        form = SignupStep1Form()

    return render(request, 'auth/signup_step1.html', {'form': form})


def signup_step2_view(request):
    """Signup step 2: company info → create account."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    signup_data = request.session.get('signup_data')
    if not signup_data:
        return redirect('signup_step1')

    if request.method == 'POST':
        form = SignupStep2Form(request.POST)
        if form.is_valid():
            names = signup_data['full_name'].split(' ', 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ''

            user = User.objects.create_user(
                username=signup_data['email'],
                email=signup_data['email'],
                password=signup_data['password'],
                first_name=first_name,
                last_name=last_name,
            )
            del request.session['signup_data']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('dashboard')
    else:
        form = SignupStep2Form()

    return render(request, 'auth/signup_step2.html', {'form': form})


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD VIEWS (login_required)
# ═══════════════════════════════════════════════════════════════════════════

@login_required
def dashboard_view(request):
    """Main operations overview."""
    total_products = InventoryItem.objects.count()
    active_alerts = RiskAlert.objects.filter(is_resolved=False).count()
    critical_alerts = (
        RiskAlert.objects
        .filter(is_resolved=False, severity='critical')
        .select_related('related_order', 'related_item', 'related_supplier')
    )
    low_stock_items = InventoryItem.objects.filter(
        current_stock__lte=F('reorder_point')
    ).select_related('supplier')
    recent_orders = (
        Order.objects
        .select_related('supplier', 'item')
        .order_by('-created_at')[:5]
    )

    # Generate synthetic chart data for the 14-day forecast
    rng = random.Random(42)
    historical = [rng.randint(80, 220) + int(i * 2.5) for i in range(14)]
    predicted = [historical[-1] + rng.randint(-15, 25) + int(i * 1.8) for i in range(14)]
    confidence_upper = [v + rng.randint(20, 45) for v in predicted]
    confidence_lower = [max(0, v - rng.randint(20, 45)) for v in predicted]

    context = {
        'total_products': total_products,
        'active_alerts': active_alerts,
        'forecast_accuracy': 91.2,
        'critical_alerts': critical_alerts,
        'low_stock_items': low_stock_items,
        'recent_orders': recent_orders,
        'chart_historical': json.dumps(historical),
        'chart_predicted': json.dumps(predicted),
        'chart_upper': json.dumps(confidence_upper),
        'chart_lower': json.dumps(confidence_lower),
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def products_view(request):
    """Paginated product inventory list with search and filtering."""
    queryset = InventoryItem.objects.select_related('supplier').all()

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))

    # Category filter
    category = request.GET.get('category', '').strip()
    if category:
        queryset = queryset.filter(category=category)

    # Stock status filter
    status = request.GET.get('status', '').strip()
    if status == 'low':
        queryset = queryset.filter(current_stock__lte=F('reorder_point'), current_stock__gt=0)
    elif status == 'out_of_stock':
        queryset = queryset.filter(current_stock=0)
    elif status == 'ok':
        queryset = queryset.filter(current_stock__gt=F('reorder_point'))

    paginator = Paginator(queryset, 15)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'search_query': q,
        'current_category': category,
        'current_status': status,
        'categories': InventoryItem.CATEGORY_CHOICES,
    }
    return render(request, 'dashboard/products.html', context)


@login_required
def alerts_view(request):
    """Alert list with filtering and inline resolve."""
    queryset = (
        RiskAlert.objects
        .select_related('related_order', 'related_item', 'related_supplier')
        .all()
    )

    severity = request.GET.get('severity', '').strip()
    if severity:
        queryset = queryset.filter(severity=severity)

    alert_type = request.GET.get('type', '').strip()
    if alert_type:
        queryset = queryset.filter(alert_type=alert_type)

    resolved = request.GET.get('resolved', '').strip()
    if resolved == 'true':
        queryset = queryset.filter(is_resolved=True)
    elif resolved == 'false':
        queryset = queryset.filter(is_resolved=False)

    paginator = Paginator(queryset, 20)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'current_severity': severity,
        'current_type': alert_type,
        'current_resolved': resolved,
        'unresolved_count': RiskAlert.objects.filter(is_resolved=False).count(),
    }
    return render(request, 'dashboard/alerts.html', context)


@login_required
def upload_view(request):
    """CSV upload for inventory data."""
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            try:
                df = pd.read_csv(file)
                required_cols = {'sku', 'name', 'category', 'current_stock', 'unit_cost'}
                if not required_cols.issubset(set(df.columns)):
                    missing = required_cols - set(df.columns)
                    return JsonResponse({
                        'success': False,
                        'error': f"Missing columns: {', '.join(missing)}"
                    }, status=400)

                created = 0
                updated = 0
                errors = []

                for idx, row in df.iterrows():
                    try:
                        item, was_created = InventoryItem.objects.update_or_create(
                            sku=row['sku'],
                            defaults={
                                'name': row['name'],
                                'category': row.get('category', 'component'),
                                'current_stock': int(row['current_stock']),
                                'unit_cost': float(row['unit_cost']),
                                'reorder_point': int(row.get('reorder_point', 50)),
                                'reorder_quantity': int(row.get('reorder_quantity', 200)),
                            }
                        )
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                    except Exception as e:
                        errors.append(f"Row {idx + 2}: {str(e)}")

                return JsonResponse({
                    'success': True,
                    'created': created,
                    'updated': updated,
                    'errors': errors,
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            return JsonResponse({
                'success': False,
                'error': '; '.join(
                    msg for field_errors in form.errors.values() for msg in field_errors
                )
            }, status=400)

    return render(request, 'dashboard/upload.html')


@login_required
@require_POST
def run_forecast_view(request):
    """Trigger ML risk analysis for all orders and inventory."""
    result = run_risk_analysis_for_all()
    return JsonResponse({
        'success': True,
        'orders_scored': result['orders_scored'],
        'items_scored': result['items_scored'],
        'alerts_created': result['alerts_created'],
    })


@login_required
def suppliers_view(request):
    """Supplier list with risk overview."""
    suppliers = Supplier.objects.annotate(
        order_count=Count('orders'),
        delayed_count=Count('orders', filter=Q(orders__status='delayed')),
    ).order_by('name')
    context = {
        'suppliers': suppliers,
        'total': suppliers.count(),
        'high_risk': sum(1 for s in suppliers if s.risk_level == 'high'),
    }
    return render(request, 'dashboard/suppliers.html', context)


@login_required
def insights_view(request):
    """ML model explainability and accuracy metrics."""
    from .ml_engine import get_model_stats
    stats = get_model_stats()
    stats['delay_pairs'] = json.dumps(stats['delay_pairs'])
    stats['stockout_pairs'] = json.dumps(stats['stockout_pairs'])
    return render(request, 'dashboard/insights.html', {'stats': stats})


@login_required
@require_POST
def retrain_models_view(request):
    """Retrain both ML models from scratch."""
    from .ml_engine import retrain_models
    stats = retrain_models()
    return JsonResponse({'success': True, 'delay_accuracy': stats['delay_accuracy'], 'stockout_r2': stats['stockout_r2']})
