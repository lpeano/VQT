# 🛡️ Protezioni e Resilienza del Sistema WQT

## ✅ Funzionalità Implementate

### 1. **Auto-Riparazione File Corrotti**
- **Modalità**: Headless + Playback
- **Funzione**: `clear_hdf5_consistency_flags()`
- **Comportamento**:
  - Rileva automaticamente file HDF5 con flag di consistenza bloccati
  - Tenta riparazione con `h5clear` (se disponibile su sistema)
  - Se h5clear manca (Windows): rinomina file in `.corrupted_backup`
  - Richiede rigenerazione dati con `--headless`

**Esempio errore riparato automaticamente:**
```
[AUTO-REPAIR] File corrotto rilevato. Tentativo di riparazione...
[RECOVERY] h5clear non disponibile. Salvataggio backup e ricreazione...
[RECOVERY] Backup salvato in: geometrodinamica_matrix.h5.corrupted_backup
```

---

### 2. **Resume Resiliente da Ultimo Frame Valido**
- **Modalità**: Solo Headless
- **Funzione**: `find_last_written_frame()`
- **Comportamento**:
  - All'avvio headless, cerca l'ultimo frame con `rm > 0` (dati validi)
  - Arretra automaticamente all'inizio del blocco chunk (2048 frame)
  - Ripristina lo stato quantistico completo (chi, velocità, parametro affine)
  - Sovrascrive il blocco corrotto con dati freschi

**Esempio resume:**
```
[RESUME RESILIENTE] Rilevato blocco interrotto. Arretramento al blocco sicuro: 47104
[STATO RIPRISTINATO 24 CAMPI] Chi medio: -0.7234 | V_Chi medio: 0.0012
[PARAMETRO AFFINE] λ = 4710.4 | Tempo Emergente = 2.341e+03
```

**Vantaggi:**
- Recupera automaticamente da crash/interruzioni
- Non perde progressi (max 2048 frame persi)
- Ripristina coerenza fisica completa

---

### 3. **Protezione Contro Corruzione Durante Scrittura**
- **Modalità**: Headless
- **Funzione**: `flush_chunk_buffer()` + SWMR mode
- **Comportamento**:
  - Scrittura a blocchi (chunk buffer) per ridurre I/O
  - Attivazione modalità SWMR (Single Writer Multiple Readers)
  - Flush emergenza all'interruzione (CTRL+C, exception)

**Limitazione Windows:**
⚠️ SWMR **DISABILITATO** su Windows per compatibilità!
- `HDF5_USE_FILE_LOCKING = "FALSE"` (riga 70)
- Necessario per evitare deadlock su filesystem Windows
- Conseguenza: **NO playback concorrente sicuro**

---

### 4. **Playback Concorrente (Solo Linux/Mac)**
- **Modalità**: Playback durante Headless
- **Funzione**: SWMR reader mode
- **Comportamento**:
  - Su Linux/Mac: playback può leggere mentre headless scrive
  - File aperto con `swmr=True` in lettura
  - Headless attiva `swmr_mode = True` dopo metadati iniziali

**Su Windows:**
❌ **NON SUPPORTATO** - File locking disabilitato
- Headless mostra avviso all'avvio:
  ```
  [AVVISO] SWMR disabilitato su Windows. NON eseguire playback concorrente durante headless.
  [CONFERMA] Premi INVIO per continuare...
  ```
- Playback rileva file bloccato e mostra errore chiaro

---

## 🔧 Come Usare le Funzionalità

### Scenario 1: File Corrotto Dopo Crash
**Problema**: `OSError: cannot open file ... consistency flags`

**Soluzione Automatica:**
```powershell
# Il playback tenta auto-riparazione
python WQT_manifold.py --playback

# Se fallisce, usa headless (controlla SEMPRE all'avvio)
python WQT_manifold.py --headless --duration 5 --fps 10
```

---

### Scenario 2: Ripresa Dopo Interruzione
**Problema**: Headless interrotto a metà (crash, CTRL+C)

**Soluzione Automatica:**
```powershell
# Basta rilanciare headless - rileva automaticamente l'ultimo frame
python WQT_manifold.py --headless --duration 2000 --fps 24

# Output atteso:
# [RESUME RESILIENTE] Rilevato blocco interrotto. Arretramento al blocco sicuro: XXXX
# [STATO RIPRISTINATO] ...
```

---

### Scenario 3: Playback Durante Generazione Dati

**Linux/Mac (SUPPORTATO):**
```bash
# Terminal 1: Genera dati
python WQT_manifold.py --headless --duration 2000 --fps 24

# Terminal 2: Visualizza in tempo reale
python WQT_manifold.py --playback
```

**Windows (NON SUPPORTATO):**
```powershell
# Genera prima, visualizza dopo
python WQT_manifold.py --headless --duration 2000 --fps 24
# Attendi completamento...
python WQT_manifold.py --playback

# OPPURE: Genera video direttamente
python WQT_manifold.py --playback --film --fps 24
```

---

## 📊 Riepilogo Compatibilità

| Funzionalità | Windows | Linux/Mac | Automatica |
|--------------|---------|-----------|------------|
| Auto-riparazione | ✅ | ✅ | ✅ |
| Resume resiliente | ✅ | ✅ | ✅ |
| Protezione corruzione | ✅ | ✅ | ✅ |
| Playback concorrente | ❌ | ✅ | ❌ |

---

## 🐛 Troubleshooting

### "File is already open for write"
**Causa**: Processo headless ancora attivo  
**Soluzione**:
```powershell
# Ferma tutti i processi Python
Stop-Process -Name python -Force

# Riprova playback
python WQT_manifold.py --playback
```

---

### "File locked by another process"
**Causa**: Tentativo playback concorrente su Windows  
**Soluzione**: Attendi fine headless, oppure genera video:
```powershell
python WQT_manifold.py --playback --film --fps 24 --output simulazione.mp4
```

---

### File corrotto non riparabile
**Causa**: Backup fallito o h5clear mancante  
**Soluzione**: Rinomina manualmente e rigenera
```powershell
Rename-Item geometrodinamica_matrix.h5 geometrodinamica_matrix.h5.backup
python WQT_manifold.py --headless --duration 5 --fps 10
```

---

## 🔍 Debug Avanzato

### Controlla ultimo frame valido manualmente:
```python
import h5py
import numpy as np

with h5py.File('geometrodinamica_matrix.h5', 'r') as f:
    data = f['telemetria_scalare'][:]
    valid_mask = data['rm'] > 0
    ultimo_valido = np.where(valid_mask)[0][-1] if valid_mask.any() else -1
    print(f"Ultimo frame valido: {ultimo_valido}")
```

### Forza pulizia flag corrotti:
```powershell
# Linux/Mac
h5clear -s geometrodinamica_matrix.h5

# Windows (nessun h5clear disponibile)
# Usa lo script Python integrato:
python -c "from WQT_manifold import clear_hdf5_consistency_flags; clear_hdf5_consistency_flags('geometrodinamica_matrix.h5')"
```

---

**Versione**: 2026-05-24  
**Ultima modifica**: Auto-riparazione attiva anche in playback
