# Metodo per studiare il comportamento multi-livello senza simulare L>7

**Branch**: `perf/evolve-vectorized` (analisi) · **Data**: 2026-06-05 · **Status**: PIANO + ANALISI (nessun esperimento ancora eseguito)

> Risponde a due domande poste nella sessione del 2026-06-05:
> 1. "Esiste un metodo per capire come varia il comportamento del sistema ai vari
>    livelli senza dover arrivare a L>7?"
> 2. "Il teorema Peano-VQT e' valido e ci puo' aiutare in questo?"
>
> Contesto: e' stato stabilito (vedi ARCHITETTURA_VETTORIZZAZIONE.md sez. 9-9c) che
> la simulazione diretta non raggiunge L>7, e che la scala metrica dei livelli e'
> microscopica (L5-L7 ~ 1e-32..1e-33 m, il protone cade a L~43). Quindi il ponte
> verso la realta' umana NON puo' essere computazionale: deve essere teorico.

---

## Parte 1 — Il metodo: Gruppo di Rinormalizzazione (RG) sulla gerarchia

### 1.1 Intuizione centrale

La gerarchia VQT **E' GIA'** una trasformazione RG di Kadanoff (block-spin):

```
24 nodi figli  --(media del blocco)-->  1 nodo genitore
```

Questa e' la definizione di trasformazione di blocco. Quindi passare da L_n a
L_{n+1} = applicare una volta l'operatore RG. Non serve simulare L grande: serve
**catturare la regola con cui un livello si trasforma nel successivo**, e iterarla
analiticamente (aritmetica, costo zero) fino a L infinito. I punti fissi della
regola = comportamento asintotico del sistema.

### 1.2 Le grandezze che FLUISCONO (gia' osservate)

Esistono gia' due punti di una traiettoria di flusso:

```
chi_c / chi_stable:   L2 = 1.338   ->   L3 = 1.240   ->   L4 = ? (da misurare)
```

Non e' rumore: e' una traiettoria RG che scende. La domanda "come si comporta a L
grande" diventa: **verso quale valore converge, e con che legge?**

Altri osservabili candidati al flusso (da tracciare tutti su L2, L3, L4):
- chi_c/chi_stable (soglia di nucleazione, FSS) — gia' 1.338, 1.240
- esponente densita' difetti p (= 1.79 +- 0.13 a L2) — universalita' se invariante
- lunghezza di correlazione del coupling (~3 nodi) — adimensionale, dovrebbe fluire
- f_dom (ritmo intrinseco) — gia' misurato FSCALE-invariante (ancora candidata: fixed)
- esponente di scaling di E_Psi con N (vedi Parte 2) — NUOVO, dal teorema

### 1.3 Due strade, nessuna richiede L>7

| Strada | Cosa fai | Cosa ottieni |
|---|---|---|
| A. Finite-Size Scaling | Fit `O(L) = O_inf + a*24^(-L/nu)` su L2,L3,L4 | Valore asintotico O_inf + esponente nu, estratti da 3 livelli |
| B. Mappa RG esplicita | Misuri la trasformazione `T: g_L -> g_{L+1}` tra livelli | La regola del flusso; la iteri fino a L qualsiasi; i punti fissi = destino |

### 1.4 Il test di auto-consistenza (qui si affronta l'emergenza)

Misurare la mappa DUE volte e confrontarla:

```
T misurata su (L2 -> L3)     vs     T misurata su (L3 -> L4)
```

- Coincidono -> il sistema e' nel "regime di scala": la regola e' stabile,
  l'estrapolazione e' legittima. Si ottiene una predizione per ogni L.
- Divergono -> si e' MISURATA l'emergenza: quanto e in che direzione la regola
  cambia per livello. Si estrapola allora LA DERIVA della regola.

Punto chiave (risponde al timore espresso dall'utente sull'emergenza): la
scale-invarianza NON viene assunta. Viene messa alla prova su 3 livelli economici
e se ne quantifica l'eventuale rottura. Anche il fallimento e' un risultato.

### 1.5 Vantaggio specifico del VQT: la mappa e' gia' analitica

In `wqt_oop/physics_context.py` i coupling sono gia' scale-dependent:

