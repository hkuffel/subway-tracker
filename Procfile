web: gunicorn subwaytracker:app
worker: celery worker -A subwaytracker.celery -l info --purge
beat: celery beat -A subwaytracker.celery