"""
Genera video volumetrico da cosmology_L3_NEW.h5
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))  # repo root (auto-shim)

from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("="*80)
print(" VOLUMETRIC ANIMATION FROM L3_NEW.h5")
print("="*80)

# Config
config = VisualizationConfig(
    torsion_threshold=0.1,
    drift_threshold=0.01,
    smoothing_sigma=2.0,
    chi_isosurface_level=0.2,
    volumetric_resolution=55,
    K_streamline_density=12,
    dpi=120
)

# Visualizer
viz = ManifoldVisualizer(config)

# Load L3_NEW
dataset_path = Path('cosmology_L3_NEW.h5')
print(f"\nLoading dataset: {dataset_path}")
viz.load_state(dataset_path)
print(f"  Frames: {viz.get_frame_count()}")

# Animate
output = Path("L3_NEW_volumetric.mp4")
print(f"\nGenerating volumetric animation...")
print(f"  Output: {output}")
print(f"  This will take several minutes...")
print()

viz.animate_volumetric_manifold(
    output_path=output,
    apply_smoothing=True,
    show_field_lines=True,
    fps=0.03,  # Ultra slow motion
    dpi=120,
    bitrate=2400,
    show_progress=True
)

print(f"\n✓ Video saved: {output}")
