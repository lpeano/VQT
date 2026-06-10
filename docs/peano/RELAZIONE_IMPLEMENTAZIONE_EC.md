# Relazione finale: implementazione Einstein-Cartan (twist 180 deg alternati + chiusura 720 deg)

**Data**: 2026-06-09 · **Branch**: `physics/einstein-cartan-saturation`
**Autonomia**: lavoro eseguito in autonomia su richiesta di Luca, con la disciplina del
progetto (codice ADDITIVO, verifica prima di documentare, OOP preservato).

Tag: **[VER]** verificato in questa sessione · **[CNG]** congettura/scelta da confermare
· **[APERTO]** non risolto.

---

## 1. Sintesi esecutiva

Ho **recuperato e re-implementato** la dinamica di Einstein-Cartan persa nel refactoring
del 2026-05-26, come modulo NUOVO e additivo, senza toccare il motore legacy:

- **NUOVO** `wqt_oop/einstein_cartan.py`: la fisica EC (torsione a chiralita' alternata
  180 deg, chiusura spinoriale 720 deg, **saturazione = pressione di degenerazione di
  spin / bounce**). Funzioni pure, gradienti **verificati** (conservativi), stabili.
- **ADDITIVO** in `SolitoneComposito`: flag `ec_dynamics_enabled` (default OFF),
  metodi `apply_ec_kick()`, `evolve_with_ec()` (Strang half-kick), `set_ec_dynamics()`.
  `evolve()` legacy **INTATTO**.
- **[VER] GATE A/B**: con flag OFF, `evolve_with_ec` e' **bit-identico** a `evolve()`
  (max|dchi| = 0.000 su L2, 40 step, stesso seed). Con flag ON: **stabile** (no NaN,
  limitato), la dinamica EC agisce.

Stato onesto: il **nucleo fisicamente importante** (la saturazione EC = il termine che
mancava) e' implementato e verificato come forza conservativa stabile. La **geometria
esatta** del twist 180->720 resta una scelta documentata **[CNG/DA CONFERMARE con Luca]**.

---

## 2. Cosa ho fatto, e come

### 2.1 Analisi (lettura)
- **[VER]** Modulo recuperato `dinamica_hamiltoniana_chiralita.py` (git 5afefb9, 318
  righe): trasporto di densita' di chiralita' SX/DX sull'anello di 24, guidato dalla
  minimizzazione di `E_coupling + E_torsion`, con `E_torsion = beta*(K2 - K2_ref)^2`,
  `K2_REF_720 = 4*pi`, inversione/attrazione oltre 720 (bounce), "porosita'"
  (disaccoppiamento esponenziale). Chiralita' dal SEGNO del campo (`tanh(chi)`), NON
  dal twist per connessione. -> usato come SCHELETRO fisico, non copiato.
- **[VER] Archeologia**: la fisica EC fu cancellata nel commit a5b417e (2026-05-26,
  "cleanup obsolete files") ASSUMENDO che `wqt_oop/` l'avesse rimpiazzata; ma il
  refactoring OOP aveva portato solo il nucleo semplificato. **Perdita da cleanup
  prematuro + port incompleto, NON instabilita'.** -> re-implementabile.
- **[VER]** Motore attuale: il segmento ha `(chi, v)` dinamici + `tau` passivo +
  `contorsione` placeholder; la forza e' SOLO doppio pozzo + damping + coupling. Il
  composito L1 ha l'anello di 24 con `coupling_matrix`, estrae chi/tau dai figli,
  calcola `E_torsion` (diagnostico). La chiusura 720 e' gia' MISURATA
  (`compute_geometric_E_psi: closure_err = sum(tau) mod 4*pi`) ma non guidata.

### 2.2 Implementazione (`wqt_oop/einstein_cartan.py`)
Due settori, entrambi come **gradienti di un'energia ben definita** (conservativi):

