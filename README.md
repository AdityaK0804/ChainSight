# ChainSight - AI-Powered Supply Chain Risk Dashboard

A full-stack Django web application that predicts supply chain disruptions using machine learning, tracks inventory risk in real time, and surfaces actionable alerts through a clean dashboard UI.

**Live Demo:** https://chainsight-crre.onrender.com/
## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework |
| ML Models | scikit-learn (RandomForest, GradientBoosting) |
| Auth | django-allauth (Google + Microsoft OAuth) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Django Templates + Tailwind CSS (CDN) + Chart.js |
| Data | pandas, numpy |

## Features

- **AI Risk Scoring** - Two ML models predict order delay probability and inventory stockout risk on demand
- **Real-time Dashboard** - KPIs, 14-day demand forecast chart, and critical alert feed
- **Inventory Management** - Searchable, filterable product table with color-coded risk indicators
- **Smart Alerts** - Auto-generated risk alerts (critical/warning/info) with one-click resolution
- **CSV Import** - Bulk upload inventory data with drag-and-drop, with import summary
- **ML Insights** - Feature importance charts and model accuracy metrics
- **REST API** - 7 DRF endpoints for all data models with pagination and filtering
- **Social Login** - Google and Microsoft OAuth via django-allauth

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Seed demo data (creates 5 suppliers, 15 products, 20 orders, runs ML analysis)
python manage.py seed_data

# 4. Create admin user
python manage.py createsuperuser

# 5. Start server
python manage.py runserver
```

Visit http://127.0.0.1:8000 - sign up or log in to see the dashboard.

## Project Structure

```
chainsight/
├── chainsight/          # Django project config (settings, urls)
├── core/                # Main app
│   ├── models.py        # Supplier, InventoryItem, Order, RiskAlert
│   ├── views.py         # Dashboard, products, alerts, upload, insights
│   ├── ml_engine.py     # RandomForest + GradientBoosting ML models
│   ├── serializers.py   # DRF serializers
│   ├── api_urls.py      # REST API routes
│   └── management/      # seed_data, run_risk_analysis commands
├── templates/           # Django HTML templates
└── static/              # CSS, JS
```

## API Endpoints

| Method | URL | Description |
|---|---|---|
| GET | /api/suppliers/ | List all suppliers |
| GET | /api/inventory/ | List inventory (filter: ?low_stock=true) |
| GET | /api/orders/ | List orders (filter: ?status=delayed) |
| GET | /api/alerts/ | List risk alerts |
| POST | /api/alerts/<id>/resolve/ | Mark alert resolved |
| GET | /api/dashboard/stats/ | Aggregate KPI stats |

## ML Models

**Order Delay Risk** (RandomForestClassifier)
- Features: supplier reliability, lead time, delivery window, historical delays, country risk
- Output: probability 0–1 + label (low/medium/high)

**Stockout Risk** (GradientBoostingRegressor)
- Features: current stock, reorder point, lead time, daily consumption, supplier reliability
- Output: risk score 0–1

Models auto-train on first run using synthetic data and are cached as .pkl files.

## Built By

Aditya Kumar - adityavinoddas@gmail.com
