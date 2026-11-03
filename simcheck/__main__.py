import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

from .checks import (compare, divider, gradient_sweep, implicit_gradient,
                     loss, seal_run, verify_run)
from .spice import spice_divider


def chart(title, x_label, y_label, series, *, log_x=False, log_y=False):
    """Small standalone SVG. Coordinates are generated from the numerical records."""
    from html import escape
    all_x = [p[0] for s in series for p in s["points"]]
    all_y = [p[1] for s in series for p in s["points"]]
    transform_x = (lambda v: math.log10(max(v, 1e-20))) if log_x else (lambda v:v)
    transform_y = (lambda v: math.log10(max(v, 1e-20))) if log_y else (lambda v:v)
    xs, ys = list(map(transform_x, all_x)), list(map(transform_y, all_y))
    xmin,xmax,ymin,ymax = min(xs),max(xs),min(ys),max(ys)
    if ymax == ymin:ymax += 1
    pad=(ymax-ymin)*0.08;ymin-=pad;ymax+=pad
    px=lambda x:86+510*(transform_x(x)-xmin)/(xmax-xmin or 1)
    py=lambda y:306-220*(transform_y(y)-ymin)/(ymax-ymin)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 420" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(x_label)} versus {escape(y_label)}. Textbook demonstration data.</desc>',
           '<rect width="680" height="420" rx="18" fill="#faf8f4"/>',
           f'<text x="36" y="40" font-family="sans-serif" font-size="20" fill="#233a37">{escape(title)}</text>']
    for i in range(5):
        val=ymin+(ymax-ymin)*i/4;y=306-220*i/4
        raw=10**val if log_y else val
        parts.append(f'<path d="M86 {y}H596" stroke="#deddd6"/><text x="76" y="{y+4}" text-anchor="end" font-family="sans-serif" font-size="12" fill="#53625c">{raw:.1e}</text>')
    for i in range(5):
        val=xmin+(xmax-xmin)*i/4;x=86+510*i/4;raw=10**val if log_x else val
        parts.append(f'<text x="{x}" y="328" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#53625c">{raw:.1g}</text>')
    parts.append('<path d="M86 80V306H596" fill="none" stroke="#53625c"/>')
    for i,s in enumerate(series):
        points=' '.join(f'{px(x):.2f},{py(y):.2f}' for x,y in s['points'])
        parts.append(f'<g id="series-{i}"><title>{escape(s["label"])}</title><polyline points="{points}" fill="none" stroke="{s["color"]}" stroke-width="3"/>')
        for x,y in s['points']:
            parts.append(f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="3" fill="{s["color"]}"/>')
        parts.append(f'<text x="{86+i*245}" y="388" font-family="sans-serif" font-size="13" fill="{s["color"]}">{escape(s["label"])}</text></g>')
    parts.append(f'<text x="341" y="355" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#233a37">{escape(x_label)}</text>')
    parts.append(f'<text x="36" y="67" font-family="sans-serif" font-size="12" fill="#53625c">{escape(y_label)}</text></svg>')
    return ''.join(parts)


def run_demo(out, require_spice=False):
    out=Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be empty; choose a fresh --out path")
    out.mkdir(parents=True,exist_ok=True)
    vin=[i/20 for i in range(-20,21)]
    reference=[v*2000/(1000+2000) for v in vin]
    actual=[divider(v) for v in vin]
    flawed=[divider(v,leakage_s=1e-4) for v in vin]
    parity=compare(reference,actual,atol=1e-9,rtol=1e-7)
    bad_parity=compare(reference,flawed,atol=1e-9,rtol=1e-7)
    spice={"status":"skipped","reason":"ngspice is not installed"}
    if shutil.which("ngspice"):
        points=[-1.0,0.0,0.25,1.0]
        result=compare([spice_divider(v) for v in points],[divider(v) for v in points],atol=1e-9,rtol=1e-7)
        version=subprocess.run(["ngspice","--version"],capture_output=True,text=True,timeout=10)
        spice={"status":"passed" if result["passed"] else "failed",
               "inputs_v":points,"comparison":result,
               "version":next((s.strip() for s in version.stdout.splitlines() if 'ngspice-' in s),'unknown')}
    elif require_spice:
        raise FileNotFoundError("--require-spice requested, but ngspice is absent")
    point=[math.log(1e-3),math.log(5e-4)]
    grad=implicit_gradient(point);steps=[10**-k for k in range(1,7)]
    good_gradient=gradient_sweep(loss,point,grad,steps)
    bad_gradient=gradient_sweep(loss,point,[10*g for g in grad],steps)
    with tempfile.TemporaryDirectory(prefix="simcheck-control-") as tmp:
        metric=Path(tmp)/"metrics.json";metric.write_text('{"voltage_v": 0.5}\n')
        seal_run(tmp,["metrics.json"],config={"example":"textbook"},command="negative-control",seed=0,source_revision="demo")
        before=verify_run(tmp);metric.write_text('{"voltage_v": 0.6}\n');after=verify_run(tmp)
    report={"data_origin":"Fresh textbook and synthetic demonstrations; no research measurements.",
            "parity":{"inputs_v":vin,"reference_v":reference,"candidate_v":actual,"flawed_v":flawed,
                      "correct":parity,"omitted_shunt_control":bad_parity,
                      "independent_ngspice":spice},
            "gradient":{"correct":good_gradient,"tenfold_scale_control":bad_gradient},
            "provenance":{"before":before,"after_mutation":after},
            "expected_outcomes_met":parity["passed"] and not bad_parity["passed"] and
              good_gradient["passed"] and not bad_gradient["passed"] and before["passed"] and
              not after["passed"] and spice["status"]!="failed"}
    (out/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (out/"parity.svg").write_text(chart("Does the solver solve the declared circuit?","Input voltage (V)","Output voltage (V)",[
        {"label":"Reference / correct KCL","color":"#176b62","points":list(zip(vin,reference))},
        {"label":"Unaccounted shunt control","color":"#b35b3b","points":list(zip(vin,flawed))}]))
    (out/"gradient.svg").write_text(chart("A correct direction can hide a wrong scale","Finite-difference step","Maximum derivative error",[
        {"label":"Correct implicit derivative","color":"#176b62","points":[(r['step'],max(r['max_absolute_error'],1e-20)) for r in good_gradient['rows']]},
        {"label":"Derivative multiplied by ten","color":"#b35b3b","points":[(r['step'],r['max_absolute_error']) for r in bad_gradient['rows']]}],log_x=True,log_y=True))
    source_files=sorted(Path(__file__).parent.glob('*.py'))
    source_digest=hashlib.sha256(b''.join(p.name.encode()+b'\0'+p.read_bytes() for p in source_files)).hexdigest()
    seal_run(out,["report.json","parity.svg","gradient.svg"],
             config={"python":platform.python_version(),"data_origin":"textbook examples","units":"SI",
                     "source_files_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}},
             command="python -m simcheck demo --out RUN_DIRECTORY",seed=0,source_revision="source-sha256:"+source_digest)
    return {"expected_outcomes_met":report["expected_outcomes_met"],
            "ngspice_status":spice["status"],"sealed_artifacts_valid":verify_run(out)["passed"]}


def main():
    parser=argparse.ArgumentParser(description="Auditable textbook simulation checks")
    sub=parser.add_subparsers(dest="command",required=True)
    demo=sub.add_parser("demo",help="Run positive and deliberately faulty examples")
    demo.add_argument("--out",type=Path,required=True)
    demo.add_argument("--require-spice",action="store_true")
    verify=sub.add_parser("verify",help="Check a run's artifact hashes")
    verify.add_argument("run",type=Path)
    study=sub.add_parser("studies",help="Reproduce the public SPICE case studies")
    study.add_argument("--out",type=Path,required=True)
    study.add_argument("--executable",default="ngspice")
    sweep=sub.add_parser("sweep",help="Run or resume a declared parameter campaign")
    sweep.add_argument("config",type=Path)
    sweep.add_argument("--out",type=Path,required=True)
    sweep.add_argument("--resume",action="store_true")
    sweep.add_argument("--workers",type=int,default=1)
    sweep.add_argument("--executable",default="ngspice")
    args=parser.parse_args()
    try:
        if args.command=="demo":
            result=run_demo(args.out,args.require_spice)
        elif args.command=="studies":
            from .studies import run_studies
            result=run_studies(args.out,args.executable)
        elif args.command=="sweep":
            from .workbench import run_campaign
            result=run_campaign(args.config,args.out,resume=args.resume,workers=args.workers,executable=args.executable)
        else:
            result=verify_run(args.run)
    except (ValueError,OSError,KeyError,RuntimeError,subprocess.TimeoutExpired) as error:
        parser.exit(2,f"simcheck: {error}\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if args.command=="demo":success=result["expected_outcomes_met"] and result["sealed_artifacts_valid"]
    elif args.command=="sweep":success=result["passed"]==result["declared_points"] and result["failed"]==0
    else:success=result["passed"]
    raise SystemExit(0 if success else 1)


if __name__=="__main__":
    main()
