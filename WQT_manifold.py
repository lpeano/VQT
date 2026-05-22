"""
================================================================================
WQT MANIFOLD - Simulazione di Geometrodinamica Quantistica con Torsione
================================================================================

TEORIA FISICA:
--------------
Questo codice simula un manifold frattale a torsione che modella la struttura
granulare dello spazio-tempo basata sulla teoria di Einstein-Cartan.

CONCETTI FONDAMENTALI:

1. GERARCHIA DI SOLITONI TOPOLOGICI
   Il sistema non rappresenta una singola particella, ma una gerarchia di
   solitoni topologici che compongono la realtà dalle scale di Planck (10^-35 m)
   fino alle scale cosmologiche (10^26 m).

2. SPAZIO-TEMPO CON TORSIONE (Einstein-Cartan)
   A differenza della Relatività Generale classica (geometria di Riemann),
   qui lo spazio-tempo ha TORSIONE oltre alla curvatura. La torsione è
   associata alla densità di spin della materia.

3. DUALITÀ MATERIA-SPAZIO (Chiralità DX/SX)
   - SX (Sinistra, Materia): Si condensa (f_sx = e^-χ), crea densità
   - DX (Destra, Spazio): Si espande (f_dx = e^χ), crea la metrica
   La gravità emerge come forza residua dalla loro interazione.

4. SIMMETRIA DEL RETICOLO DI LEECH (24 Segmenti)
   I 24 segmenti frattali corrispondono alla simmetria del cubottaedro,
   che è la base per l'impacchettamento ottimale di sfere in dimensioni
   superiori. Questo è il vincolo geometrico minimo per chiudere una
   varietà a 720° (proprietà topologica degli spinori).

5. VINCOLO TOPOLOGICO SPINORIALE (4π = 720°)
   Un solitone fermionico stabile deve soddisfare ∮ τ ds = 4π.
   Questo è il requisito di stabilità topologica: un solitone che non
   chiude a 4π decade. La gravità è la forza che mantiene questo vincolo.

EQUAZIONI RISOLTE:
------------------
Le equazioni di campo di Einstein-Cartan in forma semplificata 1D+t:

  R_μν - (1/2)g_μν R + K²_μν = 8πG T_μν

dove:
  - R_μν è il tensore di Ricci (curvatura)
  - K_μν è il tensore di contorsione (torsione)
  - T_μν è il tensore energia-impulso
  - G è la costante gravitazionale (emergente)

PARAMETRI CHIAVE:
-----------------
  - χ (chi): Potenziale di scala (livello di annidamento frattale)
  - rm: Raggio conforme di risonanza del solitone
  - H: Parametro di Hubble locale emergente
  - K: Tensore di contorsione (torsione geometrica)

RIFERIMENTI:
------------
  - Einstein-Cartan Theory (1929)
  - Wheeler's Geometrodynamics
  - Soliton Topology (Skyrme, 1961)
  - Leech Lattice (E8 × E8)

================================================================================
"""

import os
# Disabilitazione dei lock DEVE avvenire prima di importare h5py
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

import numpy as np
import sys
import argparse
from datetime import datetime
import time
import h5py

# --- INTERCETTAZIONE HEADLESS PRECOCE ---
if '--headless' in sys.argv:
    import matplotlib
    matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button  
from scipy.integrate import solve_ivp
from scipy.fft import rfft, rfftfreq

# --- ARGOMENTI LINEA DI COMANDO ---
parser = argparse.ArgumentParser(description='Simulazione geometrodinamica WQT con dataset HDF5 bidimensionali estensibili')
parser.add_argument('--film', action='store_true', help='Salva i frame e compila il filmato MP4')
parser.add_argument('--playback', action='store_true', help='Esegue il rendering leggendo dal file HDF5')
parser.add_argument('--headless', action='store_true', help='Esegue solo il calcolo numerico e scrittura HDF5 ottimizzata')
parser.add_argument('--output', type=str, default=None, help='Nome personalizzato del file MP4')
parser.add_argument('--fps', type=int, default=24, help='Frame per secondo del filmato (default: 24)')
parser.add_argument('--duration', type=int, default=15, help='Durata del filmato in secondi (default: 15)')
parser.add_argument('--db', type=str, default='geometrodinamica_matrix.h5', help='Percorso del file dati HDF5')
parser.add_argument('--speed', type=int, default=1, help='Velocità di avvio del playback (es. 1, 5, 10, 100, 1000)')
args = parser.parse_args()

# --- CALCOLO QUOTA TOTALE FRAME PRE-ALLOCAZIONE ---
NUM_TOTAL_FRAMES = args.fps * args.duration

# --- FLAG MODALITÀ ARCHITETTURA ---
# True: 24 campi locali accoppiati (Leech lattice)
# False: campo globale scalare (compatibilità)
USA_24_CAMPI_LOCALI = True

if sys.platform.startswith('win'):
    import winsound
    def riproduci_suono(frequenza): winsound.Beep(frequenza, 300)  
else:
    def riproduci_suono(frequenza): print('\a'); os.system('echo -e "\a"')

# --- STRUTTURA DATI METADATI FISICI SCALARI ---
SCALARI_DTYPE = np.dtype([
    ('frame_id', 'i8'),
    ('rm', 'f8'),
    ('g_geo', 'f8'),
    ('z_geo', 'f8'),
    ('esponente', 'f8'),
    ('tempo_assol', 'f8'),
    ('d_tau', 'f8'),
    ('v_chi', 'f8'),
    ('chi_lineare', 'f8'),
    ('h_fisica', 'f8'),  # Parametro di Hubble con segno (espansione/contrazione)
    ('contorsione_k', 'f8'),  # Norma del tensore di contorsione K_λμν
    ('chiusura_spinore', 'f8')  # Errore di chiusura topologica (0 = perfetta)
])

# --- STRUTTURA DATI PER 24 CAMPI LOCALI ---
SCALARI_24_DTYPE = np.dtype([
    ('frame_id', 'i8'),
    ('rm', 'f8'),
    ('g_geo', 'f8'),
    ('z_geo', 'f8'),
    ('esponente', 'f8'),
    ('tempo_assol', 'f8'),
    ('d_tau', 'f8'),
    ('v_chi_medio', 'f8'),
    ('chi_medio', 'f8'),
    ('h_fisica', 'f8'),
    ('contorsione_k_medio', 'f8'),
    ('chiusura_spinore_medio', 'f8'),
    # Campi vettoriali (24 elementi)
    ('chi_vettore', 'f8', (24,)),
    ('vel_vettore', 'f8', (24,)),
    ('contorsione_locale', 'f8', (24,)),
    ('chiusura_locale', 'f8', (24,))
])

# --- PULIZIA FLAG CONSISTENZA HDF5 ---
def clear_hdf5_consistency_flags(file_path):
    """Pulisce i flag di consistenza di un file HDF5 corrotto/bloccato."""
    try:
        import subprocess
        result = subprocess.run(['h5clear', '-s', file_path], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"[RECOVERY] Flag di consistenza puliti con h5clear.")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Se h5clear non è disponibile, rinomina e ricrea
    print(f"[RECOVERY] h5clear non disponibile. Salvataggio backup e ricreazione...")
    backup_path = file_path + '.corrupted_backup'
    
    # Retry con delay per file bloccati
    for attempt in range(3):
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(file_path, backup_path)
            print(f"[RECOVERY] Backup salvato in: {backup_path}")
            return False
        except PermissionError:
            if attempt < 2:
                print(f"[RECOVERY] File ancora bloccato. Attesa {attempt + 1}/3...")
                time.sleep(2)
            else:
                print(f"[RECOVERY] Impossibile rinominare il file. Chiudi tutti i processi che usano {file_path}")
                print(f"[RECOVERY] Puoi anche eseguire manualmente: Remove-Item '{file_path}' -Force")
                raise
    return False

# --- INIZIALIZZAZIONE STRUTTURA PRE-ALLOCATA FISSA ---
def inizializza_hdf5_matrix(file_path, num_frames, check_corruption=False):
    """Pre-alloca l'intero file HDF5 con dimensioni fisse per eliminare il padding su Windows."""
    # Scelta dtype in base alla modalità
    dtype_telemetria = SCALARI_24_DTYPE if USA_24_CAMPI_LOCALI else SCALARI_DTYPE
    
    if not os.path.exists(file_path):
        with h5py.File(file_path, 'w', libver='latest') as f:
            f.attrs['creato_il'] = datetime.now().isoformat()
            f.attrs['risoluzione_reticolo'] = 2400
            f.attrs['num_total_frames'] = num_frames
            f.attrs['usa_24_campi_locali'] = USA_24_CAMPI_LOCALI
            
            # Eliminazione dataset vettoriali 3D dal DB per una compressione procedurale (~1600x)
            # Salviamo solo lo "scheletro" matematico per rigenerare la geometria al volo
            f.create_dataset('telemetria_scalare', shape=(num_frames,), maxshape=(None,),
                             dtype=dtype_telemetria, chunks=(2048,))
    else:
        # Controllo corruzione SOLO se richiesto esplicitamente (modalità headless)
        # NON bloccare l'accesso SWMR durante playback concorrente!
        if check_corruption:
            try:
                test_handle = h5py.File(file_path, 'r', libver='latest')
                test_handle.close()
            except OSError as e:
                if "already open" in str(e) or "consistency" in str(e):
                    print(f"[RECOVERY] File HDF5 con flag di consistenza bloccati rilevato.")
                    cleared = clear_hdf5_consistency_flags(file_path)
                    if not cleared:
                        # Il file è stato rinominato, ricrea da zero
                        return inizializza_hdf5_matrix(file_path, num_frames, check_corruption=False)
        
        # Estensione file esistente se richiesti più frame
        needs_recreate = False
        old_data = None
        old_attrs = None
        current_frames = 0
        
        try:
            with h5py.File(file_path, 'r', libver='latest', swmr=True) as f:
                current_frames = f['telemetria_scalare'].shape[0]
                if num_frames > current_frames:
                    print(f"[ESTENSIONE] File esistente con {current_frames} frame. Richiesti {num_frames} frame...")
                    # Controlla se il dataset supporta resize
                    if f['telemetria_scalare'].maxshape[0] is None:
                        # Supporta resize, lo faremo in modalità append
                        needs_recreate = False
                    else:
                        # Non supporta resize, dobbiamo ricreare
                        print(f"[ESTENSIONE] Dataset non estendibile. Creazione nuovo file con copia dati...")
                        needs_recreate = True
                        old_data = f['telemetria_scalare'][:]
                        old_attrs = dict(f.attrs)
        except OSError:
            # File potrebbe essere aperto in scrittura da headless - modalità SWMR, nessun problema
            # Il file verrà esteso quando headless termina
            pass
        
        if needs_recreate and old_data is not None:
            # Ricrea il file completamente
            temp_path = file_path + '.temp'
            with h5py.File(temp_path, 'w', libver='latest') as f_new:
                for k, v in old_attrs.items():
                    f_new.attrs[k] = v
                f_new.attrs['num_total_frames'] = num_frames
                
                f_new.create_dataset('telemetria_scalare', shape=(num_frames,), maxshape=(None,),
                                   dtype=SCALARI_DTYPE, chunks=(2048,))
                f_new['telemetria_scalare'][:len(old_data)] = old_data
                
            os.replace(temp_path, file_path)
            print(f"[ESTENSIONE] ✓ File ricreato con {num_frames} frame ({len(old_data)} frame preservati).")
        elif num_frames > current_frames and not needs_recreate and current_frames > 0:
            # Estendi semplicemente
            with h5py.File(file_path, 'a', libver='latest') as f:
                f['telemetria_scalare'].resize((num_frames,))
                f.attrs['num_total_frames'] = num_frames
                print(f"[ESTENSIONE] ✓ Capacità aumentata da {current_frames} a {num_frames} frame.")
    return file_path

# --- BUFFER IN MEMORIA PER SCRITTURA A BLOCCHI HDF5 ---
chunk_buffer = {
    'scalari': [], 'frames': []
}

def flush_chunk_buffer(f_handle):
    global chunk_buffer
    if len(chunk_buffer['frames']) == 0:
        return
        
    start_f = chunk_buffer['frames'][0]
    end_f = start_f + len(chunk_buffer['frames'])
    
    # Scelta dtype in base alla modalità
    dtype_telemetria = SCALARI_24_DTYPE if USA_24_CAMPI_LOCALI else SCALARI_DTYPE
    f_handle['telemetria_scalare'][start_f:end_f] = np.array(chunk_buffer['scalari'], dtype=dtype_telemetria)
    
    for k in chunk_buffer:
        chunk_buffer[k].clear()

def append_stato_hdf5(f_handle, frame, Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, th, pdx, psx, rm, g_geo, z_geo, esp, t_assol, dtau, vchi, chi_lineare, h_fis, contorsione_k=0.0, chiusura_spinore=0.0, chi_vettore=None, vel_vettore=None, contorsione_locale=None, chiusura_locale=None):
    """Scrittura ottimizzata a blocchi in memoria per impedire la frammentazione SWMR."""
    global chunk_buffer
    
    if USA_24_CAMPI_LOCALI:
        # Modalità 24 campi: scrivi record esteso
        # Prepara array vuoti se non forniti
        chi_vec = chi_vettore if chi_vettore is not None else np.zeros(24)
        vel_vec = vel_vettore if vel_vettore is not None else np.zeros(24)
        cont_loc = contorsione_locale if contorsione_locale is not None else np.zeros(24)
        chiu_loc = chiusura_locale if chiusura_locale is not None else np.zeros(24)
        
        record_scalari = np.array(
            (frame, rm, g_geo, z_geo, esp, t_assol, dtau, vchi, chi_lineare, h_fis, 
             contorsione_k, chiusura_spinore,
             chi_vec, vel_vec, cont_loc, chiu_loc),
            dtype=SCALARI_24_DTYPE
        )
    else:
        # Modalità scalare: usa formato originale
        record_scalari = np.array(
            (frame, rm, g_geo, z_geo, esp, t_assol, dtau, vchi, chi_lineare, h_fis, contorsione_k, chiusura_spinore), 
            dtype=SCALARI_DTYPE
        )
    
    chunk_buffer['scalari'].append(record_scalari)
    chunk_buffer['frames'].append(frame)
    
    if len(chunk_buffer['frames']) == 2048:
        flush_chunk_buffer(f_handle)

def find_last_written_frame(file_path, handle=None):
    """Trova l'ultimo frame valido scritto analizzando il dataset scalare (rm > 0)."""
    if not os.path.exists(file_path):
        return -1
    
    try:
        if handle is not None:
            if 'telemetria_scalare' not in handle:
                return -1
            handle['telemetria_scalare'].refresh()
            scalari = handle['telemetria_scalare'][:]
            valid_indices = np.where(scalari['rm'] > 0)[0]
            if len(valid_indices) == 0:
                return -1
            return int(valid_indices[-1])
            
        try:
            f = h5py.File(file_path, 'r', libver='latest', swmr=True)
        except OSError:
            f = h5py.File(file_path, 'r')
            
        with f:
            if 'telemetria_scalare' not in f:
                return -1
            
            scalari = f['telemetria_scalare'][:]
            # Trova l'ultimo indice dove rm > 0 (dati validi)
            valid_indices = np.where(scalari['rm'] > 0)[0]
            
            if len(valid_indices) == 0:
                return -1
            
            return int(valid_indices[-1])
    except Exception as e:
        print(f"[AVVISO] Errore durante la lettura del file HDF5: {e}")
        return -1

# Inizializza il file HDF5 SOLO se NON siamo in modalità playback
# In modalità playback, accediamo al file in sola lettura, non lo modifichiamo
if args.playback:
    # In playback: verifica solo che il file esista
    file_data_path = args.db
    if not os.path.exists(file_data_path):
        print(f"[ERRORE] File HDF5 non trovato: {file_data_path}")
        sys.exit(1)
    print(f"[PLAYBACK] Lettura da: {file_data_path}")
else:
    # In modalità normale/headless: inizializza e controlla corruzione
    file_data_path = inizializza_hdf5_matrix(args.db, NUM_TOTAL_FRAMES, check_corruption=args.headless)

# ============================================================================
# SEZIONE 1: CONFIGURAZIONE GEOMETRICA DEL MANIFOLD
# ============================================================================
#
# TEORIA: Il manifold è costruito attorno a un solitone toroidale frattale
# con simmetria basata sul reticolo di Leech (24 segmenti).
#
# PARAMETRI GEOMETRICI FONDAMENTALI:
# ----------------------------------

N_u = 6  # Numero di sezioni trasversali del toro (parametrizzazione angolare)
u = np.linspace(0, 2 * np.pi, N_u)  # Coordinate angolari trasversali

risoluzione_base = 2400  # Numero di punti lungo il percorso principale
                         # Alta risoluzione necessaria per catturare oscillazioni
                         # a tutte le scale (da Planck a cosmologiche)

# SIMMETRIA DEL RETICOLO DI LEECH - 24 SEGMENTI FRATTALI
# -------------------------------------------------------
# Il numero 24 non è arbitrario, ma deriva dalla geometria del cubottaedro
# e del reticolo di Leech, che rappresenta l'impacchettamento ottimale di
# sfere in dimensioni superiori (E8 × E8 in teoria delle stringhe).
# Questo è il numero minimo di segmenti per chiudere topologicamente
# un solitone fermionico a 720° (4π radianti).

segmenti_frattali = 24

# COSTANTI FISICHE EMERGENTI DALLA GEOMETRIA
# -------------------------------------------
# Questi parametri non sono arbitrari, ma emergono dalla struttura del manifold:

ACCORCIAMENTO_ANGOLARE = 1.0 / (4.0 * np.pi)
# Fattore di compattificazione angolare. Determina quanto il manifold
# si "avvolge" su se stesso. Il fattore 4π è legato al vincolo spinoriale.

DIMENSIONALITÀ_RADIAZIONE = 4.0 / 3.0
# Indice adiabatico per radiazione ultrarelativistica (p = ρ/3).
# Governa la relazione tra pressione e densità nel regime radiativo.

COEFFICIENTE_ACCOPPIAMENTO = float(segmenti_frattali) / float(risoluzione_base)
# Parametro di accoppiamento tra le scale discrete (24 segmenti) e
# la parametrizzazione continua (2400 punti). Definisce la "granularità"
# della struttura frattale: κ ≈ 0.01

LUNGHEZZA_PLANCK_METRI = 1.616255e-35  # [m]
# Scala fondamentale di Planck. Tutte le distanze sono normalizzate
# rispetto a questa unità quantistica minima dello spazio-tempo.

