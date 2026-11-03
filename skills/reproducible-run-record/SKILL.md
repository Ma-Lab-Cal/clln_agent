---
name: reproducible-run-record
description: Package a scientific simulation run into an auditable record linking the declared protocol, code identity, environment, raw artifacts, and reported claims. Use when preparing experiments, comparisons, or figures for review and reproduction.
---

# Reproducible run record

Make it possible for another researcher to identify what ran, reproduce the intended
comparison, and trace each reported quantity to an artifact.

Before running a comparison, record the question, inclusion/exclusion rules, seed
list, parameter grid, endpoint or stopping rule, observable definition, tolerances,
and analysis procedure. Timestamp later amendments and retain earlier declarations.
Distinguish exploratory analysis from a test that was specified in advance.

Capture the launch command, configuration, code commit or content hashes, dependency
and simulator versions, model/table identifiers, units, numerical settings, and input
data identity. Record uncommitted source changes if they affect the run. A path by
itself is not a durable identity.

For learned models, declare training, selection/validation, and final evaluation sets
and check overlap. Fix sample identities independently of training-set size. Select
settings on the declared validation set, then report the final evaluation according
to the fixed protocol. If historical results selected on evaluation data, label that
history; a new split does not retroactively make them untouched-test results.

Keep configurations, raw metrics, exclusions, logs, and analysis outputs together.
Record partial or interrupted runs as partial. A small model, surrogate run,
transistor-level simulation, and physical measurement support different claims.
Do not transfer evidence between them without a separate validation.

Create a manifest of the files actually needed to support the report, with relative
paths and SHA-256 hashes. Resolve paths within the run root. Verify after copying or
archiving. Do not re-seal a changed result merely to make verification pass; explain
and preserve the change. Hashes establish consistency relative to the manifest, not
authenticity or scientific validity. Preserve an immutable reference if tamper evidence
is required.

Return a compact run card: question, protocol, source/environment, artifact inventory,
reproduction command, results with uncertainty, exclusions, and limitations. A figure
caption should identify the input records and whether parameters were fitted on the
same records. Keep private data and unpublished results outside public packages unless
the user explicitly includes them in the release scope.
