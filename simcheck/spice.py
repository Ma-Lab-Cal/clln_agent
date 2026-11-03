"""Optional independent ngspice operating-point reference for a resistor divider."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def spice_divider(vin, executable="ngspice"):
    binary = shutil.which(executable)
    if binary is None:
        raise FileNotFoundError("ngspice executable is unavailable")
    with tempfile.TemporaryDirectory(prefix="simcheck-") as directory:
        root = Path(directory)
        netlist = root / "divider.cir"
        netlist.write_text(f"""Textbook voltage divider, all values in SI
V1 in 0 {vin:.17g}
R1 in out 1000
R2 out 0 2000
.control
set numdgt=15
op
print v(out)
quit
.endc
.end
""")
        result = subprocess.run([binary, "-n", "-b", str(netlist)], cwd=root,
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise RuntimeError("ngspice failed: " + (result.stdout + result.stderr)[-1500:])
        matches = re.findall(r"v\(out\)\s*=\s*([-+0-9.eE]+)", result.stdout, re.I)
        if not matches:
            raise RuntimeError("ngspice returned no operating-point voltage")
        return float(matches[-1])
