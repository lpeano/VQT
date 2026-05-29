"""
================================================================================
HDF5 LOGGER - Persistent Data Storage per Rendering Offline
================================================================================

Sistema di logging HDF5 con SWMR (Single Writer Multiple Reader) per
catturare lo stato completo del manifold frattale durante evoluzione.

FEATURES:
- SWMR mode: Rendering real-time mentre simulazione scrive
- Emergency flush: Salvataggio sicuro su SIGINT/interruzione
- Buffer management: Scrittura batch per performance
- Schema compatibile: WQT_manifold.py playback mode

SCHEMA HDF5:
------------
geometrodinamica_matrix.h5
├── /frames/
│   ├── frame_0000/
│   │   ├── positions (N, 3)          # Posizioni segmenti [m]
│   │   ├── chi_values (N,)           # Campo χ
│   │   ├── contorsione_locale (N,)   # Torsione K²
│   │   ├── densita_screening (N,)    # ρ_local Fermi-Dirac
│   │   ├── polarizzazione            # Polarizzazione globale
│   │   ├── time                      # Tempo emergente [s]
│   │   ├── H_total                   # Energia conservata [J]
│   │   ├── T_eff                     # Temperatura efficace
│   ├── frame_0001/
│   └── ...
├── /metadata/
│   ├── target_level
│   ├── N_segments
│   ├── dt
│   ├── chi_mean
│   ├── spatial_extent
│   └── creation_timestamp

================================================================================
"""

import numpy as np
import h5py
import logging
import signal
import atexit
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import time

from .energy_drift_observer import Observer, SimulationState
from .abstract_soliton import AbstractSoliton
from .solitone_composito import SolitoneComposito
from .segmento_quantistico import SegmentoQuantistico


logger = logging.getLogger(__name__)


@dataclass
class HDF5LoggerConfig:
    """
    Configurazione HDF5 logger.
    
    Attributes:
    -----------
    filepath : Path
        Path file HDF5 output
    
    save_interval : int
        Salva ogni N steps
    
    enable_swmr : bool
        Abilita SWMR mode (Single Writer Multiple Reader)
    
    buffer_size : int
        Numero frames da bufferizzare prima di flush
    
    compression : str
        Tipo compressione ('gzip', 'lzf', None)
    """
    filepath: Path
    save_interval: int = 1
    enable_swmr: bool = True
    buffer_size: int = 10
    compression: Optional[str] = 'gzip'


