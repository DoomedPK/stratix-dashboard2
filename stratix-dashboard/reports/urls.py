from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Sites List
    path('sites-list/', views.site_visit_list, name='site_visit_list'),
    
    # Uploads
    path('upload-photos/', views.upload_photos, name='upload_photos'),
    
    # Check-in trigger
    path('start-visit/<int:report_id>/', views.start_visit, name='start_visit'),
    
    # NEW: Rework Log
    path('rework-log/', views.rework_log, name='rework_log'),
]
