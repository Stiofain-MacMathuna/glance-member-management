from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import InstituteViewSet, MemberViewSet, ShiftViewSet, AnalysisViewSet, DashboardStatsView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = DefaultRouter()
router.register(r'institutes', InstituteViewSet)
router.register(r'members', MemberViewSet)
router.register(r'shifts', ShiftViewSet)
router.register(r'analyses', AnalysisViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Documentation URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
]