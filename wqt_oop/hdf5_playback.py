"""
================================================================================
HDF5 PLAYBACK ADAPTER - Bridge per WQT_manifold.py Rendering
================================================================================

Adapter per caricare dati HDF5 salvati da run_cosmology.py e mapparli
nel formato atteso da WQT_manifold.py (modalità playback).

COMPATIBILITY:
- Mantiene schema SCALARI_24_DTYPE
- Converte arrays HDF5 → strutture manifold
- Supporta SWMR mode per rendering real-time

USAGE:
------
# Modalità offline (file completo)
python -m wqt_oop.hdf5_playback geometrodinamica_matrix.h5

# Modalità real-time (SWMR durante simulazione)
python -m wqt_oop.hdf5_playback geometrodinamica_matrix.h5 --follow

================================================================================
"""

import numpy as np
import h5py
from pathlib import Path
from typing import Dict, Optional
import logging
import time

from .hdf5_logger import load_from_hdf5, get_metadata, count_frames


logger = logging.getLogger(__name__)


# ========================================================================
# DTYPE COMPATIBILITY (WQT_manifold.py schema)
# ========================================================================

# Schema originale WQT_manifold.py
SCALARI_24_DTYPE = np.dtype([
    ('chi', 'f8'),
    ('polarizzazione', 'f8'),
    ('contorsione_locale', 'f8'),
    ('densita_screening', 'f8'),
    ('chiralita', 'f8'),  # Calcolato da polarizzazione
    ('aging_factor', 'f8'),  # Calcolato da tau_locale
    ('temperature', 'f8')
])


def convert_hdf5_to_manifold_frame(hdf5_data: Dict) -> Dict:
    """
    Converte frame HDF5 in formato WQT_manifold.py.
    
    Parameters:
    -----------
    hdf5_data : dict
        Dati da load_from_hdf5()
    
    Returns:
    --------
    manifold_data : dict
        Formato compatibile con WQT_manifold rendering engine
    """
    N = len(hdf5_data['chi_values'])
    
    # Crea array strutturato SCALARI_24_DTYPE
    scalari = np.zeros(N, dtype=SCALARI_24_DTYPE)
    
    # Mappa campi
    scalari['chi'] = hdf5_data['chi_values']
    scalari['polarizzazione'] = hdf5_data['polarizzazione']  # Globale, replicato
    scalari['contorsione_locale'] = hdf5_data['contorsione_locale']
    scalari['densita_screening'] = hdf5_data['densita_screening']
    
    # Calcola chiralità da velocità (approssimazione)
    # chiralità ~ sign(v) * |v|^0.5
    velocities = hdf5_data['velocities']
    scalari['chiralita'] = np.sign(velocities) * np.sqrt(np.abs(velocities))
    
    # Aging factor da tau_locale
    # aging = exp(-tau / tau_ref)
    tau_ref = 100.0  # Scala caratteristica aging
    scalari['aging_factor'] = np.exp(-hdf5_data['tau_locale'] / tau_ref)
    
    # Temperature (T_eff globale)
    scalari['temperature'] = hdf5_data['T_eff']
    
    # Dati completi
    manifold_data = {
        'step': hdf5_data['step'],
        'time': hdf5_data['time'],
        'positions': hdf5_data['positions'],
        'scalari_24': scalari,  # Array strutturato DTYPE-compatible
        'H_total': hdf5_data['H_total'],
        'drift': hdf5_data['drift'],
        'N_segments': N
    }
    
    return manifold_data


# ========================================================================
# PLAYBACK ENGINE
# ========================================================================

