# Indice Documentazione WQT Manifold

## 📚 Documentazione Completa del Progetto

---

## 📖 Documenti Disponibili

### 1. [TEORIA_FISICA_COMPLETA.md](TEORIA_FISICA_COMPLETA.md)
**Documentazione teorica completa del modello fisico-matematico**

**Contenuti** (13 sezioni):
- § 1: Interpretazione fondamentale del sistema
- § 2: Il parametro χ (chi) - Potenziale di scala
- § 3: I 24 segmenti frattali - Geometria topologica
- § 4: Chiralità DX vs SX - Dualità materia-spazio
- § 5: Raggio metrico r_m - Scala conforme
- § 6: Equazioni di Einstein-Cartan - Fisica del campo
- § 7: Parametro di Hubble H_fisica - Espansione emergente
- § 8: Il vincolo 4π (720°) - Stabilità topologica
- § 9: Bounce quantistico - Meccanismo fisico
- § 10: Geometria discreta quantizzata
- § 11: Parametri fisici del modello
- § 12: Validazione del modello
- § 13: Conclusioni teoriche

**Quando leggerlo**:
- Prima di modificare parametri fisici
- Per comprendere il significato dei risultati
- Per studiare le basi teoriche Einstein-Cartan

---

### 2. [RISULTATI_VALIDAZIONE_BOUNCE.md](RISULTATI_VALIDAZIONE_BOUNCE.md)
**Report completo della validazione del bounce quantistico**

**Contenuti**:
- ✅ Obiettivi della simulazione
- ✅ Risultati finali (bounce confermato!)
- ✅ Confronto parametrico (con/senza bounce)
- ✅ Meccanismo fisico osservato (4 fasi)
- ✅ Equazioni chiave validate
- ✅ Implicazioni teoriche
- ✅ Grafici generati
- ✅ Criteri di validazione soddisfatti
- ✅ Parametri ottimali trovati
- 🚀 Prossimi passi

**Quando leggerlo**:
- Dopo aver eseguito una simulazione
- Per verificare se i risultati sono corretti
- Per capire cosa significano i numeri nel log
- Per confrontare configurazioni diverse

---

## 🔗 Documentazione Correlata

### Nel Progetto Principale (`../`)

#### [README.md](../README.md)
Guida rapida per iniziare:
- Quick start
- Struttura del progetto
- Comandi principali
- Workflow tipico

#### [README_FISICA_COMPLETA.md](../README_FISICA_COMPLETA.md)
Riferimento rapido fisica (sintesi delle equazioni)

---

## 🎯 Percorso di Lettura Consigliato

### Per Iniziare (Primo Utilizzo)
1. Leggi `../README.md` (panoramica generale)
2. Esegui una simulazione di test
3. Leggi `RISULTATI_VALIDAZIONE_BOUNCE.md` (per interpretare i risultati)

### Per Approfondire (Studio Teorico)
1. Leggi `TEORIA_FISICA_COMPLETA.md` § 1-5 (concetti base)
2. Leggi `TEORIA_FISICA_COMPLETA.md` § 6-9 (fisica dettagliata)
3. Leggi `TEORIA_FISICA_COMPLETA.md` § 10-13 (implicazioni avanzate)

### Per Sviluppare (Modifica Codice)
1. Studia `TEORIA_FISICA_COMPLETA.md` § 6 (equazioni di Einstein-Cartan)
2. Studia `TEORIA_FISICA_COMPLETA.md` § 11 (parametri fisici)
3. Leggi i commenti in `WQT_manifold.py` (implementazione)
4. Confronta con `RISULTATI_VALIDAZIONE_BOUNCE.md` (configurazione validata)

---

## 📊 Tabella Rapida dei Parametri

| Parametro | Valore | Definito in | Documentato in |
|-----------|--------|-------------|----------------|
| **χ** | variabile | `equazione_stato_einstein_cartan()` | TEORIA § 2 |
| **24 segmenti** | costante | `segmenti_frattali = 24` | TEORIA § 3 |
| **DX/SX** | simmetria | `chiralita = ±1` | TEORIA § 4 |
| **r_m** | calcolato | `r_conforme = ...` | TEORIA § 5 |
| **β (beta)** | 1.0 | `BETA_REPULSIONE_SPIN` | TEORIA § 6, § 9 |
| **ω (omega)** | 1.0 | `OMEGA_RICHIAMO` | TEORIA § 6 |
| **w** | -1/3 | `w_equazione_stato` | TEORIA § 6 |
| **4π** | 12.566... | vincolo topologico | TEORIA § 8 |

---

## 🔍 Ricerca Rapida

**Cerchi informazioni su...**

- **"Perché 24 segmenti?"** → TEORIA § 3
- **"Cos'è il bounce quantistico?"** → TEORIA § 9, VALIDAZIONE § 1-2
- **"Come funziona la repulsione spin?"** → TEORIA § 6.2, VALIDAZIONE § 3.1
- **"Cosa significa χ?"** → TEORIA § 2
- **"Perché oscilla?"** → VALIDAZIONE § 3 (Meccanismo fisico)
- **"Come calibrare ω?"** → VALIDAZIONE § 8 (Parametri ottimali)
- **"Cosa è DX/SX?"** → TEORIA § 4
- **"Perché 720°?"** → TEORIA § 8
- **"Parametri usati?"** → TEORIA § 11, VALIDAZIONE § 8

---

## 📝 Note

- Tutti i documenti sono in formato Markdown (.md)
- Usa un lettore Markdown per la migliore visualizzazione
- Le equazioni sono scritte in formato ASCII/Unicode
- I grafici sono referenziati ma non inclusi (generati da simulazione)

---

**Ultima modifica**: 22 Maggio 2026  
**Versione documentazione**: 2.0
