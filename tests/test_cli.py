import json
import pytest
from sphinx_benchmark.cli import main
from sphinx_benchmark.summary import compute_summary


SAMPLE = {
    "project_info": {
        "name": "proj",
        "version": "1.0",
        "copyright": "2026, Someone",
        "HEAD": "abc123",
    },
    "build_info": {
        "builder": "html",
        "start_time": "2026-01-01 00:00:00 UTC",
        "total_wall_time": 10.0,
    },
    "calls": [
        {
            "event": "builder-inited",
            "handler": "gen_gallery",
            "module": "sphinx_gallery",
            "kind": "extension",
            "extension": "sphinx_gallery.gen_gallery",
            "call": 1,
            "start": 0.5,
            "duration": 4.0,
        },
        {
            "event": "doctree-read",
            "handler": "process_docs",
            "module": "sphinx.ext.autodoc",
            "kind": "sphinx-internal",
            "extension": None,
            "call": 1,
            "start": 5.2,
            "duration": 0.5,
        },
        {
            "event": "doctree-read",
            "handler": "process_docs",
            "module": "sphinx.ext.autodoc",
            "kind": "sphinx-internal",
            "extension": None,
            "call": 2,
            "start": 6.0,
            "duration": 0.7,
        },
    ],
    "events": [
        {
            "event_id": 0,
            "event_name": "builder-inited",
            "call": 1,
            "start": 0.5,
            "depth": 0,
            "duration": 4.5,
            "parent_id": None,
            "own_time": 4.2,
        },
        {
            "event_id": 1,
            "event_name": "env-updated",
            "call": 1,
            "start": 0.6,
            "depth": 1,
            "duration": 0.3,
            "parent_id": 0,
            "own_time": 0.3,
        },
        {
            "event_id": 2,
            "event_name": "doctree-read",
            "call": 1,
            "start": 5.2,
            "depth": 0,
            "duration": 1.5,
            "parent_id": None,
            "own_time": 1.5,
        },
        # still-in-progress emission (build-finished): must be skipped
        {
            "event_id": 3,
            "event_name": "build-finished",
            "call": 1,
            "start": 9.0,
            "depth": 0,
            "duration": None,
            "parent_id": None,
            "own_time": None,
        },
    ],
}


def test_compute_summary_aggregates():
    s = compute_summary(SAMPLE)
    assert s.total_build_time == 10.0
    # own times: 4.2 + 0.3 + 1.5 (build-finished skipped)
    assert s.time_in_events == pytest.approx(6.0)
    assert [ev.name for ev in s.events] == [
        "builder-inited",
        "doctree-read",
        "env-updated",
    ]
    assert s.events[0].has_nested is True
    doctree = s.events[1]
    assert doctree.handlers[0].calls == 2
    assert doctree.handlers[0].total == pytest.approx(1.2)
    # one gap between the two top-level emissions: 5.2 - (0.5 + 4.5) = 0.2
    assert s.gaps[0].label == "builder-inited -> doctree-read"
    assert s.gaps[0].total == pytest.approx(0.2)
    assert s.startup == pytest.approx(0.5)
    assert s.overlaps == 0


def test_run_table_and_html(tmp_path, capsys):
    json_path = tmp_path / "sphinx_benchmarks.json"
    json_path.write_text(json.dumps(SAMPLE))

    assert main(["run", "table", "-i", str(json_path)]) == 0
    out = capsys.readouterr().out
    assert "builder-inited" in out and "Gaps Summary" in out
    assert "Project: proj 1.0  |  HEAD: abc123" in out
    assert "Builder: html  |  Started: 2026-01-01 00:00:00 UTC" in out
    assert "Someone" not in out  # copyright is not printed

    report = tmp_path / "report"
    assert main(["run", "html", "-i", str(json_path), "-o", str(report)]) == 0
    for name in ("index.html", "events.html", "gaps.html", "style.css", "report.js"):
        assert (report / name).exists()
    index = (report / "index.html").read_text()
    assert "conic-gradient" in index
    assert '<span class="project">proj 1.0</span>' in index
    assert "abc123" in index and "2026-01-01 00:00:00 UTC" in index
    assert "Someone" not in index  # copyright is not printed
    assert '<span class="project">proj 1.0</span>' in (report / "gaps.html").read_text()


