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
