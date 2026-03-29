from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin
from .models import Client, Project, UserProfile, Site, Report, Photo, SitePhoto, ActivityAlert
from .resources import SiteResource

# Unregister default User to customize it for searching
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    search_fields = ('username', 'first_name', 'last_name', 'email')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # Added email and location to the search bar for Clients
    search_fields = ('name', 'email', 'location')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'client', 'role')
    autocomplete_fields = ('user', 'client')
    list_filter = ('role', 'client')

@admin.register(Site)
class SiteAdmin(ImportExportModelAdmin):
    resource_class = SiteResource
    list_display = ('site_id', 'site_name', 'project', 'get_contractors', 'priority')
    search_fields = ('site_id', 'site_name', 'location')
    list_filter = ('project', 'priority')
    
    autocomplete_fields = ('project',)
    filter_horizontal = ('assigned_contractors',)

    def get_contractors(self, obj):
        return ", ".join([user.username for user in obj.assigned_contractors.all()])
    get_contractors.short_description = 'Assigned Team'

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_import_resource_kwargs(request, *args, **kwargs)
        kwargs.update({"user": request.user})
        return kwargs

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # FIXED: Replaced 'contractor' with 'status' so the Admin panel doesn't crash!
    list_display = ('site', 'status', 'submitted_at')
    list_filter = ('status',)

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('report', 'caption')

@admin.register(SitePhoto)
class SitePhotoAdmin(admin.ModelAdmin):
    list_display = ('site', 'contractor', 'status', 'uploaded_at')
    search_fields = ('site__site_id', 'contractor__username')
    list_filter = ('status', 'site')
    readonly_fields = ('contractor', 'site', 'image', 'uploaded_at')

@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'alert_type', 'site', 'message')
    list_filter = ('alert_type', 'site', 'user')
    search_fields = ('user__username', 'message', 'site__site_id')
    readonly_fields = ('timestamp', 'user', 'site', 'alert_type', 'message')
    
    def has_add_permission(self, request):
        return False