def test_run_default_overview(tmp_path, capsys):
    json_path = tmp_path / "sphinx_benchmarks.json"
    json_path.write_text(json.dumps(SAMPLE))

    # bare 'run' prints the overview (top 10 by default) without 'gap: ' prefixes
    assert main(["run", "-i", str(json_path)]) == 0
    out = capsys.readouterr().out
    assert "Overview" in out
    assert "builder-inited -> doctree-read" in out
    assert "gap: " not in out
    assert "Inside events: 6.000000s (60.00%)" in out
    assert "Outside events (gaps): 4.000000s (40.00%)" in out
    # footer shows full-build totals: events 4.2+1.5+0.3, gaps 3.3+0.5+0.2
    assert "events total" in out and "gaps total" in out
    # sorted descending: builder-inited (4.2s) before doctree-read (1.5s)
    assert out.index("builder-inited") < out.index("doctree-read")

    # --top limits the rows: top 2 are builder-inited (4.2s) and finish (3.3s)
    assert main(["run", "--top", "2", "-i", str(json_path)]) == 0
    out = capsys.readouterr().out
    assert "Top 2 of" in out
    assert "builder-inited" in out and "doctree-read" not in out
    assert "use --top N to show more" in out

    # --top only makes sense for the bare overview
    with pytest.raises(SystemExit):
        main(["run", "table", "--top", "2", "-i", str(json_path)])
    assert "--top is only valid" in capsys.readouterr().err


def test_table_selectors(tmp_path, capsys):
    json_path = tmp_path / "sphinx_benchmarks.json"
    json_path.write_text(json.dumps(SAMPLE))

    def run(*selector):
        assert main(["run", "table", *selector, "-i", str(json_path)]) == 0
        return capsys.readouterr().out

    out = run("gaps")
    assert "Gaps Summary" in out and "builder-inited" in out

    out = run("events")
    assert "builder-inited" in out and "Gaps Summary" not in out

    # event detail: all emissions
    out = run("events", "builder-inited")
    assert "Emissions of 'builder-inited'" in out and "(top-level)" in out

    # handler detail across events
    out = run("events", "process_docs")
    assert "Calls of 'process_docs'" in out
    assert "doctree-read" in out  # the event column
    assert out.count("doctree-read") >= 2  # both calls listed

    # handler detail scoped to one event
    out = run("events", "builder-inited", "gen_gallery")
    assert "Calls of 'gen_gallery' during 'builder-inited'" in out

    # gap occurrences between two events
    out = run("gaps", "builder-inited", "doctree-read")
    assert "Gaps between 'builder-inited' -> 'doctree-read'" in out
    assert "0.200000" in out


def test_table_unknown_name_suggests(tmp_path, capsys):
    json_path = tmp_path / "sphinx_benchmarks.json"
    json_path.write_text(json.dumps(SAMPLE))
    with pytest.raises(SystemExit):
        main(["run", "table", "events", "gen_galery", "-i", str(json_path)])
    err = capsys.readouterr().err
    assert "unknown event or handler" in err and "gen_gallery" in err


def test_html_detail_pages(tmp_path):
    json_path = tmp_path / "sphinx_benchmarks.json"
    json_path.write_text(json.dumps(SAMPLE))
    report = tmp_path / "report"
    assert main(["run", "html", "-i", str(json_path), "-o", str(report)]) == 0

    events_html = (report / "events.html").read_text()
    assert 'href="event-builder-inited.html"' in events_html
    assert 'href="handler-gen_gallery.html?event=builder-inited"' in events_html

    gaps_html = (report / "gaps.html").read_text()
    assert 'href="gap-builder-inited----doctree-read.html"' in gaps_html

    handler_page = (report / "handler-process_docs.html").read_text()
    assert 'id="event-filter"' in handler_page  # per-event dropdown
    assert "All events" in handler_page
    assert 'class="sortable"' in handler_page

    event_page = (report / "event-builder-inited.html").read_text()
    assert "1 recorded emissions" in event_page

    gap_page = (report / "gap-builder-inited----doctree-read.html").read_text()
    assert "1 occurrences" in gap_page and "0.200000" in gap_page


def test_html_long_handler_name(tmp_path):
    # e.g. a functools.partial repr used as a handler: its name can exceed
    # the filesystem's 255-byte filename limit unless the slug is truncated
    data = json.loads(json.dumps(SAMPLE))
    long_name = "functools.partial(<function setup at 0x10d4b7060>, " + " ".join(
        f"arg{i}=<class 'pkg.mod{i}.Thing{i}'>" for i in range(40)
    )
    data["calls"].append(
        {
            "event": "builder-inited",
            "handler": long_name,
            "module": "conf",
            "kind": "unknown",
            "extension": "conf",
            "call": 1,
            "start": 0.6,
            "duration": 0.1,
        }
    )
    json_path = tmp_path / "sphinx_benchmarks.json"
    json_path.write_text(json.dumps(data))
    report = tmp_path / "report"
    assert main(["run", "html", "-i", str(json_path), "-o", str(report)]) == 0
    handler_pages = [p.name for p in report.glob("handler-*.html")]
    assert len(handler_pages) == 3
    assert all(len(name) < 120 for name in handler_pages)
    # the events page links to the truncated filename
    long_page = next(p for p in handler_pages if "functools" in p)
    assert f'href="{long_page}' in (report / "events.html").read_text()


def test_missing_file_exits_with_message(tmp_path):
    with pytest.raises(SystemExit, match="not found"):
        main(["run", "table", "-i", str(tmp_path / "nope.json")])
