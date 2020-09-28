from subwaytracker import celery, db, models, celeryio
from subwaytracker.utils import (
    refresh, extract_trip_details, add_delay_instance,
    add_trip_instance, add_visit_instance, read_time
)
import json
from bson import ObjectId


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


def collect(feed):
    for t in feed:
        add_trip_instance(db, models, t)
    db.session.commit()


@celery.task
def freshen():
    codes = ['', '-ace', '-bdfm', '-g', '-l', '-7', '-jz', '-nqrw']
    for code in codes:
        try:
            collect(refresh(code))
        except Exception:
            pass
    celeryio.emit('my event', {'data': 'we heard you!'})