1. **Settore chi (SATURAZIONE = il termine mancante)**:
   `E_sat = beta_sat * sum_i (K2_i - k2_ref)^2`, con `K2_i = sum_j W_ij(chi_i-chi_j)^2`
   (torsione di gradiente) e `k2_ref = (2*chi0)^2` (scala del salto Jitterbug pieno,
   NON un fit). La forza `F_chi = -dE_sat/dchi` **inverte segno oltre k2_ref**: la
   torsione in eccesso e' respinta -> la densita' SATURA. **E' la pressione di
   degenerazione di spin EC (il bounce) che mancava.** Gradiente analitico
   **[VER] verificato vs numerico (err_rel 3e-8)**.
2. **Settore tau (CHIUSURA 720 deg)**:
   `E_clo = kappa_closure * (sum(tau) - 4*pi)^2`, coerente col diagnostico
   `closure_err` gia' nel motore. `F_tau = -2 kappa (sum(tau)-4pi)` guida la fase
   spinoriale alla chiusura a 720.
- **Twist a chiralita' alternata 180 deg** (`bond_twist`): calcolato come **DIAGNOSTICO**
  della struttura (chiralita' da `sign(chi)` = up/down, alternanza `(-1)^b`, half-twist
  `+pi` per connessione). NON guida le forze, perche' la relazione esatta 180->720
  (24*180 != 720) e' **[DA CONFERMARE]**: forzarla sarebbe l'errore "termine elegante
  non verificato".

### 2.3 Hook additivo (`SolitoneComposito`)
- `__init__`: `ec_dynamics_enabled=False`, coeff `ec_beta_sat=1e-8`,
  `ec_kappa_closure=1e-2`, `ec_k2_ref_chi=(2*chi0)^2`.
- `apply_ec_kick(dt)`: su ogni blocco L1 (figli = segmenti) calcola le forze EC e le
  applica come kick additivo (`vel += F_chi*dt`, `tau_locale += F_tau*dt`); ricorre nei
  sotto-compositi per L>=2.
- `evolve_with_ec(dt)`: se flag OFF -> `evolve()` puro; se ON -> Strang (half-kick,
  evolve legacy, half-kick). `evolve()` NON modificato.
- `set_ec_dynamics(enabled, ...)`: attiva su tutto l'albero.

### 2.4 Verifica [VER]
- **GATE A/B**: flag OFF -> bit-identico a legacy (diff 0.000, L2/40 step, seed fisso).
  Il "fallimento" iniziale era il non-determinismo np.random globale (gotcha noto),
  non un bug: risolto seedando + run separati.
- **Stabilita'**: flag ON, L2, 60 step: no NaN, chi limitato, EC agisce (dchi ~3e-3
  coi coeff conservativi). Il self-test del modulo: gradiente OK, twist limitato.

---

## 3. INVENTARIO COSTANTI HARDCODED (cosa eliminare / cosa resta)

### 3.1 Da ELIMINARE/RIVEDERE (i coupling postulati/legacy = il problema di ieri)
In `physics_context.for_level` (le leggi di scala NON derivate, vedi DIAGNOSI sez.1.2):
- **`lambda_exchange ~ 24^(2L)`** (`energy_scale = 24**(2*level)`): LEGACY "esplosivo",
  riconosciuto catastrofico, mai sistemato. **PRIORITA' 1 di rimozione.**
- **`alpha_K ~ 1/24^L`** (`alpha_K_rg_exponent=1.0`): fix post-hoc, derivazione con ???.
- **`kappa ~ 1/24^(L/2)`** (`kappa_rg_exponent=0.5`): da 1 dato empirico.
- **`gamma_damping ~ (24^L)^0.2`** (`damping_scaling_exponent=0.2`): esponente scelto.
- **`d_f=2`** (commento, hardcoded in 24^(2*level)): assunto, non derivato.
> Tesi (da verificare): con la SATURAZIONE EC fisica, questi rattoppi diventano
> superflui -> i coupling dovrebbero tornare SCALE-INVARIANTI (la chiusura 24->720 e'
> scale-invariante). Test n.1 della prossima fase. NON rimossi ora: prima si verifica
> che l'EC li rimpiazzi (codice additivo, niente regressioni).

### 3.2 Da MANTENERE (fisiche/topologiche, NON fit fragili)
- `chi_stable = 50.0` (VEV del campo).
- `TAU_CLOSURE_4PI = 4*pi`, `HALF_TWIST_PI = pi` (chiusura spinoriale 720, half-twist
  180): **topologiche**, non calibrabili.
