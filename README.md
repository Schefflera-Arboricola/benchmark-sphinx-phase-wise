# [WIP] benchmark-sphinx-phase-wise

To benchmark the sphinx docs build process phase-wise

**Note**: Benchmarks are computed from observable log events msg only! If an extension does not emit log messages, it cannot be broken down further into sub-phases without adding log msg in the extension's codebase itself.

--- 

This profiler always produce benchmarks for the five standard Sphinx phases automatically:

- Initialization
- Reading
- Consistency checks
- Resolving
- Writing

To further benchmark the subphases within the above mentioned phases the user can configure the `src/setup.toml` file to indicate which subprocesses do they want to see in the benchmarks.


Thank you for stopping by :)
