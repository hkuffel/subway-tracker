import os
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

API_KEY = os.environ.get('APIKEY')

BROKER_URL = "redis://localhost:6379/0"

CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

SQLALCHEMY_DATABASE_URI = os.environ.get('SQLA_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')

SQLALCHEMY_TRACK_MODIFICATIONS = False
