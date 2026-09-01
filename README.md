# sphinx-benchmark

This is a Sphinx extension that benchmarks and profiles a docs build process [event](https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html)-wise(handler-wise), and the gaps in between the events-- so you can tell which extension, theme, or part of Sphinx itself is slowing your builds. Note, that this extension is still in its early stages of development--so it might change a lot and there might be a lot of bugs in it right now. So don't use it in production yet!

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

4. Change the directory to the build directory (where the generated `sphinx_benchmarks.json` is present) and run:

   ```bash
   sphinx-benchmark run
   ```

   This prints the top 10 events and gaps that take up the most of the build time,
   sorted by % of build descending. Following is the output for the matplotlib's docs build:
   
   ```bash
   % sphinx-benchmark run         

   Build time: 317.779871s   Inside events: 73.067759s (22.99%)   Outside events (gaps): 244.712111s (77.01%)
   ===========================================================================================================
   Top 10 of 75 events and gaps, by % of build
   ===========================================================================================================
   Name                                                              Type        Time(s)     Count   % build
   -----------------------------------------------------------------------------------------------------------
   html-page-context -> doctree-resolved                              gap      94.032040      1745    29.59%
   doctree-resolved -> html-page-context                              gap      32.449961      2081    10.21%
   source-read -> doctree-read                                        gap      21.442795       981     6.75%
   html-page-context -> missing-reference                             gap      20.821428       335     6.55%
   autodoc-process-docstring                                        event      18.713229      8350     5.89%
   doctree-read                                                     event      16.040303      2081     5.05%
   autodoc-process-signature                                        event      14.553734      8258     4.58%
   autodoc-process-docstring -> object-description-transform          gap      13.749841      1123     4.33%
   object-description-transform -> object-description-transform       gap      12.837677      5853     4.04%
   object-description-transform -> doctree-read                       gap       9.291097      1065     2.92%
   -----------------------------------------------------------------------------------------------------------
   events total                                                                73.067759              22.99%
   gaps total                                                                 244.712111              77.01%
   (65 more rows; use --top N to show more)
   ```

   Use `--top` to change how many rows are shown, e.g. `sphinx-benchmark run --top 20`.

   For the full tables (the per-event handler tables plus the gaps summary), run
   `sphinx-benchmark run table`; it also accepts a selector for more focused views:

   ```bash
   sphinx-benchmark run table events                      # only the per-event handler tables
   sphinx-benchmark run table events <event-name>         # every emission of that event, with all details
   sphinx-benchmark run table events <handler-name>       # every call of that handler from any event
   sphinx-benchmark run table events <event-name> <handler-name>    # that handler's calls during that event emission only
   sphinx-benchmark run table gaps                        # only the gaps summary table
   sphinx-benchmark run table gaps <start-event> <end-event>  # details of every individual gap between those two events
   ```

   You can find the benchmarking outputs for different Scientific Python projects in the 
   [benchmarking_outputs](./benchmarking_outputs/) directory. For what the output actually mean,
   see [the benchmarking_outputs README](./benchmarking_outputs/README.md).

5. If you want to see the benchmarks summary in html format, run:

   ```bash
   sphinx-benchmark run html
   ```

   Then a `sphinx_benchmark_report` folder will be created in your build directory. Open the `index.html` present inside
   `sphinx_benchmark_report` in your browser to see the overview and events, handlers and gaps breakdown.
   You can also specify the output directory for where you want the `sphinx_benchmark_report` folder to get created, using `--output-dir` option. Or specify a different json file using the `--input` option.

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
