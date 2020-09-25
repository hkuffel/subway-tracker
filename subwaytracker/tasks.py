from subwaytracker import celery, db, models
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


def extract_trip_details(trip_instance):
    if 'trip_update' in trip_instance.keys():
        if 'start_time' in trip_instance['trip_update']['trip'].keys():
            return (
                trip_instance['trip_update']['trip']['trip_id'],
                trip_instance['trip_update']['trip']['start_date'],
                trip_instance['trip_update']['trip']['start_time']
            )
        else:
            return (
                trip_instance['trip_update']['trip']['trip_id'],
                trip_instance['trip_update']['trip']['start_date'],
            )
    elif 'vehicle' in trip_instance.keys():
        if 'start_time' in trip_instance['vehicle']['trip'].keys():
            return (
                trip_instance['vehicle']['trip']['trip_id'],
                trip_instance['vehicle']['trip']['start_date'],
                trip_instance['vehicle']['trip']['start_time']
            )
        else:
            return (
                trip_instance['vehicle']['trip']['trip_id'],
                trip_instance['vehicle']['trip']['start_date'],
            )


def refresh(line_num):
    """Retrieves fresh data from the MTA."""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(
        f'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs{str(line_num)}',
        headers={'x-api-key': API_KEY}
    )
    feed.ParseFromString(response.content)

    # Taking the transit data from its specific format into a dictionary
    subway_feed = protobuf_to_dict(feed)
    subway_feed = [r for r in subway_feed['entity'] if 'alert' not in r.keys()]
    consol_feed = list(map(
        lambda dict_tuple: dict(ChainMap(*dict_tuple[1])),
        groupby(
            sorted(subway_feed, key=lambda t: extract_trip_details(t)),
            key=lambda t: extract_trip_details(t)
        )
    ))
    return consol_feed


# Function to comb through trip parts and combine those that share ids
def combine(trips):
    for i, trip in enumerate(trips):
        for othertrip in trips[i:]:
            if othertrip['id'] == trip['id']:
                othertrip.update(trip)
    trips = [trip for trip in trips if 'pred_stops' in trip.keys()]
    return trips


def add_visit_instance(trip_id, route_id, line_id, visit_dict):
    station_id = re.sub('[NS]$', '', visit_dict['stop_id'])
    direction = re.search('(N|S)$', visit_dict['stop_id']).group(1)
    try:
        station_name = models.station.query.get(station_id).name
    except AttributeError:
        station_name = None
    visit_instance = models.visit(
        trip_id=trip_id,
        route_id=route_id,
        station_id=station_id,
        station_name=station_name,
        line_id=line_id,
        direction=direction,
        arrival_time=None,
        pred_arrival_time=datetime.utcfromtimestamp(int(visit_dict['arrival']['time']))
    )
    db.session.add(visit_instance)


def add_delay_instance(visit_instance):
    delay_instance = models.delay(
        trip_id=visit_instance.trip_id,
        visit_id=visit_instance.id,
        route_id=visit_instance.route_id,
        line_id=visit_instance.line_id,
        station_id=visit_instance.station_id,
        station_name=visit_instance.station_name,
        delay_amount=(
            visit_instance.arrival_time - visit_instance.pred_arrival_time
        ).total_seconds()
    )
    db.session.add(delay_instance)


