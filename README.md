# sphinx-benchmark

This is a Sphinx extension that benchmarks and profiles a docs build process [event](https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html)-wise(handler-wise), and the gaps in between the events-- so you can tell which extension, theme, or part of Sphinx itself is slowing your builds. Note, that this extension is still in its early stages of development--so it might change a lot and there might be a lot of bugs in it right now. So don't use it in production yet!

You can find the benchmarking outputs for different Scientific Python projects and learn more about the benchmarking output in the [benchmarking_outputs](./benchmarking_outputs/) directory.


## Usage

1. Install the sphinx-benchmark extension

   ```bash
   pip install sphinx-benchmark
   ```

2. Add the extension to your `conf.py`:

   ```python
   extensions = ["sphinx_benchmark", ...]
   ```

   Put it first in the list as it minimizes (but doesn't eliminate) the untracked starting time.

3. Then build your docs as usual:

   ```bash
   sphinx-build -b html docs/ docs/_build/html
   ```

   The build generates a `sphinx_benchmarks.json` in the present working directory.

4. Run the `print_summary.py` script to get the benchmarking output:

   ```bash
   python path/to/sphinx-benchmark/src/sphinx_benchmark/print_summary.py
   ```

   For what the output actually mean, see [the benchmarking_outputs README](./benchmarking_outputs/README.md).


## How are benchmarks calculated?

Nearly everything an extension does in Sphinx goes through `app.events.emit()`.
Sphinx calls it at certain points in the build process, and it runs all the
registered handler for that event. This extension wraps and puts timers around this path.

`wrap_emit()` wraps `app.events.emit` that times the whole emission, and
`wrap_listener()` swaps each handler for a wrapped and timed copy of it.
So for every event you get the total time it took and the split across its handlers.
A stack is maintained to keep track of nested event, and the child event's time is
later subtracted so it isn't counted twice. `wrap_all_listeners()` wraps everything
already registered when the extension loads, and `wrap_connect()` wraps
`app.events.connect` so handlers and events registered later, also get wrapped as they are called.

Each timed call becomes a `HandlerCall` record and each event emission becomes an
`Event` record, both kept in one `EventLogger`. All times are measured from the moment
the extension started, so everything shares a starting point.

At `build-finished` (at priority 999, so other extensions' handlers gets executed first)
the extension works out each event's own time, classify every handler with where it came from,
and dumps everything into a JSON.


## Limitations of this extension - WIP

- No parallel builds: The recorder lives in the main process only, so
`parallel_read_safe` and `parallel_write_safe` are both `False`. Sphinx will fall back to a
serial build even if you pass `-j auto`, which means the wall-clock total won't match what
you'd normally see, when you are building with parallelism.
- The `build-finished` emission has `duration=None`. The handler that writes the JSON runs
inside that emission, so the emission hasn't ended yet when it's serialised. It's stored
with `duration=None` and the summary skips it. Anything after it, like `builder.cleanup()`
isn't measured at all.
- The startup blind spot: Timing begins at the extension's `setup()`. The "startup, before first emission" row in the gaps table covers only what happened after that point.
- Some handlers can't be classified: Handlers defined in `conf.py`, or in a package that
doesn't match anything in `app.extensions`, are classified as `unknown` and reported by
module or file name. Partials and callable objects have no `__qualname__`, so they're
labelled by whatever name could be recovered.
- the extension itself also adds a little bit of overhead to the build process.
- Wall clock time is not CPU time: caches, background processes, and network fetches all are included in the total time. Run benchmarks more than once before concluding anything.


Thank you for stopping by :)
