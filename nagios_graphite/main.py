#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Program entry point"""

from __future__ import print_function

import functools
import os
import sys
import urllib
from time import sleep

import requests
from pynagios import Plugin, Response, make_option, UNKNOWN

class EmptyQueryResult(Exception):
    pass


def percentile(n):
    """Create function that calculates percentile for list"""

    return lambda xs: sorted(xs)[int(len(xs)*n)]


def remove_null(aggfn):
    """Decorator for removing null values for `aggfn`"""

    @functools.wraps(aggfn)
    def wrapper(xs):
        return aggfn([x for x in xs if x is not None])
    return wrapper


def raise_on_empty(aggfn):
    """Decorator for raising EmptyQueryResult on empty results"""

    @functools.wraps(aggfn)
    def wrapper(xs):
        if not xs:
            raise EmptyQueryResult("Graphite query returned no results")
        return aggfn(xs)
    return wrapper


def values_only(aggfn):
    return remove_null(raise_on_empty(aggfn))


def nullcnt(xs):
    """Counts null values in Graphite query result"""

    return len([x for x in xs if x is None])


def nullpct(xs):
    """Calculates percentage of null values in Graphite query result"""

    return float(nullcnt(xs)) / float(len(xs))


FUNCTIONS = {
    "sum":    values_only(sum),
    "min":    values_only(min),
    "max":    values_only(max),
    "avg":    values_only(lambda xs: sum(xs) / len(xs)),
    "median": values_only(percentile(0.5)),
    "95th":   values_only(percentile(0.95)),
    "99th":   values_only(percentile(0.99)),
    "999th":  values_only(percentile(0.999)),
    "nullcnt": raise_on_empty(nullcnt),
    "nullpct": raise_on_empty(nullpct),
}


F_OPTS = ", ".join(FUNCTIONS.keys())


def combine(series, aggfn):
    """Combine Graphite series data using aggfn"""

    pairs = reduce(lambda a, b: a + b, [e["datapoints"] for e in series], [])
    points = [e[0] for e in pairs]
    return aggfn(points)


def format_from(from_):
    if not from_.startswith("-"):
        return "-" + from_
    else:
        return from_


def graphite_querystring(opts):
    qs = {
        "target": opts.target,
        "from": format_from(opts.from_),
        "until": format_from(opts.until),
        "format": "json",
    }

    return urllib.urlencode(qs)


def graphite_url(opts):
    qs = graphite_querystring(opts)
    return "{0}?{1}".format(opts.hostname, qs)


def graphite_session(opts):
    session = requests.Session()
    if opts.username:
        session.auth = (opts.username, opts.password)
    return session


def graphite_fetch(opts, session=None):
    if session is None:
        session = graphite_session(opts)

    url = graphite_url(opts)
    if opts.debug:
        print("{0}".format(url))
    resp = session.get(url, timeout=opts.http_timeout)

    if opts.retry:
        retry_count = 0
        while retry_count < opts.retry:
            retry_count = retry_count + 1

            try:
                ret = resp.json()
                if resp.ok and ret:
                    return ret
            except:
                pass

            # pause before hitting the server again
            sleep(0.2)
    else:
        return resp.json() if resp.ok else []


def check_graphite(opts, session=None):
    aggfn = FUNCTIONS[opts.func]
    raw_data = graphite_fetch(opts)

    if raw_data:
        return combine(raw_data, aggfn)
    else:
        return None


class GraphiteNagios(Plugin):
    username = make_option(
        "--username", "-U",
        help="Username (HTTP Basic Auth)")
    password = make_option(
        "--password", "-P",
        help="Password (HTTP Basic Auth)")

    name = make_option(
        "--name", "-N",
        help="Metric name", default="metric")
    target = make_option(
        "--target", "-M",
        help="Graphite target (series or query)")
    from_ = make_option(
        "--from", "-F",
        help="Starting offset", default="1minute")

    until = make_option(
        "--until", "-u",
        help="Ending offset", default="")

    func = make_option(
        "--algorithm", "-A",
        help=("Algorithm for combining metrics, options: "
              "{0}, (default: avg)".format(F_OPTS)),
        default="avg", choices=FUNCTIONS.keys())

    retry = make_option(
        "--retry", "-r",
        help="Retry graphite request n times before giving up",
        default=0,
        type=int)

    http_timeout = make_option(
        "--http-timeout", "-o",
        help="HTTP request timeout",
        default=10,
        type=int)

    notes = make_option(
        "--notes", "-n",
        help="Notes to be added to the alert")

    action = make_option(
        "--action", "-a",
        help="Actions to be listed in the alert")

    debug = make_option(
        "--debug", "-d",
        help="Print the graphite URL", action="store_true")

    def check(self):
        value = check_graphite(self.options)
        if value is None:
            return Response(UNKNOWN, "No results returned!")

        message = "{0} ({1} is {2})".format(
            self.options.name, self.options.func, value)
        response = self.response_for_value(value, message)
        try:
            response.set_perf_data(self.options.func, value)
        except ValueError as e:
            raise ValueError("failed to set {} as perf data: {}".format(
                value, str(e)))
        return response

    def status_str(self, response):
        result = "%s:" % response.status.name

        if response.message is not None:
            result += " %s" % response.message

        if len(response.perf_data) > 0:
            # Attach the performance data to the result
            data = [str(val) for key,val in response.perf_data.iteritems()]
            result += '|%s' % (' '.join(data))

        if self.options.notes:
            result += "\nNotes: {0}\n".format(self.options.notes)

        if self.options.action:
            result += "\nAction: {0}\n".format(self.options.action)

        return (response.status.exit_code, result)


def main(args):
    try:
        nag = GraphiteNagios(args)
        response = nag.check()
        (exit_code, msg) = nag.status_str(response)

        print(msg)
        return sys.exit(exit_code)
    except Exception as e:
        message = "{0}: {1}".format(e.__class__.__name__, str(e))
        Response(UNKNOWN, "Client error: " + message).exit()


def entry_point():
    return main(sys.argv)

if __name__ == '__main__':
    entry_point()
