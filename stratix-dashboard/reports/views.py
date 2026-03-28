import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q
from .models import Site, SitePhoto, Report, ActivityAlert, Project
from django.http import JsonResponse
from django.utils.timezone import now
import datetime

@login_required
def dashboard_home(request):
    user = request.user
    
    # 1. Establish the "Base" permissions (What is this user allowed to see?)
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        base_sites = Site.objects.all()
        base_reports = Report.objects.all()
        available_projects = Project.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        base_sites = Site.objects.filter(project__client=user.profile.client)
        base_reports = Report.objects.filter(site__in=base_sites)
        available_projects = Project.objects.filter(client=user.profile.client)
    else:
        base_sites = Site.objects.filter(assigned_contractors=user)
        base_reports = Report.objects.filter(site__in=base_sites)
        available_projects = Project.objects.filter(sites__in=base_sites).distinct()

    # 2. APPLY THE NEW PROJECT FILTER
    selected_project_id = request.GET.get('project')
    if selected_project_id:
        sites = base_sites.filter(project_id=selected_project_id)
        reports = base_reports.filter(site__project_id=selected_project_id)
        current_project = available_projects.filter(id=selected_project_id).first()
    else:
        sites = base_sites
        reports = base_reports
        current_project = None

    # 3. CALCULATE THE 8 METRICS
    total_sites_received = sites.count()
    total_reports_completed = reports.filter(status='submitted').count()
    total_reports_needs_completion = total_sites_received - total_reports_completed
    
    visits_completed = reports.filter(status__in=['site_data_submitted', 'qa_validation', 'engineer_review', 'submitted']).count()
    reports_in_progress = reports.filter(status__in=['site_data_submitted', 'engineer_review']).count()
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'Client'):
        pending_photos_validation = SitePhoto.objects.filter(site__in=sites, status='PENDING').count()
    else:
        pending_photos_validation = SitePhoto.objects.filter(status='PENDING').count()
        
    pending_report_validation = reports.filter(status='engineer_review').count()

    # 4. RESTORE CHART & STATUS BOARD DATA
    chart_data = [
        reports.filter(status='not_visited').count(),
        reports.filter(status='visit_in_progress').count(),
        reports.filter(status='site_data_submitted').count(),
        reports.filter(status='qa_validation').count(),
        reports.filter(status='engineer_review').count(),
        reports.filter(status='submitted').count(),
    ]

    status_labels = ['Not Visited', 'Visit In Progress', 'Site Data Submitted', 'QA Validation', 'Engineer Review', 'Completed/Delivered']
    status_colors = ['#64748b', '#f59e0b', '#0ea5e9', '#f97316', '#8b5cf6', '#10b981']

    status_data = [{'count': chart_data[i], 'label': status_labels[i], 'color': status_colors[i]} for i in range(6)]

    status_board = [
        {'stage': 'Pending QA Validation', 'count': pending_photos_validation, 'icon': 'fa-camera', 'color': 'warning', 'example': 'Photos uploaded by contractors, awaiting QA review.'},
        {'stage': 'Tech Drafting In Progress', 'count': reports_in_progress, 'icon': 'fa-pen-nib', 'color': 'info', 'example': 'Approved sites currently being drafted into PDF reports.'},
        {'stage': 'Completed & Delivered', 'count': total_reports_completed, 'icon': 'fa-check-double', 'color': 'success', 'example': 'Final technical reports successfully delivered.'},
    ]

    context = {
        'user': user,
        'available_projects': available_projects,
        'current_project': current_project,
        'total_sites_received': total_sites_received,
        'total_reports_needs_completion': total_reports_needs_completion,
        'total_reports_completed': total_reports_completed,
        'visits_completed': visits_completed,
        'reports_in_progress': reports_in_progress,
        'pending_photos_validation': pending_photos_validation,
        'pending_report_validation': pending_report_validation,
        'status_data': status_data,
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
                    site=site, contractor=user, image=image, status='PENDING',
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
def start_visit(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'visit_in_progress'
    report.save()
    ActivityAlert.objects.create(
        message=f"Contractor has arrived on site.", user=request.user, site=report.site, alert_type='CHECK_IN'
    )
    return redirect('site_visit_list')

@login_required
def site_visit_list(request):
    user = request.user
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        reports_list = Report.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        reports_list = Report.objects.filter(site__project__client=user.profile.client)
    else:
        reports_list = Report.objects.filter(site__assigned_contractors=user)

    search = request.GET.get('search', '')
    if search:
        reports_list = reports_list.filter(Q(site__site_id__icontains=search) | Q(site__site_name__icontains=search))
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
        notes = request.POST.get('notes', '')
        if new_image:
            photo.image = new_image
            photo.status = 'PENDING'
            photo.qa_feedback = f"Rework Submitted | Notes: {notes}"
            photo.save()
            ActivityAlert.objects.create(
                message=f"Contractor uploaded a fix.", user=request.user, site=photo.site, alert_type='UPLOAD'
            )
            return redirect('rework_log')
    return render(request, 'reports/rework_upload.html', {'photo': photo})

@login_required
def qa_hub(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
    sites_needing_review = Site.objects.filter(photos__status='PENDING').distinct()
    return render(request, 'reports/qa_hub.html', {'sites': sites_needing_review})

@login_required
def qa_review(request, site_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')

    site = get_object_or_404(Site, id=site_id)
    pending_photos = SitePhoto.objects.filter(site=site, status='PENDING')

    if request.method == 'POST':
        photo = get_object_or_404(SitePhoto, id=request.POST.get('photo_id'))
        action = request.POST.get('action')
        photo.qa_feedback = request.POST.get('feedback', '')
        
        if action == 'approve':
            photo.status = 'APPROVED'
        elif action == 'reject':
            photo.status = 'REJECTED'
            ActivityAlert.objects.create(message="QA rejected photo.", user=request.user, site=site, alert_type='REWORK')
        photo.save()

        if SitePhoto.objects.filter(site=site, status__in=['PENDING', 'REJECTED']).count() == 0 and SitePhoto.objects.filter(site=site).count() > 0:
            report = Report.objects.filter(site=site).first()
            if report and report.status == 'visit_in_progress':
                report.status = 'site_data_submitted'
                report.save()
                ActivityAlert.objects.create(message="Site Validated. Ready for technical writing.", user=request.user, site=site, alert_type='UPLOAD')
            return redirect('qa_hub')
        return redirect('qa_review', site_id=site.id)

    return render(request, 'reports/qa_review.html', {'site': site, 'photos': pending_photos})

@login_required
def tech_writer_hub(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer'])):
        return redirect('dashboard_home')
        
    reports_to_draft = Report.objects.filter(status='site_data_submitted')
    return render(request, 'reports/tech_writer_hub.html', {'reports': reports_to_draft})

@login_required
def draft_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer'])):
        return redirect('dashboard_home')

    report = get_object_or_404(Report, id=report_id)
    approved_photos = SitePhoto.objects.filter(site=report.site, status='APPROVED')

    if request.method == 'POST':
        final_pdf = request.FILES.get('final_document')
        comments = request.POST.get('comments', '')
        
        if final_pdf:
            report.final_document = final_pdf
            report.comments = comments
            report.status = 'submitted' 
            report.save()
            
            ActivityAlert.objects.create(
                message="Final Technical Report uploaded.", user=request.user, site=report.site, alert_type='UPLOAD'
            )
            return redirect('tech_writer_hub')

    return render(request, 'reports/draft_report.html', {'report': report, 'photos': approved_photos})

@login_required
def custom_logout(request):
    logout(request)
    return redirect('login')

# ==========================================
# BACKGROUND API FOR LIVE NOTIFICATIONS
# ==========================================
@login_required
def api_check_alerts(request):
    user = request.user
    last_check_str = request.session.get('last_alert_check')
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        alerts = ActivityAlert.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        base_sites = Site.objects.filter(project__client=user.profile.client)
        alerts = ActivityAlert.objects.filter(site__in=base_sites, alert_type='UPLOAD', message__icontains='Final')
    elif hasattr(user, 'profile') and user.profile.role == 'Tech Writer':
        alerts = ActivityAlert.objects.filter(message__icontains='technical writing')
    else:
        base_sites = Site.objects.filter(assigned_contractors=user)
        alerts = ActivityAlert.objects.filter(site__in=base_sites)

    if last_check_str:
        last_check = datetime.datetime.fromisoformat(last_check_str)
        new_alerts = alerts.filter(timestamp__gt=last_check).order_by('-timestamp')
    else:
        new_alerts = []

    request.session['last_alert_check'] = now().isoformat()

    alerts_data = []
    for a in new_alerts:
        alerts_data.append({
            'message': a.message,
            'site': a.site.site_id,
            'type': a.alert_type
        })

    return JsonResponse({'new_alerts': alerts_data})

def geographical_map_view(request):
    # 1. Fetch all your sites
    sites = Site.objects.all()
    
    # 2. Package the data into a list of dictionaries
    sites_data = []
    for site in sites:
        sites_data.append({
            'name': site.name,
            'lat': float(site.latitude),   # Make sure these match your model's field names
            'lng': float(site.longitude),
            'status': site.status          # e.g., 'Good', 'Minor', 'Critical'
        })
    
    # 3. Convert to JSON so JavaScript can understand it
    context = {
        'sites_json': json.dumps(sites_data)
    }
    
    return render(request, 'geographical_map_view.html', context)
