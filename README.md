# [WIP] benchmark-sphinx-phase-wise

To benchmark the Sphinx docs build process handler-wise (broken down by [event](https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html) and by extension). Right now, benchmarks are computed by wrapping each handler function registered against an event (each `EventListener` in `app.events.listeners`), rather than the event as a whole.

You can find the benchmarking outputs for different Scientific Python projects in the [benchmarking_outputs](./benchmarking_outputs/) directory.

## How to use it?

In your sphinx's `conf.py` add the following:

```python
extensions = [
    "benchmark_sphinx_phase_wise",
]
```

Note: being first in the list minimizes (but doesn't eliminate) the untracked starting time.


Thank you for stopping by :)
