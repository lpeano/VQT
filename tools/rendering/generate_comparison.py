"""
================================================================================
GENERA CONFRONTO: VOLUMETRIC vs DENSITY+NETWORK
================================================================================

Script per generare ENTRAMBE le visualizzazioni del manifold L3:

1. VOLUMETRIC (Marching Cubes + Gaussian Smoothing)
   - Visione "macroscopica" del campo continuo
   - Ideale per fisica classica / campi gauge
   
2. DENSITY + NETWORK (k-NN Connectivity)
   - Visione "microscopica" dei segmenti discreti
   - Preserva fluttuazioni quantistiche L0
   - NO soglie arbitrarie

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


def generate_comparison():
    """Genera entrambe le visualizzazioni per confronto."""
    
    print("="*80)
    print(" VOLUMETRIC vs DENSITY+NETWORK - Confronto Rendering L3")
    print("="*80)
    
    dataset_path = Path('cosmology_L3.h5')
    
    if not dataset_path.exists():
        print(f"ERROR: Dataset non trovato: {dataset_path}")
        sys.exit(1)
    
    # Configurazione ottimizzata
    config = VisualizationConfig(
        smoothing_sigma=2.0,
        chi_isosurface_level=0.2,
        volumetric_resolution=55,
        K_streamline_density=12,
        K_streamline_length=0.5,
        chi_threshold_positive=0.1,
        chi_threshold_negative=-0.1,
        dpi=120,
        figsize=(14, 12)
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        # Carica dataset
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        print(f"  Frames: {viz.get_frame_count()}")
        
        # =================================================================
        # RENDERING 1: VOLUMETRIC (Campo Continuo)
        # =================================================================
        print("\n" + "="*80)
        print(" [1/2] VOLUMETRIC RENDERING (Marching Cubes)")
        print("="*80)
        print("Caratteristiche:")
        print("  - Isosuperficie del campo χ con Marching Cubes")
        print("  - Gaussian smoothing 3D (σ=2.0) per eliminare L0")
        print("  - Mesh continua con texture chirale dinamica")
        print("  - Linee di campo K (torsion trails)")
        print()
        
        volumetric_path = Path('L3_volumetric_comparison.mp4')
        
        viz.animate_volumetric_manifold(
            output_path=volumetric_path,
            apply_smoothing=True,
            show_field_lines=True,
            fps=0.03,  # Ultra slow (333 sec / 5.5 min)
            dpi=120,
            bitrate=2400,
            show_progress=True
        )
        
        print(f"\n✓ Volumetric rendering completato: {volumetric_path}")
        
        # =================================================================
        # RENDERING 2: DENSITY + NETWORK (Segmenti Discreti)
        # =================================================================
        print("\n" + "="*80)
        print(" [2/2] DENSITY + NETWORK RENDERING (k-NN Connectivity)")
        print("="*80)
        print("Caratteristiche:")
        print("  - Scatter cloud (13,824 segmenti, alpha=0.05)")
        print("  - k-NN connectivity (k=6 vicini)")
        print("  - Connessioni solo se |Δχ| < 0.05")
        print("  - NO smoothing, NO soglie (fluttuazioni L0 preservate)")
        print()
        
        density_path = Path('L3_density_network_comparison.mp4')
        
        viz.animate_density_network(
            output_path=density_path,
            k_neighbors=6,
            chi_similarity_threshold=0.05,
            point_size=1.0,
            point_alpha=0.05,
            line_alpha=0.3,
            fps=0.03,  # Ultra slow (333 sec / 5.5 min)
            dpi=120,
            bitrate=2400,
            show_progress=True
        )
        
        print(f"\n✓ Density+Network rendering completato: {density_path}")
        
        # =================================================================
        # CONFRONTO FINALE
        # =================================================================
        print("\n" + "="*80)
        print(" ✓ CONFRONTO COMPLETATO")
        print("="*80)
        print("\nFile generati:")
        print(f"\n1. VOLUMETRIC (Campo Continuo):")
        print(f"   {volumetric_path}")
        print(f"   Size: {volumetric_path.stat().st_size / 1024**2:.2f} MB")
        print(f"   Approccio: Marching Cubes + Gaussian Smoothing")
        print(f"   Visione: MACROSCOPICA (fisica classica)")
        
        print(f"\n2. DENSITY + NETWORK (Segmenti Discreti):")
        print(f"   {density_path}")
        print(f"   Size: {density_path.stat().st_size / 1024**2:.2f} MB")
        print(f"   Approccio: k-NN Connectivity (k=6, Δχ<0.05)")
        print(f"   Visione: MICROSCOPICA (fluttuazioni quantistiche)")
        
        print("\n" + "="*80)
        print(" QUALE RENDERING È \"GIUSTO\"?")
        print("="*80)
        print("ENTRAMBI sono corretti, ma mostrano aspetti diversi:")
        print()
        print("✓ VOLUMETRIC:")
        print("  - Mostra il campo χ come variabile continua")
        print("  - Ideale per vedere curvatura macroscopica")
        print("  - Smoothing elimina noise stocastico L0")
        print("  - Rivela strutture geometriche emergenti")
        print()
        print("✓ DENSITY + NETWORK:")
        print("  - Mostra la natura DISCRETA dei segmenti L0")
        print("  - Preserva fluttuazioni quantistiche")
        print("  - Rivela topologia del grafo di adiacenza")
        print("  - NO artefatti da soglie isosurface")
        print()
        print("Il manifold WQT ha ENTRAMBE le nature:")
        print("  - Microscopica: Foam quantistico discreto (L0)")
        print("  - Macroscopica: Campo continuo emergente (L1+)")
        print()
        print("Visualizza entrambi i video per la visione completa! 🌌")
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
    generate_comparison()