class HDF5Logger(Observer):
    """
    Observer per salvataggio incrementale HDF5.
    
    Cattura stato manifold frattale a ogni step e scrive su file HDF5
    in modalità append. Supporta SWMR per rendering real-time.
    
    Methods:
    --------
    update(state) : Callback su step simulazione
    save_frame(universe, state) : Salva singolo frame
    flush() : Forza scrittura buffer su disco
    close() : Chiude file HDF5 (emergency safe)
    """
    
    def __init__(
        self,
        config: HDF5LoggerConfig,
        universe: AbstractSoliton,
        metadata: Dict = None
    ):
        """
        Inizializza logger.
        
        Parameters:
        -----------
        config : HDF5LoggerConfig
            Configurazione logger
        
        universe : AbstractSoliton
            Universo frattale da loggare
        
        metadata : dict, optional
            Metadati simulazione
        """
        self.config = config
        self.universe = universe
        self.metadata = metadata or {}
        
        # Buffer frames (per scrittura batch)
        self.frame_buffer: List[Dict] = []
        self.frames_written = 0
        
        # HDF5 file handle
        self.h5file: Optional[h5py.File] = None
        
        # Emergency cleanup
        self._register_cleanup_handlers()
        
        # Open file
        self._open_file()
        
        logger.info(f"HDF5Logger initialized: {config.filepath}")
        logger.info(f"  SWMR mode: {config.enable_swmr}")
        logger.info(f"  Save interval: {config.save_interval}")
    
    def _register_cleanup_handlers(self):
        """Registra handler per cleanup emergenza."""
        # SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._emergency_cleanup)
        
        # atexit (terminazione normale)
        atexit.register(self.close)
    
    def _emergency_cleanup(self, signum, frame):
        """Handler emergenza per SIGINT."""
        logger.warning("SIGINT received - emergency flush")
        self.flush()
        self.close()
        raise KeyboardInterrupt
    
    def _open_file(self):
        """Apre file HDF5 in modalità write (crea nuovo o sovrascrive)."""
        # Crea directory se non esiste
        self.config.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Apri file (sovrascrive se esiste)
        self.h5file = h5py.File(
            self.config.filepath,
            'w',
            libver='latest' if self.config.enable_swmr else 'earliest'
        )
        
        # Crea gruppi
        self.h5file.create_group('frames')
        
        # Scrivi metadata
        self._write_metadata()
        
        # Abilita SWMR se richiesto (DOPO scrittura metadata)
        if self.config.enable_swmr:
            self.h5file.swmr_mode = True
            logger.info("SWMR mode enabled (readers can attach)")
    
    def _write_metadata(self):
        """Scrive metadata simulazione."""
        meta_group = self.h5file.create_group('metadata')
        
        # Metadata base
        meta_group.attrs['creation_timestamp'] = time.time()
        meta_group.attrs['target_level'] = self.universe.physics.level
        
        # Metadata da config
        for key, value in self.metadata.items():
            if isinstance(value, (int, float, str)):
                meta_group.attrs[key] = value
            elif isinstance(value, np.ndarray):
                meta_group.create_dataset(key, data=value)
        
        logger.debug("Metadata written to HDF5")
    
    def on_simulation_start(self):
        """Hook: simulazione iniziata."""
        logger.info("HDF5 logging started")
    
    def update(self, state: SimulationState):
        """
        Callback su step simulazione.
        
        Salva frame se step % save_interval == 0.
        
        Parameters:
        -----------
        state : SimulationState
            Stato corrente simulazione
        """
        if state.step % self.config.save_interval == 0:
            self.save_frame(state)
    
    def save_frame(self, state: SimulationState):
        """
        Salva singolo frame nel buffer.
        
        Parameters:
        -----------
        state : SimulationState
            Stato simulazione
        """
        # Estrai dati da universo
        frame_data = self._extract_frame_data(state)
        
        # Aggiungi a buffer
        self.frame_buffer.append(frame_data)
        
        # Flush se buffer pieno
        if len(self.frame_buffer) >= self.config.buffer_size:
            self.flush()
    
    def _extract_frame_data(self, state: SimulationState) -> Dict:
        """
        Estrae dati completi da universo.
        
        Returns:
        --------
        data : dict
            Dizionario con arrays numpy
        """
        # Raccolta ricorsiva segmenti
        segments = self._collect_all_segments(self.universe)
        N = len(segments)
        
        # Arrays dati
        positions = np.zeros((N, 3))
        chi_values = np.zeros(N)
        velocities = np.zeros(N)
        tau_locale = np.zeros(N)
        
        for i, seg in enumerate(segments):
            positions[i] = seg.get_position()
            chi_values[i] = seg.chi
            velocities[i] = seg.vel
            tau_locale[i] = seg.tau_locale
        
        # Calcola contorsione e screening
        contorsione_locale = self._compute_torsion_field(segments)
        densita_screening = self._compute_screening_density(segments)
        
        # Polarizzazione globale (se disponibile)
        polarizzazione = 0.0
        T_eff = state.T_eff
        
        if isinstance(self.universe, SolitoneComposito):
            stats = self.universe.get_occupazione_stati()
            polarizzazione = stats['polarizzazione']
            T_eff = stats['T_eff']
        
        # Peano-VQT energy triad (scalari, se disponibile)
        E_chi, E_RX, E_Psi = 0.0, 0.0, 0.0
        if isinstance(self.universe, SolitoneComposito):
            triad = self.universe.get_energy_triad()
            if triad is not None:
                E_chi = triad.E_chi
                E_RX  = triad.E_RX
                E_Psi = triad.E_Psi

        return {
            'step': state.step,
            'time': state.time,
            'positions': positions,
            'chi_values': chi_values,
            'velocities': velocities,
            'tau_locale': tau_locale,
            'contorsione_locale': contorsione_locale,
            'densita_screening': densita_screening,
            'polarizzazione': polarizzazione,
            'H_total': state.H_total,
            'T_eff': T_eff,
            'drift': state.drift,
            'E_chi': E_chi,
            'E_RX': E_RX,
            'E_Psi': E_Psi,
        }
    
    def _collect_all_segments(self, soliton: AbstractSoliton) -> List[SegmentoQuantistico]:
        """
        Raccolta ricorsiva di tutti i segmenti atomici (L0).
        
        Parameters:
        -----------
        soliton : AbstractSoliton
            Solitone radice
        
        Returns:
        --------
        segments : List[SegmentoQuantistico]
            Lista segmenti atomici
        """
        if isinstance(soliton, SegmentoQuantistico):
            return [soliton]
        
        elif isinstance(soliton, SolitoneComposito):
            segments = []
            for child in soliton.children:
                segments.extend(self._collect_all_segments(child))
            return segments
        
        else:
            logger.warning(f"Unknown soliton type: {type(soliton)}")
            return []
    
    def _compute_torsion_field(self, segments: List[SegmentoQuantistico]) -> np.ndarray:
        """
        Stima campo di torsione locale.
        
        K² ~ |∇χ|² (approssimazione finite-difference circolare)
        """
        N = len(segments)
        K2 = np.zeros(N)
        
        for i in range(N):
            # Derivata circolare (primo vicino)
            i_next = (i + 1) % N
            i_prev = (i - 1) % N
            
            dchi_dx = (segments[i_next].chi - segments[i_prev].chi) / 2.0
            
            K2[i] = dchi_dx ** 2
        
        return K2
    
    def _compute_screening_density(self, segments: List[SegmentoQuantistico]) -> np.ndarray:
        """
        Calcola densità locale per screening.
        
        ρ_i ~ |χ_i| (approssimazione mean-field)
        """
        return np.abs([seg.chi for seg in segments])
    
    def flush(self):
        """
        Scrive buffer su disco.
        
        Scrittura batch per performance.
        """
        if not self.frame_buffer:
            return
        
        if self.h5file is None:
            logger.error("HDF5 file not open - cannot flush")
            return
        
        frames_group = self.h5file['frames']
        
        for frame_data in self.frame_buffer:
            frame_name = f"frame_{self.frames_written:06d}"
            
            # Crea gruppo frame
            frame_group = frames_group.create_group(frame_name)
            
            # Salva datasets
            for key, value in frame_data.items():
                if isinstance(value, np.ndarray):
                    frame_group.create_dataset(
                        key,
                        data=value,
                        compression=self.config.compression
                    )
                else:
                    # Scalare
                    frame_group.attrs[key] = value
            
            self.frames_written += 1
        
        # Flush file HDF5
        self.h5file.flush()
        
        logger.debug(f"Flushed {len(self.frame_buffer)} frames to HDF5")
        
        # Clear buffer
        self.frame_buffer.clear()
    
    def on_simulation_end(self):
        """Hook: simulazione terminata."""
        self.flush()
        logger.info(f"HDF5 logging complete: {self.frames_written} frames written")
    
    def close(self):
        """Chiude file HDF5 (safe)."""
        if self.h5file is not None:
            try:
                self.flush()
                self.h5file.close()
                logger.info("HDF5 file closed")
            except Exception as e:
                logger.error(f"Error closing HDF5: {e}")
            finally:
                self.h5file = None


