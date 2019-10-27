import os

API_KEY = os.environ.get('API_KEY')

MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb+srv://hk:jXmCTbdxj1c8HXhP@cluster0-htedx.mongodb.net/trips_db?retryWrites=true&w=majority'