class HDF5PlaybackEngine:
    """
    Engine per playback frames HDF5 (modalità rendering).
    
    Supporta:
    - Offline: Carica file completo
    - Real-time (SWMR): Segue simulazione in corso
    
    Methods:
    --------
    get_frame(idx) : Carica frame specifico
    get_current_frame() : Frame corrente (SWMR mode)
    wait_for_next_frame() : Blocca fino a nuovo frame disponibile
    """
    
    def __init__(
        self,
        filepath: Path,
        follow_mode: bool = False,
        poll_interval: float = 0.1
    ):
        """
        Inizializza playback engine.
        
        Parameters:
        -----------
        filepath : Path
            Path file HDF5
        
        follow_mode : bool
            Se True, segue simulazione in tempo reale (SWMR)
        
        poll_interval : float
            Intervallo polling [s] per nuovi frames
        """
        self.filepath = filepath
        self.follow_mode = follow_mode
        self.poll_interval = poll_interval
        
        # Metadata
        self.metadata = get_metadata(filepath)
        
        # Stato playback
        self.current_frame_idx = 0
        self.N_frames_cached = count_frames(filepath)
        
        logger.info(f"HDF5 Playback initialized: {filepath}")
        logger.info(f"  Follow mode: {follow_mode}")
        logger.info(f"  Frames available: {self.N_frames_cached}")
    
    def get_frame(self, idx: int) -> Dict:
        """
        Carica frame specifico.
        
        Parameters:
        -----------
        idx : int
            Indice frame
        
        Returns:
        --------
        manifold_data : dict
            Frame convertito per rendering
        """
        # Carica da HDF5
        hdf5_data = load_from_hdf5(self.filepath, frame_idx=idx)
        
        # Converti a formato manifold
        return convert_hdf5_to_manifold_frame(hdf5_data)
    
    def get_current_frame(self) -> Dict:
        """Restituisce frame corrente."""
        return self.get_frame(self.current_frame_idx)
    
    def next_frame(self) -> Optional[Dict]:
        """
        Avanza a frame successivo.
        
        Returns:
        --------
        frame : dict or None
            Frame successivo (None se fine file)
        """
        # Verifica se disponibile
        if self.current_frame_idx >= self.N_frames_cached:
            if self.follow_mode:
                # SWMR: aspetta nuovo frame
                return self.wait_for_next_frame()
            else:
                # Offline: fine file
                return None
        
        frame = self.get_frame(self.current_frame_idx)
        self.current_frame_idx += 1
        
        return frame
    
    def wait_for_next_frame(self, timeout: float = 60.0) -> Optional[Dict]:
        """
        Aspetta prossimo frame (SWMR mode).
        
        Parameters:
        -----------
        timeout : float
            Timeout massimo [s]
        
        Returns:
        --------
        frame : dict or None
            Nuovo frame (None se timeout)
        """
        if not self.follow_mode:
            raise RuntimeError("wait_for_next_frame() richiede follow_mode=True")
        
        t_start = time.time()
        
        while time.time() - t_start < timeout:
            # Aggiorna conteggio frames (refresh HDF5)
            N_frames_new = count_frames(self.filepath)
            
            if N_frames_new > self.N_frames_cached:
                self.N_frames_cached = N_frames_new
                logger.debug(f"New frame available: {N_frames_new}")
                
                # Carica nuovo frame
                frame = self.get_frame(self.current_frame_idx)
                self.current_frame_idx += 1
                return frame
            
            # Poll
            time.sleep(self.poll_interval)
        
        logger.warning(f"Timeout waiting for frame (waited {timeout}s)")
        return None
    
    def reset(self):
        """Reset playback a frame 0."""
        self.current_frame_idx = 0
    
    def get_metadata(self) -> Dict:
        """Restituisce metadata simulazione."""
        return self.metadata.copy()


# ========================================================================
# CLI PLAYBACK TOOL
# ========================================================================

