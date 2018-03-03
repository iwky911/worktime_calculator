#!/usr/bin/env python3

import argparse
from datetime import datetime
import math
import ijson.backends.yajl2 as ijson


# Earth radius in km.
EARTH_RADIUS = 6371

# Multiplier that converts the lat/lon distance into km.
DISTANCE_MULTIPLIER = EARTH_RADIUS * math.pi / (180.)

class DistanceHelper:
    def __init__(self, home, work):
        self._lon_coef = math.cos(home[0])
        self._home = home
        self._work = work

    def distance(self, a, b):
        square_sum = ((a[0] - b[0])**2 + ((a[1] - b[1]) * self._lon_coef)**2)
        return math.sqrt(square_sum) * DISTANCE_MULTIPLIER

    def at_work(self, p):
        return self.distance(p, self._work) < 0.5

    def at_home(self, p):
        return self.distance(p, self._home) < 0.5


class DayAtTheOffice:
    def __init__(self, arrived, left):
        self.arrived = arrived
        self.left = left

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('location_file', help='json extraction of your location')
    parser.add_argument('home_coord', help='coordinate of home')
    parser.add_argument('work_coord', help='coordinate of work')

    args = parser.parse_args()

    # Lat, Lon
    home = [float(c)  for c in args.home_coord.split(':')]
    work = [float(c) for c in args.work_coord.split(':')]

    distance_helper = DistanceHelper(home, work)

    print('Distance between work and home: {}'.format(distance_helper.distance(home, work)))

    days = {}
    with open(args.location_file, 'rb') as loc:
        records = ijson.items(loc, 'locations.item')
        n = 0
        for rec in records:
            n += 1
            if n % 10000 == 0:
                print('At {}'.format(n))

            timestamp = int(rec['timestampMs'])
            if timestamp < 1508882400000:
                break

            location = (rec['latitudeE7'] / 10000000., rec['longitudeE7']/10000000)
            timestamp = timestamp / 1000.
            d = datetime.fromtimestamp(timestamp)
            date_tuple = (d.year, d.month, d.day)
            if distance_helper.at_work(location):
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
            if worked_hours > 2:
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

if __name__ == '__main__':
    main()
