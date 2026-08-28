"""Terminal output: prints the two summary tables from a :class:`BuildSummary`.

This module only formats and prints -- all numbers come pre-computed
from :func:`sphinx_benchmark.summary.compute_summary`.
"""

from __future__ import annotations

from .summary import BuildSummary


def print_summary(s: BuildSummary) -> None:
    """Print the per-event handler tables and the gaps summary table."""
    col_header = (
        f"  {'Handler':50}{'Kind':20}{'Ext/Module':40}"
        f"{'Calls':>10}{'Total(s)':>15}{'Avg(ms)':>15}"
    )
    width = len(col_header)

    print()
    print("Build time: ", s.total_build_time)
    for ev in s.events:
        depth_str = (
            str(ev.depth_min)
            if ev.depth_min == ev.depth_max
            else f"{ev.depth_min}-{ev.depth_max}"
        )
        nested_str = (
            f"  |  {ev.duration:.6f}s duration (including nested event)"
            if ev.has_nested
            else ""
        )
        print("=" * width)
        print(
            f"{ev.name}  —  {ev.own_time:.6f}s own time "
            f"({s.pct(ev.own_time):.2f}% of build)  |  "
            f"{ev.emissions} emissions"
            f"{nested_str}  |  depth {depth_str}"
        )
        print("=" * width)
        print(col_header)
        print("-" * width)
        for r in ev.handlers:
            print(
                f"  {r.handler[:49]:50}{r.kind:20}{r.extension[:39]:40}"
                f"{r.calls:10d}{r.total:15.6f}{r.avg * 1000:15.3f}"
            )
        print("-" * width)
        print(f"  {'(sum of handlers)':50}{'':20}{'':40}{'':10}{ev.handler_sum:15.6f}")
        print(
            f"  {'(unaccounted overhead)':50}{'':20}{'':40}{'':10}{ev.overhead:15.6f}"
        )
        print()

    print("=" * width)
    print(
        f"Sum of own durations of all events: {s.time_in_events:.6f}s   "
        f"Wall clock: {s.total_build_time:.6f}s   "
        f"Outside any event: {s.total_build_time - s.time_in_events:.6f}s "
        f"({s.pct(s.total_build_time - s.time_in_events):.2f}%)"
    )

    # 2 for the indent, then the 15/10/12/10 numeric columns
    label_w = width - 49
    print()
    print("=" * width)
    print("Gaps Summary")
    print("=" * width)
    print(
        f"  {'Between':{label_w}}{'Gap Total(s)':>15}{'Count':>10}"
        f"{'Avg(ms)':>12}{'% build':>10}"
    )
    print("-" * width)
    have_top = bool(s.events) or s.startup or s.finish
    if have_top:
        print(
            f"  {'(startup, before first emission)':{label_w}}{s.startup:15.6f}"
            f"{'':10}{'':12}{s.pct(s.startup):9.2f}%"
        )
    for g in s.gaps:
        print(
            f"  {g.label[: label_w - 1]:{label_w}}{g.total:15.6f}"
            f"{g.count:10d}{g.total / g.count * 1000:12.3f}{s.pct(g.total):9.2f}%"
        )
    if have_top:
        print(
            f"  {'(finish, after last emission)':{label_w}}{s.finish:15.6f}"
            f"{'':10}{'':12}{s.pct(s.finish):9.2f}%"
        )
    print("-" * width)
    print(
        f"  {'(total outside events)':{label_w}}{s.outside_events:15.6f}"
        f"{'':10}{'':12}{s.pct(s.outside_events):9.2f}%"
    )
    if s.overlaps:
        print(
            f"  WARNING: {s.overlaps} negative gaps -- top-level emissions "
            "overlap, so these timings are unreliable"
        )
