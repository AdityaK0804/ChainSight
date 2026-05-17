"""ChainSight URL Configuration."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('allauth.urls')),
    path('api/', include('core.api_urls')),
]
