"""Regenerate the public case-study figures from recorded CSV/JSON evidence."""
import argparse
import csv
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def records(path):
    with Path(path).open() as stream:return list(csv.DictReader(stream))


def render(root):
    root=Path(root);out=root/'docs/figures';out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.labelcolor':'#253b35','text.color':'#253b35',
                         'axes.edgecolor':'#718178','figure.facecolor':'#faf8f4','axes.facecolor':'#faf8f4',
                         'savefig.facecolor':'#faf8f4','svg.fonttype':'none'})
    green,gold,red='#176b62','#ab8137','#b35b3b'
    def save(fig,name):
        fig.text(.015,.012,'Contrastive Local Learning Networks',fontsize=7,color='#53625c')
        fig.tight_layout(pad=1.4,rect=(0,.04,1,1))
        for ext in ['svg','png']:fig.savefig(out/(name+'.'+ext),dpi=180,bbox_inches='tight')
        plt.close(fig)
    shared=json.loads((root/'results/shared-benchmark/summary.json').read_text())
    fig,ax=plt.subplots(figsize=(7.6,4.5))
    for label,color in [('ngspice41-stock',gold),('ngspice47-stock',red),('ngspice47-localpatch',green)]:
        rows=sorted([r for r in shared['comparisons'] if r['label']==label],key=lambda r:r['branches'])
        ax.plot([r['branches'] for r in rows],[r['median_op_seconds']*1000 for r in rows],'o-',color=color,label=label)
        ax.fill_between([r['branches'] for r in rows],[r['p25_op_seconds']*1000 for r in rows],
                        [r['p75_op_seconds']*1000 for r in rows],color=color,alpha=.13)
    ax.set(xscale='log',yscale='log',xlabel='Generic diode branches',ylabel='Repeated operating-point command (ms)',
           title='A version-scoped performance result')
    ax.grid(alpha=.18);ax.legend(frameon=False,fontsize=8);save(fig,'shared-performance')

    rows=records(root/'results/public/performance/timings.csv');fig,ax=plt.subplots(figsize=(7.6,4.3))
    sizes=sorted({int(r['branches']) for r in rows});values=[[float(r['ratio']) for r in rows if int(r['branches'])==n] for n in sizes]
    ax.boxplot(values,tick_labels=[str(n) for n in sizes],patch_artist=True,boxprops={'facecolor':'#d1e1d7'})
    ax.set(xlabel='Generic diode branches',ylabel='Separate-process time / one-sweep time',
           title='Amortizing process startup over nine inputs');ax.grid(axis='y',alpha=.18);save(fig,'batch-performance')

    rows=records(root/'results/public/approximation/device-points.csv')
    selected=[r for r in rows if float(r['source_v'])==.2 and float(r['gmin_s'])==1e-8]
    fig,axes=plt.subplots(1,2,figsize=(9.5,4.1))
    x=[float(r['gate_v']) for r in selected]
    axes[0].semilogy(x,[abs(float(r['drain_in_a'])) for r in selected],color=green,label='Dense ngspice drain current')
    axes[0].semilogy(x,[max(abs(float(r['coarse_drain_a'])),1e-16) for r in selected],color=red,ls='--',label='Coarse interpolation')
    axes[0].set(xlabel='Gate voltage (V)',ylabel='Drain current magnitude (A)',title='A coarse grid distorts the turn-on')
    axes[0].legend(frameon=False,fontsize=8)
    axes[1].plot(x,[float(r['terminal_difference_a'])*1e9 for r in selected],color=gold)
    axes[1].set(xlabel='Gate voltage (V)',ylabel='Drain-in minus source-out (nA)',title='The bulk terminal closes KCL')
    for ax in axes:ax.grid(alpha=.18)
    save(fig,'approximation-failures')

    rows=records(root/'results/public/verification/xor-verification.csv');fig,axes=plt.subplots(1,2,figsize=(9.5,4.1))
    for load,color,offset in [(0,green,-.17),(10000,red,.17)]:
        subset=[r for r in rows if int(r['load_ohm'])==load]
        axes[0].bar(np.arange(4)+offset,[float(r['output_v']) for r in subset],width=.34,color=color,
                    label='Unloaded' if load==0 else '10 kΩ load')
    axes[0].axhline(1.26,color=gold,ls=':',label='Declared high threshold')
    axes[0].set(xticks=range(4),xticklabels=['00','01','10','11'],xlabel='XOR input A B',ylabel='Output voltage (V)',
                title='An unloaded truth table misses a loaded failure')
    axes[0].legend(frameon=False,fontsize=7.8)
    for name,color in [('positive',green),('negative',red)]:
        values=records(root/f'results/public/verification/latch-transient-{name}.csv')
        axes[1].plot([float(r['time'])*1e9 for r in values],[float(r['v(q)']) for r in values],color=color,
                     label='q(0) = 0.9 V '+('+' if name=='positive' else '−')+' 10 µV')
    axes[1].set(xlabel='Time (ns)',ylabel='Latch node q (V)',title='Small perturbations select opposite latch states')
    axes[1].legend(frameon=False,fontsize=7.8)
    for ax in axes:ax.grid(axis='y',alpha=.18)
    save(fig,'circuit-verification')

    rows=records(root/'results/public/robustness/corners.csv');fig,ax=plt.subplots(figsize=(6.2,4.3))
    supplies=[1.6,1.8,2.0];temperatures=[-20,27,85]
    grid=np.array([[statistics.mean(float(r['trip_fraction']) for r in rows if float(r['supply_v'])==v and int(r['temperature_c'])==t)
                    for v in supplies] for t in temperatures])
    im=ax.imshow(grid,cmap='YlGn',vmin=.48,vmax=.54,aspect='auto')
    for i in range(3):
        for j in range(3):ax.text(j,i,f'{grid[i,j]:.4f}',ha='center',va='center',color='#253b35')
    ax.set(xticks=range(3),xticklabels=supplies,yticks=range(3),yticklabels=temperatures,
           xlabel='Supply voltage (V)',ylabel='Operating temperature (°C)',title='Illustrative inverter corner sensitivity')
    fig.colorbar(im,ax=ax,label='Mean switching voltage / supply (5 paired draws)');save(fig,'robustness-corners')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    render(parser.parse_args().root)
