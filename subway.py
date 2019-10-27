import requests
import pandas as pd
import json

import time
from datetime import datetime
import pytz

from flask_pymongo import PyMongo
from flask import Flask, render_template, request, jsonify

from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict

from config import API_KEY, MANGO_URI

app = Flask(__name__)
app.config["MANGO_URI"] = MANGO_URI

mongo = PyMongo(app)
db = mongo.db

# Creating dictionary to map stop ids to the station name
df = pd.read_csv('stops.csv')[['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'location_type', 'parent_station']]
stop_pairs = zip(df['stop_id'], df['stop_name'])
stops = dict(stop_pairs)

# Dict mapping subway lines to the proper url suffix
lines = {'1': '1', '2': '1', '3': '1', '4': '1', '5': '1', '6': '1', 
        'N': '16', 'Q': '16', 'R': '16', 'W': '16', 
        'B': '21', 'D': '21', 'F': '21', 'M': '21', 
        'A': '26', 'C': '26', 'E': '26',
        'L': '2', 'G': '31', 'J': '36', 'Z': '36', '7': '51'}

# Function to convert unix timestamp into something more readable
def read_time(stamp):
    dt_stamp = datetime.utcfromtimestamp(int(stamp))
    gdt = pytz.timezone('GMT').localize(dt_stamp)
    edt = gdt.astimezone(pytz.timezone('US/Eastern'))
    return edt.strftime('%Y-%m-%d %I:%M:%S %p')

# Function to replace aspects of the MTA feed with their more user-friendly alternatives i.e. '125th St' instead of 'A15'
# This function isn't currently being used in the app, but was in a previous version
def trip_prettify(trips):
    for trip in trips:
        if 'trip_update' in trip.keys():
            t = trip['trip_update']
            if 'stop_time_update' in t.keys():
                ss = t['stop_time_update']
                for s in ss:
                    s['arrival']['time'] = read_time(s['arrival']['time'])
                    s['departure']['time'] = read_time(s['departure']['time'])
                    try:
                        s['stop_id'] = stops[s['stop_id']]
                    except:
                        pass
        elif 'vehicle' in trip.keys():
            v = trip['vehicle']
            if 'timestamp' in v.keys():
                v['timestamp'] = read_time(v['timestamp'])
            if 'stop_id' in v.keys():
                try:
                    v['stop_id'] = stops[v['stop_id']]
                except:
                    pass
    return trips

# Function to pare down the list of trips returned to just ones that haven't started yet
# This function isn't currently being used in the app, but was in a previous version
def see_assigned(feed):
    fs = []
    for f in feed:
        if 'trip_update' in f.keys():
            t = f['trip_update']['trip']['start_date'] + ' ' + f['trip_update']['trip']['start_time']
            if datetime.strptime(t, '%Y%m%d %H:%M:%S') > datetime.now():
                fs.append(f)
        elif 'vehicle' in f.keys():
            t = f['vehicle']['trip']['start_date'] + ' ' + f['vehicle']['trip']['start_time']
            if datetime.strptime(t, '%Y%m%d %H:%M:%S') > datetime.now():
                fs.append(f)
    return fs

# Create connection variable
# conn = 'mongodb+srv://hk:jXmCTbdxj1c8HXhP@cluster0-htedx.mongodb.net/test?retryWrites=true&w=majority'
# client = pymongo.MongoClient(conn)
# db = client.trip_db

''' TODO: Change mongo connection from localhost to something production-friendly'''

# Function for retrieving fresh data from the MTA
def refresh(line_num):
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(f'http://datamine.mta.info/mta_esi.php?key={API_KEY}&feed_id={str(line_num)}')
    feed.ParseFromString(response.content)

    # Taking the transit data from its specific format into a dictionary
    subway_feed = protobuf_to_dict(feed)
    return subway_feed['entity']

def collect(feed):
    db.trips.drop() # Dropping the Mongo collection if one exists
    trips = []
    for t in feed:
        if 'trip_update' in t.keys() and 'stop_time_update' in t['trip_update'].keys():
            trip_id = t['trip_update']['trip']['trip_id']
            route_id = t['trip_update']['trip']['route_id']
            stops = t['trip_update']['stop_time_update']
            try:
                trips.append({
                    'id': trip_id,
                    'line': route_id, 
                    'pred_stops': [{'stop': stop['stop_id'], 'arrival': stop['arrival']['time']} for stop in stops]
                    })
            except KeyError: # Not every trip in the MTA feed will have arrival and departure predictions
                pass
        elif 'vehicle' in t.keys() and 'timestamp' in t['vehicle'].keys():
            trips.append({'id': t['vehicle']['trip']['trip_id'], 'timestamp': t['vehicle']['timestamp']})      
    db.trips.insert_many(trips) #Dumping the collected the data into a MongoDB collection
    return list(db.trips.find())

# Function to find trains heading to a specific stop and sort them by arrival time
def find(tl, stop):
    trains = []
    for t in tl:
        if 'pred_stops' in t.keys():
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

''' TODO: Have the user be able to determine the stop and line through dropdowns'''

@app.route('/')
def index():
    return render_template('index.html', lines=lines, stops=stops)

# @app.route('/display')
# def display_from_dropdown():
#     line = request.form.get()
#     station = stops[stop]
#     trips = collect(refresh(lines[line]))
#     trains = find(trips, stop)
#     return render_template('results.html', trains=trains, station=station, line=line, stop=stop)

@app.route('/display')
def display():
    try:
        line = request.args.get('line', type=str)
        stop = request.args.get('stop', type=str)
        station = stops[stop]
        trips = collect(refresh(lines[line]))
        trains = find(trips, stop)
        return jsonify({'data': render_template('trainfeed.html', trains=trains, stop=stop, station=station)})
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run(debug=True)