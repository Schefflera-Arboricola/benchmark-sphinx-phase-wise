from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict


def load_records(path):
    """Read the benchmarks JSON and returns it as a dictionay, or fails if the file is not found."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(
            f"{path}: not found : run the build with the extension enabled or try changing the pwd to the docs directory"
        )
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: not valid JSON ({e})")


def print_summary(data: dict):
    """Print the timing summary for the given data from the json"""
    calls = data.get("calls", [])
    events = data.get("events", [])

    handler_totals: dict[tuple[str, str], float] = defaultdict(float)
    call_counts: Counter = Counter()
    meta: dict[tuple[str, str], tuple[str, str, str | None]] = {}
    for c in calls:
        key = (c["event"], c["handler"])
        handler_totals[key] += c["duration"]
        call_counts[key] += 1
        meta[key] = (c["module"], c["kind"], c["extension"])

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

    def pct(seconds: float) -> float:
        return 100 * seconds / total_build_time

    by_event: dict[str, list[tuple[str, str, str, int, float, float]]] = defaultdict(
        list
    )
    for (event, handler), total in handler_totals.items():
        n_calls = call_counts[(event, handler)]
        _module, kind, ext = meta[(event, handler)]
        avg = total / n_calls if n_calls else 0.0
        by_event[event].append((handler, kind, ext or "-", n_calls, total, avg))

    ordered_events = sorted(own_totals, key=lambda e: own_totals[e], reverse=True)

    col_header = (
        f"  {'Handler':50}{'Kind':20}{'Ext/Module':40}"
        f"{'Calls':>10}{'Total(s)':>15}{'Avg(ms)':>15}"
    )
    width = len(col_header)

    print()
    print("Build time: ", total_build_time)
    for event in ordered_events:
        ev_total = event_totals[event]
        ev_own = own_totals[event]
        depths = sorted(depths_by_event[event])
        depth_str = str(depths[0]) if len(depths) == 1 else f"{depths[0]}-{depths[-1]}"
        nested_str = (
            f"  |  {ev_total:.6f}s duration (including nested event)"
            if event in has_nested
            else ""
        )
        print("=" * width)
        print(
            f"{event}  —  {ev_own:.6f}s own time ({pct(ev_own):.2f}% of build)  |  "
            f"{emissions_by_event[event]} emissions"
            f"{nested_str}  |  depth {depth_str}"
        )
        print("=" * width)
        print(col_header)
        print("-" * width)

        handlers = sorted(by_event.get(event, []), key=lambda r: r[4], reverse=True)
        for handler, kind, ext, n_calls, total, avg in handlers:
            print(
                f"  {handler[:49]:50}{kind:20}{ext[:39]:40}"
                f"{n_calls:10d}{total:15.6f}{avg * 1000:15.3f}"
            )
        handler_sum = sum(r[4] for r in handlers)
        print("-" * width)
        print(f"  {'(sum of handlers)':50}{'':20}{'':40}{'':10}{handler_sum:15.6f}")
        print(
            f"  {'(unaccounted overhead)':50}{'':20}{'':40}{'':10}"
            f"{ev_total - handler_sum:15.6f}"
        )
        print()

    print("=" * width)
    print(
        f"Sum of own durations of all events: {time_in_events:.6f}s   "
        f"Wall clock: {total_build_time:.6f}s   "
        f"Outside any event: {total_build_time - time_in_events:.6f}s "
        f"({pct(total_build_time - time_in_events):.2f}%)"
    )

    # Sphinx emits at fixed points in the build, but the work between two
    # emissions (parsing, writing output) is not inside emit() and so it's not recorded.
    # that's why printing gaps summary table.
    # nested event emissions are skipped because a child emission is contained in its
    # parent's interval, so the gaps around it are already counted there.
    top = sorted(
        (e["start"], e["duration"], e["event_name"])
        for e in events
        if e["depth"] == 0 and e["duration"] is not None
    )
    gaps: dict[tuple[str, str], tuple[float, int]] = {}
    overlaps = 0
    for (prev_start, prev_duration, prev_name), (start, _, name) in zip(top, top[1:]):
        gap = start - (prev_start + prev_duration)
        if gap < 0:
            overlaps += 1  # top-level emissions can't overlap; flags a bug
            continue
        total, count = gaps.get((prev_name, name), (0.0, 0))
        gaps[(prev_name, name)] = (total + gap, count + 1)

    startup = top[0][0] if top else 0.0
    finish = total_build_time - (top[-1][0] + top[-1][1]) if top else 0.0
    between = sum(total for total, _ in gaps.values())

    # 2 for the indent, then the 15/10/12/10 numeric columns
    label_w = width - 49
    print()
    print("=" * width)
    print("Gaps Summary")
    print("=" * width)
    print(
        f"  {'Between':{label_w}}{'Total(s)':>15}{'Count':>10}"
        f"{'Avg(ms)':>12}{'% build':>10}"
    )
    print("-" * width)
    if top:
        print(
            f"  {'(startup, before first emission)':{label_w}}{startup:15.6f}"
            f"{'':10}{'':12}{pct(startup):9.2f}%"
        )
    for (prev_name, name), (total, count) in sorted(
        gaps.items(), key=lambda kv: kv[1][0], reverse=True
    ):
        label = f"{prev_name} -> {name}"
        print(
            f"  {label[: label_w - 1]:{label_w}}{total:15.6f}"
            f"{count:10d}{total / count * 1000:12.3f}{pct(total):9.2f}%"
        )
    if top:
        print(
            f"  {'(finish, after last emission)':{label_w}}{finish:15.6f}"
            f"{'':10}{'':12}{pct(finish):9.2f}%"
        )
    print("-" * width)
    outside = startup + between + finish
    print(
        f"  {'(total outside events)':{label_w}}{outside:15.6f}"
        f"{'':10}{'':12}{pct(outside):9.2f}%"
    )
    if overlaps:
        print(
            f"  WARNING: {overlaps} negative gaps -- top-level emissions "
            "overlap, so these timings are unreliable"
        )


path = sys.argv[1] if len(sys.argv) > 1 else "sphinx_benchmarks.json"
print_summary(load_records(path))
