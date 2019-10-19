import requests
import pandas as pd
import json

import time
from datetime import datetime
import pytz

import pymongo
from flask import Flask, render_template, request

from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict

from key import key

app = Flask(__name__)

# Creating dictionary to map stop ids to the station name
df = pd.read_csv('stops.csv')[['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'location_type', 'parent_station']]
stops = {}
for i in range(len(df)):
    stops[df.at[i, 'stop_id']] = df.at[i, 'stop_name']

# Dict mapping subway lines to the proper url suffix
lines = {'1/2/3': '1', '4/5/6': '1', 'N/Q/R/W': '16', 'B/D/F/M': '21', 
        'A/C/E': '26', 'L': '2', 'G': '31', 'J/Z': '36', '7': '51'}

# Function to convert unix timestamp into something more readable
def read_time(ts):
    ts = int(ts)
    gmt = pytz.timezone('GMT')
    dt = datetime.utcfromtimestamp(ts)
    gdt = gmt.localize(dt)
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
conn = 'mongodb://localhost:27017'
client = pymongo.MongoClient(conn)
db = client.trip_db

''' TODO: Change mongo connection from localhost to something production-friendly'''

# Function for retrieving fresh data from the MTA
def refresh(line_num):
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(f'http://datamine.mta.info/mta_esi.php?key={key}&feed_id={str(line_num)}')
    feed.ParseFromString(response.content)

    # Taking the transit data from its specific format into a dictionary
    subway_feed = protobuf_to_dict(feed)

    #Dumping the collected the data into a MongoDB collection
    db.trips.drop()
    unstarted = []
    for t in subway_feed['entity']:
        if 'trip_update' in t.keys() and 'stop_time_update' in t['trip_update'].keys():
            unstarted.append({'id': t['trip_update']['trip']['trip_id'], 
            'pred_stops': [{'stop': stop['stop_id'], 'arrival': stop['arrival']['time']} for stop in t['trip_update']['stop_time_update']]})
        elif 'vehicle' in t.keys() and 'timestamp' in t['vehicle'].keys():
            unstarted.append({'id': t['vehicle']['trip']['trip_id'], 'timestamp': t['vehicle']['timestamp']})
    db.trips.insert_many(unstarted)

    return list(db.trips.find())

# Function to find trains heading to a specific stop and sort them by arrival time
def find_trains(tl, stop):
    trains = []
    for t in tl:
        if 'pred_stops' in t.keys():
            for s in t['pred_stops']:
                if s['stop'] == stop and s['arrival'] > time.time():
                    s['arrival'] = read_time(s['arrival'])
                    try:
                        s['departure'] = read_time(s['departure'])
                    except:
                        pass
                    s['stop'] = stops[s['stop']]
                    trains.append(s)
    trains = sorted(trains, key=lambda i: i['arrival'])
    return trains

''' TODO: Right now the line and the station are hard-coded into the app, but we eventually want the user to choose these.'''

@app.route('/')
def index():
    line_num = 26
    stop = 'A15S'
    station = stops[stop]
    trips = find_trains(refresh(line_num), stop)
    return render_template('index.html', trips=trips, station=station)

if __name__ == "__main__":
    app.run(debug=True)