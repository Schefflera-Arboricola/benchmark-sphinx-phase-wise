import json
import pytest
from sphinx_benchmark.cli import main
from sphinx_benchmark.summary import compute_summary


SAMPLE = {
    "total_wall_time": 10.0,
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

    report = tmp_path / "report"
    assert main(["run", "html", "-i", str(json_path), "-o", str(report)]) == 0
    for name in ("index.html", "events.html", "gaps.html", "style.css"):
        assert (report / name).exists()
    assert "conic-gradient" in (report / "index.html").read_text()


def test_missing_file_exits_with_message(tmp_path):
    with pytest.raises(SystemExit, match="not found"):
        main(["run", "table", "-i", str(tmp_path / "nope.json")])
