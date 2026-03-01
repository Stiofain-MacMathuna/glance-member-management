#!/bin/sh

# 1. Wait for Postgres to be ready using Python's built-in socket library
echo "Waiting for postgres..."
python << END
import socket
import time
import os

db_host = os.environ.get('DB_HOST', 'db')
db_port = int(os.environ.get('DB_PORT', 5432))

while True:
    try:
        with socket.create_connection((db_host, db_port), timeout=1):
            break
    except OSError:
        print("PostgreSQL not ready, waiting...")
        time.sleep(1)
END
echo "PostgreSQL started"

# 2. Apply Database Migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# 3. Create Superuser (Admin) if it doesn't exist
echo "Checking superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@cern.ch', 'cern-pass')
    print("Superuser created.")
else:
    print("Superuser already exists.")
END

# 4. Seed Data if the Member table is empty
echo "Checking data seed..."
# We use 'tail -1' to grab the last line of output (the count)
MEMBER_COUNT=$(python manage.py shell -c "from api.models import Member; print(Member.objects.count())" | tail -1)

if [ "$MEMBER_COUNT" = "0" ]; then
    echo "Database empty. Seeding 5,000 members..."
    python manage.py seed_glance
else
    echo "Database already contains $MEMBER_COUNT members. Skipping seed."
fi

# 5. Start the Server
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 config.wsgi:application