# WQT Examples - Visualization & Animation

This directory contains example scripts demonstrating the native visualization capabilities of the WQT_OOP package.

## 📊 Available Examples

### 1. `animate_cosmology.py` - Manifold Evolution Animation

Generates MP4 video animations of the temporal evolution of the WQT manifold, visualizing chiral field dynamics and topological phase transitions.

**Features:**
- Frame-by-frame evolution rendering
- Chiral field color-coding (DX/SX/Neutral)
- Configurable quality (DPI, bitrate, FPS)
- Progress tracking
- Multi-mode rendering

**Usage:**

```bash
# Basic animation (default settings)
python examples/animate_cosmology.py --input cosmology_L1.h5 --output L1_evolution.mp4

# High-quality animation for publications
python examples/animate_cosmology.py \
  --input cosmology_L3_equilibrio.h5 \
  --output L3_HQ.mp4 \
  --fps 15 \
  --dpi 150 \
  --bitrate 3600

# Chiral-only mode (no vacuum states)
python examples/animate_cosmology.py \
  --input cosmology_L2.h5 \
  --output L2_chiral.mp4 \
  --mode chiral_only \
  --fps 12
```

**Parameters:**
- `--input`: Path to HDF5 dataset (required)
- `--output`: Output MP4 file path (default: manifold_evolution.mp4)
- `--mode`: Rendering mode (choices: full, chiral_only, matter, antimatter)
- `--fps`: Frames per second (default: 10)
- `--dpi`: Video resolution (default: 100, use 150+ for publications)
- `--bitrate`: Video bitrate in kbps (default: 1800, use 3600+ for HQ)
- `--verbose`: Enable debug logging

**Requirements:**
- ffmpeg installed on system:
  - Windows: `scoop install ffmpeg`
  - Linux: `apt install ffmpeg`
  - macOS: `brew install ffmpeg`

**Performance:**
- L1 (24 segments, 100 frames): ~5-10 seconds
- L2 (576 segments, 50 frames): ~30-60 seconds
- L3 (13,824 segments, 20 frames): ~3-5 minutes

---

## 🎨 Rendering Modes

### `full` (default)
Renders all segments with chiral color-coding:
- **Blue**: Right-handed (χ > +0.1) - "Matter"
- **Red**: Left-handed (χ < -0.1) - "Antimatter"
- **Gray (transparent)**: Neutral (|χ| ≤ 0.1) - "Vacuum"

### `chiral_only`
Renders only chiral segments (no neutral vacuum states).
Useful for highlighting matter/antimatter distribution.

### `matter`
Renders only right-handed segments with gradient coloring
proportional to χ magnitude.

### `antimatter`
Renders only left-handed segments with gradient coloring
proportional to |χ| magnitude.

---

## 🧪 Example Workflows

### Workflow 1: Quick Preview Animation

```bash
# Generate low-quality preview (fast rendering)
python examples/animate_cosmology.py \
  --input cosmology_L1.h5 \
  --output preview.mp4 \
  --fps 10 \
  --dpi 80 \
  --bitrate 1200
```

### Workflow 2: Publication-Quality Video

```bash
# High-quality animation for papers/presentations
python examples/animate_cosmology.py \
  --input cosmology_L3_equilibrio.h5 \
  --output publication_L3.mp4 \
  --fps 15 \
  --dpi 150 \
  --bitrate 3600 \
  --verbose
```

### Workflow 3: Comparative Analysis

```bash
# Generate animations for all levels
for level in L1 L2 L3; do
  python examples/animate_cosmology.py \
    --input cosmology_${level}.h5 \
    --output ${level}_evolution.mp4 \
    --fps 12
done
```

---

## 📁 Output Files

Generated MP4 files are saved in the current working directory unless an absolute path is specified with `--output`.

**Typical file sizes:**
- L1 @ 10fps, 100 DPI: ~0.3 MB
- L2 @ 10fps, 100 DPI: ~1-2 MB
- L3 @ 15fps, 150 DPI: ~5-10 MB

---

## 🔧 Troubleshooting

### Error: "ffmpeg not found"

**Solution:** Install ffmpeg on your system:

```bash
# Windows (using Scoop)
scoop install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS (using Homebrew)
brew install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

### Error: "HDF5 file missing '/frames' group"

**Solution:** Ensure the HDF5 file was generated with the `HDF5Logger` from `wqt_oop` package. The schema must include:
- `/frames/frame_NNNNNN/` groups
- Required datasets: `positions`, `chi_values`, `contorsione_locale`

### Performance Issues (L3 rendering too slow)

**Solutions:**
- Reduce DPI: `--dpi 80` (default 100)
- Reduce bitrate: `--bitrate 1200` (default 1800)
- Reduce FPS: `--fps 8` (default 10)
- Use `--mode chiral_only` to skip neutral segments

---

## 📚 API Usage (Python)

You can also use the `ManifoldVisualizer` API directly in your scripts:

```python
from wqt_oop.visualizer import ManifoldVisualizer, VisualizationConfig

# Create visualizer with custom config
config = VisualizationConfig(
    chi_threshold_positive=0.15,  # Stricter chirality threshold
    marker_size=10,
    dpi=150
)

viz = ManifoldVisualizer(config=config)

# Load dataset
viz.load_state('cosmology_L3_equilibrio.h5')

# Generate animation
viz.animate_manifold(
    output_path='custom_animation.mp4',
    mode='chiral_only',
    fps=15,
    dpi=150,
    bitrate=3600
)

# Cleanup
viz.close()
```

---

## 🌌 Physics Interpretation

The animations visualize key physics observables:

1. **Spatial segregation** of matter (DX) and antimatter (SX)
2. **Soliton formation** (clustering of chiral states)
3. **Torsion wave propagation** (via color intensity changes)
4. **Domain wall dynamics** (boundaries between DX/SX regions)
5. **CP symmetry breaking** (asymmetry in DX vs SX populations)

Use these animations to identify:
- Phase transitions
- Topological defects
- Energy localization
- Vacuum structure evolution

---

**Author:** WQT Physics Team  
**Date:** 2026-05-26  
**Version:** 1.0.0