- `beta_potential` (doppio pozzo Landau-Ginzburg on-site).
- la struttura della `coupling_matrix` (Leech/cubottaedro).
- l'integratore simplettico (Verlet) - verificato.

### 3.3 Da RIVALUTARE dopo l'EC (non ora)
- **Riscaldamento gerarchico** (`hierarchical_heat_fraction=0.9`): se la saturazione EC
  assorbe l'overflow, la "febbre" (temperatura cresce ~15%/livello) dovrebbe ridursi
  -> il serbatoio potrebbe diventare superfluo. (Ieri: la febbre NON veniva dal
  serbatoio ne' da lambda; verificare se viene dall'assenza di saturazione.)
- Costanti FDT (`T_eff=583`, `alpha_fdt=10`, `beta_fdt=2`): bagno termico empirico;
  rivalutare se l'EC cambia il bilancio energetico.

### 3.4 DINAMICHE che RESTANO
Il nucleo simplettico (Verlet su chi,v) + il doppio pozzo on-site. L'EC e' ADDITIVO
sopra. Nessuna dinamica legacy rimossa (additivita' garantita dal GATE A/B).

---

## 4. Punti pendenti di ieri: stato

- [x] Leggere il modulo recuperato INTERO -> fatto (sez.2.1).
- [x] Perche' fu tolto -> cleanup prematuro, non instabilita' (sez.2.1).
- [~] [DA CONFERMARE] geometria 180->720: scelte fatte e DOCUMENTATE (chiusura su
  sum(tau), chiralita' da sign(chi), twist diagnostico). Servono conferme di Luca su:
  aritmetica esatta 180/connessione vs 720/globale; "complementare" = pozzo opposto?;
  sinusoide in chi o in tau. **[APERTO]**
- [x] Implementare EC additivo + verificare A/B -> fatto (sez.2.2-2.4).
- [~] Coupling postulati: inventariati, tesi della dissoluzione enunciata, da
  verificare attivando l'EC e misurando se i coupling possono tornare costanti. **[APERTO]**
- [ ] `rho*_Leech == rho*_EC`: non affrontato (teorico). **[APERTO]**

---

## 5. Cosa e' VERO e cosa NO (onesta')

**[VER] Vero (verificato):**
- Il termine di saturazione EC esiste ora nel codice, come forza conservativa
  (gradiente verificato) e stabile, additiva, opt-in.
- Il legacy e' intatto (GATE A/B bit-identico).
- La fisica EC era stata persa per cleanup, non e' un'idea sbagliata.

**[CNG/APERTO] NON ancora vero (da fare):**
- Che questa dinamica EC sia la fisica GIUSTA (la geometria 180->720 e' una scelta).
- Che i coupling postulati si dissolvano (tesi, da misurare).
- Che la saturazione produca il bounce/no-singolarita' e tolga la febbre (da misurare
  in un run lungo con flag ON).
- L'aritmetica esatta del twist e il legame rho*_Leech/rho*_EC.

---

## 6. Prossimi passi (prossima sessione)

1. **Confermare con Luca** i [DA CONFERMARE] geometrici (sez.4) -> raffinare
   `bond_twist`/la chiusura se serve.
2. **Misurare** con flag ON su L1/L2 (run lungo): la densita' satura? la febbre
   (temperatura per-foglia) si riduce vs legacy? GATE statistico.
3. **Tarare** `beta_sat`, `kappa_closure` legandoli a scale fisiche (e a rho*).
4. **Test della dissoluzione dei coupling**: con EC attivo, i coupling possono essere
   resi scale-invarianti senza perdere la fenomenologia? -> se si', rimuovere i
   rattoppi di sez.3.1.
5. Teorico: `rho*_Leech == rho*_EC`? (la pietra angolare).

File toccati: `wqt_oop/einstein_cartan.py` (NUOVO), `wqt_oop/solitone_composito.py`
(additivo: __init__ + 3 metodi, evolve() intatto). Verifiche inline (non committate
come test permanenti: candidate a diventare `test_einstein_cartan_equivalence.py`).
