"""Aggregate the raw JSON records into a :class:`BuildSummary`.

This module does all the maths and none of the printing. ``table.py``
and ``html.py`` both render the same :class:`BuildSummary`, so the two
outputs can never disagree about the numbers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json


class BenchmarkFileError(Exception):
    """Raised when the benchmarks JSON cannot be read or parsed."""


def load_records(path: str) -> dict:
    """Read the benchmarks JSON and return it as a dictionary."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise BenchmarkFileError(
            f"{path}: not found : run the build with the extension enabled "
            "or try changing the pwd to the docs directory"
        ) from None
    except json.JSONDecodeError as e:
        raise BenchmarkFileError(f"{path}: not valid JSON ({e})") from None


@dataclass(frozen=True)
class HandlerRow:
    """Aggregated timings of one handler on one event."""

    handler: str
    kind: str
    extension: str
    calls: int
    total: float
    avg: float


@dataclass(frozen=True)
class EventRow:
    """Aggregated timings of one event name over all its emissions."""

    name: str
    own_time: float
    duration: float
    emissions: int
    depth_min: int
    depth_max: int
    has_nested: bool
    handlers: tuple[HandlerRow, ...]
    handler_sum: float  # Sum of the handlers' ``total`` values (in seconds).
    overhead: float  # ``duration - handler_sum``: time inside emit() but outside any wrapped handler.


@dataclass(frozen=True)
class GapRow:
    """Cumulative gap between two consecutive top-level emissions.

    Parameters
    ----------
    source, target : str
        Names of the two events the gap falls between.
    total : float
        Summed gap time (in seconds) over all occurrences of this pair.
    count : int
        How many times this pair occurred consecutively.
    """

    source: str
    target: str
    total: float
    count: int

    @property
    def label(self) -> str:
        return f"{self.source} -> {self.target}"


@dataclass(frozen=True)
class OverviewRow:
    """One line of the overview: an event's own time or a gap.

    Parameters
    ----------
    label : str
        Event name, or a gap description such as ``"a -> b"``.
    kind : str
        ``"event"`` or ``"gap"``.
    seconds : float
        Own time of the event, or total gap time, in seconds.
    count : int or None
        Emissions of the event / occurrences of the gap; ``None`` for
        the startup and finish pseudo-gaps.
    """

    label: str
    kind: str
    seconds: float
    count: int | None


@dataclass(frozen=True)
class EmissionDetail:
    """One recorded emission of a single event, verbatim from the JSON.

    ``parent_name`` resolves ``parent_id`` to the parent emission's
    event name (``None`` for top-level emissions). ``duration`` and
    ``own_time`` are ``None`` for an emission still in progress when the
    JSON was written (e.g. ``build-finished``).
    """

    event_id: int
    call: int
    start: float
    depth: int
    duration: float | None
    own_time: float | None
    parent_name: str | None


@dataclass(frozen=True)
class CallDetail:
    """One recorded call of a single handler, verbatim from the JSON."""

    event: str
    handler: str
    module: str
    kind: str
    extension: str
    call: int
    start: float
    duration: float


@dataclass(frozen=True)
class GapOccurrence:
    """One individual gap between two consecutive top-level emissions.

    Parameters
    ----------
    source, target : str
        Event names on either side of the gap.
    source_call, target_call : int
        The ``call`` numbers of the two emissions involved.
    start : float
        Seconds since build start at which the gap began (source end).
    end : float
        Seconds since build start at which the gap ended (target start).
    """

    source: str
    target: str
    source_call: int
    target_call: int
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class BuildSummary:
    """Everything the table and HTML outputs need, in one place.

    Parameters
    ----------
    total_build_time : float
        Wall-clock build time in seconds (``total_wall_time`` from the
        JSON, falling back to the sum of event own-times, or 1.0).
    time_in_events : float
        Sum of all events' own times, in seconds.
    events : tuple of EventRow
        Events sorted by ``own_time`` descending.
    gaps : tuple of GapRow
        Gaps between top-level emissions, sorted by ``total`` descending.
    startup : float
        Time (in seconds) before the first top-level emission.
    finish : float
        Time (in seconds) after the last top-level emission ends.
    overlaps : int
        Number of negative gaps found. Top-level emissions can't
        overlap, so any value > 0 flags a bug in the recording.
    """

    total_build_time: float
    time_in_events: float
    events: tuple[EventRow, ...]
    gaps: tuple[GapRow, ...]
    startup: float
    finish: float
    overlaps: int

    @property
    def gaps_total(self) -> float:
        """Summed gap time between top-level emissions, in seconds."""
        return sum(g.total for g in self.gaps)

    @property
    def outside_events(self) -> float:
        """``startup + gaps + finish``: time outside any emission."""
        return self.startup + self.gaps_total + self.finish

    def pct(self, seconds: float) -> float:
        """Return ``seconds`` as a percentage of the build time."""
        return 100 * seconds / self.total_build_time


