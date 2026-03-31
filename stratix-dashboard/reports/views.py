@login_required
def client_portal(request):
    user = request.user
    # Only allow Admins and Clients to see this page
    if not (user.is_superuser or (hasattr(user, 'profile') and user.profile.role in ['Admin', 'Client'])):
        return redirect('dashboard_home')
        
    if hasattr(user, 'profile') and user.profile.role == 'Client':
        completed_reports = Report.objects.filter(site__project__client=user.profile.client, status='submitted').order_by('-submitted_at')
        projects = Project.objects.filter(client=user.profile.client)
    else:
        completed_reports = Report.objects.filter(status='submitted').order_by('-submitted_at')
        projects = Project.objects.all()

    selected_project_id = request.GET.get('project')
    if selected_project_id:
        completed_reports = completed_reports.filter(site__project_id=selected_project_id)
        
    return render(request, 'reports/client_portal.html', {
        'reports': completed_reports, 
        'projects': projects,
        'current_project': selected_project_id
    })
