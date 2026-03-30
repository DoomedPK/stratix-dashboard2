import json
import csv
import io
import datetime
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Site, SitePhoto, Report, ActivityAlert, Project, SiteIssue, Client
from django.utils.timezone import now
from django.urls import reverse

# --- CATEGORY MINIMUMS ---
PHOTO_MINIMUMS = {
    'Site Overview': 4,
    'Access Road': 2,
    'Tower Structure': 5,
    'Tower Base & Foundation': 14,
    'Antennas & Mounting Systems': 9,
    'Cabling & Connections': 3,
    'Equipment Shelter / Cabinets': 2,
    'Power Systems': 2,
    'Grounding & Earthing': 2,
    'Perimeter, Security & Surroundings': 5,
    'Additional Observations': 0,
}

@login_required
def dashboard_home(request):
    user = request.user
    
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

    selected_project_id = request.GET.get('project')
    if selected_project_id:
        sites = base_sites.filter(project_id=selected_project_id)
        reports = base_reports.filter(site__project_id=selected_project_id)
        current_project = available_projects.filter(id=selected_project_id).first()
    else:
        sites = base_sites
        reports = base_reports
        current_project = None

    total_sites_received = sites.count()
    total_reports_completed = reports.filter(status='submitted').count()
    total_reports_needs_completion = total_sites_received - total_reports_completed
    
    visits_completed = reports.filter(status__in=['site_data_submitted', 'qa_validation', 'engineer_review', 'submitted']).count()
    visits_remaining = total_sites_received - visits_completed
    visits_in_progress_count = reports.filter(status='visit_in_progress').count()
    reports_in_progress = reports.filter(status__in=['site_data_submitted', 'engineer_review']).count()
    
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'Client'):
        pending_photos_validation = SitePhoto.objects.filter(site__in=sites, status='PENDING').count()
    else:
        pending_photos_validation = SitePhoto.objects.filter(status='PENDING').count()
        
    pending_report_validation = reports.filter(status='engineer_review').count()

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
        {'stage': 'Tech Drafting In Progress', 'count': reports_in_progress, 'icon': 'fa-pen-nib', 'color': 'info', 'example': 'Approved sites currently being drafted into reports.'},
        {'stage': 'Completed & Delivered', 'count': total_reports_completed, 'icon': 'fa-check-double', 'color': 'success', 'example': 'Final technical reports successfully delivered.'},
    ]

    sites_data = []
    for site in sites:
        if site.latitude and site.longitude:
            issues = site.issues.filter(is_resolved=False)
            if issues.filter(severity='Critical').exists():
                site_status = 'Critical Issue'
                color = '#ef4444' 
            elif issues.filter(severity='Major').exists():
                site_status = 'Major Issue'
                color = '#f97316' 
            elif issues.filter(severity='Minor').exists():
                site_status = 'Minor Issue'
                color = '#eab308' 
            else:
                report = Report.objects.filter(site=site).first()
                if report and report.status == 'submitted':
                    site_status = 'Completed (Good Condition)'
                    color = '#10b981' 
                else:
                    site_status = 'In Progress'
                    color = '#3b82f6' 
                    
            sites_data.append({
                'name': site.site_id,
                'site_name': site.site_name,
                'lat': float(site.latitude),
                'lng': float(site.longitude),
                'status': site_status,
                'color': color
            })

    total_tat_days = 0
    tat_count = 0
    for r in reports.filter(status='submitted'):
        final_alert = ActivityAlert.objects.filter(site=r.site, alert_type='UPLOAD', message__icontains='Final').order_by('-timestamp').first()
        if final_alert:
            delta = final_alert.timestamp - r.submitted_at
            total_tat_days += delta.days
            tat_count += 1
    avg_tat = round(total_tat_days / tat_count, 1) if tat_count > 0 else 0

    trend_labels = []
    tat_trend = []
    rework_trend = []
    current_date = now().date()
    
    for i in range(5, -1, -1):
        target_month = (current_date.month - i - 1) % 12 + 1
        target_year = current_date.year + ((current_date.month - i - 1) // 12)
        month_label = datetime.date(target_year, target_month, 1).strftime('%b %Y')
        trend_labels.append(month_label)
        
        m_reports = reports.filter(status='submitted')
        m_total_tat = 0
        m_tat_count = 0
        for r in m_reports:
            final_alert = ActivityAlert.objects.filter(site=r.site, alert_type='UPLOAD', message__icontains='Final', timestamp__year=target_year, timestamp__month=target_month).order_by('-timestamp').first()
            if final_alert and hasattr(r, 'submitted_at') and r.submitted_at:
                delta = final_alert.timestamp - r.submitted_at
                m_total_tat += delta.days
                m_tat_count += 1
        tat_trend.append(round(m_total_tat / m_tat_count, 1) if m_tat_count > 0 else 0)
        
        m_photos = SitePhoto.objects.filter(site__in=sites, uploaded_at__year=target_year, uploaded_at__month=target_month)
        m_total_subs = m_photos.count()
        m_reworks = m_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).count()
        rework_trend.append(round((m_reworks / m_total_subs * 100), 1) if m_total_subs > 0 else 0)
    
    contractor_stats = []
    is_client_or_admin = user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Client'])
    is_contractor = hasattr(user, 'profile') and user.profile.role == 'Contractor'
    
    if is_client_or_admin:
        contractors_to_track = User.objects.filter(assigned_sites__in=sites).distinct()
    elif is_contractor:
        contractors_to_track = User.objects.filter(id=user.id)
    else:
        contractors_to_track = []

    for c in contractors_to_track:
        c_photos = SitePhoto.objects.filter(contractor=c, site__in=sites)
        total_subs = c_photos.count()
        reworks = c_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).count()
        rework_rate = round((reworks / total_subs * 100), 1) if total_subs > 0 else 0
        
        recent_reworks = c_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).exclude(qa_feedback__isnull=True).exclude(qa_feedback='').order_by('-uploaded_at')[:2]
        common_errors = [p.qa_feedback for p in recent_reworks] if recent_reworks else ["No frequent errors detected."]

        contractor_stats.append({
            'id': c.id,
            'name': f"{c.first_name} {c.last_name}".strip() or c.username,
            'total_submissions': total_subs,
            'rework_rate': rework_rate,
            'common_errors': common_errors
        })

    context = {
        'user': user,
        'available_projects': available_projects,
        'current_project': current_project,
        'total_sites_received': total_sites_received,
        'total_reports_needs_completion': total_reports_needs_completion,
        'total_reports_completed': total_reports_completed,
        'visits_completed': visits_completed,
        'visits_remaining': visits_remaining,
        'visits_in_progress_count': visits_in_progress_count,
        'reports_in_progress': reports_in_progress,
        'pending_photos_validation': pending_photos_validation,
        'pending_report_validation': pending_report_validation,
        'status_data': status_data,
        'status_board': status_board,
        'sites_json': json.dumps(sites_data),
        'avg_tat': avg_tat,
        'contractor_stats': contractor_stats,
        'show_performance': is_client_or_admin or is_contractor,
        'is_client_or_admin': is_client_or_admin,
        'trend_labels': json.dumps(trend_labels),
        'tat_trend': json.dumps(tat_trend),
        'rework_trend': json.dumps(rework_trend),
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def import_sites(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'Admin')):
        return redirect('dashboard_home')

    if request.method == 'POST':
        file = request.FILES.get('import_file')
        if not file:
            messages.error(request, "Please select a file to upload.")
            return redirect('import_sites')

        if not file.name.endswith('.csv'):
            messages.error(request, "Invalid file format. Please ensure you saved your Excel file as a .csv")
            return redirect('import_sites')

        try:
            decoded_file = file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                site_id = clean_row.get('site_id')
                site_name = clean_row.get('site_name', 'Unnamed Site')
                project_name = clean_row.get('project')
                location = clean_row.get('location', '')
                lat_val = clean_row.get('latitude')
                lng_val = clean_row.get('longitude')
                priority = clean_row.get('priority', 'Medium')

                if not site_id or not project_name:
                    error_count += 1
                    continue
                    
                latitude = float(lat_val) if lat_val else None
                longitude = float(lng_val) if lng_val else None
                
                default_client, _ = Client.objects.get_or_create(name="Unassigned Client (Auto-Imported)")
                project, p_created = Project.objects.get_or_create(name=project_name, defaults={'client': default_client})
                
                site, s_created = Site.objects.update_or_create(
                    site_id=site_id,
                    defaults={'site_name': site_name, 'project': project, 'location': location, 'latitude': latitude, 'longitude': longitude, 'priority': priority}
                )
                
                if s_created:
                    Report.objects.create(site=site, status='not_visited')
                    ActivityAlert.objects.create(message=f"Bulk imported site {site_id}.", user=user, site=site, alert_type='UPLOAD')
                    
                success_count += 1
            
            messages.success(request, f"Successfully imported/updated {success_count} sites! {error_count} rows skipped.")
            return redirect('site_visit_list')
            
        except Exception as e:
            messages.error(request, f"Error reading file. Ensure it matches the template format. ({str(e)})")
            return redirect('import_sites')

    return render(request, 'reports/import_sites.html')


