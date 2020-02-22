# MTA Subway Tracker

This is a Flask app deployed on Heroku with a MongoDB Atlas cloud database that tracks how many total minutes of delay time each train line accrues throughout the day and displays the results using D3. The data comes from the [MTA real-time GTFS feeds](http://datamine.mta.info), and data processing is accomplished with Pandas.

The app has the functionality to update the delay totals autonomously once per minute, but the two pertinent Heroku Dynos (a worker dyno and a beat dyno) are currently switched off so that the app can remain free. A dummy data collection is in place so the bar chart still displays.