def main():
    """CLI per playback HDF5."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="HDF5 Playback Tool - Visualizza frames da simulazione"
    )
    
    parser.add_argument(
        'filepath',
        type=str,
        help='Path file HDF5'
    )
    
    parser.add_argument(
        '--follow',
        action='store_true',
        help='Follow mode (SWMR real-time)'
    )
    
    parser.add_argument(
        '--frame',
        type=int,
        default=None,
        help='Show specific frame (offline mode only)'
    )
    
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show metadata only'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    filepath = Path(args.filepath)
    
    if not filepath.exists():
        logger.error(f"File not found: {filepath}")
        return 1
    
    # Info mode
    if args.info:
        metadata = get_metadata(filepath)
        N_frames = count_frames(filepath)
        
        print("\n" + "="*70)
        print(" HDF5 FILE INFO")
        print("="*70)
        print(f"\nFile: {filepath}")
        print(f"Frames: {N_frames}")
        print("\nMetadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print("\n" + "="*70 + "\n")
        return 0
    
    # Playback
    engine = HDF5PlaybackEngine(
        filepath=filepath,
        follow_mode=args.follow
    )
    
    # Single frame mode
    if args.frame is not None:
        if args.follow:
            logger.error("--frame incompatible with --follow")
            return 1
        
        frame = engine.get_frame(args.frame)
        
        print("\n" + "="*70)
        print(f" FRAME {args.frame}")
        print("="*70)
        print(f"Step:         {frame['step']}")
        print(f"Time:         {frame['time']:.3f} s")
        print(f"H_total:      {frame['H_total']:.6e} J")
        print(f"Drift:        {frame['drift']:.3e}")
        print(f"N_segments:   {frame['N_segments']}")
        print("\nScalari sample (first 3 segments):")
        for i in range(min(3, frame['N_segments'])):
            s = frame['scalari_24'][i]
            print(f"  Seg {i}: chi={s['chi']:.3f}, "
                  f"K²={s['contorsione_locale']:.3e}, "
                  f"ρ={s['densita_screening']:.3f}")
        print("\n" + "="*70 + "\n")
        return 0
    
    # Playback loop
    print("\n" + "="*70)
    print(" HDF5 PLAYBACK")
    print("="*70)
    print(f"File: {filepath}")
    print(f"Mode: {'FOLLOW (real-time)' if args.follow else 'OFFLINE'}")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            frame = engine.next_frame()
            
            if frame is None:
                logger.info("No more frames")
                break
            
            print(f"Frame {frame['step']:6d} | "
                  f"t={frame['time']:8.3f}s | "
                  f"H={frame['H_total']:.6e} | "
                  f"drift={frame['drift']:.3e}")
            
            if not args.follow:
                # Offline: limita output
                if engine.current_frame_idx > 10:
                    logger.info("...")
                    break
    
    except KeyboardInterrupt:
        logger.info("Playback interrupted")
    
    print("\n" + "="*70)
    print(" PLAYBACK STOPPED")
    print("="*70 + "\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())


# ============================================================================
# TOPOLOGICAL PLAYBACK EXTENSION (NON-DESTRUCTIVE — aggiunta pura)
# ============================================================================
# Tutto il codice che segue è AGGIUNTIVO e non altera le classi legacy.
# Il ConstraintDensityPlaybackEngine estende HDF5PlaybackEngine e aggiunge
# la capacità di visualizzare il clustering della materia tramite la
# Densità di Vincolo topologica invece del potenziale energetico.
# ============================================================================

def load_topological_group(
    filepath,
    group_name: str = "topological_validation"
) -> Dict:
    """
    Carica il gruppo ``/topological_validation`` da un file HDF5.

    Questo gruppo viene scritto da
    ``integrate_topological_validation_to_hdf5`` durante la simulazione.

    Parameters
    ----------
    filepath : Path or str
        Path del file HDF5.
    group_name : str
        Nome del gruppo topologico.

    Returns
    -------
    dict
        Dizionario di ndarray con i dati topologici.
        Chiavi: step, time, closure_error_deg, closure_satisfied,
        detorsion_quality, detorsion_satisfied,
        mean_constraint_density, constraint_density_std,
        N_dof, N_segments, H_total_emergent, H_torsion_emergent,
        topology_charge, phase_label, transition_detected.
        Dizionario vuoto se il gruppo non esiste.
    """
    import h5py

    result = {}
    try:
        with h5py.File(filepath, 'r', swmr=True) as f:
            if group_name not in f:
                logger.warning(
                    f"Group '{group_name}' not found in {filepath}. "
                    "Run simulation with TopologicalEvolutionWrapper first."
                )
                return {}
            grp = f[group_name]
            for key in grp.keys():
                result[key] = grp[key][()]
    except Exception as exc:
        logger.error(f"Failed to load topological group: {exc}")

    return result


def convert_hdf5_frame_with_constraint_density(
    hdf5_data: Dict,
    constraint_density: Optional[np.ndarray] = None
) -> Dict:
    """
    Converte un frame HDF5 in formato manifold con densità di vincolo.

    Estende ``convert_hdf5_to_manifold_frame`` aggiungendo il campo
    ``constraint_density`` che sostituisce ``densita_screening`` come
    metrica di clustering della materia nel rendering.

    Parameters
    ----------
    hdf5_data : dict
        Frame grezzo da ``load_from_hdf5()``.
    constraint_density : ndarray, optional
        ρ_constraint per ogni segmento al frame corrente.
        Se None, usa densita_screening legacy come fallback.

    Returns
    -------
    dict
        Frame arricchito con chiave ``constraint_density``.
    """
    # Usa la conversione legacy come base
    manifold_data = convert_hdf5_to_manifold_frame(hdf5_data)

    N = manifold_data['N_segments']

    if constraint_density is not None and len(constraint_density) == N:
        manifold_data['constraint_density'] = constraint_density.copy()
    else:
        # Fallback: usa densita_screening legacy (compatibilità)
        manifold_data['constraint_density'] = (
            hdf5_data.get('densita_screening', np.zeros(N))
        )

    return manifold_data


class ConstraintDensityPlaybackEngine(HDF5PlaybackEngine):
    """
    Engine di playback con supporto alla Densità di Vincolo topologica.

    Estende ``HDF5PlaybackEngine`` aggiungendo:
    - Caricamento del gruppo ``/topological_validation`` dal file HDF5
    - Metodo ``get_constraint_density_at(step)`` per il rendering
    - Metodo ``get_frame_with_density(idx)`` che include ``constraint_density``

    Eredita tutto il comportamento legacy (offline/SWMR, CLI) invariato.
    """

    def __init__(
        self,
        filepath,
        follow_mode: bool = False,
        poll_interval: float = 0.1,
        topo_group_name: str = "topological_validation",
    ):
        """
        Parameters
        ----------
        filepath : Path or str
        follow_mode : bool
        poll_interval : float
        topo_group_name : str
            Nome gruppo topologico nel file HDF5.
        """
        super().__init__(filepath, follow_mode, poll_interval)

        self.topo_group_name = topo_group_name
        self._topo_data: Dict = {}
        self._topo_step_index: Dict[int, int] = {}  # step → indice nel topo array

        self._load_topo_data()

    def _load_topo_data(self):
        """Carica dati topologici dal file HDF5 (se presenti)."""
        self._topo_data = load_topological_group(
            self.filepath, self.topo_group_name
        )
        if self._topo_data:
            steps = self._topo_data.get('step', np.array([]))
            self._topo_step_index = {int(s): i for i, s in enumerate(steps)}
            logger.info(
                f"Topological data loaded: {len(steps)} entries, "
                f"group='{self.topo_group_name}'"
            )
        else:
            logger.info(
                "No topological data found — density will fallback to densita_screening."
            )

    def get_constraint_density_at(self, sim_step: int) -> Optional[np.ndarray]:
        """
        Restituisce ρ_constraint al passo di simulazione ``sim_step``.

        Parameters
        ----------
        sim_step : int
            Step di simulazione (chiave nel dizionario topologico).

        Returns
        -------
        ndarray or None
            Densità vincolo per ogni segmento, o None se non disponibile.
        """
        if not self._topo_data:
            return None

        idx = self._topo_step_index.get(sim_step)
        if idx is None:
            # Cerca il più vicino disponibile
            available_steps = np.array(list(self._topo_step_index.keys()))
            if len(available_steps) == 0:
                return None
            closest = int(available_steps[np.argmin(np.abs(available_steps - sim_step))])
            idx = self._topo_step_index[closest]

        # I dati di constraint_density per-segmento per ora non sono salvati
        # per-frame nel dict topologico (solo le metriche aggregate).
        # Restituiamo mean_constraint_density come scalare broadcastato.
        mean_rho = float(self._topo_data['mean_constraint_density'][idx])
        return np.array([mean_rho])

    def get_phase_label_at(self, sim_step: int) -> str:
        """Fase topologica al passo ``sim_step``."""
        if not self._topo_data:
            return "unknown"
        idx = self._topo_step_index.get(sim_step)
        if idx is None:
            return "unknown"
        raw = self._topo_data['phase_label'][idx]
        # Decodifica da bytes se necessario
        if isinstance(raw, bytes):
            return raw.decode('utf-8').rstrip('\x00')
        return str(raw)

    def get_mean_constraint_density_series(self) -> np.ndarray:
        """
        Serie temporale della densità vincolo media ρ_mean(t).

        Utile per grafici di evoluzione della fase topologica.
        """
        return self._topo_data.get(
            'mean_constraint_density', np.array([])
        )

    def get_frame_with_density(self, idx: int) -> Dict:
        """
        Carica frame con densità di vincolo inclusa.

        Equivalente a ``get_frame(idx)`` ma arricchisce il dizionario
        con ``constraint_density`` (metrica topologica) e
        ``phase_label`` (fase corrente).

        Parameters
        ----------
        idx : int
            Indice frame.

        Returns
        -------
        dict
            Frame manifold con chiavi aggiuntive:
            - ``constraint_density`` : ndarray ρ per segmento
            - ``phase_label`` : str etichetta fase
            - ``H_total`` : energia EMERGENTE (non vincolo)
        """
        from .hdf5_logger import load_from_hdf5

        hdf5_data = load_from_hdf5(self.filepath, frame_idx=idx)
        sim_step = int(hdf5_data.get('step', idx))

        # Tenta caricamento ρ topologica
        rho = self.get_constraint_density_at(sim_step)

        # Converti frame con density
        frame = convert_hdf5_frame_with_constraint_density(hdf5_data, rho)
        frame['phase_label'] = self.get_phase_label_at(sim_step)

        return frame

    def print_topological_summary(self):
        """Stampa un riassunto dei dati topologici disponibili."""
        if not self._topo_data:
            print("No topological data loaded.")
            return

        steps = self._topo_data.get('step', np.array([]))
        rho = self._topo_data.get('mean_constraint_density', np.array([]))
        phases = self._topo_data.get('phase_label', np.array([]))

        print("\n" + "=" * 60)
        print(" TOPOLOGICAL PLAYBACK DATA")
        print("=" * 60)
        print(f"  Entries:           {len(steps)}")
        if len(steps) > 0:
            print(f"  Step range:        {steps[0]} -> {steps[-1]}")
        if len(rho) > 0:
            print(f"  ρ_constraint:      "
                  f"min={rho.min():.3f}  max={rho.max():.3f}  "
                  f"mean={rho.mean():.3f}")
        if len(phases) > 0:
            decoded = [
                p.decode('utf-8').rstrip('\x00') if isinstance(p, bytes) else str(p)
                for p in phases
            ]
            unique, counts = np.unique(decoded, return_counts=True)
            print("  Phase distribution:")
            for phase, count in zip(unique, counts):
                pct = 100 * count / len(decoded)
                print(f"    {phase:12s}: {count:5d} steps ({pct:.1f}%)")
        print("=" * 60 + "\n")