```
alpha_K ~ 1/24^L        kappa ~ 1/24^(L/2)
```

Questo E' il flusso RG dei coupling in forma chiusa. Si possono quindi CONFRONTARE:
1. PREDETTO: come queste formule dicono che il sistema dovrebbe fluire.
2. MISURATO: come gli osservabili fluiscono davvero su L2-L3-L4.

Concordano -> mappa RG validata, estrapolazione affidabile. Divergono -> si sa
esattamente quale coupling l'analitica sbaglia.

---

## Parte 2 — Il teorema Peano-VQT: e' valido? Aiuta?

### 2.1 Cos'e' realmente il "teorema"

Dal VQT_MANIFESTO_TEORICO.md, il "teorema" e' la **triade energetica**
`E_chi + E_RX + E_Psi` con tre leggi:
- Legge I (Aggregazione di Leech): solitoni iso-fase aggregano in cluster di 24.
- Legge II (Frustrazione): solitoni cross-fase si respingono, dissipano ~3x.
- Legge III (Conservazione Peano-VQT): `dE_chi + dE_RX + dE_Psi = 0`, E_Psi monotona.

### 2.2 Validita': cosa regge e cosa va ridimensionato

**Cosa regge (solido):**
- L'invariante `dE_chi + dE_RX + dE_Psi = 0` e' VERO e verificato numericamente
  (total_before = total_after = 105.0, Delta < 1e-10). E' un controllo di
  consistenza del bilancio energetico: nessuna energia si perde nel bookkeeping.
- Le Leggi I e II sono regolarita' EMPIRICHE ben supportate dai run (aggregazione
  spontanea a 24 nel run L4; rapporto di dissipazione frustrato/aggregato ~2.87x).
- E_Psi come DISCRIMINATORE (salto >5% = cristallizzazione; E_Psi alto = frustrazione)
  e' una firma fenomenologica reale e utile.

