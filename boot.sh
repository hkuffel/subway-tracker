#!/bin/sh
flask db init
flask db migrate
flask db upgrade
exec gunicorn --workers 4 --bind 0.0.0.0:5000 subwaytracker:app --log-level info