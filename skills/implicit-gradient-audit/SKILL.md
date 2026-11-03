---
name: implicit-gradient-audit
description: Check derivatives through an implicit physical simulation using converged state residuals and a finite-difference step sweep. Use to diagnose sign, scale, branch, or parameterization errors before trusting an optimizer.
---

# Implicit gradient audit

Determine whether the supplied derivative matches the declared scalar objective with
respect to the actual optimization parameters, at a specific converged state.

Write the contract as `F(x, theta) = 0` and `L(x, theta)`. Confirm whether theta is
a physical value, a logarithm, a normalized variable, or a transformed constrained
parameter. Include both explicit and state-mediated terms in the derivative. For a
smooth nonsingular branch, `dx/dtheta = -(dF/dx)^(-1) (dF/dtheta)`.

Check that the forward solve converges and that its residual is sufficiently small
for the intended perturbations. A derivative through an unconverged last iteration
can agree with that iteration while failing to describe the physical root. Make
solver tolerance, branch selection, stochastic state, and warm-start behavior explicit.

Use central differences on several decreasing step sizes. Fix randomness or use a
declared common-random-numbers protocol. Perturb the same parameterization used by the
optimizer, solve both perturbed states to the same standard, and retain every row of
the sweep. At a bound, use a documented feasible one-sided difference or an interior
point; do not silently clip perturbations.

Compare sign, absolute error, relative error, and vector direction. A cosine near one
can conceal a large multiplicative error. Choose tolerances from objective scale and
solver accuracy, and look for adjacent step sizes that agree before cancellation
dominates. A single lucky step is insufficient. Include near-zero components, where
absolute tolerance controls the verdict. The textbook demo's adjacent-step rule is
a diagnostic convention, not a proof of differentiability.

If perturbations change the solution branch, encounter a singular Jacobian, or cross
a nonsmooth element boundary, report that limitation and evaluate an appropriate
local/one-sided question. Do not repair a disagreement by fitting the derivative's
scale to the finite-difference answer.

Use a controlled wrong-sign or wrong-scale derivative on a scratch example to verify
that the audit can fail. Return the residuals, parameterization and units, perturbation
steps, componentwise comparison, branch/convergence exclusions, and a bounded verdict.
Keep the evidence separate from any claim that an approximate local learning rule
must equal an exact objective gradient.