def compute_summary(data: dict) -> BuildSummary:
    """Aggregate the raw JSON ``data`` into a :class:`BuildSummary`."""
    calls = data.get("calls", [])
    events = data.get("events", [])

    # ---- per-(event, handler) aggregation -------------------------------
    handler_totals: dict[tuple[str, str], float] = defaultdict(float)
    call_counts: Counter = Counter()
    meta: dict[tuple[str, str], tuple[str, str, str | None]] = {}
    for c in calls:
        key = (c["event"], c["handler"])
        handler_totals[key] += c["duration"]
        call_counts[key] += 1
        meta[key] = (c["module"], c["kind"], c["extension"])

    # ---- per-event aggregation ------------------------------------------
    event_totals: dict[str, float] = defaultdict(float)
    own_totals: dict[str, float] = defaultdict(float)
    depths_by_event: dict[str, set[int]] = defaultdict(set)
    emissions_by_event: Counter = Counter()
    has_nested: set[str] = set()
    for e in events:
        if e["duration"] is None:
            continue
        event_totals[e["event_name"]] += e["duration"]
        depths_by_event[e["event_name"]].add(e["depth"])
        emissions_by_event[e["event_name"]] += 1
        if e["own_time"] is not None:
            own_totals[e["event_name"]] += e["own_time"]
            if e["own_time"] < e["duration"]:
                has_nested.add(e["event_name"])

    time_in_events = sum(own_totals.values())
    total_build_time = data.get("total_wall_time") or time_in_events or 1.0

    by_event: dict[str, list[HandlerRow]] = defaultdict(list)
    for (event, handler), total in handler_totals.items():
        n_calls = call_counts[(event, handler)]
        _module, kind, ext = meta[(event, handler)]
        avg = total / n_calls if n_calls else 0.0
        by_event[event].append(
            HandlerRow(handler, kind, ext or "-", n_calls, total, avg)
        )

    event_rows = []
    for name in sorted(own_totals, key=lambda e: own_totals[e], reverse=True):
        handlers = tuple(
            sorted(by_event.get(name, []), key=lambda r: r.total, reverse=True)
        )
        handler_sum = sum(r.total for r in handlers)
        depths = sorted(depths_by_event[name])
        event_rows.append(
            EventRow(
                name=name,
                own_time=own_totals[name],
                duration=event_totals[name],
                emissions=emissions_by_event[name],
                depth_min=depths[0],
                depth_max=depths[-1],
                has_nested=name in has_nested,
                handlers=handlers,
                handler_sum=handler_sum,
                overhead=event_totals[name] - handler_sum,
            )
        )

    top = sorted(
        (e["start"], e["duration"], e["event_name"])
        for e in events
        if e["depth"] == 0 and e["duration"] is not None
    )
    gap_acc: dict[tuple[str, str], tuple[float, int]] = {}
    overlaps = 0
    for (prev_start, prev_duration, prev_name), (start, _, name) in zip(top, top[1:]):
        gap = start - (prev_start + prev_duration)
        if gap < 0:
            overlaps += 1  # top-level emissions can't overlap; flags a bug
            continue
        total, count = gap_acc.get((prev_name, name), (0.0, 0))
        gap_acc[(prev_name, name)] = (total + gap, count + 1)

    gap_rows = tuple(
        sorted(
            (
                GapRow(src, dst, total, count)
                for (src, dst), (total, count) in gap_acc.items()
            ),
            key=lambda g: g.total,
            reverse=True,
        )
    )
    startup = top[0][0] if top else 0.0
    finish = total_build_time - (top[-1][0] + top[-1][1]) if top else 0.0

    return BuildSummary(
        total_build_time=total_build_time,
        time_in_events=time_in_events,
        events=tuple(event_rows),
        gaps=gap_rows,
        startup=startup,
        finish=finish,
        overlaps=overlaps,
    )


