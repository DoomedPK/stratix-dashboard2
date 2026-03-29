from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from reports.views import custom_logout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reports.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', custom_logout, name='logout'),
    
    # This securely serves images on Render's disk even when DEBUG=False
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