@login_required
def site_visit_list(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        reports_list = Report.objects.all()
        projects = Project.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        reports_list = Report.objects.filter(site__project__client=user.profile.client)
        projects = Project.objects.filter(client=user.profile.client)
    else:
        reports_list = Report.objects.filter(site__assigned_contractors=user)
        projects = Project.objects.filter(sites__assigned_contractors=user).distinct()

    return render(request, 'reports/site_list.html', {'reports': reports_list, 'projects': projects})

@login_required
def report_issue(request, site_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('site_visit_list')

    if request.method == 'POST':
        site = get_object_or_404(Site, id=site_id)
        severity = request.POST.get('severity', 'Minor')
        description = request.POST.get('description', 'No description provided.')
        SiteIssue.objects.create(site=site, reported_by=request.user, severity=severity, description=description)
        ActivityAlert.objects.create(message=f"{severity} issue logged for this site.", user=request.user, site=site, alert_type='REWORK')
        messages.success(request, f"Issue logged for Site {site.site_id}.")
        
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('site_visit_list')

@login_required
def site_issues_list(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        issues = SiteIssue.objects.filter(is_resolved=False).order_by('-created_at')
        projects = Project.objects.filter(sites__issues__is_resolved=False).distinct()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        issues = SiteIssue.objects.filter(site__project__client=user.profile.client, is_resolved=False).order_by('-created_at')
        projects = Project.objects.filter(client=user.profile.client, sites__issues__is_resolved=False).distinct()
    else:
        issues = SiteIssue.objects.filter(site__assigned_contractors=user, is_resolved=False).order_by('-created_at')
        projects = Project.objects.filter(sites__assigned_contractors=user, sites__issues__is_resolved=False).distinct()

    return render(request, 'reports/site_issues.html', {'issues': issues, 'projects': projects})


# 🚀 FIX 1 & 2: Pre-selected site upload flow & Categories
@login_required
def upload_photos(request):
    user = request.user
    
    # Pre-select site from URL or POST
    site_id = request.GET.get('site_id') or request.POST.get('site_id')
    selected_site = get_object_or_404(Site, id=site_id) if site_id else None

    if request.method == 'POST' and selected_site:
        category = request.POST.get('category')
        notes = request.POST.get('contractor_notes')
        images = request.FILES.getlist('site_images')
        
        for image in images:
            SitePhoto.objects.create(
                site=selected_site, contractor=user, image=image, status='PENDING',
                category=category, contractor_notes=notes
            )
        messages.success(request, f"Uploaded {len(images)} photos to '{category}'.")
        return redirect(f"{reverse('upload_photos')}?site_id={selected_site.id}")

    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        sites = Site.objects.filter(reports__status='visit_in_progress').distinct()
    else:
        sites = Site.objects.filter(assigned_contractors=user, reports__status='visit_in_progress').distinct()

    uploaded_photos = SitePhoto.objects.filter(site=selected_site, contractor=user).order_by('-uploaded_at') if selected_site else None

    return render(request, 'reports/upload_photo.html', {
        'sites': sites, 
        'selected_site': selected_site, 
        'uploaded_photos': uploaded_photos,
        'minimums': PHOTO_MINIMUMS
    })

@login_required
def finish_upload(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    if request.method == 'POST':
        
        # 🚀 FIX 2: Check Photo Minimums if Admin enabled it
        if site.project.require_photo_minimums:
            missing = []
            for cat, min_count in PHOTO_MINIMUMS.items():
                if min_count > 0:
                    count = SitePhoto.objects.filter(site=site, category=cat).count()
                    if count < min_count:
                        missing.append(f"{cat} (needs {min_count - count} more)")
            
            if missing:
                messages.error(request, "Cannot finish upload! Missing required photos: " + ", ".join(missing))
                return redirect(f"{reverse('upload_photos')}?site_id={site.id}")
        
        report = site.reports.first()
        if report and report.status == 'visit_in_progress':
            report.status = 'qa_validation' # Sends it to QA
            report.save()
            ActivityAlert.objects.create(message=f"Contractor finished uploading photos for QA validation.", user=request.user, site=site, alert_type='UPLOAD')
            messages.success(request, "Uploads completed and sent to QA for validation!")
    
    return redirect('site_visit_list')

@login_required
def start_visit(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.status = 'visit_in_progress'
    report.save()
    ActivityAlert.objects.create(message=f"Contractor has arrived on site.", user=request.user, site=report.site, alert_type='CHECK_IN')
    # 🚀 FIX 1: Auto-redirect straight into the upload hub with the site selected!
    return redirect(f"{reverse('upload_photos')}?site_id={report.site.id}")

@login_required
def rework_log(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA']):
        reworks = SitePhoto.objects.filter(status='REJECTED').order_by('-uploaded_at')
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        reworks = SitePhoto.objects.filter(site__project__client=user.profile.client, status='REJECTED').order_by('-uploaded_at')
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
        notes = request.POST.get('contractor_notes', '')
        if new_image:
            photo.image = new_image
            photo.status = 'PENDING'
            photo.contractor_notes = notes
            photo.qa_feedback = f"[Rework Submitted] " + (photo.qa_feedback or "")
            photo.save()
            ActivityAlert.objects.create(message=f"Contractor uploaded a fix.", user=request.user, site=photo.site, alert_type='UPLOAD')
            return redirect('rework_log')
    return render(request, 'reports/rework_upload.html', {'photo': photo})

@login_required
def qa_hub(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    sites_needing_review = Site.objects.filter(photos__status='PENDING').distinct()
    drafted_reports = Report.objects.filter(status='engineer_review')
    
    return render(request, 'reports/qa_hub.html', {'sites': sites_needing_review, 'drafted_reports': drafted_reports})

@login_required
def qa_review(request, site_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')

    site = get_object_or_404(Site, id=site_id)
    # Grouping logic handled in the template now!
    pending_photos = SitePhoto.objects.filter(site=site, status='PENDING').order_by('category')

    if request.method == 'POST':
        photo = get_object_or_404(SitePhoto, id=request.POST.get('photo_id'))
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')
        
        if action == 'approve':
            photo.status = 'APPROVED'
        elif action == 'reject':
            photo.status = 'REJECTED'
            ActivityAlert.objects.create(message="QA rejected photo.", user=request.user, site=site, alert_type='REWORK')
            
        if 'Rework' in (photo.qa_feedback or ""):
            photo.qa_feedback = f"[Reworked] {feedback}"
        else:
            photo.qa_feedback = feedback
        photo.save()

        if SitePhoto.objects.filter(site=site, status__in=['PENDING', 'REJECTED']).count() == 0 and SitePhoto.objects.filter(site=site).count() > 0:
            report = Report.objects.filter(site=site).first()
            if report and report.status == 'qa_validation':
                report.status = 'site_data_submitted'
                report.save()
                ActivityAlert.objects.create(message="Site Validated. Ready for technical writing.", user=request.user, site=site, alert_type='UPLOAD')
            return redirect('qa_hub')
        return redirect('qa_review', site_id=site.id)
    return render(request, 'reports/qa_review.html', {'site': site, 'photos': pending_photos})

@login_required
def approve_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':
        report.status = 'submitted'
        report.save()
        ActivityAlert.objects.create(message="Final Technical Report Approved and Sent to Client.", user=request.user, site=report.site, alert_type='UPLOAD')
        messages.success(request, "Report Approved and Delivered!")
    return redirect('qa_hub')

# 🚀 FIX 6: QA Decline Final Report
@login_required
def decline_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA'])):
        return redirect('dashboard_home')
        
    report = get_object_or_404(Report, id=report_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided.')
        report.status = 'site_data_submitted' # Kicks it back to Tech Writer
        report.final_document = None # Clears the bad PDF
        report.comments = f"DECLINED BY QA: {reason} | Previous Notes: {report.comments}"
        report.save()
        ActivityAlert.objects.create(message="QA declined the drafted report.", user=user, site=report.site, alert_type='REWORK')
        messages.warning(request, "Report declined and sent back to Technical Writer.")
    return redirect('qa_hub')

@login_required
def tech_writer_hub(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Tech Writer', 'QA'])):
        return redirect('dashboard_home')
        
    reports_to_draft = Report.objects.filter(status='site_data_submitted')
    return render(request, 'reports/tech_writer_hub.html', {'reports': reports_to_draft})

@login_required
def draft_report(request, report_id):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Tech Writer', 'QA'])):
        return redirect('dashboard_home')

    report = get_object_or_404(Report, id=report_id)
    approved_photos = SitePhoto.objects.filter(site=report.site, status='APPROVED').order_by('category')

    if request.method == 'POST':
        final_pdf = request.FILES.get('final_document')
        comments = request.POST.get('comments', '')
        
        if final_pdf:
            report.final_document = final_pdf
            report.comments = comments
            report.status = 'engineer_review' 
            report.save()
            ActivityAlert.objects.create(message="Draft Report submitted for QA final approval.", user=request.user, site=report.site, alert_type='UPLOAD')
            messages.success(request, "Draft sent to QA!")
            return redirect('tech_writer_hub')

    return render(request, 'reports/draft_report.html', {'report': report, 'photos': approved_photos})

@login_required
def custom_logout(request):
    logout(request)
    return redirect('login')

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
    alerts_data = [{'message': a.message, 'site': a.site.site_id, 'type': a.alert_type} for a in new_alerts]
    return JsonResponse({'new_alerts': alerts_data})

@login_required
def geographical_map_view(request):
    user = request.user
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'QA', 'Tech Writer']):
        sites = Site.objects.all()
    elif hasattr(user, 'profile') and user.profile.role == 'Client':
        sites = Site.objects.filter(project__client=user.profile.client)
    else:
        sites = Site.objects.filter(assigned_contractors=user)
    
    sites_data = []
    for site in sites:
        if site.latitude and site.longitude:
            issues = site.issues.filter(is_resolved=False)
            if issues.filter(severity='Critical').exists():
                site_status = 'Critical Issue'
                color = '#ef4444' 
            elif issues.filter(severity='Major').exists():
                site_status = 'Major Issue'
                color = '#f97316' 
            elif issues.filter(severity='Minor').exists():
                site_status = 'Minor Issue'
                color = '#eab308' 
            else:
                report = Report.objects.filter(site=site).first()
                if report and report.status == 'submitted':
                    site_status = 'Completed (Good Condition)'
                    color = '#10b981' 
                else:
                    site_status = 'In Progress'
                    color = '#3b82f6' 
                    
            sites_data.append({
                'name': site.site_id,
                'site_name': site.site_name,
                'lat': float(site.latitude),
                'lng': float(site.longitude),
                'status': site_status,
                'color': color
            })
            
    return render(request, 'reports/geographical_map_view.html', {'sites_json': json.dumps(sites_data)})

@login_required
def export_performance_csv(request):
    user = request.user
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Client'])):
        return redirect('dashboard_home')
    
    if hasattr(user, 'profile') and user.profile.role == 'Client':
        sites = Site.objects.filter(project__client=user.profile.client)
    else:
        sites = Site.objects.all()
        
    selected_project_id = request.GET.get('project')
    if selected_project_id:
        sites = sites.filter(project_id=selected_project_id)
        
    contractors = User.objects.filter(assigned_sites__in=sites).distinct()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Contractor_Performance_Export.csv"'
    writer = csv.writer(response)
    writer.writerow(['Contractor Name', 'Total Submissions', 'Reworks', 'Rework Rate (%)', 'Common Errors'])
    
    for c in contractors:
        c_photos = SitePhoto.objects.filter(contractor=c, site__in=sites)
        total_subs = c_photos.count()
        reworks = c_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).count()
        rework_rate = round((reworks / total_subs * 100), 1) if total_subs > 0 else 0
        recent_reworks = c_photos.filter(Q(status='REJECTED') | Q(qa_feedback__icontains='Rework')).exclude(qa_feedback__isnull=True).exclude(qa_feedback='').order_by('-uploaded_at')[:2]
        errors = " | ".join([p.qa_feedback for p in recent_reworks]) if recent_reworks else "None"
        writer.writerow([f"{c.first_name} {c.last_name}".strip() or c.username, total_subs, reworks, rework_rate, errors])
    return response

@login_required
def support_page(request):
    if request.method == 'POST':
        # In the future, this can be wired to send an actual email via SendGrid/AWS SES.
        # For now, it logs the request and shows a success message.
        ticket_subject = request.POST.get('subject', 'General Support')
        ActivityAlert.objects.create(
            message=f"Submitted a Support Ticket: {ticket_subject}", 
            user=request.user, 
            site=Site.objects.first(), # Just attaching to a dummy site for the alert log
            alert_type='REWORK'
        )
        messages.success(request, "Your support ticket has been prioritized and sent to the Engineering Team. We will contact you shortly!")
        return redirect('dashboard_home')
        
    return render(request, 'reports/support.html')
