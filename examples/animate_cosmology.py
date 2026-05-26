"""
================================================================================
EXAMPLE: Animate Cosmology Evolution
================================================================================

Genera video MP4 dell'evoluzione temporale del manifold WQT usando il
ManifoldVisualizer nativo.

Questo esempio dimostra:
1. Caricamento dataset HDF5 multi-frame
2. Rendering animato con FuncAnimation
3. Export MP4 ad alta qualità
4. Configurazione parametri visualizzazione

REQUISITI:
----------
- Dataset HDF5 con multiple frames (es. cosmology_L1.h5, cosmology_L3_equilibrio.h5)
- ffmpeg installato nel sistema
- matplotlib >= 3.5.0

OUTPUT:
-------
- Video MP4 con evoluzione chirale del manifold
- Durata proporzionale a numero frames
- Qualità configurabile (DPI, bitrate, FPS)

USAGE:
------
python examples/animate_cosmology.py --input cosmology_L3_equilibrio.h5 --output L3_evolution.mp4 --fps 15

Author: WQT Physics Team
Date: 2026-05-26
================================================================================
"""

import argparse
import logging
from pathlib import Path
import sys

# Aggiungi parent directory al path per import wqt_oop
sys.path.insert(0, str(Path(__file__).parent.parent))

from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig


def main():
    """Main entry point."""
    
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description='Generate MP4 animation of WQT manifold evolution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Animate L1 dataset (24 segments, fast)
  python animate_cosmology.py --input cosmology_L1.h5 --output L1_evolution.mp4 --fps 10
  
  # Animate L3 equilibrium (13,824 segments, high quality)
  python animate_cosmology.py --input cosmology_L3_equilibrio.h5 \\
         --output L3_evolution_HQ.mp4 --fps 15 --dpi 150 --bitrate 3600
  
  # Chiral-only mode (no neutral vacuum)
  python animate_cosmology.py --input cosmology_L2.h5 \\
         --output L2_chiral.mp4 --mode chiral_only --fps 12

Notes:
  - Rendering time scales with (N_frames × N_segments)
  - L3 datasets with 20 frames @ 13,824 segments take ~5-10 minutes
  - Ensure ffmpeg is installed: scoop install ffmpeg (Windows)
        """
    )
    
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input HDF5 file path (e.g., cosmology_L3_equilibrio.h5)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('manifold_evolution.mp4'),
        help='Output MP4 file path (default: manifold_evolution.mp4)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'chiral_only', 'matter', 'antimatter'],
        default='full',
        help='Rendering mode (default: full)'
    )
    
    parser.add_argument(
        '--fps',
        type=int,
        default=10,
        help='Frames per second (default: 10)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=100,
        help='Video resolution DPI (default: 100, use 150+ for publications)'
    )
    
    parser.add_argument(
        '--bitrate',
        type=int,
        default=1800,
        help='Video bitrate in kbps (default: 1800, use 3600+ for HQ)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Validate input file
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    logger.info("="*80)
    logger.info(" WQT MANIFOLD ANIMATION GENERATOR")
    logger.info("="*80)
    logger.info(f"  Input:    {args.input}")
    logger.info(f"  Output:   {args.output}")
    logger.info(f"  Mode:     {args.mode}")
    logger.info(f"  FPS:      {args.fps}")
    logger.info(f"  DPI:      {args.dpi}")
    logger.info(f"  Bitrate:  {args.bitrate} kbps")
    logger.info("="*80)
    
    # Crea visualizzatore
    config = VisualizationConfig(
        marker_size=20 if args.input.stem.endswith('L1') else 10,  # Reduce for L2/L3
        dpi=args.dpi
    )
    
    viz = ManifoldVisualizer(config=config)
    
    try:
        # Carica stato
        logger.info("Loading HDF5 state...")
        viz.load_state(args.input)
        
        frame_count = viz.get_frame_count()
        metadata = viz.get_metadata()
        
        logger.info(f"  Frames loaded:   {frame_count}")
        logger.info(f"  Target level:    {metadata.get('target_level', 'N/A')}")
        logger.info(f"  Total segments:  {metadata.get('N_segments', 'N/A')}")
        logger.info(f"  Video duration:  {frame_count / args.fps:.1f} seconds")
        logger.info("")
        
        # Genera animazione
        logger.info("Generating animation (this may take several minutes)...")
        logger.info("")
        
        viz.animate_manifold(
            output_path=args.output,
            mode=args.mode,
            fps=args.fps,
            dpi=args.dpi,
            bitrate=args.bitrate,
            show_progress=True
        )
        
        logger.info("")
        logger.info("="*80)
        logger.info("✓ ANIMATION COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info(f"  Output file: {args.output.absolute()}")
        logger.info(f"  File size:   {args.output.stat().st_size / 1024**2:.2f} MB")
        logger.info("")
        logger.info("View with: vlc " + str(args.output))
        logger.info("="*80)
        
        return 0
    
    except Exception as e:
        logger.error(f"Animation failed: {e}", exc_info=args.verbose)
        return 1
    
    finally:
        viz.close()


if __name__ == '__main__':
    sys.exit(main())
