# Field Geometry Rendering System

## Panoramica

Il modulo `ManifoldVisualizer` è stato completamente riscritto per passare da un rendering **basato su punti** (particle cloud) a un rendering **basato sulla geometria delle forze**.

### Paradigma Shift: Da Punti a Forze

**Prima (Particle Cloud):**
```
❌ Manifold visualizzato come nuvola di punti sparsi
❌ Difficile vedere la struttura connessa
❌ Nessuna informazione sulla direzione delle forze
❌ Torsione visualizzata solo come colore sui punti
```

**Dopo (Field Geometry):**
```
✅ Manifold come network di connessioni (edges)
✅ Visualizzazione esplicita della "trama" del campo
✅ Vettori direzionali delle forze di torsione (quivers)
✅ Superfici isosurface 3D (Marching Cubes)
✅ Animazione con deformazione dinamica della mesh
```

---

## Nuove Funzionalità

### 1. **Network Edges** - Trama del Manifold

Visualizza le connessioni tra segmenti che presentano torsione **K > threshold**.

**Algoritmo:**
- Costruisce KDTree per ricerca efficiente dei vicini
- Per ogni segmento con K significativo, trova i K nearest neighbors
- Crea edge solo se entrambi i segmenti superano la soglia
- Colora edges in base all'intensità K (colormap plasma)

**Implementazione:**
```python
edges = viz._compute_torsion_network(positions, K_values)
# Ritorna: List[(idx_i, idx_j, K_avg)]
```

**Rendering:**
```python
from mpl_toolkits.mplot3d.art3d import Line3DCollection

segments = [[positions[i], positions[j]] for i, j, _ in edges]
lc = Line3DCollection(segments, colors=colors, linewidths=0.5, alpha=0.3)
ax.add_collection3d(lc)
```

**Fisica:**
- Le connessioni rappresentano "linee di forza" del campo di torsione
- Densità del network indica intensità locale del campo
- Clustering indica formazione di strutture topologiche (solitoni)

---

### 2. **Torsion Quivers** - Vettori di Forza

Visualizza direzione e intensità delle forze nei punti hotspot (drift > threshold).

**Algoritmo:**
- Identifica hotspots: segmenti con drift > threshold (o top 10% di K)
- Per ogni hotspot, calcola gradiente locale di K usando vicini
- Crea vettore: direzione = grad(K), lunghezza ∝ |K|

**Implementazione:**
```python
origins, vectors = viz._compute_torsion_quivers(positions, K_values, drift_values)
# origins: (M, 3) posizioni hotspots
# vectors: (M, 3) direzioni*intensità
```

**Rendering:**
```python
ax.quiver(
    origins[:, 0], origins[:, 1], origins[:, 2],
    vectors[:, 0], vectors[:, 1], vectors[:, 2],
    color='red', alpha=0.7, arrow_length_ratio=0.3
)
```

**Fisica:**
- Direzione: verso cui "fluisce" la torsione
- Lunghezza: intensità della forza locale
- Permette identificare vortici, sorgenti, pozzi del campo

---

### 3. **Isosurfaces** - Superfici di Campo 3D

Genera superfici isosurface del campo K usando **Marching Cubes** (scikit-image).

**Algoritmo:**
1. Interpola K su griglia 3D regolare (via KDTree)
2. Applica smoothing Gaussiano per continuità
3. Estrae isosurface a livello = `config.isosurface_level * max(K)`
4. Ritorna mesh triangolare (vertices, faces)

**Implementazione:**
```python
vertices, faces = viz._compute_isosurface(positions, K_values, level=None)
# vertices: (N_vertices, 3)
# faces: (N_faces, 3) indici triangoli
```

**Rendering:**
```python
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

triangles = vertices[faces]
poly = Poly3DCollection(triangles, alpha=0.4, facecolors='cyan', shade=True)
ax.add_collection3d(poly)
```

**Fisica:**
- Superficie rappresenta "equipotenziale" del campo K
- Deformazioni mostrano geometria non-Euclidea del manifold
- Topology changes evidenti durante transizioni di fase

---

### 4. **Field Dynamics** - Animazione con Mesh Deformabile

Animazione che aggiorna la geometria del campo invece dei punti.

**Differenza Chiave:**
- **Vecchio metodo**: Aggiorna posizioni punti scatter plot
- **Nuovo metodo**: Ricalcola edges/quivers/mesh ad ogni frame

**Implementazione:**
```python
def update(frame_idx):
    # Rimuovi vecchi oggetti grafici
    network_collection.remove()
    quiver_object.remove()
    mesh_collection.remove()
    
    # Ricalcola geometria per nuovo frame
    edges = viz._compute_torsion_network(positions, K_values)
    origins, vectors = viz._compute_torsion_quivers(positions, K_values)
    vertices, faces = viz._compute_isosurface(positions, K_values)
    
    # Crea nuovi oggetti grafici
    network_collection = Line3DCollection(...)
    quiver_object = ax.quiver(...)
    mesh_collection = Poly3DCollection(...)
```

