---
name: solver-parity
description: Audit a physical simulation or surrogate against an independent reference, including units, boundary conditions, numerical regularizers, operating regimes, and residuals. Use for solver equivalence checks, not claims of experimental hardware validation.
---

# Solver parity

Produce a comparison that answers whether both implementations solve the same declared
physical problem over the domain that matters to the user.

Establish the equation contract before comparing outputs: terminal conventions, SI
units or explicit conversions, boundary conditions, material/device parameters,
temperature, regularizers, tolerances, and data-table identity. Treat a stabilizing
shunt or junction conductance as part of the equations. Identify which source/current
sign and terminal each implementation returns; currents at different terminals need
not be interchangeable when there is leakage.

Use an independent reference when available. Comparing two wrappers around the same
backend is a consistency check, not independent validation. Identify the actual loaded
simulator/version and any fallback tables or reduced models. A missing reference is
a named gap; do not substitute a self-comparison and report parity.

Choose points before examining the discrepancies. Include ordinary operating points,
near-zero responses, regime boundaries, and the edges of the claimed domain. Compare
converged states only, while counting and reporting nonconverged or excluded points.
Where applicable, read the physical residual as well as the state error. If tightening
tolerances changes the result, resolve numerical convergence before interpreting physics.

Use a declared combined tolerance per value:
`abs(candidate - reference) <= atol + rtol * abs(reference)`.
Explain the units and scientific purpose of `atol` and `rtol`. Nonfinite outputs fail.
Report the worst cases and coverage per regime; a small average can hide a failing corner.

For a new check, introduce one controlled mismatch on a scratch example, such as an
omitted shunt or a unit conversion error. Confirm the check detects it. Keep the fault
separate from scientific data and restore the correct setup.

Return the problem contract, commands/environment, sample construction, convergence
counts, comparison table, and a verdict bounded to the tested domain. Distinguish
model agreement from agreement with measurements. Retain raw numerical records so a
plot can be regenerated. If the reference is unavailable or coverage is incomplete,
state exactly which conclusion remains untested.
