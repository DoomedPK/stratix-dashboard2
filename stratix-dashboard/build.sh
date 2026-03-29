#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Convert static files (CSS/JS) for Whitenoise
python manage.py collectstatic --no-input

# Run database migrations to Supabase
python manage.py migrate


