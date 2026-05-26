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
