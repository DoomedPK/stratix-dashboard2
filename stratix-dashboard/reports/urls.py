from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Home
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Sites List (Make sure this has the trailing slash!)
    path('sites-list/', views.site_visit_list, name='site_visit_list'),
    
    # Uploads
    path('upload-photos/', views.upload_photos, name='upload_photos'),
]