def add_trip_instance(t):
    if ('trip_update' in t.keys()
            and 'stop_time_update' in t['trip_update'].keys()
            and 'vehicle' in t.keys()
            and 'timestamp' in t['vehicle'].keys()):
        # Assigning necessary information to variables
        route_id = t['trip_update']['trip']['trip_id']
        if 'start_time' in t['trip_update']['trip'].keys():
            date_str = datetime.strptime(
                t['trip_update']['trip']['start_date']
                + ' ' + t['trip_update']['trip']['start_time'],
                '%Y%m%d %H:%M:%S'
            )
        else:
            date_str = datetime.strptime(
                t['trip_update']['trip']['start_date'], '%Y%m%d'
            )
        if models.trip.query.filter(models.trip.route_id == route_id).filter(
            models.trip.start_time == date_str
        ).count() == 0:
            trip_id = ''.join(random.choice(
                string.ascii_uppercase
                + string.ascii_lowercase
                + string.digits
            ) for _ in range(24))
            line_id = t['trip_update']['trip']['route_id']
            try:
                if t['vehicle']['current_stop_sequence'] > 1:
                    has_started = True
                else:
                    has_started = False
            except KeyError:
                has_started = True
            trips_instance = models.trip(
                id=trip_id, route_id=route_id,
                line_id=line_id, has_started=has_started,
                start_time=date_str, has_finished=False,
                has_predictions=True
            )
            db.session.add(trips_instance)
            for visit_dict in t['trip_update']['stop_time_update']:
                if 'arrival' in visit_dict.keys():
                    add_visit_instance(trip_id, route_id, line_id, visit_dict)
        elif models.trip.query.filter(models.trip.route_id == route_id).filter(
            models.trip.start_time == date_str
        ).count() == 1:
            trip_id = models.trip.query.filter(
                models.trip.route_id == route_id
            ).filter(
                models.trip.start_time == date_str
            ).all()[0].id
            station = re.sub('[NS]$', '', t['vehicle']['stop_id'])
            timestamp = datetime.utcfromtimestamp(int(t['vehicle']['timestamp']))
            try:
                visit_to_update = models.visit.query.filter(
                    models.visit.trip_id == trip_id
                ).filter(
                    models.visit.station_id == station
                ).first()
                if visit_to_update.arrival_time is not None:
                    visit_to_update.arrival_time = timestamp
                    add_delay_instance(visit_to_update)
                else:
                    visit_to_update.arrival_time = timestamp
                    delay_to_update = models.delay.query.filter(
                        models.delay.visit_id == visit_to_update.id
                    ).first()
                    delay_to_update.delay_amount = (
                        visit_to_update.arrival_time - visit_to_update.pred_arrival_time
                    ).total_seconds()
            except AttributeError:
                pass
        # TODO Close off finished trips at this point


def collect(feed):
    for t in feed:
        add_trip_instance(t)
    db.session.commit()


# def collect(feed):
#     trips = []
#     for t in feed:
#         if 'trip_update' in t.keys() and 'stop_time_update' in t['trip_update'].keys():
#             # Assigning necessary information to variables
#             trip_id = t['trip_update']['trip']['trip_id']
#             route_id = t['trip_update']['trip']['route_id']
#             stops = t['trip_update']['stop_time_update']
#             try:
#                 trips.append({
#                     'id': trip_id,
#                     'line': route_id,
#                     'pred_stops': [
#                         {
#                             'stop': stop['stop_id'],
#                             'arrival': stop['arrival']['time']
#                         } for stop in stops
#                     ]
#                 })
#             except KeyError:  # Not every trip in the MTA feed will have predictions
#                 pass
#         elif 'vehicle' in t.keys() and 'timestamp' in t['vehicle'].keys():
#             tri = {
#                 'id': t['vehicle']['trip']['trip_id'],
#                 'timestamp': t['vehicle']['timestamp']
#             }
#             try:
#                 tri['cs'] = t['vehicle']['stop_id']
#             except Exception:
#                 pass
#             trips.append(tri)
#     # Combine the two elements of each trip
#     # trips = combine(trips)
#     # Dumping the collected the data into a MongoDB collection
#     # db.trips.insert_many(trips)
#     return trips  # list(db.trips.find())


def record_predictions(trips):
    """Find trips that haven't yet started and record the first predictions in the db."""
    for t in trips:
        if db.predictions.find({'id': t['id']}).count() > 0:
            try:
                if len(t['pred_stops']) < 2:
                    db.predictions.delete_one({'id': t['id']})
            except Exception:
                pass
        else:
            db.predictions.insert_one(t)
    return list(db.predictions.find())


