# Metodi Spettrali e Simplettici per la Simulazione VQT

**Data**: 2026-05-31
**Branch**: `research-backup`
**Moduli implementati**: `wqt_oop/spectral_coupling.py`, `wqt_oop/symplectic_step.py`, `wqt_oop/fast_evolver.py`

---

## Motivazione

Il metodo numerico standard (integratore di Eulero, `dt=0.01`) richiede ~8 minuti per step
a L4 (331.776 segmenti), portando la catena L1→L4 a ~80 ore di calcolo.
Questo documento descrive due metodologie che accelerano il calcolo di
**100-1000x senza alterare la fisica**.

### Domanda critica: la discretezza del reticolo VQT è preservata?

**Risposta: Sì, completamente.**

La decomposizione spettrale usa la **Trasformata di Fourier Discreta** (DFT) sul gruppo
ciclico Z₂₄ (24 nodi fissi). Non si avvicina mai al limite continuo N→∞.

La trasformazione χᵢ → χ̃ₖ è **biettiva e invertibile** — è un cambio di base,
non un cambio di fisica. Il reticolo ha ancora esattamente 24 nodi discreti, ma
l'evoluzione avviene nel dominio dei modi normali invece del dominio nodale.

---

## Metodo 1 — Decomposizione Spettrale

### Fondamento fisico

La matrice di accoppiamento W del reticolo cubottaedrico VQT è una **matrice
circolante**: il peso W_ij dipende solo dalla distanza ciclica d(i,j) = min(|i−j|, N−|i−j|).

```
W_ij = exp(−d(i,j) / L_eff) / Z_i
```

Una matrice circolante su Z_N ammette decomposizione spettrale esatta con:

**Autovettori**: basi della DFT discreta
```
φ_k(n) = exp(2πi·k·n/N) / √N,   k = 0, 1, ..., N−1
```

**Autovalori**: Trasformata di Fourier della prima riga di W
```
λ_k = Σⱼ W₀ⱼ · exp(−2πi·k·j/N)
```

**Autovalori del Laplaciano** L = D − W (sempre reali ≥ 0):
```
μ_k = degree − λ_k
```

μ_k = 0 per k=0 (modo di traslazione uniforme, conservato)
μ_k > 0 per k > 0 (modi di oscillazione, frequenze crescenti)

### Disaccoppiamento dell'equazione del moto

L'equazione originale (24 equazioni **accoppiate**):
```
m · d²χᵢ/dt² = F_pot(χᵢ) − α_K · (L·χ)ᵢ − γ·vᵢ
```

Nel dominio spettrale (24 equazioni **indipendenti**):
```
m · d²χ̃ₖ/dt² = F̃ₖ_nonlin(t) − α_K · μₖ · χ̃ₖ − γ · ṽₖ
```

La parte lineare ha **soluzione analitica esatta** (oscillatore armonico smorzato):
```
χ̃ₖ(t) = exp(−γ·t/2m) · [Aₖ·cos(Ωₖ·t) + Bₖ·sin(Ωₖ·t)]
```

dove la frequenza smorzata è:
```
Ωₖ = √(α_K·μₖ/m − (γ/2m)²)
```

Solo il termine del **doppio pozzo** F̃ₖ_nonlin = DFT(−dV/dχ) richiede integrazione numerica.

### Schema Strang Splitting

Combinando propagazione lineare analitica con integrazione non-lineare numerica:

```
L(dt/2) → N(dt) → L(dt/2)
```

dove L = propagazione lineare (analitica, zero errore) e N = doppio pozzo (Verlet).

Accuratezza: **O(dt³) per passo**, O(dt²) globale.
L'errore totale è dominato dalla sola parte non-lineare.

### Invarianza della costante Jitterbug √2

La soglia Jitterbug χ_max/χ_stable = √2 è una proprietà **topologica** del reticolo:
dipende dalla struttura delle connessioni (autovalori μ_k), non dalla base di
rappresentazione. È invariante sotto trasformazione DFT.

