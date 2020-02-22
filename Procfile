web: gunicorn subway:app
worker: celery worker -A subway.celery -l info --purge
beat: celery beat -A subway.celery