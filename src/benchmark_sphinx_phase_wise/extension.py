from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Callable

from sphinx.application import Sphinx

# Some common theme packages
# todo: better way to identify themes
THEME_PACKAGES = {
    "alabaster",
    "sphinx_rtd_theme",
    "sphinx_book_theme",
    "furo",
    "pydata_sphinx_theme",
    "sphinx_material",
    "sphinx_immaterial",
}


@dataclass
class HandlerCall:
    """A single timed call of one event handler.

    One instance is created every time a wrapped handler finishes
    executing, so a handler connected to an event that emits many times
    (e.g. ``source-read``) produces one :class:`HandlerCall` per emitting.

    Parameters
    ----------
    event : str
        Name of the Sphinx event this handler function was connected to
        (e.g. ``"doctree-resolved"``).
    handler : str
        Qualified name of the handler function (``__qualname__``), used
        to identify it in benchmark summary.
    module : str
        Full module path (separated by '.') of where the handler function is defined.
    kind : str
        Classification of where the handler is coming from. Could be:
        ``"extension"``, ``"sphinx-internal"``, ``"theme"``, or
        ``"unknown"``.
    extension : str or None
        Name of the extension the handler belongs to, if ``kind="extension"``;
        otherwise ``None``.
    call : int
        Number of call for the specific ``(event, handler)`` pair
        (1 for the first time this handler ran for this event, 2 for the
        second call, and so on).
    start : float
        Time (in seconds) when the build starts.
    duration : float
        Time (in seconds) this handler call took to execute.
    """

    event: str
    handler: str
    module: str
    kind: str
    extension: str | None
    call: int
    start: float
    duration: float


