"""
================================================================================
DEMO: Field Geometry Rendering
================================================================================

Script dimostrativo per il nuovo sistema di visualizzazione basato sulla
geometria delle forze del manifold WQT.

CARATTERISTICHE:
----------------
1. Network Edges: Visualizza le connessioni tra segmenti con torsione K > threshold
2. Torsion Quivers: Vettori direzionali delle forze nei hotspots
3. Isosurfaces: Superfici 3D del campo K tramite Marching Cubes
4. Field Dynamics: Animazione con deformazione della mesh

REQUISITI:
----------
- scikit-image (per Marching Cubes): pip install scikit-image
- scipy (per KDTree): pip install scipy
- Dataset HDF5 con contorsione_locale e drift_matrix

ESEMPI USO:
-----------
1. Rendering statico network+quivers:
   >>> python demo_field_geometry.py --mode network+quivers

2. Rendering con isosurface:
   >>> python demo_field_geometry.py --mode isosurface+quivers

3. Animazione dinamica:
   >>> python demo_field_geometry.py --animate --fps 15

AUTHOR: WQT Physics Team
DATE: 2026-05-26
================================================================================
"""

import sys
import logging
from pathlib import Path
import argparse

# Setup path per import wqt_oop
sys.path.insert(0, str(Path(__file__).parent.parent))

from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig


