from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import health, UploadViewSet

router = DefaultRouter()
router.register('uploads', UploadViewSet, basename='upload')

urlpatterns = [
    path('health/', health, name='health'),
    path('', include(router.urls)),
]