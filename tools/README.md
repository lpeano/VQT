# tools/ — Script di supporto (standalone)

Script eseguibili autonomi: **nessuno è importato da altri moduli**.
Quelli che usano il motore (`wqt_oop`/`core`) hanno un **auto-shim** che aggiunge
la repo-root a `sys.path`, quindi funzionano da qualsiasi directory:

```bash
python tools/<categoria>/<script>.py
```

| Cartella | Contenuto |
|---|---|
| `tests/` (5) | Test del motore: baseline simplettico, convergenza, Verlet puro, timestep relativistico, field geometry |
| `validation/` (8) | Diagnostica run: audit L3, check parametri/frames, inspect equilibrio, validate baseline/L3, verify dataset |
| `rendering/` (12) | Generatori video/dataset e visualizzatori: `generate_*`, `master_*video`, `manifold_*`, `torsion_video` |
| `analysis/` (3) | Analisi: `analyze_topo_dataset`, `compare_l2_runs`, `compare_scales` |

> ⚠️ Alcuni script di `rendering/` e `validation/` cercano file `.h5` di run
> specifiche (es. `cosmology_L3.h5`): vanno eseguiti dopo aver generato o
> posizionato i relativi dataset. L'import del motore è comunque garantito
> dall'auto-shim.
