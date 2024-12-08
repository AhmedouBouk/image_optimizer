from django.urls import path
from . import views

urlpatterns = [
    path('', views.ImageListView.as_view(), name='image-list'),
    path('upload/', views.ImageUploadView.as_view(), name='image-upload'),
    path('image/<int:pk>/', views.ImageDetailView.as_view(), name='image-detail-pk'),
    path('image/<slug:slug>/', views.ImageDetailView.as_view(), name='image-detail'),
    path('image/<int:pk>/download-responsive/', views.download_responsive_image, name='download-responsive'),
    path('api/stats/', views.get_optimization_stats, name='api-stats'),
    path('api/load-time/', views.measure_load_time, name='api-load-time'),
    path('documentation/', views.DocumentationView.as_view(), name='documentation'),
]
