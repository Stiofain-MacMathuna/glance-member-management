#!/bin/sh

# 1. Apply Database Migrations
echo "Applying migrations..."
python manage.py migrate

# 2. Auto-Create Superuser (Only if it doesn't exist)
echo "Checking superuser..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('cern', 'admin@cern.ch', 'cms123') if not User.objects.filter(username='cern').exists() else print('Superuser already exists')" | python manage.py shell

# 3. Auto-Seed Data (Only if the database is empty)
echo "Checking data seed..."
count=$(echo "from api.models import Member; print(Member.objects.count())" | python manage.py shell)

if [ "$count" = "0" ]; then
    echo "Database empty. Seeding 5,000 members..."
    python manage.py seed_glance
else
    echo "Database already seeded ($count members found). Skipping."
fi

# 4. Start the Server
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application