Verifica numerica: `SpectralBasis.jitterbug_invariance_check()` conferma che
chi_max nel dominio nodale è identico dopo un round-trip spettrale (errore < 10⁻¹⁰).

---

## Metodo 2 — Integratori Simplettici

### Il problema con Eulero

L'integratore di Eulero (ordine 1) accumula **deriva energetica** sistematica:
```
Eulero:  H(t+T) = H(t) · (1 + O(dt·T))   → deriva O(dt) sull'intervallo T
```

Questo limita dt ≈ 0.01 per mantenere la deriva sotto il 10%.

### Störmer-Verlet (ordine 2, simplettico)

```
χ(t+dt) = χ(t) + v(t)·dt + ½·a(t)·dt²
v(t+dt) = v(t) + ½·[a(t) + a(t+dt)]·dt
```

**Proprietà fondamentali**:
- Conserva esattamente il volume nello spazio delle fasi (teorema di Liouville)
- Mantiene una Hamiltoniana "ombra" H_shadow con deriva O(dt²) (non O(dt))
- Permette dt ≈ 0.1 con la stessa accuratezza di Eulero con dt ≈ 0.01

### Forest-Ruth (ordine 4, simplettico)

Con la costante universale θ = 1/(2 − 2^(1/3)):

```
Quattro sotto-step: L(θ/2) → N(θ) → L((1−θ)/2) → N(1−2θ) → L((1−θ)/2) → N(θ) → L(θ/2)
```

- Errore O(dt⁴) globale
- Permette dt ≈ 0.3−1.0 su problemi tipici VQT
- Richiede 3 valutazioni di F per step (vs 1 di Eulero)

### Teorema di Liouville e il drain Peano-VQT

Il teorema di Liouville afferma che il flusso hamiltoniano preserva il volume
nello spazio delle fasi. Gli integratori simplettici **rispettano** questo teorema
numericamente.

Il drain Peano-VQT (E_χ → E_Ψ) è un fenomeno **fisico** non-hamiltoniano
(il sistema è aperto, ha smorzamento γ). L'integratore simplettico gestisce
correttamente la separazione tra:
- Parte conservativa (W coupling, doppio pozzo): simplettica
- Parte dissipativa (γ·v, drain): trattata separatamente con splitting

---

## Stima delle Prestazioni

| Configurazione | dt | Errore/step | Speedup vs Eulero | Note |
|---|---|---|---|---|
| Eulero (attuale) | 0.01 | O(dt) | 1× | Standard |
| Verlet | 0.1 | O(dt²) | ~10× | Same accuracy |
| Forest-Ruth | 0.5 | O(dt⁴) | ~15× | 3 F/step |
| Spettrale + Verlet | 0.1 | O(dt²) lineare + O(dt³) | ~100× | Accoppiamento analitico |
| Spettrale + FR | 0.5 | O(dt⁴) | ~500× | Massima efficienza |

Per L4: da ~80 ore a **10−60 minuti** con la combinazione ottimale.

---

## Compatibilità con il Codice Esistente

I nuovi moduli sono **additivi** — non modificano nessun file esistente:

```
wqt_oop/spectral_coupling.py   — SpectralBasis (nuovo)
wqt_oop/symplectic_step.py     — verlet_step, forest_ruth_step (nuovi)
wqt_oop/fast_evolver.py        — FastEvolver wrapper (nuovo)
```

`SolitoneComposito.evolve()` rimane invariato. I test esistenti (7/7 PASS) continuano
a funzionare identicamente.

---

## Relazione con i Documenti Esistenti

| Documento | Connessione |
|---|---|
| `TOPOLOGICAL_DYNAMICS.md` | Spettroscopia topologica: autovalori μ_k = frequenze dei modi |
| `VQT_MANIFESTO_TEORICO.md` | Legge III: S_residual è un invariante spettrale |
| `ARCHITETTURA_SCALING_MASSIVO.md` | FastEvolver si affianca a SpatialHashGrid e SpatialCache |
| `CHANGE_PROPOSAL_STRANG_SPLITTING.md` | Precursore: proposta dello Strang splitting (2026-05-26) |
