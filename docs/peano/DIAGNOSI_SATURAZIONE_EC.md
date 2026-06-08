# Diagnosi: i coupling postulati e il termine di saturazione Einstein-Cartan mancante

**Data**: 2026-06-08 · **Branch**: `physics/einstein-cartan-saturation`
**Origine**: sessione del 2026-06-08, partita dalla misura del flusso RG di chi_c e
arrivata, via "verifica prima di interpretare", a una diagnosi foundational.

---

## Avvertenza epistemica

Tag come nel resto del progetto, con due aggiunte:
- **[VER]** Verificato in questa sessione (codice letto / misura fatta). FATTO.
- **[CNG]** Congettura / cornice teorica (plausibile, NON dimostrata).
- **[APERTO]** Problema non risolto, cuore del lavoro futuro.

Questo documento separa con cura cio' che e' VERIFICATO (la diagnosi) da cio' che e'
CONGETTURATO (la cura). La cura NON e' ancora ne' implementata ne' verificata.

---

## 1. I fatti VERIFICATI oggi (la diagnosi)

### 1.1 [VER] Il "flusso di chi_c" e' una parametrizzazione, non una legge derivata

Misurato chi_c/chi_stable: L2=1.353, L3=1.237 (P1/P2). L4 lanciata, poi fermata
(sweep mis-centrato: cm54-57 nucleavano gia' al 100% con M_tot~1e6, plasma ->
chi_c(L4)<1.08). Il flusso NON si appiattisce verso un punto fisso a 1.23: continua
a scendere. MA (sotto) e' confuso.

### 1.2 [VER] Le leggi di scala dei coupling sono POSTULATE/LEGACY

In `physics_context.for_level` + `RG_FLOW_TOPOLOGICAL_SCREENING.md`:
- `alpha_K ~ 1/24^L`: FIX post-hoc per instabilita'. La "derivazione" nel doc e'
  auto-contraddittoria (da' sia 24^(2n) sia 1/24^n, con `???` letterali nel testo).
  Calibrata su UN solo rapporto empirico K_L2/K_L1=0.185.
- `kappa ~ 1/24^(L/2)`: da quell'unico rapporto (beta≈0.5).
- `lambda_exchange ~ 24^(2L)`: scaling LEGACY "esplosivo", riconosciuto dal progetto
  stesso come "instabilita' catastrofica" per alpha_K, MAI sistemato per lambda
  ("mantiene scaling old per backward compatibility", physics_context riga 208).
- `gamma_damping ~ (24^L)^0.2`: esponente "conservativo" scelto.
- `d_f = 2`: appare solo come COMMENTO (hardcoded in 24^(2*level) per lambda), NON
  e' una quantita' derivata.
-> Nessuna deriva da principi primi. Il motore E' fisico nel nucleo (integratore
   simplettico verificato a 1e-7), ma le leggi di corsa dei coupling sono un fit.

### 1.3 [VER] La temperatura per-foglia cresce con N (confound, causa non pinnata)

KE/foglia a cm54, 40 step: L1=625, L2=744, L3=832 (~15%/livello). ROBUSTA: invariata
con serbatoio OFF (`hierarchical_heat_fraction=0`) e con `lambda_exchange` azzerato.
Due ipotesi sulla causa SBAGLIATE (serbatoio, lambda). Effetto MITE, probabilmente
separato dal grosso calo di chi_c.

### 1.4 [VER] Confound dell'osservabile

chi_c via P(M_tot>1) = P(>=1 difetto OVUNQUE) scala con N per STATISTICA DEI VALORI
ESTREMI, non criticita' intrinseca. -> usare la DENSITA' n_def/N (intensiva).

### 1.5 [VER] Il termine di saturazione Einstein-Cartan MANCA nel motore

`segmento_quantistico._compute_force` (riga 422-476) ha SOLO:
1. `F_potential = -4*beta*chi*(chi^2-chi_0^2)` (doppio pozzo Landau-Ginzburg);
2. `F_dissipative` (smorzamento FDT);
3. `F_external` (coupling dal genitore).
La torsione `K^2` e' marcata "proprieta' GEOMETRICA che emerge" (riga 45) = DIAGNOSTICO
PASSIVO, non entra nella forza. La `contorsione` e' un "Placeholder per compatibilita'"
(riga 173). Cercata in tutto `wqt_oop/`: nessuna `RHO_SATURATION`/`rho_max`/densita'
critica. **La pressione di degenerazione di spin EC (beta*rho^2, sez. 6 di
TEORIA_FISICA_COMPLETA.md) NON e' implementata nella dinamica.**

### 1.6 [VER] Clustering (P10) uniforme nel plasma

6 campi L4 plasma (~5000 difetti): fattore di Fano ~1.0 a tutte le scale -> Poisson/
uniforme, NO rete cosmica nel regime denso. Il regime diluito non e' testato.

---

## 2. La DIAGNOSI [CNG]

> Il solitone di base NON ha una saturazione fisica perche' manca il termine di
> Einstein-Cartan `P_rep = beta*rho^2` (pressione di degenerazione di spin che da' il
> BOUNCE quando rho->infinito). Senza di esso la densita' non si auto-limita -> il
> modello l'ha FALSIFICATA con i coupling postulati (alpha_K~1/24^L, lambda legacy) e
> l'energia che non puo' condensare diventa CALORE (la temperatura crescente).

