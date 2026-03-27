from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Site, SitePhoto
from .models import Site, Report
from django.db.models import Q

def dashboard(request):
    # Get actual counts from the database
    total_sites = Site.objects.count()
    
    # Count photos based on the STATUS_CHOICES we made earlier
    pending_photos = SitePhoto.objects.filter(status='PENDING').count()
    approved_photos = SitePhoto.objects.filter(status='APPROVED').count()
    rework_photos = SitePhoto.objects.filter(status='REJECTED').count()

    # Build the status board using your real Stratix workflow data
    status_board = [
        {
            'stage': 'Pending QA Validation', 
            'count': pending_photos, 
            'example': 'Photos uploaded by contractors, awaiting QA review.'
        },
        {
            'stage': 'QA Approved', 
            'count': approved_photos, 
            'example': 'Photos validated. Ready for technical report writing.'
        },
        {
            'stage': 'Rework Requested', 
            'count': rework_photos, 
            'example': 'Images rejected. Contractors need to retake photos.'
        },
    ]

    context = {
        'total_sites': total_sites,
        'total_reports': 0, # We will update this when we build the Report model!
        'status_board': status_board,
    }
    
    return render(request, 'dashboard.html', context)

# Placeholder view for our next step!
def upload_photos(request):
    return render(request, 'upload_photos.html')

@login_required
def dashboard_home(request):
    user = request.user
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        reports = Report.objects.all()
    else:
        reports = Report.objects.filter(site__assigned_contractors=user)

    total_reports = reports.count() or 1
    completed = reports.filter(status='submitted').count()
    completion_percentage = round((completed / total_reports) * 100, 1)

    chart_data = [
        reports.filter(status='not_visited').count(),
        reports.filter(status='visit_in_progress').count(),
        reports.filter(status='site_data_submitted').count(),
        reports.filter(status='qa_validation').count(),
        reports.filter(status='engineer_review').count(),
        reports.filter(status='submitted').count(),
    ]

    status_labels = ['Not Visited', 'Visit In Progress', 'Site Data Submitted', 'QA Validation', 'Engineer Review', 'Submitted']
    status_colors = ['secondary', 'warning', 'info', 'orange', 'primary', 'success']

    status_data = [
        {'count': chart_data[i], 'label': status_labels[i], 'color': status_colors[i]}
        for i in range(6)
    ]

    # Dynamic Report Status Board (only first 3 stages shown like your screenshot)
    status_board = [
        {'stage': 'Visit', 'count': chart_data[0], 'example': 'CT-001 (demo - will show real sites when you add data)'},
        {'stage': 'Photos', 'count': chart_data[1], 'example': 'CT-001 (demo - will show real sites when you add data)'},
        {'stage': 'Drafting', 'count': chart_data[2], 'example': 'No reports yet'},
    ]

    context = {
        'user': user,
        'total_sites': Site.objects.count(),
        'total_reports': reports.count(),
        'completed_reports': completed,
        'completion_percentage': completion_percentage,
        'status_data': status_data,
        'status_board': status_board,
    }
    return render(request, 'reports/dashboard.html', context)

@login_required
def site_visit_list(request):
    user = request.user
    sites = Site.objects.all()

    # Search + basic filter (we'll add the full search bar in the next step)
    search = request.GET.get('search', '')
    if search:
        sites = sites.filter(
            Q(site_id__icontains=search) |
            Q(site_name__icontains=search) |
            Q(location__icontains=search)
        )

    # Role-based filtering
    if not (user.is_superuser or user.profile.role in ['Admin', 'QA']):
        sites = sites.filter(assigned_contractors=user)

    return render(request, 'reports/site_list.html', {'sites': sites})



from django.contrib.auth import logout
from django.shortcuts import redirect

@login_required
def custom_logout(request):
    logout(request)
    return redirect('login')   # or 'accounts/login' if you use allauth