def demo_static_rendering(dataset_path: Path, mode: str = 'network+quivers'):
    """
    Dimostra rendering statico della geometria del campo.
    
    Parameters:
    -----------
    dataset_path : Path
        Path al file HDF5
    
    mode : str
        Modalità rendering ('network+quivers', 'isosurface+quivers', 'full', etc.)
    """
    print("="*80)
    print(" DEMO: Static Field Geometry Rendering")
    print("="*80)
    print(f"  Dataset: {dataset_path.name}")
    print(f"  Mode:    {mode}")
    print("="*80)
    
    # Configura visualizer
    config = VisualizationConfig(
        torsion_threshold=1e-6,      # Soglia K per network edges
        drift_threshold=1e-8,         # Soglia drift per quivers
        max_neighbors=6,              # Max connessioni per segmento
        edge_alpha=0.4,               # Trasparenza edges
        edge_linewidth=0.8,           # Spessore linee
        quiver_scale=1.5,             # Scala vettori
        quiver_alpha=0.8,             # Trasparenza quivers
        isosurface_level=0.3,         # Livello isosurface (30% del max K)
        grid_resolution=50,           # Risoluzione griglia marching cubes
        mesh_alpha=0.5,               # Trasparenza mesh
        dpi=150,                      # Alta risoluzione
        figsize=(14, 12)              # Figura grande
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        # Carica dataset
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        
        # Rendering ultimo frame
        output_path = Path('field_geometry_demo.png')
        
        print(f"\nRendering field geometry (mode: {mode})...")
        viz.render_field_geometry(
            frame_index=-1,
            render_mode=mode,
            save_path=output_path,
            show=True
        )
        
        print(f"\n✓ Rendering completato: {output_path}")
        
    finally:
        viz.close()


def demo_animation(dataset_path: Path, mode: str = 'network+quivers', fps: int = 10):
    """
    Dimostra animazione della dinamica del campo con mesh deformabile.
    
    Parameters:
    -----------
    dataset_path : Path
        Path al file HDF5
    
    mode : str
        Modalità rendering
    
    fps : int
        Frame per second
    """
    print("="*80)
    print(" DEMO: Field Dynamics Animation")
    print("="*80)
    print(f"  Dataset: {dataset_path.name}")
    print(f"  Mode:    {mode}")
    print(f"  FPS:     {fps}")
    print("="*80)
    
    # Configura visualizer
    config = VisualizationConfig(
        torsion_threshold=5e-7,       # Soglia più bassa per animazione
        drift_threshold=5e-9,
        max_neighbors=5,
        edge_alpha=0.5,
        edge_linewidth=0.6,
        quiver_scale=1.2,
        quiver_alpha=0.7,
        grid_resolution=40,           # Risoluzione ridotta per performance
        mesh_alpha=0.4,
        dpi=120,                      # DPI medio per bilanciare qualità/tempo
        figsize=(12, 10)
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        # Carica dataset
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        
        frame_count = viz.get_frame_count()
        print(f"  Frames disponibili: {frame_count}")
        
        # Genera animazione
        output_path = Path('field_dynamics_demo.mp4')
        
        print(f"\nGenerating animation...")
        print(f"  (This may take several minutes for large datasets)")
        
        viz.animate_field_dynamics(
            output_path=output_path,
            render_mode=mode,
            fps=fps,
            dpi=120,
            bitrate=2400,
            show_progress=True
        )
        
        print(f"\n✓ Animation completata: {output_path}")
        
    finally:
        viz.close()


def demo_comparison(dataset_path: Path):
    """
    Dimostra confronto side-by-side tra rendering classico e geometrico.
    
    Parameters:
    -----------
    dataset_path : Path
        Path al file HDF5
    """
    print("="*80)
    print(" DEMO: Comparison - Points vs. Field Geometry")
    print("="*80)
    
    viz = ManifoldVisualizer()
    
    try:
        viz.load_state(dataset_path)
        
        # 1. Rendering classico (nuvola punti)
        print("\n1. Rendering classico (particle cloud)...")
        viz.render_torsion_field(
            frame_index=-1,
            save_path='torsion_points_classic.png',
            show=False
        )
        print("   ✓ Salvato: torsion_points_classic.png")
        
        # 2. Rendering geometrico (network)
        print("\n2. Rendering geometrico (network)...")
        viz.render_field_geometry(
            frame_index=-1,
            render_mode='network',
            save_path='torsion_network_geometry.png',
            show=False
        )
        print("   ✓ Salvato: torsion_network_geometry.png")
        
        # 3. Rendering completo (network + quivers + isosurface)
        print("\n3. Rendering completo (full geometry)...")
        viz.render_field_geometry(
            frame_index=-1,
            render_mode='full',
            save_path='torsion_full_geometry.png',
            show=True
        )
        print("   ✓ Salvato: torsion_full_geometry.png")
        
        print("\n" + "="*80)
        print(" CONFRONTO COMPLETATO")
        print("="*80)
        print(" Ora puoi confrontare le tre immagini:")
        print("   - torsion_points_classic.png    (vecchio metodo)")
        print("   - torsion_network_geometry.png  (solo network)")
        print("   - torsion_full_geometry.png     (geometria completa)")
        print("="*80)
        
    finally:
        viz.close()


def demo_volumetric_rendering(dataset_path: Path):
    """
    Dimostra rendering volumetrico avanzato con isosuperficie e linee di campo K.
    
    Parameters:
    -----------
    dataset_path : Path
        Path al file HDF5
    """
    print("="*80)
    print(" DEMO: Volumetric Manifold Rendering")
    print("="*80)
    print(f"  Dataset: {dataset_path.name}")
    print("="*80)
    
    # Configura per rendering volumetrico
    config = VisualizationConfig(
        smoothing_sigma=2.5,          # Gaussian smoothing per eliminare rumore L0
        chi_isosurface_level=0.15,    # Livello isosuperficie χ
        K_streamline_density=15,      # Numero linee di campo K
        K_streamline_length=0.6,      # Lunghezza streamlines
        volumetric_resolution=60,     # Risoluzione griglia alta
        dpi=150,
        figsize=(14, 12)
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        # Carica dataset
        print(f"\nLoading dataset: {dataset_path}")
        viz.load_state(dataset_path)
        
        # Rendering volumetrico completo
        output_path = Path('volumetric_manifold_full.png')
        
        print(f"\nRendering volumetric manifold (isosurface + K field lines)...")
        viz.render_volumetric_manifold(
            frame_index=-1,
            show_isosurface=True,
            show_field_lines=True,
            apply_smoothing=True,
            save_path=output_path,
            show=False
        )
        print(f"   ✓ Salvato: {output_path}")
        
        # Solo isosuperficie (no smoothing per confronto)
        output_path_no_smooth = Path('volumetric_manifold_no_smoothing.png')
        
        print(f"\nRendering senza smoothing (per confronto)...")
        viz.render_volumetric_manifold(
            frame_index=-1,
            show_isosurface=True,
            show_field_lines=False,
            apply_smoothing=False,
            save_path=output_path_no_smooth,
            show=False
        )
        print(f"   ✓ Salvato: {output_path_no_smooth}")
        
        # Solo linee di campo K
        output_path_klines = Path('volumetric_K_fieldlines.png')
        
        print(f"\nRendering solo linee di campo K...")
        viz.render_volumetric_manifold(
            frame_index=-1,
            show_isosurface=False,
            show_field_lines=True,
            apply_smoothing=True,
            save_path=output_path_klines,
            show=True  # Mostra l'ultimo
        )
        print(f"   ✓ Salvato: {output_path_klines}")
        
        print("\n" + "="*80)
        print(" VOLUMETRIC RENDERING COMPLETATO")
        print("="*80)
        print(" File generati:")
        print(f"   - {output_path} (completo: isosurface + field lines)")
        print(f"   - {output_path_no_smooth} (no smoothing, confronto)")
        print(f"   - {output_path_klines} (solo linee di campo K)")
        print("="*80)
        
    finally:
        viz.close()


def main():
    """Entry point principale."""
    parser = argparse.ArgumentParser(
        description='Demo Field Geometry Rendering',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        default='cosmology_L3.h5',
        help='Nome file HDF5 (default: cosmology_L3.h5)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'network', 'quivers', 'isosurface', 
                 'network+quivers', 'isosurface+quivers'],
        default='network+quivers',
        help='Modalità rendering (default: network+quivers)'
    )
    
    parser.add_argument(
        '--animate',
        action='store_true',
        help='Genera animazione invece di rendering statico'
    )
    
    parser.add_argument(
        '--comparison',
        action='store_true',
        help='Genera confronto tra rendering classico e geometrico'
    )
    
    parser.add_argument(
        '--volumetric',
        action='store_true',
        help='Rendering volumetrico avanzato (isosurface + K field lines)'
    )
    
    parser.add_argument(
        '--fps',
        type=int,
        default=10,
        help='FPS per animazione (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Trova dataset
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        # Cerca in directory corrente e parent
        search_paths = [
            Path.cwd() / args.dataset,
            Path(__file__).parent.parent / args.dataset,
            Path(__file__).parent.parent / 'VQT' / args.dataset
        ]
        
        for path in search_paths:
            if path.exists():
                dataset_path = path
                break
        else:
            print(f"ERROR: Dataset non trovato: {args.dataset}")
            print(f"Percorsi cercati:")
            for path in search_paths:
                print(f"  - {path}")
            sys.exit(1)
    
    # Esegui demo
    if args.comparison:
        demo_comparison(dataset_path)
    elif args.volumetric:
        demo_volumetric_rendering(dataset_path)
    elif args.animate:
        demo_animation(dataset_path, mode=args.mode, fps=args.fps)
    else:
        demo_static_rendering(dataset_path, mode=args.mode)


if __name__ == '__main__':
    main()
