import os

***REMOVED***

MANGO_URI = os.environ.get('MANGO_URI') or 'mongodb+srv://hunter:C8RKnWrxIgvxoXSD@cluster0-h8le0.mongodb.net/test?retryWrites=true&w=majority'

BROKER_URL=os.environ['REDIS_URL'] or 'redis://h:p7acd042d80ca6853a3cb9da07756f17580bbcb99b75695114d5ec24be7efc9c2@ec2-35-175-12-112.compute-1.amazonaws.com:13779'

CELERY_RESULT_BACKEND=os.environ['REDIS_URL'] or 'redis://h:p7acd042d80ca6853a3cb9da07756f17580bbcb99b75695114d5ec24be7efc9c2@ec2-35-175-12-112.compute-1.amazonaws.com:13779'