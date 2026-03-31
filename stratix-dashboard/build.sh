#!/usr/bin/env bash
# exit on error
set -o errexit

# Tell Render to step inside the correct folder where the code lives
cd stratix-dashboard

# Install dependencies and gather static files
pip install -r requirements.txt
python manage.py collectstatic --no-input

# --- SMART DATABASE SYNC FIX ---
# This safely handles the "relation already exists" error by checking if the new 
# photo rules exist yet. If not, it temporarily drops the conflicting table so 
# Django can rebuild the entire schema perfectly in one go.
cat << 'EOF' > fix_db.py
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='reports_project' AND column_name='require_photo_minimums';")
    if not cursor.fetchone():
        print("Detected out-of-sync database. Safely resetting SiteIssue table for clean migration...")
        cursor.execute("DROP TABLE IF EXISTS reports_siteissue CASCADE;")
EOF
python fix_db.py
# -------------------------------

# 🚀 FIX: Explicitly target the 'reports' app so Django is forced to build the SupportTicket table!
python manage.py makemigrations reports
python manage.py migrate

python create_admin.py
