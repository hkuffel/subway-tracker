from subwaytracker import app, db
from subwaytracker.models import delay, visit, station
from flask import render_template, request, jsonify
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
from sqlalchemy import func, extract

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
    return subway_feed['entity']


# Function to comb through trip parts and combine those that share ids
def combine(trips):
    for i, trip in enumerate(trips):
        for trip in trips[i:]:
            if trips[i]['id'] == trip['id']:
                trips[i].update(trip)
    trips = [trip for trip in trips if 'pred_stops' in trip.keys()]
    return trips


def collect(feed):
    trips = []
    for t in feed:
        if 'trip_update' in t.keys() and 'stop_time_update' in t['trip_update'].keys():
            # Assigning necessary information to variables
            trip_id = t['trip_update']['trip']['trip_id']
            route_id = t['trip_update']['trip']['route_id']
            stops = t['trip_update']['stop_time_update']
            try:
                trips.append({
                    'id': trip_id,
                    'line': route_id,
                    'pred_stops': [
                        {
                            'stop': stop['stop_id'],
                            'arrival': stop['arrival']['time']
                        } for stop in stops
                    ]
                })
            except KeyError:  # Not every trip in the MTA feed will have predictions
                pass
        elif 'vehicle' in t.keys() and 'timestamp' in t['vehicle'].keys():
            tri = {
                'id': t['vehicle']['trip']['trip_id'],
                'timestamp': t['vehicle']['timestamp']
            }
            try:
                tri['cs'] = t['vehicle']['stop_id']
            except Exception:
                pass
            trips.append(tri)
    # Combine the two elements of each trip
    trips = combine(trips)
    # Dumping the collected the data into a MongoDB collection
    db.trips.insert_many(trips)
    return list(db.trips.find())


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


@app.route('/')
def index():
    return render_template('index.html', lines=lines, stops=stops)


@app.route('/display')
def display():
    try:
        line = request.args.get('line', type=str)
        print(line)
        stop = request.args.get('stop', type=str)
        print(stop)
        d = request.args.get('direction', type=str)
        print(d)
        station_name = db.session.query(station.name).filter(station.id == stop).first()[0]
        trains = db.session.query(visit.line_id, visit.pred_arrival_time).filter(
            visit.line_id == line
        ).filter(
            visit.station_id == stop
        ).filter(
            visit.direction == d
        ).filter(
            visit.arrival_time == None
        ).filter(
            extract('month', visit.pred_arrival_time) == datetime.today().month
        ).filter(
            extract('year', visit.pred_arrival_time) == datetime.today().year
        ).filter(
            extract('day', visit.pred_arrival_time) == datetime.today().day
        ).filter(
            extract('hour', visit.pred_arrival_time) >= datetime.today().hour
        ).filter(
            extract('minute', visit.pred_arrival_time) >= datetime.today().minute
        ).all()[:10]
        stop = stop + d
        train_arr = []
        for t in trains:
            arrivalstr = t[1].strftime('%I:%M %p')
            train_arr.append({'line': t[0], 'arrival': arrivalstr})
        tn = len(trains)
        return jsonify(
            {
                'data': render_template(
                    'trainfeed.html',
                    trains=train_arr, stop=stop,
                    station=station_name, tn=tn
                )
            }
        )
    except Exception as e:
        return f'There was an error: {str(e)}.'


@app.route('/api/feed')
def feed():
    # codes = ['', '-ace', '-bdfm', '-g', '-l', '-7', '-jz', '-nqrw']
    # feed = []
    # for code in codes:
    #     try:
    #         feed += collect(refresh(code))
    #     except Exception:
    #         pass
    return JSONEncoder().encode(list(db.trips.find()))


@app.route('/api/predictions')
def predictions():
    # codes = ['', '-ace', '-bdfm', '-g', '-l', '-7', '-jz', '-nqrw']
    # feed = []
    # for code in codes:
    #     try:
    #         feed += record_predictions(collect(refresh(code)))
    #     except Exception:
    #         pass
    return JSONEncoder().encode(list(db.predictions.find()))


@app.route('/api/delays')
def show_reckoning():
    delay_query = db.session.query(
        delay.line_id,
        func.sum(delay.delay_amount).label('delay')
    ).group_by(
        delay.line_id
    ).all()
    line_list = [
        '1', '2', '3', '4', '5', '5X', '6', '7', 'A', 'B', 'C',
        'D', 'E', 'F', 'G', 'H', 'J', 'L', 'M', 'N', 'Q', 'R', 'Z'
    ]
    colors = [
        '#EE352E', '#EE352E', '#EE352E', '#00933C', '#00933C', '#00933C',
        '#00933C', '#B933AD', '#2850AD', '#FF6319', '#2850AD', '#FF6319',
        '#2850AD', '#FF6319', '#6CBE45', '#2850AD', '#996633', '#A7A9AC',
        '#FF6319', '#FCCC0A', '#FCCC0A', '#FCCC0A', '#996633'
    ]
    colordict = {l: colors[i] for i, l in enumerate(line_list)}
    returnarr = []
    for o in delay_query:
        line = o[0]
        try:
            color = colordict[line[0]]
        except KeyError:
            color = '#996633'
        delay_amount = o[1]
        returnarr.append({'line': line, 'color': color, 'count': delay_amount})
    return jsonify(returnarr)
    # JSONEncoder().encode(
    #     sorted(
    #         list(db.delays.find()), key=lambda k: k['line']
    #     )
    # )


@app.route('/api/delays/reset')
def reset():
    reset_delays()
    return JSONEncoder().encode(
        sorted(
            list(db.delays.find()), key=lambda k: k['line']
        )
    )
