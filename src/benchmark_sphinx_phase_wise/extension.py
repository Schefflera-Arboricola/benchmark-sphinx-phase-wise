from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from time import perf_counter
from functools import wraps
from sphinx.application import Sphinx
from importlib.metadata import entry_points

THEME_PACKAGES = {
    ep.module.split(".")[0] for ep in entry_points(group="sphinx.html_themes")
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
        Origin package of the handler: extension name for
        ``kind="extension"``, theme package for ``kind="theme"``,
        top-level module for ``kind="unknown"``, ``None`` otherwise.
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


@dataclass
class Event:
    """Records the total time spent in a single event emission (including all its listeners and any gaps between them)."""

    event_name: str
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
    events : list of Event
        Every recorded event emission for the current build, in the order
        they were recorded. These records are later stored in a json.
    start_time : float or None
        The :func:`time.perf_counter` value captured when :meth:`start`
        was called, used as the zero point for relative timings.
        ``None`` before :meth:`start` has been called.
    call_counts : collections.Counter
        Number of calls per ``(event, handler)`` pair; used to
        assign the ``call`` attribute of each :class:`HandlerCall`.
    event_call_counts : collections.Counter
        Number of calls per ``event_name``; used to assign the ``call``
        attribute of each :class:`Event`.
    total_wall_time : float
        Total wall-clock time of the build, as measured by
        ``perf_counter() - start_time``. This is not the same as the
        sum of all recorded handler durations, because there may be
        gaps between handler calls.
    """

    def __init__(self) -> None:
        self.calls: list[HandlerCall] = []
        self.events: list[Event] = []
        self.start_time: float | None = None
        self.call_counts: Counter = Counter()
        self.event_call_counts: Counter = Counter()
        self.total_wall_time: float = 0.0

    def start(self) -> None:
        """Reset all recorded state and mark the start of a new build.

        Clears :attr:`calls` and :attr:`call_counts` and records a fresh
        :attr:`start_time`. This must be called at the beginning of each
        build so that repeated builds within the same process (e.g. via
        ``sphinx-autobuild``-style tooling) don't mix stale data from a
        previous build into the current benchmark.
        """
        self.calls = []
        self.events = []
        self.call_counts = Counter()
        self.event_call_counts = Counter()
        self.start_time = perf_counter()

    def record(
        self,
        event: str,
        handler_name: str,
        module: str,
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
                kind="unknown",  # will be filled in later by classify_handler
                extension=None,  # will be filled in later by classify_handler
                call=self.call_counts[key],
                start=start_offset,
                duration=duration,
            )
        )

    def record_event(
        self, event_name: str, start_offset: float, duration: float
    ) -> None:
        """Record one completed event emission (full wall-clock time of the
        emit() call, including all its listeners and any gaps between them).

        Parameters
        ----------
        event_name : str
            Name of the emitted event.
        start_offset : float
            Seconds since :attr:`start_time` at which this emit began.
        duration : float
            Seconds the whole emit() call took.
        """
        self.event_call_counts[event_name] += 1
        self.events.append(
            Event(
                event_name=event_name,
                call=self.event_call_counts[event_name],
                start=start_offset,
                duration=duration,
            )
        )

    def classify_all_handlers(self, app: Sphinx) -> None:
        """Classify every recorded call and set its ``kind`` and ``extension``.

        Sphinx adds an extension to `app.extensions` after its `setup()`
        returns, so classifying at the time of wrapping reports "extension"
        as `"unknown"`.
        """
        all_hc = {}
        for hc in self.calls:
            module = hc.module
            top = module.split(".")[0]
            if module not in all_hc:
                if module == "sphinx" or module.startswith("sphinx."):
                    all_hc[module] = ("sphinx-internal", None)
                # Checked before extensions: most themes also register a setup(), so they
                # appear in app.extensions and would otherwise be classified as extensions.
                elif top in THEME_PACKAGES:
                    all_hc[module] = ("theme", top)
                else:
                    all_hc[module] = ("unknown", top or None)
                    for ext_name, ext in app.extensions.items():
                        ext_top = ext.module.__name__.split(".")[0]
                        if ext_top == top:
                            all_hc[module] = ("extension", ext_name)
                            break
            hc.kind, hc.extension = all_hc[module]

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

    def totals_by_event(self) -> dict[str, float]:
        """Total recorded emit() time per event, across all its emissions."""
        totals: dict[str, float] = defaultdict(float)
        for e in self.events:
            totals[e.event_name] += e.duration
        return totals

    def write_json(self, filename: str = "sphinx_benchmarks.json") -> None:
        """Write all recorded handler calls to a JSON file.

        The json has a two top-level keys:

        ``"calls"`` is a list of the recorded :class:`HandlerCall` entries (as
        plain dicts, via :func:`dataclasses.asdict`), one per handler
        function call.

        ``"events"`` is a list of the recorded :class:`Event` entries (as
        plain dicts, via :func:`dataclasses.asdict`), one per event emission.

        Parameters
        ----------
        filename : str, optional
            Path to dump the benchmarking records.
            Defaults to ``"sphinx_benchmarks.json"``.
        """
        with open(filename, "w") as f:
            json.dump(
                {
                    "calls": [asdict(c) for c in self.calls],
                    "events": [asdict(e) for e in self.events],
                },
                f,
                indent=2,
            )

    def print_summary(self) -> None:
        """Print a grouped, sorted timing summary to stdout.

        Handlers are grouped by the event they're connected to. Each
        event group is headed by the event's name, its total recorded
        time, and its percentage share of total build wall-clock time;
        within a group, handlers are listed sorted by their own total
        time, highest first. Event groups themselves are ordered by
        their percentage share of total build time, highest first.
        """
        handler_totals = self.totals_by_handler()
        event_totals = self.totals_by_event()
        sum_of_events = sum(event_totals.values())
        total_build_time = self.total_wall_time or sum_of_events or 1.0

        meta: dict[tuple[str, str], tuple[str, str, str | None]] = {}
        for c in self.calls:
            meta[(c.event, c.handler)] = (c.module, c.kind, c.extension)

        by_event: dict[str, list[tuple[str, str, str, int, float, float]]] = (
            defaultdict(list)
        )
        for (event, handler), total in handler_totals.items():
            calls = self.call_counts[(event, handler)]
            _module, kind, ext = meta[(event, handler)]
            avg = total / calls if calls else 0.0
            by_event[event].append((handler, kind, ext or "-", calls, total, avg))

        ordered_events = sorted(
            event_totals, key=lambda e: event_totals[e], reverse=True
        )

        col_header = (
            f"  {'Handler':50}{'Kind':20}{'Ext/Module':40}"
            f"{'Calls':>10}{'Total(s)':>15}{'Avg(ms)':>15}"
        )
        width = len(col_header)

        print()
        print("Build time: ", total_build_time)
        for event in ordered_events:
            ev_total = event_totals[event]
            ev_pct = 100 * ev_total / total_build_time
            print("=" * width)
            print(f"{event}  —  {ev_total:.6f}s total  ({ev_pct:.2f}% of build)")
            print("=" * width)
            print(col_header)
            print("-" * width)

            handlers = sorted(by_event.get(event, []), key=lambda r: r[4], reverse=True)
            for handler, kind, ext, calls, total, avg in handlers:
                print(
                    f"  {handler[:49]:50}{kind:20}{ext[:39]:40}"
                    f"{calls:10d}{total:15.6f}{avg * 1000:15.3f}"
                )
            handler_sum = sum(r[4] for r in handlers)
            print("-" * width)
            print(f"  {'(sum of handlers)':50}{'':20}{'':40}{'':10}{handler_sum:15.6f}")
            print(
                f"  {'(unaccounted overhead)':50}{'':20}{'':40}{'':10}{ev_total - handler_sum:15.6f}"
            )
            print()

        print("=" * width)
        print(
            f"Sum of durations of all events: {sum_of_events:.6f}s   "
            f"Wall clock: {total_build_time:.6f}s   "
            f"Outside any event: {total_build_time - sum_of_events:.6f}s "
            f"({100 * (total_build_time - sum_of_events) / total_build_time:.2f}%)"
        )


recorder = EventLogger()

# set as an attribute on every wrapped handler to avoid wrapping an already wrapped handler
_WRAP_FLAG = "_event_profiler_wrapped"


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

    handler_name = getattr(
        orig_handler,
        "__qualname__",
        getattr(orig_handler, "__name__", repr(orig_handler)),
    )
    module = getattr(orig_handler, "__module__", "unknown")

    @wraps(orig_handler)
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
                start_offset,
                duration,
            )

    setattr(wrapped, _WRAP_FLAG, True)
    if not hasattr(orig_handler, "__qualname__"):
        # for handlers that aren't simple functions (partials, callable objects, etc.)
        # have no qualname/name for @wraps to copy, so setting those explicitly
        wrapped.__name__ = handler_name
        wrapped.__qualname__ = handler_name

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


def wrap_connect(app: Sphinx) -> None:
    """Wraps the ``app.connect`` so listeners get wrapped when registered."""
    original_connect = app.events.connect

    def wrapped(name, callback, *args, **kwargs):
        listener_id = original_connect(name, callback, *args, **kwargs)
        listeners = app.events.listeners[name]
        for i, listener in enumerate(listeners):
            if listener.id == listener_id:
                listeners[i] = wrap_listener(app, name, listener)
                break
        return listener_id

    app.events.connect = wrapped


def wrap_emit(app: Sphinx, *_args) -> None:
    """Wrap ``app.events.emit`` so the full cost of each event emission
    (all listeners plus any Sphinx-internal overhead between them) is
    recorded, not just the sum of the wrapped handlers' own durations.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The running Sphinx application whose ``app.events.emit`` should
        be wrapped in place.
    *_args
        Extra positional arguments Sphinx passes when this is connected
        directly as an event handler.
    """
    original_emit = app.events.emit

    def wrapped(event_name, *args, **kwargs):
        t0 = perf_counter()
        start_offset = t0 - (recorder.start_time or t0)
        try:
            return original_emit(event_name, *args, **kwargs)
        finally:
            recorder.record_event(event_name, start_offset, perf_counter() - t0)

    app.events.emit = wrapped


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
    recorder.total_wall_time = perf_counter() - (recorder.start_time or perf_counter())
    recorder.classify_all_handlers(app)
    recorder.write_json()
    print("sphinx_benchmarks.json written")
    recorder.print_summary()


def setup(app: Sphinx):
    """Sphinx extension entry point."""
    recorder.start()
    wrap_emit(app)
    wrap_all_listeners(app)
    wrap_connect(app)

    # the priority is set to 999  so that if any other handlers are connected
    # with the build-finished event, then those get executed first and stored in the json.
    app.connect("build-finished", build_finished, priority=999)

    # builder.cleanup() happens after build-finished
    # maybe should wrap `app.build`?

    return {
        "version": "0.1",
        "parallel_read_safe": False,
        "parallel_write_safe": False,
    }
