# Reproducing the release

## Core examples and public studies

Use Python 3.10+ and an installed ngspice executable. The recorded CLI studies used ngspice 41; their exact settings and source-file hashes are in `results/public/config.json`. Run from the repository root:

```bash
python -m simcheck studies --out fresh-public-run
python -m simcheck verify fresh-public-run
python -m simcheck demo --out fresh-introduction --require-spice
```

The self-contained netlists need no proprietary process files. A campaign example is in `examples/inverter-campaign.json`. Its netlist path is resolved relative to that configuration file. Each point may provide simulator control commands, metadata, and an ID; the top-level `analysis` supplies the common analysis commands and `vectors` declares the exported quantities. Use known, reviewed netlists and commands for a new campaign.

```bash
python -m simcheck sweep examples/inverter-campaign.json --out fresh-campaign --workers 2
python -m simcheck sweep examples/inverter-campaign.json --out fresh-campaign --resume
```

A resume does not rerun successful, verified points. Failed points can be attempted on resume under the same declared configuration. There is no infinite retry loop.

## Optional shared-library performance replication

The recorded comparison includes separately built stock and locally patched ngspice 47, plus an installed ngspice 41 control. The 47 source archive URL, hash, build flags, library hashes, repetitions, and raw timings are included in `results/shared-benchmark/`. This is a specific source-version experiment, not a promise about every release.

Install the optional Python dependencies:

The recorded shared runs used PySpice 1.5, which warns about unfamiliar ngspice version numbers. These API paths and numerical checks ran successfully; broad compatibility with every binding feature is not claimed.

```bash
python -m pip install -r requirements-shared.txt
```

Obtain a disposable checkout of the `ngspice-47` tag from upstream or its read-only source mirror. The source archive used for this release is identified in `results/shared-benchmark/source-build.json`. With a C toolchain and autotools installed, build both variants:

```bash
bash tools/build_benchmark_libraries.sh /path/to/disposable-ngspice-47 /path/to/fresh-build-output
python -m simcheck.shared_benchmark run /path/to/fresh-build-output/libraries.json --out fresh-shared-run
```

The helper intentionally modifies that disposable source tree and preserves the stock library before building the patched one. The benchmark's JSON input maps labels to absolute shared-library paths on the reproducing machine. Published measurements retain labels and library hashes, not private paths. A ngspice 41 control can be added as another entry if available; it is unnecessary to compare the two 47 variants.

## Figures and documents

Install `requirements-figures.txt` to regenerate SVG/PNG plots from the checked-in records:

```bash
python -m pip install -r requirements-figures.txt
python tools/render_figures.py
```

Figure generation reads `results/public/` and `results/shared-benchmark/`. To adopt a new run, preserve the previous evidence, verify the replacement, and update the notes and validation record together. Do not silently replace old results.

PDF copies of the three technical notes can be regenerated after installing `requirements-documents.txt`:

```bash
python -m pip install -r requirements-documents.txt
python tools/render_documents.py
```

Hashes verify consistency with a manifest. They do not authenticate the author, establish experimental truth, or substitute for the numerical and scientific checks.
