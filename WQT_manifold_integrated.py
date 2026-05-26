"""
================================================================================
WQT MANIFOLD - VERSIONE INTEGRATA COMPLETA
================================================================================

ARCHITETTURA IBRIDA:
--------------------
✅ Nucleo: Oggetti dinamici (ManifoldBase) con solitoni topologici
✅ Visualizzazione: 3D real-time con matplotlib (compatibile con originale)
✅ Telemetria: HDF5 completo (backward compatible)
✅ Modalità: headless, playback, film, interattivo
✅ Fisica: Einstein-Cartan con torsione quantizzata

FUNZIONALITÀ COMPLETE:
----------------------
1. Simulazione real-time con animazione 3D
2. Modalità headless per calcolo parallelo HPC
3. Playback da file HDF5 con controlli interattivi
4. Generazione filmati MP4 automatica
5. Telemetria dettagliata multi-livello
6. Compatibilità backward con script di analisi esistenti

================================================================================
"""

import os
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

import numpy as np
import sys
import argparse
from datetime import datetime
import time
import h5py
import multiprocessing as mp
from multiprocessing import Pool
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# Intercettazione headless precoce
if '--headless' in sys.argv:
    import matplotlib
    matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d import Axes3D

# ============================================================================
# PARSING ARGOMENTI
# ============================================================================

parser = argparse.ArgumentParser(description='Simulazione WQT integrata: oggetti dinamici + visualizzazione completa')
parser.add_argument('--film', action='store_true', help='Salva frame e compila filmato MP4')
parser.add_argument('--playback', action='store_true', help='Rendering da file HDF5')
parser.add_argument('--headless', action='store_true', help='Solo calcolo numerico e scrittura HDF5')
parser.add_argument('--output', type=str, default=None, help='Nome file MP4')
parser.add_argument('--fps', type=int, default=24, help='Frame per secondo (default: 24)')
parser.add_argument('--duration', type=int, default=15, help='Durata filmato in secondi (default: 15)')
parser.add_argument('--db', type=str, default='geometrodinamica_integrated.h5', help='File dati HDF5')
parser.add_argument('--speed', type=int, default=1, help='Velocità playback')
parser.add_argument('--n-manifold', type=int, default=10, help='Numero manifold iniziali')
parser.add_argument('--cores', type=int, default=None, help='Numero core CPU (None=tutti)')
args = parser.parse_args()

NUM_TOTAL_FRAMES = args.fps * args.duration

# ============================================================================
# COSTANTI FISICHE
# ============================================================================

# Costanti fisiche fondamentali
LUNGHEZZA_PLANCK = 1.616255e-35
TEMPO_PLANCK = 5.391247e-44

# Parametri geometrici (DA ORIGINALE WQT_manifold.py)
N_u = 6  # Numero di sezioni trasversali del toro
u = np.linspace(0, 2 * np.pi, N_u)  # Coordinate angolari trasversali
N_SEGMENTI = 24  # segmenti_frattali
RISOLUZIONE_RENDERING = 2400  # risoluzione_base
ACCORCIAMENTO_ANGOLARE = 1.0 / (4.0 * np.pi)
COEFFICIENTE_ACCOPPIAMENTO = float(N_SEGMENTI) / float(RISOLUZIONE_RENDERING)

# Parametri dinamici
TORSIONE_CRITICA = 4.0 * np.pi
RISONANZA_MINIMA = 0.5
LAMBDA_DOPPIO_POZZO = 0.5

# ============================================================================
# CLASSE MANIFOLDBASE (Nucleo Refactorato)
# ============================================================================