# --------------------------------------------------------------- details --


def event_names(data: dict) -> set[str]:
    """Return every event name that appears in the recorded emissions."""
    return {e["event_name"] for e in data.get("events", [])}


def handler_names(data: dict) -> set[str]:
    """Return every handler name that appears in the recorded calls."""
    return {c["handler"] for c in data.get("calls", [])}


def overview_rows(s: BuildSummary) -> tuple[OverviewRow, ...]:
    """Events (own time) and gaps interleaved, sorted by time descending."""
    rows = [OverviewRow(ev.name, "event", ev.own_time, ev.emissions) for ev in s.events]
    if s.startup > 0:
        rows.append(
            OverviewRow("(startup, before first emission)", "gap", s.startup, None)
        )
    if s.finish > 0:
        rows.append(OverviewRow("(finish, after last emission)", "gap", s.finish, None))
    rows += [OverviewRow(g.label, "gap", g.total, g.count) for g in s.gaps]
    rows.sort(key=lambda r: r.seconds, reverse=True)
    return tuple(rows)


def all_emission_details(data: dict) -> dict[str, tuple[EmissionDetail, ...]]:
    """Every recorded emission, grouped by event name, in emission order."""
    events = data.get("events", [])
    id_to_name = {e["event_id"]: e["event_name"] for e in events}
    grouped: dict[str, list[EmissionDetail]] = defaultdict(list)
    for e in events:
        grouped[e["event_name"]].append(
            EmissionDetail(
                event_id=e["event_id"],
                call=e["call"],
                start=e["start"],
                depth=e["depth"],
                duration=e["duration"],
                own_time=e["own_time"],
                parent_name=id_to_name.get(e["parent_id"]),
            )
        )
    return {name: tuple(rows) for name, rows in grouped.items()}


def emission_details(data: dict, event_name: str) -> tuple[EmissionDetail, ...]:
    """Every recorded emission of ``event_name``, in emission order."""
    return all_emission_details(data).get(event_name, ())


def all_handler_call_details(data: dict) -> dict[str, tuple[CallDetail, ...]]:
    """Every recorded call, grouped by handler name, in chronological order."""
    grouped: dict[str, list[CallDetail]] = defaultdict(list)
    for c in data.get("calls", []):
        grouped[c["handler"]].append(
            CallDetail(
                event=c["event"],
                handler=c["handler"],
                module=c["module"],
                kind=c["kind"],
                extension=c["extension"] or "-",
                call=c["call"],
                start=c["start"],
                duration=c["duration"],
            )
        )
    for rows in grouped.values():
        rows.sort(key=lambda r: r.start)
    return {name: tuple(rows) for name, rows in grouped.items()}


def handler_call_details(
    data: dict, handler_name: str, event_name: str | None = None
) -> tuple[CallDetail, ...]:
    """Every recorded call of ``handler_name``, in chronological order.

    If ``event_name`` is given, only calls made during that event's
    emissions are returned.
    """
    rows = all_handler_call_details(data).get(handler_name, ())
    if event_name is not None:
        rows = tuple(r for r in rows if r.event == event_name)
    return rows


def all_gap_occurrence_details(
    data: dict,
) -> dict[tuple[str, str], tuple[GapOccurrence, ...]]:
    """Every individual gap, grouped by (source, target) event pair, in
    chronological order.

    Negative gaps (overlapping emissions, which flag a recording bug)
    are skipped, matching :func:`compute_summary`.
    """
    top = sorted(
        (e["start"], e["duration"], e["event_name"], e["call"])
        for e in data.get("events", [])
        if e["depth"] == 0 and e["duration"] is not None
    )
    grouped: dict[tuple[str, str], list[GapOccurrence]] = defaultdict(list)
    for (p_start, p_dur, p_name, p_call), (start, _, name, call) in zip(top, top[1:]):
        gap_start = p_start + p_dur
        if start < gap_start:
            continue
        grouped[(p_name, name)].append(
            GapOccurrence(p_name, name, p_call, call, gap_start, start)
        )
    return {pair: tuple(rows) for pair, rows in grouped.items()}


def gap_occurrence_details(
    data: dict, source: str, target: str
) -> tuple[GapOccurrence, ...]:
    """Every individual gap between consecutive top-level emissions of
    ``source`` and ``target``, in chronological order.
    """
    return all_gap_occurrence_details(data).get((source, target), ())
