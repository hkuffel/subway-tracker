import requests
import pandas as pd
import json

import time
from datetime import datetime
import pytz

import pymongo
from flask import Flask, render_template

from google.transit import gtfs_realtime_pb2
from protobuf_to_dict import protobuf_to_dict

from key import key

app = Flask(__name__)

df = pd.read_csv('stops.csv')[['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'location_type', 'parent_station']]
df.head()
stops = {}
for i in range(len(df)):
    stops[df.at[i, 'stop_id']] = df.at[i, 'stop_name']

def read_time(ts):
    ts = int(ts)
    gmt = pytz.timezone('GMT')
    dt = datetime.utcfromtimestamp(ts)
    gdt = gmt.localize(dt)
    edt = gdt.astimezone(pytz.timezone('US/Eastern'))
    return edt.strftime('%Y-%m-%d %I:%M:%S %p')

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

def see_assigned(pfeed):
    ps = []
    for p in pfeed:
        if 'trip_update' in p.keys():
            t = p['trip_update']['trip']['start_date'] + ' ' + p['trip_update']['trip']['start_time']
            if datetime.strptime(t, '%Y%m%d %H:%M:%S') > datetime.now():
                ps.append(p)
        elif 'vehicle' in p.keys():
            t = p['vehicle']['trip']['start_date'] + ' ' + p['vehicle']['trip']['start_time']
            if datetime.strptime(t, '%Y%m%d %H:%M:%S') > datetime.now():
                ps.append(p)
    return ps

# Create connection variable
conn = 'mongodb://localhost:27017'
client = pymongo.MongoClient(conn)
db = client.trip_db

# Function for retrieving fresh data from the MTA
def refresh(line_num):
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(f'http://datamine.mta.info/mta_esi.php?key={key}&feed_id={str(line_num)}')
    feed.ParseFromString(response.content)

    subway_feed = protobuf_to_dict(feed)
    pfeed = trip_prettify(subway_feed['entity'])

    db.trips.drop()
    unstarted = []
    for t in see_assigned(pfeed):
        if 'trip_update' in t.keys() and 'stop_time_update' in t['trip_update'].keys():
            unstarted.append({'id': t['trip_update']['trip']['trip_id'], 
            'pred_stops': [{'stop': stop['stop_id'], 'arrival': stop['arrival']['time'], 
                            'departure': stop['departure']['time']} for stop in t['trip_update']['stop_time_update']]})
        elif 'vehicle' in t.keys() and 'timestamp' in t['vehicle'].keys():
            unstarted.append({'id': t['vehicle']['trip']['trip_id'], 'timestamp': t['vehicle']['timestamp']})
    db.trips.insert_many(unstarted)
    return list(db.trips.find())

@app.route('/')
def index():
    line_num = 26
    trips = refresh(line_num)
    return render_template('index.html', trips=trips)

if __name__ == "__main__":
    app.run(debug=True)