class EventLogger:
    """Records and reports per-handler timing data for a single build.

    An :class:`EventLogger` instance (i.e. :data:`recorder`) accumulates
    one :class:`HandlerCall` per wrapped-handler call and keeps all the
    records in one place.

    Attributes
    ----------
    calls : list of HandlerCall
        Every recorded handler call for the current build, in the order
        they were recorded. These records are later stored in a json.
    start_time : float or None
        The :func:`time.perf_counter` value captured when :meth:`start`
        was called, used as the zero point for relative timings.
        ``None`` before :meth:`start` has been called.
    call_counts : collections.Counter
        Number of calls per ``(event, handler)`` pair; used to
        assign the ``call`` attribute of each :class:`HandlerCall`.
    """

    def __init__(self) -> None:
        self.calls: list[HandlerCall] = []
        self.start_time: float | None = None
        self.call_counts: Counter = Counter()

    def start(self) -> None:
        """Reset all recorded state and mark the start of a new build.

        Clears :attr:`calls` and :attr:`call_counts` and records a fresh
        :attr:`start_time`. This must be called at the beginning of each
        build so that repeated builds within the same process (e.g. via
        ``sphinx-autobuild``-style tooling) don't mix stale data from a
        previous build into the current benchmark.
        """
        self.calls = []
        self.call_counts = Counter()
        self.start_time = perf_counter()

    def record(
        self,
        event: str,
        handler_name: str,
        module: str,
        kind: str,
        extension: str | None,
        start_offset: float,
        duration: float,
    ) -> None:
        """Record one completed handler call.

        This also increments the internal per-``(event, handler_name)``
        counter in :attr:`call_counts` and appends a new
        :class:`HandlerCall` to :attr:`calls`.

        Parameters
        ----------
        event : str
            Name of the event the handler was connected to.
        handler_name : str
            Qualified name of the handler function.
        module : str
            Module path (separated by '.') where the handler is defined in.
        kind : str
            Classification of the handler's origin (``"extension"``,
            ``"sphinx-internal"``, ``"theme"``, or ``"unknown"``).
        extension : str or None
            Name of the owning extension, if ``kind="extension"``.
        start_offset : float
            Seconds since :attr:`start_time` at which this call began.
        duration : float
            Seconds this handler call took to execute.
        """
        key = (event, handler_name)
        self.call_counts[key] += 1
        self.calls.append(
            HandlerCall(
                event=event,
                handler=handler_name,
                module=module,
                kind=kind,
                extension=extension,
                call=self.call_counts[key],
                start=start_offset,
                duration=duration,
            )
        )

    def totals_by_handler(self) -> dict[tuple[str, str], float]:
        """Adds the handler function call durations for each ``(event, handler)`` pair.

        Returns
        -------
        dict of {(str, str): float}
            Mapping from ``(event, handler_name)`` to the total time in
            seconds spent across all recorded calls of that handler for
            that event.
        """
        totals: dict[tuple[str, str], float] = defaultdict(float)
        for c in self.calls:
            totals[(c.event, c.handler)] += c.duration
        return totals

    def write_json(self, filename: str = "sphinx_benchmarks.json") -> None:
        """Write all recorded handler calls to a JSON file.

        The json has a single top-level key, ``"calls"``, whose value
        is a list of the recorded :class:`HandlerCall` entries (as
        plain dicts, via :func:`dataclasses.asdict`), one per handler
        function call.

        Parameters
        ----------
        filename : str, optional
            Path to dump the benchmarking records.
            Defaults to ``"sphinx_benchmarks.json"``.
        """
        with open(filename, "w") as f:
            json.dump({"calls": [asdict(c) for c in self.calls]}, f, indent=2)

    def print_summary(self) -> None:
        """Print a grouped, sorted timing summary to stdout.

        Handlers are grouped by the event they're connected to. Each
        event group is headed by the event's name, its total recorded
        time, and its percentage share of total recorded build time;
        within a group, handlers are listed sorted by their own total
        time, highest first. Event groups themselves are ordered by
        their percentage share of total build time, highest first.

        Notes
        -----
        "Total build time" here means the sum of all recorded handler
        durations, not Sphinx's true wall-clock build time -- gaps
        between handler calls (e.g. time in file I/O between events)
        are not included!
        """
        totals = self.totals_by_handler()
        total_build_time = sum(totals.values()) or 1.0

        # look up kind/extension for each (event, handler)
        meta: dict[tuple[str, str], tuple[str, str, str | None]] = {}
        for c in self.calls:
            meta[(c.event, c.handler)] = (c.module, c.kind, c.extension)

        # group handler totals by event
        by_event: dict[str, list[tuple[str, str, str, int, float, float]]] = (
            defaultdict(list)
        )
        event_totals: dict[str, float] = defaultdict(float)
        for (event, handler), total in totals.items():
            calls = self.call_counts[(event, handler)]
            _module, kind, ext = meta[(event, handler)]
            avg = total / calls if calls else 0.0
            by_event[event].append((handler, kind, ext or "-", calls, total, avg))
            event_totals[event] += total

        # sort events by their share of total build time, max to min
        ordered_events = sorted(
            event_totals, key=lambda e: event_totals[e], reverse=True
        )

        col_header = (
            f"  {'Handler':50}{'Kind':20}{'Ext':40}"
            f"{'Calls':>10}{'Total(s)':>15}{'Avg(ms)':>15}"
        )
        width = len(col_header)

        print()
        for event in ordered_events:
            ev_total = event_totals[event]
            ev_pct = 100 * ev_total / total_build_time
            print("=" * width)
            print(f"{event}  —  {ev_total:.6f}s total  ({ev_pct:.2f}% of build)")
            print("=" * width)
            print(col_header)
            print("-" * width)

            handlers = sorted(by_event[event], key=lambda r: r[4], reverse=True)
            for handler, kind, ext, calls, total, avg in handlers:
                print(
                    f"  {handler[:49]:50}{kind:20}{ext[:39]:40}"
                    f"{calls:10d}{total:15.6f}{avg * 1000:15.3f}"
                )
            print()


recorder = EventLogger()

# set as an attribute on every wrapped handler to avoid wrapping an already wrapped handler
_WRAP_FLAG = "_event_profiler_wrapped"


def classify_handler(
    app: Sphinx, handler: Callable[..., Any]
) -> tuple[str, str | None]:
    """Classify where an event handler function comes from.

    The classification is based on the handler's ``__module__`` attribute.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The running Sphinx application, used to look up loaded
        extensions via ``app.extensions``.
    handler : callable
        The handler function to classify (the original, unwrapped
        callable that was registered with :meth:`app.connect`).

    Returns
    -------
    kind : str
        One of ``"sphinx-internal"``, ``"extension"``, ``"theme"``, or
        ``"unknown"``.
    extension : str or None
        The matching extension's name if ``kind="extension"``;
        otherwise ``None``.
    """
    module = getattr(handler, "__module__", "") or ""
    top = module.split(".")[0]

    if module == "sphinx" or module.startswith("sphinx."):
        return "sphinx-internal", None

    for ext_name, ext in app.extensions.items():
        ext_top = ext.module.__name__.split(".")[0]
        if ext_top == top:
            return "extension", ext_name

    if top in THEME_PACKAGES:
        return "theme", top

    return "unknown", None


