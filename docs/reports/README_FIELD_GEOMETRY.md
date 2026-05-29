# Field Geometry Rendering - Quick Start

## 🎯 Cosa è Cambiato

Il `ManifoldVisualizer` ora può renderizzare il manifold WQT come **geometria delle forze** invece che come nuvola di punti.

### Prima (Particle Cloud)
```python
viz.render_torsion_field(frame_index=-1)
```
![old](https://via.placeholder.com/400x300/cccccc/000000?text=Particle+Cloud)

### Dopo (Field Geometry)
```python
viz.render_field_geometry(
    frame_index=-1, 
    render_mode='network+quivers'
)
```
![new](https://via.placeholder.com/400x300/00aaff/ffffff?text=Network+%2B+Quivers)

---

## 🚀 Quick Start (5 minuti)

### 1. Installa dipendenze
```bash
cd VQT_repo
pip install scipy scikit-image  # Nuove dipendenze
```

### 2. Test rapido
```bash
python test_field_geometry.py
```

Output atteso:
```
TEST 1: Import verificati ✓
TEST 2: Configurazione ✓
TEST 3: Inizializzazione ManifoldVisualizer ✓
TEST 4: Rendering con dataset ✓
✓ TUTTI I TEST COMPLETATI CON SUCCESSO
```

### 3. Primo rendering
```bash
python examples/demo_field_geometry.py --mode network+quivers
```

### 4. Confronto vecchio vs nuovo
```bash
python examples/demo_field_geometry.py --comparison
```

Genera 3 immagini:
- `torsion_points_classic.png` - Vecchio metodo (punti)
- `torsion_network_geometry.png` - Nuovo metodo (network)
- `torsion_full_geometry.png` - Geometria completa

---

## 📊 Cosa Puoi Fare Ora

### 1. **Network Edges** - Visualizza Connessioni
```python
viz.render_field_geometry(render_mode='network')
```
- ✅ Mostra la "trama" del manifold
- ✅ Edges colorati per intensità torsione K
- ✅ Identifica clustering topologico

### 2. **Torsion Quivers** - Vettori di Forza
```python
viz.render_field_geometry(render_mode='quivers')
```
- ✅ Direzione delle forze di torsione
- ✅ Lunghezza ∝ intensità K
- ✅ Identifica hotspots dinamici

### 3. **Isosurfaces** - Superfici 3D
```python
viz.render_field_geometry(render_mode='isosurface')
```
- ✅ Manifold come struttura solida
- ✅ Marching Cubes algorithm
- ✅ Deformazioni geometriche visibili

### 4. **Animazioni Dinamiche**
```python
viz.animate_field_dynamics(
    output_path='evolution.mp4',
    render_mode='network+quivers',
    fps=10
)
```
- ✅ Mesh deformabile (no punti)
- ✅ Formazione/distruzione connessioni
- ✅ Propagazione onde di torsione

---

## 🎛️ Parametri Chiave

```python
from wqt_oop.visualizer import VisualizationConfig

config = VisualizationConfig(
    # Network
    torsion_threshold=1e-6,   # Soglia K per connessioni
    max_neighbors=6,          # Max edges per segmento
    
    # Quivers
    drift_threshold=1e-8,     # Soglia drift per hotspots
    quiver_scale=1.5,         # Scala lunghezza vettori
    
    # Isosurface
    isosurface_level=0.3,     # 30% del max(K)
    grid_resolution=50,       # Risoluzione griglia
)

viz = ManifoldVisualizer(config=config)
```

---

## 📖 Documentazione Completa

- **Full Guide**: [`docs/FIELD_GEOMETRY_RENDERING.md`](docs/FIELD_GEOMETRY_RENDERING.md)
- **Changelog**: [`CHANGELOG_FIELD_GEOMETRY.md`](CHANGELOG_FIELD_GEOMETRY.md)
- **API Docs**: Docstrings in `wqt_oop/visualizer.py`

---

## 🎨 Modalità Rendering

| Mode | Network | Quivers | Isosurface | Use Case |
|------|---------|---------|------------|----------|
| `network` | ✅ | ❌ | ❌ | Topologia connessioni |
| `quivers` | ❌ | ✅ | ❌ | Direzioni forze |
| `isosurface` | ❌ | ❌ | ✅ | Geometria manifold |
| **`network+quivers`** | ✅ | ✅ | ❌ | **Raccomandato** |
| `isosurface+quivers` | ❌ | ✅ | ✅ | Forze + geometria |
| `full` | ✅ | ✅ | ✅ | Analisi completa (slow) |

---

## 💡 Esempi Pratici

### Analisi Hotspots
```python
viz = ManifoldVisualizer(VisualizationConfig(
    drift_threshold=1e-7,  # Solo top hotspots
    quiver_scale=2.0       # Vettori più visibili
))
viz.load_state('cosmology_L3.h5')
viz.render_field_geometry(render_mode='quivers')
```

### Evoluzione Topologica
```python
viz.load_state('cosmology_L3.h5')
for idx in [0, 50, 100, -1]:  # Frames chiave
    viz.render_field_geometry(
        frame_index=idx,
        render_mode='network',
        save_path=f'topology_{idx:04d}.png',
        show=False
    )
```

### Animazione Pubblicazione
```python
viz.animate_field_dynamics(
    output_path='paper_animation.mp4',
    render_mode='network+quivers',
    fps=15,
    dpi=150,        # Alta qualità
    bitrate=3600    # Alta qualità
)
```

---

## ⚡ Performance Tips

### Rendering Statico
- ✅ Usa `network+quivers` (fast)
- ⚠️ `isosurface` può richiedere 10-20s
- ❌ Evita `full` se non necessario

### Animazioni
- ✅ **Raccomandato**: `network+quivers` (~8 min per 100 frames)
- ⚠️ `isosurface+quivers` (~25 min)
- ❌ `full` con isosurface (~45 min)

### Ottimizzazioni
```python
# Per animazioni veloci
config = VisualizationConfig(
    grid_resolution=40,   # Riduci per isosurface
    max_neighbors=5,      # Riduci connessioni
    torsion_threshold=1e-5  # Aumenta soglia
)
```

---

## 🐛 Troubleshooting

### "scikit-image not available"
```bash
pip install scikit-image
```

### "No segments above torsion threshold"
- Abbassa `torsion_threshold` in config
- Verifica che dataset contenga `contorsione_locale`

### Quivers non visibili
```python
config = VisualizationConfig(
    quiver_scale=3.0,      # Aumenta
    drift_threshold=1e-9   # Abbassa
)
```

### Animazione lenta
```python
# Usa network+quivers (NO isosurface)
viz.animate_field_dynamics(
    render_mode='network+quivers',
    dpi=100  # Riduci risoluzione
)
```

---

## 📦 Compatibilità

✅ **Backward compatible al 100%**

Tutti i vecchi metodi funzionano senza modifiche:
- `render_chiral_manifold()` ✓
- `animate_manifold()` ✓
- `render_torsion_field()` ✓

I nuovi metodi sono **addizionali**, non sostitutivi.

---

## 🔬 Fisica Implementata

### Network Edges
```
Connette segmenti con K > threshold
K = Tr(Θ²) = contorsione locale
```

### Quivers
```
Direzione: ∇K (gradiente torsione)
Lunghezza: |K| (intensità)
```

### Isosurface
```
S_L = {x ∈ ℝ³ : |K(x)| = L}
Algoritmo: Marching Cubes
```

---

## 🎯 Next Steps

1. **Prova i demo**: `python examples/demo_field_geometry.py --comparison`
2. **Leggi la doc completa**: `docs/FIELD_GEOMETRY_RENDERING.md`
3. **Sperimenta parametri**: Modifica `VisualizationConfig`
4. **Crea visualizzazioni custom**: Combina network+quivers+isosurface

---

## 📞 Support

- **Documentazione**: `docs/FIELD_GEOMETRY_RENDERING.md`
- **Test Suite**: `test_field_geometry.py`
- **Demo**: `examples/demo_field_geometry.py`

---

**Version**: 2.0.0  
**Author**: Scientific Visualization Engineer  
**Date**: 2026-05-26

🚀 **Buon rendering!**
