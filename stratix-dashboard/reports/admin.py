from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin
from .models import Client, Project, UserProfile, Site, Report, Photo, SitePhoto, ActivityAlert
from .resources import SiteResource
from django.utils.html import format_html

# ---------------------------------------------------------
# UI CUSTOMIZATION: Branding the Admin Panel
# ---------------------------------------------------------
admin.site.site_header = "Stratix Command Center"
admin.site.site_title = "Stratix Admin Portal"
admin.site.index_title = "Global Database Administration"


# ---------------------------------------------------------
# INLINES: Show related data on the same page
# ---------------------------------------------------------
class SitePhotoInline(admin.TabularInline):
    model = SitePhoto
    extra = 0 # Don't show empty extra rows
    readonly_fields = ['image_preview', 'uploaded_at']
    fields = ['image_preview', 'contractor', 'status', 'qa_feedback', 'uploaded_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);"/>', obj.image.url)
        return "-"
    image_preview.short_description = 'Preview'


# ---------------------------------------------------------
# MODEL ADMINS: Customizing the Data Grids
# ---------------------------------------------------------
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # Stripped back to just 'name' to guarantee it matches your database!
    list_display = ('name',) 
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'client')
    search_fields = ('name',)
    ordering = ('-start_date',)

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'site_name', 'project', 'priority')
    list_filter = ('priority', 'project__client', 'project')
    search_fields = ('site_id', 'site_name', 'location')
    inlines = [SitePhotoInline] # Shows photos inside the Site page!
    filter_horizontal = ('assigned_contractors',) # Makes the contractor selection box much nicer

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('site', 'status', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('site__site_id', 'site__site_name')
    readonly_fields = ('submitted_at',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'client')
    list_filter = ('role', 'client')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

@admin.register(SitePhoto)
class SitePhotoAdmin(admin.ModelAdmin):
    list_display = ('site', 'contractor', 'status', 'image_thumbnail', 'uploaded_at')
    list_filter = ('status', 'contractor')
    search_fields = ('site__site_id', 'qa_feedback')
    readonly_fields = ('uploaded_at',)

    # Generates a clickable thumbnail in the main list view
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 40px; border-radius: 4px;"/></a>', obj.image.url, obj.image.url)
        return "No Image"
    image_thumbnail.short_description = 'Photo'

# ---------------------------------------------------------
# AUDIT LOG PROTECTION: ActivityAlert
# ---------------------------------------------------------
@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    list_display = ('site', 'alert_type', 'user', 'timestamp', 'message')
    list_filter = ('alert_type', 'timestamp')
    search_fields = ('site__site_id', 'message', 'user__username')
    
    # Guidelines: Logs should be immutable.
    # We make all fields readonly and disable add/delete permissions.
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
