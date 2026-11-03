# Agent entry point: Contrastive Local Learning Networks

This repository shares peripheral simulation methods and reproducible case studies
from Claude-assisted physical-learning work. Public examples are generic circuits.
Read this map before scanning generated results or changing a reported finding.

## Efficient reading order

1. `README.md`: scope, installation, entry commands, and case-study overview.
2. `docs/case-studies/`: three technical notes; each links to its raw evidence.
3. `docs/validation.md`: what ran, what passed, and what remains untested.
4. `docs/index.html`: offline visual overview. `docs/walkthrough.html` retains the
   smaller introductory checks. Both are portable review surfaces.
5. `simcheck/`: executable implementations. Read the specific module named by the CLI
   command instead of loading all results. `tests/` describes observable invariants.
6. `skills/`: six self-contained task skills. Load the one relevant to the request.

## Map

- `simcheck/checks.py`: numerical comparisons, implicit-gradient checks, artifact hashes.
- `simcheck/workbench.py`: subprocess simulator runner and resumable parameter campaigns.
- `simcheck/studies.py`: public circuit definitions and case-study measurements.
- `simcheck/shared_benchmark.py`: optional isolated shared-library timing comparisons.
- `simcheck/__main__.py`: CLI entry point (`python -m simcheck --help`).
- `examples/`: standard SPICE netlists and example sweep configuration.
- `results/public/`: recorded public experiments, configuration, raw CSV/JSON, and logs.
- `docs/figures/`: generated SVG/PNG figures with source records identified in the notes.
- `tools/`: reproduction and optional pinned simulator-build helpers.
- `third_party/`: upstream notices and the version-scoped simulator patch.

The validation record states the completed checks. The GitHub workflow is provided
for future publication; no hosted CI result is claimed in this local release.

## Reproduce and validate

Core checks use Python 3.10+. Install ngspice for the public circuit studies.
The optional shared-library benchmark also needs NumPy and PySpice.

- `python -m unittest discover -s tests -v`
- `python -m simcheck demo --out FRESH_DIRECTORY --require-spice`
- `python -m simcheck studies --out FRESH_DIRECTORY`
- `python -m simcheck verify RUN_DIRECTORY`
- `python -m simcheck --help` lists core and campaign commands. The optional benchmark
  uses `python -m simcheck.shared_benchmark --help`.

Use a fresh output directory for a new study. Resume only the same declared campaign.
Do not edit recorded numerical outputs or re-seal changed results to conceal a
discrepancy. Regenerate into a new directory, inspect changes, then update figures,
notes, source hashes, and the validation record together.

## Scientific and disclosure boundaries

These examples establish bounded simulation and verification findings. They do not
establish device fabrication, a new circuit topology, a universal speedup, or measured
agent-performance improvement. Keep numerical settings, versions, timing scope,
partial results, and failed checks explicit. Preserve third-party attribution.

Do not introduce private research figures, CLLN architectures, trained parameters,
unpublished physical laws, device cards, account information, or original research
logs. The public repo has no dependency on the private research tree. Publishing or
emailing is a separate user action; this file grants no external-action authority.
