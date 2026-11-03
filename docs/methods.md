# Method notes

The examples use simple physical equations so every reference is inspectable.

## Solver comparison

For a voltage divider, KCL gives
`Vout = (Vin/Rtop)/(1/Rtop + 1/Rbottom + gleak)`.
The declared reference uses Rtop = 1,000 ohms, Rbottom = 2,000 ohms, and no shunt
conductance. The fault control uses an extra 0.0001 S shunt in one implementation.
This intentionally changes the problem and therefore fails parity. The zero-volt
point still agrees: the decision uses all points, rather than one favorable example.

The independent reference launches the installed ngspice executable with a fresh
temporary netlist, disables user startup files with `-n`, and reads the operating
point. The helper supports this divider only. An unavailable ngspice is a skip;
a timeout, failed process, missing output, or disagreement is an error/failure.
See the [official simulator documentation](https://ngspice.sourceforge.io/docs.html).

## Gradient comparison

The forward equation is
`g*(V - 0.7) + gload*V + 1e-12*(exp(V/0.026)-1) = 0`.
The objective is `0.5*(V - 0.3)^2`, and the two optimization parameters are
`log(g)` and `log(gload)`. The positive derivative of the residual with respect
to V makes this example monotone; bisection solves the unique physical root.

The analytic implicit derivative is compared with central differences from step
0.1 through 0.000001. The decision requires two adjacent steps to pass the declared
componentwise absolute and relative tolerances. Multiplying both derivative
components by ten leaves cosine similarity close to one, while the magnitude
test fails. This is a teaching example, not a guarantee for arbitrary nonsmooth
or multistable simulations.

## Artifact records

The demo records its Python version, source-file content hashes, units, and commands.
Its manifest hashes the JSON report and both generated SVGs. A scratch negative
control alters a sealed metrics file and confirms a verification failure.
The manifest itself is not signed. Someone able to alter both a file and its
manifest can replace both; the check does not prove integrity against that actor.

The record skill additionally describes experiment declarations, split hygiene,
and partial-run labeling. Those practices are instructions for real projects;
this toy demo has no training dataset or classifier accuracy to evaluate.
