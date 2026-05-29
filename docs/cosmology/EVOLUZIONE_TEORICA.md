# Evoluzione Teorica — Dal Ramo A (Cosmology) al Ramo B (Peano-VQT)

Questo documento spiega **come e perché** la linea di ricerca Peano-VQT (Ramo B)
è emersa dall'analisi cosmologica/RG-flow (Ramo A). Non introduce nuova fisica:
collega due corpi di documentazione già esistenti e verificati, mostrando la
continuità del motore sottostante.

> **Sintesi in una frase**: il Ramo A ha dimostrato che il manifold frattale
> possiede un **vuoto topologico coerente** (f_dom invariante di scala, σ in
> plateau, cristallizzazione spettrale); il Ramo B ha preso quello stesso motore
> e gli ha aggiunto un **strato di contabilità energetica** (la triade
> E_χ / E_RX / E_Ψ) per misurare come la materia si auto-organizza.

---

## 1. Il motore condiviso (la spina dorsale comune)

Entrambi i rami girano sullo **stesso core**, invariato:

| Modulo | Ruolo |
|---|---|
| `wqt_oop/segmento_quantistico.py` | Unità L0: 2 DOF (χ, v), doppio pozzo `V=β(χ²−χ₀²)²` |
| `wqt_oop/solitone_composito.py` | Composizione frattale 24 unità/livello, coupling Yukawa |
| `wqt_oop/physics_context.py` | Costanti scale-dependent, RG-flow `α_K ~ 1/24^L`, `κ ~ 1/24^(L/2)` |
| `wqt_oop/fermi_dirac_screening.py` | Screening continuo (usato da entrambi quando `screening_enabled=True`) |

Tutto ciò che distingue i due rami è **costruito sopra** questa base, senza modificarla.

---

## 2. Ramo A — cosa ha stabilito

Il Ramo A (documentato in [TOPOLOGICAL_DYNAMICS.md](TOPOLOGICAL_DYNAMICS.md)) ha
studiato il manifold come **sistema variazionale autonomo**, con osservabile
primaria σ(ρ) — la deviazione standard della densità di vincolo topologico.

Risultati fondanti (su run L1–L3, file `data/cosmo_L*.h5`):

1. **Invarianza di scala della frequenza**: `f_dom ≈ 0.75·N_dof^(−0.033)` — quasi
   costante su tre decadi di gradi di libertà. Il manifold ha una "frequenza di
   vuoto" indipendente dalla risoluzione [Eq. FSCALE-1].
2. **Cristallizzazione spettrale**: l'entropia spettrale cala con il livello
   (2.539 → 1.986 → 1.237). Più gradi di libertà → *meno* modi dominanti, il
   contrario di un sistema caotico classico.
3. **Vuoto topologico coerente**: σ in plateau (`σ_∞ > 0`), il manifold "respira"
   attorno a un vuoto vivo, non collassa su uno stato morto.
4. **Numero 24 come ramificazione frattale**: ogni livello L contiene `24^L` voxel,
   la struttura del reticolo di Leech proiettato in 3D.

Il Ramo A risponde alla domanda: **"qual è la firma dinamica del vuoto?"**

---

## 3. Il punto di svolta — la domanda che il Ramo A non poteva porre

Il Ramo A misura σ(ρ) e lo spettro, ma **non traccia dove va l'energia** quando
il manifold cristallizza. L'Hamiltoniana `H_phys` oscilla (è un osservabile, non
un target), e l'energia "cambia forma" tra cinetica e topologica — ma non c'era
un conto esplicito del flusso irreversibile.

La domanda emergente era diversa:

> *Quando due strutture stabili si avvicinano, si legano o si respingono?
> E quanta energia viene rilasciata (o intrappolata) nel processo?*

Questa è una domanda di **auto-organizzazione della materia**, non di spettroscopia
del vuoto. Richiedeva uno strumento nuovo.

---

## 4. Ramo B — cosa è stato aggiunto

Il Ramo B (documentato in [VQT_MANIFESTO_TEORICO.md](../peano/VQT_MANIFESTO_TEORICO.md))
ha introdotto un **unico modulo nuovo** e tre script sperimentali:

| Aggiunta | File | Funzione |
|---|---|---|
| Triade energetica | `wqt_oop/energy_metrics.py` | `PeanoVQTAnalyzer`: decompone H_coupling in E_χ (allineamento), E_RX (reattiva), E_Ψ (sink radiativo) |
| Genesi | `experiments/genesis_run.py` | Transizione vuoto→materia (Ottaedrica→Icosaedrica) |
| Aggregazione | `experiments/l2_aggregation_run.py` | Due solitoni: legame vs frustrazione topologica |
| Auto-assembly | `experiments/l4_self_assembly_run.py` | 48 solitoni → cristallizzazione spontanea |

L'**invariante chiave** del Ramo B (`dE_χ + dE_RX + dE_Ψ = 0`) è il complemento
naturale dell'osservazione del Ramo A che "l'energia cambia forma": qui quel flusso
viene **contabilizzato esattamente**, e la parte irreversibile (E_Ψ) diventa un
indicatore misurabile.

Il Ramo B risponde alla domanda: **"come si lega la materia, e con quale energia?"**

---

## 5. Il ponte — il numero 24 appare in entrambi

La connessione più profonda tra i due rami è il **numero di Leech (24)**:

- **Ramo A**: 24 è imposto come *ramificazione frattale* della costruzione (`24^L` voxel).
- **Ramo B**: 24 *emerge spontaneamente* come dimensione del cluster auto-organizzato
  nel run L4 Self-Assembly (48 solitoni casuali → cluster stabile di 24, step 600).

In altre parole: il Ramo A **postula** la geometria di Leech; il Ramo B **la ritrova**
come stato di minima energia di un sistema non vincolato. Questa è la validazione
incrociata che dà solidità all'intera teoria.

```
Ramo A:  24^L  (costruzione)  ──────┐
                                     ├──►  stesso motore, stesso χ₀=50,
Ramo B:  24    (emergenza)  ─────────┘     stesso doppio pozzo, stesso screening
```

---

## 6. Mappa di lettura

```
EVOLUZIONE_TEORICA.md  (sei qui — il ponte)
        │
        ├──►  Ramo A:  TOPOLOGICAL_DYNAMICS.md      (firma del vuoto)
        │             ARCHITETTURA_SCALING_MASSIVO.md (toolchain)
        │             FIELD_GEOMETRY_RENDERING.md     (visualizzazione)
        │
        └──►  Ramo B:  ../peano/VQT_MANIFESTO_TEORICO.md  (3 leggi)
                       ../peano/MIGRAZIONE_CHECKPOINT.md   (cronologia run)
```

*Creato il 2026-05-29 durante la separazione a doppia elica dell'archivio.*
