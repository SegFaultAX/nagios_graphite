# -*- coding: utf-8 -*-

# The parametrize function is generated, so this doesn't work:
#
#     from pytest.mark import parametrize
#

import re
import json
import shlex
import random
import urllib

import pytest
import responses
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


def options_for(s):
    argv = shlex.split("nagios_graphite " + s)
    return GraphiteNagios(argv).options


def test_format_from():
    assert main.format_from("1second") == "-1second"
    assert main.format_from("-1second") == "-1second"


def test_graphite_querystring():
    opts = options_for("-M 'cpu.load.average' -F 1minute")
    qs = main.graphite_querystring(opts)

    assert urllib.urlencode({"from": main.format_from("1minute")}) in qs
    assert urllib.urlencode({"target": "cpu.load.average"}) in qs
    assert urllib.urlencode({"format": "json"}) in qs


def test_graphite_url():
    opts = options_for("-M 'cpu.load.average' -H http://example.com")
    expected = "{}?{}".format(
        "http://example.com", main.graphite_querystring(opts))

    assert main.graphite_url(opts) == expected


def test_graphite_session_noauth():
    opts = options_for("-M 'cpu.load.average' -H http://example.com")
    assert main.graphite_session(opts).auth is None


def test_graphite_session_auth():
    opts = options_for(
        "-M 'cpu.load.average' -H http://example.com -U foo -P pass")
    assert main.graphite_session(opts).auth == ("foo", "pass")


@responses.activate
def test_graphite_fetch_success():
    opts = options_for(
        "-M 'cpu.load.average' -H http://example.com -U foo -P pass")
    url_re = re.compile("^{}.*$".format(re.escape(opts.hostname)))

    resp = json.dumps(graphite_with_none)
    responses.add(
        responses.GET, url_re,
        body=resp, status=200,
        content_type='application/json')

    assert main.graphite_fetch(opts) == graphite_with_none


@responses.activate
def test_graphite_fetch_failure():
    opts = options_for(
        "-M 'cpu.load.average' -H http://example.com -U foo -P pass")
    url_re = re.compile("^{}.*$".format(re.escape(opts.hostname)))

    responses.add(
        responses.GET, url_re, status=500)

    assert main.graphite_fetch(opts) == []


@responses.activate
def test_check_graphite_success():
    for fn_name, aggfn in FUNCTIONS.iteritems():
        opts = options_for(
            "-M 'cpu.load.average' -H http://example.com -U foo -P pass "
            "-A {}".format(fn_name))
        url_re = re.compile("^{}.*$".format(re.escape(opts.hostname)))

        resp = json.dumps(graphite_with_none)
        responses.add(
            responses.GET, url_re,
            body=resp, status=200,
            content_type='application/json')

        expected = main.combine(graphite_with_none, aggfn)
        assert main.check_graphite(opts) == expected


@responses.activate
def test_check_graphite_failure():
    for fn_name, aggfn in FUNCTIONS.iteritems():
        opts = options_for(
            "-M 'cpu.load.average' -H http://example.com -U foo -P pass "
            "-A {}".format(fn_name))
        url_re = re.compile("^{}.*$".format(re.escape(opts.hostname)))

        responses.add(
            responses.GET, url_re, status=500)

        assert main.check_graphite(opts) is None
