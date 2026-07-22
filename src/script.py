from __future__ import annotations

import subprocess
import time
import tomllib


"""
MAIN_PHASES = [
    ("Initialization", "Running Sphinx", "reading sources"),
    ("Reading", "reading sources", "checking consistency"),
    ("Consistency", "checking consistency", "preparing documents"),
    ("Resolving", "preparing documents", "writing output"),
    ("Writing", "writing output", "build succeeded"),
]
"""


def load_config(path="setup.toml"):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}


def run_build():
    """Run a verbose HTML build and timestamp every log line."""

    proc = subprocess.Popen(
        ["make", "html", "SPHINXOPTS=-vvv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    start = time.perf_counter()
    logs = []

    for line in proc.stdout:
        t = time.perf_counter() - start
        line = line.rstrip()

        logs.append((t, line))
        # print(f"{t:8.3f}s  {line}")

    proc.wait()

    return logs


def benchmark_main_phases(logs):
    """Benchmark the 5 major HTML build phases.

    We ignore non-html builders (e.g. mo).
    """

    builder = None

    phases = {
        "Initialization": None,
        "Reading": None,
        "Consistency": None,
        "Resolving": None,
        "Writing": None,
    }

    for t, line in logs:
        # Detect builder
        if "building [html]" in line:
            builder = "html"
            continue

        elif line.startswith("building ["):
            builder = "other"
            continue

        if builder != "html":
            continue

        if phases["Initialization"] is None and "reading sources" in line:
            phases["Initialization"] = t

        elif phases["Reading"] is None and "checking consistency" in line:
            phases["Reading"] = t

        elif phases["Consistency"] is None and "preparing documents" in line:
            phases["Consistency"] = t

        elif phases["Resolving"] is None and "writing output... [" in line:
            phases["Resolving"] = t

        elif phases["Writing"] is None and "build succeeded" in line:
            phases["Writing"] = t

    print("\n=== Main Phase Benchmarks ===\n")

    previous = 0.0

    for phase in [
        "Initialization",
        "Reading",
        "Consistency",
        "Resolving",
        "Writing",
    ]:
        end = phases[phase]

        if end is None:
            print(f"{phase:20} not found")
            continue

        print(f"{phase:20} {end - previous:8.3f} s")
        previous = end


def benchmark_subphases(logs, config):
    """Benchmark user-defined subphases.

    Measures time between first and last occurrence of
    any configured keyword.
    """

    if not config:
        return

    print("\n=== Subphases ===\n")

    for phase, subphases in config.items():
        print(f"[{phase}]")

        for name, patterns in subphases.items():
            first = None
            last = None

            for t, line in logs:
                if any(p.lower() in line.lower() for p in patterns):
                    if first is None:
                        first = t
                    last = t

            if first is None:
                print(f"  {name:20} not found")
            else:
                print(f"  {name:20} {last - first:8.3f} s")

        print()


def main():
    config = load_config()
    logs = run_build()
    benchmark_main_phases(logs)
    benchmark_subphases(logs, config)


if __name__ == "__main__":
    main()
