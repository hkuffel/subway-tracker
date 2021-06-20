from subwaytracker import app, db
from subwaytracker.models import delay, visit, station, trip
from subwaytracker.utils import (
    refresh, extract_trip_details, add_delay_instance,
    add_trip_instance, add_visit_instance, read_time
)
from flask import render_template, request, jsonify
import csv
from datetime import datetime
import json
from bson import ObjectId
from sqlalchemy import func, extract

# Creating dictionary to map stop ids to the station name
with open('stops.csv') as stopsfile:
    reader = csv.DictReader(stopsfile)
    stops = {row['stop_id']: row['stop_name'] for row in reader}

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
        i = 0
        station_name = db.session.query(station.name).filter(station.id == stop).first()[0]
        print(f'station name: {station_name}')
        i = 1
        trains = db.session.query(visit.line_id, visit.pred_arrival_time).filter(
            visit.line_id == line
        ).filter(
            visit.station_id == stop
        ).filter(
            visit.direction == d
        ).filter(
            visit.arrival_time == None
        ).all()[:10]
        stop = stop + d
        train_arr = []
        i = 2
        for t in trains:
            arrivalstr = read_time(t[1])
            train_arr.append({'line': t[0], 'arrival': arrivalstr})
            i = i + 1
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
        return f'There was an error {i}: {str(e)}.'


@app.route('/api/feed')
def feed():
    feed_query = db.session.query(
        trip.line_id,
        trip.route_id,
        trip.start_time
    ).order_by(
        trip.start_time.desc()
    ).limit(100)
    return jsonify([{'line': v[0], 'route': v[1], 'time': v[2]} for v in feed_query])


@app.route('/api/predictions')
def predictions():
    return JSONEncoder().encode(list(db.predictions.find()))


@app.route('/api/delays')
def show_reckoning():
    delay_query = db.session.query(
        delay.line_id,
        func.sum(delay.delay_amount).label('delay')
    ).group_by(
        delay.line_id
    ).order_by(
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
