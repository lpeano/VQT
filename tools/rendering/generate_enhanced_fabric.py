"""
================================================================================
DENSITY+NETWORK ENHANCED - Parametri Estremi per Visualizzazione "Tessuto"
================================================================================

Versione ENHANCED del rendering density+network con:
- Alpha ancora più basso (0.01) per effetto "nebbia quantistica"
- Punti ancora più piccoli (s=0.3)
- Più vicini k-NN (k=12 invece di 6)
- Soglia similarità più permissiva (Δχ < 0.10)
- Linee più visibili (alpha=0.5)

Questo crea un effetto "tessuto" ancora più marcato.

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


def generate_enhanced_fabric():
    """Genera rendering 'tessuto' con parametri estremi."""
    
    print("="*80)
    print(" ENHANCED FABRIC RENDERING - Parametri Estremi")
    print("="*80)
    
    dataset_path = Path('cosmology_L3.h5')
    
    if not dataset_path.exists():
        print(f"ERROR: Dataset non trovato: {dataset_path}")
        sys.exit(1)
    
    config = VisualizationConfig(
        dpi=120,
        figsize=(16, 14)
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        print(f"  Frames: {viz.get_frame_count()}")
        
        print("\n" + "="*80)
        print(" ENHANCED FABRIC PARAMETERS")
        print("="*80)
        print("Modifiche rispetto a versione standard:")
        print("  - point_size: 1.0 → 0.3 (punti MOLTO piccoli)")
        print("  - point_alpha: 0.05 → 0.01 (effetto nebbia)")
        print("  - k_neighbors: 6 → 12 (rete più densa)")
        print("  - chi_threshold: 0.05 → 0.10 (più connessioni)")
        print("  - line_alpha: 0.3 → 0.5 (linee più visibili)")
        print()
        print("EFFETTO ATTESO:")
        print("  → Nuvola quantistica ancora più eterea")
        print("  → Rete di connessioni molto più fitta")
        print("  → 'Tessuto' del manifold ben visibile")
        print("="*80)
        print()
        
        output_path = Path('L3_enhanced_fabric.mp4')
        
        viz.animate_density_network(
            output_path=output_path,
            k_neighbors=12,              # Più vicini → rete più fitta
            chi_similarity_threshold=0.10,  # Più permissivo → più connessioni
            point_size=0.3,              # Punti molto più piccoli
            point_alpha=0.01,            # Nebbia quantistica
            line_alpha=0.5,              # Linee più visibili
            fps=0.03,                    # Ultra slow (333 sec)
            dpi=120,
            bitrate=2400,
            show_progress=True
        )
        
        print("\n" + "="*80)
        print(" ✓ ENHANCED FABRIC RENDERING COMPLETATO")
        print("="*80)
        print(f"\nFile generato: {output_path}")
        print(f"Size: {output_path.stat().st_size / 1024**2:.2f} MB")
        print()
        print("CONFRONTO CON VERSIONE STANDARD:")
        print()
        print("Standard (L3_density_network_comparison.mp4):")
        print("  - k=6, Δχ<0.05, s=1.0, alpha=0.05")
        print("  - ~300 edges (media)")
        print()
        print("Enhanced (L3_enhanced_fabric.mp4):")
        print("  - k=12, Δχ<0.10, s=0.3, alpha=0.01")
        print("  - ~1200+ edges (stimato, molto più denso)")
        print()
        print("QUALE USARE:")
        print("  - Standard: Bilanciato (vede sia punti che rete)")
        print("  - Enhanced: Massima visibilità 'tessuto' (focus su rete)")
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
    generate_enhanced_fabric()
