"""Optional version-scoped, process-isolated shared-ngspice timing study.

NumPy and PySpice are optional dependencies. Library paths are accepted at run time;
published records identify library bytes and labels without retaining private paths.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
import time

from .checks import compare, sha256
from .studies import diode_bank
from .workbench import write_csv


def worker(library, sizes, repeats, samples):
    os.environ.update(NGSPICE_LIBRARY_PATH=library, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    try:
        os.nice(10)
    except (AttributeError, OSError):
        pass
    from PySpice.Spice.NgSpice.Shared import NgSpiceShared
    NgSpiceShared.LIBRARY_PATH=library
    ng=NgSpiceShared(send_data=False)
    version=ng.exec_command('version -f')
    match=re.search(r'ngspice-\d+',version)
    klu='Compiled with KLU' in version
    rows=[]
    for size in sizes:
        circuit=diode_bank(size)
        circuit=circuit.replace('.end', '.save all\n.op\n'+('.options klu\n' if klu else '')+'.end')
        ng.load_circuit(circuit);ng.exec_command('set numdgt=15')
        for _ in range(2):
            ng.run();ng.exec_command('destroy all')
        for repetition in range(repeats):
            for sample in range(samples):
                vin=.4+.4*sample/(samples-1)
                ng.exec_command(f'alter VIN dc={vin:.16g}')
                start=time.perf_counter();ng.run();elapsed=time.perf_counter()-start
                text=ng.exec_command('print allv')
                readings={m.group(1):float(m.group(2)) for m in re.finditer(r'^\s*(\S+)\s*=\s*([-+0-9.eE]+)\s*$',text,re.M)}
                if len(readings)<size+1:raise RuntimeError('Incomplete node readout')
                rows.append({'branches':size,'repetition':repetition,'sample':sample,'vin_v':vin,
                             'op_seconds':elapsed,'node_voltages':readings})
                ng.exec_command('destroy all')
        ng.exec_command('remcirc')
    return {'version':match.group() if match else 'unknown','klu_enabled':klu,'rows':rows,
            'library_sha256':sha256(library),'python':platform.python_version()}


def benchmark(libraries, out, *, sizes=(128,512,2048), repeats=3, samples=9):
    out=Path(out)
    if out.exists() and any(out.iterdir()):raise ValueError('Benchmark directory must be fresh')
    if len(libraries)<2 or samples<2 or repeats<2:raise ValueError('Need two libraries, two repetitions, and two samples')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',label) for label in libraries):raise ValueError('Invalid library label')
    out.mkdir(parents=True,exist_ok=True)
    results={};timings=[];orders=[]
    for repetition in range(repeats):
        order=list(libraries) if repetition%2==0 else list(reversed(libraries))
        orders.append(order)
        for label in order:
            path=libraries[label]
            command=[sys.executable,'-m','simcheck.shared_benchmark','worker',str(Path(path).resolve()),
                     '--sizes',','.join(map(str,sizes)),'--repeats','1','--samples',str(samples)]
            proc=subprocess.run(command,capture_output=True,text=True,timeout=300)
            if proc.returncode:raise RuntimeError(f'Benchmark worker {label} failed: {proc.stderr[-2000:]}')
            data=json.loads(proc.stdout)
            for row in data['rows']:row['repetition']=repetition
            if label not in results:results[label]=data
            else:results[label]['rows'].extend(data['rows'])
    for label,data in results.items():
        (out/(label+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        for row in data['rows']:
            timings.append({'label':label,**{k:v for k,v in row.items() if k!='node_voltages'}})
    reference=next(iter(results));comparisons=[]
    for label,data in results.items():
        for size in sizes:
            a=[r for r in results[reference]['rows'] if r['branches']==size]
            b=[r for r in data['rows'] if r['branches']==size]
            maximum=0.0;passed=True
            for expected,actual in zip(a,b):
                keys=sorted(expected['node_voltages'])
                if keys!=sorted(actual['node_voltages']):raise RuntimeError('Reference/candidate node sets differ')
                c=compare([expected['node_voltages'][k] for k in keys],[actual['node_voltages'][k] for k in keys],atol=1e-7,rtol=1e-6)
                maximum=max(maximum,max(r['absolute_error'] for r in c['rows']));passed &= c['passed']
            median=statistics.median(r['op_seconds'] for r in b)
            refmedian=statistics.median(r['op_seconds'] for r in a)
            comparisons.append({'label':label,'branches':size,'median_op_seconds':median,
                                'p25_op_seconds':statistics.quantiles([r['op_seconds'] for r in b],n=4)[0],
                                'p75_op_seconds':statistics.quantiles([r['op_seconds'] for r in b],n=4)[2],
                                'reference_to_candidate_ratio':refmedian/median,
                                'max_all_node_voltage_error_v':maximum,'parity_passed':passed})
    write_csv(out/'timings.csv',timings);write_csv(out/'comparisons.csv',comparisons)
    summary={'reference_label':reference,'libraries':{k:{x:v for x,v in d.items() if x!='rows'} for k,d in results.items()},
             'timing_scope':'Synchronous ngspice run command, including wrapper and simulator setup/teardown; excludes alter/read/cleanup',
             'load_order_by_repetition':orders,'repetitions':repeats,'samples_per_repetition':samples,
             'warmup_solves':2,'sizes':list(sizes),'comparisons':comparisons,
             'passed':all(r['parity_passed'] for r in comparisons),
             'limitations':'One host under shared load; library order alternates across repetitions. These workloads stress internal-node housekeeping, not all simulation costs.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    w=sub.add_parser('worker');w.add_argument('library');w.add_argument('--sizes',required=True)
    w.add_argument('--repeats',type=int,default=3);w.add_argument('--samples',type=int,default=9)
    b=sub.add_parser('run');b.add_argument('libraries',type=Path);b.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='worker':
        result=worker(args.library,[int(x) for x in args.sizes.split(',')],args.repeats,args.samples)
    else:result=benchmark(json.loads(args.libraries.read_text()),args.out)
    print(json.dumps(result,allow_nan=False))
