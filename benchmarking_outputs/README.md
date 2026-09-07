This directory contains the benchmarking results for some of the Scientific Python projects' documentation builds.

# Reading the benchmarking output

At fixed points in a docs build process (e.g. after config is read, after a page is parsed, before a page is written, etc.) Sphinx emits an **event**, and every extension or theme that registered a **handler** for
that event gets called. This tool times each of those events and the handler calls within those events.

Every build with this extension enabled creates a `sphinx_benchmarks.json` file with following three things:

- `total_wall_time` : the whole build time, start to finish
- `events` : one record per event emission (when it started, how long it took, how deeply nested it was, etc.)
- `calls` : one record per handler call (which handler, which event, which extension it came from, how long it took, etc.)

The `sphinx-benchmark run table` command uses the data in the above JSON file to print out the two benchamrks summary tables. 

## Table 1 : where time goes inside events

The first table has one block per event, sorted by the most expensive event first.
The header line of each block looks like this:

```
builder-inited — 107.478046s own time (41.46% of build) | 1 emissions | 107.494970s duration (including nested event) | depth 0
```

- **own time** : total time spent in this event across the whole build, *excluding*
  any other events that fired from inside it. This is what the blocks are sorted by,
  and what the percentage is measured against `total_wall_time`.
- **emissions** : how many times the event fired.
- **duration (including nested event)** : only printed when this event emits another events.
  It is the total time spent in this event *including* the durations of events that were fired
  from inside it.
- **depth** : `0` means the event fired at the top level of the build. `1` means it
  only ever fired from inside another event. A range like `0-1` means both.

Underneath is a row per handler that ran during that event:

- **Handler** : The function's name
- **Kind** : `extension`, `theme`, `sphinx-internal`, or `unknown` 
- **Ext/Module** : The extension or the package(or file) the handler belongs to
- **Calls** : How many times this handler function was called
- **Total(s)** : All of its execution times added up
- **Avg(ms)** : Total / Calls

Two numbers close each block:

- **(sum of handlers)** : the handler rows added together.
- **(unaccounted overhead)** : the event's duration minus the above sum. It's
  normally small. If it's large, the time is going somewhere the per-handler timers
  can't see.

You can further see the break-down of each event emission using the 
`sphinx-benchamrk run table events <event_name>`, and see the break down of each
handler call using either `sphinx-benchamrk run table events <handler_name>` or
`sphinx-benchamrk run table events <event_name> <handler_name>` commands.

At the very bottom:

```
Sum of own durations of all events: 131.263775s   Wall clock: 259.262810s   Outside any event: 127.999036s (49.37%)
```

That last figure is usually the surprise. Roughly half of a real build isn't inside
any event at all-- it's Sphinx reading source files, resolving references, and
writing HTML. Events are checkpoints, not phases, and nothing times the work
*between* them. That's what the second table is for.

## Table 2 : the gaps between events

We take all event emissions (excluding any nested events), sort them by start time, and measure the time between one ending and the next one starting. Each row aggregates every gap that occurred at
an event boundary:

```
html-page-context -> missing-reference    30.198548    910    33.185    11.65%
```

Read this as: 910 times during the build, `html-page-context` finished and
`missing-reference` was the next event to fire, and the stretch in between added up
to 30s (about 33ms gap each time, 11.65% of the build).

If you ever see a `WARNING: negative gaps` line, two top-level emissions
overlapped, that shouldn't happen, so please report an issue for it.

You can further see the break-down of each gap using the 
`sphinx-benchmark run table gaps <start-event> <end-event>` command.
