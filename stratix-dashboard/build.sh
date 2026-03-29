#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r stratix-dashboard/requirements.txt

# Run Django commands
cd stratix-dashboard
python manage.py collectstatic --no-input
python manage.py migrate

python manage.py makemigrations 
python manage.py migrate
# Automatically create the superuser on Supabase!
# (The || true prevents build crashes on future deploys if the user already exists)
python create_admin.py || true
