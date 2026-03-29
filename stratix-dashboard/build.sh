#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies from the correct folder
pip install -r stratix-dashboard/requirements.txt

# Run Django commands from within the project folder
cd stratix-dashboard
python manage.py collectstatic --no-input
python manage.py migrate