# ========================================================================
# UTILITY: Load from HDF5 per Rendering
# ========================================================================

def load_from_hdf5(filepath: Path, frame_idx: int = 0) -> Dict:
    """
    Carica singolo frame da file HDF5.
    
    Compatibile con WQT_manifold.py playback mode.
    
    Parameters:
    -----------
    filepath : Path
        Path file HDF5
    
    frame_idx : int
        Indice frame da caricare
    
    Returns:
    --------
    data : dict
        Dizionario con arrays numpy compatibili manifold rendering
    """
    with h5py.File(filepath, 'r', libver='latest', swmr=True) as f:
        frame_name = f"frame_{frame_idx:06d}"
        
        if frame_name not in f['frames']:
            raise ValueError(f"Frame {frame_idx} not found in {filepath}")
        
        frame = f['frames'][frame_name]
        
        # Carica dati (E_chi/E_RX/E_Psi con default 0 per backward-compat)
        data = {
            'step': frame.attrs['step'],
            'time': frame.attrs['time'],
            'positions': frame['positions'][:],
            'chi_values': frame['chi_values'][:],
            'velocities': frame['velocities'][:],
            'tau_locale': frame['tau_locale'][:],
            'contorsione_locale': frame['contorsione_locale'][:],
            'densita_screening': frame['densita_screening'][:],
            'polarizzazione': frame.attrs['polarizzazione'],
            'H_total': frame.attrs['H_total'],
            'T_eff': frame.attrs['T_eff'],
            'drift': frame.attrs['drift'],
            'E_chi': frame.attrs.get('E_chi', 0.0),
            'E_RX':  frame.attrs.get('E_RX',  0.0),
            'E_Psi': frame.attrs.get('E_Psi', 0.0),
        }
        
        return data


