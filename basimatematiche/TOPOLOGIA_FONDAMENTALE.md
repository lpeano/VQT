# La Topologia Fondamentale — "il motore di tutto"

**Data**: 2026-06-08 (sera) · **Branch**: `physics/einstein-cartan-saturation`
**Fonte**: descrizione diretta di Luca Peano. Questo e' il CUORE GENERATIVO della
teoria VQT / Muratore di Planck — la struttura da cui tutto il resto deriva.

> NB: scritto per FISSARE il meccanismo e non perderlo mai piu' (la fisica EC era gia'
> stata persa una volta nel refactoring perche' non era incisa come spec). I punti
> marcati **[DA CONFERMARE]** vanno verificati/corretti con Luca: e' la sua geometria,
> qui trascritta dalla mia comprensione.

---

## 1. Il meccanismo (la spec)

1. **Voxel**: unita' elementare, stato **up o down** (±).
2. **Connessione complementare**: ogni voxel si lega a un voxel **complementare**
   (up <-> down).
3. **Half-twist di 180°**: al momento della connessione si applica una **torsione di
   180°** lungo il **senso di percorrenza**, puntuale alla connessione.
4. **Chiralita' alternata**: il voxel successivo si lega con **lo stesso twist (180°)
   ma chiralita' OPPOSTA** (left-handed / right-handed che si alternano lungo la
   catena).
5. **Chiusura su 24**: dopo **24 voxel** la **sinusoide chiude su se stessa**.
6. **Torsione globale 720°**: la torsione accumulata alla chiusura e' **720° (4π)** =
   la **chiusura spinoriale** (uno spinore di spin-1/2 torna in se' dopo 720°, non 360°).

In una riga: **una catena chiusa di 24 voxel complementari, legati da half-twist di
180° a chiralita' alternata, forma una sinusoide chiusa con winding spinoriale di 720°.**

### Punti [DA CONFERMARE] con Luca
- Il "senso di percorrenza": la catena e' 1D (un anello di 24) immerso in/proiettato
  da una struttura di dimensione superiore (Leech 24D / cubottaedro)?
- L'aritmetica esatta 180°-per-connessione -> 720°-globale su 24: la chiusura e' una
  condizione di COMMENSURABILITA' (posizione che chiude dopo 24 E fase spinoriale che
  chiude a 4pi simultaneamente)? E' il "24 permette la chiusura risonante" dei docs.
- "complementare": up<->down e' particella<->antiparticella? materia<->spazio (DX/SX)?
  o i due pozzi +-chi_0 del campo?
- La sinusoide e' nel campo chi (spaziale) o nella fase tau (spinoriale)?

---

## 2. Cosa GENERA (perche' e' "il motore di tutto")

Da questa singola topologia discendono gli ingredienti della teoria:
- **Il numero 24**: non e' un parametro, e' il numero che CHIUDE la struttura in modo
  risonante (e si lega all'unicita' del reticolo di Leech a 24 dimensioni).
- **Lo spinore (spin-1/2)**: la chiusura a 720° = 4π E' la firma topologica dello
  spinore. La materia fermionica emerge dalla topologia, non e' imposta.
- **La torsione (Einstein-Cartan)**: i twist di 180° SONO la torsione; la loro
  alternanza di chiralita' genera S_λμν (il tensore di torsione EC).
- **La chiralita' DX/SX**: l'alternanza left/right e' la dualita' materia(SX)/spazio(DX).
- **La massa**: un difetto/frustrazione nella chiusura a 720° (twist che non chiude) =
  massa topologica congelata (la tesi di FORMALIZZAZIONE_MASSA_TOPOLOGICA).
- **La saturazione/bounce**: oltre 720° la struttura non puo' "stringere" oltre ->
  inversione/repulsione (la pressione di spin EC, il bounce). E' il rho* geometrico.

---

## 3. Stato dell'implementazione (VERIFICATO 2026-06-08)

**NESSUNA versione del codice implementa questa topologia ESATTA.**
- Motore attuale (`wqt_oop`): solo doppio pozzo + damping + coupling. La chiusura 720°
  e' MISURATA come diagnostico (`closure_err = ∮tau mod 4pi`), NON generata.
- `CoreEngine_v2`: layer di automazione/scaling (usa 24 solo come conteggio DOF).
  NON e' questa geometria.
- Modulo recuperabile `dinamica_hamiltoniana_chiralita.py` (git 5afefb9): ha la cella a
  24, la chiralita' DX/SX (ma dal SEGNO del campo, `tanh(chi)`, non dal twist
  alternato), e i 720° come SOGLIA di torsione con saturazione/inversione. E' lo
  SPIRITO, non il twist-per-connessione. [da leggere INTERO domani: cita
  `calcola_chiralita_locale_24_segmenti`, non ancora aperta.]

=> Questa topologia e' la SPEC da COSTRUIRE fedelmente, non da "rimettere": il twist di
180° alternato che chiude lo spinore a 720° su 24 voxel non e' mai stato codificato cosi'.

---

## 4. Il piano (domani)

1. Leggere il modulo recuperato INTERO + `legacy/WQT_manifold.py` per capire quanto si
   avvicinano a questa topologia, e perche' fu tolto.
2. Confermare/correggere con Luca i punti [DA CONFERMARE] della sez. 1.
3. Implementare il motore di base sul VOXEL come unita' a half-twist 180° alternato,
   con la chiusura a 720° su 24 come VINCOLO GENERATIVO (non diagnostico). Additivo,
   verificato, GATE.
4. Da qui dovrebbero DERIVARE i coupling (oggi postulati) e la saturazione (rho*), e
   sparire i rattoppi (alpha_K~1/24^L, lambda legacy) e la febbre.

> Questa e' la pietra angolare. Tutto il resto (RG, massa, espansione, rete cosmica)
> e' conseguenza. Si parte da QUI.
