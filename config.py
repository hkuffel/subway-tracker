import os

***REMOVED***

MANGO_URI = os.environ.get('MANGO_URI') or 'mongodb+srv://hunter:C8RKnWrxIgvxoXSD@cluster0-h8le0.mongodb.net/test?retryWrites=true&w=majority'

BROKER_URL=os.environ['REDIS_URL']

CELERY_RESULT_BACKEND=os.environ['REDIS_URL']