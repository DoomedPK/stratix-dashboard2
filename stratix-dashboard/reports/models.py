from django.db import models
from django.contrib.auth.models import User

class Client(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Completed', 'Completed')], default='Active')

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=[
        ('Admin', 'Admin'), 
        ('Client', 'Client'), 
        ('Contractor', 'Contractor'),
        ('QA', 'QA'),
    ], default='Client')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Site(models.Model):
    site_id = models.CharField(max_length=100, unique=True)
    site_name = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    location = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Updated to ManyToMany for multiple contractors
    assigned_contractors = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='assigned_sites'
    )
    
    priority = models.CharField(max_length=20, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], default='Medium')

    def __str__(self):
        return f"{self.site_id} - {self.site_name}"

# ADDED THESE BACK IN:
class Report(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='reports')
    contractor = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)

    # NEW: Status field with your director's exact statuses + color coding ready
    STATUS_CHOICES = [
        ('not_visited', 'Not Visited'),
        ('visit_in_progress', 'Visit In Progress'),
        ('site_data_submitted', 'Site Data Submitted'),
        ('qa_validation', 'QA Validation'),
        ('engineer_review', 'Engineer Review'),
        ('submitted', 'Submitted'),
    ]
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='not_visited'
    )

    def __str__(self):
        return f"Report for {self.site.site_id} by {self.contractor.username}"
class Photo(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='site_photos/')
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Photo for {self.report.site.site_id}"

class SitePhoto(models.Model):
    # These are the statuses the QA can choose from
    STATUS_CHOICES = [
        ('PENDING', 'Pending Validation'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rework Required'),
    ]

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='photos')
    contractor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Contractors'})
    image = models.ImageField(upload_to='site_photos/%Y/%m/%d/')
    
    # QA Assessment fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    qa_feedback = models.TextField(blank=True, null=True, help_text="Reason for rework if rejected.")
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.site.site_id} by {self.contractor.username} - {self.status}"

class ActivityAlert(models.Model):
    # The actual alert message
    message = models.CharField(max_length=255)
    
    # The contractor who triggered the alert
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triggered_alerts')
    
    # The site this alert is about
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='site_alerts')
    
    # Automatically records exactly when this happened
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # We can use this later to filter alerts specifically for QAs, Clients, etc.
    alert_type = models.CharField(max_length=50, choices=[
        ('CHECK_IN', 'Contractor Checked In'),
        ('UPLOAD', 'Photos Uploaded'),
        ('REWORK', 'Rework Requested'),
    ], default='CHECK_IN')

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user.username}: {self.message}"
