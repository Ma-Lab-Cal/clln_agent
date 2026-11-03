"""Process-isolated ngspice runs and resumable, declared parameter campaigns."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from .checks import artifact_path, seal_run


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def simulator_version(executable="ngspice"):
    binary = shutil.which(executable)
    if not binary:
        raise FileNotFoundError(f"Simulator executable unavailable: {executable}")
    proc = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
    if proc.returncode:
        raise RuntimeError("Could not query simulator version")
    match = re.search(r"ngspice-\d+[^\n]*", proc.stdout + proc.stderr)
    return match.group(0).strip() if match else "ngspice (version unidentified)"


def parse_table(path):
    """Read wrdata with wr_singlescale and wr_vecnames enabled."""
    lines = Path(path).read_text().strip().splitlines()
    if len(lines) < 2:
        raise RuntimeError("Simulator returned an empty numerical table")
    names = lines[0].split()
    if len(set(names)) != len(names):
        raise RuntimeError("Ambiguous duplicate output-vector names")
    result = {name: [] for name in names}
    for line in lines[1:]:
        values = [float(x) for x in line.split()]
        if len(values) != len(names) or not all(math.isfinite(x) for x in values):
            raise RuntimeError("Malformed or nonfinite simulator output")
        for name, value in zip(names, values):
            result[name].append(value)
    return result


def run_spice(netlist, commands, vectors, *, executable="ngspice", timeout=30, save_dir=None):
    """Run a self-contained netlist. Each call owns one child process and directory."""
    binary = shutil.which(executable)
    if not binary:
        raise FileNotFoundError(f"Simulator executable unavailable: {executable}")
    if re.search(r"^\s*\.control\b", netlist, re.M | re.I):
        raise ValueError("Supply a netlist without an existing control block")
    if not vectors or any(not re.fullmatch(r"[vi]\([A-Za-z0-9_+#.-]+\)", x, re.I) for x in vectors):
        raise ValueError("Use explicitly named voltage or source-current vectors")
    body = re.sub(r"^\s*\.end\s*$", "", netlist, flags=re.M | re.I).strip()
    script = body + "\n.control\nset noaskquit\nset wr_singlescale\nset wr_vecnames\nset numdgt=15\n"
    script += "\n".join(commands) + "\nwrdata result.tsv " + " ".join(vectors)
    script += "\nquit\n.endc\n.end\n"
    with tempfile.TemporaryDirectory(prefix="simcheck-run-") as tmp:
        root = Path(tmp)
        (root / "input.cir").write_text(script)
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
        destination = Path(save_dir) if save_dir is not None else None
        if destination is not None:
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "input.cir").write_text(script)
        start = time.perf_counter()
        try:
            proc = subprocess.run([binary, "-n", "-b", "input.cir"], cwd=root, env=env,
                                  capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            if destination is not None:
                def decoded(value):
                    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
                (destination / "simulator.log").write_text(decoded(error.stdout)+decoded(error.stderr)+"\nTIMEOUT\n")
            raise
        elapsed = time.perf_counter() - start
        log = proc.stdout + proc.stderr
        if destination is not None:
            (destination / "simulator.log").write_text(log)
        table = root / "result.tsv"
        if proc.returncode or not table.exists() or re.search(r"^\s*(?:Error:|Fatal error)", log, re.M | re.I):
            raise RuntimeError(f"ngspice failed ({proc.returncode}): {log[-1600:]}")
        result = parse_table(table)
        if save_dir is not None:
            shutil.copy2(table, Path(save_dir) / "result.tsv")
        return {"vectors": result, "wall_seconds": elapsed, "log": log,
                "netlist_sha256": hashlib.sha256(netlist.encode()).hexdigest()}


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError("Cannot write an empty result table")
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_campaign(config_path, out, *, resume=False, executable="ngspice", workers=1):
    """Run a declared sweep, preserving individual success/failure records on restart."""
    config_path, out = Path(config_path), Path(out)
    config = json.loads(config_path.read_text())
    netlist_path = config_path.parent / config["netlist"]
    netlist = netlist_path.read_text()
    points = config["points"]
    if not points or len({p["id"] for p in points}) != len(points):
        raise ValueError("Campaign points need unique IDs")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", p["id"]) for p in points):
        raise ValueError("Point IDs may contain letters, digits, underscores, and hyphens")
    if not 1 <= workers <= 4:
        raise ValueError("Use one to four isolated workers")
    version = simulator_version(executable)
    identity = {"config": config, "netlist_sha256": hashlib.sha256(netlist.encode()).hexdigest(),
                "simulator": version,
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    signature = digest(identity)
    declaration = out / "declaration.json"
    if out.exists() and any(out.iterdir()) and not resume:
        raise ValueError("Use a fresh output directory, or --resume for the same declared campaign")
    out.mkdir(parents=True, exist_ok=True)
    if declaration.exists():
        previous = json.loads(declaration.read_text())
        if previous["signature"] != signature:
            raise ValueError("Resume refused: configuration, netlist, simulator, or runner changed")
    elif resume:
        raise ValueError("Resume requires an existing campaign declaration")
    else:
        declaration.write_text(json.dumps({"signature": signature, **identity}, indent=2) + "\n")
    records_path = out / "records.jsonl"
    completed = {}
    if records_path.exists():
        for line in records_path.read_text().splitlines():
            record = json.loads(line)
            if record["status"] == "passed":
                completed[record["id"]] = record
    # Verify recorded artifacts before skipping a completed point.
    for record in completed.values():
        for relative, expected in record["artifact_hashes"].items():
            path = artifact_path(out, relative)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Resume refused: a completed point's artifacts changed")
    pending = [point for point in points if point["id"] not in completed]

    def evaluate(point):
        directory = out / "points" / point["id"]
        try:
            result = run_spice(netlist, point.get("commands", []) + config["analysis"],
                               config["vectors"], executable=executable,
                               timeout=config.get("timeout_seconds", 30), save_dir=directory)
            paths = [directory / n for n in ("input.cir", "simulator.log", "result.tsv")]
            return {"id": point["id"], "status": "passed", "parameters": point.get("parameters", {}),
                    "wall_seconds": result["wall_seconds"], "vectors": result["vectors"],
                    "artifact_hashes": {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
        except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
            return {"id": point["id"], "status": "failed", "error": str(error)}

    with ThreadPoolExecutor(max_workers=workers) as pool, records_path.open("a") as stream:
        for future in as_completed([pool.submit(evaluate, point) for point in pending]):
            record = future.result()
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            stream.flush()
            completed[record["id"]] = record
    summary = {"declared_points": len(points), "executed_this_invocation": len(pending),
               "passed": sum(r["status"] == "passed" for r in completed.values()),
               "failed": sum(r["status"] != "passed" for r in completed.values()),
               "signature": signature, "simulator": version}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    artifacts = [str(p.relative_to(out)) for p in sorted(out.rglob("*"))
                 if p.is_file() and p.name != "manifest.json"]
    seal_run(out, artifacts, config={"campaign_signature": signature}, command="python -m simcheck sweep CONFIG --out RUN",
             seed=config.get("seed", 0), source_revision="runner-sha256:" + identity["runner_sha256"])
    return summary
