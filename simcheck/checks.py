"""Numerical comparisons, implicit sensitivities, and artifact verification.

All circuits and parameters in this module are textbook demonstration examples.
"""

import hashlib
import json
import math
from pathlib import Path


def compare(reference, candidate, *, atol, rtol):
    """Use |candidate-reference| <= atol + rtol*|reference|, per value."""
    if not reference or len(reference) != len(candidate):
        raise ValueError("Expected equally sized, nonempty vectors")
    if not all(math.isfinite(x) and x >= 0 for x in (atol, rtol)):
        raise ValueError("Tolerances must be finite and nonnegative")
    rows = []
    for expected, actual in zip(reference, candidate):
        finite = math.isfinite(expected) and math.isfinite(actual)
        error = abs(actual - expected) if finite else None
        limit = atol + rtol * abs(expected) if finite else None
        rows.append({"reference": expected if math.isfinite(expected) else None,
                     "candidate": actual if math.isfinite(actual) else None,
                     "absolute_error": error, "limit": limit,
                     "passed": finite and error <= limit})
    return {"passed": all(r["passed"] for r in rows), "rows": rows,
            "atol": atol, "rtol": rtol}


def divider(vin, r_top=1000.0, r_bottom=2000.0, leakage_s=0.0):
    """Voltage from KCL with an explicit shunt conductance (SI units)."""
    if r_top <= 0 or r_bottom <= 0 or leakage_s < 0:
        raise ValueError("Invalid passive circuit parameters")
    return (vin / r_top) / (1 / r_top + 1 / r_bottom + leakage_s)


def diode_state(log_g, vin=0.7):
    """Solve g(V-Vin)+g_load*V+Is*(exp(V/Vt)-1)=0 by bisection."""
    if len(log_g) != 2 or vin <= 0 or not math.isfinite(vin):
        raise ValueError("Expected two log-conductances and a positive voltage")
    g, load = (math.exp(x) for x in log_g)
    lo, hi = 0.0, vin
    for _ in range(100):
        v = (lo + hi) / 2
        f = g * (v - vin) + load * v + 1e-12 * math.expm1(v / 0.026)
        if f > 0:
            hi = v
        else:
            lo = v
    return (lo + hi) / 2


def loss(log_g):
    return 0.5 * (diode_state(log_g) - 0.3) ** 2


def implicit_gradient(log_g):
    """Implicit-function derivative of loss with respect to log conductances."""
    v = diode_state(log_g)
    g, load = (math.exp(x) for x in log_g)
    jacobian = g + load + 1e-12 / 0.026 * math.exp(v / 0.026)
    return [(v - 0.3) * g * (0.7 - v) / jacobian,
            -(v - 0.3) * load * v / jacobian]


def gradient_sweep(objective, point, gradient, steps, *, atol=1e-9, rtol=1e-4):
    """Return every finite-difference step; require two adjacent passing steps."""
    if not point or len(point) != len(gradient):
        raise ValueError("Gradient shape does not match the parameter vector")
    if len(steps) < 2 or any(h <= 0 or not math.isfinite(h) for h in steps):
        raise ValueError("Provide at least two positive, finite step sizes")
    if any(a <= b for a, b in zip(steps, steps[1:])):
        raise ValueError("Step sizes must strictly decrease")
    rows = []
    for h in steps:
        fd = []
        for i in range(len(point)):
            plus, minus = list(point), list(point)
            plus[i] += h
            minus[i] -= h
            fd.append((objective(plus) - objective(minus)) / (2 * h))
        result = compare(fd, gradient, atol=atol, rtol=rtol)
        denominator = math.sqrt(sum(x*x for x in fd) * sum(x*x for x in gradient))
        cosine = sum(a*b for a, b in zip(fd, gradient)) / denominator if denominator else None
        if cosine is not None and not math.isfinite(cosine):
            cosine = None
        rows.append({"step": h, "finite_difference": fd,
                     "analytic": [x if math.isfinite(x) else None for x in gradient],
                     "cosine": cosine,
                     "max_absolute_error": max((r["absolute_error"] for r in result["rows"]
                                                 if r["absolute_error"] is not None), default=None),
                     "passed": result["passed"]})
    adjacent = any(a["passed"] and b["passed"] for a, b in zip(rows, rows[1:]))
    return {"passed": adjacent, "criterion": "two adjacent step sizes pass componentwise",
            "atol": atol, "rtol": rtol, "rows": rows}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_path(root, relative):
    """Reject paths outside the run directory, including symlink escapes."""
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("Artifact path must remain inside its run directory")
    return path


def seal_run(root, artifacts, *, config, command, seed, source_revision):
    root = Path(root).resolve()
    if len(artifacts) != len(set(artifacts)):
        raise ValueError("Duplicate artifact paths")
    records = [{"path": str(p), "sha256": sha256(artifact_path(root, p))} for p in artifacts]
    manifest = {"schema_version": 1, "command": command, "seed": seed,
                "source_revision": source_revision, "config": config, "artifacts": records}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest


def verify_run(root):
    """Check the listed files against their recorded hashes, without running code."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema_version") != 1 or not manifest.get("artifacts"):
        raise ValueError("Unsupported or empty manifest")
    rows = []
    seen = set()
    for record in manifest["artifacts"]:
        relative = record["path"]
        if relative in seen:
            raise ValueError("Duplicate artifact paths")
        seen.add(relative)
        path = artifact_path(root, relative)
        actual = sha256(path) if path.is_file() else None
        rows.append({"path": relative, "passed": actual == record["sha256"],
                     "expected_sha256": record["sha256"], "actual_sha256": actual})
    return {"passed": all(row["passed"] for row in rows), "artifacts": rows,
            "limitation": "Hashes detect changes relative to this manifest; they do not authenticate its author or prove scientific validity."}
