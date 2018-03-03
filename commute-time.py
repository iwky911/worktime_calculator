#!/usr/bin/env python3

import argparse
import ijson.backends.yajl2 as ijson
import math
from collections import namedtuple
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('location_file', help='json extraction of your location')
parser.add_argument('home_coord', help='coordinate of home')
parser.add_argument('work_coord', help='coordinate of work')

args = parser.parse_args()

# Earth radius in km.
EARTH_RADIUS = 6371

# Lat, Lon
home = [float(c)  for c in args.home_coord.split(':')]
work = [float(c) for c in args.work_coord.split(':')]

# Coefficients use for distance calculations
coefficients = math.cos(work[0])

multiplier = EARTH_RADIUS * math.pi / (180.)


def distance(a, b):
    try:
        square_sum = ((a[0] - b[0])**2 + ((a[1] - b[1]) * coefficients)**2)
        return math.sqrt(square_sum) * multiplier
    except ValueError:
        print('{} {} {} {}'.format(a, b))

def at_work(p):
    return distance(p, work) < 0.5

def at_home(p):
    return distance(p, home) < 0.5

print('Distance between work and home: {}'.format(distance(home, work)))

days = {}

class DayAtTheOffice:
    def __init__(self, arrived, left):
        self.arrived = arrived
        self.left = left

with open(args.location_file, 'rb') as loc:
    records = ijson.items(loc, 'locations.item')
    n = 0

    for rec in records:
        n+=1
        if n % 10000 == 0:
            print('At {}'.format(n))

        timestamp = int(rec['timestampMs'])
        if timestamp < 1508882400000:
            break

        location = (rec['latitudeE7'] / 10000000., rec['longitudeE7']/10000000)
        timestamp = timestamp / 1000.
        d = datetime.fromtimestamp(timestamp)
        date_tuple = (d.year, d.month, d.day)
        if at_work(location):
            day = days.setdefault(date_tuple, DayAtTheOffice(d.max, d.min))
            if day.arrived.timestamp() > timestamp:
                day.arrived = d
            if day.left.timestamp() < timestamp:
                day.left = d
        
    print('Processed {} records'.format(n))
    print('worked for {} days'.format(len(days)))

    worked_seconds = []
    for k in sorted(days.keys()):
        arrived = days[k].arrived
        left = days[k].left
        t = left - arrived
        worked_hours = int(t.total_seconds() / 3600)
        worked_minutes = int((t.total_seconds() % 3600) / 60)
        if (worked_hours > 2):
            worked_seconds.append(t.total_seconds())
        print('Worked on {} from {} to {} ({}:{})'.format(
            arrived.strftime('%a %b %d'),
            arrived.strftime('%H:%M'),
            left.strftime('%H:%M'),
            worked_hours, worked_minutes))


    average_seconds = sum(worked_seconds) / len(worked_seconds)
    print('On average: {} hours and {} minutes'.format(
        int(average_seconds / 3600),
        int((average_seconds % 3600) / 60)))
