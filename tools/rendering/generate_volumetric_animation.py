"""
================================================================================
GENERA ANIMAZIONE VOLUMETRICA L3
================================================================================

Script per generare animazione MP4 del manifold L3 con rendering volumetrico.

CARATTERISTICHE:
----------------
1. Validazione L3: Richiede 13,824 segmenti
2. Isosuperficie χ con texture chirale dinamica
3. Smoothing Gaussiano 3D (elimina rumore Planckiano L0)
4. Linee di campo K (torsion trails)
5. Opacità dinamica basata su ∂χ/∂t

AUTHOR: WQT Physics Team - Scientific Visualization Engineer
DATE: 2026-05-26
================================================================================
"""

import sys
from pathlib import Path
import logging

# Setup path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))  # repo root (auto-shim)

from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_volumetric_animation():
    """Genera animazione volumetrica L3."""
    
    print("="*80)
    print(" VOLUMETRIC MANIFOLD ANIMATION GENERATOR - L3 FRACTAL LEVEL")
    print("="*80)
    
    # Dataset L3
    dataset_path = Path('cosmology_L3.h5')
    
    if not dataset_path.exists():
        print(f"ERROR: Dataset non trovato: {dataset_path}")
        sys.exit(1)
    
    # Configurazione rendering volumetrico ottimizzato
    config = VisualizationConfig(
        # Smoothing topologico
        smoothing_sigma=2.0,          # Gaussian σ per eliminare L0
        
        # Isosuperficie
        chi_isosurface_level=0.2,     # Livello isosurface (20% range)
        volumetric_resolution=55,     # Risoluzione griglia (compromesso qualità/tempo)
        
        # Linee di campo K
        K_streamline_density=12,      # Numero streamlines
        K_streamline_length=0.5,      # Lunghezza max
        
        # Chiralità
        chi_threshold_positive=0.1,
        chi_threshold_negative=-0.1,
        
        # Rendering
        dpi=120,
        figsize=(14, 12)
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        # Carica dataset L3
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        
        print(f"  Frames: {viz.get_frame_count()}")
        
        # Genera animazione volumetrica
        output_path = Path('L3_volumetric_evolution.mp4')
        
        print(f"\nGenerating volumetric animation...")
        print(f"  Output: {output_path}")
        print(f"  This will take several minutes for L3 dataset (13,824 segments)")
        print(f"  Please wait...")
        print()
        
        viz.animate_volumetric_manifold(
            output_path=output_path,
            apply_smoothing=True,      # Gaussian smoothing ON
            show_field_lines=True,     # K field lines ON
            fps=0.03,                  # 0.03 FPS → 333 secondi (5.5 min - ultra slow motion 100×)
            dpi=120,                   # Risoluzione HD
            bitrate=2400,              # Alta qualità
            show_progress=True
        )
        
        print()
        print("="*80)
        print(" ✓ ANIMAZIONE VOLUMETRICA COMPLETATA CON SUCCESSO")
        print("="*80)
        print(f" File: {output_path}")
        print(f" Caratteristiche:")
        print(f"   - Rendering volumetrico (NO scatter points)")
        print(f"   - Smoothing Gaussiano 3D (σ=2.0)")
        print(f"   - Texture chirale dinamica (opacità ∝ |∂χ/∂t|)")
        print(f"   - Linee di campo K (torsion trails)")
        print(f"   - Dataset L3: 13,824 segmenti")
        print("="*80)
        print()
        print("Visualizza con:")
        print(f"  vlc {output_path}")
        print(f"  Start-Process {output_path}")
        print("="*80)
        
    except ValueError as e:
        print(f"\n❌ ERRORE VALIDAZIONE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        viz.close()


if __name__ == '__main__':
    generate_volumetric_animation()