# would run every day at midnight when app is at full capacity
def reset_delays():
    """Reset the delay database."""
    db.trips.drop()
    db.predictions.drop()
    db.delays.drop()
    line_list = [
        '1', '2', '3', '4', '5', '6', '7', 'A', 'B', 'C',
        'D', 'E', 'F', 'G', 'H', 'J', 'L', 'M', 'N', 'Q', 'R', 'Z'
    ]

    colors = [
        '#EE352E', '#EE352E', '#EE352E', '#00933C', '#00933C',
        '#00933C', '#B933AD', '#2850AD', '#FF6319', '#2850AD', '#FF6319',
        '#2850AD', '#FF6319', '#6CBE45', '#2850AD', '#996633', '#A7A9AC',
        '#FF6319', '#FCCC0A', '#FCCC0A', '#FCCC0A', '#996633'
    ]

    delay_cache = [
        {'line': line_list[i], 'count': 0, 'color': colors[i]} for i in range(len(colors))
    ]
    db.delays.insert_many(delay_cache)


def reckoning(trips):
    """Match trips with their initial predictions and add new delays to the db."""
    trips = [trip for trip in trips if 'timestamp' in trip.keys() and 'cs' in trip.keys()]
    for trip in trips:
        preds = list(db.predictions.find({'id': trip['id']}).limit(1))
        try:
            preds = preds[0]['pred_stops']
        except Exception:
            continue
        for pred in preds:
            if (pred['stop'] == trip['cs']
                    or pred['stop'][:-1] == trip['cs'] or pred['stop'] == trip['cs'][:-1]):
                db.delays.update_one(
                    {'line': str(trip['id'][7])},
                    {'$inc': {
                        'count': int((trip['timestamp'] - pred['arrival']))
                    }}
                )
    return list(db.delays.find())


def read_time(stamp):
    """Convert unix timestamp into something more readable"""
    dt_stamp = datetime.utcfromtimestamp(int(stamp))
    gdt = pytz.timezone('GMT').localize(dt_stamp)
    edt = gdt.astimezone(pytz.timezone('US/Eastern'))
    return edt.strftime('%Y-%m-%d %I:%M:%S %p')


def find(tl, stop, line):
    """Compile trains headed to a stop and sort them by arrival time."""
    trains = []
    for t in tl:
        if 'pred_stops' in t.keys() and t['line'] == line:
            for s in t['pred_stops']:
                if s['stop'] == stop and s['arrival'] > time.time():
                    # Converting the timestamps and stop codes into readable versions
                    s['arrival'] = read_time(s['arrival'])
                    s['stop'] = stops[s['stop']]
                    s['id'] = t['id']
                    s['line'] = t['line']
                    trains.append(s)
    trains = sorted(trains, key=lambda i: i['arrival'])
    return trains


@celery.task
def freshen():
    #  db.trips.drop()   Dropping the Mongo collection if one exists
    codes = ['', '-ace', '-bdfm', '-g', '-l', '-7', '-jz', '-nqrw']
    for code in codes:
        try:
            collect(refresh(code))
        except Exception:
            pass


@celery.task
def rec_pred():
    codes = ['', '-ace', '-bdfm', '-g', '-l', '-7', '-jz', '-nqrw']
    feed = []
    for code in codes:
        try:
            feed += record_predictions(collect(refresh(code)))
        except Exception:
            pass
    return JSONEncoder().encode(list(db.predictions.find()))


@celery.task
def reckon():
    reckoning(db.trips.find())
    return JSONEncoder().encode(
        sorted(
            list(db.delays.find()), key=lambda k: k['line']
        )
    )


@celery.task
def clean():
    reset_delays()
    return JSONEncoder().encode(list(db.delays.find()))
