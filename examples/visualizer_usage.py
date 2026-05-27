"""
================================================================================
EXAMPLE: Basic Usage of ManifoldVisualizer
================================================================================

Demonstrates native integration of visualization module in wqt_oop package.

This script shows how to:
1. Load HDF5 simulation data
2. Render chiral manifold (matter/antimatter distribution)
3. Visualize torsion field K
4. Generate publication-quality plots

Author: WQT Physics Team
Date: 2026-05-26
================================================================================
"""

from pathlib import Path
from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig

# ============================================================================
# Example 1: Basic Usage with Default Configuration
# ============================================================================

print("="*80)
print(" EXAMPLE 1: Basic Chiral Rendering")
print("="*80)

# Create visualizer with default settings
viz = ManifoldVisualizer()

# Load HDF5 dataset
hdf5_path = Path(r'C:\Users\lpeano\plank\VQT\cosmology_L3_equilibrio.h5')
viz.load_state(hdf5_path)

# Render final frame (full mode: matter + antimatter + vacuum)
viz.render_chiral_manifold(
    mode='full',
    frame_index=-1,  # -1 = last frame
    save_path='example_chiral_full.png',
    show=False  # Set True for interactive plot
)

print("\n✓ Chiral manifold rendered → example_chiral_full.png")

# Render torsion field
viz.render_torsion_field(
    frame_index=-1,
    save_path='example_torsion.png',
    show=False
)

print("✓ Torsion field rendered → example_torsion.png")

# Cleanup
viz.close()


# ============================================================================
# Example 2: Custom Configuration (Publication-Quality)
# ============================================================================

print("\n" + "="*80)
print(" EXAMPLE 2: Custom Configuration for Publication")
print("="*80)

# Create custom config for high-quality rendering
custom_config = VisualizationConfig(
    chi_threshold_positive=0.05,   # More sensitive chirality detection
    chi_threshold_negative=-0.05,
    color_right='darkblue',
    color_left='darkred',
    color_neutral='whitesmoke',
    marker_size=15,               # Smaller markers for dense datasets
    alpha_neutral=0.1,            # More transparent vacuum
    alpha_chiral=0.9,             # More opaque chiral states
    dpi=300,                      # Publication quality
    figsize=(14, 12)              # Larger figure
)

viz_hq = ManifoldVisualizer(config=custom_config)
viz_hq.load_state(hdf5_path)

# Render only chiral states (no vacuum)
viz_hq.render_chiral_manifold(
    mode='chiral_only',
    frame_index=-1,
    save_path='example_chiral_hq.png',
    show=False
)

print("\n✓ High-quality chiral rendering → example_chiral_hq.png (300 DPI)")

viz_hq.close()


# ============================================================================
# Example 3: Time Evolution Analysis
# ============================================================================

print("\n" + "="*80)
print(" EXAMPLE 3: Time Evolution (Multiple Frames)")
print("="*80)

viz_time = ManifoldVisualizer()
viz_time.load_state(hdf5_path)

# Render frames at different times
frame_indices = [0, 25, 50, 75, 99]
output_dir = Path('evolution_frames')
output_dir.mkdir(exist_ok=True)

for idx in frame_indices:
    if idx < viz_time.get_frame_count():
        viz_time.render_frame(
            step_index=idx,
            save_path=output_dir / f'frame_{idx:03d}.png',
            show=False
        )
        print(f"  ✓ Frame {idx:03d} rendered")

print(f"\n✓ Time evolution rendered → {output_dir}/ ({len(frame_indices)} frames)")

viz_time.close()


# ============================================================================
# Example 4: Context Manager (Recommended Pattern)
# ============================================================================

print("\n" + "="*80)
print(" EXAMPLE 4: Context Manager Pattern (Best Practice)")
print("="*80)

# Automatic resource cleanup with context manager
with ManifoldVisualizer() as viz_ctx:
    viz_ctx.load_state(hdf5_path)
    
    # Get metadata
    meta = viz_ctx.get_metadata()
    print(f"\nDataset metadata:")
    print(f"  Total frames: {viz_ctx.get_frame_count()}")
    for key, value in meta.items():
        print(f"  {key}: {value}")
    
    # Render matter-only view
    viz_ctx.render_chiral_manifold(
        mode='matter',
        frame_index=-1,
        save_path='example_matter_only.png',
        show=False
    )
    print("\n✓ Matter-only rendering → example_matter_only.png")

# File automatically closed after context exit


# ============================================================================
# Summary
# ============================================================================

print("\n" + "="*80)
print(" SUMMARY")
print("="*80)
print("""
Generated files:
  - example_chiral_full.png    (Full chiral manifold)
  - example_torsion.png        (Torsion field K)
  - example_chiral_hq.png      (High-quality chiral-only, 300 DPI)
  - example_matter_only.png    (Matter distribution only)
  - evolution_frames/          (Time evolution sequence)

Key Features Demonstrated:
  ✓ Native integration in wqt_oop package
  ✓ HDF5 direct loading (SWMR-compatible)
  ✓ Chiral field rendering (χ classification)
  ✓ Torsion field visualization (K)
  ✓ Custom configuration (publication-quality)
  ✓ Context manager pattern (resource safety)
  ✓ Time evolution analysis (multi-frame)

Next Steps:
  - Integrate with analyze_hotspots.py for spatial correlation
  - Add animation export (MP4/GIF)
  - Implement mayavi backend for interactive 3D
""")

print("="*80)
print(" ✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
print("="*80)
