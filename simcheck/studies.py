"""Reproducible public case studies using generic, self-contained SPICE circuits."""

import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import time

from .checks import compare, seal_run
from .workbench import run_spice, simulator_version, write_csv


MODELS = """.model NGEN NMOS (LEVEL=1 VTO=0.45 KP=150u LAMBDA=0.02)
.model PGEN PMOS (LEVEL=1 VTO=-0.45 KP=60u LAMBDA=0.02)
.options reltol=1e-7 abstol=1e-14 vntol=1e-9 gmin=1e-12
.temp 27
"""


def inverter(vdd=1.8):
    return f"""Generic CMOS inverter; illustrative Level-1 models, no process calibration
VDD vdd 0 {vdd}
VIN in 0 0
MP out in vdd vdd PGEN W=5u L=1u
MN out in 0 0 NGEN W=2u L=1u
CL out 0 1p
{MODELS}.end
"""


def diode_bank(size):
    """Independent diode branches stress analysis setup/teardown, not dense linear algebra."""
    lines = [f"Generic diode bank with {size} branches", "VIN in 0 0.8",
             ".model DB D(IS=1e-12 N=1.2 RS=20)",
             ".options reltol=1e-7 abstol=1e-14 vntol=1e-9 gmin=1e-12"]
    for i in range(size):
        node = "out" if i == 0 else f"n{i}"
        lines += [f"R{i} in {node} {1000 + i % 17}", f"D{i} {node} 0 DB"]
    return "\n".join(lines) + "\n.end\n"


def xor_gate(load=None):
    """Textbook transmission-gate mux implementing A?~B:B, with two input inverters."""
    lines = ["Textbook transmission-gate XOR, no new topology", "VDD vdd 0 1.8", "VA a 0 0", "VB b 0 0",
             "MPA ab a vdd vdd PGEN W=5u L=1u", "MNA ab a 0 0 NGEN W=2u L=1u",
             "MPB bb b vdd vdd PGEN W=5u L=1u", "MNB bb b 0 0 NGEN W=2u L=1u",
             "MNT out ab b 0 NGEN W=2u L=1u", "MPT out a b vdd PGEN W=5u L=1u",
             "MNF out a bb 0 NGEN W=2u L=1u", "MPF out ab bb vdd PGEN W=5u L=1u", "CL out 0 1p"]
    if load:
        lines.append(f"RL out 0 {load}")
    return "\n".join(lines) + "\n" + MODELS + ".end\n"


def latch():
    return """Textbook cross-coupled CMOS latch
VDD vdd 0 1.8
MP1 q qb vdd vdd PGEN W=5u L=1u
MN1 q qb 0 0 NGEN W=2u L=1u
MP2 qb q vdd vdd PGEN W=5u L=1u
MN2 qb q 0 0 NGEN W=2u L=1u
C1 q 0 1p
C2 qb 0 1p
""" + MODELS + ".end\n"


def interpolate(x, xp, yp):
    if x <= xp[0]:return yp[0]
    if x >= xp[-1]:return yp[-1]
    for i in range(1, len(xp)):
        if x <= xp[i]:
            t = (x - xp[i-1]) / (xp[i] - xp[i-1])
            return yp[i-1] * (1-t) + yp[i] * t
    raise ValueError("Interpolation point outside interval")


