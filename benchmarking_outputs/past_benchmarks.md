Just for reference: 

- benchmarks for event-wise benchmarking for matplotlib:

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
