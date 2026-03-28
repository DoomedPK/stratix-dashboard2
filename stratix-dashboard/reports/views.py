from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q
from .models import Site, SitePhoto, Report, ActivityAlert

def dashboard(request):
    total_sites = Site.objects.count()
    
    pending_photos = SitePhoto.objects.filter(status='PENDING').count()
    approved_photos = SitePhoto.objects.filter(status='APPROVED').count()
    rework_photos = SitePhoto.objects.filter(status='REJECTED').count()

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
        'total_reports': 0, 
        'status_board': status_board,
    }
    
    return render(request, 'reports/dashboard.html', context)

@login_required
def upload_photos(request):
    user = request.user
    
    if request.method == 'POST':
        site_id = request.POST.get('site_id')
        category = request.POST.get('category')
        notes = request.POST.get('notes')
        images = request.FILES.getlist('site_images')
        
        try:
            site = Site.objects.get(id=site_id)
            for image in images:
                SitePhoto.objects.create(
                    site=site,
                    contractor=user,
                    image=image,
                    status='PENDING',
                    qa_feedback=f"Category: {category} | Notes: {notes}"
                )
            return redirect('site_visit_list')
        except Site.DoesNotExist:
            pass

    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        sites = Site.objects.filter(reports__status='visit_in_progress').distinct()
    else:
        sites = Site.objects.filter(assigned_contractors=user, reports__status='visit_in_progress').distinct()
        
    return render(request, 'reports/upload_photo.html', {'sites': sites})

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

    status_board = [
        {'stage': 'Visit', 'count': chart_data[0], 'example': 'Sites awaiting initial contractor visit'},
        {'stage': 'Photos', 'count': chart_data[1], 'example': 'Photos uploaded, pending QA validation'},
        {'stage': 'Drafting', 'count': chart_data[2], 'example': 'Technical report drafting in progress'},
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
def start_visit(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'visit_in_progress'
    report.save()
    
    ActivityAlert.objects.create(
        message=f"Contractor has arrived on site and commenced the visit.",
        user=request.user,
        site=report.site,
        alert_type='CHECK_IN'
    )
    
    return redirect('site_visit_list')

@login_required
def site_visit_list(request):
    user = request.user
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        reports_list = Report.objects.all()
    else:
        reports_list = Report.objects.filter(site__assigned_contractors=user)

    search = request.GET.get('search', '')
    if search:
        reports_list = reports_list.filter(
            Q(site__site_id__icontains=search) |
            Q(site__site_name__icontains=search) |
            Q(site__location__icontains=search)
        )

    return render(request, 'reports/site_list.html', {'reports': reports_list})

@login_required
def rework_log(request):
    user = request.user
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        reworks = SitePhoto.objects.filter(status='REJECTED').order_by('-uploaded_at')
    else:
        reworks = SitePhoto.objects.filter(contractor=user, status='REJECTED').order_by('-uploaded_at')
        
    return render(request, 'reports/rework_log.html', {'reworks': reworks})

@login_required
def rework_upload(request, photo_id):
    photo = get_object_or_404(SitePhoto, id=photo_id, status='REJECTED')
    
    if not request.user.is_superuser and request.user != photo.contractor:
        return redirect('rework_log')

    if request.method == 'POST':
        new_image = request.FILES.get('replacement_image')
        contractor_notes = request.POST.get('notes', '')
        
        if new_image:
            photo.image = new_image
            photo.status = 'PENDING'
            photo.qa_feedback = f"Rework Submitted | Notes: {contractor_notes}"
            photo.save()
            
            ActivityAlert.objects.create(
                message=f"Contractor uploaded a fix for a rejected photo.",
                user=request.user,
                site=photo.site,
                alert_type='UPLOAD'
            )
            return redirect('rework_log')

    return render(request, 'reports/rework_upload.html', {'photo': photo})

# NEW: The QA Dashboard showing sites that need review
@login_required
def qa_hub(request):
    user = request.user
    # Security: Bounce contractors out of this view
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    # Grab sites that have at least one PENDING photo
    sites_needing_review = Site.objects.filter(photos__status='PENDING').distinct()
    
    return render(request, 'reports/qa_hub.html', {'sites': sites_needing_review})

# NEW: The actual review screen where QAs assess the photos
@login_required
def qa_review(request, site_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')

    site = get_object_or_404(Site, id=site_id)
    pending_photos = SitePhoto.objects.filter(site=site, status='PENDING')

    if request.method == 'POST':
        photo_id = request.POST.get('photo_id')
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')

        photo = get_object_or_404(SitePhoto, id=photo_id)

        if action == 'approve':
            photo.status = 'APPROVED'
            photo.qa_feedback = feedback
            photo.save()
        elif action == 'reject':
            photo.status = 'REJECTED'
            photo.qa_feedback = feedback
            photo.save()
            # Alert the contractor that rework is needed
            ActivityAlert.objects.create(
                message=f"QA rejected a photo. Rework required.",
                user=request.user,
                site=site,
                alert_type='REWORK'
            )

        # --- THE LOGIC CHECK ---
        # Are there any pending or rejected photos left for this site?
        remaining_issues = SitePhoto.objects.filter(
            site=site,
            status__in=['PENDING', 'REJECTED']
        ).count()

        total_photos = SitePhoto.objects.filter(site=site).count()

        # If 100% of the photos are Approved
        if remaining_issues == 0 and total_photos > 0:
            report = Report.objects.filter(site=site).first()
            if report and report.status == 'visit_in_progress':
                # Upgrade the report status!
                report.status = 'site_data_submitted'
                report.save()
                
                # Fire the final completion alert
                ActivityAlert.objects.create(
                    message=f"Site Data 100% Validated by QA. Ready for technical report drafting.",
                    user=request.user,
                    site=site,
                    alert_type='UPLOAD'
                )
            return redirect('qa_hub') # Send them back to the hub if the site is finished

        return redirect('qa_review', site_id=site.id) # Stay on page to review next photo

    return render(request, 'reports/qa_review.html', {'site': site, 'photos': pending_photos})

@login_required
def custom_logout(request):
    logout(request)
    return redirect('login')
