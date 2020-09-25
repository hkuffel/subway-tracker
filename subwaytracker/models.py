from datetime import datetime
from time import time
from flask import current_app
from subwaytracker import db


class station(db.Model):
    id = db.Column(db.String(8), primary_key=True)
    name = db.Column(db.String(40))

    def __repr__(self):
        return f'<Station ID: {self.id}, Station Name: {self.name}>'


class station_line_pair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.String(8), db.ForeignKey('station.id'))
    line_id = db.Column(db.String(2))

    def __repr__(self):
        return f'<Line: {self.line_id}, station: {self.station_id}>'


class trip(db.Model):
    id = db.Column(db.String(30), primary_key=True, unique=True)
    route_id = db.Column(db.String(30))
    line_id = db.Column(db.String(2))
    has_started = db.Column(db.Boolean)
    start_time = db.Column(db.DateTime)
    has_finished = db.Column(db.Boolean)
    has_predictions = db.Column(db.Boolean)

    def __repr__(self):
        return f'<Trip: {self.id}, Line: {self.line_id}>'


class visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.String(30), db.ForeignKey('trip.id'))
    route_id = db.Column(db.String(30))
    station_id = db.Column(db.String(8), db.ForeignKey('station.id'))
    station_name = db.Column(db.String(40), nullable=True)
    line_id = db.Column(db.String(2))
    direction = db.Column(db.String(1))
    arrival_time = db.Column(db.DateTime, nullable=True)
    pred_arrival_time = db.Column(db.DateTime)

    def __repr__(self):
        return '<{} Train arriving at {} at {}>'.format(
            self.line_id, self.station_name, self.arrival_time
        )


class delay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    visit_id = db.Column(db.Integer, db.ForeignKey('visit.id'))
    trip_id = db.Column(db.String(30), db.ForeignKey('trip.id'))
    route_id = db.Column(db.String(30))
    station_id = db.Column(db.String(8), db.ForeignKey('station.id'))
    station_name = db.Column(db.String(40))
    line_id = db.Column(db.String(2))
    delay_amount = db.Column(db.Integer)

    def __repr__(self):
        return '<{} Train arriving at {} {} seconds late>'.format(
            self.line_id, self.station_name, self.delay_amount
        )