BETA_REPULSIONE_SPIN = 1.0  # Coefficiente di accoppiamento ρ² (Einstein-Cartan)
# ============================================================================
# FISICA DELLA PRESSIONE DI DEGENERAZIONE SPIN (Einstein-Cartan Theory)
# ============================================================================
# In teoria Einstein-Cartan, la pressione di repulsione spin-spin è data da:
#
#   P_rep = β * ρ²
#
# Dove:
#   - ρ = densità di energia totale (materia + torsione)
#   - β = costante di accoppiamento (unità naturali: β ≈ 1)
#
# COMPORTAMENTO FISICO:
#   - A bassa densità (ρ → 0):     P_rep ≈ 0 (gravità domina)
#   - A densità crescente:          P_rep ∝ ρ² vs P_grav ∝ ρ
#   - A densità di Planck (ρ → ∞): P_rep >> P_grav (BOUNCE!)
#
# Questo è il meccanismo di "degenerazione quantistica dello spin":
# - La pressione cresce quadraticamente con la densità
# - Quando ρ diverge, P_rep diverge più velocemente di P_grav
# - Il sistema non può collassare sotto la scala di Planck
# - Risultato: "bounce quantistico" invece di singolarità
# ============================================================================

OMEGA_RICHIAMO = 1.0  # Coefficiente potenziale armonico di richiamo (AUMENTATO)
# ============================================================================
# POTENZIALE ARMONICO DI RICHIAMO (Equilibrio Dinamico)
# ============================================================================
# Forza che richiama χ verso l'equilibrio (scala classica, χ = 0):
#
#   F_richiamo = -ω * χ
#
# FISICA:
#   - Simula un "potenziale cosmologico" che previene divergenza infinita
#   - Sostituisce il meccanismo di saturazione (tanh) senza bloccare ρ
#   - Permette al sistema di oscillare invece di fuggire all'infinito
#
# COMPORTAMENTO:
#   - χ > 0 (espansione): forza attrattiva → riporta verso equilibrio
#   - χ < 0 (collasso):   forza repulsiva → riporta verso equilibrio
#   - Risultato: oscillazioni stabili attorno a χ ≈ 0
#
# CALIBRAZIONE:
#   ω = 0.01 → troppo debole (collasso continua anche con bounce)
#   ω = 1.0  → bilanciato (forza comparabile alla pressione totale)
#
# Con ω = 1.0, quando χ = -500k, F_richiamo = +500k (forza repulsiva forte).
# Questo deve bilanciarsi con P_totale per permettere oscillazioni stabili.
# ============================================================================

# ============================================================================
# SEZIONE 24 CAMPI LOCALI - TRANSIZIONE DA GLOBALE A GRANULARE
# ============================================================================
#
# Il sistema evolve da un modello a campo unico (χ scalare) a un modello
# con 24 campi locali accoppiati (χ_vettore), uno per ogni segmento del
# reticolo di Leech.
#
# FISICA:
# -------
# - Ogni segmento i ha il proprio χᵢ e densità (ρ_SX[i], ρ_DX[i])
# - I segmenti interagiscono tramite accoppiamento topologico
# - La torsione si propaga tra vicini (diffusione geometrica)
# - Emergono clustering spontanei e bounce locali asincroni
#
# VANTAGGI:
# ---------
# - Anisotropia locale → formazione di strutture
# - Bounce quantistico per segmento (non globale)
# - Clustering di materia dove K² è alta
# - Propagazione di perturbazioni (onde)
# ============================================================================

def costruisci_matrice_accoppiamento_leech():
    """
    Costruisce la matrice di accoppiamento topologico per i 24 segmenti del reticolo di Leech.
    
    TOPOLOGIA:
    ----------
    I 24 segmenti sono disposti su un cerchio (topologia toroidale).
    Ogni segmento interagisce con i vicini con forza decrescente con la distanza:
    
        w_ij ∝ 1 / (dist_ij² + ε)
    
    dove dist_ij è la distanza minima sul cerchio (considerando periodicità).
    
    ACCOPPIAMENTO:
    --------------
    - Vicini immediati (dist=1): peso massimo ~0.5
    - Vicini secondi (dist=2): peso ~0.12
    - Opposti (dist=12): peso minimo ~0.002
    
    La matrice è normalizzata per righe: Σⱼ w_ij = 1
    
    Restituisce:
    -----------
    W : ndarray, shape (24, 24)
        Matrice di accoppiamento normalizzata.
    """
    N = segmenti_frattali  # 24
    W = np.zeros((N, N))
    
    for i in range(N):
        for j in range(N):
            if i != j:
                # Distanza minima sul cerchio (topologia toroidale)
                diff = abs(i - j)
                dist_circle = min(diff, N - diff)
                
                # Peso inversamente proporzionale al quadrato della distanza
                # +0.1 per evitare divisione per zero e saturare accoppiamento forte
                W[i, j] = 1.0 / (dist_circle**2 + 0.1)
    
    # Normalizzazione per righe: ogni segmento "distribuisce" forza totale = 1
    somma_righe = W.sum(axis=1, keepdims=True)
    W_normalizzata = np.where(somma_righe > 0, W / somma_righe, 0.0)
    
    return W_normalizzata


