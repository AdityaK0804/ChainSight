from django.test import TestCase
from core.ml_engine import predict_order_delay_risk, predict_stockout_risk


class DelayRiskModelTest(TestCase):
    def test_returns_tuple(self):
        result = predict_order_delay_risk(
            lead_time_days=14, supplier_on_time_rate=0.85,
            supplier_avg_delay=1.5, order_quantity=200,
            days_until_delivery=7, past_delays_count=2, country_risk=0.3)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_probability_in_range(self):
        prob, label = predict_order_delay_risk(
            lead_time_days=14, supplier_on_time_rate=0.85,
            supplier_avg_delay=1.5, order_quantity=200,
            days_until_delivery=7, past_delays_count=2, country_risk=0.3)
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_label_values(self):
        _, label = predict_order_delay_risk(
            lead_time_days=7, supplier_on_time_rate=0.95,
            supplier_avg_delay=0.2, order_quantity=50,
            days_until_delivery=10, past_delays_count=0, country_risk=0.1)
        self.assertIn(label, ['low', 'medium', 'high'])

    def test_high_risk_supplier_increases_probability(self):
        low_prob, _ = predict_order_delay_risk(14, 0.97, 0.1, 100, 20, 0, 0.05)
        high_prob, _ = predict_order_delay_risk(14, 0.55, 8.0, 100, 1, 8, 0.48)
        self.assertGreater(high_prob, low_prob)


class StockoutRiskModelTest(TestCase):
    def test_returns_float(self):
        result = predict_stockout_risk(
            current_stock=50, reorder_point=100, lead_time_days=14,
            avg_daily_consumption=5.0, supplier_reliability=0.85, pending_orders=1)
        self.assertIsInstance(result, float)

    def test_score_in_range(self):
        score = predict_stockout_risk(50, 100, 14, 5.0, 0.85, 1)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_zero_stock_high_risk(self):
        score = predict_stockout_risk(0, 100, 21, 10.0, 0.6, 0)
        self.assertGreater(score, 0.5)

    def test_ample_stock_low_risk(self):
        score = predict_stockout_risk(5000, 50, 3, 2.0, 0.98, 3)
        self.assertLess(score, 0.5)
