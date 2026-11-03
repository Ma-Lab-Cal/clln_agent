---
name: robustness-corner-analysis
description: Design and interpret circuit parameter, supply, temperature, noise, and mismatch sweeps with explicit models and reproducible draws. Use when evaluating how a simulated design behaves away from nominal conditions.
---

# Robustness and corner analysis

Declare the measured quantity, acceptance threshold, axes and ranges, corner grid,
random-draw model, seed list, and aggregation before reading results. Keep design
selection and final evaluation separate. Include the nominal circuit as a control.

Distinguish operating temperature from the model's nominal/reference temperature.
Check which temperature-dependent effects the model actually includes. A simple
device model does not establish process-calibrated leakage, self-heating, or yield.
Varying a model parameter numerically does not make its distribution a measured
manufacturing distribution.

Separate coherent shifts, independent device mismatch, input noise, and finite
parameter precision. Preserve correlation assumptions. Reuse the same draws across
corners when estimating paired differences, and record the actual sampled values
as well as seeds. Ensure positive parameters remain physical, for example through
a declared lognormal distribution rather than clipping unexplained negative draws.

First verify that the expanded/parameterized netlist reproduces the nominal model.
Record simulator nonconvergence separately from a circuit failing its specification.
Preserve failed points and partial runs; do not plot only successful corners.

Report the distributions across devices/draws separately from variation across
training or design seeds. Show nominal behavior, spread, and the worst tested
corner with the number of independent draws. Interpolated threshold crossings need
their grid resolution and interpolation rule. Small illustrative draw counts support
a sensitivity demonstration, not a production-yield estimate.

If calibration or compensation is tested, state which data fit its parameters and
which conditions evaluate it. Keep the uncorrected result beside the corrected one.
Return the declared protocol, raw corner table, reproducible draw records, numerical
failures, sensitivity plots, and a conclusion restricted to the modeled effects.
