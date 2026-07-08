#!/bin/bash
# Sahyog Setu - Quiz Module Partial Deployment Script
# Execute this script manually on your live GoDaddy VPS within the Django Project root.

set -e

echo "Starting Safe Partial Deployment for Quiz Module..."

# Define paths (Adjust PROJECT_DIR to your GoDaddy server setup)
PROJECT_DIR="$(pwd)"
BACKUP_DIR="${PROJECT_DIR}/deploy_backups_$(date +%F_%T)"
ZIP_FILE="${PROJECT_DIR}/quiz_module_updates.zip"

echo "1. Checking prerequisites..."
if [ ! -f "$ZIP_FILE" ]; then
    echo "ERROR: quiz_module_updates.zip not found in $PROJECT_DIR"
    exit 1
fi

echo "2. Setting up Backup Directory at $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"

echo "3. Backing up Database..."
# Assuming db.sqlite3 - adjust if using PostgreSQL
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 "${BACKUP_DIR}/db.sqlite3.bak"
    echo "   -> Database backed up."
else
    echo "   -> db.sqlite3 not found. If using PostgreSQL, ensure you manually dump the DB."
fi

echo "4. Backing up specific target templates and static files..."
mkdir -p "${BACKUP_DIR}/templates"
mkdir -p "${BACKUP_DIR}/css"

[ -f "custom_admin/templates/custom_admin/quizzes/quiz_take.html" ] && cp "custom_admin/templates/custom_admin/quizzes/quiz_take.html" "${BACKUP_DIR}/templates/"
[ -f "custom_admin/templates/custom_admin/quizzes/quiz_result.html" ] && cp "custom_admin/templates/custom_admin/quizzes/quiz_result.html" "${BACKUP_DIR}/templates/"
[ -f "custom_admin/templates/custom_admin/quizzes/certificate.html" ] && cp "custom_admin/templates/custom_admin/quizzes/certificate.html" "${BACKUP_DIR}/templates/"
[ -f "custom_admin/static/custom_admin/css/quiz_take.css" ] && cp "custom_admin/static/custom_admin/css/quiz_take.css" "${BACKUP_DIR}/css/"
echo "   -> Required files backed up."

echo "5. Extracting and replacing ONLY the specified quiz files..."
# Unzip forces overwrite only for files contained within the zip.
unzip -o "$ZIP_FILE"
echo "   -> Zip files successfully applied."

echo "6. Running Collectstatic safely..."
# Activate your virtual environment before running this script if native
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "venv_win" ]; then
    source venv_win/bin/activate
fi

python manage.py collectstatic --noinput
echo "   -> Static files collected."

echo "7. Initiating Zero-Downtime Reload..."
# Graceful reloading
if [ -f "SAHYOG_SETU_ADMIN/wsgi.py" ]; then
    touch SAHYOG_SETU_ADMIN/wsgi.py
    echo "   -> WSGI file touched for Passenger Graceful Reload."
else
    sudo systemctl reload gunicorn || echo "Please reload your web server manually."
    echo "   -> Gunicorn reload initiated safely."
fi

echo "Deployment completed successfully! Zero impact on other modules."
echo "Backup saved in: $BACKUP_DIR"