def wrap_listener(app: Sphinx, event_name: str, listener):
    """Wrap a single event listener's handler by adding a
    ``perf_counter()`` at the start and the end of the handler
    function call.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The running Sphinx application.
    event_name : str
        Name of the event this listener is registered for.
    listener : sphinx.events.EventListener
        The listener to wrap, as found in ``app.events.listeners``.

    Returns
    -------
    sphinx.events.EventListener
        A new listener with the same ``id`` and ``priority`` as the
        input, but with its ``handler`` replaced by a wrapped handler.
        If handler is already wrapped (see
        :data:`_WRAP_FLAG`), the original listener is returned
        as it is. Refer
        https://www.sphinx-doc.org/en/master/_modules/sphinx/events.html#EventManager

    Notes
    -----
    The returned wrapper calls the original handler, records its
    duration via :meth:`EventLogger.record`, and re-raises any exception
    the original handler raised (timing is recorded in a ``finally`` block,
    so exceptions propagate normally and Sphinx's own error handling is unaffected).
    The wrapper's ``__name__``, ``__qualname__``, and ``__module__`` are
    copied from the original handler so that Sphinx's and extension's
    own error messages still point to the real handler rather than to the wrapper.
    """
    orig_handler = listener.handler
    if getattr(orig_handler, _WRAP_FLAG, False):
        return listener  # already wrapped, don't double-wrap

    kind, ext_name = classify_handler(app, orig_handler)
    handler_name = getattr(
        orig_handler,
        "__qualname__",
        getattr(orig_handler, "__name__", repr(orig_handler)),
    )
    module = getattr(orig_handler, "__module__", "unknown")

    def wrapped(app_arg, *args, **kwargs):
        t0 = perf_counter()
        start_offset = t0 - (recorder.start_time or t0)
        try:
            return orig_handler(app_arg, *args, **kwargs)
        finally:
            duration = perf_counter() - t0
            recorder.record(
                event_name,
                handler_name,
                module,
                kind,
                ext_name,
                start_offset,
                duration,
            )

    setattr(wrapped, _WRAP_FLAG, True)
    wrapped.__name__ = getattr(orig_handler, "__name__", "handler")
    wrapped.__qualname__ = handler_name
    wrapped.__module__ = module

    return listener._replace(handler=wrapped)


def wrap_all_listeners(app: Sphinx, *_args) -> None:
    """Wrap every currently-registered event listener for timing.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The running Sphinx application whose ``app.events.listeners``
        registry should be wrapped in place.
    *_args
        Extra positional arguments Sphinx passes when this is connected
        directly as an event handler.

    Notes
    -----
    Iterates over every event name currently in
    ``app.events.listeners`` (including custom events added via
    ``app.add_event``). Safe to call more than once -- already-wrapped
    listeners are left unchanged.
    """
    for event_name in list(app.events.listeners.keys()):
        app.events.listeners[event_name] = [
            wrap_listener(app, event_name, listener)
            for listener in app.events.listeners[event_name]
        ]


def build_finished(app: Sphinx, exception) -> None:
    """Write the collected benchmarks and print the summary at the end of the build.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The running Sphinx application.
    exception : Exception or None
        The exception that terminated the build, if any, or ``None``
        for a successful build. Unused, but received because
        Sphinx always passes it to ``build-finished`` handlers.
    """
    recorder.write_json()
    print("sphinx_benchmarks.json written")
    recorder.print_summary()


def setup(app: Sphinx):
    """Sphinx extension entry point."""
    recorder.start()

    # By the time config-inited is emitted, every extension's setup(app) has
    # already run app.connect() for its own handlers, so this catches
    # essentially everything registered so far.
    app.connect("config-inited", wrap_all_listeners, priority=999)
    # Safety net for anything connected between config-inited and
    # builder-inited (rare, but some extensions might do this).
    app.connect("builder-inited", wrap_all_listeners, priority=999)

    app.connect("build-finished", build_finished, priority=999)

    return {
        "version": "0.1",
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