Questa singola assenza e' coerente con TUTTI i fatti VER della sez. 1: il flusso di
chi_c (i coupling truccati), la febbre (overflow), il bisogno di leggi di scala
postulate. E' una diagnosi, non una dimostrazione: va testata implementando il termine.

---

## 3. La CORNICE TEORICA [CNG] (la cura, da costruire)

### 3.1 Il solitone di base E' un oggetto Einstein-Cartan
tau = fase spinoriale (chiusura a 720°/4pi, spin-1/2), K = torsione/contorsione. Le
equazioni di campo nei docs (TEORIA_FISICA_COMPLETA §6) sono EC esplicite:
`R_uv - 1/2 g_uv R + Lambda g_uv = 8piG T_uv`, `S_λμν = (kappa_spin/8piG) sigma_λμν`
(torsione S sorgentata dalla densita' di spin sigma).

### 3.2 La saturazione viene dalla pressione di spin EC
`P_rep = beta*rho^2` (TEORIA_FISICA_COMPLETA §6.2, riga 207-210): "cresce
quadraticamente con la densita'; quando rho->inf, P_rep>>P_grav -> BOUNCE!". E' il
bounce di Einstein-Cartan (la torsione regolarizza la singolarita'). Questo da' una
densita' di saturazione `rho*` DERIVATA da G, kappa_spin e dallo spin, NON postulata.

### 3.3 Saturazione di Leech = saturazione EC?  [APERTO, la posta vera]
Due densita' critiche costanti:
- `rho*_Leech` = densita' d'impacchettamento geometrica (Lambda_24, costante a ogni
  livello: la cella a 24 nodi e' la stessa). NB: Leech da' rho* COSTANTE, NON 1/24^L.
- `rho*_EC` = densita' di bounce di spin.
Se `rho*_Leech = rho*_EC`, geometria (Leech) e gravita' (spin EC) coincidono -> i
coupling sarebbero DETERMINATI. E' il cuore del "Muratore di Planck come teoria".

### 3.4 Densita' costante -> espansione -> rete cosmica
Se rho* e' COSTANTE e la materia aumenta, per mantenere rho=rho* lo SPAZIO deve
espandersi: `dN/dt = (1/rho*) dE/dt`. Con iniezione di punto-zero per-nodo (Nyquist)
`dE/dt = eps*N` -> `N(t)=N_0 exp((eps/rho*)t)`: espansione esponenziale (de Sitter),
con H=eps/rho* costante. Struttura della costante cosmologica / gravita' UNIMODULARE
(e Lambda_24 e' unimodulare: risonanza [CNG], non dimostrata). La materia = sovra-
densita' che condensa piu' in fretta di quanto l'espansione la diluisca (~ Delta t_relax
gia' misurato) -> distribuzione INOMOGENEA = rete cosmica (il clustering, assente nel
reticolo fisso, emergerebbe qui).

---

## 4. IL PIANO (additivo, verificato, su questo branch)

Regole (CLAUDE.md): codice ADDITIVO dietro flag (legacy intatto), branch dedicato,
verifica prima di documentare come fisica. NON ripetere l'errore di oggi (termine
elegante non verificato).

- [x] **1. Branch + questo documento di diagnosi.** FATTO.
- [ ] **2. [DESIGN, il punto critico] Derivare la FORMA discreta di `P_rep=beta*rho^2`.**
      Mappare la densita' di spin sigma sullo stato del segmento (da tau? dalla
      concentrazione locale?), tradurla in forza su chi via S=sigma. Il coefficiente
      beta legato a rho* (G, kappa_spin, idealmente rho*_Leech). DERIVATA da sigma->S,
      NON indovinata.
- [ ] **3. [IMPL] Aggiungere il termine additivo** in `_compute_force` dietro flag
      `ec_saturation_enabled` (default OFF). Legacy preservato.
- [ ] **4. [VERIFICA]** La densita' si auto-limita al bounce? La febbre si riduce? La
      nucleazione diventa fisica? Servono ancora i coupling postulati o spariscono?
      A/B contro il legacy. GATE statistico.
- [ ] **5. [TEORIA]** Calcolare se rho*_EC = rho*_Leech (sez. 3.3).

### Problemi [APERTO] che decidono se e' teoria o rattoppo
1. La forma discreta di beta*rho^2 (sez. 4 passo 2) — il cuore fisico.
2. rho* in unita' del modello (= densita' di Leech? di bounce EC?).
3. Se serve N dinamico (espansione) per la coerenza, o se la saturazione basta.

---

## 5. Cosa NON cambia (sta in piedi)

- L'integratore simplettico (verificato equivalente a RK45, 1e-7).
- I risultati a livello fisso (massa = difetto topologico, bimodalita', difetto
  single-site, Delta t_relax ~50).
- La pipeline P1-P10 (tool funzionanti, committati). Cambia COSA misuriamo (densita'
  intensiva, non il binario) e COME interpretiamo (i coupling come parametrizzazione).
