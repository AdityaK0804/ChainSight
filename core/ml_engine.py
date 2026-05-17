"""
ChainSight ML Risk Scoring Engine
──────────────────────────────────
Two scikit-learn models:
  1. Order Delay Risk    → RandomForestClassifier
  2. Stockout Risk       → GradientBoostingRegressor

Models are trained on synthetic data and persisted as .pkl files.
Auto-trains on first invocation if pkl files are missing.
"""

import logging
import os
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split

from django.utils import timezone

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / 'ml_models'
DELAY_MODEL_PATH = MODEL_DIR / 'delay_risk_model.pkl'
STOCKOUT_MODEL_PATH = MODEL_DIR / 'stockout_risk_model.pkl'

# Country risk scores (higher = riskier logistics environment)
COUNTRY_RISK_MAP = {
    'China': 0.3, 'India': 0.35, 'Vietnam': 0.4, 'Germany': 0.1,
    'USA': 0.15, 'Japan': 0.12, 'Brazil': 0.45, 'Mexico': 0.38,
    'South Korea': 0.15, 'Taiwan': 0.2, 'Thailand': 0.35,
}


def _get_country_risk(country: str) -> float:
    """Return a risk score for a supplier's country."""
    return COUNTRY_RISK_MAP.get(country, 0.3)


# ── Synthetic Data Generation ────────────────────────────────────────────

def _generate_delay_training_data(n_samples: int = 2000) -> tuple:
    """Generate synthetic training data for the delay risk model."""
    rng = np.random.RandomState(42)

    lead_times = rng.randint(3, 30, n_samples).astype(float)
    on_time_rates = rng.uniform(0.5, 0.99, n_samples)
    avg_delays = rng.uniform(0, 10, n_samples)
    quantities = rng.randint(10, 5000, n_samples).astype(float)
    days_until = rng.randint(-5, 30, n_samples).astype(float)
    past_delays = rng.randint(0, 15, n_samples).astype(float)
    country_risks = rng.uniform(0.05, 0.5, n_samples)

    X = np.column_stack([
        lead_times, on_time_rates, avg_delays, quantities,
        days_until, past_delays, country_risks,
    ])

    # Probabilistic delay logic
    delay_prob = (
        0.15
        + 0.25 * (1 - on_time_rates)
        + 0.10 * np.clip(avg_delays / 10, 0, 1)
        + 0.10 * np.clip(lead_times / 30, 0, 1)
        + 0.10 * country_risks
        + 0.15 * np.clip(-days_until / 10, 0, 1)
        + 0.05 * np.clip(past_delays / 15, 0, 1)
    )
    delay_prob = np.clip(delay_prob + rng.normal(0, 0.08, n_samples), 0, 1)
    y = (rng.random(n_samples) < delay_prob).astype(int)

    return X, y


def _generate_stockout_training_data(n_samples: int = 2000) -> tuple:
    """Generate synthetic training data for the stockout risk model."""
    rng = np.random.RandomState(123)

    current_stock = rng.randint(0, 500, n_samples).astype(float)
    reorder_point = rng.randint(20, 150, n_samples).astype(float)
    lead_time = rng.randint(3, 25, n_samples).astype(float)
    daily_consumption = rng.uniform(1, 30, n_samples)
    supplier_reliability = rng.uniform(0.5, 1.0, n_samples)
    pending_orders = rng.randint(0, 10, n_samples).astype(float)

    X = np.column_stack([
        current_stock, reorder_point, lead_time,
        daily_consumption, supplier_reliability, pending_orders,
    ])

    # Risk score: days of stock left vs lead time
    days_of_stock = np.where(daily_consumption > 0, current_stock / daily_consumption, 999)
    stock_ratio = np.clip(reorder_point / np.maximum(current_stock, 1), 0, 3)

    risk_score = (
        0.30 * np.clip(1 - days_of_stock / (lead_time + 1), 0, 1)
        + 0.25 * np.clip(stock_ratio / 3, 0, 1)
        + 0.15 * (1 - supplier_reliability)
        + 0.10 * np.clip(lead_time / 25, 0, 1)
        + 0.10 * np.clip(1 - pending_orders / 5, 0, 1)
        + 0.10 * np.clip(daily_consumption / 30, 0, 1)
    )
    y = np.clip(risk_score + rng.normal(0, 0.06, n_samples), 0, 1)

    return X, y


# ── Model Training ───────────────────────────────────────────────────────

