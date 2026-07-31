from __future__ import annotations

from pathlib import Path
from time import perf_counter

from sphinx.application import Sphinx


# tuple --> (Phase mame, Start event, End event)
PHASES = [
    ("Initialization", "config-inited", "env-before-read-docs"),
    ("Reading", "env-before-read-docs", "env-updated"),
    ("Consistency", "env-updated", "env-check-consistency"),
    ("Pre-writing", "env-check-consistency", "write-started"),
    ("Resolving", "write-started", "doctree-resolved"),
    ("Writing", "doctree-resolved", "build-finished"),
    # or ("Resolving+Writing", "write-started", "build-finished"),
]


class PhaseBenchmark:
    def __init__(self) -> None:
        self.start_time: float | None = None
        self.timestamps: dict[str, float] = {}

    def start(self) -> None:
        self.start_time = perf_counter()

    def mark(self, event: str) -> None:
        self.timestamps[event] = perf_counter()

    def duration(self, start: str, end: str) -> float:
        return self.timestamps[end] - self.timestamps[start]


bench = PhaseBenchmark()

# Event callbacks


def config_inited(app: Sphinx, *args) -> None:
    bench.start()
    bench.mark("config-inited")


def env_before_read_docs(app: Sphinx, env, docnames) -> None:
    bench.mark("env-before-read-docs")


def env_updated(app: Sphinx, env) -> None:
    bench.mark("env-updated")


def env_check_consistency(app: Sphinx, env) -> None:
    bench.mark("env-check-consistency")


def write_started(app: Sphinx, builder) -> None:
    bench.mark("write-started")


def doctree_resolved(app: Sphinx, doctree, docname) -> None:
    bench.mark("doctree-resolved")


def build_finished(app: Sphinx, exception: Exception | None) -> None:
    bench.mark("build-finished")

    lines = [
        "=" * 50,
        "Sphinx phase-wise benchmarks",
        "=" * 50,
        "",
    ]

    for phase, start, end in PHASES:
        if start not in bench.timestamps or end not in bench.timestamps:
            lines.append(f"{phase:<15}: Not recorded")
            continue

        lines.append(f"{phase:<15}: {bench.duration(start, end):8.3f} s")

    if bench.start_time is not None:
        total = perf_counter() - bench.start_time
        lines.extend(
            [
                "",
                "-" * 50,
                f"{'Total':<15}: {total:8.3f} s",
            ]
        )

    output = "\n".join(lines)

    log_file = Path(app.outdir) / "phase_wise_benchmarks.log"
    log_file.write_text(output, encoding="utf-8")

    print("\n" + output)


# Extension setup


def setup(app: Sphinx):
    app.connect("config-inited", config_inited)
    app.connect("env-before-read-docs", env_before_read_docs)
    app.connect("env-updated", env_updated)
    app.connect("env-check-consistency", env_check_consistency)
    app.connect("write-started", write_started)
    app.connect("doctree-resolved", doctree_resolved)
    app.connect("build-finished", build_finished)

    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
