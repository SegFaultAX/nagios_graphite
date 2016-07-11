# Nagios Graphite

A nagios check for graphite

## Quick Start

```shell
$ pip install nagios_graphite

$ nagios_graphite \
  -H http://example.com/render \
  -M 'com.example.*.cpu.load' \
  -N cpu_load_avg -w 4 -c 8 -F "5minutes" -A avg
CRIT: cpu_load_avg (avg = 11)|avg=11;;;;

$ echo $?
2
```

## Documentation

```
Usage: nagios_graphite [options]

Options:
  -U USERNAME, --username=USERNAME
                        Username (HTTP Basic Auth)
  -N NAME, --name=NAME  Metric name
  -A FUNC, --algorithm=FUNC
                        Algorithm for combining metrics, options: nullpct,
                        999th, 95th, min, max, sum, avg, median, 99th,
                        nullcnt, (default: avg)
  -F FROM_, --from=FROM_
                        Starting offset
  -P PASSWORD, --password=PASSWORD
                        Password (HTTP Basic Auth)
  -o HTTP_TIMEOUT, --http-timeout=HTTP_TIMEOUT
                        HTTP request timeout
  -u UNTIL, --until=UNTIL
                        Ending offset
  -M TARGET, --target=TARGET
                        Graphite target (series or query)
  -v, --verbose
  -H HOSTNAME, --hostname=HOSTNAME
  -w WARNING, --warning=WARNING
  -c CRITICAL, --critical=CRITICAL
  -t TIMEOUT, --timeout=TIMEOUT
  -h, --help            show this help message and exit
```

## Contributing

Want to contribute? Great!

1. Fork it.
2. Create a branch (`git checkout -b my_markup`)
3. Commit your changes (`git commit -am "Added Snarkdown"`)
4. Push to the branch (`git push origin my_markup`)
5. Open a [Pull Request][1]
6. Enjoy a refreshing cup of coffee!

## License

The MIT License (MIT)

Copyright (c) 2015 Michael-Keith Bernard

See LICENSE for full license.

[1]: http://github.com/segfaultax/nagios_graphite/pulls
