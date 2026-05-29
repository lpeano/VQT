#!/usr/bin/env python3
"""
merge_l3_runs.py — Concatena le serie temporali topological_validation
di più run L3 sequenziali in un singolo file HDF5 usabile dall'analisi spettrale.

Uso:
  python experiments/merge_l3_runs.py \
    experiments/exp1/cosmo_L3.h5 \
    experiments/exp1/cosmo_L3_ext.h5 \
    experiments/exp1/cosmo_L3_ext2.h5 \
    --output experiments/exp1/cosmo_L3_merged.h5
"""

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np


_TOPO_SCALAR_KEYS = [
    'step', 'time',
    'mean_constraint_density', 'constraint_density_std',
    'closure_error_deg', 'closure_satisfied',
    'detorsion_quality', 'detorsion_satisfied',
    'H_total_emergent', 'H_torsion_emergent',
    'topology_charge', 'N_segments', 'N_dof',
    'transition_detected', 'phase_label',
]


def load_topo(hdf5_path: Path) -> dict:
    """Carica topological_validation da un file HDF5."""
    with h5py.File(hdf5_path, 'r') as f:
        if 'topological_validation' not in f:
            raise ValueError(f"{hdf5_path.name}: nessun gruppo topological_validation")
        tv = f['topological_validation']
        data = {}
        for k in _TOPO_SCALAR_KEYS:
            if k in tv:
                data[k] = tv[k][:]
        # Metadata
        data['_source'] = hdf5_path.name
        data['_n'] = len(data['step'])
        return data


def merge_and_write(sources: list, output_path: Path):
    """Concatena le serie temporali (ordinate per step) e scrive un nuovo HDF5."""
    all_data = []
    last_abs_step = 0
    last_abs_time = 0.0

    for src in sources:
        d = load_topo(src)

        # Auto-offset: se i passi del file iniziano prima dell'ultimo passo assoluto,
        # significa che il run usa numerazione relativa (reset a 1 al resume).
        step_offset = 0
        time_offset = 0.0
        if int(d['step'][0]) <= last_abs_step:
            step_offset = last_abs_step
            time_offset = last_abs_time

        if step_offset:
            d = dict(d)
            d['step'] = d['step'] + step_offset
            d['time'] = d['time'] + time_offset

        last_abs_step = int(d['step'][-1])
        last_abs_time = float(d['time'][-1])

        offset_str = f"  [+step {step_offset}, +t {time_offset:.3f}]" if step_offset else ""
        print(f"  {src.name}: {d['_n']} entry  step=[{d['step'][0]}..{d['step'][-1]}]  "
              f"t=[{d['time'][0]:.3f}..{d['time'][-1]:.3f}]{offset_str}")
        all_data.append(d)

    # Deduplicazione per step assoluto e ordinamento
    combined = {}
    seen_steps = set()
    for d in all_data:
        for i, s in enumerate(d['step']):
            if s not in seen_steps:
                seen_steps.add(s)
                for k in _TOPO_SCALAR_KEYS:
                    if k in d:
                        combined.setdefault(k, []).append(d[k][i])

    # Ordina per step
    order = np.argsort(combined['step'])
    sorted_combined = {k: np.array(v)[order] for k, v in combined.items()}

    n_total = len(sorted_combined['step'])
    print(f"\n  Totale entry merge: {n_total}  step=[{sorted_combined['step'][0]}..{sorted_combined['step'][-1]}]")
    print(f"  Intervallo temporale: [{sorted_combined['time'][0]:.3f}..{sorted_combined['time'][-1]:.3f}] Planck")

    # Crea un nuovo HDF5 con struttura compatibile con compare_fdom_scaling.py
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Copia metadata dall'ultimo file sorgente (ha le info più aggiornate)
    with h5py.File(sources[0], 'r') as src_f:
        level = int(src_f['metadata'].attrs.get('target_level', 3))
        N_segments = int(src_f['metadata'].attrs.get('N_segments', 13824))
        dt = float(src_f['metadata'].attrs.get('dt', 0.01))
        seed = int(src_f['metadata'].attrs.get('seed', 42))
        chi_mean = float(src_f['metadata'].attrs.get('chi_mean', 50.0))
        chi_std = float(src_f['metadata'].attrs.get('chi_std', 5.0))
        spatial_extent = float(src_f['metadata'].attrs.get('spatial_extent', 50.0))

    with h5py.File(output_path, 'w') as f:
        # Metadata compatibile con compare_fdom_scaling.py
        meta = f.create_group('metadata')
        meta.attrs['target_level'] = level
        meta.attrs['N_segments'] = N_segments
        meta.attrs['dt'] = dt
        meta.attrs['seed'] = seed
        meta.attrs['chi_mean'] = chi_mean
        meta.attrs['chi_std'] = chi_std
        meta.attrs['spatial_extent'] = spatial_extent
        meta.attrs['paradigm'] = 'topological_v1'
        meta.attrs['merged_from'] = [str(s) for s in sources]
        meta.attrs['total_steps'] = n_total

        # topological_validation (obbligatorio per compare_fdom_scaling.py)
        tv = f.create_group('topological_validation')
        for k, arr in sorted_combined.items():
            if k == 'phase_label':
                tv.create_dataset(k, data=arr.astype('S16'), compression='gzip')
            elif arr.dtype == object:
                tv.create_dataset(k, data=arr.astype('S16'), compression='gzip')
            else:
                tv.create_dataset(k, data=arr, compression='gzip')
        tv.attrs['merged'] = True
        tv.attrs['n_sources'] = len(sources)

        # frames vuoto (il compare script non richiede frames)
        f.create_group('frames')

    print(f"\n  Output: {output_path}")
    print("  Pronto per compare_fdom_scaling.py")


def main():
    p = argparse.ArgumentParser(description="Merge L3 sequential HDF5 runs")
    p.add_argument('sources', nargs='+', type=Path, help="File HDF5 sorgente (in ordine cronologico)")
    p.add_argument('--output', '-o', type=Path, required=True, help="File HDF5 di output merged")
    args = p.parse_args()

    print("Merge L3 topological time series")
    print("=" * 50)
    print(f"Sorgenti ({len(args.sources)}):")

    try:
        merge_and_write(args.sources, args.output)
    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
