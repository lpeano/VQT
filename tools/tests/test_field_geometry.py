"""
Quick Test - Field Geometry Rendering
======================================

Test rapido per verificare che il nuovo sistema di rendering funzioni correttamente.
Esegui questo script per testare tutte le funzionalità in sequenza.

Usage:
    python test_field_geometry.py
"""

import sys
from pathlib import Path

# Setup path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))  # repo root (auto-shim)

from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_import():
    """Test che tutti gli import funzionino."""
    logger.info("TEST 1: Import verificati ✓")
    
    try:
        from scipy.spatial import KDTree
        logger.info("  - scipy.spatial.KDTree ✓")
    except ImportError:
        logger.warning("  - scipy.spatial.KDTree ✗ (installa: pip install scipy)")
        return False
    
    try:
        from skimage.measure import marching_cubes
        logger.info("  - skimage.measure.marching_cubes ✓")
    except ImportError:
        logger.warning("  - skimage.measure.marching_cubes ✗ (installa: pip install scikit-image)")
        logger.warning("    Isosurface rendering non disponibile")
    
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    logger.info("  - matplotlib Line3DCollection ✓")
    
    return True


def test_config():
    """Test configurazione."""
    logger.info("\nTEST 2: Configurazione")
    
    config = VisualizationConfig(
        torsion_threshold=1e-6,
        drift_threshold=1e-8,
        max_neighbors=6,
        grid_resolution=30
    )
    
    logger.info(f"  - torsion_threshold: {config.torsion_threshold}")
    logger.info(f"  - drift_threshold: {config.drift_threshold}")
    logger.info(f"  - max_neighbors: {config.max_neighbors}")
    logger.info(f"  - grid_resolution: {config.grid_resolution}")
    logger.info("  Configurazione ✓")


def test_visualizer_init():
    """Test inizializzazione visualizer."""
    logger.info("\nTEST 3: Inizializzazione ManifoldVisualizer")
    
    viz = ManifoldVisualizer()
    logger.info("  - Visualizer creato ✓")
    
    # Verifica metodi esistano
    assert hasattr(viz, '_compute_torsion_network')
    assert hasattr(viz, '_compute_torsion_quivers')
    assert hasattr(viz, '_compute_isosurface')
    assert hasattr(viz, 'render_field_geometry')
    assert hasattr(viz, 'animate_field_dynamics')
    
    logger.info("  - Metodi field geometry presenti ✓")
    
    viz.close()


def test_with_data():
    """Test con dataset reale (se disponibile)."""
    logger.info("\nTEST 4: Rendering con dataset")
    
    # Cerca dataset
    search_paths = [
        Path.cwd() / 'cosmology_L3.h5',
        Path(__file__).parent.parent / 'cosmology_L3.h5',
        Path.cwd() / 'cosmology_L1.h5',
        Path(__file__).parent.parent / 'cosmology_L1.h5'
    ]
    
    dataset_path = None
    for path in search_paths:
        if path.exists():
            dataset_path = path
            break
    
    if dataset_path is None:
        logger.warning("  - Nessun dataset trovato, skip test rendering")
        logger.warning("    (Posiziona un file .h5 nella directory per testare)")
        return
    
    logger.info(f"  - Dataset trovato: {dataset_path.name}")
    
    viz = ManifoldVisualizer()
    
    try:
        # Carica
        viz.load_state(dataset_path)
        logger.info(f"  - Dataset caricato: {viz.get_frame_count()} frames ✓")
        
        # Test rendering (no show, no save)
        logger.info("  - Test render_field_geometry (mode='network')...")
        
        # Rendering senza salvare/mostrare per velocità
        import matplotlib.pyplot as plt
        plt.ioff()  # Disattiva interactive mode
        
        viz.render_field_geometry(
            frame_index=-1,
            render_mode='network',
            save_path=None,
            show=False
        )
        
        logger.info("  - Rendering network completato ✓")
        
        # Chiudi tutte le figure
        plt.close('all')
        
    except Exception as e:
        logger.error(f"  - Errore durante rendering: {e}")
        raise
    finally:
        viz.close()


def run_all_tests():
    """Esegue tutti i test."""
    print("="*80)
    print(" FIELD GEOMETRY RENDERING - Quick Test Suite")
    print("="*80)
    
    try:
        # Test 1: Import
        if not test_import():
            print("\n⚠ ATTENZIONE: Alcune dipendenze mancanti")
            print("  Installa con: pip install scipy scikit-image")
        
        # Test 2: Config
        test_config()
        
        # Test 3: Init
        test_visualizer_init()
        
        # Test 4: Data (opzionale)
        test_with_data()
        
        print("\n" + "="*80)
        print(" ✓ TUTTI I TEST COMPLETATI CON SUCCESSO")
        print("="*80)
        print("\nIl sistema di Field Geometry Rendering è operativo!")
        print("\nProva i demo:")
        print("  python examples/demo_field_geometry.py --mode network+quivers")
        print("  python examples/demo_field_geometry.py --comparison")
        print("="*80)
        
    except Exception as e:
        print("\n" + "="*80)
        print(" ✗ TEST FALLITO")
        print("="*80)
        print(f"Errore: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()
