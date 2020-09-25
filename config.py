import os
basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

API_KEY = '***REMOVED***'

MONGO_URI = "mongodb://localhost:27017/trips_db"

BROKER_URL = "redis://localhost:6379/0"

CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

ENV = 'development'

SQLALCHEMY_DATABASE_URI = os.environ.get('SQLA_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')

SQLALCHEMY_TRACK_MODIFICATIONS = False
