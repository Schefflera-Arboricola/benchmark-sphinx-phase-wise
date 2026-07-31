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
