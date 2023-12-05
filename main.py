#!/usr/bin/env python3

import argparse
import datetime
import json
import re
import subprocess
import sys

import requests

from .metrics import Metric, MetricCounter, MetricSummary
from .time import UTC_NOW


SUCCESS_PATTERN = re.compile(
    r"\d+ bytes from (?P<host>[^ ]+) \((?P<ip>[^ ]+)\): icmp_seq=(?P<seq>\d+) ttl=\d+ time=(?P<time>[^ ]+) ms"
)
GRAFANA_USER_ID = 1269240
GRAFANA_API_KEY = "glc_eyJvIjoiOTgxNjQ5IiwibiI6InN0YWNrLTc4MDY2OS1pbnRlZ3JhdGlvbi1waW5nbW9uIiwiayI6IjhkNkw2bjRmTWlNNjczbDhISHUwbndNNCIsIm0iOnsiciI6InByb2QtdXMtZWFzdC0wIn19"


def run_ping(hostname: str, count: int = 10) -> subprocess.Popen:
    return subprocess.Popen(
        ["ping", "-c", str(count), hostname], stdout=subprocess.PIPE
    )


def main():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Monitor a continuous ping",
    )
    parser.add_argument("hostname", help="Host to continuously ping")
    parser.add_argument(
        "-c", "--count", help="Number of pings to send each batch", default=10
    )
    args = parser.parse_args()

    total_counter = MetricCounter(
        "pingmon.ping.total", [Metric.tag("host", args.hostname)]
    )
    success_counter = MetricCounter(
        "pingmon.ping.success", [Metric.tag("host", args.hostname)]
    )
    failure_counter = MetricCounter(
        "pingmon.ping.failure", [Metric.tag("host", args.hostname)]
    )
    rtt_summary = MetricSummary("pingmon.ping.rtt", [Metric.tag("host", args.hostname)])

    try:
        while True:
            ping_process = run_ping(hostname=args.hostname, count=args.count)
            ping_process.wait()
            total_counter.measure(args.count)
            successes = 0
            for ping_line in ping_process.stdout:
                ping_line = ping_line.decode("utf-8").strip()
                match = SUCCESS_PATTERN.match(ping_line)

                if match:
                    successes += 1
                    rtt_summary.measure(float(match.groupdict()["time"]))

            success_counter.measure(successes)
            failure_counter.measure(args.count - successes)

            try:
                metrics = (
                    total_counter.report()
                    + success_counter.report()
                    + failure_counter.report()
                    + rtt_summary.report()
                )
                response = requests.post(
                    "https://graphite-prod-13-prod-us-east-0.grafana.net/graphite/metrics",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {GRAFANA_USER_ID}:{GRAFANA_API_KEY}",
                    },
                    data=json.dumps([m.model_dump() for m in metrics]),
                )
                response.raise_for_status()

                total_counter.reset()
                success_counter.reset()
                failure_counter.reset()
                rtt_summary.reset()
            except Exception as exc:
                print("Failed to publish data to grafana")
                print(response.text)

    except KeyboardInterrupt:
        ping_process.kill()


if __name__ == "__main__":
    main()
