import pandas as pd
import pytz
from datetime import datetime

# Creating dictionary to map stop ids to the station name
df = pd.read_csv('stops.csv')[
    [
        'stop_id', 'stop_name', 'stop_lat', 'stop_lon',
        'location_type', 'parent_station'
        ]
    ]
stop_pairs = zip(df['stop_id'], df['stop_name'])
stops = dict(stop_pairs)


# This function isn't currently being used in the app,
# but it was in a previous version
def trip_prettify(trips):
    """Replace aspects of the MTA feed with more user-friendly alternatives."""
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
                    except Exception:
                        pass
        elif 'vehicle' in trip.keys():
            v = trip['vehicle']
            if 'timestamp' in v.keys():
                v['timestamp'] = read_time(v['timestamp'])
            if 'stop_id' in v.keys():
                try:
                    v['stop_id'] = stops[v['stop_id']]
                except Exception:
                    pass
    return trips


# This function isn't currently being used in the app,
# but it was in a previous version
def see_assigned(feed):
    """Pares down the list of trips returned to just those that haven't yet started."""
    fs = []
    for f in feed:
        if 'trip_update' in f.keys():
            t = (f['trip_update']['trip']['start_date']
                 + ' ' + f['trip_update']['trip']['start_time'])
            if datetime.strptime(t, '%Y%m%d %H:%M:%S') > datetime.now():
                fs.append(f)
        elif 'vehicle' in f.keys():
            t = f['vehicle']['trip']['start_date'] + ' ' + f['vehicle']['trip']['start_time']
            if datetime.strptime(t, '%Y%m%d %H:%M:%S') > datetime.now():
                fs.append(f)
    return fs


def read_time(stamp):
    """Convert unix timestamp into something more readable"""
    dt_stamp = datetime.utcfromtimestamp(int(stamp))
    gdt = pytz.timezone('GMT').localize(dt_stamp)
    edt = gdt.astimezone(pytz.timezone('US/Eastern'))
    return edt.strftime('%Y-%m-%d %I:%M:%S %p')