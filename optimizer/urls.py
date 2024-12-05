from django.urls import path
from . import views

urlpatterns = [
    path('', views.ImageListView.as_view(), name='image-list'),
    path('upload/', views.ImageUploadView.as_view(), name='image-upload'),
    path('image/<slug:slug>/', views.ImageDetailView.as_view(), name='image-detail'),
    path('api/stats/', views.get_optimization_stats, name='optimization-stats'),
    path('api/measure-load-time/', views.measure_load_time, name='measure-load-time'),
]
