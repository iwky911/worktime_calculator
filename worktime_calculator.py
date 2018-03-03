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
    def __init__(self, home, work, tolerance):
        self._lon_coef = math.cos(home[0][0])
        self._home = home
        self._work = work
        self._tolerance = tolerance

    def distance(self, a, b):
        square_sum = ((a[0] - b[0])**2 + ((a[1] - b[1]) * self._lon_coef)**2)
        return math.sqrt(square_sum) * DISTANCE_MULTIPLIER

    def at_work(self, p):
        for w in self._work:
            if self.distance(p, w) < self._tolerance:
                return True
        return False

    def at_home(self, p):
        for h in self._home:
            if self.distance(p, h) < self._tolerance:
                return True
        return False


class DaySomewhere:
    def __init__(self, arrived, left):
        self.arrived = arrived
        self.left = left


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('location_file', help='json extraction of your location')
    parser.add_argument(
            'home_coord',
            help='coordinate of home locations. (list of comma separated lat/lon)')
    parser.add_argument(
            'work_coord',
            help='coordinate of work locations. (list of comma separated lat/lon)')
    parser.add_argument(
            '--start_date',
            help='only parse data since this date. Format is YYYY/MM/DD')
    parser.add_argument(
            '--tolerance', default=0.5, type=float,
            help='default tolerance when detection location')

    args = parser.parse_args()
    start_date = args.start_date
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y/%m/%d')
        except ValueError:
            print('start date "{}" doesn\'t match the expected format: '
                    'YYYY/MM/DD'.format(start_date))

    start_date_ms = int(start_date.timestamp() * 1000) if start_date else 0

    # Lat, Lon
    home = [[float(c)  for c in l.split(':')] for l in args.home_coord.split(',')]
    work = [[float(c)  for c in l.split(':')] for l in args.work_coord.split(',')]

    distance_helper = DistanceHelper(home, work, args.tolerance)

    print('Distance between work and home: {}'.format(distance_helper.distance(home[0], work[0])))

    days_at_work = {}
    days_at_home = {}
    with open(args.location_file, 'rb') as loc:
        records = ijson.items(loc, 'locations.item')
        n = 0
        for rec in records:
            n += 1
            if n % 10000 == 0:
                print('At {}'.format(n))

            timestamp = int(rec['timestampMs'])
            if timestamp < start_date_ms:
                break

            location = (rec['latitudeE7'] / 10000000., rec['longitudeE7']/10000000)
            timestamp = timestamp / 1000.
            d = datetime.fromtimestamp(timestamp)
            date_tuple = (d.year, d.month, d.day)

            if distance_helper.at_work(location):
                day = days_at_work.setdefault(date_tuple, DaySomewhere(d.max, d.min))
                if day.arrived.timestamp() > timestamp:
                    day.arrived = d
                if day.left.timestamp() < timestamp:
                    day.left = d
            elif distance_helper.at_home(location):
                day = days_at_home.setdefault(date_tuple, DaySomewhere(d.max, d.min))
                if day.arrived.timestamp() > timestamp and d.hour > 13:
                    day.arrived = d
                elif day.left.timestamp() < timestamp and d.hour < 13:
                    day.left = d

        print('Processed {} records'.format(n))
        print('worked for {} days'.format(len(days_at_work)))
        print('was home for {} days'.format(len(days_at_home)))

        # Print the work day length.
        worked_seconds = []
        for k in sorted(days_at_work.keys()):
            arrived = days_at_work[k].arrived
            left = days_at_work[k].left
            t = left - arrived
            worked_hours = int(t.total_seconds() / 3600)
            worked_minutes = int((t.total_seconds() % 3600) / 60)
            if worked_hours > 2:
                worked_seconds.append(t.total_seconds())

            print('{}: Worked {} hours and {} minutes, from {} to {}'.format(
                arrived.strftime('%a %b %d'),
                worked_hours, worked_minutes,
                arrived.strftime('%H:%M'),
                left.strftime('%H:%M')))

        average_seconds = sum(worked_seconds) / len(worked_seconds)
        print('On average: {} hours and {} minutes'.format(
            int(average_seconds / 3600),
            int((average_seconds % 3600) / 60)))

        # Print the commute length.
        print('\n\n\nCommute lengths:')
        commute_seconds = []
        for k in sorted(days_at_work.keys()):
            if not k in days_at_home:
                continue
            work = days_at_work[k]
            home = days_at_home[k]
            morning_commute = int((work.arrived - home.left).total_seconds() / 60)
            evening_commute = int((home.arrived - work.left).total_seconds() / 60)

            print('{}: Morning {}min, Evening {}min'.format(
                work.arrived.strftime('%a %b %d'),
                morning_commute, evening_commute))


if __name__ == '__main__':
    main()
