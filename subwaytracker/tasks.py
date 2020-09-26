from subwaytracker import celery, db, models
from subwaytracker.utils import (
    refresh, extract_trip_details, add_delay_instance,
    add_trip_instance, add_visit_instance, read_time
)
import pandas as pd
import pytz
import time
from datetime import datetime
import requests
import json
from bson import ObjectId
from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict
from config import API_KEY
import random
import string
from itertools import groupby
from collections import ChainMap
from _operator import itemgetter
import re

# Creating dictionary to map stop ids to the station name
df = pd.read_csv('stops.csv')[
    [
        'stop_id', 'stop_name', 'stop_lat', 'stop_lon',
        'location_type', 'parent_station'
    ]
]
stop_pairs = zip(df['stop_id'], df['stop_name'])
stops = dict(stop_pairs)

# Dict mapping subway lines to the proper url suffix
lines = {
    '1': '', '2': '', '3': '', '4': '', '5': '', '6': '',
    '7': '-7', 'A': '-ace', 'C': '-ace', 'E': '-ace',
    'B': '-bdfm', 'D': '-bdfm', 'F': '-bdfm', 'M': '-bdfm',
    'G': '-g', 'N': '-nqrw', 'Q': '-nqrw', 'R': '-nqrw',
    'W': '-nqrw', 'L': '-l', 'J': '-jz', 'Z': '-jz'
}


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
    #  db.trips.drop()   Dropping the Mongo collection if one exists
    codes = ['', '-ace', '-bdfm', '-g', '-l', '-7', '-jz', '-nqrw']
    for code in codes:
        try:
            collect(refresh(code))
        except Exception:
            pass
