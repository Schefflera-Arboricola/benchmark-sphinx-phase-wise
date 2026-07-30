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

Initialization :  446.999 s
Reading        :  215.299 s
Consistency    :    0.699 s
Writing        :  172.083 s

--------------------------------------------------
Total          :  835.080 s
```

For NumPy docs build:

```bash

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
