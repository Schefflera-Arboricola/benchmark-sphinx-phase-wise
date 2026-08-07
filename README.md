# [WIP] benchmark-sphinx-phase-wise

To benchmark the sphinx docs build process event-wise. The benchmarks are computed from [sphinx's event callback API](https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html).

## Demo output

For Matplotlib docs build:

```bash
Event                                   Calls       Total(s)        Avg(ms)    %Build
-------------------------------------------------------------------------------------
config-inited                               1     407.897459     407897.459    51.76%
doctree-resolved                         2081     159.895919         76.836    20.29%
source-read                              2081     118.485265         56.937    15.03%
object-description-transform             7034      71.411225         10.152     9.06%
doctree-read                             2081      19.743725          9.488     2.51%
env-purge-doc                            2081       4.523341          2.174     0.57%
write-started                               1       1.744397       1744.397     0.22%
builder-inited                              1       1.361653       1361.653     0.17%
include-read                               50       1.286405         25.728     0.16%
warn-missing-reference                    141       1.183458          8.393     0.15%
env-updated                                 1       0.538349        538.349     0.07%
env-before-read-docs                        1       0.000224          0.224     0.00%
env-check-consistency                       1       0.000117          0.117     0.00%
build-finished                              1       0.000000          0.000     0.00%
```

For NumPy docs build:

```bash
Event                                   Calls       Total(s)        Avg(ms)    %Build
-------------------------------------------------------------------------------------
doctree-resolved                         2673     151.714524         56.758    50.05%
source-read                              2673     112.351479         42.032    37.06%
object-description-transform             3480      16.495565          4.740     5.44%
config-inited                               1       9.698906       9698.906     3.20%
env-purge-doc                            2673       5.636594          2.109     1.86%
doctree-read                             2673       4.485057          1.678     1.48%
include-read                               25       1.214643         48.586     0.40%
builder-inited                              1       0.841800        841.800     0.28%
env-updated                                 1       0.504075        504.075     0.17%
write-started                               1       0.210907        210.907     0.07%
env-before-read-docs                        1       0.000199          0.199     0.00%
env-check-consistency                       1       0.000153          0.153     0.00%
build-finished                              1       0.000000          0.000     0.00%
```

For NetworkX docs build:

```bash
Event                                   Calls       Total(s)        Avg(ms)    %Build
-------------------------------------------------------------------------------------
config-inited                               1      99.908844      99908.844    44.77%
doctree-resolved                         1561      68.802479         44.076    30.83%
source-read                              1561      36.947228         23.669    16.56%
object-description-transform             1317       9.619805          7.304     4.31%
doctree-read                             1561       3.242623          2.077     1.45%
env-purge-doc                            1561       3.064107          1.963     1.37%
builder-inited                              1       0.910023        910.023     0.41%
env-updated                                 1       0.291570        291.570     0.13%
write-started                               1       0.270730        270.730     0.12%
include-read                                6       0.108453         18.075     0.05%
warn-missing-reference                      1       0.002586          2.586     0.00%
env-before-read-docs                        1       0.000420          0.420     0.00%
env-check-consistency                       1       0.000278          0.278     0.00%
build-finished                              1       0.000000          0.000     0.00%
```

For CPython docs build:

```bash
ToDo
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

Just for reference: 

- benchmarks for phase-wise benchmarking for matplotlib:

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

- benchmarks from the previous "time-stampped logging messages" approach for matplotlib:

```bash
=== Main Phase Benchmarks ===

Initialization        443.825 s
Reading               233.482 s
Consistency             0.051 s
Resolving               3.702 s
Writing               182.212 s
```

---


Thank you for stopping by :)
