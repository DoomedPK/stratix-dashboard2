from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class Client(models.Model):
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    location = models.CharField(max_length=100, default='Unknown')

    def __str__(self):
        return self.name

class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Completed', 'Completed')], default='Active')
    
    # 🚀 FIX 2: Admin Toggle for Minimum Photo Requirements
    require_photo_minimums = models.BooleanField(default=False, help_text="Enforce minimum photo counts per category for contractors.")

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=50, choices=[
        ('Admin', 'Admin'), 
        ('Client', 'Client'), 
        ('Contractor', 'Contractor'),
        ('QA', 'QA'),
        ('Tech Writer', 'Technical Report Writer'), 
    ], default='Client')

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class Site(models.Model):
    site_id = models.CharField(max_length=100, unique=True)
    site_name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    assigned_contractors = models.ManyToManyField(User, blank=True, related_name='assigned_sites')
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')

    def __str__(self):
        return f"{self.site_id} - {self.site_name}"

class Report(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='reports')
    submitted_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    final_document = models.FileField(upload_to='final_reports/%Y/%m/', blank=True, null=True)

    STATUS_CHOICES = [
        ('not_visited', 'Not Visited'),
        ('visit_in_progress', 'Visit In Progress'),
        ('qa_validation', 'QA Validation'),
        ('site_data_submitted', 'Site Data Submitted'),
        ('engineer_review', 'Engineer Review'),
        ('submitted', 'Submitted'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='not_visited')

    def __str__(self):
        return f"Report for {self.site.site_id}"

class Photo(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='site_photos/')
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Photo for {self.report.site.site_id}"

class SitePhoto(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Validation'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rework Required'),
    ]
    
    CATEGORY_CHOICES = [
        ('Site Overview', 'Site Overview (Min: 4)'),
        ('Access Road', 'Access Road (Min: 2)'),
        ('Tower Structure', 'Tower Structure (Min: 5)'),
        ('Tower Base & Foundation', 'Tower Base & Foundation (Min: 14)'),
        ('Antennas & Mounting Systems', 'Antennas & Mounting Systems (Min: 9)'),
        ('Cabling & Connections', 'Cabling & Connections (Min: 3)'),
        ('Equipment Shelter / Cabinets', 'Equipment Shelter / Cabinets (Min: 2)'),
        ('Power Systems', 'Power Systems (Min: 2)'),
        ('Grounding & Earthing', 'Grounding & Earthing (Min: 2)'),
        ('Perimeter, Security & Surroundings', 'Perimeter, Security & Surroundings (Min: 5)'),
        ('Additional Observations', 'Additional Observations (Optional)'),
    ]

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='photos')
    contractor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Contractors'})
    image = models.ImageField(upload_to='site_photos/%Y/%m/%d/')
    
    # 🚀 FIX 2 & 3: New Categories & Contractor Notes Separated from QA Feedback
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='Site Overview')
    contractor_notes = models.TextField(blank=True, null=True, help_text="Notes from the contractor.")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    qa_feedback = models.TextField(blank=True, null=True, help_text="Reason for rework if rejected.")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.site.site_id} by {self.contractor.username} - {self.status}"

class ActivityAlert(models.Model):
    message = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triggered_alerts')
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='site_alerts')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    alert_type = models.CharField(max_length=50, choices=[
        ('CHECK_IN', 'Contractor Checked In'),
        ('UPLOAD', 'Photos/Reports Uploaded'),
        ('REWORK', 'Rework Requested'),
    ], default='CHECK_IN')

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user.username}: {self.message}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=UserProfile)
def sync_role_and_group(sender, instance, **kwargs):
    role_to_group = {
        'Admin': 'Admins',
        'Client': 'Clients',
        'Contractor': 'Contractors',
        'QA': 'QAs',
        'Tech Writer': 'Technical Report Writers' 
    }
    
    group_name = role_to_group.get(instance.role)
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.user.groups.clear()
        instance.user.groups.add(group)

@receiver(post_save, sender=ActivityAlert)
def trigger_client_fetch(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'global_ping',
            {'type': 'ping_client'}
        )

class SiteIssue(models.Model):
    SEVERITY_CHOICES = [
        ('Minor', 'Minor'),
        ('Major', 'Major'),
        ('Critical', 'Critical'),
    ]
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='issues')
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Minor')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.site.site_id} - {self.severity} Issue"
