---
name: convergence-stability-diagnosis
description: Diagnose nonlinear circuit convergence, multiple operating points, hysteresis, and transient stability. Use when a plausible DC solution, truth table, or solver success flag does not establish the intended circuit behavior.
---

# Convergence and stability diagnosis

Clarify whether the device is intended to be combinational, stateful, or oscillatory.
A latch legitimately has memory; that same state dependence may invalidate a proposed
combinational gate. Define the intended input, loading, supply, and timing contract.

Check physical residuals and numerical tolerances, not only a solver's status flag.
On a weakly held node, a small current residual can correspond to a large voltage
uncertainty. Tighten tolerances as a convergence control and inspect the device
currents or conductance that hold the node. Avoid interpreting a regularization-held
node as a robust physical voltage without testing that regularization.

Use multiple initial conditions and continuation in both directions where feasible.
Cluster distinct converged roots using a declared voltage tolerance; retain failed
starts. Finite sampling cannot prove uniqueness. A nodeset is a solver initial guess,
not a physical initial-condition experiment, and some simulators may stop near a
root rather than on it under loose tolerances.

A DC root need not be dynamically stable. Test transients with explicit capacitive
or dynamic elements and small perturbations of the operating point. State whether
the simulation begins from a solved operating point or explicit initial conditions.
Where a linear stability analysis is available, use the physical dynamic Jacobian
and capacitance model, not an arbitrary solver iteration Jacobian.

For a logic candidate, check sampled levels together with input current, output
load, interior input values, transition histories, timing, and relevant supply/model
corners. Declare logic thresholds and driver assumptions. An ideal voltage source
can hide the cost of powering an output through an input terminal.

Return the contract, roots found, failed starts, tolerance sensitivity, perturbation
traces, and an evidence-bounded classification. Distinguish demonstrated instability
or state dependence from a proof about all possible operating conditions.
