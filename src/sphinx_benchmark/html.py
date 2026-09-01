"""HTML output: writes a small static report from a :class:`BuildSummary`.

The output directory gets three top-level pages plus one detail page per
event, per handler, and per gap pair, and the shared assets:

- ``index.html``    : overview with a pie chart of build % (events' own time and the gaps between them, labels in descending order)
- ``events.html``   : handler-breakdown table per event
- ``gaps.html``     : the gaps summary table
- ``event-*.html``  : every emission of one event
- ``handler-*.html``: every call of one handler, filterable by event
- ``gap-*.html``    : every individual gap between one pair of events
- ``style.css``, ``report.js``

Every event name, handler name and gap in the tables is a hyperlink to
its detail page, and all tables can be re-sorted by clicking a column
heading (the arrows show the current sort direction).
"""

from __future__ import annotations

import hashlib
import os
import re
from html import escape
from urllib.parse import quote

from .summary import (
    BuildSummary,
    all_emission_details,
    all_gap_occurrence_details,
    all_handler_call_details,
    event_names,
    handler_names,
)

#: What each column means; shown in the "i" tooltip on column headings.
COLUMN_HELP = {
    "Handler": "Qualified name of the event handler function.",
    "Kind": "Where the handler comes from: extension, sphinx-internal, theme, or unknown.",
    "Ext/Module": "Origin package: extension or theme name, or the top-level module for unknown handlers.",
    "Module": "Full module path where the handler function is defined.",
    "Calls": "Number of times this handler ran for this event.",
    "Total(s)": "Summed execution time over all calls, in seconds.",
    "Avg(ms)": "Total divided by Calls, in milliseconds.",
    "Between": "The two consecutive top-level emissions this gap falls between.",
    "Gap Total(s)": "Summed duration of all gaps between the 2 events, in seconds.",
    "Count": "Number of times this pair of emissions occurred consecutively.",
    "Avg Gap(ms)": "Gap Total divided by Count, in milliseconds.",
    "% build": "Share of the total wall-clock build time.",
    "Event": "Name of the event this handler call was made from.",
    "Call#": "Sequence number of this emission/call (1 for the first, and so on).",
    "Start(s)": "Seconds since the start of the build at which this began.",
    "Depth": "Nesting level: 0 is a top-level emission, 1 was emitted from inside another emission, and so on.",
    "Duration(s)": "How long this took, in seconds.",
    "Own(s)": "Duration excluding nested event emissions, in seconds.",
    "Parent event": "The emission this one was nested inside, or (top-level).",
    "#": "Chronological number of this gap occurrence.",
    "Source call#": "Call number of the source event's emission before the gap.",
    "Target call#": "Call number of the target event's emission after the gap.",
    "Gap start(s)": "Seconds since build start at which the source emission ended.",
    "Gap end(s)": "Seconds since build start at which the target emission began.",
}

#: Slice colours for the pie chart, cycled if there are more slices.
PALETTE = [
    "#155e63",
    "#c26a2a",
    "#5a4fa2",
    "#2e7d4f",
    "#a83a5a",
    "#946200",
    "#3a6ea5",
    "#7a5230",
    "#4f7d7d",
    "#8a4fa2",
    "#6b7d2e",
    "#a25a4f",
]

_PAGES = [("index.html", "Overview"), ("events.html", "Events"), ("gaps.html", "Gaps")]


# ------------------------------------------------------------------- links --


#: Longest slug used in a detail-page filename. Handler names can be huge
#: (e.g. the repr of a functools.partial), and most filesystems cap a file
#: name at 255 bytes, so anything longer is truncated and disambiguated
#: with a short hash of the full name.
_MAX_SLUG = 80


def _slug(text: str) -> str:
    """Make ``text`` safe for use in a filename."""
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", text).strip("-").lower() or "x"
    if len(slug) > _MAX_SLUG:
        digest = hashlib.sha1(text.encode()).hexdigest()[:8]
        slug = f"{slug[:_MAX_SLUG].rstrip('-.')}-{digest}"
    return slug


