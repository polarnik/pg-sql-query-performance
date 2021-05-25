#!/bin/sh

docker stop sql_monitor_influxdb
docker stop sql_monitor_telegraf
docker stop sql_monitor_grafana
docker stop sql_monitor_jmeter
docker stop sql_monitor_postgres