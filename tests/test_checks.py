import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from simcheck.checks import (compare, divider, gradient_sweep, implicit_gradient,
                             loss, seal_run, verify_run)
from simcheck.spice import spice_divider


class NumericalChecks(unittest.TestCase):
    def test_zero_reference_and_nonfinite_values(self):
        self.assertTrue(compare([0], [1e-10], atol=1e-9, rtol=0)["passed"])
        self.assertFalse(compare([0], [1e-7], atol=1e-9, rtol=0)["passed"])
        for x in [math.nan, math.inf, -math.inf]:
            self.assertFalse(compare([1], [x], atol=0, rtol=0)["passed"])

    def test_empty_or_mismatched_vectors_are_errors(self):
        for a,b in [([], []), ([1], [1, 2])]:
            with self.assertRaises(ValueError):
                compare(a,b,atol=0,rtol=0)

    def test_gradient_magnitude_error_cannot_hide_behind_cosine(self):
        x = [math.log(1e-3), math.log(5e-4)]
        grad = implicit_gradient(x)
        steps = [10**-k for k in range(1,7)]
        good = gradient_sweep(loss,x,grad,steps)
        bad = gradient_sweep(loss,x,[10*g for g in grad],steps)
        self.assertTrue(good["passed"])
        self.assertFalse(bad["passed"])
        self.assertGreater(bad["rows"][-1]["cosine"],0.999)

    def test_an_isolated_matching_step_does_not_pass(self):
        result = gradient_sweep(lambda p:p[0]**3,[1],[3.01],[0.2,0.1,0.05],atol=1e-9,rtol=0)
        self.assertEqual([r["passed"] for r in result["rows"]],[False,True,False])
        self.assertFalse(result["passed"])

    def test_omitted_shunt_conductance_changes_the_solution(self):
        self.assertAlmostEqual(divider(1.0),2/3)
        self.assertFalse(compare([divider(1.0)],[divider(1.0,leakage_s=1e-4)],atol=1e-6,rtol=1e-5)["passed"])


class RunRecords(unittest.TestCase):
    def test_tampering_and_missing_files_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"metrics.json";p.write_text('{"value": 1}')
            seal_run(tmp,["metrics.json"],config={},command="demo",seed=0,source_revision="example")
            self.assertTrue(verify_run(tmp)["passed"])
            p.write_text('{"value": 2}')
            self.assertFalse(verify_run(tmp)["passed"])
            p.unlink()
            self.assertFalse(verify_run(tmp)["passed"])

    def test_manifest_paths_cannot_escape_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"outside").write_text("private");(root/"run").mkdir()
            with self.assertRaises(ValueError):
                seal_run(root/"run",["../outside"],config={},command="demo",seed=0,source_revision="example")
            (root/"run"/"link").symlink_to(root/"outside")
            with self.assertRaises(ValueError):
                seal_run(root/"run",["link"],config={},command="demo",seed=0,source_revision="example")

    def test_duplicate_entries_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"a").write_text("x")
            with self.assertRaises(ValueError):
                seal_run(tmp,["a","a"],config={},command="demo",seed=0,source_revision="example")


@unittest.skipUnless(shutil.which("ngspice"),"ngspice is an optional external reference")
class IndependentReference(unittest.TestCase):
    def test_positive_zero_and_negative_voltage(self):
        values=[-1.0,0.0,0.25,1.0]
        self.assertTrue(compare([spice_divider(v) for v in values],
                                [divider(v) for v in values],atol=1e-9,rtol=1e-7)["passed"])


if __name__ == "__main__":
    unittest.main()