**Cosa va ridimensionato (onesta'):**
- La conservazione e' vera PER COSTRUZIONE: il drain e' DEFINITO come
  `E_chi -= delta; E_Psi += delta; E_RX invariato`, quindi la somma si conserva
  banalmente. E' un'identita' di bilancio, NON una legge di conservazione scoperta
  nella dinamica. Distinguere "il codice conserva cio' che ho definito conservato"
  da "la dinamica possiede un invariante".
- La monotonia di E_Psi e' anch'essa per costruzione (drain >= 0): l'irreversibilita'
  e' INSERITA a mano (sink dissipativo), non derivata. Legittima come modello di
  sistema aperto, ma non e' una predizione del modello.
- E_Psi e' un SINK esterno -> il sistema e' APERTO. "Conservazione" qui significa
  "traccio dove finisce l'energia dissipata" (contabilita'), non conservazione di
  un sistema chiuso. Da non confondere.
- Status logico corretto: e' un **principio di conservazione (bilancio) + leggi
  fenomenologiche** (tipo leggi di Keplero: regolarita' empiriche), NON un teorema
  dimostrato da assiomi. Robusto come impalcatura di consistenza e come descrizione;
  sovrastimato se presentato come "teorema provato".

### 2.3 Aiuta il programma RG? SI', e qui sta il valore vero

Tre agganci concreti tra il teorema e il metodo della Parte 1:

1. **E_Psi e' un osservabile che FLUISCE, gia' pronto.** Il manifesto documenta gia'
   "E_Psi scala superlinearmente con N". L'esponente `a` in `E_Psi ~ N^a` (a>1) e'
   esattamente il tipo di quantita' RG da tracciare su L2-L3-L4. Si innesta diretto
   nella tabella degli osservabili (sez. 1.2).

2. **La triade, SE RG-covariante, e' un invariante strutturale del flusso.** In RG,
   sotto coarse-graining si perdono i dettagli ma SOPRAVVIVONO le quantita' conservate
   e le simmetrie: sono gli ANCORAGGI del flusso. Se la partizione E_chi/E_RX/E_Psi
   conserva la stessa FORMA per i block-means al livello superiore, la triade vincola
   il flusso e riduce il rischio di estrapolazione. DA VERIFICARE (non assumere).

3. **E_Psi monotona suggerisce una c-function di scala.** E_Psi e' monotona nel TEMPO.
   Se si trovasse un analogo monotono nella SCALA (livello -> livello), sarebbe una
   "c-function" alla Zamolodchikov: lo strumento piu' potente per controllare il
   limite L->infinito e identificare i punti fissi. Speculativo ma promettente.

### 2.4 Conclusione sul teorema

Il teorema NON dimostra di per se' lo scaling multi-livello, e la sua "conservazione"
e' in buona parte definitoria. MA fornisce due cose preziose al programma RG:
(a) un osservabile che fluisce gia' caratterizzato (E_Psi e la sua legge di scala);
(b) una possibile struttura invariante (la triade) che, SE RG-covariante, e'
proprio l'ancora che serve per controllare l'estrapolazione. Va pero' RI-TESTATO
come proprieta' del flusso, non assunto.

---

## Parte 3 — Cosa fare (piano operativo)

Prerequisito trasversale: **misurare a L4** (gia' fattibile, vedi scale-limits).
Con L4 si passa da 2 a 3 punti -> primo vero fit di flusso.

- [ ] **P1. Strumento multi-osservabile L2/L3/L4.** Script che, per ogni livello,
      misura e logga: chi_c/chi_stable, p, lunghezza di correlazione coupling,
      f_dom, partizione (E_chi, E_RX, E_Psi), esponente E_Psi~N^a. Riusa il
      pattern resume/parallel gia' nel progetto. (docs: TESTS_E_STRUMENTI.md)
- [ ] **P2. Fit FSS (Strada A).** `O(L) = O_inf + a*24^(-L/nu)` su L2,L3,L4 per
      ogni osservabile -> valore asintotico + nu. Parte da chi_c (1.338, 1.240, ?).
- [ ] **P3. Mappa RG (Strada B) + test di consistenza.** Misurare T:(L2->L3) e
      T:(L3->L4), confrontarle. Concordanza -> regime di scala; discordanza ->
      quantificare la deriva (emergenza misurata).
- [ ] **P4. Confronto predetto vs misurato** dei coupling (alpha_K~1/24^L,
      kappa~1/24^(L/2)) contro il flusso osservato degli osservabili.
- [ ] **P5. Test RG-covarianza della triade.** Verificare se la conservazione
      E_chi+E_RX+E_Psi mantiene la stessa forma per i block-means coarse-grained.
      Se si', cercare una c-function di scala basata su E_Psi.
- [ ] **P6. [DOPO L4] Test del winding del parametro d'ordine psi.** Cluster =
      campo complesso GL `psi_B = m_B*exp(i*phi_B)`; testare se la massa e' un
      DIFETTO TOPOLOGICO di psi (winding intero della fase + dip di |psi| nel core).
      Protocollo completo in FORMALIZZAZIONE_MASSA_TOPOLOGICA.md sez. 7.3. Se il
      winding e' intero -> massa = carica topologica quantizzata (il dominio GIUSTO
      per un'eventuale "legge dei divisori": un conteggio, non le energie).
- [ ] **P7. [eseguibile gia' ora] Decomposizione spettrale a due canali.** Campo
      congelato -> canale RADIALE (ampiezza m_B = massa, Higgs-like) vs canale FASE
      (phi_B dal settore tau = propagazione, Goldstone-like). DFT su Z_24 del canale
      di fase: i periodi 24/gcd(m,24) SONO i divisori di 24 (struttura della base,
      esatta). Test: split di energia, ortogonalita' (cross-corr ~0), dove sta la
      potenza. NB: difetto singolo si SPALMA su tutti i modi (atteso, non struttura);
      concentrazione su divisori solo da pattern collettivi. Protocollo:
      FORMALIZZAZIONE_MASSA_TOPOLOGICA.md sez. 8. Tool: analyze_spettro_cluster.py
      (usa SpectralBasis SOLO come diagnostica, NON l'integratore spettrale buggato).

NB metodologico (vincolo di progetto): nessun numero/affermazione di performance o
di fisica va scritto prima di averlo MISURATO. Questo documento e' un PIANO: i
risultati vanno aggiunti solo dopo l'esecuzione, con sorgente di log/dato.
