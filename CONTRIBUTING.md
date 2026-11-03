# Contributing

Keep examples small enough to inspect and reproduce with the Python standard library.
New scientific checks should include a correct case and a controlled failure case,
with evidence that the decision changes for the intended reason.

Run `python -m unittest discover -s tests -v` and the demo before proposing changes.
If ngspice is absent, report the skipped independent reference. A new run goes into
a fresh output directory; preserve the input records for published figures.

Keep skill instructions self-contained and specific to the named task. Behavior
claims about an agent require separate evaluation; passing a format validator is
not evidence that the skill improves an agent's scientific decisions.

Use textbook, synthetic, or explicitly authorized public inputs for examples.
