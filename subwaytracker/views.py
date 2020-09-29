from subwaytracker import app, db
from subwaytracker.models import delay, visit, station
from subwaytracker.utils import (
    refresh, extract_trip_details, add_delay_instance,
    add_trip_instance, add_visit_instance, read_time
)
from flask import render_template, request, jsonify
import pandas as pd
from datetime import datetime
import json
from bson import ObjectId
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
            arrivalstr = read_time(t[1])
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
    return jsonify(json.dumps(visit.query.all()))


@app.route('/api/predictions')
def predictions():
    return JSONEncoder().encode(list(db.predictions.find()))


@app.route('/api/delays')
def show_reckoning():
    delay_query = db.session.query(
        delay.line_id,
        func.sum(delay.delay_amount).label('delay')
    ).filter(
        extract('month', delay.timestamp) == datetime.today().month
    ).filter(
        extract('year', delay.timestamp) == datetime.today().year
    ).filter(
        extract('day', delay.timestamp) == datetime.today().day
    ).filter(
        delay.line_id.notilike("%x%")
    ).filter(
        delay.line_id.notilike("%s%")
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


@app.route('/api/delays/2')
def show_one_reckoning():
    delay_query = db.session.query(
        delay.station_name,
        func.sum(delay.delay_amount).label('delay')
    ).filter(
        extract('month', delay.timestamp) == datetime.today().month
    ).filter(
        extract('year', delay.timestamp) == datetime.today().year
    ).filter(
        extract('day', delay.timestamp) == datetime.today().day
    ).filter(
        delay.line_id == '2'
    ).group_by(
        delay.station_name
    ).order_by(
        func.sum(delay.delay_amount).desc()
    ).limit(10).all()
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
        s_name = o[0]
        try:
            color = '#EE352E'
        except KeyError:
            color = '#996633'
        delay_amount = o[1]
        returnarr.append({'station': s_name, 'color': color, 'count': delay_amount})
    return jsonify(returnarr)