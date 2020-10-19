from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, send
from flask_migrate import Migrate
from sqlalchemy import MetaData
from celery import Celery
import celeryconfig

from config import BROKER_URL

app = Flask(__name__)
app.config.from_object('config')
# app.config.from_pyfile('instance/config.py')
celeryio = SocketIO(app, message_queue='redis://')

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(app, metadata=metadata)
migrate = Migrate(app, db, render_as_batch=True)


def make_celery(app):
    celery = Celery(app.import_name, broker=BROKER_URL)
    celery.conf.update(app.config)
    celery.config_from_object(celeryconfig)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)

from subwaytracker import tasks, views, models


if __name__ == "__main__":
    celeryio.run(app, debug=True)
