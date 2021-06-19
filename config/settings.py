import os


class Config(object):
    DEBUG = False
    TESTING = False
    FLASK_APP = 'subwaytracker'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@postgresql:8026/subway-tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_KEY = os.environ.get('API_KEY')
    SECRET_KEY = os.environ.get('SECRET_KEY', "jfjfjf")
    DB_USER = 'postgres'
    DB_PASS = 'postgres'
    DB_PORT = '8026'
    REDIS_PATH = 'redis://redis:6379'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@postgresql/postgres'
    POSTGRES_HOST_AUTH_METHOD = 'trust'
    BROKER_URL = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND = "redis://redis:6379/0"
    FLASK_ENV = 'production'
    STOPS_CSV_PATH = 'stops.csv'
    REDIS_PATH = 'redis://redis:6379'


class DevConfig(Config):
    BROKER_URL = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND = "redis://redis:6379/0"
    FLASK_ENV = 'development'
    SQLALCHEMY_ECHO = False


class TestConfig(Config):
    TESTING = True
