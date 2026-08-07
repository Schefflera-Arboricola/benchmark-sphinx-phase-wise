from __future__ import annotations

import json

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from time import perf_counter

from sphinx.application import Sphinx

# Safe notification-style events only
EVENTS = [
    "config-inited",
    "builder-inited",
    # "env-get-outdated",
    "env-before-read-docs",
    "env-purge-doc",
    "source-read",
    "include-read",
    "doctree-read",
    "env-merge-info",
    "env-updated",
    # "env-get-updated",
    "env-check-consistency",
    "write-started",
    "doctree-resolved",
    # "missing-reference",
    "warn-missing-reference",
    # "html-collect-pages",
    "object-description-transform",
    # "html-page-context",
    "linkcheck-process-uri",
    "build-finished",
]


@dataclass
class Event:
    name: str
    call: int  # indicates n_th call of this event (1st, 2nd, ...)
    start: float
    duration: float = 0.0
    # ToDo - Add more fields like:
    # extension: str | None = None
    # threads: int | None = None


class EventLogger:
    def __init__(self):
        self.events: list[Event] = []
        self.start_time: float | None = None
        # todo: need to end an end-time as well to calculate the time dor last event
        self.call_counts = Counter()

    def start(self):
        self.start_time = perf_counter()

    def record(self, name: str):
        now = perf_counter()

        self.call_counts[name] += 1

        self.events.append(
            Event(
                name=name,
                call=self.call_counts[name],
                start=now - self.start_time,
            )
        )

    def finalize(self):
        self.events.sort(key=lambda e: e.start)

        # Duration is time until the next event is triggered
        for current, nxt in zip(self.events, self.events[1:]):
            current.duration = nxt.start - current.start

    def totals(self):
        """Summarize total time spent in each event type."""
        totals = defaultdict(float)

        for event in self.events:
            totals[event.name] += event.duration

        return dict(totals)

    def write_json(self, filename="event_trace.json"):
        self.finalize()
        with open(filename, "w") as f:
            json.dump(
                {
                    "events": [asdict(event) for event in self.events],
                    "totals": self.totals(),
                },
                f,
                indent=2,
            )

    def print_summary(self):
        """To display the benchmarking summary table at the end"""
        totals = self.totals()

        total_build_time = sum(totals.values())

        rows = []

        for event in sorted(totals):
            total = totals[event]
            calls = self.call_counts[event]

            rows.append(
                (
                    event,
                    calls,
                    total,
                    total / calls if calls else 0,
                    100 * total / total_build_time if total_build_time else 0,
                )
            )

        rows.sort(key=lambda row: row[2], reverse=True)

        header = (
            f"{'Event':35}{'Calls':>10}{'Total(s)':>15}{'Avg(ms)':>15}{'%Build':>10}"
        )

        print()
        print(header)
        print("-" * len(header))

        for event, calls, total, avg, pct in rows:
            print(f"{event:35}{calls:10d}{total:15.6f}{avg * 1000:15.3f}{pct:9.2f}%")


recorder = EventLogger()


def make_callback(event_name):
    def callback(app, *args, **kwargs):
        recorder.record(event_name)

    return callback


def build_finished(app, exception):
    recorder.write_json()
    print("event_trace.json written")
    recorder.print_summary()


def setup(app: Sphinx):
    recorder.start()
    for event in EVENTS:
        app.connect(
            event,
            make_callback(event),
        )
    app.connect(
        "build-finished",
        build_finished,
    )
    return {
        "version": "0.1",
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
