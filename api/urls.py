"""
URL Configuration for API endpoints
"""

from django.urls import path
from .views import (
    FeatureRetrieveView,
    FeatureCreateUpdateView,
    FeatureDeleteView,
    BulkFeatureCreateView,
    HealthCheckView,
    CacheStrategyInfoView,
)

app_name = "api"

urlpatterns = [
    # Cache strategy information
    path("info/", CacheStrategyInfoView.as_view(), name="cache-info"),
    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # Bulk operations (must come before parameterized routes)
    path("features/bulk/", BulkFeatureCreateView.as_view(), name="feature-bulk-create"),
    # Feature CRUD operations
    path("features/", FeatureCreateUpdateView.as_view(), name="feature-create"),
    path(
        "features/<str:customer_id>/",
        FeatureRetrieveView.as_view(),
        name="feature-retrieve",
    ),
    path(
        "features/<str:customer_id>/delete/",
        FeatureDeleteView.as_view(),
        name="feature-delete",
    ),
]
