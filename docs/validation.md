# CLLN project validation record

Validated on 2 November 2026. The checks describe this project collection and its fresh generic-circuit measurements. They do not establish the main CLLN scientific results, fabricated hardware, or measured improvement in agent performance.

| Check | Observed outcome |
|---|---|
| Standard-library and simulator integration suite | 17 tests passed, none skipped in the validation environment |
| Standalone skills | All six passed naming/frontmatter validation; instructions manually reviewed |
| Public studies | Complete run passed its declared checks; 1,610 device points and 45 robustness corner/draw points recorded |
| CLI batching | All compared outputs passed numerical tolerance across three sizes and three repetitions |
| Shared-library experiment | All-node voltage comparisons passed for three libraries, three sizes, and three worker rounds |
| Source patch | ngspice 47 baseline and local variant built with identical flags; only node-deletion source changed |
| Verification counterexamples | Unloaded XOR passed 4/4 points; loaded XOR passed 3/4, exposing the expected specification failure |
| Campaign resume | Completed points skipped only after hash checks; changed configurations and altered artifacts refused |
| Recorded artifacts | Public study and shared-benchmark manifests verified |
| CI | Workflow included; no GitHub execution claimed |

The [test log](test-results.txt) preserves the local suite outcome. Raw study records, explicit configs, input circuits, simulator logs, library identities, and source hashes are supplied under `results/`.

The CLI studies used the installed ngspice 41 executable. The optional shared study compared the installed 41 library with two separately built ngspice 47 libraries. Python versions and library hashes are in the respective records. The public studies require ngspice; a test run without it will skip the relevant integrations. Reproduction instructions are in [reproduction.md](reproduction.md).

The performance patch has not been tested against every device or analysis path in ngspice. The illustrated models are not calibrated process models. The five draws per corner are a sensitivity example, not a yield study. No controlled agent-efficacy study was run.
