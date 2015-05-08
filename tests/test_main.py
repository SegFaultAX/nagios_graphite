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


def test_remove_null_without_null():
    xs = [1, 2, 3, 4]
    assert main.remove_null(sum)(xs) == 10


def test_remove_null_with_null():
    xs = [1, None, 2, None]
    assert main.remove_null(sum)(xs) == 3


def test_raise_on_empty_without_empty():
    xs = [1, 2, 3, 4]
    assert main.raise_on_empty(sum)(xs) == 10


def test_raise_on_empty_with_empty():
    xs = []
    with pytest.raises(main.EmptyQueryResult):
        main.raise_on_empty(sum)(xs)


def test_values_only_with_values():
    assert main.values_only(sum)([1, 2, 3]) == 6
    assert main.values_only(sum)([1, None, 3]) == 4


def test_values_only_without_values():
    with pytest.raises(main.EmptyQueryResult):
        main.values_only(sum)([])

    with pytest.raises(main.EmptyQueryResult):
        main.values_only(sum)([None, None, None])


def test_nullcnt():
    assert main.nullcnt([1, 2, 3]) == 0
    assert main.nullcnt([1, None, None]) == 2


def test_nullpct():
    assert main.nullpct([1, 2, 3]) == 0.0
    assert main.nullpct([None, 2, 3, None]) == 0.5


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


def test_raising_aggregators():
    for name, fn in FUNCTIONS.iteritems():
        with pytest.raises(main.EmptyQueryResult):
            fn([])


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
    id_ = lambda xs: xs
    assert combine(graphite_without_none, id_) == [1, 2, 3, 4, 5, 6]


def test_combine_with_none():
    id_ = lambda xs: xs
    assert combine(graphite_with_none, id_) == [1, 2, 3, None, 5, None]


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
