# -*- coding: utf-8 -*-
# from pytest import raises

# The parametrize function is generated, so this doesn't work:
#
#     from pytest.mark import parametrize
#

import shlex
import random
import urllib

import pytest
import requests_mock
parametrize = pytest.mark.parametrize

# from nagios_graphite import metadata
from nagios_graphite import main
from nagios_graphite.main import FUNCTIONS, combine, GraphiteNagios

xs = range(1000)
random.shuffle(xs)


def test_sum():
    assert FUNCTIONS["sum"](xs) == sum(xs)


def test_min():
    assert FUNCTIONS["min"](xs) == min(xs)


def test_max():
    assert FUNCTIONS["max"](xs) == max(xs)


def test_avg():
    assert FUNCTIONS["avg"](xs) == sum(xs) / len(xs)


def test_median():
    assert FUNCTIONS["median"](xs) == 500


def test_95th():
    assert FUNCTIONS["95th"](xs) == 950


def test_99th():
    assert FUNCTIONS["99th"](xs) == 990


def test_999th():
    assert FUNCTIONS["999th"](xs) == 999


graphite_without_none = [
    {"target": "foo", "datapoints": [[1, 10], [2, 11], [3, 12]]},
    {"target": "bar", "datapoints": [[4, 10], [5, 11], [6, 12]]},
]
graphite_with_none = [
    {"target": "foo", "datapoints": [[1, 10], [2, 11], [3, 12]]},
    {"target": "bar", "datapoints": [[None, 10], [5, 11], [None, 12]]},
]


def test_combine_empty():
    assert combine([], sum) == 0


def test_combine_without_none():
    assert combine(graphite_without_none, sum) == 21


def test_combine_with_none():
    assert combine(graphite_with_none, sum) == 11


def make_opt(s):
    return GraphiteNagios(list(shlex.shlex("test " + s))).options


def test_format_from():
    assert main.format_from("1second") == "-1second"
    assert main.format_from("-1second") == "-1second"


def test_graphite_querystring():
    opts = make_opt("-T cpu.load.average -F 1minute")
    qs = main.graphite_querystring(opts)

    assert urllib.urlencode({"from": main.format_from("1minute")}) in qs
    assert urllib.urlencode({"target": opts.target}) in qs
    assert urllib.urlencode({"format": "json"}) in qs


def test_graphite_url():
    opts = make_opt("-T cpu.load.average -H http://example.com")
    expected = "{}?{}".format(opts.hostname, main.graphite_querystring(opts))

    assert main.graphite_url(opts) == expected


def test_graphite_session_noauth():
    opts = make_opt("-T cpu.load.average -H http://example.com")
    assert main.graphite_session(opts).auth is None


def test_graphite_session_auth():
    opts = make_opt("-T cpu.load.average -H http://example.com -U foo -P pass")
    assert main.graphite_session(opts).auth == ("foo", "pass")


def test_graphite_fetch():
    pass
