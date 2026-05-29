# Indice Documentazione VQT — Hub Centrale

La documentazione segue la struttura a **doppia elica** della ricerca:
il **Ramo A (Cosmology/RG-flow)** è l'impalcatura scientifica da cui è emerso
il **Ramo B (Peano-VQT)**. Entrambi condividono lo stesso motore (`wqt_oop/`).

**Ultima riorganizzazione**: 2026-05-29

---

## 🧬 Ramo B — Peano-VQT (il cuore attuale)

Auto-organizzazione, triade energetica, leggi di aggregazione. È la linea di ricerca corrente.

| Documento | Contenuto |
|---|---|
| [VQT_MANIFESTO_TEORICO.md](VQT_MANIFESTO_TEORICO.md) | Le 3 leggi Peano-VQT (Aggregazione, Repulsione topologica, Dissipazione radiativa), ancorate ai log delle run e verificate formula-per-formula |
| [MIGRAZIONE_CHECKPOINT.md](MIGRAZIONE_CHECKPOINT.md) | Checkpoint persistente: cronologia run (Genesis, L2, L4 Leech, Self-Assembly), riorganizzazione archivio |

**Codice**: `experiments/genesis_run.py`, `l2_aggregation_run.py`, `l4_self_assembly_run.py` → `wqt_oop/energy_metrics.py` (`PeanoVQTAnalyzer`)
**Dati**: `data/peano_data.zip` · **Grafici**: `assets/plot_genesi.png`

---

## 🌌 Ramo A — Cosmology / RG-flow (la base scientifica)

Analisi spettrale, invarianza di scala della frequenza, Einstein-Cartan discreto.
È la linea da cui è emerso il Ramo B.

| Documento | Contenuto |
|---|---|
| [TOPOLOGICAL_DYNAMICS.md](../cosmology/TOPOLOGICAL_DYNAMICS.md) | Formalizzazione variazionale completa: potenziale topologico S, spettroscopia (f_dom, σ plateau), predizioni falsificabili P-1…P-5, mappatura Einstein-Cartan |
| [ARCHITETTURA_SCALING_MASSIVO.md](../cosmology/ARCHITETTURA_SCALING_MASSIVO.md) | Toolchain del Ramo A: Fermi-Dirac screening, Spatial Hash, Spatial Cache, Fractal Factory, run_cosmology |
| [FIELD_GEOMETRY_RENDERING.md](../cosmology/FIELD_GEOMETRY_RENDERING.md) | Rendering geometria delle forze (`ManifoldVisualizer`) usato dai `generate_*.py` |
| [EVOLUZIONE_TEORICA.md](../cosmology/EVOLUZIONE_TEORICA.md) | **Come il Ramo A ha generato il Ramo B**: la transizione concettuale e di codice |

**Codice**: `wqt_oop/run_cosmology.py` → `fractal_universe_factory.py` · rendering: `generate_*.py`
**Dati**: `data/cosmo_L*.h5`, `experiments/exp1/cosmo_L*.h5`

---

## 📜 history/ — Pre-OOP (superato)

Modelli e codice antecedenti al motore `wqt_oop/`. Conservati per tracciabilità.
Dettaglio in [history/README.md](../history/README.md):
χ-potenziale-di-scala, diffusione laplaciana, metrica esponenziale χ→±∞,
`c_locale`, risultati `WQT_manifold.py` v2.0.

## 🗑️ obsoletes/ — Patch e proposte già archiviate

Vedi [../obsoletes/](../obsoletes/).

---

## Percorso di lettura

1. **Capire da dove viene tutto** → [EVOLUZIONE_TEORICA.md](../cosmology/EVOLUZIONE_TEORICA.md)
2. **La fisica fondante (Ramo A)** → [TOPOLOGICAL_DYNAMICS.md](../cosmology/TOPOLOGICAL_DYNAMICS.md)
3. **Le leggi emergenti (Ramo B)** → [VQT_MANIFESTO_TEORICO.md](VQT_MANIFESTO_TEORICO.md)
4. **Stato lavori** → [MIGRAZIONE_CHECKPOINT.md](MIGRAZIONE_CHECKPOINT.md)

> Citazione tipo per pubblicazione: *"Il sistema di auto-organizzazione Peano-VQT
> (Ramo B) è emerso dall'analisi di screening e scaling spettrale del manifold
> frattale (Ramo A); l'invarianza di scala di f_dom valida l'esistenza di un
> vuoto topologico coerente alla base della cristallizzazione a numero di Leech."*