**Fisica:**
- Visualizza propagazione onde di torsione
- Formazione/distruzione connessioni mostra dinamica topologica
- Deformazione mesh evidenzia instabilità geometriche

---

## Parametri di Configurazione

```python
from wqt_oop.visualizer import VisualizationConfig

config = VisualizationConfig(
    # --- NETWORK EDGES ---
    torsion_threshold=1e-6,      # Soglia K per creare connessioni
    max_neighbors=6,             # Max edges per segmento
    edge_alpha=0.3,              # Trasparenza edges (0-1)
    edge_linewidth=0.5,          # Spessore linee
    
    # --- TORSION QUIVERS ---
    drift_threshold=1e-8,        # Soglia drift per hotspots
    quiver_scale=1.0,            # Moltiplicatore lunghezza vettori
    quiver_alpha=0.7,            # Trasparenza quivers
    
    # --- ISOSURFACES ---
    isosurface_level=0.3,        # Livello come frazione max(K) (0-1)
    grid_resolution=50,          # Risoluzione griglia marching cubes
    mesh_alpha=0.4,              # Trasparenza superfici
    
    # --- GENERALE ---
    dpi=150,                     # Risoluzione output
    figsize=(12, 10)             # Dimensione figura (inches)
)
```

### Tuning Guidelines

**Network Edges:**
- `torsion_threshold`: 
  - Troppo basso → troppi edges, grafico affollato
  - Troppo alto → pochi edges, struttura non visibile
  - Raccomandato: 1e-6 a 1e-5 per L3
  
- `max_neighbors`: 
  - 4-6: Struttura locale chiara
  - 8-10: Network denso, buono per analisi topologica
  
**Quivers:**
- `drift_threshold`:
  - Controlla numero vettori visualizzati
  - Se troppi vettori, aumenta threshold
  
- `quiver_scale`:
  - Controlla lunghezza vettori
  - Aumenta se vettori troppo piccoli
  
**Isosurfaces:**
- `isosurface_level`:
  - 0.1-0.3: Superfici più estese
  - 0.5-0.7: Solo picchi intensi
  
- `grid_resolution`:
  - 30-40: Performance, superfici "blocky"
  - 50-70: Bilanciamento qualità/tempo
  - 80-100: Alta qualità, SLOW (minuti)

---

## API Usage

### Rendering Statico

```python
from wqt_oop.visualizer import ManifoldVisualizer

viz = ManifoldVisualizer()
viz.load_state('cosmology_L3.h5')

# Rendering completo
viz.render_field_geometry(
    frame_index=-1,              # Ultimo frame
    render_mode='full',          # Network + quivers + isosurface + points
    save_path='field_full.png',
    show=True
)

# Solo network
viz.render_field_geometry(
    render_mode='network',
    save_path='field_network.png'
)

# Network + quivers (raccomandato per analisi)
viz.render_field_geometry(
    render_mode='network+quivers',
    save_path='field_forces.png'
)

# Isosurface + quivers
viz.render_field_geometry(
    render_mode='isosurface+quivers',
    save_path='field_surface.png'
)

viz.close()
```

### Animazione Dinamica

```python
viz = ManifoldVisualizer()
viz.load_state('cosmology_L3.h5')

viz.animate_field_dynamics(
    output_path='field_evolution.mp4',
    render_mode='network+quivers',  # Raccomandato per performance
    fps=10,
    dpi=120,
    bitrate=2400,
    show_progress=True
)

viz.close()
```

### Modalità Rendering

| Mode | Network | Quivers | Isosurface | Points | Use Case |
|------|---------|---------|------------|--------|----------|
| `full` | ✅ | ✅ | ✅ | ✅ | Analisi completa (SLOW) |
| `network` | ✅ | ❌ | ❌ | ❌ | Studio topologia connessioni |
| `quivers` | ❌ | ✅ | ❌ | ❌ | Studio direzioni forze |
| `isosurface` | ❌ | ❌ | ✅ | ❌ | Geometria manifold |
| `network+quivers` | ✅ | ✅ | ❌ | ❌ | **Raccomandato** (bilanciato) |
| `isosurface+quivers` | ❌ | ✅ | ✅ | ❌ | Forze + geometria |

---

## Esempi Pratici

### 1. Quick Start

```bash
# Rendering statico network+quivers
cd VQT_repo/examples
python demo_field_geometry.py --mode network+quivers

# Animazione
python demo_field_geometry.py --animate --fps 15

# Confronto vecchio vs nuovo rendering
python demo_field_geometry.py --comparison
```

### 2. Analisi Hotspots

```python
viz = ManifoldVisualizer()
viz.load_state('cosmology_L3.h5')

# Configura per evidenziare solo hotspots intensi
config = VisualizationConfig(
    drift_threshold=1e-7,  # Solo top hotspots
    quiver_scale=2.0,      # Vettori più lunghi
    quiver_alpha=0.9       # Più opachi
)

viz = ManifoldVisualizer(config=config)
viz.load_state('cosmology_L3.h5')

viz.render_field_geometry(
    render_mode='quivers',
    save_path='hotspots_analysis.png'
)
```