def get_metadata(filepath: Path) -> Dict:
    """
    Carica metadata da file HDF5.
    
    Parameters:
    -----------
    filepath : Path
        Path file HDF5
    
    Returns:
    --------
    metadata : dict
        Metadata simulazione
    """
    with h5py.File(filepath, 'r') as f:
        return dict(f['metadata'].attrs)


def count_frames(filepath: Path) -> int:
    """
    Conta numero frames nel file HDF5.
    
    Parameters:
    -----------
    filepath : Path
        Path file HDF5
    
    Returns:
    --------
    N_frames : int
        Numero totale frames
    """
    with h5py.File(filepath, 'r') as f:
        return len(f['frames'])


# ========================================================================
# TEST
# ========================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print(" TEST: HDF5 LOGGER")
    print("="*70 + "\n")
    
    # Mock test (senza simulazione completa)
    from .physics_context import PhysicsContext
    from .segmento_quantistico import SegmentoQuantistico
    
    # Crea segmento test
    physics = PhysicsContext(level=0, length_scale=1e-10)
    segment = SegmentoQuantistico(chi=50.0, vel=0.1, physics=physics)
    
    # Config logger
    config = HDF5LoggerConfig(
        filepath=Path("test_hdf5_logger.h5"),
        save_interval=1,
        enable_swmr=False,  # Disabilitato per test
        buffer_size=5,
        compression='gzip'
    )
    
    # Crea logger
    logger_obj = HDF5Logger(
        config=config,
        universe=segment,
        metadata={'test': True, 'N_segments': 1}
    )
    
    # Simula 10 steps
    for step in range(10):
        state = SimulationState(
            step=step,
            time=step * 0.01,
            H_total=1e5,
            drift=1e-5,
            N_solitons=1,
            T_eff=5.0,
            wall_time=time.time()
        )
        
        logger_obj.update(state)
    
    # Close
    logger_obj.close()
    
    # Verifica
    N_frames = count_frames(Path("test_hdf5_logger.h5"))
    print(f"Frames written: {N_frames}")
    
    # Load test
    data = load_from_hdf5(Path("test_hdf5_logger.h5"), frame_idx=0)
    print(f"Frame 0 loaded: time={data['time']}, H={data['H_total']:.3e}")
    
    # Metadata
    meta = get_metadata(Path("test_hdf5_logger.h5"))
    print(f"Metadata: {meta}")
    
    # Cleanup
    Path("test_hdf5_logger.h5").unlink()
    
    print("\n" + "="*70)
    print(" HDF5 LOGGER TEST COMPLETATO")
    print("="*70 + "\n")
