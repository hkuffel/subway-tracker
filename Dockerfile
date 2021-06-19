FROM python:3-slim

RUN adduser --disabled-password subwaytracker

WORKDIR /home/subway-tracker

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn psycopg2-binary

COPY subwaytracker subwaytracker
COPY migrations migrations
COPY config config
COPY celeryconfig.py boot.sh stops.csv stops.json ./
RUN chmod +x boot.sh

RUN chown -R subwaytracker:subwaytracker ./
USER subwaytracker

# expose the app port
EXPOSE 5000

# run the app server in production with gunicorn
CMD exec gunicorn -w 4 -b 0.0.0.0:5000 subwaytracker:app --log-level debug