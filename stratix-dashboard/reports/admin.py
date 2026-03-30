from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import Client, Project, UserProfile, Site, Report, SitePhoto, ActivityAlert, SiteIssue
from django.utils.html import format_html

admin.site.unregister(Group)
@admin.register(Group)
class CustomGroupAdmin(BaseGroupAdmin, ModelAdmin):
    search_fields = ('name',)

admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    autocomplete_fields = ['groups', 'user_permissions']

class SitePhotoInline(TabularInline):
    model = SitePhoto
    extra = 0 
    readonly_fields = ['image_preview', 'uploaded_at']
    fields = ['image_preview', 'category', 'contractor', 'status', 'contractor_notes', 'qa_feedback', 'uploaded_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);"/>', obj.image.url)
        return "-"
    image_preview.short_description = 'Preview'

@admin.register(Client)
class ClientAdmin(ModelAdmin):
    list_display = ('name',) 
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ('name', 'client', 'require_photo_minimums', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'client', 'require_photo_minimums')
    search_fields = ('name',)
    ordering = ('-start_date',)

@admin.register(Site)
class SiteAdmin(ModelAdmin):
    list_display = ('site_id', 'site_name', 'project', 'priority')
    list_filter = ('priority', 'project__client', 'project')
    search_fields = ('site_id', 'site_name', 'location')
    inlines = [SitePhotoInline] 
    autocomplete_fields = ['assigned_contractors']

@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ('site', 'status', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('site__site_id', 'site__site_name')
    readonly_fields = ('submitted_at',)

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'role', 'client')
    list_filter = ('role', 'client')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ['user']

@admin.register(SitePhoto)
class SitePhotoAdmin(ModelAdmin):
    list_display = ('site', 'category', 'contractor', 'status', 'image_thumbnail', 'uploaded_at')
    list_filter = ('status', 'category', 'contractor')
    search_fields = ('site__site_id', 'contractor_notes', 'qa_feedback')
    readonly_fields = ('uploaded_at',)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<a href="{}" target="_blank"><img src="{}" style="max-height: 40px; border-radius: 4px;"/></a>', obj.image.url, obj.image.url)
        return "No Image"
    image_thumbnail.short_description = 'Photo'

@admin.register(SiteIssue)
class SiteIssueAdmin(ModelAdmin):
    list_display = ('site', 'severity', 'is_resolved', 'reported_by', 'created_at')
    list_filter = ('severity', 'is_resolved')
    search_fields = ('site__site_id', 'description')
    autocomplete_fields = ['site', 'reported_by']

@admin.register(ActivityAlert)
class ActivityAlertAdmin(ModelAdmin):
    list_display = ('site', 'alert_type', 'user', 'timestamp', 'message')
    list_filter = ('alert_type', 'timestamp')
    search_fields = ('site__site_id', 'message', 'user__username')
    
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