@dataclass
class ManifoldBase:
    """Solitone topologico con 24 segmenti e torsione 4π."""
    
    chi: np.ndarray = field(default_factory=lambda: np.zeros(N_SEGMENTI))
    vel: np.ndarray = field(default_factory=lambda: np.zeros(N_SEGMENTI))
    torsione: float = 0.0
    posizione: np.ndarray = field(default_factory=lambda: np.zeros(3))
    id_manifold: int = 0
    generazione: int = 0
    
    def __post_init__(self):
        """Inizializza con chiralità alternata."""
        if np.allclose(self.chi, 0.0):
            chiralita = np.array([(-1)**(i) for i in range(N_SEGMENTI)])
            self.chi = 1e-3 * chiralita * np.abs(np.random.randn(N_SEGMENTI))  # Forza segno corretto
            self.vel = np.zeros(N_SEGMENTI)
    
    def calcola_torsione_totale(self) -> float:
        """Calcola ∮ K ds dalla derivata discreta di χ."""
        # Torsione = contributo gradiente + contributo ampiezza
        delta_chi = np.diff(self.chi, append=self.chi[0])
        gradiente = np.sum(np.abs(delta_chi))
        ampiezza = np.linalg.norm(self.chi)  # Norma L2 del campo
        self.torsione = gradiente + 0.5 * ampiezza  # Mix dei due contributi
        return self.torsione
    
    def check_saturazione(self) -> bool:
        """Verifica se τ > 4π (fissione richiesta)."""
        self.calcola_torsione_totale()
        return self.torsione > (1.01 * TORSIONE_CRITICA)
    
    def calcola_accoppiamento(self, other: 'ManifoldBase') -> float:
        """Accoppiamento emergente = correlazione × decadimento spaziale."""
        distanza = np.linalg.norm(self.posizione - other.posizione)
        norma_self = np.linalg.norm(self.chi) + 1e-12
        norma_other = np.linalg.norm(other.chi) + 1e-12
        correlazione = np.dot(self.chi, other.chi) / (norma_self * norma_other)
        chi_medio = 0.5 * (np.mean(np.abs(self.chi)) + np.mean(np.abs(other.chi)))
        scala = chi_medio * LUNGHEZZA_PLANCK
        decadimento = np.exp(-distanza / (scala + 1e-30))
        return correlazione * decadimento
    
    def congiungi(self, other: 'ManifoldBase') -> 'ManifoldBase':
        """Fusione topologica: χ_nuovo = (χ_A + χ_B)/2."""
        chi_nuovo = (self.chi + other.chi) / 2.0
        vel_nuovo = (self.vel + other.vel) / 2.0
        peso_self = np.linalg.norm(self.chi) + 1e-12
        peso_other = np.linalg.norm(other.chi) + 1e-12
        peso_totale = peso_self + peso_other
        posizione_nuova = (self.posizione * peso_self + other.posizione * peso_other) / peso_totale
        id_nuovo = self.id_manifold + other.id_manifold
        gen_nuova = max(self.generazione, other.generazione) + 1
        m_fuso = ManifoldBase(
            chi=chi_nuovo, vel=vel_nuovo, torsione=0.0,
            posizione=posizione_nuova, id_manifold=id_nuovo, generazione=gen_nuova
        )
        m_fuso.calcola_torsione_totale()
        return m_fuso
    
    def fissione(self) -> Tuple['ManifoldBase', 'ManifoldBase']:
        """Mitosi topologica: divide in 2 manifold con τ ≈ 2π ciascuno."""
        # Strategia: ogni figlio prende una metà e la interpola smooth per 24 segmenti
        fattore_norm = 0.7  # Riduzione ampiezza (conservazione energia approssimata)
        
        # Metà A: segmenti 0-11 interpolati su 24 posizioni
        indici_A = np.linspace(0, 11, N_SEGMENTI, dtype=int)
        chi_A = fattore_norm * self.chi[indici_A]
        vel_A = fattore_norm * self.vel[indici_A]
        
        # Metà B: segmenti 12-23 interpolati su 24 posizioni
        indici_B = np.linspace(12, 23, N_SEGMENTI, dtype=int)
        chi_B = fattore_norm * self.chi[indici_B]
        vel_B = fattore_norm * self.vel[indici_B]
        
        # Separazione spaziale
        scala_sep = np.mean(np.abs(self.chi)) * LUNGHEZZA_PLANCK
        theta = 2.0 * np.pi * np.random.rand()
        phi = np.arccos(2.0 * np.random.rand() - 1.0)
        direzione = np.array([
            np.sin(phi) * np.cos(theta),
            np.sin(phi) * np.sin(theta),
            np.cos(phi)
        ])
        
        pos_A = self.posizione - 0.5 * scala_sep * direzione
        pos_B = self.posizione + 0.5 * scala_sep * direzione
        
        m_A = ManifoldBase(chi=chi_A, vel=vel_A, torsione=0.0, posizione=pos_A,
                          id_manifold=2*self.id_manifold, generazione=self.generazione+1)
        m_B = ManifoldBase(chi=chi_B, vel=vel_B, torsione=0.0, posizione=pos_B,
                          id_manifold=2*self.id_manifold+1, generazione=self.generazione+1)
        
        m_A.calcola_torsione_totale()
        m_B.calcola_torsione_totale()
        return m_A, m_B
    
    def evolvi_locale(self, dt: float) -> None:
        """Velocity Verlet simplectico: dχ/dτ = v, dv/dτ = -∂V/∂χ + A·χ."""
        # Matrice accoppiamento
        A = np.zeros((N_SEGMENTI, N_SEGMENTI))
        for i in range(N_SEGMENTI):
            for j in range(N_SEGMENTI):
                if i != j:
                    dist_min = min(abs(i - j), N_SEGMENTI - abs(i - j))
                    A[i, j] = 0.1 * np.exp(-dist_min / 3.0)  # Ridotto per stabilità
        
        # Forze: -dV/dχ = λχ - χ³
        forza_pot = LAMBDA_DOPPIO_POZZO * self.chi - self.chi**3
        forza_acopp = A @ self.chi
        accel = forza_pot + forza_acopp
        
        # Velocity Verlet
        self.chi = self.chi + self.vel * dt + 0.5 * accel * dt**2
        
        # Ricalcola accel al nuovo chi
        forza_pot_new = LAMBDA_DOPPIO_POZZO * self.chi - self.chi**3
        forza_acopp_new = A @ self.chi
        accel_new = forza_pot_new + forza_acopp_new
        
        self.vel = self.vel + 0.5 * (accel + accel_new) * dt
        self.calcola_torsione_totale()


