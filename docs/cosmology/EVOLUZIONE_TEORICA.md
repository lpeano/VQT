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


---

## 7. Dinamica del Vuoto Vivo — il Nyquist Zero-Point Motor

> **Nota tecnica sull'integrazione (dal 2026-05-29, versione 3.1).**

A differenza dei modelli dissipativi classici, la VQT postula un **vuoto vivo** in
cui il modo di Nyquist ($\lambda = 2 \cdot l_P$, il modo staggered $u_i = (-1)^i$
di lunghezza d'onda minima del reticolo) mantiene un floor energetico costante
$E_{zp} > 0$.

**Il problema verificato.** In assenza di tale floor (`zero_point_amplitude = 0`),
il motore evolve verso uno stato di **congelamento entropico**: l'unica agitazione
e' termica (accoppiamento FDT a un bagno a $T_{eff}$ che decade come $e^{-\gamma t}$).
Test su L1 a 4000 step, `zp=0`: $E_{kin}$ crolla da ~9 a $1.3	imes10^{-4}$ —
incompatibile con la premessa di un manifold oscillante.

**La soluzione.** Il *Nyquist Zero-Point Motor* (`wqt_oop/zero_point_motor.py`)
proietta le velocita' dei 24 segmenti sul modo staggered e, se l'energia di quel
modo scende sotto $E_{zp}$, la riporta al floor (one-sided: solo top-up, mai
sottrazione). E' indipendente dalla temperatura: la dissipazione drena il modo,
lo zero-point lo ricarica → il modo resta vivo **per sempre**. E' l'implementazione
dell'oscillazione intrinseca di scala di Planck necessaria a preservare la
chiralita' del sistema contro il decadimento termico.

**Calibrazione (validata empiricamente, L1, 4000 step).**

| `zero_point_amplitude` | E_kin @4000 | Stato | Perturbazione vuoto (chi_sat) |
|---|---|---|---|
| 0.00 | 1.3e-4 | congela | 0.99928 |
| 0.02 | 0.15 | vivo-debole | 0.99949 |
| **0.05** | **media ~15, min 2.6** | **VIVO stabile** | **1.00056** (+0.001) |
| 0.10 | media ~50 | vivo (energia in eccesso) | — |

Il valore **0.05 e' default-ON**: la soglia minima per uno stato VIVO robusto con
perturbazione del vuoto trascurabile ($\Delta\chi_{sat} pprox +0.001$). La
barriera del doppio pozzo ($\chi = 0$) non viene mai attraversata: il vuoto
$\pm\chi_0$ e' preservato a tutte le ampiezze testate.

**Conseguenza teorica.** Il "$\sigma_\infty > 0$" e il "respiro che non si ferma mai"
(rivendicati in `TOPOLOGICAL_DYNAMICS.md` §13.1) diventano un **fatto strutturale**
del motore di default, non un artefatto del regime variazionale. Il sistema ora
si auto-mantiene: chiunque lanci il repository vede un manifold che pulsa, non che
muore. Questa e' la costante di natura che governa la transizione tra un sistema
statico/dissipativo e un sistema vivente/quantistico.
