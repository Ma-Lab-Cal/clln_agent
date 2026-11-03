---
name: spice-execution-performance
description: Set up, profile, and manage repeated SPICE simulations with explicit simulator identity, bounded workers, output cleanup, and numerical parity checks. Use for slow or memory-growing circuit campaigns.
---

# SPICE execution and performance

Separate process startup, circuit parsing/setup, nonlinear iteration, matrix work,
readout, and retained simulation data before choosing an optimization. Record the
actual executable or loaded shared-library version and build capabilities. A command
line option is not proof that its feature is compiled in or active.

Use the smallest representative workload that preserves the observed bottleneck.
Time cold starts separately from repeated analysis on a resident circuit. If inputs
can be altered without changing circuit structure, compare resident runs with reloads.
For a fixed circuit and parameter set, a DC sweep may amortize overhead; verify its
warm-started trajectory against independent operating points before adopting it.
Multistable circuits can follow different branches under continuation.

Preserve the equation contract. Adding leakage, removing device parasitics, changing
model level, loosening tolerances, or replacing a device is a model change, not a
pure execution optimization. Record those arms separately. Check voltages and the
decision-relevant currents or other observables, including near-zero regimes.

Shared-library simulators may keep global state. Use a separate process for each
library or independent worker unless its API explicitly supports isolation. Bound
parallelism; benchmark total throughput as well as individual latency, and account
for memory use and contention. Periodically remove obsolete output plots using the
simulator's supported lifecycle, retaining evidence needed for the report.

When a worker fails, retain its input and diagnostic output. Retry only within a
declared bound. Restore state from explicit parameters or a verified checkpoint;
never silently drop a point or change its seed. For long campaigns, preserve a
completed-point ledger and verify artifacts before resuming.

Report paired numerical agreement, timing scope, repetitions and spread, host/load
conditions, version/build differences, and the tested size range. A combined build
and configuration speedup does not isolate the effect of one patch. Treat historical
version-specific optimizations as hypotheses to re-test on the intended version.