### 3. Studio Evoluzione Topologica

```python
# Genera frame specifici per paper
viz = ManifoldVisualizer()
viz.load_state('cosmology_L3.h5')

for idx in [0, 50, 100, 150, -1]:  # Inizio, intermedi, fine
    viz.render_field_geometry(
        frame_index=idx,
        render_mode='network',
        save_path=f'topology_frame_{idx:04d}.png',
        show=False
    )
```

---

## Performance

### Benchmarks (Intel i7, 16GB RAM)

**Rendering Statico (L3, 13824 segments, ultimo frame):**

| Mode | Network | Quivers | Isosurface | Time |
|------|---------|---------|------------|------|
| `network` | 1247 edges | - | - | ~2s |
| `quivers` | - | 342 vectors | - | ~3s |
| `isosurface` | - | - | 50³ grid | ~15s |
| `network+quivers` | 1247 | 342 | - | ~5s |
| `full` | 1247 | 342 | 50³ grid | ~20s |

**Animazione (100 frames):**

| Mode | Grid Res | DPI | Time | File Size |
|------|----------|-----|------|-----------|
| `network+quivers` | N/A | 100 | ~8 min | 12 MB |
| `isosurface+quivers` | 40³ | 100 | ~25 min | 18 MB |
| `full` | 50³ | 120 | ~45 min | 35 MB |

### Ottimizzazione Tips

1. **Usa `network+quivers` per animazioni** (NO isosurface)
2. **Grid resolution**: Max 50 per animazioni, 70 per singoli frame
3. **Sub-sample points** in mode `full`: già implementato (1/2000)
4. **Bitrate video**: 1800 (standard), 2400 (alta), 3600 (pubblicazioni)

---

## Troubleshooting

### Errore: "scikit-image not available"

```bash
pip install scikit-image
```

### Errore: "No segments above torsion threshold"

- Abbassa `torsion_threshold` in config
- Verifica che il dataset contenga `contorsione_locale`

### Errore: "Marching cubes failed"

- Riduci `grid_resolution` (es. 30-40)
- Verifica che K abbia variabilità spaziale sufficiente

### Animazione troppo lenta

- Usa `render_mode='network+quivers'` (NO isosurface)
- Riduci `dpi` (80-100)
- Aumenta `bitrate` per compensare perdita qualità

### Quivers non visibili

- Aumenta `quiver_scale` (es. 2.0-3.0)
- Abbassa `drift_threshold`
- Verifica che il dataset contenga `drift_matrix`

---

## Dipendenze

```bash
# Core requirements (già presenti)
pip install numpy h5py matplotlib

# Nuove dipendenze per field geometry
pip install scipy scikit-image

# Opzionale (animazioni)
# Richiede ffmpeg installato nel sistema
# Windows: scoop install ffmpeg
# Linux: sudo apt install ffmpeg
```

---

## Fisica Sottostante

### Torsione K e Geometria

La contorsione locale **K** rappresenta la **densità di informazione geometrica** del manifold:

$$
K = \text{Tr}(\Theta^2), \quad \Theta = \text{torsione\_matrix}
$$

- **K > 0**: Curvatura intrinseca, deformazione geometrica
- **Network edges**: Connettono regioni con K elevato → "linee di forza" del campo
- **Gradiente di K**: Direzione del "flusso" di informazione geometrica

### Drift e Hotspots

Il drift misura l'**instabilità locale** del campo:

$$
\text{drift} = \|\partial_t \chi\|
$$

- **Hotspots** (drift > threshold): Punti di rapida evoluzione
- **Quivers**: Visualizzano direzione della "pressione" topologica
- Clustering di quivers → formazione strutture coerenti (solitoni)

### Isosurfaces e Topologia

La superficie isosurface a livello **L**:

$$
S_L = \{x \in \mathbb{R}^3 : |K(x)| = L\}
$$

- **Componenti connesse**: Numero di regioni ad alta torsione separate
- **Genus**: Buchi topologici (handles)
- **Deformazioni**: Evidenziano transizioni di fase geometriche

---

## Roadmap Future

- [ ] **Interactive 3D Viewer** (plotly/mayavi)
- [ ] **Streamlines** del campo gradK
- [ ] **Volume Rendering** invece di isosurface
- [ ] **Topology Analysis**: Calcolo automatico Betti numbers
- [ ] **Multi-scale Network**: Edges a diversi thresholds
- [ ] **VR Export**: Export mesh per visualizzazione VR

---

## Riferimenti

- Marching Cubes: Lorensen & Cline (1987)
- KDTree: scipy.spatial documentation
- Field Topology: Helman & Hesselink (1991)

---

**AUTHOR**: WQT Physics Team - Scientific Visualization Engineer  
**DATE**: 2026-05-26  
**VERSION**: 2.0.0
