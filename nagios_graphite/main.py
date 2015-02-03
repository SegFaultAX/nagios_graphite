#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Program entry point"""

from __future__ import print_function

import sys
import urllib

import requests
from pynagios import Plugin, Response, make_option, UNKNOWN

def percentile(n):
    return lambda xs: sorted(xs)[int(len(xs)*n)]

FUNCTIONS = {
    "sum": sum,
    "min": min,
    "max": max,
    "avg": lambda xs: sum(xs) / len(xs),
    "median": percentile(0.5),
    "95th":   percentile(0.95),
    "99th":   percentile(0.99),
    "999th":  percentile(0.999)
}
F_OPTS = ", ".join(FUNCTIONS.keys())

def combine(series, aggfn):
    pairs = reduce(lambda a, b: a + b, [e["datapoints"] for e in series])
    points = [e[0] for e in pairs if e[0] is not None]
    return aggfn(points)

class Graphite(object):
    def __init__(self, options):
        self.options = options
        self._session = None

        self.init_session()
        self.aggfn = FUNCTIONS[options.func]

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
        return self._session

    @property
    def query(self):
        if not self.options.from_.startswith("-"):
            from_ = "-" + self.options.from_
        else:
            from_ = self.options.from_

        qs = {
            "target": self.options.target,
            "from": from_,
            "format": "json",
        }
        return urllib.urlencode(qs)

    def init_session(self):
        if self.options.username:
            self.session.auth(
                self.options.username,
                self.options.password)

    def fetch(self):
        url = "{}?{}".format(self.options.hostname, self.query)
        results = self.session.get(url)
        if results.ok and results.json():
            return combine(results.json(), self.aggfn)
        return None

class GraphiteNagios(Plugin):
    username = make_option("--username", "-U",
        help="Username (HTTP Basic Auth)")
    password = make_option("--password", "-P",
        help="Password (HTTP Basic Auth)")

    name = make_option("--name", "-N",
        help="Metric name", default="metric")
    target = make_option("--target", "-M",
        help="Graphite target (series or query)")
    from_ = make_option("--from", "-F",
        help="Starting offset", default="1minute")

    func = make_option("--algorithm", "-A",
        help=("Algorithm for combining metrics, options: "
              "{}, (default: avg)".format(F_OPTS)),
        default="avg", choices=FUNCTIONS.keys())

    def check(self):
        try:
            value = Graphite(self.options).fetch()
            if value is None:
                return Response(UNKNOWN, "No results returned!")
        except Exception as e:
            return Response(UNKNOWN, "Client error: " + str(e))

        message = "{} ({} = {})".format(
            self.options.name, self.options.func, value)
        response = self.response_for_value(value, message)
        response.set_perf_data(self.options.func, value)
        return response

def main(args):
    return GraphiteNagios(args).check().exit()

def entry_point():
    return main(sys.argv)

if __name__ == '__main__':
    entry_point()
