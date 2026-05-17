"""Core app URL configuration."""
from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('products/', views.products_view, name='products'),
    path('suppliers/', views.suppliers_view, name='suppliers'),
    path('alerts/', views.alerts_view, name='alerts'),
    path('upload/', views.upload_view, name='upload'),
    path('insights/', views.insights_view, name='insights'),
    path('retrain/', views.retrain_models_view, name='retrain_models'),
    path('signup/', views.signup_step1_view, name='signup_step1'),
    path('signup/step2/', views.signup_step2_view, name='signup_step2'),
    path('run-forecast/', views.run_forecast_view, name='run_forecast'),
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=False), name='login'),
]
