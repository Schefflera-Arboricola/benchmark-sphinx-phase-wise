# [WIP] benchmark-sphinx-phase-wise

To benchmark the sphinx docs build process phase-wise. The benchmarks are computed from sphinx's event callback API. This profiler always produce benchmarks for the five main Sphinx phases:

- Initialization
- Reading
- Consistency checks
- Resolving -- WIP
- Writing

## Demo output

For Matplotlib docs build:

```bash
Event                                   Calls      Total (s)       Avg (ms)   % Build
-------------------------------------------------------------------------------------
config-inited                               1     524.072088     524072.088    52.53%
doctree-resolved                         2081     192.077803         92.301    19.25%
source-read                              2081     153.767586         73.891    15.41%
object-description-transform             7034      85.980617         12.224     8.62%
doctree-read                             2081      23.250254         11.173     2.33%
env-purge-doc                            2081       8.892121          4.273     0.89%
write-started                               1       3.728634       3728.634     0.37%
include-read                               50       1.720333         34.407     0.17%
builder-inited                              1       1.625397       1625.397     0.16%
env-updated                                 1       1.278362       1278.362     0.13%
warn-missing-reference                    141       1.271878          9.020     0.13%
env-before-read-docs                        1       0.000482          0.482     0.00%
env-check-consistency                       1       0.000428          0.428     0.00%
build-finished                              1       0.000000          0.000     0.00%
```

```bash
==================================================
Sphinx phase-wise benchmarks
==================================================

Initialization :  452.402 s
Reading        :  207.971 s
Consistency    :    0.699 s
Pre-writing    :    0.000 s
Resolving      :  180.908 s
Writing        :    7.531 s

--------------------------------------------------
Total          :  849.511 s
```

For NumPy docs build:

```bash
ToDo
```

For NetworkX docs build:

```bash
==================================================
Sphinx phase-wise benchmarks
==================================================

Initialization :  112.857 s
Reading        :   50.288 s
Consistency    :    0.270 s
Pre-writing    :    0.000 s
Resolving      :   14.329 s
Writing        :   56.618 s

--------------------------------------------------
Total          :  234.362 s
```

For CPython docs build:

```bash
ToDo
```

Just for reference: benchmarks from the previous "time-stampped logging messages" approach for matplotlib:

```bash
=== Main Phase Benchmarks ===

Initialization        443.825 s
Reading               233.482 s
Consistency             0.051 s
Resolving               3.702 s
Writing               182.212 s
```

---

## How to use it?

In your sphinx's `conf.py` add the following:

```python
extensions = [
    "benchmark_sphinx_phase_wise",
]
```

---

Thank you for stopping by :)