def _train_delay_model():
    """Train and save the delay risk RandomForestClassifier."""
    logger.info("Training delay risk model...")
    X, y = _generate_delay_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    logger.info(f"Delay model trained. Test accuracy: {accuracy:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(DELAY_MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

    return model


def _train_stockout_model():
    """Train and save the stockout risk GradientBoostingRegressor."""
    logger.info("Training stockout risk model...")
    X, y = _generate_stockout_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(
        n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
    )
    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)
    logger.info(f"Stockout model trained. Test R²: {score:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(STOCKOUT_MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

    return model


# ── Model Loading (with auto-train) ─────────────────────────────────────

_delay_model_cache = None
_stockout_model_cache = None


def _load_delay_model():
    """Load delay model from pkl, training first if missing."""
    global _delay_model_cache
    if _delay_model_cache is not None:
        return _delay_model_cache

    if DELAY_MODEL_PATH.exists():
        with open(DELAY_MODEL_PATH, 'rb') as f:
            _delay_model_cache = pickle.load(f)
    else:
        _delay_model_cache = _train_delay_model()

    return _delay_model_cache


def _load_stockout_model():
    """Load stockout model from pkl, training first if missing."""
    global _stockout_model_cache
    if _stockout_model_cache is not None:
        return _stockout_model_cache

    if STOCKOUT_MODEL_PATH.exists():
        with open(STOCKOUT_MODEL_PATH, 'rb') as f:
            _stockout_model_cache = pickle.load(f)
    else:
        _stockout_model_cache = _train_stockout_model()

    return _stockout_model_cache


# ── Prediction Functions ─────────────────────────────────────────────────

def predict_order_delay_risk(
    lead_time_days: float,
    supplier_on_time_rate: float,
    supplier_avg_delay: float,
    order_quantity: float,
    days_until_delivery: float,
    past_delays_count: float,
    country_risk: float,
) -> tuple:
    """
    Predict order delay risk.

    Returns:
        tuple: (probability 0–1, label 'low'|'medium'|'high')
    """
    model = _load_delay_model()
    features = np.array([[
        lead_time_days, supplier_on_time_rate, supplier_avg_delay,
        order_quantity, days_until_delivery, past_delays_count, country_risk,
    ]])
    prob = float(model.predict_proba(features)[0][1])

    if prob < 0.35:
        label = 'low'
    elif prob < 0.65:
        label = 'medium'
    else:
        label = 'high'

    return prob, label


def predict_stockout_risk(
    current_stock: float,
    reorder_point: float,
    lead_time_days: float,
    avg_daily_consumption: float,
    supplier_reliability: float,
    pending_orders: float,
) -> float:
    """
    Predict stockout risk score.

    Returns:
        float: Risk score clipped to 0.0–1.0
    """
    model = _load_stockout_model()
    features = np.array([[
        current_stock, reorder_point, lead_time_days,
        avg_daily_consumption, supplier_reliability, pending_orders,
    ]])
    score = float(model.predict(features)[0])
    return max(0.0, min(1.0, score))


# ── Master Orchestrator ──────────────────────────────────────────────────

def run_risk_analysis_for_all() -> dict:
    """
    Score all active orders and inventory items. Generate RiskAlerts.

    Returns:
        dict: {'orders_scored': N, 'items_scored': N, 'alerts_created': N}
    """
    from .models import Order, InventoryItem, RiskAlert, Supplier

    # Delete existing unresolved alerts (fresh analysis)
    RiskAlert.objects.filter(is_resolved=False).delete()

    alerts_created = 0
    orders_scored = 0
    items_scored = 0

    # ── Score Orders ─────────────────────────────────────────────────────
    active_orders = (
        Order.objects
        .filter(status__in=['pending', 'confirmed', 'in_transit'])
        .select_related('supplier', 'item')
    )

    for order in active_orders:
        supplier = order.supplier
        days_until = (order.expected_delivery - timezone.now().date()).days
        past_delays = (
            Order.objects
            .filter(supplier=supplier, status='delayed')
            .count()
        )
        country_risk = _get_country_risk(supplier.country)

        prob, label = predict_order_delay_risk(
            lead_time_days=supplier.lead_time_days,
            supplier_on_time_rate=supplier.on_time_delivery_rate,
            supplier_avg_delay=supplier.average_delay_days,
            order_quantity=order.quantity,
            days_until_delivery=days_until,
            past_delays_count=past_delays,
            country_risk=country_risk,
        )

        order.delay_risk_score = round(prob, 3)
        order.save(update_fields=['delay_risk_score'])
        orders_scored += 1

        if label in ('medium', 'high'):
            severity = 'critical' if label == 'high' else 'warning'
            RiskAlert.objects.create(
                alert_type='delay',
                severity=severity,
                title=f"{order.item.sku} — Delivery delay risk",
                message=(
                    f"Order {order.order_number} from {supplier.name} has a "
                    f"{prob:.0%} delay probability. Expected delivery: "
                    f"{order.expected_delivery.strftime('%b %d, %Y')}."
                ),
                related_order=order,
                related_item=order.item,
                related_supplier=supplier,
            )
            alerts_created += 1

    # ── Score Inventory Items ────────────────────────────────────────────
    items = InventoryItem.objects.select_related('supplier').all()

    for item in items:
        supplier = item.supplier
        supplier_reliability = supplier.on_time_delivery_rate if supplier else 0.8
        lead_time = supplier.lead_time_days if supplier else 7
        pending_count = (
            Order.objects
            .filter(item=item, status__in=['pending', 'confirmed', 'in_transit'])
            .count()
        )
        # Estimate daily consumption from recent orders
        avg_daily = max(1.0, item.reorder_quantity / max(lead_time, 1) * 0.5)

        score = predict_stockout_risk(
            current_stock=item.current_stock,
            reorder_point=item.reorder_point,
            lead_time_days=lead_time,
            avg_daily_consumption=avg_daily,
            supplier_reliability=supplier_reliability,
            pending_orders=pending_count,
        )

        item.stockout_risk_score = round(score, 3)
        item.last_risk_updated = timezone.now()
        item.save(update_fields=['stockout_risk_score', 'last_risk_updated'])
        items_scored += 1

        if score >= 0.75:
            RiskAlert.objects.create(
                alert_type='stockout',
                severity='critical',
                title=f"{item.sku} — Critical stockout risk",
                message=(
                    f"{item.name} has a risk score of {score:.0%}. "
                    f"Current stock: {item.current_stock} units "
                    f"(reorder point: {item.reorder_point})."
                ),
                related_item=item,
                related_supplier=supplier,
            )
            alerts_created += 1
        elif score >= 0.5:
            RiskAlert.objects.create(
                alert_type='stockout',
                severity='warning',
                title=f"{item.sku} — Elevated stockout risk",
                message=(
                    f"{item.name} has a risk score of {score:.0%}. "
                    f"Current stock: {item.current_stock} units. "
                    f"Consider placing a reorder."
                ),
                related_item=item,
                related_supplier=supplier,
            )
            alerts_created += 1

    return {
        'orders_scored': orders_scored,
        'items_scored': items_scored,
        'alerts_created': alerts_created,
    }


def get_model_stats() -> dict:
    """
    Return accuracy metrics and feature importances for both models.
    Used by the insights view.
    """
    delay_model = _load_delay_model()
    stockout_model = _load_stockout_model()

    # Re-generate test data to compute accuracy scores
    X_delay, y_delay = _generate_delay_training_data(n_samples=400)
    _, X_d_test, _, y_d_test = train_test_split(X_delay, y_delay, test_size=0.2, random_state=42)
    delay_accuracy = round(float(delay_model.score(X_d_test, y_d_test)) * 100, 1)

    X_stock, y_stock = _generate_stockout_training_data(n_samples=400)
    _, X_s_test, _, y_s_test = train_test_split(X_stock, y_stock, test_size=0.2, random_state=42)
    stockout_r2 = round(float(stockout_model.score(X_s_test, y_s_test)) * 100, 1)

    delay_features = [
        'Lead time (days)', 'On-time delivery rate', 'Avg delay (days)',
        'Order quantity', 'Days until delivery', 'Past delays count', 'Country risk score',
    ]
    stockout_features = [
        'Current stock', 'Reorder point', 'Lead time (days)',
        'Avg daily consumption', 'Supplier reliability', 'Pending orders',
    ]

    delay_importances = [round(float(v) * 100, 1) for v in delay_model.feature_importances_]
    stockout_importances = [round(float(v) * 100, 1) for v in stockout_model.feature_importances_]

    delay_pairs = sorted(zip(delay_features, delay_importances), key=lambda x: -x[1])
    stockout_pairs = sorted(zip(stockout_features, stockout_importances), key=lambda x: -x[1])

    return {
        'delay_accuracy': delay_accuracy,
        'stockout_r2': stockout_r2,
        'delay_pairs': delay_pairs,
        'stockout_pairs': stockout_pairs,
        'delay_model_type': 'RandomForestClassifier',
        'stockout_model_type': 'GradientBoostingRegressor',
        'n_estimators_delay': delay_model.n_estimators,
        'n_estimators_stockout': stockout_model.n_estimators,
        'training_samples': 2000,
    }


def retrain_models() -> dict:
    """Delete pkl files and retrain both models. Returns new stats."""
    global _delay_model_cache, _stockout_model_cache
    _delay_model_cache = None
    _stockout_model_cache = None
    if DELAY_MODEL_PATH.exists():
        DELAY_MODEL_PATH.unlink()
    if STOCKOUT_MODEL_PATH.exists():
        STOCKOUT_MODEL_PATH.unlink()
    _train_delay_model()
    _train_stockout_model()
    return get_model_stats()
