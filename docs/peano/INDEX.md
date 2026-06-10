# Indice Documentazione VQT — Hub Centrale

**Linea di ricerca corrente (2026-06-09)**: **motore Einstein-Cartan integrato** — la
torsione è sorgentata dallo **spin** (voxel = campo + spinore, `β/α = pendenza del kink`,
twist 180/720), e da quell'unica torsione emergono gravità (clumping), espansione, e la
fisica del tempo (dilatazione e direzione). Branch `physics/einstein-cartan-saturation`.

---

## ⭐ Motore Einstein-Cartan (linea attuale)

| Documento | Contenuto |
|---|---|
| [VQT_FORMALIZZAZIONE.md](VQT_FORMALIZZAZIONE.md) | **Teoria formale**: ontologia (voxel + spinore), statica (Leech, scala di Planck, rigidezza → G), dinamica (torsione dallo spin, saturazione/bounce, espansione, gravità/clumping, tempo proprio attivo, **direzione del tempo**), costanti, formule, ipotesi aperte. Con **schema d'insieme** (`../figures/vqt_sistema.png`). |
| [EDIFICIO_EINSTEIN_CARTAN.md](EDIFICIO_EINSTEIN_CARTAN.md) | Diario implementativo dell'edificio EC (i passi, le verifiche, l'inventario costanti). |
| [MIGRAZIONE_CHECKPOINT.md](MIGRAZIONE_CHECKPOINT.md) | **Stato lavori** (blocco "PER DOMANI"): cosa è fatto, cosa resta, comandi di verifica rapida. |
| [../TESTS_E_STRUMENTI.md](../TESTS_E_STRUMENTI.md) §8 | Moduli (`einstein_cartan`, `muratore_planck`, `rigidezza_geometrica`, `scala_planck`, `motore_chirale_spinoriale`), GATE ed esperimenti. |
| [DIAGNOSI_SATURAZIONE_EC.md](DIAGNOSI_SATURAZIONE_EC.md) · [RELAZIONE_IMPLEMENTAZIONE_EC.md](RELAZIONE_IMPLEMENTAZIONE_EC.md) | Diagnosi e relazione della prima implementazione EC (storico del recupero). |

**Codice**: `wqt_oop/{einstein_cartan,muratore_planck,rigidezza_geometrica,scala_planck,motore_chirale_spinoriale}.py`
→ `solitone_composito.py` (`set_ec_integrato`, `evolve_with_muratore`).
**Esperimenti**: `experiments/exp3/test_{gravita_clumping,cosmogenesi,inversione_tempo,g_nonmonotono,g_dinamico,cura_coupling,legge_febbre}.py`.
**Figura**: `docs/figures/vqt_sistema.png` (rigenerabile: `tools/rendering/genera_diagramma_vqt.py`).

### Percorso di lettura (linea attuale)

1. **Il quadro** → [VQT_FORMALIZZAZIONE.md](VQT_FORMALIZZAZIONE.md) (parti dallo *Schema d'insieme*).
2. **Come è stato costruito** → [EDIFICIO_EINSTEIN_CARTAN.md](EDIFICIO_EINSTEIN_CARTAN.md).
3. **Stato e prossimi passi** → [MIGRAZIONE_CHECKPOINT.md](MIGRAZIONE_CHECKPOINT.md).
4. **Riprodurre** → [../TESTS_E_STRUMENTI.md](../TESTS_E_STRUMENTI.md) §8.

---

## 📐 Fondamenti matematici / topologici

| Documento | Contenuto |
|---|---|
| [../../basimatematiche/TOPOLOGIA_FONDAMENTALE.md](../../basimatematiche/TOPOLOGIA_FONDAMENTALE.md) | La topologia 180°/720° (voxel up/down, chiralità alternata, chiusura spinoriale): "il motore di tutto". |
| [FORMALIZZAZIONE_MASSA_TOPOLOGICA.md](FORMALIZZAZIONE_MASSA_TOPOLOGICA.md) | Massa = difetto topologico congelato; soglia geometrica √2 (Jitterbug). |
| [../../basimatematiche/teorema_peano_vqt.md](../../basimatematiche/teorema_peano_vqt.md) | Il teorema Peano-VQT. |

---

## 🧬🌌 Fase precedente — "doppia elica" (substrato)

Modello v3.0 (Ramo A Cosmology/RG-flow + Ramo B Peano-VQT) da cui è cresciuto il motore
EC. **Ancora valido come substrato** (doppio pozzo, kink, Leech, costante √2), ma non la
linea corrente.

| Documento | Ramo | Contenuto |
|---|---|---|
| [VQT_MANIFESTO_TEORICO.md](VQT_MANIFESTO_TEORICO.md) | B | Le 3 leggi Peano-VQT (aggregazione, repulsione, triade energetica) |
| [../cosmology/TOPOLOGICAL_DYNAMICS.md](../cosmology/TOPOLOGICAL_DYNAMICS.md) | A | Formalizzazione variazionale (potenziale topologico, spettroscopia f_dom) |
| [../cosmology/EVOLUZIONE_TEORICA.md](../cosmology/EVOLUZIONE_TEORICA.md) | A→B | Come il Ramo A ha generato il Ramo B |
| [../reference/PHYSICS_MANIFESTO.md](../reference/PHYSICS_MANIFESTO.md) | — | Manifesto fisico (substrato) |

## 📜 Archivio

- [../history/](../history/) — modelli pre-OOP superati (tracciabilità).
- [../obsoletes/](../obsoletes/) — patch e proposte archiviate.
- [../reports/](../reports/) — artefatti di processo (proposte, fix, audit).