# ============================================================================
# GENERAZIONE GEOMETRIA 3D (Compatibilità con Rendering Originale)
# ============================================================================

def genera_mappatura_da_manifold(manifold: ManifoldBase, frame: int):
    """
    Genera geometria 3D (Xdx, Ydx, Zdx, Xsx, Ysx, Zsx) da un ManifoldBase.
    
    Compatibile con il sistema di rendering originale.
    Usa il profilo χ del manifold per creare le superfici DX (spazio) e SX (materia).
    
    IMPORTANTE: Restituisce coordinate in UNITÀ DI PLANCK (normalizzate)
    """
    # Usa media di χ come parametro di scala globale
    chi_medio = np.mean(manifold.chi)
    
    # Saturazione tanh per evitare divergenze
    chi_sat = 150.0 * np.tanh(chi_medio / 150.0)
    
    # Fattori chirali fondamentali
    f_dx = np.exp(+chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    f_sx = np.exp(-chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    
    # Generazione reticolo angolare
    th = np.linspace(0, 2 * np.pi, RISOLUZIONE_RENDERING)
    
    # Chiralità alternata
    chiralita = np.where(np.arange(RISOLUZIONE_RENDERING) % 2 == 0, 1.0, -1.0)
    
    # Argomenti torsionali
    arg_dx = (4 * np.pi / RISOLUZIONE_RENDERING) * f_dx / (1.0 + chi_sat**2)
    arg_sx = (4 * np.pi / RISOLUZIONE_RENDERING) * f_sx
    
    # Componenti di torsione
    tor_dx = np.sinh(chiralita * arg_dx)
    tor_sx = np.sinh(chiralita * arg_sx)
    
    # Raggi conformi IN UNITÀ DI PLANCK (normalizzato!)
    r_conforme_metri = float(N_SEGMENTI) * ACCORCIAMENTO_ANGOLARE * np.exp(chi_sat * COEFFICIENTE_ACCOPPIAMENTO)
    r_conforme_metri = np.maximum(r_conforme_metri, 1.0 * LUNGHEZZA_PLANCK)
    
    # NORMALIZZA in unità di Planck per rendering
    r_conforme = r_conforme_metri / LUNGHEZZA_PLANCK
    
    # Coordinate 3D (proiezione stereografica) - GIÀ IN UNITÀ NORMALIZZATE
    Xdx = r_conforme * np.cos(th) * (1.0 + 0.5 * tor_dx / np.max(np.abs(tor_dx) + 1e-9))
    Ydx = r_conforme * np.sin(th) * (1.0 + 0.5 * tor_dx / np.max(np.abs(tor_dx) + 1e-9))
    Zdx = tor_dx * r_conforme * 0.3
    
    Xsx = r_conforme * np.cos(th) * (1.0 - 0.5 * tor_sx / np.max(np.abs(tor_sx) + 1e-9))
    Ysx = r_conforme * np.sin(th) * (1.0 - 0.5 * tor_sx / np.max(np.abs(tor_sx) + 1e-9))
    Zsx = -tor_sx * r_conforme * 0.3
    
    return Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, r_conforme, th, tor_dx, tor_sx


# ============================================================================
# PARALLELIZZAZIONE
# ============================================================================

def evolvi_manifold_parallelo(manifold: ManifoldBase, dt: float) -> ManifoldBase:
    """Wrapper per pool.starmap()."""
    manifold.evolvi_locale(dt)
    return manifold

def evolvi_sistema_parallelo(lista: List[ManifoldBase], dt: float, 
                             n_cores: Optional[int] = None) -> List[ManifoldBase]:
    """Evoluzione parallela su multi-core."""
    if n_cores is None:
        n_cores = mp.cpu_count()
    
    if len(lista) <= 1 or n_cores == 1:
        for m in lista:
            m.evolvi_locale(dt)
        return lista
    
    with Pool(processes=n_cores) as pool:
        lista_evoluti = pool.starmap(evolvi_manifold_parallelo, [(m, dt) for m in lista])
    
    return lista_evoluti

def trova_coppie_candidate(lista: List[ManifoldBase], raggio: float) -> List[Tuple[int, int]]:
    """Collision detection O(N²) naive."""
    coppie = []
    N = len(lista)
    for i in range(N):
        for j in range(i + 1, N):
            dist = np.linalg.norm(lista[i].posizione - lista[j].posizione)
            if dist < raggio:
                acopp = lista[i].calcola_accoppiamento(lista[j])
                if np.abs(acopp) > RISONANZA_MINIMA:
                    coppie.append((i, j))
    return coppie

def gestisci_congiunzioni(lista: List[ManifoldBase], raggio: float) -> List[ManifoldBase]:
    """Fusioni tra manifold compatibili."""
    coppie = trova_coppie_candidate(lista, raggio)
    fusi = set()
    nuovi = []
    
    for i, j in coppie:
        if i in fusi or j in fusi:
            continue
        
        m_i, m_j = lista[i], lista[j]
        somma_chi = m_i.chi + m_j.chi
        norma_somma = np.linalg.norm(somma_chi)
        norma_media = 0.5 * (np.linalg.norm(m_i.chi) + np.linalg.norm(m_j.chi))
        
        if norma_somma < 0.5 * norma_media:
            nuovi.append(m_i.congiungi(m_j))
            fusi.add(i)
            fusi.add(j)
    
    return [m for idx, m in enumerate(lista) if idx not in fusi] + nuovi

def gestisci_fissioni(lista: List[ManifoldBase]) -> List[ManifoldBase]:
    """Mitosi dei manifold saturi."""
    nuovi = []
    da_rimuovere = set()
    
    for idx, m in enumerate(lista):
        if m.check_saturazione():
            m_A, m_B = m.fissione()
            nuovi.append(m_A)
            nuovi.append(m_B)
            da_rimuovere.add(idx)
    
    return [m for idx, m in enumerate(lista) if idx not in da_rimuovere] + nuovi


# ============================================================================
# HDF5 TELEMETRIA (Compatibilità Backward)
# ============================================================================

SCALARI_DTYPE = np.dtype([
    ('frame_id', 'i8'),
    ('rm', 'f8'),
    ('chi_medio', 'f8'),
    ('v_chi_medio', 'f8'),
    ('torsione_media', 'f8'),
    ('n_manifold', 'i8'),
    ('energia_totale', 'f8'),
    ('generazione_max', 'i8')
])

def inizializza_hdf5(file_path: str, n_frames: int):
    """Crea file HDF5 pre-allocato."""
    if os.path.exists(file_path):
        return
    
    with h5py.File(file_path, 'w') as f:
        f.attrs['creato_il'] = datetime.now().isoformat()
        f.attrs['num_total_frames'] = n_frames
        f.attrs['architettura'] = 'integrata_oggetti_dinamici'
        
        f.create_dataset('telemetria_scalare', shape=(n_frames,), maxshape=(None,),
                        dtype=SCALARI_DTYPE, chunks=(2048,))

def salva_frame_hdf5(f_handle, frame: int, lista_manifold: List[ManifoldBase]):
    """Salva stato corrente nel frame specificato."""
    # Calcola aggregati
    n_manifold = len(lista_manifold)
    
    if n_manifold == 0:
        return
    
    chi_medio = np.mean([np.mean(m.chi) for m in lista_manifold])
    v_chi_medio = np.mean([np.mean(m.vel) for m in lista_manifold])
    torsione_media = np.mean([m.torsione for m in lista_manifold])
    generazione_max = max([m.generazione for m in lista_manifold])
    
    # Calcola rm medio (dalla geometria del primo manifold come rappresentante)
    m_rappresentante = lista_manifold[0]
    Xdx, Ydx, Zdx, _, _, _, rm, _, _, _ = genera_mappatura_da_manifold(m_rappresentante, frame)
    
    # Energia totale
    energia_totale = 0.0
    for m in lista_manifold:
        E_cin = 0.5 * np.sum(m.vel**2)
        E_pot = np.sum(-0.5 * LAMBDA_DOPPIO_POZZO * m.chi**2 + 0.25 * m.chi**4)
        energia_totale += E_cin + E_pot
    
    # Scrivi record
    record = np.array(
        (frame, rm, chi_medio, v_chi_medio, torsione_media, n_manifold, energia_totale, generazione_max),
        dtype=SCALARI_DTYPE
    )
    
    f_handle['telemetria_scalare'][frame] = record


# ============================================================================
# VISUALIZZAZIONE 3D (Compatibile con Originale)
# ============================================================================

# Setup figura globale
if not args.headless:
    fig = plt.figure(figsize=(18, 10), facecolor='#020617')
    
    # Layout compatibile: usa (10, 2) per permettere subplot (5, 2) laterali
    # 1 grande 3D + 5 subplot laterali (MULTI-SCALA)
    ax_3d = fig.add_subplot(10, 2, (1, 15), projection='3d', facecolor='#0a0e27')
    ax_torsione = fig.add_subplot(10, 2, 2, facecolor='#0a0e27')
    ax_popolazione = fig.add_subplot(10, 2, 4, facecolor='#0a0e27')
    ax_energia = fig.add_subplot(10, 2, 6, facecolor='#0a0e27')
    ax_generazione = fig.add_subplot(10, 2, 8, facecolor='#0a0e27')
    ax_distribuzione = fig.add_subplot(10, 2, 10, facecolor='#0a0e27')  # Nuovo: distribuzione generazioni
    
    # Plot objects (saranno riempiti durante animazione)
    scat_dx = None
    scat_sx = None
    linee_torsione = None
    linee_popolazione = None
    linee_energia = None
    linee_generazione = None
    
    # Buffer dati per plot temporali
    buffer_torsione = []
    buffer_popolazione = []
    buffer_energia = []
    buffer_generazione = []
    
    # Palette colori per generazioni (MULTI-SCALA)
    # Gen 0: rosso, Gen 1: arancione, Gen 2: giallo, Gen 3: verde, Gen 4+: blu/viola
    COLORI_GENERAZIONE = {
        0: '#FF3333',  # Rosso brillante (primordiali)
        1: '#FF8C00',  # Arancione (prima generazione)
        2: '#FFD700',  # Oro (seconda generazione)
        3: '#32CD32',  # Verde lime (terza generazione)
        4: '#1E90FF',  # Blu dodger (quarta generazione)
        5: '#9370DB',  # Viola medio (quinta generazione)
    }
    
    # Scale di riferimento spaziali
    SCALA_PLANCK = LUNGHEZZA_PLANCK
    SCALA_ATOMICA = 1e-10  # 1 Angstrom
    SCALA_NUCLEARE = 1e-15  # 1 femtometro


def aggiorna_visualizzazione(frame: int, lista_manifold: List[ManifoldBase]):
    """
    Aggiorna tutti i plot per il frame corrente.
    Compatibile con FuncAnimation.
    
    IMPORTANTE: Genera UNA SOLA geometria toroidale aggregando TUTTI i manifold!
    """
    global scat_dx, scat_sx, linee_torsione, linee_popolazione, linee_energia, linee_generazione
    global buffer_torsione, buffer_popolazione, buffer_energia, buffer_generazione
    
    if len(lista_manifold) == 0:
        return
    
    # ========================================================================
    # AGGREGAZIONE: Combina tutti i manifold in un unico campo χ[24]
    # ========================================================================
    # Strategia: Media pesata dei campi χ di tutti i manifold
    # Peso: basato sulla torsione (manifold con più torsione influenzano di più)
    
    chi_aggregato = np.zeros(N_SEGMENTI)
    peso_totale = 0.0
    
    for m in lista_manifold:
        # Peso: usa torsione + 1 per evitare divisione per zero
        peso = m.torsione + 1.0
        chi_aggregato += m.chi * peso
        peso_totale += peso
    
    # Normalizza per ottenere media pesata
    if peso_totale > 0:
        chi_aggregato /= peso_totale
    
    # Genera UNA SOLA geometria 3D dal campo aggregato
    # Passa chi_aggregato come se fosse un singolo manifold rappresentativo
    manifold_virtuale = ManifoldBase(chi=chi_aggregato, torsione=np.mean([m.torsione for m in lista_manifold]))
    Xdx, Ydx, Zdx, Xsx, Ysx, Zsx, rm, th, tor_dx, tor_sx = genera_mappatura_da_manifold(
        manifold_virtuale, frame
    )
    
    # ========================================================================
    # PLOT 3D: UNA SOLA GEOMETRIA TOROIDALE (come originale)
    # ========================================================================
    ax_3d.cla()
    ax_3d.set_facecolor('#0a0e27')
    
    # Colori basati sulla generazione MEDIA del sistema
    gen_media = np.mean([m.generazione for m in lista_manifold])
    
    if gen_media < 0.5:
        # Primordiali: cyan/magenta classici
        color_dx, color_sx = 'cyan', 'magenta'
        alpha_val = 0.6
    elif gen_media < 1.5:
        # Prima generazione: oro/arancione
        color_dx, color_sx = '#FFD700', '#FF8C00'
        alpha_val = 0.5
    else:
        # Generazioni avanzate: verde/blu
        color_dx, color_sx = '#32CD32', '#1E90FF'
        alpha_val = 0.4
    
    # Plot superfici DX e SX
    scat_dx = ax_3d.scatter(Xdx, Ydx, Zdx, c=color_dx, s=1, alpha=alpha_val, label='Spazio (DX)')
    scat_sx = ax_3d.scatter(Xsx, Ysx, Zsx, c=color_sx, s=1.5, alpha=alpha_val+0.1, label='Materia (SX)')
    
    # Titolo e assi
    ax_3d.set_xlabel('X [L_P]', color='white', fontsize=9)
    ax_3d.set_ylabel('Y [L_P]', color='white', fontsize=9)
    ax_3d.set_zlabel('Z [L_P]', color='white', fontsize=9)
    
    # Conta generazioni per info
    gen_counts = {}
    for m in lista_manifold:
        gen_counts[m.generazione] = gen_counts.get(m.generazione, 0) + 1
    gen_str = ', '.join([f'G{g}:{n}' for g, n in sorted(gen_counts.items())])
    
    ax_3d.set_title(f'Frame {frame} | N={len(lista_manifold)} [{gen_str}] | Gen_med={gen_media:.1f}', 
                    color='white', fontsize=11, fontweight='bold')
    
    # Legenda semplice (geometria aggregata)
    ax_3d.legend(loc='upper right', fontsize=9)
    ax_3d.tick_params(colors='white', labelsize=8)
    
    # INDICATORI DI SCALA (MULTI-SCALA)
    # Aggiungi testo informativo con riferimenti di scala fisica
    # Calcola scala media dei manifold presenti
    if len(lista_manifold) > 0:
        scala_media = np.mean([np.linalg.norm(m.posizione) for m in lista_manifold])
        
        # Testo con scala corrente e riferimenti fisici
        info_scala = f"Scala simulazione: {scala_media/LUNGHEZZA_PLANCK:.1f} L_P\n"
        info_scala += f"L_Planck = {LUNGHEZZA_PLANCK:.2e} m\n"
        
        # Aggiungi riferimenti di scala se rilevanti
        if scala_media < SCALA_NUCLEARE:
            info_scala += f"< Scala nucleare ({SCALA_NUCLEARE:.0e} m)"
        elif scala_media < SCALA_ATOMICA:
            info_scala += f"< Scala atomica ({SCALA_ATOMICA:.0e} m)"
        else:
            info_scala += f"> Scala atomica"
        
        # Posiziona testo in basso a sinistra
        ax_3d.text2D(0.02, 0.02, info_scala, transform=ax_3d.transAxes,
                    fontsize=7, color='yellow', alpha=0.7, 
                    verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
    
    # Aggiungi metriche ai buffer
    torsione_media = np.mean([m.torsione for m in lista_manifold])
    n_manifold = len(lista_manifold)
    energia_totale = sum([0.5 * np.sum(m.vel**2) + np.sum(-0.5 * LAMBDA_DOPPIO_POZZO * m.chi**2 + 0.25 * m.chi**4) for m in lista_manifold])
    gen_max = max([m.generazione for m in lista_manifold])
    
    buffer_torsione.append(torsione_media)
    buffer_popolazione.append(n_manifold)
    buffer_energia.append(energia_totale)
    buffer_generazione.append(gen_max)
    
    # Limita buffer a ultimi 100 frame
    if len(buffer_torsione) > 100:
        buffer_torsione.pop(0)
        buffer_popolazione.pop(0)
        buffer_energia.pop(0)
        buffer_generazione.pop(0)
    
    # Plot torsione
    ax_torsione.cla()
    ax_torsione.plot(buffer_torsione, color='green', linewidth=2)
    ax_torsione.axhline(TORSIONE_CRITICA, color='red', linestyle='--', label='Soglia 4π')
    ax_torsione.set_ylabel('<τ>', color='white')
    ax_torsione.set_title('Torsione Media', color='white', fontsize=10)
    ax_torsione.set_facecolor('#0a0e27')
    ax_torsione.tick_params(colors='white')
    ax_torsione.legend(fontsize=8, loc='upper right')
    ax_torsione.grid(True, alpha=0.3)
    
    # Plot popolazione
    ax_popolazione.cla()
    ax_popolazione.plot(buffer_popolazione, color='blue', linewidth=2)
    ax_popolazione.set_ylabel('N(t)', color='white')
    ax_popolazione.set_title('Popolazione Manifold', color='white', fontsize=10)
    ax_popolazione.set_facecolor('#0a0e27')
    ax_popolazione.tick_params(colors='white')
    ax_popolazione.grid(True, alpha=0.3)
    
    # Plot energia
    ax_energia.cla()
    ax_energia.plot(buffer_energia, color='purple', linewidth=2)
    ax_energia.set_ylabel('E_tot', color='white')
    ax_energia.set_title('Energia Totale', color='white', fontsize=10)
    ax_energia.set_facecolor('#0a0e27')
    ax_energia.tick_params(colors='white')
    ax_energia.grid(True, alpha=0.3)
    
    # Plot generazione massima
    ax_generazione.cla()
    ax_generazione.plot(buffer_generazione, color='orange', linewidth=2)
    ax_generazione.set_ylabel('Gen_max', color='white', fontsize=9)
    ax_generazione.set_title('Generazione Massima', color='white', fontsize=10)
    ax_generazione.set_facecolor('#0a0e27')
    ax_generazione.tick_params(colors='white', labelsize=8)
    ax_generazione.grid(True, alpha=0.3)
    
    # Nuovo subplot: DISTRIBUZIONE GENERAZIONI (MULTI-SCALA)
    ax_distribuzione.cla()
    
    # Conta manifold per generazione
    gen_counts = {}
    for m in lista_manifold:
        gen_counts[m.generazione] = gen_counts.get(m.generazione, 0) + 1
    
    if gen_counts:
        generazioni = sorted(gen_counts.keys())
        conteggi = [gen_counts[g] for g in generazioni]
        colori_barre = [COLORI_GENERAZIONE.get(g, '#9370DB') for g in generazioni]
        
        bars = ax_distribuzione.bar(generazioni, conteggi, color=colori_barre, 
                                     alpha=0.8, edgecolor='white', linewidth=0.5)
        
        # Etichette con conteggi sopra le barre
        for bar, count in zip(bars, conteggi):
            height = bar.get_height()
            ax_distribuzione.text(bar.get_x() + bar.get_width()/2., height,
                                 f'{count}', ha='center', va='bottom', 
                                 color='white', fontsize=8, fontweight='bold')
    
    ax_distribuzione.set_xlabel('Generazione', color='white', fontsize=9)
    ax_distribuzione.set_ylabel('N', color='white', fontsize=9)
    ax_distribuzione.set_title('Distribuzione Gerarchica', color='white', fontsize=10)
    ax_distribuzione.set_facecolor('#0a0e27')
    ax_distribuzione.tick_params(colors='white', labelsize=8)
    ax_distribuzione.grid(True, axis='y', alpha=0.3)
    
    # Aggiungi linea di riferimento per scala frattale ideale: N(gen) = N0 * 2^gen
    if len(generazioni) > 0:
        gen_max = max(generazioni)
        gen_ideale = range(gen_max + 1)
        n_ideale = [gen_counts.get(0, 1) * (2 ** g) for g in gen_ideale]
        ax_distribuzione.plot(gen_ideale, n_ideale, 'w--', alpha=0.3, linewidth=1, label='Ideale 2^n')
        ax_distribuzione.legend(fontsize=7, loc='upper left')
    
    plt.tight_layout()


# ============================================================================
# LOOP PRINCIPALE DI SIMULAZIONE
# ============================================================================

def run_simulazione():
    """
    Loop principale: evoluzione + congiunzioni + fissioni + visualizzazione.
    """
    # Inizializza manifold primordiali
    volume = 100.0 * LUNGHEZZA_PLANCK
    lista_manifold = []
    
    for i in range(args.n_manifold):
        pos = (np.random.rand(3) - 0.5) * volume
        m = ManifoldBase(posizione=pos, id_manifold=i, generazione=0)
        lista_manifold.append(m)
    
    print(f"[INIT] Creati {len(lista_manifold)} manifold primordiali")
    
    # Inizializza HDF5
    inizializza_hdf5(args.db, NUM_TOTAL_FRAMES)
    
    # Parametri dinamici
    dt = 0.01
    raggio_congiunzione = 10.0 * LUNGHEZZA_PLANCK
    
    # Modalità headless
    if args.headless:
        print(f"[HEADLESS] Inizio calcolo {NUM_TOTAL_FRAMES} frame...")
        
        with h5py.File(args.db, 'a') as f:
            for frame in range(NUM_TOTAL_FRAMES):
                # Evoluzione locale parallela
                lista_manifold = evolvi_sistema_parallelo(lista_manifold, dt, args.cores)
                
                # Congiunzioni
                lista_manifold = gestisci_congiunzioni(lista_manifold, raggio_congiunzione)
                
                # Fissioni
                lista_manifold = gestisci_fissioni(lista_manifold)
                
                # Salva stato
                salva_frame_hdf5(f, frame, lista_manifold)
                
                if (frame + 1) % 100 == 0:
                    print(f"[HEADLESS] Frame {frame+1}/{NUM_TOTAL_FRAMES} | N_manifold: {len(lista_manifold)}")
        
        print(f"[HEADLESS] ✓ Simulazione completata. Dati salvati in {args.db}")
    
    # Modalità interattiva
    else:
        print("[INTERATTIVO] Avvio animazione real-time...")
        
        # File handle HDF5 per salvataggio concorrente
        f_handle = h5py.File(args.db, 'a')
        
        def update_frame(frame):
            """Callback FuncAnimation."""
            nonlocal lista_manifold
            
            # Evolvi sistema
            lista_manifold = evolvi_sistema_parallelo(lista_manifold, dt, args.cores)
            lista_manifold = gestisci_congiunzioni(lista_manifold, raggio_congiunzione)
            lista_manifold = gestisci_fissioni(lista_manifold)
            
            # Salva HDF5
            salva_frame_hdf5(f_handle, frame, lista_manifold)
            
            # Aggiorna visualizzazione
            aggiorna_visualizzazione(frame, lista_manifold)
            
            return []
        
        # Crea animazione
        anim = FuncAnimation(fig, update_frame, frames=NUM_TOTAL_FRAMES,
                           interval=1000 // args.fps, blit=False, repeat=False)
        
        plt.show()
        
        # Chiudi file HDF5
        f_handle.close()
        
        print(f"[INTERATTIVO] ✓ Simulazione completata. Dati salvati in {args.db}")


# ============================================================================
# MODALITÀ PLAYBACK
# ============================================================================

def run_playback():
    """
    Modalità playback: leggi da HDF5 e renderizza.
    """
    print(f"[PLAYBACK] Lettura dati da {args.db}...")
    
    # Apri file HDF5
    with h5py.File(args.db, 'r') as f:
        telemetria = f['telemetria_scalare'][:]
        n_frames = len(telemetria)
    
    print(f"[PLAYBACK] Trovati {n_frames} frame. Avvio rendering...")
    
    # Se modalità film, salva frame come immagini
    if args.film:
        frames_dir = f"frames_playback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(frames_dir, exist_ok=True)
        
        for idx in range(n_frames):
            # Ricostruisci lista_manifold da telemetria (semplificato)
            # Per ora usa solo un manifold rappresentante
            record = telemetria[idx]
            
            m_temp = ManifoldBase()
            m_temp.chi = np.full(N_SEGMENTI, record['chi_medio'])
            m_temp.vel = np.full(N_SEGMENTI, record['v_chi_medio'])
            m_temp.torsione = record['torsione_media']
            
            lista_temp = [m_temp] * int(record['n_manifold'])
            
            # Aggiorna visualizzazione
            aggiorna_visualizzazione(idx, lista_temp)
            
            # Salva frame
            fig.savefig(os.path.join(frames_dir, f"frame_{idx:05d}.png"), dpi=100, facecolor='#020617')
            
            if (idx + 1) % 10 == 0:
                print(f"[PLAYBACK] Frame {idx+1}/{n_frames} renderizzato")
        
        print(f"\n[PLAYBACK] Compilazione video MP4...")
        import subprocess
        
        output_filename = args.output if args.output else f"playback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        input_pattern = os.path.join(frames_dir, 'frame_%05d.png').replace("\\", "/")
        
        ffmpeg_cmd = ['ffmpeg', '-y', '-framerate', str(args.fps), '-i', input_pattern,
                     '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', output_filename]
        
        try:
            risultato = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if risultato.returncode == 0:
                print(f"[PLAYBACK] ✓ Video salvato: {output_filename}")
            else:
                print(f"[ERRORE] FFmpeg fallito:\n{risultato.stderr}")
        except FileNotFoundError:
            print("[ERRORE] FFmpeg non trovato nel PATH")
    
    # Altrimenti, animazione interattiva
    else:
        print("[PLAYBACK] Animazione interattiva non implementata in questa versione")
        print("Usa --film per generare video MP4")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("WQT MANIFOLD - VERSIONE INTEGRATA")
    print("=" * 80)
    print(f"Modalità: {'HEADLESS' if args.headless else 'PLAYBACK' if args.playback else 'INTERATTIVO'}")
    print(f"File dati: {args.db}")
    print(f"Frame totali: {NUM_TOTAL_FRAMES}")
    print(f"Manifold iniziali: {args.n_manifold}")
    print(f"Core CPU: {args.cores if args.cores else mp.cpu_count()}")
    print("=" * 80)
    
    try:
        if args.playback:
            run_playback()
        else:
            run_simulazione()
    except KeyboardInterrupt:
        print("\n[INTERROTTO] Simulazione fermata dall'utente")
    except Exception as e:
        print(f"\n[ERRORE] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[FINE] Terminazione pulita")
