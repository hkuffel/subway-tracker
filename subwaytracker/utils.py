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


def extract_trip_details(trip_instance):
    """Helper function to parse json object with data regarding a subway trip

    Args:
        trip_instance (json): a dictionary with data regarding a subway trip.
        An item from the array returned by refresh.

    Returns:
        tuple: a tuple containing the trip ID and the date (str) the trip started.
    """
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


def read_time(stamp):
    """Convert unix timestamp into something more readable.

    Args:
        stamp (datetime object): datetime object to be converted.

    Returns:
        str: string of eastern time datetime string.
    """
    gdt = pytz.timezone('GMT').localize(stamp)
    edt = gdt.astimezone(pytz.timezone('US/Eastern'))
    return datetime.strftime(edt, '%I:%M %p')


def refresh(line_code):
    """Retrieves fresh data from the MTA.

    Args:
        line_code (str): code for the line or lines whose trips will be retrieved.

    Returns:
        list: list of dicts with train data.
    """    """"""
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(
        f'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs{str(line_code)}',
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


def add_visit_instance(db, models, trip_id, route_id, line_id, visit_dict):
    """Gathers necessary data and adds an instance of the Visit model to the database.

    Args:
        db (obj): instance of the sqlalchemy database
        models (obj): collection of sqlalchemy database models
        trip_id (str): id of the subway trip of which the visit is a part
        route_id (str): id of the route the subway trip is traveling, e.g. 116000_3..S01R'
        line_id (str): the subway line of the trip, e.g. A
        visit_dict (dict): dictionary with data concerning the specific visit
    """
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


def add_delay_instance(db, models, visit_instance):
    """adds an instance of the Delay model to the database.

    Args:
        db (obj): instance of the sqlalchemy database
        models (obj): collection of sqlalchemy models
        visit_instance (obj): instance of the Visit sqlalchemy model
            which pertains to this delay
    """
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


def add_trip_instance(db, models, t):
    """altogether-too-long function that parses a trip dictionary, adds the trip and its
        visits to the database, or updates the visits and adds delays if the trip is
        already in the database.

    Args:
        db (obj): SQLAlchemy database
        models (obj): Collection of SQLAlchemy models
        t (dict): dictionary with trip data. Item in the array returned by refresh.
    """
    if ('trip_update' in t.keys()
            and 'stop_time_update' in t['trip_update'].keys()
            and 'vehicle' in t.keys()
            and 'timestamp' in t['vehicle'].keys()):  # Ensuring that no data is missing
        route_id = t['trip_update']['trip']['trip_id']
        if 'start_time' in t['trip_update']['trip'].keys():
            date_str = datetime.strptime(
                t['trip_update']['trip']['start_date']
                + ' ' + t['trip_update']['trip']['start_time'],
                '%Y%m%d %H:%M:%S'  # Some lines have date and times
            )
        else:
            date_str = datetime.strptime(
                t['trip_update']['trip']['start_date'], '%Y%m%d'  # Others just have dates
            )
        if models.trip.query.filter(models.trip.route_id == route_id).filter(
            models.trip.start_time == date_str
        ).count() == 0:  # If this is a never-before-seen trip
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
                    add_visit_instance(db, models, trip_id, route_id, line_id, visit_dict)
        elif models.trip.query.filter(models.trip.route_id == route_id).filter(
            models.trip.start_time == date_str
        ).count() == 1:  # If this specific trip is already in the database
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
                    add_delay_instance(db, models, visit_to_update)
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
