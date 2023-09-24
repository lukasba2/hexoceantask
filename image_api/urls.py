from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileViewSet, ImageViewSet, CustomTierViewSet
from . import views
# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'userprofiles', UserProfileViewSet)
router.register(r'images', ImageViewSet)
router.register(r'customtiers', CustomTierViewSet)
urlpatterns = [
    # Include the default router URLs
    path('', include(router.urls)),

    # Custom endpoint for generating expiring links
    path('images/<int:pk>/get_expiring_link/',
         ImageViewSet.as_view({'get': 'get_expiring_link'})),
    path('images/original/<int:image_id>/',
         views.serve_original_image, name='serve_original_image'),
    path('images/thumbnails/<int:image_id>/<str:size>/',
         views.serve_thumbnail_image, name='serve_thumbnail_image'),

]
