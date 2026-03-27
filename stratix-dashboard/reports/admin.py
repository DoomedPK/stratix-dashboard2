from django.contrib import admin
from django.contrib.auth.models import User
from import_export.admin import ImportExportModelAdmin
from .models import Client, Project, UserProfile, Site, Report, Photo, SitePhoto, ActivityAlert
from .models import Site, SitePhoto
from .resources import SiteResource

# Unregister default User to customize it for searching
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ('username', 'first_name', 'last_name', 'email')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    search_fields = ('name',)

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
    list_display = ('site', 'contractor', 'submitted_at')

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('report', 'caption')

@admin.register(SitePhoto)
class SitePhotoAdmin(admin.ModelAdmin):
    # This creates the columns QAs will see in the admin panel
    list_display = ('site', 'contractor', 'status', 'uploaded_at')
    # This adds the search bar you requested!
    search_fields = ('site__site_id', 'contractor__username')
    # This adds the filters on the right side!
    list_filter = ('status', 'site')
    # NEW: Locks these fields so QAs can view them but cannot change them!
    readonly_fields = ('contractor', 'site', 'image', 'uploaded_at')

# NEW: Our custom Activity Alert admin interface
@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    # This dictates exactly which columns show up in the admin table
    list_display = ('timestamp', 'user', 'alert_type', 'site', 'message')
    
    # Adds a filter box on the right side to sort by type or site
    list_filter = ('alert_type', 'site', 'user')
    
    # Adds a search bar to look up specific alerts
    search_fields = ('user__username', 'message', 'site__site_id')
    
    # Makes the table read-only so people don't accidentally edit history
    readonly_fields = ('timestamp',)