def calcola_chiralita_locale_24_segmenti(chi_vettore, contorsione_locale):
    """
    Calcola densità DX (spazio) e SX (materia) per ciascuno dei 24 segmenti.
    
    FISICA:
    -------
    Ogni segmento ha densità locale dipendente da:
    1. Il proprio χᵢ (potenziale di scala)
    2. La propria contorsione K²ᵢ (torsione geometrica)
    
    Dove la contorsione è alta → materia si concentra (ρ_SX alta)
    Dove la contorsione è bassa → spazio si dilata (ρ_DX alta)
    
    Parametri:
    ----------
    chi_vettore : ndarray, shape (24,)
        Potenziale di scala per ogni segmento.
    contorsione_locale : ndarray, shape (24,)
        Norma del tensore di contorsione K²ᵢ per segmento.
        
    Restituisce:
    -----------
    densita_dx : ndarray, shape (24,)
        Densità di espansione (spazio) per segmento.
    densita_sx : ndarray, shape (24,)
        Densità di condensazione (materia) per segmento.
    """
    # Saturazione locale (evita divergenze numeriche)
    chi_sat = 150.0 * np.tanh(chi_vettore / 150.0)
    
    # Fattori chirali fondamentali (come nel modello globale)
    f_dx_base = np.exp(+chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    f_sx_base = np.exp(-chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    
    # Modulazione topologica basata sulla contorsione locale
    # La torsione "piega" lo spazio-tempo favorendo la concentrazione di materia
    K_media = np.mean(contorsione_locale) + 1e-12
    modulazione_torsione = 1.0 + 0.5 * np.tanh(contorsione_locale / K_media)
    
    # Densità finali:
    # - SX aumenta dove K² è alta (materia attirata dalla curvatura)
    # - DX diminuisce dove K² è alta (spazio si contrae)
    densita_sx = f_sx_base * modulazione_torsione
    densita_dx = f_dx_base / modulazione_torsione
    
    return densita_dx, densita_sx


# Costruzione matrice di accoppiamento (calcolata una volta all'avvio)
MATRICE_ACCOPPIAMENTO_LEECH = costruisci_matrice_accoppiamento_leech()

# Coefficiente che controlla la forza dell'accoppiamento tra segmenti
# DEBOLE (0.05-0.1) → forte anisotropia, clustering pronunciato
# MEDIO (0.2-0.5) → bilanciamento tra locale e globale
# FORTE (0.8-1.0) → tende verso comportamento omogeneo (come modello originale)
KAPPA_COUPLING_24 = 0.15  # Accoppiamento debole/medio → formazione strutture

# ============================================================================

# STATO INIZIALE DEL SISTEMA
# ---------------------------
# Il sistema parte da uno stato vicino alla scala di Planck,
# leggermente perturbato per iniziare l'evoluzione dinamica.

theta_init = np.linspace(0, 4 * np.pi, risoluzione_base)  # Coordinate angolari [0, 4π]
                                                            # Nota: 4π = 720° (chiusura spinoriale)

# POTENZIALE DI SCALA χ (Chi)
# ----------------------------
# χ è il parametro fondamentale che determina il "livello di annidamento"
# frattale del manifold. Mappa le scale da Planck (10^-35 m) a cosmologiche (10^26 m).
#
# FISICA:
#   χ < 0  → Regime subatomico/Planck (particelle)
#   χ ≈ 0  → Regime classico/umano
#   χ > 0  → Regime cosmologico/galattico
#
# La saturazione tanh(χ/150) previene divergenze numeriche permettendo
# al sistema di evolvere su 60+ ordini di grandezza in modo stabile.

chi_init = -4.50  # Stato iniziale: leggermente sopra la scala di Planck
chi_sat_init = 150.0 * np.tanh(chi_init / 150.0)  # Saturazione per stabilità numerica

# DUALITÀ MATERIA-SPAZIO: CHIRALITÀ DX vs SX
# -------------------------------------------
# Il manifold si separa in due "canali chirali" che evolvono in modo opposto:
#
# DX (Destra, Spazio):
#   f_dx = exp(+χ) → ESPANSIONE
#   Rappresenta la metrica spaziale che si dilata
#   Crea "spazio vuoto" in cui la materia risiede
#
# SX (Sinistra, Materia):
#   f_sx = exp(-χ) → CONDENSAZIONE  
#   Rappresenta la densità di materia/energia che si concentra
#   Crea curvatura locale (massa gravitazionale)
#
# GRAVITÀ = Forza residua dall'annichilazione/creazione di torsione tra DX e SX

f_dx_init = np.exp(chi_sat_init * COEFFICIENTE_ACCOPPIAMENTO)   # Fattore di espansione DX
f_sx_init = np.exp(-chi_sat_init * COEFFICIENTE_ACCOPPIAMENTO)  # Fattore di condensazione SX

# FREQUENZA DI OSCILLAZIONE
# -------------------------
# La frequenza è determinata dai 24 segmenti frattali (freq_base = 12)
# più correzioni dipendenti dalla scala χ.
freq_init = float(segmenti_frattali // 2) + (np.floor(np.abs(chi_sat_init * COEFFICIENTE_ACCOPPIAMENTO)) * 2.0)

# RAGGIO CONFORME DI RISONANZA
# -----------------------------
# rm non è un raggio "fisso", ma la scala spaziale locale del solitone.
# Si dilata/contrae con χ mantenendo la risonanza topologica 4π.
r_m_init = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(chi_sat_init * COEFFICIENTE_ACCOPPIAMENTO)

# DISTORSIONE TOPOLOGICA
# ----------------------
# La differenza tra f_dx e f_sx crea una distorsione nello spazio-tempo
# che separa le coordinate di "spazio" e "materia".
dist_top_init = (f_dx_init - f_sx_init) * (COEFFICIENTE_ACCOPPIAMENTO * 0.1)

theta_spazio_init = theta_init + dist_top_init * np.sin(3.0 * theta_init)    # Coordinate dello spazio (DX)
theta_materia_init = theta_init - dist_top_init * np.sin(3.0 * theta_init)   # Coordinate della materia (SX)

# INVILUPPI DI PERTURBAZIONE (p_dx, p_sx)
# ----------------------------------------
# Rappresentano le ampiezze di oscillazione dei due canali chirali.
# Fisicamente: densità di energia/momento nei rispettivi settori.
p_dx_init = np.sqrt(float(segmenti_frattali)) * 0.3 * np.sin(freq_init * theta_spazio_init) * f_dx_init
p_sx_init = np.sqrt(float(segmenti_frattali)) * 0.3 * np.sin(freq_init * theta_materia_init) * f_sx_init

# TRIEDRO DI FRENET-SERRET (Geometria Differenziale)
# ---------------------------------------------------
# Definisce il sistema di riferimento locale mobile lungo il manifold:
#   T = Tangente (direzione del moto)
#   N = Normale (direzione della curvatura)
#   B = Binormale (T × N, direzione della torsione)
xb_init = r_m_init * np.cos(theta_init); yb_init = r_m_init * np.sin(theta_init); zb_init = np.zeros_like(theta_init)
T_init = np.vstack(np.gradient([xb_init,yb_init,zb_init], axis=1)); T_init /= (np.linalg.norm(T_init, axis=0) + 1e-12)
N_init = np.vstack(np.gradient(T_init, axis=1)); N_init /= (np.linalg.norm(N_init, axis=0) + 1e-12)
B_init = np.cross(T_init.T, N_init.T).T

# COSTRUZIONE DEL MANIFOLD 3D
# ----------------------------
# Il manifold è costruito come un "tubo" attorno alla curva base,
# con sezioni trasversali circolari che ruotano secondo la chiralità.
A_DX_init = u[:, None] + (theta_init/2)[None, :]  # Angolo di rotazione della sezione DX
foc_dx_init = (r_m_init / float(N_u)) * f_dx_init * (1 + 0.3 * np.sin(freq_init*theta_spazio_init))
x_s_init = (r_m_init + (p_dx_init + p_sx_init)*0.5) * np.cos(theta_init)
y_s_init = (r_m_init + (p_dx_init + p_sx_init)*0.5) * np.sin(theta_init)
z_s_init = (r_m_init * ACCORCIAMENTO_ANGOLARE) * np.cos(freq_init * theta_init)
X_dx_init = x_s_init + foc_dx_init * (np.cos(A_DX_init)*N_init[0] + np.sin(A_DX_init)*B_init[0])
Y_dx_init = y_s_init + foc_dx_init * (np.cos(A_DX_init)*N_init[1] + np.sin(A_DX_init)*B_init[1])
Z_dx_init = z_s_init + foc_dx_init * (np.cos(A_DX_init)*N_init[2] + np.sin(A_DX_init)*B_init[2])
LUNGHEZZA_GEOMETRICA_INIZIALE = np.sum(np.sqrt(np.diff(X_dx_init.flatten())**2 + np.diff(Y_dx_init.flatten())**2 + np.diff(Z_dx_init.flatten())**2))

# --- 1.5 GEOMETRIA BASATA SULLA TORSIONE ---
def calcola_contorsione(nodi):
    """
    Calcola il tensore di contorsione basato sulla geometria del manifold con torsione.
    
    Parametri:
    ----------
    nodi : array_like, shape (N, 3)
        Coordinate dei nodi del manifold (X, Y, Z).
        
    Restituisce:
    -----------
    K : ndarray, shape (N-2, 3, 3, 3)
        Tensore di contorsione K_λμν calcolato come:
        K_λμν = S_λμν + S_μλν + S_νλμ
        
    Note:
    -----
    - Il tensore di torsione S_λμν viene calcolato come gradiente della fase
      del sinusoide, dove i 24 nodi definiscono la frequenza di oscillazione.
    - Il calcolo è ottimizzato per evitare operazioni analitiche globali pesanti.
    - La simmetria antisimmetrica nella torsione S_λμν = -S_μλν è preservata.
    """
    nodi = np.asarray(nodi)
    if nodi.ndim != 2 or nodi.shape[1] != 3:
        raise ValueError("nodi deve essere un array di forma (N, 3)")
    
    N = len(nodi)
    if N < 3:
        raise ValueError("Servono almeno 3 nodi per calcolare la contorsione")
    
    # Frequenza di oscillazione basata sui 24 segmenti frattali
    frequenza_base = segmenti_frattali / 2.0
    
    # Calcolo delle coordinate parametriche lungo il manifold
    # Usiamo la lunghezza d'arco cumulativa come parametro
    differenze = np.diff(nodi, axis=0)
    lunghezze = np.sqrt(np.sum(differenze**2, axis=1))
    lunghezze_cumulative = np.concatenate([[0], np.cumsum(lunghezze)])
    
    # Normalizzazione del parametro [0, 2π] per definire la fase
    param_normalizzato = lunghezze_cumulative / (lunghezze_cumulative[-1] + 1e-12) * 2 * np.pi
    
    # Calcolo della fase del sinusoide basata sulla frequenza
    fase = frequenza_base * param_normalizzato
    
    # Calcolo del tensore di torsione S_λμν usando differenze finite
    # S_λμν rappresenta il gradiente della fase rispetto alle coordinate spaziali
    
    # Gradiente della fase (derivata rispetto al parametro)
    grad_fase = np.gradient(fase)
    
    # Inizializzazione del tensore di torsione S[i, λ, μ, ν]
    # dove i è l'indice del nodo, λ,μ,ν sono gli indici spaziali (0,1,2) = (x,y,z)
    S = np.zeros((N, 3, 3, 3))
    
    # Calcolo dei gradienti spaziali (derivate seconde miste)
    # Usiamo differenze finite centrate per maggiore accuratezza
    for i in range(1, N-1):
        # Vettori tangenti (approssimazione locale)
        tangente = (nodi[i+1] - nodi[i-1]) / 2.0
        tangente_norm = np.linalg.norm(tangente) + 1e-12
        t_hat = tangente / tangente_norm
        
        # Variazione della fase locale
        delta_fase = (fase[i+1] - fase[i-1]) / 2.0
        
        # Tensore di torsione: S_λμν = ∂_λ(fase) * (t_μ * n_ν - t_ν * n_μ)
        # dove t è il vettore tangente e n è la normale
        
        # Calcolo approssimato della normale (perpendicolare alla tangente)
        # Usiamo il gradiente della tangente come approssimazione
        if i < N-2:
            grad_tangente = (nodi[i+2] - 2*nodi[i+1] + nodi[i]) / (tangente_norm**2 + 1e-12)
            normale = grad_tangente - np.dot(grad_tangente, t_hat) * t_hat
            norm_normale = np.linalg.norm(normale) + 1e-12
            n_hat = normale / norm_normale
        else:
            # Caso limite: usa la normale del punto precedente
            n_hat = np.array([0, 0, 1])  # fallback
        
        # Costruzione del tensore antisimmetrico
        for lam in range(3):
            for mu in range(3):
                for nu in range(3):
                    if mu != nu:
                        # Contributo dalla fase e dalla geometria locale
                        S[i, lam, mu, nu] = grad_fase[i] * (
                            t_hat[lam] * (t_hat[mu] * n_hat[nu] - t_hat[nu] * n_hat[mu]) * 
                            np.sin(fase[i])
                        )
    
    # Calcolo del tensore di contorsione K_λμν = S_λμν + S_μλν + S_νλμ
    # Questa è la parte completamente antisimmetrica del tensore di torsione
    K = np.zeros_like(S)
    
    for i in range(N):
        for lam in range(3):
            for mu in range(3):
                for nu in range(3):
                    K[i, lam, mu, nu] = (
                        S[i, lam, mu, nu] + 
                        S[i, mu, lam, nu] + 
                        S[i, nu, lam, mu]
                    )
    
    # Restituiamo solo i punti interni dove la derivata è ben definita
    return K[1:-1]

def check_chiusura_spinore(nodi):
    """
    Verifica la chiusura topologica spinoriale del solitone attraverso l'integrale di linea.
    
    Calcola l'integrale di linea della torsione lungo il sinusoide che chiude il solitone:
    ∮ torsione ds
    
    e confronta con il vincolo topologico 4π (720°) per la stabilità fermionica.
    
    Parametri:
    ----------
    nodi : array_like, shape (N, 3)
        Coordinate dei nodi del manifold (X, Y, Z).
        
    Restituisce:
    -----------
    scalar_error : float
        Differenza normalizzata tra l'integrale calcolato e 4π.
        Valori vicini a 0 indicano chiusura topologica corretta.
        
    diagnostica : dict
        Dizionario contenente:
        - 'integrale_calcolato': valore dell'integrale ∮ torsione ds
        - 'target_teorico': valore target 4π
        - 'errore_percentuale': errore percentuale rispetto al target
        - 'errore_assoluto': |integrale - 4π|
        - 'errore_planck': errore in unità di lunghezza di Planck
        - 'torsione_media': valore medio della torsione
        - 'lunghezza_totale': lunghezza totale del percorso
        
    Note:
    -----
    In teoria degli spinori, una rotazione di 720° (4π radianti) riporta uno spinore
    al suo stato originale, mentre 360° (2π) lo porta a -ψ. Questo è un requisito
    topologico fondamentale per particelle fermioniche.
    
    L'integrale di linea della torsione lungo una curva chiusa che racchiude un solitone
    fermionico deve essere esattamente 4π per garantire la stabilità topologica.
    
    La normalizzazione in unità di Planck permette di confrontare errori a scale
    diverse (da Planck a cosmologiche).
    """
    nodi = np.asarray(nodi)
    if nodi.ndim != 2 or nodi.shape[1] != 3:
        raise ValueError("nodi deve essere un array di forma (N, 3)")
    
    N = len(nodi)
    if N < 3:
        raise ValueError("Servono almeno 3 nodi per il calcolo della chiusura spinoriale")
    
    # Calcolo delle lunghezze differenziali ds lungo la curva
    differenze = np.diff(nodi, axis=0)
    ds = np.sqrt(np.sum(differenze**2, axis=1))
    
    # Lunghezza totale del percorso
    lunghezza_totale = np.sum(ds)
    
    # Calcolo della torsione geometrica punto per punto
    # La torsione τ è legata alla derivata della binormale lungo il percorso
    # τ = -dB/ds · N (formula di Frenet-Serret)
    
    torsione_punti = np.zeros(N)
    
    for i in range(1, N-1):
        # Vettore tangente (derivata prima)
        if i < N-1:
            tangente = (nodi[i+1] - nodi[i-1]) / 2.0
        else:
            tangente = nodi[i] - nodi[i-1]
            
        tangente_norm = np.linalg.norm(tangente) + 1e-15
        T = tangente / tangente_norm
        
        # Derivata seconda (per la normale)
        if i < N-2:
            derivata_seconda = nodi[i+1] - 2*nodi[i] + nodi[i-1]
        else:
            derivata_seconda = np.zeros(3)
            
        # Vettore normale
        N_vec = derivata_seconda - np.dot(derivata_seconda, T) * T
        N_norm = np.linalg.norm(N_vec) + 1e-15
        N_hat = N_vec / N_norm
        
        # Vettore binormale
        B = np.cross(T, N_hat)
        
        # Derivata della binormale (approssimazione con differenze finite)
        if i < N-2 and i > 1:
            # Calcolo B al punto successivo
            tangente_next = (nodi[i+2] - nodi[i]) / 2.0
            T_next = tangente_next / (np.linalg.norm(tangente_next) + 1e-15)
            derivata_seconda_next = nodi[i+2] - 2*nodi[i+1] + nodi[i]
            N_next_vec = derivata_seconda_next - np.dot(derivata_seconda_next, T_next) * T_next
            N_next = N_next_vec / (np.linalg.norm(N_next_vec) + 1e-15)
            B_next = np.cross(T_next, N_next)
            
            # Derivata di B
            dB = (B_next - B) / (ds[i] + 1e-15)
            
            # Torsione: τ = -dB/ds · N
            torsione_punti[i] = -np.dot(dB, N_hat)
        else:
            torsione_punti[i] = 0.0
    
    # Frequenza di oscillazione basata sui 24 segmenti frattali
    frequenza_base = segmenti_frattali / 2.0
    
    # Calcolo della lunghezza d'arco cumulativa per la fase
    lunghezze_cumulative = np.concatenate([[0], np.cumsum(ds)])
    
    # Parametro normalizzato [0, 2π]
    param_normalizzato = lunghezze_cumulative / (lunghezza_totale + 1e-15) * 2 * np.pi
    
    # Fase del sinusoide (modulazione basata sui 24 segmenti)
    fase = frequenza_base * param_normalizzato
    
    # Modulazione della torsione con la fase del sinusoide
    # Questo cattura l'oscillazione del manifold che genera la chiusura topologica
    torsione_modulata = torsione_punti * (1.0 + 0.5 * np.sin(fase))
    
    # Integrale di linea: ∮ torsione ds
    # Uso regola del trapezio per l'integrazione
    integrale = 0.0
    for i in range(len(ds)):
        # Media della torsione tra i punti i e i+1
        torsione_media_locale = (torsione_modulata[i] + torsione_modulata[i+1]) / 2.0
        integrale += torsione_media_locale * ds[i]
    
    # Aggiungi contributo di chiusura (dal primo all'ultimo punto per chiudere il loop)
    if N > 2:
        ds_chiusura = np.linalg.norm(nodi[-1] - nodi[0])
        torsione_chiusura = (torsione_modulata[-1] + torsione_modulata[0]) / 2.0
        integrale += torsione_chiusura * ds_chiusura
    
    # Valore target teorico: 4π per la chiusura spinoriale fermionica
    target_teorico = 4.0 * np.pi
    
    # Errore assoluto
    errore_assoluto = np.abs(integrale - target_teorico)
    
    # Errore percentuale
    errore_percentuale = 100.0 * errore_assoluto / target_teorico
    
    # Normalizzazione in unità di lunghezza di Planck
    # L'errore viene scalato rispetto alla lunghezza del percorso in unità di Planck
    lunghezza_in_planck = lunghezza_totale / LUNGHEZZA_PLANCK_METRI
    errore_planck = errore_assoluto / (lunghezza_in_planck + 1e-15)
    
    # Scalar error normalizzato (questo è il valore di ritorno principale)
    # Normalizzato sia per il target che per la scala di lunghezza
    scalar_error = (integrale - target_teorico) / target_teorico
    
    # Diagnostica completa
    diagnostica = {
        'integrale_calcolato': integrale,
        'target_teorico': target_teorico,
        'errore_percentuale': errore_percentuale,
        'errore_assoluto': errore_assoluto,
        'errore_planck': errore_planck,
        'torsione_media': np.mean(np.abs(torsione_punti[torsione_punti != 0])) if np.any(torsione_punti != 0) else 0.0,
        'lunghezza_totale': lunghezza_totale,
        'numero_punti': N,
        'frequenza_modulazione': frequenza_base
    }
    
    return scalar_error, diagnostica

def estrai_nodi_manifold(X, Y, Z):
    """
    Estrae i nodi del manifold da array di coordinate 3D.
    
    Parametri:
    ----------
    X, Y, Z : array_like
        Coordinate del manifold (possono essere array 1D o 2D).
        
    Restituisce:
    -----------
    nodi : ndarray, shape (N, 3)
        Array di coordinate dei nodi nel formato richiesto da calcola_contorsione.
        
    Esempio:
    --------
    >>> nodi = estrai_nodi_manifold(X_dx_init, Y_dx_init, Z_dx_init)
    >>> K = calcola_contorsione(nodi)
    """
    # Flatten degli array se sono multidimensionali
    X_flat = np.asarray(X).flatten()
    Y_flat = np.asarray(Y).flatten()
    Z_flat = np.asarray(Z).flatten()
    
    # Verifica che abbiano la stessa lunghezza
    if not (len(X_flat) == len(Y_flat) == len(Z_flat)):
        raise ValueError("X, Y, Z devono avere la stessa lunghezza")
    
    # Costruzione array nodi
    nodi = np.column_stack([X_flat, Y_flat, Z_flat])
    
    return nodi

# ============================================================================
# SEZIONE 2: EQUAZIONI DI EINSTEIN-CARTAN CON TORSIONE
# ============================================================================
#
# Questa funzione risolve le equazioni di campo di Einstein-Cartan semplificate
# per un manifold 1D+t con torsione.
#
# EQUAZIONE DI CAMPO:
# -------------------
#   R_μν - (1/2)g_μν R + K²_μν = 8πG T_μν
#
# dove:
#   R_μν = tensore di Ricci (curvatura)
#   K_μν = tensore di contorsione (torsione)
#   T_μν = tensore energia-impulso
#   G = costante gravitazionale (emergente dalla geometria)
#
# FISICA IMPLEMENTATA:
# --------------------
# 1. Curvatura di Ricci modificata dalla contorsione
# 2. Forza di richiamo geometrico (vincolo topologico 4π)
# 3. Pressione metrica che minimizza l'energia topologica
# 4. Auto-organizzazione verso strutture solitoniche stabili
# 5. Damping viscoso per stabilità numerica
#
# PARAMETRI:
# ----------
#   lambda_affine: Parametro affine (non tempo esterno)
#   stato_metrico: [χ, dχ/dλ] - Potenziale di scala e sua derivata
#   scatolamento: Parametro di confinamento (box cosmologico)
#   errore_chiusura: Errore normalizzato rispetto a 4π
#   contorsione_k: Norma del tensore di contorsione
#
# ============================================================================

def equazione_stato_einstein_cartan(lambda_affine, stato_metrico, scatolamento, errore_chiusura=0.0, contorsione_k=0.0):
    """
    Evoluzione geometrodinamica basata su parametro affine λ con fisica della torsione integrata.
    
    TEORIA:
    -------
    La dinamica è guidata dalla minimizzazione dell'energia topologica totale:
    
        E_tot = E_Ricci + E_torsione + E_chiusura + E_auto-org
    
    dove:
    - E_Ricci: Energia di curvatura (Einstein-Hilbert)
    - E_torsione: Energia del campo di torsione (K²)
    - E_chiusura: Energia di vincolo spinoriale (∮τds - 4π)²
    - E_auto-org: Potenziale di stabilizzazione solitonica
    
    Il sistema evolve verso stati che minimizzano questa energia totale,
    risultando in solitoni fermionici topologicamente stabili.
    
    FISICA:
    -------
    1. CURVATURA DI RICCI CON CONTORSIONE
       R_total = R_Riemann + ∇K + K²
       La torsione modifica la curvatura dello spazio-tempo
    
    2. FORZA DI RICHIAMO GEOMETRICO
       F_richiamo = -k * (∮τds - 4π)
       Forza che "tira" il manifold verso la configurazione 720°
    
    3. PRESSIONE METRICA
       P_metrica = -∂E_chiusura/∂V
       Pressione che deforma lo spazio per minimizzare l'errore
    
    4. AUTO-ORGANIZZAZIONE
       Termine attrattivo che stabilizza solitoni compatti
       Previene espansione indefinita → formazione di strutture
    """
    # STATO DEL SISTEMA
    chi = stato_metrico[0]          # Potenziale di scala χ
    velocita_chi = stato_metrico[1]  # dχ/dλ (velocità rispetto al parametro affine)
    
    # SATURAZIONE PER ESPONENZIALI: Mappa χ ∈ (-∞, +∞) → χ_sat ∈ (-150, +150)
    # Permette al sistema di navigare tra Planck e scale cosmologiche senza divergenze
    # numeriche negli esponenziali (exp(χ_sat) rimane in range calcolabile)
    chi_sat = 150.0 * np.tanh(chi / 150.0)
    log_r_dx = chi_sat
    
    # INDICATORE DI DENSITÀ (crescita illimitata con |χ|)
    # Questo cresce monotonicamente con |χ| senza saturare, a differenza di chi_sat
    # FISICA: Quando il manifold collassa (χ → -∞), la densità deve divergere
    # Uso crescita LINEARE invece di esponenziale per evitare overflow numerico:
    #   ρ_indicatore = 1 + |χ|/scala
    # Con scala = 100:
    #   χ = -60656 → indicatore ≈ 607 → ρ ≈ 30 → P_rep = ρ² ≈ 900
    #   P_grav ≈ w×ρ ≈ -10 → Rapporto ≈ 90 → BOUNCE!
    indicatore_densita = 1.0 + np.abs(chi) / 100.0  # Crescita lineare controllata
    
    # DUALITÀ MATERIA-SPAZIO
    # DX (Spazio): f_dx = e^(+χ) → ESPANSIONE
    # SX (Materia): f_sx = e^(-χ) → CONDENSAZIONE
    fattore_dx = np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)  
    fattore_sx = np.exp(-log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
    
    # CALCOLO DELLA TORSIONE LOCALE
    # La torsione emerge dalla chiralità alternata dei 2400 punti del reticolo
    arg_dx = (4 * np.pi / risoluzione_base) * fattore_dx / (1.0 + log_r_dx**2)
    arg_sx = (4 * np.pi / risoluzione_base) * fattore_sx
    
    # Pattern chirale: +1, -1, +1, -1, ... (alternanza left/right)
    chiralita = np.where(np.arange(risoluzione_base) % 2 == 0, 1.0, -1.0)
    
    # Componenti di torsione per DX e SX
    # sinh: funzione iperbolica che cresce esponenzialmente per grandi argomenti
    tor_dx = np.sinh(chiralita * arg_dx)
    tor_sx = np.sinh(chiralita * arg_sx)
    
    # DENSITÀ MEDIE (integrate sul reticolo)
    mu_dx = np.mean(np.abs(tor_dx))  # Densità spazio
    mu_sx = np.mean(np.abs(tor_sx))  # Densità materia
    
    # TENSIONE DI TAGLIO (Interazione DX-SX)
    # Fisicamente: lo "stress" dove materia e spazio si annichilano/creano
    tensione_taglio = np.mean(tor_dx * tor_sx)
    
    # ENERGIA TORSIONALE (Asimmetria DX-SX)
    # Energia immagazzinata nella differenza tra i due canali chirali
    energia_torsionale = np.mean((np.abs(tor_dx) - np.abs(tor_sx))**2)
    
    # RAGGIO CONFORME DI RISONANZA
    # Scala spaziale locale del solitone (si dilata/contrae con χ)
    r_conforme = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
    
    # PROTEZIONE DI PLANCK (Floor numerico)
    # Impedisce al manifold di collassare sotto la scala di Planck
    r_conforme = np.maximum(r_conforme, 1.0 * LUNGHEZZA_PLANCK_METRI)
    
    # ACCOPPIAMENTO TOPOLOGICO (1/r²)
    # Intensità delle interazioni geometriche (più forte a piccole scale)
    accoppiamento_topologico = 1.0 / (r_conforme**2 + 1e-6)
    
    # ========================================================================
    # FISICA DELLA TORSIONE E CHIUSURA SPINORIALE INTEGRATA
    # ========================================================================
    
    # 1. CONTRIBUTO DEL TENSORE DI CONTORSIONE ALLA CURVATURA DI RICCI
    # ------------------------------------------------------------------
    # In teoria di Einstein-Cartan:
    #   R_μν^(EC) = R_μν^(Riemann) + ∇_λ K^λ_μν + K^λ_ρμ K_νλ^ρ
    #
    # Il termine K² contribuisce alla densità di energia effettiva
    correzione_curvatura_contorsione = contorsione_k**2 * accoppiamento_topologico
    
    # 2. FORZA DI RICHIAMO GEOMETRICO (Vincolo Topologico 4π = 720°)
    # ---------------------------------------------------------------
    # TEORIA:
    #   Un solitone fermionico deve soddisfare ∮ τ ds = 4π
    #   Deviazioni da questo valore creano "energia di deformazione topologica"
    #
    # ENERGIA:
    #   E_top = (1/2) k_top * (∮τds - 4π)²
    #
    # FORZA DERIVATA (gradiente negativo dell'energia):
    #   F_richiamo = -k_top * (∮τds - 4π)
    #
    # INTERPRETAZIONE:
    #   - Se ∮τds > 4π → Forza CONTRATTIVA (riporta verso 4π)
    #   - Se ∮τds < 4π → Forza ESPANSIVA (riporta verso 4π)
    #   - Questa è la "gravità topologica" che stabilizza il solitone
    
    TARGET_CHIUSURA_4PI = 4.0 * np.pi
    costante_richiamo_topologico = 50.0  # Intensità della forza di richiamo (IRRIGIDITO)
    
    # errore_chiusura è normalizzato: (integrale - 4π) / 4π
    # Lo riportiamo all'errore assoluto
    errore_assoluto = errore_chiusura * TARGET_CHIUSURA_4PI
    
    # Forza di richiamo geometrico
    forza_richiamo_geometrico = -costante_richiamo_topologico * errore_assoluto * accoppiamento_topologico
    
    # 3. PRESSIONE METRICA (Minimizzazione Energia Topologica)
    # ---------------------------------------------------------
    # La pressione è il gradiente dell'energia rispetto al volume:
    #   P = -∂E/∂V
    #
    # Per una sfera: V ∝ r³, quindi:
    #   P_metrica ∝ -errore² / r³
    #
    # Questo crea una pressione che "schiaccia" o "espande" il manifold
    # per minimizzare l'errore di chiusura
    pressione_metrica_chiusura = -(errore_assoluto**2) / (r_conforme**3 + 1e-9)
    
    # ========================================================================
    # 4. DENSITÀ DI ENERGIA TOTALE (T^00 - Componente temporale)
    # ========================================================================
    # FISICA:
    #   In relatività generale, il tensore stress-energia T^μν ha componenti:
    #     T^00 = ρ (densità di energia)
    #     T^ii = P (pressione spaziale)
    #   
    #   IMPORTANTE: I termini quadratici di torsione sono ENERGIA, non pressione!
    #   Vanno in T^00, non in T^ii.
    # ========================================================================
    
    # DENSITÀ DI MATERIA BASE
    # Differenza tra densità SX (materia) e DX (spazio)
    densita_materia = (mu_sx - mu_dx) * scatolamento
    
    # DENSITÀ DI ENERGIA TORSIONALE
    # Include sia tensione_taglio² che energia_torsionale²
    # QUESTA VA NELLA DENSITÀ, NON NELLA PRESSIONE!
    densita_torsione_quadratica = (tensione_taglio**2 + energia_torsionale**2) * accoppiamento_topologico
    
    # DENSITÀ DI ENERGIA DELLA CONTORSIONE (dal tensore K)
    # Energia gravitazionale associata alla torsione (attrattiva)
    densita_energia_contorsione = correzione_curvatura_contorsione
    
    # DENSITÀ DI ENERGIA TOTALE (Somma di tutte le contribuzioni)
    # Questa è la componente T^00 del tensore stress-energia
    # CORREZIONE FISICA: Moltiplico per indicatore_densita che cresce con |χ|
    # In questo modo, quando χ → -∞ (collasso), ρ → ∞ (densità diverge)
    # senza essere bloccato dalla saturazione di chi_sat
    densita_energia_totale = (
        densita_materia 
        + densita_torsione_quadratica     # Energia torsione
        + densita_energia_contorsione     # Energia contorsione K²
    ) * indicatore_densita
    
    # TENSIONE NEWTONIANA (Accoppiamento lineare torsione-curvatura)
    # Questa è la "gravità" classica emergente
    tensione_newtoniana = tensione_taglio * accoppiamento_topologico
    
    # ========================================================================
    # PRESSIONE DI REPULSIONE SPIN-SPIN (Einstein-Cartan)
    # ========================================================================
    # TEORIA CORRETTA (Einstein-Cartan):
    #   La pressione di degenerazione spin scala come ρ², NON come K²:
    #
    #   P_rep = β * ρ²
    #
    # FISICA:
    #   - ρ = densità di energia totale (materia + torsione)
    #   - Durante il collasso: ρ → ∞
    #   - P_grav ∝ ρ (lineare), ma P_rep ∝ ρ² (quadratico)
    #   - Quando ρ → ∞: P_rep >> P_grav → BOUNCE QUANTISTICO!
    #
    # PERCHÉ ρ² E NON K²?
    #   - ρ diverge durante il collasso (NON satura)
    #   - K² è già incluso in ρ (densita_energia_contorsione)
    #   - Il termine ρ² cattura TUTTA l'energia (materia + torsione)
    #
    # SEGNO: POSITIVO (repulsione)
    # ========================================================================
    
    pressione_repulsione_spin = BETA_REPULSIONE_SPIN * densita_energia_totale**2
    
    # ========================================================================
    # PRESSIONE TOTALE (T^ii - Componenti spaziali)
    # ========================================================================
    # FISICA:
    #   La pressione è legata alla densità di energia tramite EQUAZIONE DI STATO:
    #   
    #   P_materia = w * ρ_totale
    #   
    #   dove w è il parametro dell'equazione di stato:
    #     w = +1/3  → Radiazione (ultra-relativistica)
    #     w = 0     → Materia polverosa (non relativistica)  
    #     w = -1/3  → Materia con torsione (attrattiva)
    #     w = -1    → Energia del vuoto (cosmologica)
    #   
    #   Per il nostro sistema con torsione dominante, usiamo w ≈ -1/3.
    #   Il segno negativo rende questa componente ATTRATTIVA.
    # ========================================================================
    
    # PARAMETRO EQUAZIONE DI STATO
    # w < 0 → pressione attrattiva ("gravità")
    # Questo è il termine che causa il collasso gravitazionale
    w_equazione_stato = -1.0 / 3.0
    
    # PRESSIONE GRAVITAZIONALE (da equazione di stato)
    # Questa è la pressione "classica" che include materia + energia di torsione
    # SEGNO NEGATIVO → ATTRATTIVA
    pressione_gravitazionale = w_equazione_stato * densita_energia_totale - tensione_newtoniana
    
    # PRESSIONE TOTALE
    # Somma di:
    #   1. Pressione gravitazionale (attrattiva, da equazione di stato)
    #   2. Pressione repulsione spin-spin (repulsiva, da Einstein-Cartan)
    #   3. Forza richiamo geometrico (vincolo topologico 4π)
    #   4. Pressione metrica (minimizzazione energia topologica)
    pressione_vuoto_totale = (
        pressione_gravitazionale             # Equazione di stato (ATTRATTIVA)
        + pressione_repulsione_spin          # Repulsione spin-spin (REPULSIVA) ★
        + forza_richiamo_geometrico          # Forza verso chiusura 4π
        + pressione_metrica_chiusura         # Pressione di minimizzazione
    )
    
    # 5. AUTO-ORGANIZZAZIONE VERSO STRUTTURE SOLITONICHE
    # ---------------------------------------------------
    # TEORIA:
    #   Senza questo termine, il sistema potrebbe espandersi indefinitamente.
    #   L'auto-organizzazione introduce un potenziale attrattivo che
    #   favorisce la formazione di solitoni compatti e stabili.
    #
    # POTENZIALE:
    #   V_auto = α * (r - r_opt)² / r³
    #
    # FORZA:
    #   F_auto = -dV/dr ∝ -(r - r_opt)² / r³
    #
    # FISICA:
    #   - Se r > r_opt → Forza attrattiva (riporta verso r_opt)
    #   - Se r < r_opt → Forza repulsiva debole
    #   - Risultato: Formazione di nodi e filamenti invece di espansione uniforme
    
    raggio_ottimale_solitone = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * 2.0
    deviazione_raggio = r_conforme - raggio_ottimale_solitone
    forza_auto_organizzazione = -0.1 * (deviazione_raggio**2) / (r_conforme**3 + 1e-9)
    
    # PRESSIONE TOTALE (Con auto-organizzazione)
    pressione_totale = pressione_vuoto_totale + forza_auto_organizzazione
    
    # 6. JACOBIANO METRICO
    # --------------------
    # FISICA:
    #   Il jacobiano modifica la relazione tra χ e le quantità fisiche osservabili.
    #   Permette transizioni fluide tra regimi (Planck → classico → cosmologico)
    #   senza discontinuità numeriche.
    #
    # FORMULA:
    #   J = 1 + 4 * (1 + tanh(|χ| - 13.5)) / |χ|
    #
    # COMPORTAMENTO:
    #   - Per χ piccolo: J ≈ 1 (regime lineare)
    #   - Per χ grande: J amplifica (regime non-lineare)
    #   - Transizione attorno a χ ≈ 13.5
    
    jacobiano_metrico = 1.0 + 4.0 * (1.0 + np.tanh(np.abs(chi_sat) - 13.5)) / (np.abs(chi_sat) + 1e-9)
    
    # 7. ACCELERAZIONE FINALE
    # ------------------------
    # L'accelerazione è guidata dalla minimizzazione dell'energia topologica totale:
    #
    #   d²χ/dλ² = J * P_totale
    #
    # dove:
    #   J = Jacobiano metrico
    #   P_totale = Pressione totale (include tutti i contributi sopra)
    #
    # FISICA:
    #   Il sistema evolve naturalmente verso stati che minimizzano E_totale,
    #   risultando in solitoni fermionici topologicamente stabili (chiusura 4π).
    
    accelerazione_conforme = pressione_totale * (jacobiano_metrico + 1e-9)
    
    # 8. DAMPING VISCOSO (Stabilità Numerica)
    # ----------------------------------------
    # TEORIA:
    #   Un piccolo termine di damping previene oscillazioni caotiche
    #   attorno ai punti di equilibrio.
    #
    # FORMULA:
    #   F_damp = -γ * dχ/dλ
    #
    # FISICA:
    #   Simula "attrito geometrico" o dissipazione nel sistema.
    #   Essenziale per la convergenza verso configurazioni stabili.
    
    coefficiente_damping = 0.8  # AUMENTATO per smorzare energia cinetica in eccesso
    termine_damping = -coefficiente_damping * velocita_chi
    
    # 9. POTENZIALE ARMONICO DI RICHIAMO
    # -----------------------------------
    # TEORIA:
    #   Forza elastica che richiama χ verso l'equilibrio (χ = 0).
    #   Previene divergenza infinita senza saturare la densità.
    #
    # FORMULA:
    #   F_richiamo = -ω * χ
    #
    # FISICA:
    #   - Sostituisce il meccanismo di saturazione (tanh rimosso)
    #   - Permette oscillazioni stabili attorno alla scala classica
    #   - La densità può ancora divergere (senza saturare), ma χ oscillerà
    #
    # COMPORTAMENTO:
    #   - χ → +∞: forza negativa (richiamo verso 0)
    #   - χ → -∞: forza positiva (richiamo verso 0)
    #   - Risultato: sistema diventa un oscillatore armonico smorzato
    
    forza_richiamo_armonico = -OMEGA_RICHIAMO * chi
    
    # ACCELERAZIONE TOTALE
    accelerazione_finale = accelerazione_conforme + termine_damping + forza_richiamo_armonico
    
    # ========================================================================
    # EQUAZIONI DI EVOLUZIONE (Sistema dinamico 2D)
    # ========================================================================
    # Restituiamo [dχ/dλ, d²χ/dλ²] al solutore ODE (solve_ivp)
    #
    # Il sistema evolve secondo le equazioni:
    #   dχ/dλ = velocita_chi
    #   d²χ/dλ² = accelerazione_finale
    #
    # dove λ è il parametro affine (non il tempo esterno t).
    # Il tempo fisico emerge dalla geometria attraverso H_fisica.
    return [velocita_chi, accelerazione_finale]


# ============================================================================
# EQUAZIONE DI EINSTEIN-CARTAN PER 24 CAMPI LOCALI ACCOPPIATI
# ============================================================================

def equazione_estado_einstein_cartan_24_campi(lambda_affine, stato_vettoriale, scatolamento, 
                                               errore_chiusura_locale, contorsione_locale):
    """
    Evoluzione geometrodinamica per 24 campi χᵢ accoppiati topologicamente.
    
    ARCHITETTURA:
    -------------
    Ogni segmento i del reticolo di Leech ha:
    - χᵢ: Potenziale di scala locale
    - vᵢ: Velocità locale dχᵢ/dλ
    
    I segmenti interagiscono tramite:
    - Accoppiamento topologico (matrice 24×24)
    - Diffusione di torsione tra vicini
    - Forze locali (pressione, bounce, chiusura)
    
    DINAMICA:
    ---------
    Per ogni segmento i:
    
      d²χᵢ/dλ² = F_local[i] + F_coupling[i] + F_torsion[i] + F_closure[i]
      
    dove:
      - F_local[i]:    Pressione locale (ρ_SX - ρ_DX)
      - F_coupling[i]: Σⱼ w_ij × (χⱼ - χᵢ)  (diffusione)
      - F_torsion[i]:  Bounce locale (β × ρᵢ²)
      - F_closure[i]:  Forza topologica (∮τds[i] → 4π)
    
    Parametri:
    ----------
    lambda_affine : float
        Parametro affine (non tempo).
    stato_vettoriale : ndarray, shape (48,)
        Stato: [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]
    scatolamento : float
        Parametro di confinamento cosmologico.
    errore_chiusura_locale : ndarray, shape (24,)
        Errore da 4π per ogni segmento.
    contorsione_locale : ndarray, shape (24,)
        Norma K² per ogni segmento.
        
    Restituisce:
    -----------
    derivata : ndarray, shape (48,)
        [dχ₀/dλ, dv₀/dλ, dχ₁/dλ, dv₁/dλ, ...]
    """
    N_segmenti = segmenti_frattali  # 24
    
    # ========================================================================
    # ESTRAZIONE STATO
    # ========================================================================
    # Stato vettoriale: [χ₀, v₀, χ₁, v₁, ...] → separare χ e v
    chi_array = stato_vettoriale[::2]   # Indici pari: χᵢ  (shape: 24)
    vel_array = stato_vettoriale[1::2]  # Indici dispari: vᵢ (shape: 24)
    
    # ========================================================================
    # 1. GEOMETRIA LOCALE PER OGNI SEGMENTO
    # ========================================================================
    # Calcolo fattori chirali locali (come modello globale, ma per ogni i)
    
    chi_sat = 150.0 * np.tanh(chi_array / 150.0)
    f_dx = np.exp(+chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    f_sx = np.exp(-chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    
    # Densità locale per ogni segmento
    # IMPORTANTE: Non saturo con tanh - lascio crescere linearmente
    indicatore_densita = 1.0 + np.abs(chi_array) / 100.0
    
    # Densità base (materia vs spazio)
    densita_materia = (f_sx - f_dx) * scatolamento
    
    # Densità da torsione locale (include contorsione K²)
    densita_torsione = contorsione_locale * COEFFICIENTE_ACCOPPIAMENTO
    
    # Densità totale per segmento (T^00)
    densita_totale = (densita_materia + densita_torsione) * indicatore_densita
    
    # ========================================================================
    # 2. PRESSIONI LOCALI (T^ii)
    # ========================================================================
    
    # Equazione di stato: P = w × ρ (w = -1/3 per relatività)
    w = -1.0 / 3.0
    pressione_gravitazionale = w * densita_totale  # ATTRATTIVA (negativa)
    
    # Pressione di repulsione spin (Einstein-Cartan): P_rep = β × ρ²
    pressione_repulsione_spin = BETA_REPULSIONE_SPIN * (densita_totale ** 2)  # REPULSIVA
    
    # ========================================================================
    # 3. ACCOPPIAMENTO TOPOLOGICO TRA SEGMENTI
    # ========================================================================
    # Ogni segmento "sente" i vicini tramite la matrice di accoppiamento
    # 
    # F_coupling[i] = κ × Σⱼ w_ij × (χⱼ - χᵢ)
    #
    # FISICA:
    #   - Se χⱼ > χᵢ → vicino j "spinge" i verso espansione
    #   - Se χⱼ < χᵢ → vicino j "tira" i verso contrazione
    #   - Effetto: diffusione di densità/torsione tra segmenti
    
    forza_coupling = np.zeros(N_segmenti)
    for i in range(N_segmenti):
        # Differenza pesata con tutti i vicini
        differenza_vicini = chi_array - chi_array[i]  # χⱼ - χᵢ per tutti j
        forza_coupling[i] = np.dot(MATRICE_ACCOPPIAMENTO_LEECH[i, :], differenza_vicini)
    
    # Coefficiente che controlla la forza dell'accoppiamento
    forza_coupling *= KAPPA_COUPLING_24
    
    # ========================================================================
    # 4. FORZA DI CHIUSURA SPINORIALE LOCALE (4π vincolo)
    # ========================================================================
    # Ogni segmento deve soddisfare ∮τds = 4π localmente
    # Se errore > 0 → forza contrattiva
    # Se errore < 0 → forza espansiva
    
    k_chiusura_locale = 50.0
    TARGET_4PI = 4.0 * np.pi
    
    # errore_chiusura_locale è normalizzato: riporto ad assoluto
    errore_assoluto = errore_chiusura_locale * TARGET_4PI
    forza_chiusura = -k_chiusura_locale * errore_assoluto
    
    # ========================================================================
    # 5. FORZA DI RICHIAMO ARMONICO (Previene divergenza)
    # ========================================================================
    # Richiama ogni χᵢ verso equilibrio (χᵢ = 0)
    forza_richiamo = -OMEGA_RICHIAMO * chi_array
    
    # ========================================================================
    # 6. ACCELERAZIONE TOTALE PER OGNI SEGMENTO
    # ========================================================================
    # Somma di tutte le forze
    
    accelerazione = (
        pressione_repulsione_spin - pressione_gravitazionale +  # Fisica locale
        forza_coupling +                                         # Accoppiamento vicini
        forza_chiusura +                                         # Vincolo topologico
        forza_richiamo                                           # Richiamo armonico
    )
    
    # Damping locale (stabilità numerica)
    # AUMENTATO per sistema 24-campi: maggiore damping previene divergenza
    damping = 0.6
    forza_viscosa = -damping * vel_array
    
    accelerazione_finale = accelerazione + forza_viscosa
    
    # ========================================================================
    # 7. COSTRUZIONE DERIVATA VETTORIALE
    # ========================================================================
    # Formato: [dχ₀/dλ, dv₀/dλ, dχ₁/dλ, dv₁/dλ, ...]
    
    derivata = np.zeros(2 * N_segmenti)  # 48 elementi
    derivata[::2] = vel_array             # dχᵢ/dλ = vᵢ
    derivata[1::2] = accelerazione_finale # dvᵢ/dλ = Fᵢ
    
    return derivata


# --- 3. DEFINIZIONE STILI GRAFICI ---
def set_style_3d(ax, title, color):
    ax.set_title(title, color=color, fontsize=9, weight='bold', pad=15)
    ax.xaxis.set_pane_color((0,0,0,0)); ax.yaxis.set_pane_color((0,0,0,0)); ax.zaxis.set_pane_color((0,0,0,0))
    ax.xaxis._axinfo["grid"].update({'color': '#22c55e', 'linewidth': 0.1, 'alpha': 0.15})
    ax.yaxis._axinfo["grid"].update({'color': '#22c55e', 'linewidth': 0.1, 'alpha': 0.15})
    ax.zaxis._axinfo["grid"].update({'color': '#22c55e', 'linewidth': 0.1, 'alpha': 0.15})
    ax.tick_params(colors='#64748b', labelsize=7)

def set_style_2d(ax, title, color):
    ax.set_title(title, color=color, fontsize=9, weight='bold', pad=10)
    ax.spines['bottom'].set_color('#1e293b'); ax.spines['left'].set_color('#1e293b')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(colors='#64748b', labelsize=7)
    ax.grid(color='#22c55e', linestyle='--', linewidth=0.1, alpha=0.2)

# --- 4. INIZIALIZZAZIONE INTERFACCIA E SUBPLOTS ---
fig = plt.figure(figsize=(18, 10), facecolor='#020617')
gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 0.8], hspace=0.35, wspace=0.25)
plt.subplots_adjust(bottom=0.15, top=0.85, left=0.06, right=0.90)

ax_mat = fig.add_subplot(gs[0, 0], projection='3d', facecolor='#020617')
ax_main = fig.add_subplot(gs[0, 1], projection='3d', facecolor='#020617')
ax_spa = fig.add_subplot(gs[0, 2], projection='3d', facecolor='#020617')

set_style_3d(ax_mat, "SPETTRO MATERIA 3D (CHIRALITÀ SX)", '#ff007f')
set_style_3d(ax_main, "TOPOLOGIA GLOBALE INTRINSECA REALE", '#deff9a')
set_style_3d(ax_spa, "SPETTRO SPAZIO 3D (CHIRALITÀ DX)", '#00d2ff')

ax_fft = fig.add_subplot(gs[1, 0:2], facecolor='#020617') 
ax_fractal = fig.add_subplot(gs[1, 2], facecolor='#020617') 

set_style_2d(ax_fft, "TELEMETRIA GEOMETRICA PURA", '#deff9a')
set_style_2d(ax_fractal, "COMPLESSITÀ FRATTALE ORIGINARIA", '#ffb100')

ax_z_axis = ax_fft.twinx()
ax_z_axis.spines['top'].set_visible(False); ax_z_axis.spines['left'].set_visible(False)
ax_z_axis.spines['right'].set_color('#ff007f'); ax_z_axis.tick_params(colors='#ff007f', labelsize=7)

ax_g_axis = ax_fft.twinx()
ax_g_axis.spines['top'].set_visible(False); ax_g_axis.spines['left'].set_visible(False)
ax_g_axis.spines['right'].set_position(('outward', 45))
ax_g_axis.spines['right'].set_color('#38bdf8'); ax_g_axis.tick_params(colors='#38bdf8', labelsize=7)

linea_fft, = ax_fft.plot([], [], color='#deff9a', lw=1.5, label='FFT Modale (SX)')
linea_z, = ax_z_axis.plot([], [], color='#ff007f', lw=1.2, linestyle='--', label='Z Geometrico')
linea_g, = ax_g_axis.plot([], [], color='#38bdf8', lw=1.5, linestyle='-', label='G Geometrico')
linea_fractal, = ax_fractal.plot([], [], color='#ffb100', lw=1.5)

linea_mat, = ax_mat.plot([], [], [], color='#ff007f', lw=1.2, alpha=0.8)
linea_spa, = ax_spa.plot([], [], [], color='#00d2ff', lw=1.2, alpha=0.8)

# Il DX (Spazio) diventa l'involucro esterno espanso, l'SX (Materia) diventa il nucleo denso.
scat_dx = ax_main.scatter([], [], [], color='#00d2ff', s=1.0, alpha=0.15)
scat_sx = ax_main.scatter([], [], [], color='#ff007f', s=1.5, alpha=0.9)

punti_complessita = []; punti_G = []; punti_Z = []

# ==============================================================================
# SISTEMA DI RENDERING DINAMICO ADATTIVO
# ==============================================================================
# Gestisce la visualizzazione del manifold durante variazioni esponenziali di rm
# causate da bounce quantistici, collassi gravitazionali, e transizioni di fase.
#
# Strategia multi-livello:
# 1. EMA (Exponential Moving Average) per smooth tracking di rm
# 2. Soft clipping per prevenire overflow durante picchi estremi
# 3. Box aspect dinamico per mantenere proporzioni geometriche corrette
# 4. Zoom adaptivo durante fasi di bounce (quando rapporto P_rep/P_grav >> 1)
#
limiti_plot_history = []     # Storia completa rm per diagnostica
rm_ema = None                # Exponential Moving Average di rm
ema_alpha = 0.3              # Peso per nuovi valori (0.3 = smoothing moderato)
bounce_zoom_factor = 1.0     # Fattore zoom extra durante bounce (dinamico)
last_rm_derivative = 0.0     # Derivata rm per rilevare accelerazioni

text_info = fig.text(0.06, 0.96, "", color='#deff9a', fontname='monospace', fontsize=8, weight='bold', verticalalignment='top')
text_regime = fig.text(0.50, 0.96, "", color='#ffb100', fontname='monospace', fontsize=9, weight='bold', verticalalignment='top', horizontalalignment='center')

linee = [linea_fft, linea_z, linea_g]
etichette = [l.get_label() for l in linee]
legenda = ax_fft.legend(linee, etichette, loc='upper right', facecolor='#0f172a', edgecolor='#1e293b', fontsize=8)
for testo in legenda.get_texts(): testo.set_color('#64748b')

# --- 5. ENGINE DI PROIEZIONE GEOMETRICA UNIFICATO ---

# INIZIALIZZAZIONE STATO DINAMICO: Scalare vs 24 Campi Locali
# ------------------------------------------------------------
if USA_24_CAMPI_LOCALI:
    # MODALITÀ 24 CAMPI LOCALI
    # ------------------------
    # Stato: [χ₀, v₀, χ₁, v₁, ..., χ₂₃, v₂₃]  → shape (48,)
    #
    # Ogni segmento del reticolo di Leech ha:
    # - χᵢ: potenziale di scala locale
    # - vᵢ: velocità locale dχᵢ/dλ
    #
    # Condizioni iniziali: tutti i segmenti partono vicino alla scala di Planck
    # con una piccola perturbazione casuale per rompere la simmetria
    
    chi_medio_iniziale = -4.50  # Scala di Planck
    perturbazione_std = 0.3      # Deviazione standard della perturbazione casuale
    
    # Seed fisso per riproducibilità
    np.random.seed(42)
    
    # Genera χᵢ iniziali con perturbazione casuale
    chi_iniziale_24 = chi_medio_iniziale + np.random.normal(0, perturbazione_std, segmenti_frattali)
    
    # Velocità iniziali: leggera espansione + perturbazione casuale
    vel_iniziale_24 = 1.0 + np.random.normal(0, 0.2, segmenti_frattali)
    
    # Costruzione stato vettoriale: [χ₀, v₀, χ₁, v₁, ...]
    stato_attuale = np.zeros(2 * segmenti_frattali)  # 48 elementi
    stato_attuale[::2] = chi_iniziale_24   # Indici pari: χᵢ
    stato_attuale[1::2] = vel_iniziale_24  # Indici dispari: vᵢ
    
    print(f"\n[24 CAMPI LOCALI] Sistema inizializzato con {segmenti_frattali} segmenti accoppiati")
    print(f"  χ medio: {np.mean(chi_iniziale_24):.3f} ± {np.std(chi_iniziale_24):.3f}")
    print(f"  Perturbazione: ±{perturbazione_std} (rompe simmetria)")
    print(f"  Accoppiamento κ: {KAPPA_COUPLING_24}")
else:
    # MODALITÀ CAMPO GLOBALE SCALARE (compatibilità con modello originale)
    # --------------------------------------------------------------------
    # Stato: [χ, v]  → shape (2,)
    stato_attuale = [-4.50, 1.0] 
    print("\n[CAMPO GLOBALE] Modalità compatibilità (χ scalare)")

lambda_affine_corrente = 0.0  # Parametro affine, non tempo esterno
complessita_precedente = None
tempo_emergente_cumulativo = 0.0  # Orologio geometrico emergente
animazione_in_esecuzione = args.headless or args.film or False

# Variabili per calcolo curvatura e torsione
curvatura_scalare_precedente = 0.0
torsione_precedente = 0.0

# Variabili per la dinamica guidata dalla chiusura topologica
errore_chiusura_precedente = 0.0
contorsione_k_precedente = 0.0

velocita_precedente = stato_attuale[1]
suono_inversione_fatto = False

# File di log per tracciare la stabilità topologica
log_stabilita_path = os.path.join(os.path.dirname(__file__), 'stabilita.log')
log_stabilita_file = None
if args.headless or args.film:
    # Apri il file di log in modalità append con encoding UTF-8
    log_stabilita_file = open(log_stabilita_path, 'w', encoding='utf-8')  # UTF-8 per supportare π
    log_stabilita_file.write("=" * 120 + "\n")
    log_stabilita_file.write(f"LOG STABILITÀ TOPOLOGICA - Avvio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_stabilita_file.write("=" * 120 + "\n")
    log_stabilita_file.write(f"{'Frame':<8} {'Lambda':<12} {'Chi':<12} {'K (norm)':<15} {'Errore 4π':<15} {'ρ_total':<12} {'Rapp R/A':<12} {'Status':<20}\n")
    log_stabilita_file.write("-" * 120 + "\n")
    log_stabilita_file.flush()


def genera_mappatura(log_r, frame):
    """
    Genera la mappatura geometrica con supporto per χ scalare o vettoriale (24 campi).
    
    Parametri:
    ----------
    log_r : float o ndarray
        - Se scalare: χ globale (compatibilità)
        - Se array (24,): χᵢ per ogni segmento
    frame : int
        Numero del frame corrente
        
    Restituisce:
    -----------
    X_dx, Y_dx, Z_dx : ndarray
        Coordinate 3D del lobo DX (espansione)
    X_sx, Y_sx, Z_sx : ndarray
        Coordinate 3D del lobo SX (materia)
    r_m : float
        Raggio metrico medio
    freq : float
        Frequenza base
    theta, p_dx, p_sx : ndarray
        Coordinate angolari e perturbazioni
    """
    # Gestione input: scalare vs vettoriale
    if np.ndim(log_r) == 0:
        # Modalità scalare (compatibilità)
        chi_medio = float(log_r)
        usa_variazione_locale = False
    else:
        # Modalità 24 campi locali
        if len(log_r) != segmenti_frattali:
            raise ValueError(f"log_r deve essere scalare o array di {segmenti_frattali} elementi")
        chi_array = np.asarray(log_r)
        chi_medio = np.mean(chi_array)  # Usa media per geometria base
        usa_variazione_locale = True
    
    # Perturbazione stocastica minima per evitare congelamento in minimi locali (regime de Sitter)
    perturbazione_antistasi = np.random.normal(0, 1e-15)
    log_r_clamped = 150.0 * np.tanh((chi_medio + perturbazione_antistasi) / 150.0)
    f_dx = np.exp(log_r_clamped * COEFFICIENTE_ACCOPPIAMENTO)
    f_sx = np.exp(-log_r_clamped * COEFFICIENTE_ACCOPPIAMENTO)
    theta = np.linspace(0, 4 * np.pi, risoluzione_base)
    
    if np.abs(chi_medio) < 15.0:
        esponente = chi_medio - 35.0
    else:
        esponente = np.sign(chi_medio) * (15.0 + np.log(np.abs(chi_medio) - 13.5) * 5.0) - 35.0
    ordini_di_grandezza = max(0.0, esponente + 35.0)
    
    r_m = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(log_r_clamped * COEFFICIENTE_ACCOPPIAMENTO)
    distorsione_topologica = (f_dx - f_sx) * (COEFFICIENTE_ACCOPPIAMENTO * 0.1)
    theta_spazio = theta + distorsione_topologica * np.sin(3.0 * theta)
    theta_materia = theta - distorsione_topologica * np.sin(3.0 * theta)
    
    env_dx_f = np.zeros_like(theta_spazio)
    env_sx_f = np.zeros_like(theta_materia)
    z_s_f = np.zeros_like(theta)
    foc_dx_f = np.zeros_like(theta_spazio)
    foc_sx_f = np.zeros_like(theta_materia)
    
    # MODULAZIONE LOCALE PER 24 CAMPI
    # Se usa_variazione_locale = True, moduliamo le ampiezze in base a χᵢ locale
    if usa_variazione_locale:
        # Dividi theta in 24 settori
        punti_per_segmento = risoluzione_base // segmenti_frattali
        modulazione_locale = np.ones(risoluzione_base)
        
        for i_seg in range(segmenti_frattali):
            idx_start = i_seg * punti_per_segmento
            idx_end = min((i_seg + 1) * punti_per_segmento, risoluzione_base)
            
            # Deviazione dal χ medio
            delta_chi = chi_array[i_seg] - chi_medio
            
            # Modulazione: fattore moltiplicativo basato su deviazione locale
            # Se χᵢ > χ_medio → amplifica (più denso)
            # Se χᵢ < χ_medio → riduce (meno denso)
            fattore_locale = 1.0 + 0.3 * np.tanh(delta_chi / 2.0)
            modulazione_locale[idx_start:idx_end] = fattore_locale
    else:
        modulazione_locale = 1.0
    
    for k in range(4):
        freq_k = 12.0 * (12.0 ** k)
        amp_k = 1.0 / (12.0 ** k)
        peso = 1.0 if k == 0 else np.clip(ordini_di_grandezza - (k - 1), 0.0, 1.0)
            
        if peso > 0.0:
            env_dx_f += peso * amp_k * np.sin(freq_k * theta_spazio) * modulazione_locale
            env_sx_f += peso * amp_k * np.sin(freq_k * theta_materia) * modulazione_locale
            z_s_f += peso * amp_k * np.cos(freq_k * theta)
            foc_dx_f += peso * amp_k * np.cos(freq_k * theta_spazio) * modulazione_locale
            foc_sx_f += peso * amp_k * np.cos(freq_k * theta_materia) * modulazione_locale
            
    env_dx = np.sqrt(float(segmenti_frattali)) * 0.3 * env_dx_f
    env_sx = np.sqrt(float(segmenti_frattali)) * 0.3 * env_sx_f
    p_dx = env_dx * f_dx
    p_sx = env_sx * f_sx
    
    xb = (r_m + (p_dx + p_sx)*0.5) * np.cos(theta)
    yb = (r_m + (p_dx + p_sx)*0.5) * np.sin(theta)
    zb = (r_m * ACCORCIAMENTO_ANGOLARE) * z_s_f
    
    # --- TRIEDRO DI FRENET-SERRET PURO ---
    # Nessun filtraggio sulle derivate: mostra l'effettivo calcolo spaziale nudo e crudo
    dx_ = np.gradient(xb); dy_ = np.gradient(yb); dz_ = np.gradient(zb)
    T = np.vstack((dx_, dy_, dz_)); T /= (np.linalg.norm(T, axis=0) + 1e-12)
    ddx_ = np.gradient(dx_); ddy_ = np.gradient(dy_); ddz_ = np.gradient(dz_)
    N = np.vstack((ddx_, ddy_, ddz_)); N /= (np.linalg.norm(N, axis=0) + 1e-12)
    B = np.cross(T.T, N.T).T
    
    A_DX = u[:, None] + (theta/2)[None, :] + frame*0.05
    A_SX = u[:, None] - (theta/2)[None, :] - frame*0.05
    
    # Ripristino della Chiralità di Spessore (Il DX si espande, l'SX si condensa)
    foc_dx = (r_m / float(N_u)) * f_dx * (1 + 0.3 * foc_dx_f)
    foc_sx = (r_m / float(N_u)) * f_sx * (1 + 0.3 * foc_sx_f)
    
    X_dx = xb + foc_dx * (np.cos(A_DX)*N[0] + np.sin(A_DX)*B[0])
    Y_dx = yb + foc_dx * (np.cos(A_DX)*N[1] + np.sin(A_DX)*B[1])
    Z_dx = zb + foc_dx * (np.cos(A_DX)*N[2] + np.sin(A_DX)*B[2])
    X_sx = xb + foc_sx * (np.cos(A_SX)*N[0] + np.sin(A_SX)*B[0])
    Y_sx = yb + foc_sx * (np.cos(A_SX)*N[1] + np.sin(A_SX)*B[1])
    Z_sx = zb + foc_sx * (np.cos(A_SX)*N[2] + np.sin(A_SX)*B[2])
    
    return X_dx.flatten(), Y_dx.flatten(), Z_dx.flatten(), X_sx.flatten(), Y_sx.flatten(), Z_sx.flatten(), r_m, 12.0, np.tile(theta, N_u), np.tile(p_dx, N_u), np.tile(p_sx, N_u)

# --- MAPPATURA SPETTRALE DELLE SCALE METRICHE NATURALI ---
def ottieni_regime_metrico(esponente):
    if esponente < -35.0:
        return "REGIME SUB-PLANCKIANO (SCHIUMA QUANTISTICA DISCRETA)"
    elif esponente < -34.0:
        return "SCALA DI PLANCK FONDAMENTALE (EMERGENTE DA L_ARCO)"
    elif esponente < -30.0:
        return "SCALA DI GRANDE UNIFICAZIONE (GUT / TRANSIZIONE CHIRALE)"
    elif esponente < -18.0:
        return "SCALA ELETTRODEBOLE / MECCANISMO DI HIGGS"
    elif esponente < -15.0:
        return "SCALA ADRO-NUCLEARE (FORZA NUCLEARE FORTE / QUARK)"
    elif esponente < -14.0:
        return "SCALA DEI NUCLEI ATOMICI (FORZA NUCLEARE DEBOLE)"
    elif esponente < -10.0:
        return "SCALA ATOMICA CORRENTE (RAGGIO DI BOHR / ELETTRONICA)"
    elif esponente < -9.0:
        return "SCALA NANOMETRICA (CRISTALLI / CHIMICA MOLECOLARE)"
    elif esponente < -6.0:
        return "REGIME BIOLOGICO CELLULARE (MICRON)"
    elif esponente < -3.0:
        return "REGIME FISICO MACROSCOPICO STANDARD"
    elif esponente < 6.0:
        return "SCALA PLANETARIA / GEODINAMICA COVARIANTE"
    elif esponente < 11.0:
        return "SCALA DEL SISTEMA SOLARE"
    elif esponente < 21.0:
        return "REGIME INTERSTELLARE / STRUTTURA GALATTICA"
    elif esponente < 26.0:
        return "SCALA DI AMMASSI GALATTICI (GRANDE STRUTTURA)"
    else:
        return "MACROCOSMO COSMOLOGICO (ORIZZONTE OSSERVABILE)"

# --- FORMATTAZIONE TELEMETRIA HUMAN-READABLE ---
def format_human_time(seconds):
    """Converte il tempo emergente in formato leggibile umano con unità appropriate."""
    if seconds == 0:
        return "0 s"
    
    abs_seconds = abs(seconds)
    segno = "⏪ " if seconds < 0 else ""  # Freccia retrocausale per tempo negativo
    
    # Scale temporali subatomiche
    if abs_seconds < 1e-15:
        return f"{segno}{abs_seconds * 1e18:.2f} as"  # attosecondi
    elif abs_seconds < 1e-12:
        return f"{segno}{abs_seconds * 1e15:.2f} fs"  # femtosecondi
    elif abs_seconds < 1e-9:
        return f"{segno}{abs_seconds * 1e12:.2f} ps"  # picosecondi
    elif abs_seconds < 1e-6:
        return f"{segno}{abs_seconds * 1e9:.2f} ns"   # nanosecondi
    elif abs_seconds < 1e-3:
        return f"{segno}{abs_seconds * 1e6:.2f} μs"   # microsecondi
    elif abs_seconds < 1:
        return f"{segno}{abs_seconds * 1e3:.2f} ms"   # millisecondi
    # Scale umane
    elif abs_seconds < 60:
        return f"{segno}{abs_seconds:.2f} s"
    elif abs_seconds < 3600:
        return f"{segno}{abs_seconds / 60:.2f} min"
    elif abs_seconds < 86400:
        return f"{segno}{abs_seconds / 3600:.2f} ore"
    elif abs_seconds < 31557600:  # anno siderale
        return f"{segno}{abs_seconds / 86400:.2f} giorni"
    # Scale cosmiche
    elif abs_seconds < 3.15576e9:  # 100 anni
        return f"{segno}{abs_seconds / 31557600:.2f} anni"
    elif abs_seconds < 3.15576e12:  # 100,000 anni
        return f"{segno}{abs_seconds / 3.15576e7:.2f} millenni"
    elif abs_seconds < 3.15576e15:  # 100 milioni di anni
        return f"{segno}{abs_seconds / 3.15576e10:.2f} Myr"  # Milioni di anni (Megayears)
    else:
        return f"{segno}{abs_seconds / 3.15576e13:.2f} Gyr"  # Miliardi di anni (Gigayears)

def format_hubble(h_value):
    """Formatta il parametro di Hubble locale in unità leggibili con contesto fisico."""
    if abs(h_value) < 1e-50:
        return "H: ZERO (STASI METRICA)"
    
    abs_h = abs(h_value)
    segno = "↓" if h_value < 0 else "↑"
    
    # Conversione a unità cosmologiche standard (km/s/Mpc)
    # H_0 ~ 70 km/s/Mpc ~ 2.27e-18 s^-1
    h_cosmo_units = abs_h / 2.27e-18 * 70.0  # conversione a km/s/Mpc
    
    # Scale fisiche
    if abs_h < 1e-25:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (ultra-lento)"
    elif abs_h < 1e-20:
        return f"H {segno}: {h_cosmo_units:.2f} km/s/Mpc (cosmologico)"
    elif abs_h < 1e-15:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (galattico)"
    elif abs_h < 1e-10:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (stellare)"
    elif abs_h < 1e-5:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (planetario)"
    elif abs_h < 1:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (rapido)"
    else:
        return f"H {segno}: {abs_h:.2e} s⁻¹ (esplosivo)"


# --- SISTEMA DI LOGGING EVENTI SCIENTIFICI ---
def log_evento_visivo(tipo_evento, descrizione, tempo_emergente, metrica_exp, hubble_value):
    """
    Registra eventi scientifici significativi nel diario di bordo della simulazione.
    Salva timestamp del tempo emergente, scala metrica e parametro di Hubble.
    
    Args:
        tipo_evento: Categoria dell'evento (es: 'TRANSIZIONE_FASE', 'INVERSIONE_TEMPORALE', 'VUOTO_QUANTISTICO')
        descrizione: Descrizione testuale dell'evento
        tempo_emergente: Valore del tempo proprio emergente (secondi)
        metrica_exp: Esponente della scala metrica (10^exp metri)
        hubble_value: Valore del parametro di Hubble (s^-1)
    """
    log_file = 'osservazioni_simulazione.log'
    timestamp_reale = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tempo_formattato = format_human_time(tempo_emergente)
    hubble_formattato = format_hubble(hubble_value)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"="*80 + "\n")
        f.write(f"[{timestamp_reale}] EVENTO: {tipo_evento}\n")
        f.write(f"Descrizione: {descrizione}\n")
        f.write(f"Tempo Emergente: {tempo_formattato} ({tempo_emergente:.6e} s)\n")
        f.write(f"Scala Metrica: 10^({metrica_exp:.2f}) m\n")
        f.write(f"Parametro di Hubble: {hubble_formattato} ({hubble_value:.6e} s⁻¹)\n")
        f.write(f"="*80 + "\n\n")


f_playback_handle = None
ultimo_errore_frame = -1

# Variabili globali per tracking eventi
evento_vuoto_quantistico_attivo = False
evento_inversione_temporale_precedente = False

# --- 6. LOOP DI COERENZA DINAMICA INTEGRALE ---
def update(frame, target_file_handle=None):
    global stato_attuale, lambda_affine_corrente, complessita_precedente, tempo_emergente_cumulativo
    global curvatura_scalare_precedente, torsione_precedente
    global punti_complessita, punti_G, punti_Z, animazione_in_esecuzione, velocita_precedente, suono_inversione_fatto
    global f_playback_handle, ultimo_errore_frame
    global evento_vuoto_quantistico_attivo, evento_inversione_temporale_precedente
    global limiti_plot_history, rm_ema, bounce_zoom_factor, last_rm_derivative  # Sistema rendering dinamico
    global scat_dx, scat_sx, linea_mat, linea_spa  # Plot objects ricreatati dopo ax.cla()
    
    if args.playback:
        if f_playback_handle is None:
            try:
                f_playback_handle = h5py.File(file_data_path, 'r', libver='latest', swmr=True)
            except OSError:
                f_playback_handle = h5py.File(file_data_path, 'r')
                
        if frame >= f_playback_handle['telemetria_scalare'].shape[0]:
            return scat_dx, scat_sx, linea_mat, linea_spa, linea_fft, linea_z, linea_g, linea_fractal
            
        try:
            meta = f_playback_handle['telemetria_scalare'][frame]
            rm = meta['rm']
            G_geometrica = meta['g_geo']
            Z_geometrica = meta['z_geo']
            esponente_visualizzato = meta['esponente']
            tempo_assoluto_adimensionale = meta['tempo_assol']
            d_tau_dinamico = meta['d_tau']
            velocita_chi = meta['v_chi']
            H_fisica = meta['h_fisica']
            tempo_emergente_cumulativo = tempo_assoluto_adimensionale * (H_fisica + 1e-43)  # Ricostruzione tempo emergente
            stato_attuale = [meta['chi_lineare'], meta['v_chi']]
            
            # RIGENERAZIONE ISTANTANEA PROCEDURALE: Ricreo i vettori 3D in tempo reale dalle coordinate scalari
            Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, _, _, th, pdx, psx = genera_mappatura(stato_attuale[0], frame)
            
            # Leggi contorsione se disponibile, altrimenti calcola in tempo reale
            if 'contorsione_k' in meta.dtype.names:
                contorsione_k = meta['contorsione_k']
            else:
                # Calcolo in tempo reale per compatibilità con vecchi file HDF5
                try:
                    nodi_sx = estrai_nodi_manifold(Xsx, Ysx, Zsx)
                    if len(nodi_sx) >= 3:
                        K_tensor = calcola_contorsione(nodi_sx)
                        contorsione_k = np.sqrt(np.mean(K_tensor**2))
                    else:
                        contorsione_k = 0.0
                except Exception:
                    contorsione_k = 0.0
            
            # Leggi chiusura spinoriale se disponibile
            if 'chiusura_spinore' in meta.dtype.names:
                chiusura_spinore = meta['chiusura_spinore']
            else:
                # Calcolo in tempo reale per compatibilità con vecchi file HDF5
                try:
                    nodi_sx = estrai_nodi_manifold(Xsx, Ysx, Zsx)
                    if len(nodi_sx) >= 3:
                        scalar_error, _ = check_chiusura_spinore(nodi_sx)
                        chiusura_spinore = scalar_error
                    else:
                        chiusura_spinore = 0.0
                except Exception:
                    chiusura_spinore = 0.0
            
            comp = np.sum(np.abs(np.diff(psx))) / (rm + 1e-9)
        except OSError as e:
            if frame != ultimo_errore_frame:
                print(f"\n[ERRORE HDF5] Lettura fallita al frame {frame} (soppressione log per i tentativi successivi): {e}")
                ultimo_errore_frame = frame
            return scat_dx, scat_sx, linea_mat, linea_spa, linea_fft, linea_z, linea_g, linea_fractal
    else:
        chi = stato_attuale[0]
        velocita_chi = stato_attuale[1]
        
        # --- CALCOLO ANALITICO DELLA SCALA METRICA SBLOCCATO ---
        chi_sat_ev = 150.0 * np.tanh(chi / 150.0)
        
        # L'esponente visivo e telemetrico si sgancia dal limite asintotico di 150 per poter misurare l'intero cosmo
        if np.abs(chi) < 15.0:
            esponente_visualizzato = chi - 35.0
        else:
            esponente_visualizzato = np.sign(chi) * (15.0 + np.log(np.abs(chi) - 13.5) * 5.0) - 35.0
            
        esponente_per_dtau = (chi_sat_ev - 35.0) if np.abs(chi_sat_ev) < 15.0 else (np.sign(chi_sat_ev) * (15.0 + np.log(np.abs(chi_sat_ev) - 13.5) * 5.0) - 35.0)
        
        # PROTEZIONE ANTI-OVERFLOW: anche qui limitiamo esponente
        esponente_dtau_totale = esponente_per_dtau + 35.0
        if np.abs(esponente_dtau_totale) > 100:
            # Regime estremo: usa valore saturato per evitare warning
            fattore_allungamento_dtau = 1e100 if esponente_dtau_totale > 100 else 1e-100
        else:
            fattore_allungamento_dtau = 10**esponente_dtau_totale
            
        d_tau_dinamico = min(0.02 + 0.005 * (fattore_allungamento_dtau ** 0.05), 1.5)  

        # ========================================================================
        # STEP 1: GENERAZIONE GEOMETRIA CORRENTE (Metrica g_μν)
        # ========================================================================
        # Generiamo il manifold 3D basato sullo stato CORRENTE di χ
        # Questo rappresenta la configurazione geometrica PRIMA dell'evoluzione temporale
        
        # Estrazione χ corrente: scalare o vettoriale
        if USA_24_CAMPI_LOCALI:
            chi_array = stato_attuale[::2]   # Estrai χᵢ da stato vettoriale [χ₀,v₀,χ₁,v₁,...]
            vel_array = stato_attuale[1::2]  # Estrai vᵢ
            chi = np.mean(chi_array)         # Per compatibilità con telemetria
            velocita_chi = np.mean(vel_array)
            Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, rm, fr, th, pdx, psx = genera_mappatura(chi_array, frame)
        else:
            chi = stato_attuale[0]
            velocita_chi = stato_attuale[1]
            Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, rm, fr, th, pdx, psx = genera_mappatura(chi, frame)
        
        # Calcolo parametri geometrici dalla configurazione corrente
        mu_dx_ist = np.mean(np.abs(pdx))
        mu_sx_ist = np.mean(np.abs(psx))
        tensione_taglio_ist = np.mean(pdx * psx)
        energia_torsionale = np.mean((np.abs(pdx) - np.abs(psx))**2)
        
        # Calcolo dell'esponente per scale visualizzate
        esponente_visualizzato = (chi - 35.0) if np.abs(chi) < 15.0 else (np.sign(chi) * (15.0 + np.log(np.abs(chi) - 13.5) * 5.0) - 35.0)
        
        # PROTEZIONE ANTI-OVERFLOW: Limitiamo a ±100 per evitare RuntimeWarning
        # Float64 può teoricamente arrivare a 10^308, ma già 10^300 genera warning
        # Range ±100 copre da scala sub-Planck a cosmologica senza overflow
        esponente_reale = esponente_visualizzato + 35.0
        esponente_safe = np.clip(esponente_reale, -100, 100)
        
        # Se esponente clippato, gestiamo esplicitamente senza calcolare 10**x
        if np.abs(esponente_reale) > 100:
            # Regime estremo: usa inf/0 invece di calcolo esatto
            fattore_allungamento_reale = np.inf if esponente_reale > 100 else 0.0
        else:
            fattore_allungamento_reale = 10**(esponente_safe)
        
        # Osservabili geometriche emergenti
        invariante_reticolo = 1.0 / (risoluzione_base * (th[1] - th[0]))
        G_geometrica = (np.abs(tensione_taglio_ist) / ((mu_dx_ist * mu_sx_ist) + 1e-12)) * invariante_reticolo * fattore_allungamento_reale
        Z_geometrica = np.abs(energia_torsionale) / (np.abs(tensione_taglio_ist) + 1e-12)
        
        volume_conforme = rm**3
        rho_totale = np.abs((np.sum(np.abs(psx)) * (th[1] - th[0]) / (volume_conforme + 1e-12)) - (energia_torsionale / (volume_conforme + 1e-12)))
        H_quadrato = (8.0 * np.pi * G_geometrica / 3.0) * rho_totale
        
        # Sblocco analitico completo dello Jacobiano per l'espansione macroscopica H
        jac_ev = 1.0 + 4.0 * (1.0 + np.tanh(np.abs(chi) - 13.5)) / (np.abs(chi) + 1e-9)
        H_fisica = np.sign(velocita_chi * jac_ev * np.log(10)) * np.sqrt(H_quadrato + 1e-36)
        
        # Curvatura scalare e torsione dalla configurazione corrente
        curvatura_scalare = np.abs(tensione_taglio_ist) / (rm**2 + 1e-12)
        torsione = np.sqrt(energia_torsionale) / (rm + 1e-12)
        
        # ========================================================================
        # STEP 2: CALCOLO TENSORE DI CONTORSIONE E CHIUSURA SPINORIALE
        # ========================================================================
        # Questi valori caratterizzano la METRICA CORRENTE e guideranno l'evoluzione
        # verso il frame successivo attraverso le equazioni di Einstein-Cartan
        
        try:
            # Estraggo i nodi del manifold SX (materia) per calcolare la geometria con torsione
            nodi_sx = estrai_nodi_manifold(Xsx, Ysx, Zsx)
            
            if len(nodi_sx) >= 3:
                # MODULO 1: Calcolo tensore di contorsione K_λμν
                K_tensor = calcola_contorsione(nodi_sx)
                # Norma di Frobenius del tensore come invariante scalare
                contorsione_k = np.sqrt(np.mean(K_tensor**2))
                
                # MODULO 2: Validazione topologica spinoriale
                # Verifica che il solitone mantenga la proprietà topologica 4π (720°)
                scalar_error, diagnostica_spinore = check_chiusura_spinore(nodi_sx)
                chiusura_spinore = scalar_error
            else:
                # Manifold troppo piccolo per calcolo affidabile
                contorsione_k = contorsione_k_precedente
                chiusura_spinore = errore_chiusura_precedente
        except Exception as e:
            # Fallback a valori precedenti in caso di errore numerico
            contorsione_k = contorsione_k_precedente
            chiusura_spinore = errore_chiusura_precedente
        
        # ========================================================================
        # LOGGING STABILITÀ TOPOLOGICA
        # ========================================================================
        # Logga i valori di contorsione e chiusura per analisi post-simulazione
        if log_stabilita_file is not None:
            # Calcola il rapporto critico Repulsione/Attrazione
            # Questo rapporto indica quando la repulsione spin-spin diventa dominante:
            #   Rapporto << 1 → Gravità domina (collasso)
            #   Rapporto ≈ 1  → Equilibrio (transizione)
            #   Rapporto > 1   → Repulsione domina (BOUNCE quantistico!)
            
            # Ricostruisco i calcoli necessari per il rapporto
            chi_sat = 150.0 * np.tanh(chi / 150.0)
            log_r_dx = chi_sat
            r_conforme = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
            r_conforme = np.maximum(r_conforme, 1.0 * LUNGHEZZA_PLANCK_METRI)
            accoppiamento_topologico = 1.0 / (r_conforme**2 + 1e-6)
            
            # Calcolo componenti torsionali locali (semplificato dal loop principale)
            fattore_dx = np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
            fattore_sx = np.exp(-log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
            arg_dx = (4 * np.pi / risoluzione_base) * fattore_dx / (1.0 + log_r_dx**2)
            arg_sx = (4 * np.pi / risoluzione_base) * fattore_sx
            chiralita = np.where(np.arange(risoluzione_base) % 2 == 0, 1.0, -1.0)
            tor_dx = np.sinh(chiralita * arg_dx)
            tor_sx = np.sinh(chiralita * arg_sx)
            tensione_taglio = np.mean(tor_dx * tor_sx)
            energia_torsionale = np.mean((np.abs(tor_dx) - np.abs(tor_sx))**2)
            
            # DENSITÀ E PRESSIONI
            mu_dx = np.mean(np.abs(tor_dx))
            mu_sx = np.mean(np.abs(tor_sx))
            densita_materia_local = (mu_sx - mu_dx) * 2.0  # scatolamento = 2.0
            tensione_newtoniana = tensione_taglio * accoppiamento_topologico
            
            # CALCOLO DENSITÀ TOTALE (con amplificazione basata su |χ|)
            densita_torsione_quadratica = (tensione_taglio**2 + energia_torsionale**2) * accoppiamento_topologico
            densita_energia_contorsione = contorsione_k**2 * accoppiamento_topologico
            densita_base_local = densita_materia_local + densita_torsione_quadratica + densita_energia_contorsione
            
            # AMPLIFICAZIONE DENSITÀ (cresce con |χ| senza saturare)
            # Quando il manifold collassa (χ → -∞), la densità deve divergere
            # Questo è il meccanismo fisico del bounce: ρ → ∞ → P_rep = ρ² → ∞
            indicatore_densita_local = 1.0 + np.abs(chi) / 100.0
            densita_energia_totale_local = densita_base_local * indicatore_densita_local
            
            # REPULSIONE SPIN-SPIN (Einstein-Cartan: P_rep = β * ρ²)
            # Questa è la forza che blocca il collasso quando ρ diverge
            pressione_repulsione_spin = BETA_REPULSIONE_SPIN * densita_energia_totale_local**2
            
            # PRESSIONE GRAVITAZIONALE (attrattiva)
            w_equazione_stato = -1.0 / 3.0
            pressione_gravitazionale = w_equazione_stato * densita_energia_totale_local - tensione_newtoniana
            
            # RAPPORTO CRITICO CORRETTO
            # Questo è il rapporto che determina il bounce:
            #   Rapporto << 1 → Gravità domina (collasso)
            #   Rapporto ≈ 1  → Equilibrio (transizione)
            #   Rapporto > 1   → Repulsione domina (BOUNCE quantistico!)
            if abs(pressione_gravitazionale) > 1e-30:
                rapporto_repulsione_attrazione = pressione_repulsione_spin / abs(pressione_gravitazionale)
            else:
                rapporto_repulsione_attrazione = 0.0
            
            # Determina status topologico
            if abs(chiusura_spinore) < 0.01:
                status = "STABILE ✓"
            elif abs(chiusura_spinore) < 0.05:
                status = "BUONO"
            elif abs(chiusura_spinore) < 0.10:
                status = "ACCETTABILE"
            else:
                status = "INSTABILE ⚠"
            
            # EVIDENZIA IL BOUNCE!
            if rapporto_repulsione_attrazione >= 1.0:
                status += " ★BOUNCE!★"
            
            # Scrivi nel log (con ρ_total per monitorare la densità durante il collasso)
            log_stabilita_file.write(
                f"{frame:<8} {lambda_affine_corrente:<12.6f} {chi:<12.6f} "
                f"{contorsione_k:<15.6e} {chiusura_spinore:<15.6f} "
                f"{densita_energia_totale_local:<12.6e} {rapporto_repulsione_attrazione:<12.6e} {status:<20}\n"
            )
            log_stabilita_file.flush()  # Forza scrittura immediata
        
        # ========================================================================
        # STEP 3: EVOLUZIONE TEMPORALE CON FISICA DELLA TORSIONE (MODULO 3)
        # ========================================================================
        # I valori di contorsione_k e chiusura_spinore calcolati sopra
        # vengono ora usati per guidare l'evoluzione verso il frame successivo
        
        # Inizializzazione variabili locali per 24 campi (usate sia in evoluzione che in HDF5)
        if USA_24_CAMPI_LOCALI:
            contorsione_locale = np.full(segmenti_frattali, contorsione_k)
            errore_chiusura_locale = np.full(segmenti_frattali, chiusura_spinore)
        
        if animazione_in_esecuzione:
            # Evoluzione basata su parametro affine λ con fisica della torsione
            delta_lambda = 0.1  # Incremento parametro affine
            
            if USA_24_CAMPI_LOCALI:
                # ============================================================
                # MODALITÀ 24 CAMPI LOCALI
                # ============================================================
                # Ogni segmento ha contorsione e chiusura locali
                
                # Aggiorna contorsione locale per ogni segmento (semplificato)
                # In futuro, questo dovrebbe campionare K_tensor in 24 regioni angolari
                # Per ora, uso un modello semplificato con variazione angolare
                contorsione_locale[:] = contorsione_k  # Aggiorna valori (già allocato)
                # Modulazione angolare basata su θ
                angoli_segmenti = np.linspace(0, 4*np.pi, segmenti_frattali, endpoint=False)
                modulazione_angolare = 1.0 + 0.2 * np.sin(3 * angoli_segmenti)
                contorsione_locale *= modulazione_angolare
                
                # Aggiorna errore chiusura locale
                # Anche questo è semplificato: distribuisco l'errore globale
                errore_chiusura_locale[:] = chiusura_spinore  # Aggiorna valori
                # Modulazione per creare anisotropia
                errore_chiusura_locale *= (1.0 + 0.15 * np.cos(2 * angoli_segmenti))
                
                # Wrapper per solve_ivp con 24 campi
                def equazione_con_torsione_24(t, y):
                    return equazione_estado_einstein_cartan_24_campi(
                        t, y,
                        scatolamento=2.0,
                        errore_chiusura_locale=errore_chiusura_locale,
                        contorsione_locale=contorsione_locale
                    )
                
                # Integrazione ODE per 48 variabili [χ₀,v₀,χ₁,v₁,...,χ₂₃,v₂₃]
                sol = solve_ivp(
                    equazione_con_torsione_24,
                    [lambda_affine_corrente, lambda_affine_corrente + delta_lambda],
                    stato_attuale,
                    method='Radau',
                    rtol=1e-4,
                    atol=1e-6
                )
                
                # Aggiornamento stato vettoriale
                stato_attuale = sol.y[:, -1]
                
            else:
                # ============================================================
                # MODALITÀ CAMPO GLOBALE SCALARE (Compatibilità)
                # ============================================================
                
                # Wrapper per solve_ivp che include i parametri topologici
                # IMPORTANTE: equazione_stato_einstein_cartan riceve:
                #   - errore_chiusura: guida la forza di richiamo geometrico verso 4π
                #   - contorsione_k: modifica la curvatura di Ricci tramite termine K²
                def equazione_con_torsione(t, y):
                    return equazione_stato_einstein_cartan(
                        t, y, 
                        scatolamento=2.0,
                        errore_chiusura=chiusura_spinore,    # Guida verso vincolo 4π
                        contorsione_k=contorsione_k          # Contributo K² alla curvatura
                    )
                
                # Integrazione ODE con metodo implicito Radau (stabile per sistemi stiff)
                sol = solve_ivp(
                    equazione_con_torsione, 
                    [lambda_affine_corrente, lambda_affine_corrente + delta_lambda], 
                    stato_attuale, 
                    method='Radau', 
                    rtol=1e-4, 
                    atol=1e-6
                )
                
                # Aggiornamento stato per il prossimo frame
                stato_attuale = sol.y[:, -1]
                chi = stato_attuale[0]
                velocita_chi = stato_attuale[1]
            
            lambda_affine_corrente += delta_lambda
            
            # Aggiorna variabili globali per il prossimo ciclo
            errore_chiusura_precedente = chiusura_spinore
            contorsione_k_precedente = contorsione_k
        
        # ========================================================================
        # STEP 4: CALCOLO TEMPO EMERGENTE E COMPLESSITÀ
        # ========================================================================
        # Il tempo emergente è calcolato dalla geometria (curvatura + torsione)
        # Non è il tempo esterno t, ma emerge dalla dinamica del manifold
        
        comp = np.sum(np.abs(np.diff(psx))) / (rm + 1e-9)
        # Protezione anti-NaN
        if not np.isfinite(comp): comp = complessita_precedente if complessita_precedente is not None else 0.0
        
        if animazione_in_esecuzione:
            if complessita_precedente is not None:
                # Incremento temporale emergente basato sulla geometria del manifold
                # dt ∝ √(R² + τ²) dove R = curvatura scalare, τ = torsione
                delta_lambda = 0.1
                dt_emergente = np.sqrt(curvatura_scalare**2 + torsione**2) * delta_lambda
                tempo_emergente_cumulativo += dt_emergente
            complessita_precedente = comp
            curvatura_scalare_precedente = curvatura_scalare
            torsione_precedente = torsione

        # TEMPO PROPRIO FISICO CON INVERSIONI RETROCAUSALI
        # Ripristino del segno di H_fisica: se il manifold si contrae, il tempo rallenta o inverte
        tempo_assoluto_adimensionale = tempo_emergente_cumulativo / (H_fisica + 1e-43)
        
        # ========================================================================
        # STEP 5: SALVATAGGIO DATI HDF5
        # ========================================================================
        # Salviamo lo stato del manifold includendo i parametri topologici
        # che hanno guidato l'evoluzione verso questo frame
        
        if target_file_handle is not None:
            if USA_24_CAMPI_LOCALI:
                # Estrai array 24D da stato vettoriale
                chi_vec_current = stato_attuale[::2]
                vel_vec_current = stato_attuale[1::2]
                
                # Prepara array locali (semplificati - calcolati sopra se evolution attiva)
                # Se animazione non attiva, usa valori globali replicati
                if animazione_in_esecuzione:
                    # Usa i valori calcolati durante l'evoluzione
                    # (contorsione_locale e errore_chiusura_locale già definiti)
                    pass
                else:
                    # Replica valori globali
                    contorsione_locale = np.full(segmenti_frattali, contorsione_k)
                    errore_chiusura_locale = np.full(segmenti_frattali, chiusura_spinore)
                
                append_stato_hdf5(
                    target_file_handle, frame,
                    Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, th, pdx, psx, rm,
                    G_geometrica, Z_geometrica, esponente_visualizzato,
                    tempo_assoluto_adimensionale, d_tau_dinamico,
                    velocita_chi, chi, H_fisica,
                    contorsione_k, chiusura_spinore,
                    chi_vettore=chi_vec_current,
                    vel_vettore=vel_vec_current,
                    contorsione_locale=contorsione_locale,
                    chiusura_locale=errore_chiusura_locale
                )
            else:
                # Modalità scalare: usa chiamata originale
                append_stato_hdf5(
                    target_file_handle, frame, 
                    Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, th, pdx, psx, rm, 
                    G_geometrica, Z_geometrica, esponente_visualizzato, 
                    tempo_assoluto_adimensionale, d_tau_dinamico, 
                    velocita_chi, chi, H_fisica, 
                    contorsione_k,      # Norma tensore K_λμν che ha guidato l'evoluzione
                    chiusura_spinore    # Errore da 4π che ha guidato l'evoluzione
                )

    # ========================================================================
    # STEP 6: RENDERING VISUALE DINAMICO ADATTIVO CON NORMALIZZAZIONE PROIETTIVA
    # ========================================================================
    # Sistema multi-livello per gestire variazioni esponenziali di rm durante
    # bounce quantistici, collassi, e transizioni di fase geometrica.
    #
    # ARCHITETTURA RENDERING (Senior Graphics Engineer approach):
    # 1. RESET ASSI: ax.cla() per prevenire artefatti da sovrapposizioni
    # 2. NORMALIZZAZIONE PROIETTIVA: Limiti calcolati da dati reali (ptp) + centroide
    # 3. BOX ASPECT DINAMICO: Proporzioni adattive basate su geometria locale
    # 4. DEBUG LOGGING: Diagnostica limiti e aspect per troubleshooting
    
    # ==============================================================================
    # FASE 0: RESET ASSI E RICOSTRUZIONE PLOT
    # ==============================================================================
    # Pulizia completa degli assi per evitare overlay di frame precedenti.
    # Ricrea scatter plots e linee da zero ad ogni frame.
    #
    for ax in [ax_main, ax_mat, ax_spa]:
        ax.cla()  # Clear completo - rimuove tutti gli artist precedenti
        
        # Ricrea scatter plots DX (espansione) e SX (materia)
        if ax == ax_main:
            # Plot principale: entrambi i lobi
            scat_dx = ax.scatter(Xdx, Ydx, Zdx, c='#00d2ff', s=1.0, alpha=0.15, label='DX (Espansione)')
            scat_sx = ax.scatter(Xsx, Ysx, Zsx, c='#ff007f', s=1.5, alpha=0.9, label='SX (Materia)')
        elif ax == ax_mat:
            # Vista materia: solo lobo SX + linea inviluppo
            ax.scatter(Xsx, Ysx, Zsx, c='#ff007f', s=6, alpha=0.7)
            linea_mat, = ax.plot([], [], [], color='#ff007f', lw=1.2, alpha=0.8)
        elif ax == ax_spa:
            # Vista spazio: solo lobo DX + linea inviluppo
            ax.scatter(Xdx, Ydx, Zdx, c='#00d2ff', s=6, alpha=0.7)
            linea_spa, = ax.plot([], [], [], color='#00d2ff', lw=1.2, alpha=0.8)
        
        # Rigenera labels e stile dopo clear
        ax.set_xlabel('X (m)', fontsize=8)
        ax.set_ylabel('Y (m)', fontsize=8)
        ax.set_zlabel('Z (m)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
    
    # ==============================================================================
    # FASE 1: NORMALIZZAZIONE PROIETTIVA - CALCOLO CENTROIDE E RANGE DATI REALI
    # ==============================================================================
    # Calcola limiti degli assi direttamente dai dati 3D effettivi (X, Y, Z)
    # usando peak-to-peak (ptp) invece di basarsi su rm teorico.
    # Centra il manifold tramite la media delle coordinate (centro di massa).
    #
    # Unisci tutti i punti del manifold (lobo DX + lobo SX)
    all_X = np.concatenate([Xdx, Xsx])
    all_Y = np.concatenate([Ydx, Ysx])
    all_Z = np.concatenate([Zdx, Zsx])
    
    # Calcola centroide (centro di massa geometrico)
    if len(all_X) > 0:
        centroid_X = np.mean(all_X)
        centroid_Y = np.mean(all_Y)
        centroid_Z = np.mean(all_Z)
    else:
        centroid_X = centroid_Y = centroid_Z = 0.0
    
    # Calcola range effettivo (peak-to-peak) dei dati
    if len(all_X) > 0:
        range_X = np.ptp(all_X)  # max - min
        range_Y = np.ptp(all_Y)
        range_Z = np.ptp(all_Z)
    else:
        range_X = range_Y = range_Z = 1e-10  # Fallback per evitare divisione per zero
    
    # ==============================================================================
    # FASE 2: MARGINE ADATTIVO PER EVITARE CLIPPING
    # ==============================================================================
    # Aggiungi margine 20% attorno ai dati per evitare che i punti tocchino i bordi.
    # Durante bounce, aumenta margine per catturare dinamica veloce.
    #
    margin_factor = 1.2  # 20% margine standard
    
    # Tracking EMA per rilevare bounce (inversioni rapide)
    limiti_plot_history.append(rm)
    if len(limiti_plot_history) > 100:
        limiti_plot_history.pop(0)
    
    if rm_ema is None:
        rm_ema = rm
    else:
        rm_ema = ema_alpha * rm + (1 - ema_alpha) * rm_ema
    
    # Rilevamento bounce: derivata di rm cambia segno → aumenta margine temporaneamente
    rm_derivative = rm_ema - last_rm_derivative
    if abs(rm_derivative) > 1e-30 and abs(last_rm_derivative) > 1e-30:
        if np.sign(rm_derivative) != np.sign(last_rm_derivative):
            # BOUNCE! Aumenta margine per catturare inversione
            bounce_zoom_factor = min(bounce_zoom_factor + 0.3, 1.8)  # Max 1.8× durante bounce
    
    # Decay esponenziale dopo bounce
    bounce_zoom_factor = max(bounce_zoom_factor * 0.93, 1.0)
    last_rm_derivative = rm_ema
    
    # Margine finale = base × bounce_factor
    margin_factor *= bounce_zoom_factor
    
    # ==============================================================================
    # FASE 3: CALCOLO LIMITI CENTRATI CON PROTEZIONE UNDERFLOW/OVERFLOW
    # ==============================================================================
    # Limiti centrati sul centroide del manifold.
    # Protezione: limiti non scendono sotto scala di Planck (1e-35 m)
    #
    half_range_X = max(range_X * margin_factor * 0.5, 1e-35)
    half_range_Y = max(range_Y * margin_factor * 0.5, 1e-35)
    half_range_Z = max(range_Z * margin_factor * 0.5, 1e-35)
    
    # Limiti assoluti centrati
    lim_X_min = centroid_X - half_range_X
    lim_X_max = centroid_X + half_range_X
    lim_Y_min = centroid_Y - half_range_Y
    lim_Y_max = centroid_Y + half_range_Y
    lim_Z_min = centroid_Z - half_range_Z
    lim_Z_max = centroid_Z + half_range_Z
    
    # ==============================================================================
    # FASE 4: BOX ASPECT DINAMICO BASATO SU GEOMETRIA LOCALE
    # ==============================================================================
    # Calcola aspect ratio dal rapporto effettivo dei range, non da valori teorici.
    # Durante collasso: Z si comprime → aspect Z ridotto
    # Durante espansione: Z si dilata → aspect Z aumenta
    #
    xy_range_max = max(range_X, range_Y)
    
    if xy_range_max > 1e-35:
        # Aspect ratio Z rispetto a XY (clip tra 0.2 e 1.2)
        z_aspect = np.clip(range_Z / xy_range_max, 0.2, 1.2)
    else:
        z_aspect = 0.6  # Default se dati troppo piccoli
    
    # ==============================================================================
    # FASE 5: APPLICAZIONE LIMITI CENTRATI E ASPECT AI PLOT
    # ==============================================================================
    for ax in [ax_main, ax_mat, ax_spa]:
        # Applica limiti centrati sul centroide
        ax.set_xlim(lim_X_min, lim_X_max)
        ax.set_ylim(lim_Y_min, lim_Y_max)
        ax.set_zlim(lim_Z_min, lim_Z_max)
        
        # Box aspect dinamico (normalizzato con max XY = 1.0)
        if xy_range_max > 1e-35:
            aspect_X = range_X / xy_range_max
            aspect_Y = range_Y / xy_range_max
        else:
            aspect_X = aspect_Y = 1.0
        
        ax.set_box_aspect((aspect_X, aspect_Y, z_aspect))
    
    # ==============================================================================
    # FASE 6: DEBUG LOGGING PER DIAGNOSTICA RENDERING
    # ==============================================================================
    # Stampa diagnostica limiti e aspect ogni N frames per troubleshooting.
    # Mostra: frame, limiti X/Y/Z, centroide, box aspect, margine attivo
    #
    if frame % 10 == 0 or bounce_zoom_factor > 1.1:  # Log ogni 10 frames O durante bounce
        print(f"\n[RENDER DEBUG] Frame: {frame}")
        print(f"  Centroide: ({centroid_X:.6e}, {centroid_Y:.6e}, {centroid_Z:.6e}) m")
        print(f"  Range (ptp): X={range_X:.6e} Y={range_Y:.6e} Z={range_Z:.6e} m")
        print(f"  Limiti X: [{lim_X_min:.6e}, {lim_X_max:.6e}]")
        print(f"  Limiti Y: [{lim_Y_min:.6e}, {lim_Y_max:.6e}]")
        print(f"  Limiti Z: [{lim_Z_min:.6e}, {lim_Z_max:.6e}]")
        print(f"  Box Aspect: ({aspect_X:.3f}, {aspect_Y:.3f}, {z_aspect:.3f})")
        print(f"  Margine attivo: {margin_factor:.2f}× (bounce_factor={bounce_zoom_factor:.2f})")
        print(f"  rm_ema: {rm_ema:.6e} m | rm_derivative: {rm_derivative:.6e}")
    
    # Adattamento dello slicing per l'estrazione grafica del profilo dell'inviluppo sinusoidale
    th_plot = th[:risoluzione_base]
    psx_plot = psx[:risoluzione_base]
    pdx_plot = pdx[:risoluzione_base]
    zs = np.sin(th_plot*2) * rm * 0.2
    linea_mat.set_data_3d((rm+psx_plot)*np.cos(th_plot), (rm+psx_plot)*np.sin(th_plot), zs)
    linea_spa.set_data_3d((rm+pdx_plot)*np.cos(th_plot), (rm+pdx_plot)*np.sin(th_plot), zs)

    d_theta = th_plot[1] - th_plot[0] if len(th_plot) > 1 and np.abs(th_plot[1] - th_plot[0]) > 1e-12 else 1.0
    yf = rfft(psx_plot)
    xf = rfftfreq(risoluzione_base, d=d_theta)
    linea_fft.set_data(xf[:120], np.abs(yf[:120]))
    ax_fft.set_xlim(0, 25); ax_fft.set_ylim(0, np.max(np.abs(yf[:120]))*1.1 if np.max(np.abs(yf[:120])) > 0 else 1.0)
    
    # Protezione anti-NaN/Inf prima di aggiungere a plot
    G_safe = G_geometrica if np.isfinite(G_geometrica) else (punti_G[-1] if punti_G else 0.0)
    Z_safe = Z_geometrica if np.isfinite(Z_geometrica) else (punti_Z[-1] if punti_Z else 0.0)
    
    punti_G.append(G_safe)
    punti_Z.append(Z_safe)
    if len(punti_G) > 100: punti_G.pop(0)
    if len(punti_Z) > 100: punti_Z.pop(0)
    
    asse_x_dinamico = np.linspace(0, 25, len(punti_G))
    linea_g.set_data(asse_x_dinamico, punti_G)
    linea_z.set_data(asse_x_dinamico, punti_Z)
    
    g_min, g_max = min(punti_G), max(punti_G)
    z_min, z_max = min(punti_Z), max(punti_Z)
    
    # Protezione anti-NaN/Inf per overflow numerici
    if not np.isfinite(z_min): z_min = 0.0
    if not np.isfinite(z_max): z_max = 1.0
    if not np.isfinite(g_min): g_min = 0.0
    if not np.isfinite(g_max): g_max = 1.0
    
    if np.abs(z_max - z_min) < 1e-12: 
        ax_z_axis.set_ylim(z_min * 0.9, z_min * 1.1 if z_min > 0 else 1.0)
    else: 
        ax_z_axis.set_ylim(z_min - (z_max-z_min)*0.2, z_max + (z_max-z_min)*0.2)
        
    if np.abs(g_max - g_min) < 1e-12: 
        delta_g = max(abs(g_min) * 0.01, 1e-6)
        ax_g_axis.set_ylim(g_min - delta_g, g_min + delta_g)
    else: 
        ax_g_axis.set_ylim(g_min - (g_max-g_min)*0.2, g_max + (g_max-g_min)*0.2)
    
    punti_complessita.append(comp)
    if len(punti_complessita) > 100: punti_complessita.pop(0)
    linea_fractal.set_data(range(len(punti_complessita)), punti_complessita)
    max_comp = max(punti_complessita) if punti_complessita else 0.0
    ax_fractal.set_xlim(0, 100); ax_fractal.set_ylim(0, max(max_comp * 1.2, 1.0))
    
    vel_str = f"{sys._wqt_step}x" if hasattr(sys, '_wqt_step') else "1x"
    
    # Formattazione human-readable del tempo emergente
    tempo_leggibile = format_human_time(tempo_emergente_cumulativo)
    
    # Formattazione parametro di Hubble
    hubble_str = format_hubble(H_fisica)
    
    # === DASHBOARD DI TELEMETRIA SCIENTIFICA ===
    global evento_vuoto_quantistico_attivo, evento_inversione_temporale_precedente
    
    # Determinazione stato cosmologico
    if abs(H_fisica) < 1e-43:
        # VUOTO QUANTISTICO: Parametro di Hubble sotto la scala di Planck
        stato_cosmologico = "STAZIONARIO - VUOTO QUANTISTICO"
        orologio_str = "TEMPO CONGELATO"
        
        # Logging evento se è la prima volta
        if not args.playback and not evento_vuoto_quantistico_attivo:
            log_evento_visivo(
                "VUOTO_QUANTISTICO",
                "Il parametro di Hubble è sceso sotto la scala di Planck (H < 1e-43 s⁻¹). Il tempo geometrico è effettivamente congelato.",
                tempo_emergente_cumulativo,
                esponente_visualizzato,
                H_fisica
            )
            evento_vuoto_quantistico_attivo = True
    elif abs(H_fisica) < 1e-50:
        stato_cosmologico = "STAZIONARIO (TEMPO FERMO)"
        orologio_str = "BLOCCATO"
    else:
        evento_vuoto_quantistico_attivo = False  # Reset flag
        
        # Conversione tempo assoluto (adimensionale) in secondi fisici
        # Calibrazione dinamica basata sulla scala metrica del manifold
        # Il tempo caratteristico della scala è T ~ L/c dove L = 10^esponente metri
        
        # PROTEZIONE ANTI-OVERFLOW: Gestione sicura per esponenti estremi
        # Float64 supporta fino a 10^308, ma già 10^300 genera RuntimeWarning
        # Soluzione: limitiamo a ±100 (range da scala subatomica a cosmologica)
        c_luce = 299792458.0  # m/s
        
        if np.abs(esponente_visualizzato) > 100:
            # REGIME ESTREMO: Gestione esplicita con inf per evitare warning
            # Scale > 10^100 m (molto oltre orizzonte osservabile ~10^26 m)
            # Scale < 10^-100 m (molto sotto lunghezza di Planck ~10^-35 m)
            if esponente_visualizzato > 100:
                tempo_caratteristico = np.inf  # Scala cosmologica estrema → tempo infinito
            else:
                tempo_caratteristico = 0.0     # Scala quantistica estrema → tempo nullo
        else:
            # REGIME NORMALE: Calcolo standard senza overflow
            esponente_safe_time = esponente_visualizzato  # già nel range sicuro
            scala_metri = 10**esponente_safe_time
            tempo_caratteristico = scala_metri / c_luce  # tempo di attraversamento luce
        
        # Il tempo emergente è normalizzato rispetto al tempo caratteristico della scala
        tempo_fisico_sec = tempo_assoluto_adimensionale * tempo_caratteristico
        orologio_str = format_human_time(tempo_fisico_sec)
        
        # Classificazione dinamica dello stato
        if H_fisica > 0:
            direzione_tempo = "ESPANSIONE"
        elif H_fisica < 0:
            direzione_tempo = "CONTRAZIONE"
            
            # Logging inversione temporale
            if not args.playback and not evento_inversione_temporale_precedente:
                log_evento_visivo(
                    "INVERSIONE_TEMPORALE",
                    "Il parametro di Hubble è diventato negativo. Il manifold è in fase di contrazione retrocausale.",
                    tempo_emergente_cumulativo,
                    esponente_visualizzato,
                    H_fisica
                )
                evento_inversione_temporale_precedente = True
        else:
            direzione_tempo = "STASI"
            evento_inversione_temporale_precedente = False
        
        stato_cosmologico = f"{direzione_tempo} | TEMPO PROPRIO EMERGENTE"
    
    # === DISPLAY STRUTTURATO ===
    # Linea 1: Scala metrica e velocità di calcolo
    # Linea 2: OROLOGIO COSMOLOGICO (tempo emergente e fisico calibrato)
    # Linea 3: HUBBLE LOCALE (parametro di espansione/contrazione)
    # Linea 4: Costanti geometriche (G e Z)
    # Linea 5: Contorsione del manifold
    # Linea 6: Validazione topologica spinoriale
    text_info.set_text(
        f"SCALA METRICA: 10^({esponente_visualizzato:.2f}) m | VELOCITÀ CALCOLO: {vel_str}\n"
        f"OROLOGIO COSMOLOGICO: {tempo_leggibile} | TEMPO FISICO: {orologio_str}\n"
        f"HUBBLE LOCALE: {hubble_str}\n"
        f"G_GEO: {G_geometrica:.3e} | Z_GEO: {Z_geometrica:.3e}\n"
        f"CONTORSIONE K: {contorsione_k:.3e}\n"
        f"CHIUSURA SPINORE: {chiusura_spinore:.3e} (Δ da 4π)"
    )
    
    # Regime metrico e stato del sistema
    regime_descritto = ottieni_regime_metrico(esponente_visualizzato)
    text_regime.set_text(
        f"REGIME FISICO: {regime_descritto}\n"
        f"STATO: {stato_cosmologico}"
    )
    
    velocita_precedente = velocita_chi
    return scat_dx, scat_sx, linea_mat, linea_spa, linea_fft, linea_z, linea_g, linea_fractal

# --- 7. LOGICA DI ESECUZIONE ORCHESTRATA ---
if args.headless:
    # Logica di resume resiliente con ricerca dell'ultimo frame valido
    ultimo_frame_salvato = find_last_written_frame(file_data_path)
    start_frame = 0
    chunk_size = 2048
    
    if ultimo_frame_salvato > 0:
        # Arretriamo all'inizio del blocco chunk (64) per sovrascriverlo interamente.
        # Cura in modo trasparente i blocchi HDF5 compressi a metà (filter failure)
        start_frame = (ultimo_frame_salvato // chunk_size) * chunk_size
        
        if start_frame > 0:
            try:
                f_check = h5py.File(file_data_path, 'r', libver='latest', swmr=True)
            except OSError:
                f_check = h5py.File(file_data_path, 'r')
                
            with f_check:
                meta = f_check['telemetria_scalare'][start_frame - 1]
                stato_attuale = [meta['chi_lineare'], meta['v_chi']]
                lambda_affine_corrente = (start_frame - 1) * 0.1  # Parametro affine accumulato
                tempo_emergente_cumulativo = meta['tempo_assol'] * (meta['g_geo'] + 1e-43)  # Ricostruzione tempo emergente
                print(f"\n[RESUME RESILIENTE] Rilevato blocco interrotto. Arretramento al blocco sicuro: {start_frame}")
                print(f"[STATO RIPRISTINATO] Chi: {stato_attuale[0]:.4f} | V_Chi: {stato_attuale[1]:.4f}")
                print(f"[PARAMETRO AFFINE] \u03bb = {lambda_affine_corrente:.4f} | Tempo Emergente = {tempo_emergente_cumulativo:.6e}")

    if start_frame >= NUM_TOTAL_FRAMES:
        print(f"[COMPLETATO] Tutti i {NUM_TOTAL_FRAMES} frame già calcolati. Fine.")
        sys.exit(0)

    if start_frame == 0:
        print(f"\n[HEADLESS PRE-ALLOCATO] Avvio calcolo da frame 0.")

    print(f"[HEADLESS] Elaborazione da frame {start_frame} a {NUM_TOTAL_FRAMES}...")
    start_time = time.time()
    
    with h5py.File(file_data_path, 'a', libver='latest') as active_h5_file:
        try:
            active_h5_file.swmr_mode = True  
        except Exception:
            pass
            
        active_h5_file.id.set_mdc_config(active_h5_file.id.get_mdc_config())
        
        # --- CURA DEL CHUNK CORROTTO ---
        # Inserendo un chunk intero esatto bypassiamo la decompressione in lettura
        chunk_end = min(start_frame + chunk_size, NUM_TOTAL_FRAMES)
        if chunk_end - start_frame == chunk_size:
            zeri_scalari = np.zeros((chunk_size,), dtype=SCALARI_DTYPE)
            active_h5_file['telemetria_scalare'][start_frame:chunk_end] = zeri_scalari
        # -------------------------------
        
        for idx_frame in range(start_frame, NUM_TOTAL_FRAMES):
            update(idx_frame, target_file_handle=active_h5_file)
            
            if (idx_frame + 1) % chunk_size == 0 or idx_frame == NUM_TOTAL_FRAMES - 1:
                if idx_frame == NUM_TOTAL_FRAMES - 1:
                    flush_chunk_buffer(active_h5_file)
                active_h5_file.flush()
                elapsed = time.time() - start_time
                fps_calc = (idx_frame + 1 - start_frame) / max(elapsed, 0.001)
                print(f"[HEADLESS] Frame {idx_frame+1}/{NUM_TOTAL_FRAMES} | {elapsed/60:.2f} min | {fps_calc:.1f} fps")
                
    print("\n[HEADLESS] ✓ Calcolo cumulativo completato con successo.")
    
    # Chiudi file di log stabilità
    if log_stabilita_file is not None:
        log_stabilita_file.write("=" * 80 + "\n")
        log_stabilita_file.write(f"Fine simulazione: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_stabilita_file.write("=" * 80 + "\n")
        log_stabilita_file.close()
        print(f"[LOG STABILITÀ] File salvato in: {log_stabilita_path}")
    
elif args.playback:
    print("\n[PLAYBACK HDF5] Analisi dell'albero binario in corso...")
    
    # Rileva dinamicamente i frame REALMENTE scritti tramite la telemetria
    max_frame = find_last_written_frame(file_data_path)
    
    if max_frame < 0:
        print("[AVVISO] Il file dati HDF5 è vuoto o corrotto."); max_frame = 0
    else:
        print(f"[PLAYBACK] Rilevati {max_frame + 1} frame geometrici pronti nel file HDF5.")
    
    if args.film:
        frames_dir = f"frames_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(frames_dir, exist_ok=True)
        print(f"[PLAYBACK -> VIDEO] Rendering offline da HDF5. Salvataggio in: {frames_dir}")
        
        for idx_frame in range(max_frame + 1):
            update(idx_frame)
            fig.savefig(os.path.join(frames_dir, f"frame_{idx_frame:05d}.png"), dpi=100, facecolor='#020617')
            if (idx_frame + 1) % 10 == 0:
                print(f"[PLAYBACK] Renderizzato Frame: {idx_frame+1}/{max_frame + 1}")
                
        print(f"\n[ASSEMBLAGGIO] Innesco automatico FFmpeg in sub-processo...")
        output_filename = args.output if args.output else f"manifold_dal_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        input_pattern = os.path.join(frames_dir, 'frame_%05d.png').replace("\\", "/")
        
        import subprocess
        ffmpeg_cmd = ['ffmpeg', '-y', '-framerate', str(args.fps), '-i', input_pattern, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'fast', output_filename]
        try:
            risultato = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if risultato.returncode == 0: print(f"[FILMATO] ✓ Video compilato con successo: {output_filename}")
            else: print(f"[ERRORE] FFmpeg ha fallito:\\n{risultato.stderr}")
        except FileNotFoundError: print("[ERRORE] Eseguibile 'ffmpeg' non trovato nel PATH.")
    else:
        print("[PLAYBACK -> APPLICATIVA] Avvio interfaccia interattiva asincrona on-demand.")
        
        animazione_in_esecuzione = True  # Avvio automatico abilitato
        frame_corrente_db = 0
        
        scale_velocita = [1, 5, 10, 100, 1000]
        
        if args.speed in scale_velocita:
            indice_velocita = scale_velocita.index(args.speed)
        else:
            print(f"[AVVISO] Velocità {args.speed}x non standard. La aggiungo alle opzioni.")
            scale_velocita.append(args.speed)
            indice_velocita = len(scale_velocita) - 1
        sys._wqt_step = scale_velocita[indice_velocita]
        
        ultimo_frame_renderizzato = -1
        
        def update_playback_dinamico(f_step):
            global frame_corrente_db, max_frame, ultimo_frame_renderizzato, f_playback_handle
            
            if animazione_in_esecuzione:
                prossimo_frame = frame_corrente_db + sys._wqt_step
                
                # Aggiorniamo il traguardo massimo live solo se stiamo per superarlo
                if prossimo_frame > max_frame:
                    nuovo_max = find_last_written_frame(file_data_path, handle=f_playback_handle)
                    if nuovo_max > max_frame:
                        max_frame = nuovo_max
                        
                if prossimo_frame <= max_frame:
                    frame_corrente_db = prossimo_frame
                else:
                    frame_corrente_db = max_frame
                    
            # Se siamo fermi sullo stesso frame (in attesa o in pausa), non stressiamo il disco
            if frame_corrente_db == ultimo_frame_renderizzato:
                if animazione_in_esecuzione and frame_corrente_db == max_frame:
                    text_regime.set_text(f"⏳ IN ATTESA DAL PRODUTTORE... (Buffer fermo a {max_frame})")
                return scat_dx, scat_sx, linea_mat, linea_spa, linea_fft, linea_z, linea_g, linea_fractal
                
            ultimo_frame_renderizzato = frame_corrente_db
            return update(frame_corrente_db)

        ax_btn_play = fig.add_axes([0.40, 0.04, 0.08, 0.04])
        ax_btn_ff = fig.add_axes([0.50, 0.04, 0.08, 0.04])
        
        btn_play = Button(ax_btn_play, 'PAUSE', color='#dc2626', hovercolor='#b91c1c')
        btn_play.label.set_color('white'); btn_play.label.set_weight('bold')
        
        btn_ff = Button(ax_btn_ff, 'FF >>', color='#1e293b', hovercolor='#334155')
        btn_ff.label.set_color('#94a3b8'); btn_ff.label.set_weight('bold')

        if sys._wqt_step != 1:
            btn_ff.label.set_text(f"FF {sys._wqt_step}x")
            btn_ff.ax.set_facecolor('#3b82f6')
            btn_ff.label.set_color('white')

        def toggle_playback(e):
            global animazione_in_esecuzione
            animazione_in_esecuzione = not animazione_in_esecuzione
            btn_play.label.set_text("PAUSE" if animazione_in_esecuzione else "PLAY")
            btn_play.ax.set_facecolor('#dc2626' if animazione_in_esecuzione else '#16a34a')
            if animazione_in_esecuzione:
                ani.event_source.start()
            else:
                ani.event_source.stop()

        def toggle_fast_forward(e):
            global indice_velocita
            indice_velocita = (indice_velocita + 1) % len(scale_velocita)
            sys._wqt_step = scale_velocita[indice_velocita]
            
            if sys._wqt_step == 1:
                btn_ff.label.set_text("FF >>")
                btn_ff.ax.set_facecolor('#1e293b')
                btn_ff.label.set_color('#94a3b8')
            else:
                btn_ff.label.set_text(f"FF {sys._wqt_step}x")
                btn_ff.ax.set_facecolor('#3b82f6')  
                btn_ff.label.set_color('white')
            fig.canvas.draw_idle()

        btn_play.on_clicked(toggle_playback)
        btn_ff.on_clicked(toggle_fast_forward)
        
        ani = FuncAnimation(
            fig, 
            update_playback_dinamico, 
            interval=40, 
            blit=False,
            cache_frame_data=False,
            save_count=999999
        )
        # ani.event_source.stop() rimosso per permettere avvio immediato
        plt.show()

elif args.film:
    num_frames = args.fps * args.duration
    frames_dir = f"frames_calcolo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(frames_dir, exist_ok=True)
    print(f"\n[FILMATO] Calcolo e rendering combinati avviati. Salvataggio in: {frames_dir}")
    
    with h5py.File(file_data_path, 'a', libver='latest') as active_film_h5:
        for idx_frame in range(num_frames):
            update(idx_frame, target_file_handle=active_film_h5)
            fig.savefig(os.path.join(frames_dir, f"frame_{idx_frame:05d}.png"), dpi=100, facecolor='#020617')
            if (idx_frame + 1) % 10 == 0:
                print(f"[FILMATO] Calcolato e renderizzato Frame: {idx_frame+1}/{num_frames}")
                
        flush_chunk_buffer(active_film_h5)
            
    print(f"\\n[ASSEMBLAGGIO] Innesco automatico FFmpeg in sub-processo...")
    output_filename = args.output if args.output else f"manifold_calcolato_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    input_pattern = os.path.join(frames_dir, 'frame_%05d.png').replace("\\\\", "/")
    
    import subprocess
    ffmpeg_cmd = ['ffmpeg', '-y', '-framerate', str(args.fps), '-i', input_pattern, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'fast', output_filename]
    try:
        risultato = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if risultato.returncode == 0: print(f"[FILMATO] ✓ Video compilato con successo: {output_filename}")
        else: print(f"[ERRORE] FFmpeg ha fallito:\\n{risultato.stderr}")
    except FileNotFoundError: print("[ERRORE] Eseguibile 'ffmpeg' non trovato nel PATH.")
    
    # Chiudi file di log stabilità
    if log_stabilita_file is not None:
        log_stabilita_file.write("=" * 80 + "\n")
        log_stabilita_file.write(f"Fine simulazione: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_stabilita_file.write("=" * 80 + "\n")
        log_stabilita_file.close()
        print(f"[LOG STABILITÀ] File salvato in: {log_stabilita_path}")

else:
    ax_btn = fig.add_axes([0.45, 0.04, 0.1, 0.04])
    btn = Button(ax_btn, 'PLAY', color='#16a34a', hovercolor='#15803d')
    btn.label.set_color('white'); btn.label.set_weight('bold')

    def toggle(e):
        global animazione_in_esecuzione
        animazione_in_esecuzione = not animazione_in_esecuzione
        btn.label.set_text("PAUSE" if animazione_in_esecuzione else "PLAY")
        btn.ax.set_facecolor('#dc2626' if animazione_in_esecuzione else '#16a34a')

    btn.on_clicked(toggle)
    ani = FuncAnimation(fig, update, frames=200, interval=50, blit=False)
    plt.show()