import json
import re
import time
import types
import pytest
from sphinx.application import Sphinx
from sphinx.events import EventListener
from sphinx.extension import Extension
import sphinx_benchmark.extension as bs
from sphinx_benchmark.extension import (
    EventLogger,
    _WRAP_FLAG,
    recorder,
    wrap_all_listeners,
    wrap_connect,
    wrap_emit,
    wrap_listener,
)

SLEEP = 0.5


# dummy stuff and fixtures


class DummyEventManager:
    def __init__(self, app):
        self.app = app
        self.listeners: dict[str, list[EventListener]] = {}
        self._next_id = 0

    def connect(self, name, callback, priority=500):
        listener = EventListener(self._next_id, callback, priority)
        self._next_id += 1
        self.listeners.setdefault(name, []).append(listener)
        return listener.id

    def emit(self, name, *args, **kwargs):
        return [
            listener.handler(self.app, *args, **kwargs)
            for listener in self.listeners.get(name, [])
        ]


class DummyApp:
    def __init__(self):
        self.events = DummyEventManager(self)
        self.extensions: dict[str, Extension] = {}

    def add_extension(self, name: str) -> None:
        self.extensions[name] = Extension(name, types.ModuleType(name))


@pytest.fixture
def app():
    return DummyApp()


@pytest.fixture(autouse=True)
def fresh_recorder():
    """The wrappers write to the module-level ``recorder``, so reset it before every test."""
    recorder.start()


@pytest.fixture
def log():
    """A standalone EventLogger, for tests that don't go through the wrappers."""
    logger = EventLogger()
    logger.start()
    return logger


def dummy_handler(app, *args, **kwargs):
    """A handler that takes a measurable amount of time."""
    time.sleep(SLEEP)


# wrapping a listener should be invisible to Sphinx and to the handler


def test_wrapped_listener():
    original = EventListener(7, dummy_handler, 42)
    wrapped = wrap_listener("build-finished", original)

    assert wrapped.id == original.id
    assert wrapped.priority == original.priority
    assert wrapped.handler is not original.handler
    assert wrapped.handler.__qualname__ == dummy_handler.__qualname__
    assert wrapped.handler.__module__ == dummy_handler.__module__


def test_wrapped_handler(app):
    seen = {}

    def handler(app_arg, docname, source):
        seen.update(app=app_arg, docname=docname, source=source)
        return {"ok": True}

    wrapped = wrap_listener("source-read", EventListener(0, handler, 500))

    result = wrapped.handler(app, "index", source=["blah blah"])

    assert result == {"ok": True}
    assert seen == {"app": app, "docname": "index", "source": ["blah blah"]}


def test_listeners_wrapped_once(app):
    app.events.connect("builder-inited", dummy_handler)

    wrap_all_listeners(app)
    first_wrapper = app.events.listeners["builder-inited"][0].handler
    assert getattr(first_wrapper, _WRAP_FLAG, False) is True

    wrap_all_listeners(app)
    assert app.events.listeners["builder-inited"][0].handler is first_wrapper

    app.events.emit("builder-inited")
    assert len(recorder.calls) == 1


def test_handler_connected_after_setup_gets_wrapped(app):
    wrap_connect(app)

    app.events.connect("source-read", dummy_handler)
    app.events.emit("source-read")

    assert [c.handler for c in recorder.calls] == ["dummy_handler"]


# testing durations and timings


def test_handler_duration_and_start(app):
    app.events.connect("builder-inited", dummy_handler)
    wrap_all_listeners(app)

    app.events.emit("builder-inited")

    (call,) = recorder.calls
    build_time = time.perf_counter() - recorder.start_time
    assert call.duration >= SLEEP
    assert call.start >= 0
    assert call.start + call.duration <= build_time


def test_repeated_calls_are_counted_per_event_and_handler(app):
    app.events.connect("source-read", dummy_handler)
    app.events.connect("doctree-read", dummy_handler)
    wrap_all_listeners(app)

    app.events.emit("source-read")
    app.events.emit("source-read")
    app.events.emit("doctree-read")

    assert [(c.event, c.call) for c in recorder.calls] == [
        ("source-read", 1),
        ("source-read", 2),
        ("doctree-read", 1),
    ]