def performance_study(out, executable):
    out.mkdir()
    rows = []
    for size in (16, 128, 512):
        circuit = diode_bank(size)
        (out / f"bank-{size}.cir").write_text(circuit)
        for repetition in range(3):
            separate, total = [], 0.0
            # Alternate arm order across repetitions to reduce order effects.
            def independent():
                nonlocal total, separate
                for i in range(9):
                    value = .4 + .05 * i
                    r = run_spice(circuit, [f"alter VIN dc={value:.12g}", "op"], ["v(out)"],
                                  executable=executable, save_dir=out/f"independent-{size}-{repetition}-{i}")
                    total += r["wall_seconds"]
                    separate.append(r["vectors"]["v(out)"][0])
            def batched():
                return run_spice(circuit, ["dc VIN 0.4 0.8 0.05"], ["v(out)"], executable=executable,
                                 save_dir=out/f"batch-{size}-{repetition}")
            if repetition % 2:
                batch = batched(); independent()
            else:
                independent(); batch = batched()
            parity = compare(separate, batch["vectors"]["v(out)"], atol=1e-7, rtol=1e-6)
            rows.append({"branches": size, "repetition": repetition, "points": 9,
                         "independent_process_seconds": total, "one_sweep_seconds": batch["wall_seconds"],
                         "ratio": total/batch["wall_seconds"], "parity_passed": parity["passed"],
                         "max_voltage_error_v": max(r["absolute_error"] for r in parity["rows"])})
    write_csv(out/"timings.csv", rows)
    result = {"comparison": "nine independent CLI processes versus one CLI DC sweep",
              "timing_scope": "wall time includes process launch, simulation, and readout; not a patch-only speedup",
              "rows": rows, "all_parity_passed": all(r["parity_passed"] for r in rows),
              "median_ratios": {str(n): statistics.median(r["ratio"] for r in rows if r["branches"] == n)
                                for n in (16,128,512)}}
    (out/"summary.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def approximation_study(out, executable):
    out.mkdir()
    rows=[]
    for gmin in (1e-8, 1e-12):
        for source in (0.0, .1, .2, .3, .4):
            drain = source + .2
            circuit = f"""Generic single MOS device terminal-current audit
VD d 0 {drain:.12g}
VS s 0 {source:.12g}
VG g 0 0
VB b 0 0
M1 d g s b NM W=1u L=1u
.model NM NMOS (LEVEL=1 VTO=0.7 KP=100u LAMBDA=0 GAMMA=0 IS=1e-14)
.options gmin={gmin:.12g} reltol=1e-8 abstol=1e-16 vntol=1e-10
.temp 27
.end
"""
            r=run_spice(circuit,["dc VG 0 1.6 0.01"],["i(VD)","i(VS)","i(VB)"], executable=executable,
                        save_dir=out/f"device-g{gmin:.0e}-s{source:.1f}")
            values=r["vectors"];scale=values[next(iter(values))]
            ids=[-x for x in values["i(VD)"]]; iss=values["i(VS)"];ibs=values["i(VB)"]
            coarse_i=list(range(0,len(scale),40))
            if coarse_i[-1]!=len(scale)-1:coarse_i.append(len(scale)-1)
            xp=[scale[i] for i in coarse_i];yp=[ids[i] for i in coarse_i]
            for gate, current, source_out, bulk in zip(scale,ids,iss,ibs):
                approx=interpolate(gate,xp,yp)
                rows.append({"gmin_s":gmin,"source_v":source,"gate_v":gate,
                             "overdrive_v":gate-source-.7,"drain_in_a":current,"source_out_a":source_out,
                             "bulk_source_a":bulk,"terminal_difference_a":current-source_out,
                             "terminal_kcl_error_a":abs(-current+source_out+bulk),
                             "coarse_drain_a":approx,"coarse_error_a":abs(approx-current),
                             "coarse_relative_error":abs(approx-current)/max(abs(current),1e-9)})
    write_csv(out/"device-points.csv",rows)
    active=[r for r in rows if r["drain_in_a"]>1e-9]
    near=[r for r in active if 0<r["overdrive_v"]<.2]
    result={"points":len(rows),"max_terminal_kcl_error_a":max(r["terminal_kcl_error_a"] for r in rows),
            "max_drain_source_difference_a":max(abs(r["terminal_difference_a"]) for r in rows),
            "near_threshold_coarse_relative_error_median":statistics.median(r["coarse_relative_error"] for r in near),
            "near_threshold_coarse_relative_error_max":max(r["coarse_relative_error"] for r in near),
            "relative_error_floor_a":1e-9,"coarse_gate_grid_v":[0,.4,.8,1.2,1.6],
            "model_scope":"Illustrative Level-1 model with hard cutoff; no calibrated process or subthreshold claim"}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


def verification_study(out,executable):
    out.mkdir();rows=[]
    for load in (None,10000):
        circuit=xor_gate(load)
        (out/("xor-unloaded.cir" if load is None else "xor-loaded.cir")).write_text(circuit)
        for a,b in ((0,0),(0,1),(1,0),(1,1)):
            r=run_spice(circuit,[f"alter VA dc={a*1.8}",f"alter VB dc={b*1.8}","op"],
                        ["v(out)","i(VA)","i(VB)","i(VDD)"],executable=executable,
                        save_dir=out/f"xor-{load}-{a}{b}")
            v=r["vectors"];expected=a^b;output=v['v(out)'][0]
            rows.append({"load_ohm":load or 0,"a":a,"b":b,"expected":expected,"output_v":output,
                         "logic_passed":output>=1.26 if expected else output<=.54,
                         "input_a_current_a":v['i(VA)'][0],"input_b_current_a":v['i(VB)'][0],
                         "supply_current_a":v['i(VDD)'][0]})
    write_csv(out/"xor-verification.csv",rows)
    latch_rows=[]
    for i,(q,qb) in enumerate(((0,1.8),(1.8,0),(.9,.9))):
        circuit=latch().replace('.end',f'.nodeset v(q)={q} v(qb)={qb}\n.end')
        r=run_spice(circuit,["op"],["v(q)","v(qb)"],executable=executable,save_dir=out/f"latch-op-{i}")
        latch_rows.append({"start_q_v":q,"start_qb_v":qb,"q_v":r['vectors']['v(q)'][0],"qb_v":r['vectors']['v(qb)'][0]})
    write_csv(out/"latch-operating-points.csv",latch_rows)
    for label,delta in (("positive",1e-5),("negative",-1e-5)):
        circuit=latch().replace('.end',f'.ic v(q)={.9+delta} v(qb)={.9-delta}\n.end')
        r=run_spice(circuit,["tran 0.2n 200n uic"],["v(q)","v(qb)"],executable=executable,save_dir=out/f"latch-transient-{label}")
        values=r['vectors'];names=list(values)
        write_csv(out/f"latch-transient-{label}.csv",[dict(zip(names,row)) for row in zip(*(values[n] for n in names))])
    (out/"latch.cir").write_text(latch())
    result={"xor_rows":rows,"all_sampled_logic_levels_passed":all(r['logic_passed'] for r in rows),
            "unloaded_logic_passed":all(r['logic_passed'] for r in rows if not r['load_ohm']),
            "loaded_logic_pass_count":sum(r['logic_passed'] for r in rows if r['load_ohm']),
            "max_loaded_input_current_a":max(abs(r['input_b_current_a']) for r in rows if r['load_ohm']),
            "latch_operating_points":latch_rows,
            "scope":"Known transmission-gate XOR and cross-coupled latch; distinct examples of input loading and state dependence, not new logic designs"}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


def robustness_study(out,executable):
    out.mkdir();rows=[]
    for supply in (1.6,1.8,2.0):
        for temperature in (-20,27,85):
            for seed in range(5):
                rng=random.Random(seed);dv_n=rng.gauss(0,.025);dv_p=rng.gauss(0,.025)
                gain_n=math.exp(rng.gauss(0,.08));gain_p=math.exp(rng.gauss(0,.08))
                circuit=inverter(supply).replace('VTO=0.45 KP=150u',f'VTO={.45+dv_n:.12g} KP={150e-6*gain_n:.12g}')
                circuit=circuit.replace('VTO=-0.45 KP=60u',f'VTO={-.45+dv_p:.12g} KP={60e-6*gain_p:.12g}')
                circuit=circuit.replace('.temp 27',f'.temp {temperature}')
                result=run_spice(circuit,[f"dc VIN 0 {supply} {supply/180}"],["v(out)"],executable=executable,
                                 save_dir=out/f"v{supply}-t{temperature}-s{seed}")
                values=result['vectors'];x=values[next(iter(values))];y=values['v(out)'];trip=None
                for i in range(1,len(x)):
                    if y[i]<=supply/2<=y[i-1]:
                        trip=x[i-1]+(x[i]-x[i-1])*(y[i-1]-supply/2)/(y[i-1]-y[i]);break
                if trip is None:raise RuntimeError('Inverter sweep has no mid-supply crossing')
                rows.append({'supply_v':supply,'temperature_c':temperature,'seed':seed,'trip_v':trip,
                             'trip_fraction':trip/supply,'vto_n_v':.45+dv_n,'vto_p_v':-.45+dv_p,
                             'kp_n_a_per_v2':150e-6*gain_n,'kp_p_a_per_v2':60e-6*gain_p})
    write_csv(out/'corners.csv',rows)
    summary={'rows':len(rows),'draws_per_corner':5,'nominal_model_temperature_c':27,
             'same_parameter_draws_across_corners':True,
             'trip_fraction_min':min(r['trip_fraction'] for r in rows),'trip_fraction_max':max(r['trip_fraction'] for r in rows),
             'scope':'Illustrative Level-1 model sensitivity; five draws are not a manufacturing-yield estimate'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def run_studies(out,executable='ngspice'):
    out=Path(out)
    if out.exists() and any(out.iterdir()):raise ValueError('Study output directory must be fresh')
    out.mkdir(parents=True,exist_ok=True)
    version=simulator_version(executable)
    source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}
    config={'schema_version':1,'data_origin':'Fresh generic-circuit measurements, generated for this public release',
            'simulator':version,'python':platform.python_version(),'source_sha256':source,
            'timing_repetitions':3,'threads_per_simulator':1,'robustness_seeds':list(range(5))}
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    result={'performance':performance_study(out/'performance',executable),
            'approximation':approximation_study(out/'approximation',executable),
            'verification':verification_study(out/'verification',executable),
            'robustness':robustness_study(out/'robustness',executable)}
    result['passed']=(result['performance']['all_parity_passed'] and result['approximation']['max_terminal_kcl_error_a']<1e-12
                      and result['verification']['unloaded_logic_passed']
                      and result['verification']['max_loaded_input_current_a']>1e-6)
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    artifacts=[str(p.relative_to(out)) for p in sorted(out.rglob('*')) if p.is_file()]
    seal_run(out,artifacts,config=config,command='python -m simcheck studies --out RUN_DIRECTORY',seed=0,
             source_revision='sources-sha256:'+hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest())
    return result