def _unique_files(prefix: str, names: set[str]) -> dict[str, str]:
    """Map each name to a unique ``<prefix>-<slug>.html`` filename."""
    files: dict[str, str] = {}
    used: set[str] = set()
    for name in sorted(names):
        base = f"{prefix}-{_slug(name)}"
        fname, i = base + ".html", 2
        while fname in used:
            fname, i = f"{base}-{i}.html", i + 1
        used.add(fname)
        files[name] = fname
    return files


class _Links:
    """Filenames of the detail pages, keyed by event/handler/gap-pair name."""

    def __init__(self, data: dict, s: BuildSummary) -> None:
        self.events = _unique_files("event", event_names(data))
        self.handlers = _unique_files("handler", handler_names(data))
        self.gaps = _unique_files("gap", {f"{g.source} --> {g.target}" for g in s.gaps})
        self.gap_pairs = {
            (g.source, g.target): self.gaps[f"{g.source} --> {g.target}"]
            for g in s.gaps
        }

    def event_a(self, name: str) -> str:
        """An ``<a>`` to the event's detail page (or plain text if unknown)."""
        fname = self.events.get(name)
        if not fname:
            return escape(name)
        return f'<a href="{fname}">{escape(name)}</a>'

    def handler_a(self, name: str, event: str | None = None) -> str:
        """An ``<a>`` to the handler's detail page, optionally pre-filtered."""
        fname = self.handlers.get(name)
        if not fname:
            return escape(name)
        if event:
            fname += "?event=" + quote(event)
        return f'<a href="{fname}">{escape(name)}</a>'

    def gap_a(self, source: str, target: str, label: str) -> str:
        """An ``<a>`` to the gap pair's detail page (or plain text)."""
        fname = self.gap_pairs.get((source, target))
        if not fname:
            return escape(label)
        return f'<a href="{fname}">{escape(label)}</a>'


# ------------------------------------------------------------------- cells --


def _th(name: str) -> str:
    """Return a ``<th>`` with an "i" info button that explains the column on hover."""
    tip = escape(COLUMN_HELP.get(name, ""))
    return (
        f'<th>{escape(name)} <span class="info" tabindex="0">i'
        f'<span class="tip">{tip}</span></span></th>'
    )


def _num_td(v: float | None, fmt: str = "{:.6f}", suffix: str = "") -> str:
    """A right-aligned numeric ``<td>`` with a machine-sortable value."""
    if v is None:
        return "<td class='num' data-sort='-1'>-</td>"
    return f"<td class='num' data-sort='{v!r}'>{fmt.format(v)}{suffix}</td>"