def test_nested_emissions_record_parent_depth_and_own_time(app):
    def outer(app_arg):
        app_arg.events.emit("inner")

    def inner(app_arg):
        time.sleep(SLEEP)

    app.events.connect("outer", outer)
    app.events.connect("inner", inner)
    wrap_emit(app)

    app.events.emit("outer")

    outer_rec, inner_rec = recorder.events
    assert (outer_rec.event_name, outer_rec.depth, outer_rec.parent_id) == (
        "outer",
        0,
        None,
    )
    assert (inner_rec.event_name, inner_rec.depth, inner_rec.parent_id) == (
        "inner",
        1,
        outer_rec.event_id,
    )
    assert outer_rec.duration >= inner_rec.duration >= SLEEP

    recorder.compute_own_times()
    assert inner_rec.own_time == pytest.approx(inner_rec.duration)
    assert outer_rec.own_time == pytest.approx(outer_rec.duration - inner_rec.duration)


# testing classification and output


def test_classify_all_handlers(app, log, monkeypatch):
    monkeypatch.setattr(bs, "THEME_PACKAGES", {"pydata_sphinx_theme"})
    app.add_extension("sphinx_gallery.gen_gallery")

    expected = {
        "sphinx.builders.html": ("sphinx-internal", None),
        "sphinx.ext.intersphinx": ("extension", "sphinx.ext.intersphinx"),
        "sphinx.ext.autodoc.typehints": ("extension", "sphinx.ext.autodoc"),
        "sphinx_gallery.gen_gallery": ("extension", "sphinx_gallery.gen_gallery"),
        "sphinx_gallery.interactive_example": (
            "extension",
            "sphinx_gallery.gen_gallery",
        ),
        "pydata_sphinx_theme.toctree": ("theme", "pydata_sphinx_theme"),
        "conf.py": ("unknown", "conf"),
    }
    for module in expected:
        log.record("builder-inited", f"handler_in_{module}", module, 0.0, 0.1)

    log.classify_all_handlers(app)

    assert {c.module: (c.kind, c.extension) for c in log.calls} == expected


def test_write_json(log, tmp_path):
    log.record("source-read", "handler", "some_ext", 0.5, 0.25)
    log.enter_event("source-read")
    log.exit_event()
    out = tmp_path / "bench.json"
    project_info = {"name": "proj", "version": "1.0", "copyright": "me", "HEAD": None}
    build_info = {
        "builder": "html",
        "start_time": "2026-01-01 00:00:00 UTC",
        "total_wall_time": 12.5,
    }

    log.write_json(project_info, build_info, str(out))
    data = json.loads(out.read_text())

    assert set(data) == {"project_info", "build_info", "calls", "events"}
    assert data["project_info"] == project_info
    assert data["build_info"] == build_info
    assert data["calls"][0]["handler"] == "handler"
    assert data["calls"][0]["duration"] == 0.25
    assert data["events"][0]["event_name"] == "source-read"


def test_starts_fresh_build(log):
    log.record("source-read", "handler", "some_ext", 0.0, 0.1)
    log.enter_event("source-read")
    log.exit_event()

    log.start()

    assert log.calls == []
    assert log.events == []
    assert log.call_counts == {}
    assert log.event_call_counts == {}


# end-to-end smoke test on a dummy Sphinx build


def test_real_build_benchmarks(tmp_path, monkeypatch):
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(
        "project = 'proj'\nextensions = ['sphinx_benchmark']\n"
    )
    (srcdir / "index.rst").write_text("Title\n=====\n\nblah blah blah blah\n")
    outdir = tmp_path / "out"

    monkeypatch.chdir(tmp_path)
    app = Sphinx(
        str(srcdir),
        str(srcdir),
        str(outdir),
        str(outdir / ".doctrees"),
        "html",
        status=None,
        freshenv=True,
    )
    app.build()

    # sphinx_benchmarks_<date>-<time>[_<short HEAD>].json
    (json_path,) = tmp_path.glob("sphinx_benchmarks_*.json")
    assert re.fullmatch(
        r"sphinx_benchmarks_\d{8}-\d{6}(_[0-9a-f]{7})?\.json", json_path.name
    )
    data = json.loads(json_path.read_text())

    assert data["build_info"]["total_wall_time"] > 0
    assert data["build_info"]["builder"] == "html"
    assert data["build_info"]["start_time"]
    assert data["project_info"]["name"] == "proj"
    assert "HEAD" in data["project_info"]
    assert data["calls"] and data["events"]
    assert {"builder-inited", "build-finished"} <= {
        e["event_name"] for e in data["events"]
    }
    assert all(c["kind"] != "unknown" or c["extension"] for c in data["calls"])
    assert any(c["kind"] == "sphinx-internal" for c in data["calls"])
