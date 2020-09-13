import os

***REMOVED***

MANGO_URI = os.environ.get('MANGO_URI')

BROKER_URL = os.environ['REDIS_URL']

CELERY_RESULT_BACKEND = os.environ['REDIS_URL']
