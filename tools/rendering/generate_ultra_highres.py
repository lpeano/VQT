"""
================================================================================
VOLUMETRIC ULTRA-HIGH RESOLUTION - Smoothness Massima
================================================================================

Versione ad altissima risoluzione del rendering volumetrico per superfici
estremamente lisce e morbide.

MIGLIORAMENTI:
--------------
1. volumetric_resolution: 55 → 128 (griglia molto più fine)
2. smoothing_sigma: 2.0 → 3.0 (smoothing più aggressivo)
3. Rendering solo mesh (no field lines per focus su superficie)
4. DPI più alto (150) per dettagli fini

TEMPI: ~15-20 minuti per L3 (13,824 segmenti, 10 frames)

AUTHOR: WQT Physics Team - Scientific Visualization Engineer
DATE: 2026-05-26
================================================================================
"""

import sys
from pathlib import Path
import logging


import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))  # repo root (auto-shim)

from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_ultra_high_res():
    """Genera rendering volumetrico ad altissima risoluzione."""
    
    print("="*80)
    print(" VOLUMETRIC ULTRA-HIGH RESOLUTION - Maximum Smoothness")
    print("="*80)
    
    dataset_path = Path('cosmology_L3.h5')
    
    if not dataset_path.exists():
        print(f"ERROR: Dataset non trovato: {dataset_path}")
        sys.exit(1)
    
    # CONFIGURAZIONE ULTRA-HIGH-RES
    config = VisualizationConfig(
        smoothing_sigma=3.0,              # Smoothing più aggressivo
        chi_isosurface_level=0.2,
        volumetric_resolution=128,        # Griglia MOLTO più fine (55→128)
        K_streamline_density=0,           # NO field lines (focus su mesh)
        K_streamline_length=0.5,
        chi_threshold_positive=0.1,
        chi_threshold_negative=-0.1,
        dpi=150,                          # Risoluzione molto alta
        figsize=(16, 14)
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        print(f"  Frames: {viz.get_frame_count()}")
        
        print("\n" + "="*80)
        print(" ULTRA-HIGH-RES PARAMETERS")
        print("="*80)
        print("Miglioramenti rispetto a versione standard:")
        print()
        print("  volumetric_resolution:")
        print("    Standard: 55×55×55 = 166,375 punti griglia")
        print("    Ultra-HR: 128×128×128 = 2,097,152 punti griglia")
        print("    → +1157% risoluzione! ⚡")
        print()
        print("  smoothing_sigma:")
        print("    Standard: 2.0 (elimina L0)")
        print("    Ultra-HR: 3.0 (smoothing molto più aggressivo)")
        print("    → Superfici estremamente lisce")
        print()
        print("  field_lines:")
        print("    Standard: 12 streamlines K")
        print("    Ultra-HR: 0 (disabilitate)")
        print("    → Focus totale sulla mesh")
        print()
        print("  dpi:")
        print("    Standard: 120")
        print("    Ultra-HR: 150")
        print("    → Dettagli ancora più fini")
        print("="*80)
        print()
        print("⚠️  ATTENZIONE:")
        print("   Tempo stimato: 15-20 minuti per 10 frames L3")
        print("   (Marching Cubes su griglia 128³ è computazionalmente intenso)")
        print()
        
        output_path = Path('L3_volumetric_ultra_highres.mp4')
        
        print("Generazione in corso...")
        print("(Progress logs ogni 10% del rendering)")
        print()
        
        viz.animate_volumetric_manifold(
            output_path=output_path,
            apply_smoothing=True,        # Gaussian smoothing ON
            show_field_lines=False,      # NO K lines (focus su mesh)
            fps=0.03,                    # Ultra slow (333 sec)
            dpi=150,                     # Alta risoluzione
            bitrate=3200,                # Bitrate più alto per dettagli
            show_progress=True
        )
        
        print("\n" + "="*80)
        print(" ✓ ULTRA-HIGH-RES RENDERING COMPLETATO")
        print("="*80)
        print(f"\nFile generato: {output_path}")
        print(f"Size: {output_path.stat().st_size / 1024**2:.2f} MB")
        print()
        print("CONFRONTO CON VERSIONE STANDARD:")
        print()
        print("Standard (L3_volumetric_comparison.mp4):")
        print("  - Griglia: 55³ (166k punti)")
        print("  - Sigma: 2.0")
        print("  - Field lines: 12")
        print("  - File: ~0.5 MB")
        print()
        print(f"Ultra-HR ({output_path.name}):")
        print("  - Griglia: 128³ (2.1M punti)")
        print("  - Sigma: 3.0")
        print("  - Field lines: 0 (focus mesh)")
        print(f"  - File: {output_path.stat().st_size / 1024**2:.2f} MB")
        print()
        print("RISULTATO ATTESO:")
        print("  ✓ Superfici estremamente lisce e morbide")
        print("  ✓ Eliminazione totale artefatti 'bollose'")
        print("  ✓ Transizioni graduali tra frames")
        print("  ✓ Texture chirale ultra-dettagliata")
        print()
        print("Questo è il rendering più 'liscio' possibile del manifold!")
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
    print()
    print("⚠️  Questo rendering richiede ~15-20 minuti.")
    print("   Vuoi procedere? (Ctrl+C per annullare)")
    print()
    
    import time
    time.sleep(3)
    
    generate_ultra_high_res()