def _page(title: str, current: str, body: str, s: BuildSummary) -> str:
    """Wrap ``body`` in the shared page shell (head, nav bar, footer)."""
    nav = "".join(
        f'<a href="{fname}"{' class="current"' if fname == current else ""}>{label}</a>'
        for fname, label in _PAGES
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — sphinx-benchmark</title>
<link rel="stylesheet" href="style.css">
<script src="report.js" defer></script>
</head>
<body>
<header>
  <span class="brand">sphinx-benchmark</span>
  <nav>{nav}</nav>
  <span class="wall">wall clock {s.total_build_time:.3f}s</span>
</header>
<main>
{body}
</main>
<footer>Generated by sphinx-benchmark from sphinx_benchmarks.json</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- overview --


def _pie_slices(s: BuildSummary, links: _Links) -> list[tuple[str, float, str | None]]:
    """Return ``(label, seconds, detail-page filename)`` slices, descending.

    Slices are the events' own times plus the time outside events
    (startup, each gap pair, finish). Slices below 1% of the build are
    grouped into one "everything else" slice to keep the chart readable.
    """
    items: list[tuple[str, float, str | None]] = [
        (ev.name, ev.own_time, links.events.get(ev.name)) for ev in s.events
    ]
    items += [("gap: (startup)", s.startup, None), ("gap: (finish)", s.finish, None)]
    items += [
        (f"gap: {g.label}", g.total, links.gap_pairs.get((g.source, g.target)))
        for g in s.gaps
    ]

    items = [it for it in items if it[1] > 0]
    items.sort(key=lambda it: it[1], reverse=True)

    big = [it for it in items if s.pct(it[1]) >= 1.0]
    rest = sum(sec for _, sec, _ in items) - sum(sec for _, sec, _ in big)
    if rest > 0:
        big.append(("everything else (< 1% each)", rest, None))
    return big


def _overview_body(s: BuildSummary, links: _Links) -> str:
    slices = _pie_slices(s, links)
    stops, legend, acc = [], [], 0.0
    for i, (label, sec, href) in enumerate(slices):
        colour = PALETTE[i % len(PALETTE)]
        start, acc = acc, acc + s.pct(sec)
        # clamp both ends: decreasing stop positions are invalid CSS
        stops.append(f"{colour} {min(start, 100):.3f}% {min(acc, 100):.3f}%")
        text = f'<a href="{href}">{escape(label)}</a>' if href else escape(label)
        legend.append(
            f'<li><span class="swatch" style="background:{colour}"></span>'
            f'{text}<span class="num">{sec:.3f}s · {s.pct(sec):.2f}%</span></li>'
        )
    if acc < 100:  # rounding / unattributed remainder
        stops.append(f"#d9d9d9 {acc:.3f}% 100%")

    outside_pct = s.pct(s.total_build_time - s.time_in_events)
    body = f"""
<h1>Where the build time went</h1>
<div class="stats">
  <div><b>{s.total_build_time:.3f}s</b> wall clock</div>
  <div><b>{s.time_in_events:.3f}s</b> inside events (own time) ({s.pct(s.time_in_events):.2f}%)</div>
  <div><b>{s.total_build_time - s.time_in_events:.3f}s</b> outside any event ({outside_pct:.2f}%)</div>
</div>
<div class="pie-wrap">
  <div class="pie" style="background: conic-gradient({", ".join(stops)})"
       role="img" aria-label="Pie chart of build time share"></div>
  <ol class="legend">{"".join(legend)}</ol>
</div>
<p class="note">Slices are each event's <i>own</i> time (nested emissions excluded)
plus the gaps between top-level emissions, where Sphinx-core work such as
parsing and writing happens. See <a href="events.html">Events</a> and
<a href="gaps.html">Gaps</a> for the full tables; every name is a link to
its detailed breakdown.</p>
"""
    if s.overlaps:
        body += (
            f'<p class="warn">WARNING: {s.overlaps} negative gaps -- top-level '
            "emissions overlap, so these timings are unreliable</p>"
        )
    return body


# ------------------------------------------------------------------ events --


def _events_body(s: BuildSummary, links: _Links) -> str:
    header = "".join(
        _th(n)
        for n in ("Handler", "Kind", "Ext/Module", "Calls", "Total(s)", "Avg(ms)")
    )
    parts = [
        "<h1>Events &amp; handlers</h1> <p class='meta'>Note that the `unaccounted overhead` is `event_duration - sum_of_handlers` i.e. the time inside an event's `emit()` but outside any handler.</p><p class='meta'>The `depth` represents the nesting of events. `depth 0` means a top-level event emission. `depth 1` means emission happened from inside another event emission. And `depth 0-1` means that the event was a top-level event as well as a child event during the build process.</p><p class='meta'>Lastly, the `duration incl. nested events` is only displayed for events that had internal event emissions, and the `own_time` is the `duration_of_the_event - durations_of_child_events`</p>"
    ]
    for ev in s.events:
        depth = (
            str(ev.depth_min)
            if ev.depth_min == ev.depth_max
            else f"{ev.depth_min}–{ev.depth_max}"
        )
        nested = (
            f" · {ev.duration:.6f}s duration incl. nested events"
            if ev.has_nested
            else ""
        )
        rows = "".join(
            f"<tr><td>{links.handler_a(r.handler, ev.name)}</td><td>{escape(r.kind)}</td>"
            f"<td>{escape(r.extension)}</td>{_num_td(r.calls, '{:d}')}"
            f"{_num_td(r.total)}{_num_td(r.avg * 1000, '{:.3f}')}</tr>"
            for r in ev.handlers
        )
        parts.append(f"""
<section>
<h2>{links.event_a(ev.name)}</h2>
<p class="meta">{ev.own_time:.6f}s own time ({s.pct(ev.own_time):.2f}% of build)
 · {ev.emissions} emissions{nested} · depth {depth}</p>
<table class="sortable">
<thead><tr>{header}</tr></thead>
<tbody>{rows}
<tr class="total"><td>(sum of handlers)</td><td></td><td></td><td></td>
<td class="num">{ev.handler_sum:.6f}</td><td></td></tr>
<tr class="total"><td>(unaccounted overhead)</td><td></td><td></td><td></td>
<td class="num">{ev.overhead:.6f}</td><td></td></tr>
</tbody>
</table>
</section>""")
    return "".join(parts)


# -------------------------------------------------------------------- gaps --


def _gaps_body(s: BuildSummary, links: _Links) -> str:
    header = "".join(
        _th(n) for n in ("Between", "Gap Total(s)", "Count", "Avg Gap(ms)", "% build")
    )

    def row(label_html: str, total: float, count: int | None) -> str:
        count_td = _num_td(count, "{:d}") if count is not None else "<td></td>"
        avg_td = _num_td(total / count * 1000, "{:.3f}") if count else "<td></td>"
        return (
            f"<tr><td>{label_html}</td>{_num_td(total)}"
            f"{count_td}{avg_td}"
            f"{_num_td(s.pct(total), '{:.2f}', '%')}</tr>"
        )

    rows = [row("(startup, before first emission)", s.startup, None)]
    rows += [
        row(links.gap_a(g.source, g.target, g.label), g.total, g.count) for g in s.gaps
    ]
    rows.append(row("(finish, after last emission)", s.finish, None))
    body = f"""
<h1>Gaps between emissions</h1>
<p class="meta">Sphinx emits events at fixed points in the build; the work between
two emissions (parsing, writing output) is not inside emit() and so is not
recorded per handler. These rows account for that time.</p>
<table class="sortable">
<thead><tr>{header}</tr></thead>
<tbody>{"".join(rows)}
<tr class="total"><td>(total outside events)</td>
<td class="num">{s.outside_events:.6f}</td><td></td><td></td>
<td class="num">{s.pct(s.outside_events):.2f}%</td></tr>
</tbody>
</table>
"""
    if s.overlaps:
        body += (
            f'<p class="warn">WARNING: {s.overlaps} negative gaps -- top-level '
            "emissions overlap, so these timings are unreliable</p>"
        )
    return body


# ----------------------------------------------------------- detail pages --


def _event_page_body(name: str, rows: tuple, s: BuildSummary, links: _Links) -> str:
    header = "".join(
        _th(n)
        for n in (
            "Call#",
            "Start(s)",
            "Depth",
            "Parent event",
            "Duration(s)",
            "Own(s)",
            "% build",
        )
    )
    body_rows = []
    for r in rows:
        parent = links.event_a(r.parent_name) if r.parent_name else "(top-level)"
        pct = s.pct(r.own_time) if r.own_time is not None else None
        body_rows.append(
            f"<tr>{_num_td(r.call, '{:d}')}{_num_td(r.start)}"
            f"{_num_td(r.depth, '{:d}')}<td>{parent}</td>"
            f"{_num_td(r.duration)}{_num_td(r.own_time)}"
            f"{_num_td(pct, '{:.2f}', '%')}</tr>"
        )
    total_own = sum(r.own_time for r in rows if r.own_time is not None)
    in_progress = (
        "<p class='meta'>'-' marks an emission still in progress when the JSON "
        "was written (e.g. build-finished).</p>"
        if any(r.duration is None for r in rows)
        else ""
    )
    return f"""
<p class="backlink"><a href="events.html">← all events</a></p>
<h1>Event: {escape(name)}</h1>
<p class="meta">{len(rows)} recorded emissions · {total_own:.6f}s own time
 ({s.pct(total_own):.2f}% of build). Click a column heading to sort.</p>
<table class="sortable">
<thead><tr>{header}</tr></thead>
<tbody>{"".join(body_rows)}
<tr class="total"><td>(total)</td><td></td><td></td><td></td><td></td>
<td class="num">{total_own:.6f}</td>
<td class="num">{s.pct(total_own):.2f}%</td></tr>
</tbody>
</table>
{in_progress}"""


def _handler_page_body(name: str, rows: tuple, s: BuildSummary, links: _Links) -> str:
    # default order: biggest share of the build first
    rows = tuple(sorted(rows, key=lambda r: r.duration, reverse=True))
    from_events = sorted({r.event for r in rows})
    options = '<option value="">All events</option>' + "".join(
        f'<option value="{escape(ev, quote=True)}">{escape(ev)}</option>'
        for ev in from_events
    )
    header_names = (
        "Event",
        "Call#",
        "Start(s)",
        "Duration(s)",
        "% build",
        "Kind",
        "Ext/Module",
        "Module",
    )
    header = "".join(
        # pre-mark the default sort column so its arrow shows
        _th(n).replace("<th>", '<th data-dir="desc">', 1)
        if n == "Duration(s)"
        else _th(n)
        for n in header_names
    )
    body_rows = "".join(
        f'<tr data-event="{escape(r.event, quote=True)}">'
        f"<td>{links.event_a(r.event)}</td>{_num_td(r.call, '{:d}')}"
        f"{_num_td(r.start)}{_num_td(r.duration)}"
        f"{_num_td(s.pct(r.duration), '{:.2f}', '%')}"
        f"<td>{escape(r.kind)}</td><td>{escape(r.extension)}</td>"
        f"<td>{escape(r.module)}</td></tr>"
        for r in rows
    )
    total = sum(r.duration for r in rows)
    return f"""
<p class="backlink"><a href="events.html">← all events</a></p>
<h1>Handler: {escape(name)}</h1>
<p class="meta">{len(rows)} recorded calls across {len(from_events)} event(s)
 · {total:.6f}s total ({s.pct(total):.2f}% of build). Rows are ordered by
duration (share of build) descending; click a column heading to re-sort.</p>
<p class="filter"><label>Show calls from event:
<select id="event-filter">{options}</select></label></p>
<p class="meta" id="filter-summary" hidden></p>
<noscript><p class="meta">Filtering and sorting require JavaScript; all
calls are shown.</p></noscript>
<table class="sortable">
<thead><tr>{header}</tr></thead>
<tbody>{body_rows}
<tr class="total"><td>(total, all events)</td><td></td><td></td>
<td class="num">{total:.6f}</td>
<td class="num">{s.pct(total):.2f}%</td><td></td><td></td><td></td></tr>
</tbody>
</table>"""


def _gap_page_body(
    source: str, target: str, rows: tuple, s: BuildSummary, links: _Links
) -> str:
    header = "".join(
        _th(n)
        for n in (
            "#",
            "Source call#",
            "Target call#",
            "Gap start(s)",
            "Gap end(s)",
            "Duration(s)",
            "% build",
        )
    )
    body_rows = "".join(
        f"<tr>{_num_td(i, '{:d}')}{_num_td(r.source_call, '{:d}')}"
        f"{_num_td(r.target_call, '{:d}')}{_num_td(r.start)}{_num_td(r.end)}"
        f"{_num_td(r.duration)}{_num_td(s.pct(r.duration), '{:.2f}', '%')}</tr>"
        for i, r in enumerate(rows, 1)
    )
    total = sum(r.duration for r in rows)
    return f"""
<p class="backlink"><a href="gaps.html">← all gaps</a></p>
<h1>Gap: {links.event_a(source)} → {links.event_a(target)}</h1>
<p class="meta">{len(rows)} occurrences · {total:.6f}s total
 ({s.pct(total):.2f}% of build). Click a column heading to sort.</p>
<table class="sortable">
<thead><tr>{header}</tr></thead>
<tbody>{body_rows}
<tr class="total"><td>(total)</td><td></td><td></td><td></td><td></td>
<td class="num">{total:.6f}</td>
<td class="num">{s.pct(total):.2f}%</td></tr>
</tbody>
</table>"""


# ------------------------------------------------------------------- write --


def write_report(s: BuildSummary, out_dir: str, data: dict) -> str:
    """Write the report into ``out_dir`` and return that path.

    Parameters
    ----------
    s : BuildSummary
        The aggregated build data to render.
    out_dir : str
        Directory to write the pages and assets into. Created if missing.
    data : dict
        The raw benchmarks JSON, used for the per-event, per-handler and
        per-gap detail pages.
    """
    os.makedirs(out_dir, exist_ok=True)
    links = _Links(data, s)

    def write(fname: str, content: str) -> None:
        with open(os.path.join(out_dir, fname), "w") as f:
            f.write(content)

    write("index.html", _page("Overview", "index.html", _overview_body(s, links), s))
    write("events.html", _page("Events", "events.html", _events_body(s, links), s))
    write("gaps.html", _page("Gaps", "gaps.html", _gaps_body(s, links), s))
    write("style.css", _STYLE)
    write("report.js", _REPORT_JS)
    # group the raw records once; each detail page then renders its own rows
    emissions = all_emission_details(data)
    for name, fname in links.events.items():
        body = _event_page_body(name, emissions.get(name, ()), s, links)
        write(fname, _page(f"Event {name}", "events.html", body, s))
    calls = all_handler_call_details(data)
    for name, fname in links.handlers.items():
        body = _handler_page_body(name, calls.get(name, ()), s, links)
        write(fname, _page(f"Handler {name}", "events.html", body, s))
    occurrences = all_gap_occurrence_details(data)
    for (source, target), fname in links.gap_pairs.items():
        body = _gap_page_body(
            source, target, occurrences.get((source, target), ()), s, links
        )
        write(fname, _page(f"Gap {source} → {target}", "gaps.html", body, s))
    return out_dir


_STYLE = """\
:root {
  --ink: #1c2222; --muted: #5c6a6a; --line: #d8dede;
  --bg: #fbfbf9; --panel: #ffffff; --accent: #155e63;
  --mono: "SF Mono", ui-monospace, "Cascadia Code", Consolas, monospace;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { display: flex; align-items: baseline; gap: 1.5rem; flex-wrap: wrap;
  padding: .8rem 1.5rem; border-bottom: 2px solid var(--accent); background: var(--panel); }
.brand { font-family: var(--mono); font-weight: 700; color: var(--accent); }
nav a { margin-right: 1rem; color: var(--muted); text-decoration: none; }
nav a.current { color: var(--accent); font-weight: 600;
  border-bottom: 2px solid var(--accent); }
.wall { margin-left: auto; font-family: var(--mono); color: var(--muted); }
main { max-width: 70rem; margin: 0 auto; padding: 1.5rem; }
h1 { font-size: 1.5rem; } h2 { font-size: 1.1rem; margin: 2rem 0 .2rem;
  font-family: var(--mono); color: var(--accent); }
.meta, .note, .backlink { color: var(--muted); font-size: .9rem; }
.warn { color: #a83a3a; font-weight: 600; }
.stats { display: flex; gap: 2.5rem; flex-wrap: wrap; margin: 1rem 0;
  font-family: var(--mono); }
.stats b { font-size: 1.25rem; display: block; }
table { border-collapse: collapse; width: 100%; background: var(--panel);
  font-size: .85rem; }
th, td { padding: .35rem .6rem; border-bottom: 1px solid var(--line);
  text-align: left; }
th { border-bottom: 2px solid var(--ink); white-space: nowrap; }
td.num { text-align: right; font-family: var(--mono); }
td a, h2 a, .legend a { color: var(--accent); }
tr.total td { border-top: 2px solid var(--line); color: var(--muted); }
tbody tr:hover { background: #f1f5f4; }
/* click-to-sort column headings */
table.sortable th { cursor: pointer; -webkit-user-select: none; user-select: none; }
table.sortable th::after { content: " \\2195"; color: var(--muted); opacity: .45; }
table.sortable th[data-dir="asc"]::after { content: " \\2191"; color: var(--accent); opacity: 1; }
table.sortable th[data-dir="desc"]::after { content: " \\2193"; color: var(--accent); opacity: 1; }
.filter select { font: inherit; padding: .25rem .4rem; }
/* "i" info button with a hover/focus tooltip */
.info { position: relative; display: inline-block; width: 1.05em; height: 1.05em;
  line-height: 1.05em; text-align: center; border-radius: 50%;
  border: 1px solid var(--muted); color: var(--muted);
  font: italic 700 .7rem/1.35 Georgia, serif; cursor: help; }
.info .tip { display: none; position: absolute; left: 50%; top: 130%; z-index: 2;
  transform: translateX(-50%); width: 16rem; padding: .5rem .6rem;
  background: var(--ink); color: #fff; font: .78rem/1.4 system-ui, sans-serif;
  font-style: normal; border-radius: 4px; white-space: normal; }
.info:hover .tip, .info:focus .tip { display: block; }
/* pie */
.pie-wrap { display: flex; gap: 2.5rem; align-items: center; flex-wrap: wrap;
  margin: 1.5rem 0; }
.pie { width: 260px; height: 260px; border-radius: 50%;
  border: 1px solid var(--line); flex-shrink: 0; }
.legend { list-style: none; margin: 0; padding: 0; font-size: .85rem;
  max-width: 32rem; flex: 1; min-width: 18rem; }
.legend li { display: flex; align-items: baseline; gap: .5rem; padding: .15rem 0; }
.legend .num { margin-left: auto; font-family: var(--mono); color: var(--muted);
  white-space: nowrap; padding-left: 1rem; }
.swatch { width: .8rem; height: .8rem; border-radius: 2px; flex-shrink: 0;
  align-self: center; }
footer { text-align: center; color: var(--muted); font-size: .8rem;
  padding: 2rem 0; }
@media (max-width: 640px) { .wall { margin-left: 0; } main { padding: 1rem; } }
"""

_REPORT_JS = """\
// Click-to-sort for table.sortable and the per-handler event filter.
(function () {
  function cellKey(row, i) {
    var td = row.cells[i];
    if (!td) return "";
    var v = td.dataset.sort !== undefined ? td.dataset.sort : td.textContent.trim();
    // Number (not parseFloat) so "2captcha" stays text, not the number 2
    var n = v === "" ? NaN : Number(v);
    return !isNaN(n) ? n : v.toLowerCase();
  }
  function cmp(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }
  document.querySelectorAll("table.sortable").forEach(function (table) {
    var ths = table.querySelectorAll("thead th");
    ths.forEach(function (th, i) {
      th.addEventListener("click", function (ev) {
        if (ev.target.closest(".info")) return; // the "i" tooltip, not a sort
        var dir = th.dataset.dir === "desc" ? "asc" : "desc";
        ths.forEach(function (h) { h.removeAttribute("data-dir"); });
        th.dataset.dir = dir;
        var tbody = table.tBodies[0];
        var rows = Array.prototype.slice.call(tbody.rows);
        var totals = rows.filter(function (r) { return r.classList.contains("total"); });
        rows = rows.filter(function (r) { return !r.classList.contains("total"); });
        rows.sort(function (a, b) {
          var ka = cellKey(a, i), kb = cellKey(b, i);
          var na = typeof ka === "number", nb = typeof kb === "number";
          // numbers group above text/empty cells in both directions
          if (na !== nb) return na ? -1 : 1;
          return cmp(ka, kb) * (dir === "asc" ? 1 : -1);
        });
        rows.concat(totals).forEach(function (r) { tbody.appendChild(r); });
      });
    });
  });
  var sel = document.getElementById("event-filter");
  if (sel) {
    var note = document.getElementById("filter-summary");
    var apply = function () {
      var v = sel.value, count = 0, total = 0;
      document.querySelectorAll("tbody tr[data-event]").forEach(function (tr) {
        var show = v === "" || tr.dataset.event === v;
        tr.style.display = show ? "" : "none";
        if (show) {
          count += 1;
          total += Number(tr.cells[3].dataset.sort) || 0; // Duration(s) column
        }
      });
      if (note) {
        note.hidden = v === "";
        if (v !== "") {
          note.textContent = "Filtered: " + count + " call(s) during '" + v +
            "' \\u00b7 " + total.toFixed(6) + "s; the totals above cover all events.";
        }
      }
    };
    // links from the events page pre-select one event via ?event=...
    var pre = new URLSearchParams(location.search).get("event");
    if (pre) {
      for (var i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === pre) { sel.value = pre; break; }
      }
    }
    sel.addEventListener("change", apply);
    apply();
  }
})();
"""
