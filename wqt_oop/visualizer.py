"""
================================================================================
MANIFOLD VISUALIZER - Rendering 3D Native per Analisi Fisica
================================================================================

Modulo di visualizzazione nativo per il manifold frattale WQT.
Integrato direttamente nel core package per analisi fisica immediata.

CHIRALITÀ FIELD χ:
------------------
- χ > +0.1  → BLU (Destrorsa, "materia")
- χ < -0.1  → ROSSO (Sinistrorsa, "antimateria")
- |χ| ≤ 0.1 → BIANCO/Trasparente (Vuoto quantistico)

FEATURES:
---------
1. Caricamento diretto da HDF5 (SWMR-compatible)
2. Rendering singolo frame o animazione temporale
3. Codifica chirale nativa del campo scalare
4. Integrazione con schema dati esistente
5. Export PNG/MP4 per pubblicazioni

ESEMPI USO:
-----------
>>> from wqt_oop.visualizer import ManifoldVisualizer
>>> viz = ManifoldVisualizer()
>>> viz.load_state('cosmology_L3.h5')
>>> viz.render_chiral_manifold(mode='full', save_path='manifold.png')
>>> viz.render_frame(step_index=50, save_path='frame_50.png')

DIPENDENZE:
-----------
- matplotlib >= 3.5.0 (rendering 2D/3D)
- numpy >= 1.20.0 (data processing)
- h5py >= 3.0.0 (HDF5 I/O)
- mayavi (opzionale, rendering avanzato)

AUTHOR: WQT Physics Team (Senior Software Architect)
DATE: 2026-05-26
================================================================================
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
from dataclasses import dataclass

import numpy as np
import h5py
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from scipy.spatial import KDTree
from scipy.ndimage import gaussian_filter
try:
    from skimage.measure import marching_cubes
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    logging.warning("scikit-image not available. Isosurface rendering disabled.")

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfig:
    """
    Configurazione parametri visualizzazione.
    
    Attributes:
    -----------
    chi_threshold_positive : float
        Soglia per classificare χ come destrorsa (default: 0.1)
    
    chi_threshold_negative : float
        Soglia per classificare χ come sinistrorsa (default: -0.1)
    
    color_right : str
        Colore destrorsa (default: 'blue')
    
    color_left : str
        Colore sinistrorsa (default: 'red')
    
    color_neutral : str
        Colore vuoto quantistico (default: 'lightgray')
    
    marker_size : int
        Dimensione markers scatter plot (default: 20)
    
    alpha_neutral : float
        Trasparenza vuoto (0.0-1.0, default: 0.2)
    
    alpha_chiral : float
        Trasparenza stati chirali (0.0-1.0, default: 0.8)
    
    dpi : int
        Risoluzione output PNG (default: 150)
    
    figsize : Tuple[int, int]
        Dimensione figura in inches (default: (12, 10))
    
    # FIELD-BASED RENDERING PARAMETERS
    torsion_threshold : float
        Soglia torsione K per visualizzare connessioni (default: 1e-6)
    
    drift_threshold : float
        Soglia drift per identificare hotspots (default: 1e-8)
    
    max_neighbors : int
        Numero massimo vicini per network edges (default: 6)
    
    edge_alpha : float
        Trasparenza edges del network (default: 0.3)
    
    edge_linewidth : float
        Spessore linee network (default: 0.5)
    
    quiver_scale : float
        Fattore scala lunghezza vettori (default: 1.0)
    
    quiver_alpha : float
        Trasparenza quivers (default: 0.7)
    
    isosurface_level : float
        Livello isosurface come frazione max(K) (default: 0.3)
    
    grid_resolution : int
        Risoluzione griglia per marching cubes (default: 50)
    
    mesh_alpha : float
        Trasparenza superfici isosurface (default: 0.4)
    """
    chi_threshold_positive: float = 0.1
    chi_threshold_negative: float = -0.1
    color_right: str = 'blue'
    color_left: str = 'red'
    color_neutral: str = 'lightgray'
    marker_size: int = 20
    alpha_neutral: float = 0.2
    alpha_chiral: float = 0.8
    dpi: int = 150
    figsize: Tuple[int, int] = (12, 10)
    
    # Field-based rendering
    torsion_threshold: float = 1e-6
    drift_threshold: float = 1e-8
    max_neighbors: int = 6
    edge_alpha: float = 0.3
    edge_linewidth: float = 0.5
    quiver_scale: float = 1.0
    quiver_alpha: float = 0.7
    isosurface_level: float = 0.3
    grid_resolution: int = 50
    mesh_alpha: float = 0.4
    
    # Volumetric rendering
    smoothing_sigma: float = 2.0         # Sigma per Gaussian smoothing 3D
    chi_isosurface_level: float = 0.15   # Livello isosurface per campo chi
    K_streamline_density: int = 10       # Numero linee di campo K
    K_streamline_length: float = 0.5     # Lunghezza max streamlines (frazione domain)
    volumetric_resolution: int = 60      # Risoluzione griglia volumetrica


class ManifoldVisualizer:
    """
    [LEGGE FISICA: Visualizzazione Chirale del Campo Scalare]
    
    Il campo χ rappresenta la "fase topologica" del manifold. La chiralità
    emerge dalla rottura di simmetria CP nel doppio pozzo:
    
        V(χ) = -β·χ² + χ⁴/4
    
    Stati chirali:
        - χ > 0: Vacuum destrorso (particelle standard)
        - χ < 0: Vacuum sinistrorso (antiparticelle)
        - χ ≈ 0: Instabilità del vuoto (fluttuazioni quantistiche)
    
    La visualizzazione codifica spazialmente la distribuzione di materia/antimateria
    e identifica regioni di transizione di fase.
    
    Methods:
    --------
    load_state(hdf5_path) : Carica stato manifold da HDF5
    render_chiral_manifold(mode, frame_index, save_path) : Rendering 3D campo χ
    render_frame(step_index, save_path) : Rendering singolo frame temporale
    render_torsion_field(frame_index, save_path) : Rendering campo K
    get_frame_count() : Numero frames disponibili
    get_metadata() : Metadati simulazione
    close() : Chiude file HDF5
    """
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        """
        Inizializza visualizzatore.
        
        Parameters:
        -----------
        config : VisualizationConfig, optional
            Configurazione rendering (default: parametri standard)
        """
        self.config = config or VisualizationConfig()
        self.hdf5_file: Optional[h5py.File] = None
        self.frames_group: Optional[h5py.Group] = None
        self.metadata: Dict = {}
        self.frame_names: List[str] = []
        
        logger.info("ManifoldVisualizer initialized")
        logger.info(f"  Chi thresholds: [{self.config.chi_threshold_negative:.2f}, {self.config.chi_threshold_positive:.2f}]")
        logger.info(f"  Color scheme: {self.config.color_left} / {self.config.color_neutral} / {self.config.color_right}")
    
    def load_state(self, hdf5_path: Union[str, Path]) -> None:
        """
        Carica stato manifold da file HDF5.
        
        Compatibile con schema HDF5Logger:
            /frames/frame_NNNNNN/{positions, chi_values, contorsione_locale, ...}
            /metadata/{target_level, N_segments, dt, ...}
        
        Parameters:
        -----------
        hdf5_path : str or Path
            Path file HDF5 contenente simulazione
        
        Raises:
        -------
        FileNotFoundError
            Se file non esiste
        
        ValueError
            Se schema HDF5 non compatibile
        """
        hdf5_path = Path(hdf5_path)
        
        if not hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")
        
        logger.info(f"Loading HDF5 state from: {hdf5_path}")
        
        # Apri file in modalità read-only
        self.hdf5_file = h5py.File(hdf5_path, 'r')
        
        # Valida schema
        if 'frames' not in self.hdf5_file:
            raise ValueError("HDF5 file missing '/frames' group. Invalid schema.")
        
        self.frames_group = self.hdf5_file['frames']
        
        # Estrai lista frames ordinati
        self.frame_names = sorted([
            k for k in self.frames_group.keys() 
            if k.startswith('frame_')
        ])
        
        if len(self.frame_names) == 0:
            raise ValueError("No frames found in HDF5 file")
        
        # Carica metadata (se disponibile)
        if 'metadata' in self.hdf5_file:
            meta_group = self.hdf5_file['metadata']
            self.metadata = {
                key: meta_group[key][()] if key in meta_group else None
                for key in ['target_level', 'N_segments', 'dt', 'chi_mean', 'spatial_extent']
            }
        
        # Log info
        logger.info(f"  Frames loaded: {len(self.frame_names)}")
        logger.info(f"  Target level:  {self.metadata.get('target_level', 'N/A')}")
        logger.info(f"  N segments:    {self.metadata.get('N_segments', 'N/A')}")
        logger.info(f"  Spatial extent: {self.metadata.get('spatial_extent', 'N/A')} m")
        
        # Verifica primo frame
        first_frame = self.frames_group[self.frame_names[0]]
        required_datasets = ['positions', 'chi_values']
        missing = [ds for ds in required_datasets if ds not in first_frame]
        
        if missing:
            raise ValueError(f"Frame missing required datasets: {missing}")
        
        logger.info("✓ HDF5 state loaded successfully")
    
    def get_frame_count(self) -> int:
        """Ritorna numero frames disponibili."""
        return len(self.frame_names)
    
    def get_metadata(self) -> Dict:
        """Ritorna metadati simulazione."""
        return self.metadata.copy()
    
    def _classify_chirality(self, chi_values: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Classifica segmenti per chiralità.
        
        Parameters:
        -----------
        chi_values : np.ndarray (N,)
            Valori campo χ
        
        Returns:
        --------
        right_mask : np.ndarray (N,) bool
            Mask segmenti destrorsi (χ > threshold_pos)
        
        left_mask : np.ndarray (N,) bool
            Mask segmenti sinistrorsi (χ < threshold_neg)
        
        neutral_mask : np.ndarray (N,) bool
            Mask vuoto quantistico (|χ| ≤ threshold)
        """
        right_mask = chi_values > self.config.chi_threshold_positive
        left_mask = chi_values < self.config.chi_threshold_negative
        neutral_mask = ~(right_mask | left_mask)
        
        return right_mask, left_mask, neutral_mask
    
    def _compute_torsion_network(
        self,
        positions: np.ndarray,
        K_values: np.ndarray
    ) -> List[Tuple[int, int, float]]:
        """
        [GEOMETRIA DELLE FORZE: Network di Connessioni per Torsione]
        
        Calcola le connessioni tra segmenti che presentano torsione K > threshold.
        Questo renderizza la "trama" del manifold come network di forze.
        
        Algoritmo:
        ----------
        1. Costruisce KDTree per ricerca veloce dei vicini
        2. Per ogni segmento con K > threshold:
           - Trova i K nearest neighbors
           - Crea edge se entrambi superano la soglia
        3. Ritorna lista di edges con intensità K media
        
        Parameters:
        -----------
        positions : np.ndarray (N, 3)
            Posizioni segmenti
        
        K_values : np.ndarray (N,)
            Valori torsione locale
        
        Returns:
        --------
        edges : List[Tuple[int, int, float]]
            Lista di (index_i, index_j, K_avg) per edges significative
        """
        # Identifica segmenti con torsione significativa
        active_mask = np.abs(K_values) > self.config.torsion_threshold
        active_indices = np.where(active_mask)[0]
        
        if len(active_indices) == 0:
            logger.warning("No segments above torsion threshold. Network empty.")
            return []
        
        # Costruisci KDTree per ricerca efficiente
        tree = KDTree(positions)
        
        edges = []
        processed_pairs = set()
        
        for idx in active_indices:
            # Query k+1 neighbors (include il punto stesso)
            distances, neighbors = tree.query(
                positions[idx],
                k=self.config.max_neighbors + 1
            )
            
            # Salta il primo (se stesso) e filtra per distanza/attività
            for neighbor_idx, dist in zip(neighbors[1:], distances[1:]):
                if neighbor_idx not in active_indices:
                    continue
                
                # Evita duplicati (edge già processato nella direzione opposta)
                pair = tuple(sorted([idx, neighbor_idx]))
                if pair in processed_pairs:
                    continue
                
                processed_pairs.add(pair)
                
                # Intensità edge = media torsioni
                K_avg = (np.abs(K_values[idx]) + np.abs(K_values[neighbor_idx])) / 2.0
                edges.append((idx, neighbor_idx, K_avg))
        
        logger.info(f"Torsion network: {len(edges)} edges from {len(active_indices)} active segments")
        
        return edges
    
    def _compute_torsion_quivers(
        self,
        positions: np.ndarray,
        K_values: np.ndarray,
        drift_values: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        [GEOMETRIA DELLE FORZE: Vettori Direzionali di Torsione]
        
        Calcola vettori che indicano la direzione e l'intensità della forza
        di torsione nei punti hotspot (drift > threshold).
        
        La direzione del vettore è stimata dal gradiente locale di K.
        La lunghezza è proporzionale a K.
        
        Parameters:
        -----------
        positions : np.ndarray (N, 3)
            Posizioni segmenti
        
        K_values : np.ndarray (N,)
            Valori torsione
        
        drift_values : np.ndarray (N,), optional
            Valori drift (se None, usa K stesso per selezionare hotspots)
        
        Returns:
        --------
        quiver_origins : np.ndarray (M, 3)
            Posizioni di partenza vettori (hotspots)
        
        quiver_vectors : np.ndarray (M, 3)
            Vettori direzione*intensità
        """
        # Identifica hotspots
        if drift_values is not None:
            hotspot_mask = np.abs(drift_values) > self.config.drift_threshold
        else:
            # Fallback: usa top 10% dei valori K
            threshold = np.percentile(np.abs(K_values), 90)
            hotspot_mask = np.abs(K_values) > threshold
        
        hotspot_indices = np.where(hotspot_mask)[0]
        
        if len(hotspot_indices) == 0:
            logger.warning("No hotspots detected. Quivers empty.")
            return np.empty((0, 3)), np.empty((0, 3))
        
        # KDTree per calcolo gradiente
        tree = KDTree(positions)
        
        quiver_origins = []
        quiver_vectors = []
        
        for idx in hotspot_indices:
            # Query vicini per stima gradiente
            distances, neighbors = tree.query(positions[idx], k=7)  # 6 neighbors + self
            
            if len(neighbors) < 4:
                continue  # Troppo pochi vicini per gradiente affidabile
            
            # Calcola gradiente K come differenza pesata
            neighbor_positions = positions[neighbors[1:]]  # Salta se stesso
            neighbor_K = K_values[neighbors[1:]]
            current_K = K_values[idx]
            
            # Vettore gradiente (direzione forza)
            dK = neighbor_K - current_K
            dp = neighbor_positions - positions[idx]
            
            # Gradiente medio pesato per distanza inversa
            weights = 1.0 / (distances[1:] + 1e-10)
            weights /= weights.sum()
            
            grad_K = np.sum(dK[:, None] * dp * weights[:, None], axis=0)
            
            # Normalizza e scala per intensità K
            grad_norm = np.linalg.norm(grad_K)
            if grad_norm > 1e-12:
                direction = grad_K / grad_norm
                magnitude = np.abs(current_K) * self.config.quiver_scale
                
                quiver_origins.append(positions[idx])
                quiver_vectors.append(direction * magnitude)
        
        if len(quiver_origins) == 0:
            logger.warning("No valid quivers computed.")
            return np.empty((0, 3)), np.empty((0, 3))
        
        logger.info(f"Torsion quivers: {len(quiver_origins)} vectors at hotspots")
        
        return np.array(quiver_origins), np.array(quiver_vectors)
    
    def _compute_isosurface(
        self,
        positions: np.ndarray,
        K_values: np.ndarray,
        level: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        [GEOMETRIA DELLE FORZE: Superficie di Campo via Marching Cubes]
        
        Genera superficie 3D isosurface del campo di torsione K usando
        l'algoritmo Marching Cubes. Questo trasforma la nuvola di punti
        in una struttura solida deformata.
        
        Algoritmo:
        ----------
        1. Interpola K_values su griglia 3D regolare
        2. Applica smoothing Gaussiano per continuità
        3. Estrae isosurface a level specificato
        4. Ritorna vertici e facce della mesh
        
        Parameters:
        -----------
        positions : np.ndarray (N, 3)
            Posizioni segmenti
        
        K_values : np.ndarray (N,)
            Valori torsione
        
        level : float, optional
            Livello isosurface assoluto (se None, usa config.isosurface_level * max(K))
        
        Returns:
        --------
        vertices : np.ndarray (M, 3)
            Vertici della mesh isosurface
        
        faces : np.ndarray (F, 3)
            Triangoli della mesh (indici vertici)
        
        Raises:
        -------
        ImportError
            Se scikit-image non disponibile
        """
        if not HAS_SKIMAGE:
            raise ImportError(
                "scikit-image required for isosurface rendering. "
                "Install with: pip install scikit-image"
            )
        
        # Determina bounds spaziali
        mins = positions.min(axis=0)
        maxs = positions.max(axis=0)
        
        # Crea griglia 3D
        res = self.config.grid_resolution
        x = np.linspace(mins[0], maxs[0], res)
        y = np.linspace(mins[1], maxs[1], res)
        z = np.linspace(mins[2], maxs[2], res)
        
        grid_x, grid_y, grid_z = np.meshgrid(x, y, z, indexing='ij')
        grid_points = np.c_[grid_x.ravel(), grid_y.ravel(), grid_z.ravel()]
        
        # Interpola K su griglia (nearest neighbor per robustezza)
        tree = KDTree(positions)
        distances, indices = tree.query(grid_points, k=1)
        grid_K = K_values[indices].reshape((res, res, res))
        
        # Smoothing per continuità superficie
        grid_K_smooth = gaussian_filter(grid_K, sigma=1.0)
        
        # Determina livello isosurface
        if level is None:
            level = self.config.isosurface_level * np.abs(grid_K_smooth).max()
        
        logger.info(f"Computing isosurface at level={level:.3e}")
        logger.info(f"  Grid resolution: {res}x{res}x{res}")
        logger.info(f"  K range on grid: [{grid_K_smooth.min():.3e}, {grid_K_smooth.max():.3e}]")
        
        # Marching Cubes
        try:
            vertices, faces, normals, values = marching_cubes(
                np.abs(grid_K_smooth),
                level=level,
                spacing=((maxs[0]-mins[0])/res, (maxs[1]-mins[1])/res, (maxs[2]-mins[2])/res)
            )
            
            # Trasla vertici in coordinate fisiche
            vertices += mins
            
            logger.info(f"  Isosurface: {len(vertices)} vertices, {len(faces)} faces")
            
            return vertices, faces
        
        except Exception as e:
            logger.error(f"Marching cubes failed: {e}")
            return np.empty((0, 3)), np.empty((0, 3))
    
    def _compute_chiral_isosurface(
        self,
        positions: np.ndarray,
        chi_values: np.ndarray,
        apply_smoothing: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        [GEOMETRIA VOLUMETRICA: Isosuperficie Chirale con Smoothing Topologico]
        
        Genera isosuperficie del campo χ con smoothing Gaussiano 3D per eliminare
        rumore stocastico L0 e rivelare la curvatura macroscopica.
        
        Algoritmo:
        ----------
        1. Interpola χ su griglia 3D regolare
        2. Applica Gaussian filter 3D con sigma configurabile
        3. Estrae isosuperficie a livello = config.chi_isosurface_level
        4. Ritorna vertici, facce, e valori χ sui vertici (per texture mapping)
        
        Parameters:
        -----------
        positions : np.ndarray (N, 3)
            Posizioni segmenti
        
        chi_values : np.ndarray (N,)
            Valori campo chirale
        
        apply_smoothing : bool
            Se True, applica Gaussian smoothing (elimina rumore L0)
        
        Returns:
        --------
        vertices : np.ndarray (M, 3)
            Vertici mesh isosuperficie
        
        faces : np.ndarray (F, 3)
            Triangoli mesh (indici vertici)
        
        chi_on_vertices : np.ndarray (M,)
            Valori χ interpolati sui vertici (per texture chirale)
        
        Raises:
        -------
        ImportError
            Se scikit-image non disponibile
        """
        if not HAS_SKIMAGE:
            raise ImportError(
                "scikit-image required for volumetric rendering. "
                "Install with: pip install scikit-image"
            )
        
        # Determina bounds spaziali
        mins = positions.min(axis=0)
        maxs = positions.max(axis=0)
        
        # Crea griglia 3D ad alta risoluzione
        res = self.config.volumetric_resolution
        x = np.linspace(mins[0], maxs[0], res)
        y = np.linspace(mins[1], maxs[1], res)
        z = np.linspace(mins[2], maxs[2], res)
        
        grid_x, grid_y, grid_z = np.meshgrid(x, y, z, indexing='ij')
        grid_points = np.c_[grid_x.ravel(), grid_y.ravel(), grid_z.ravel()]
        
        # Interpola χ su griglia (nearest neighbor per robustezza)
        tree = KDTree(positions)
        distances, indices = tree.query(grid_points, k=1)
        grid_chi = chi_values[indices].reshape((res, res, res))
        
        # SMOOTHING TOPOLOGICO: Elimina rumore stocastico L0
        if apply_smoothing:
            sigma = self.config.smoothing_sigma
            grid_chi_smooth = gaussian_filter(grid_chi, sigma=sigma)
            logger.info(f"Applied Gaussian smoothing (sigma={sigma:.1f}) to eliminate L0 noise")
        else:
            grid_chi_smooth = grid_chi
        
        # Determina livello isosuperficie (adatta al range dei dati)
        chi_min = np.abs(grid_chi_smooth).min()
        chi_max = np.abs(grid_chi_smooth).max()
        level = chi_min + (chi_max - chi_min) * self.config.chi_isosurface_level
        
        logger.info(f"Computing chiral isosurface at level={level:.3f}")
        logger.info(f"  Grid resolution: {res}x{res}x{res}")
        logger.info(f"  Chi range (smoothed): [{grid_chi_smooth.min():.3f}, {grid_chi_smooth.max():.3f}]")
        
        # Marching Cubes su campo χ (non su |χ|, per preservare segno)
        try:
            # Usa valore assoluto per isosuperficie, ma mantieni segno per texture
            vertices, faces, normals, values = marching_cubes(
                np.abs(grid_chi_smooth),
                level=level,
                spacing=((maxs[0]-mins[0])/res, (maxs[1]-mins[1])/res, (maxs[2]-mins[2])/res)
            )
            
            # Trasla vertici in coordinate fisiche
            vertices += mins
            
            # Interpola χ originale (con segno) sui vertici per texture mapping
            tree_grid = KDTree(grid_points.reshape(res, res, res, 3).reshape(-1, 3))
            _, vert_indices = tree_grid.query(vertices, k=1)
            chi_on_vertices = grid_chi_smooth.ravel()[vert_indices]
            
            logger.info(f"  Isosurface: {len(vertices)} vertices, {len(faces)} faces")
            logger.info(f"  Chi on vertices: [{chi_on_vertices.min():.3f}, {chi_on_vertices.max():.3f}]")
            
            return vertices, faces, chi_on_vertices
        
        except Exception as e:
            logger.error(f"Chiral isosurface marching cubes failed: {e}")
            return np.empty((0, 3)), np.empty((0, 3)), np.empty(0)
    
    def _compute_K_field_lines(
        self,
        positions: np.ndarray,
        K_values: np.ndarray,
        num_lines: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        [GEOMETRIA DEL CAMPO: Linee di Campo della Torsione K]
        
        Calcola linee di campo (streamlines) del campo di torsione K per visualizzare
        il "telaio" geometrico sottostante. Le linee seguono il gradiente di K.
        
        Algoritmo:
        ----------
        1. Seleziona N seed points (punti ad alto K)
        2. Per ogni seed, integra gradiente di K in entrambe le direzioni
        3. Usa Euler integrator con step adattivo
        4. Ferma quando K < threshold o esce dal dominio
        
        Parameters:
        -----------
        positions : np.ndarray (N, 3)
            Posizioni segmenti
        
        K_values : np.ndarray (N,)
            Valori torsione
        
        num_lines : int, optional
            Numero linee di campo (default: config.K_streamline_density)
        
        Returns:
        --------
        streamlines : List[np.ndarray]
            Lista di array (M_i, 3) rappresentanti le linee di campo
        """
        if num_lines is None:
            num_lines = self.config.K_streamline_density
        
        # Seleziona seed points: top N segmenti per |K|
        K_abs = np.abs(K_values)
        seed_indices = np.argsort(K_abs)[-num_lines:]
        seed_points = positions[seed_indices]
        
        logger.info(f"Computing K field lines from {num_lines} seed points")
        
        # Costruisci KDTree per interpolazione rapida
        tree = KDTree(positions)
        
        # Determina bounds spaziali
        mins = positions.min(axis=0)
        maxs = positions.max(axis=0)
        domain_size = maxs - mins
        
        # Parametri integrazione
        max_length = self.config.K_streamline_length * domain_size.max()
        step_size = domain_size.max() / 100.0  # Step adattivo
        max_steps = int(max_length / step_size)
        
        streamlines = []
        
        for seed_point in seed_points:
            # Integra in entrambe le direzioni
            for direction in [1, -1]:
                line_points = [seed_point.copy()]
                current_point = seed_point.copy()
                
                for _ in range(max_steps // 2):
                    # Query K e gradiente al punto corrente
                    distances, indices = tree.query(current_point, k=6)
                    
                    if distances[0] > step_size * 2:
                        break  # Troppo lontano dai dati
                    
                    # Stima gradiente con finite differences sui vicini
                    neighbor_pos = positions[indices]
                    neighbor_K = K_values[indices]
                    
                    # Gradiente pesato per distanza inversa
                    weights = 1.0 / (distances + 1e-10)
                    weights /= weights.sum()
                    
                    dp = neighbor_pos - current_point
                    dK = neighbor_K - K_values[indices[0]]
                    
                    grad_K = np.sum(dK[:, None] * dp * weights[:, None], axis=0)
                    grad_norm = np.linalg.norm(grad_K)
                    
                    if grad_norm < 1e-12:
                        break  # Gradiente nullo
                    
                    # Step lungo gradiente
                    step_direction = grad_K / grad_norm * direction
                    next_point = current_point + step_direction * step_size
                    
                    # Verifica bounds
                    if np.any(next_point < mins) or np.any(next_point > maxs):
                        break
                    
                    # Verifica K threshold
                    _, next_idx = tree.query(next_point, k=1)
                    if np.abs(K_values[next_idx]) < K_abs.mean() * 0.1:
                        break  # K troppo basso
                    
                    line_points.append(next_point)
                    current_point = next_point
                
                if len(line_points) > 2:
                    streamlines.append(np.array(line_points))
        
        logger.info(f"  Generated {len(streamlines)} streamlines")
        logger.info(f"  Average points per line: {np.mean([len(s) for s in streamlines]):.1f}")
        
        return streamlines
    
    def render_volumetric_manifold(
        self,
        frame_index: int = -1,
        show_isosurface: bool = True,
        show_field_lines: bool = True,
        apply_smoothing: bool = True,
        save_path: Optional[Union[str, Path]] = None,
        show: bool = True
    ) -> None:
        """
        [RENDERING VOLUMETRICO: Geometria Manifold con Isosuperficie e Campo K]
        
        Rendering avanzato che visualizza il manifold come:
        1. **Isosuperficie del campo χ** con texture chirale (no scatter points)
        2. **Smoothing topologico Gaussiano 3D** per eliminare rumore L0
        3. **Linee di campo K** come "telaio" geometrico sottostante
        
        Questo rendering rivela la vera natura geometrica del manifold eliminando
        il rumore stocastico delle particelle individuali.
        
        Physics Rendered:
        -----------------
        - **Isosurface χ**: Superficie equipotenziale del campo chirale
        - **Texture chirale**: Mappa Blu/Rosso/Bianco che segue le undulazioni
        - **K field lines**: Telaio geometrico della torsione (gradiente K)
        
        Parameters:
        -----------
        frame_index : int
            Indice frame da visualizzare (default: -1 = ultimo)
        
        show_isosurface : bool
            Mostra isosuperficie χ con texture chirale
        
        show_field_lines : bool
            Mostra linee di campo K
        
        apply_smoothing : bool
            Applica Gaussian smoothing 3D (elimina rumore L0)
        
        save_path : str or Path, optional
            Path file PNG output
        
        show : bool
            Mostra plot interattivo
        
        Raises:
        -------
        ValueError
            Se HDF5 non caricato
        
        ImportError
            Se scikit-image non disponibile
        
        Examples:
        ---------
        >>> viz = ManifoldVisualizer()
        >>> viz.load_state('cosmology_L3.h5')
        >>> viz.render_volumetric_manifold(
        ...     show_isosurface=True,
        ...     show_field_lines=True,
        ...     apply_smoothing=True
        ... )
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        # Carica frame
        frame_name = self.frame_names[frame_index]
        frame = self.frames_group[frame_name]
        
        positions = frame['positions'][:]
        chi_values = frame['chi_values'][:]
        K_values = frame['contorsione_locale'][:]
        
        time = frame.attrs.get('time', 0.0)
        H_total = frame.attrs.get('H_total', 0.0)
        
        logger.info("="*80)
        logger.info(f"VOLUMETRIC RENDERING: {frame_name}")
        logger.info(f"  Time: {time:.3f} s")
        logger.info(f"  Chi range: [{chi_values.min():.3f}, {chi_values.max():.3f}]")
        logger.info(f"  K range: [{K_values.min():.3e}, {K_values.max():.3e}]")
        logger.info(f"  Smoothing: {'ON' if apply_smoothing else 'OFF'}")
        logger.info("="*80)
        
        # Compute geometria
        iso_vertices = np.empty((0, 3))
        iso_faces = np.empty((0, 3))
        chi_on_vertices = np.empty(0)
        k_streamlines = []
        
        if show_isosurface:
            logger.info("Computing chiral isosurface...")
            iso_vertices, iso_faces, chi_on_vertices = self._compute_chiral_isosurface(
                positions, chi_values, apply_smoothing=apply_smoothing
            )
        
        if show_field_lines:
            logger.info("Computing K field lines...")
            k_streamlines = self._compute_K_field_lines(positions, K_values)
        
        # Setup plot
        fig = plt.figure(figsize=(14, 12))
        ax = fig.add_subplot(111, projection='3d')
        
        # 1. RENDER K FIELD LINES (sotto l'isosuperficie per z-ordering)
        if len(k_streamlines) > 0:
            from mpl_toolkits.mplot3d.art3d import Line3DCollection
            
            # Converti streamlines in formato Line3DCollection (lista di segmenti)
            segments = []
            for line in k_streamlines:
                for i in range(len(line) - 1):
                    segments.append([line[i], line[i+1]])
            
            lc = Line3DCollection(
                segments,
                colors='gray',
                linewidths=0.3,
                alpha=0.4,
                label=f'K field lines ({len(k_streamlines)})'
            )
            ax.add_collection3d(lc)
            logger.info(f"  ✓ K field lines rendered: {len(k_streamlines)} streamlines, {len(segments)} segments")
        
        # 2. RENDER ISOSURFACE CON TEXTURE CHIRALE
        if len(iso_vertices) > 0:
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            
            # Crea triangoli dalla mesh
            triangles = iso_vertices[iso_faces]
            
            # TEXTURE CHIRALE: Mappa colori sui vertici
            # Calcola colore medio per ogni triangolo basato su χ sui vertici
            chi_per_face = chi_on_vertices[iso_faces].mean(axis=1)
            
            # Classifica chiralità per faccia
            right_mask = chi_per_face > self.config.chi_threshold_positive
            left_mask = chi_per_face < self.config.chi_threshold_negative
            neutral_mask = ~(right_mask | left_mask)
            
            # Crea array colori
            face_colors = np.ones((len(iso_faces), 4))  # RGBA
            
            # Applica colorazione chirale
            face_colors[right_mask] = [0.2, 0.4, 0.9, 0.7]   # Blu destrorsa
            face_colors[left_mask] = [0.9, 0.2, 0.2, 0.7]    # Rosso sinistrorsa
            face_colors[neutral_mask] = [0.95, 0.95, 0.95, 0.5]  # Bianco neutro
            
            poly = Poly3DCollection(
                triangles,
                facecolors=face_colors,
                linewidths=0,
                shade=True
            )
            ax.add_collection3d(poly)
            
            N_right = np.sum(right_mask)
            N_left = np.sum(left_mask)
            N_neutral = np.sum(neutral_mask)
            
            logger.info(f"  ✓ Isosurface rendered: {len(iso_vertices)} vertices, {len(iso_faces)} faces")
            logger.info(f"    Chiral distribution (faces):")
            logger.info(f"      Right (Blue):   {N_right} ({100*N_right/len(iso_faces):.1f}%)")
            logger.info(f"      Left (Red):     {N_left} ({100*N_left/len(iso_faces):.1f}%)")
            logger.info(f"      Neutral (White): {N_neutral} ({100*N_neutral/len(iso_faces):.1f}%)")
        
        # Styling
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        
        title = f"Volumetric Manifold - Level {self.metadata.get('target_level', '?')} | t={time:.3f}s\n"
        if apply_smoothing:
            title += f"Gaussian Smoothing (σ={self.config.smoothing_sigma:.1f}) | "
        title += f"Isosurface χ={self.config.chi_isosurface_level:.2f}"
        
        ax.set_title(title, fontsize=13, fontweight='bold')
        
        if len(k_streamlines) > 0:
            ax.legend(loc='upper right', fontsize=9)
        
        # Equal aspect ratio
        if len(iso_vertices) > 0:
            # Usa bounds isosurface
            ref_positions = iso_vertices
        else:
            ref_positions = positions
        
        max_range = np.array([
            ref_positions[:, 0].max() - ref_positions[:, 0].min(),
            ref_positions[:, 1].max() - ref_positions[:, 1].min(),
            ref_positions[:, 2].max() - ref_positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (ref_positions[:, 0].max() + ref_positions[:, 0].min()) * 0.5
        mid_y = (ref_positions[:, 1].max() + ref_positions[:, 1].min()) * 0.5
        mid_z = (ref_positions[:, 2].max() + ref_positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Viewpoint ottimale per vedere geometria
        ax.view_init(elev=20, azim=45)
        
        plt.tight_layout()
        
        # Salva
        if save_path is not None:
            save_path = Path(save_path)
            plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight')
            logger.info(f"✓ Volumetric rendering saved to {save_path}")
        
        # Mostra
        if show:
            plt.show()
        else:
            plt.close()
        
        logger.info("="*80)
    
    def render_field_geometry(
        self,
        frame_index: int = -1,
        render_mode: str = 'full',
        save_path: Optional[Union[str, Path]] = None,
        show: bool = True
    ) -> None:
        """
        [LEGGE FISICA: Rendering Geometria del Campo di Forze]
        
        Visualizza il manifold come geometria delle forze invece che nuvola di punti.
        
        Rendering Elements:
        -------------------
        1. NETWORK EDGES: Connessioni tra segmenti con K > threshold
           → Visualizza la "trama" del manifold come grafo di forze
        
        2. TORSION QUIVERS: Vettori direzionali nei hotspots
           → Direzione e intensità delle forze di torsione
        
        3. ISOSURFACE: Superficie 3D del campo K (Marching Cubes)
           → Manifold come struttura solida deformata
        
        4. FIELD POINTS: Punti colorati per intensità K (opzionale)
           → Mappa spaziale della densità di informazione
        
        Parameters:
        -----------
        frame_index : int
            Indice frame da visualizzare (default: -1 = ultimo)
        
        render_mode : str
            Elementi da visualizzare:
            - 'full': Network + Quivers + Isosurface + Points
            - 'network': Solo network edges
            - 'quivers': Solo vettori di forza
            - 'isosurface': Solo superficie campo
            - 'network+quivers': Network + vettori (recommended)
            - 'isosurface+quivers': Superficie + vettori
        
        save_path : str or Path, optional
            Path file PNG output
        
        show : bool
            Mostra plot interattivo
        
        Raises:
        -------
        ValueError
            Se HDF5 non caricato o mode non valido
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        valid_modes = ['full', 'network', 'quivers', 'isosurface', 
                       'network+quivers', 'isosurface+quivers']
        if render_mode not in valid_modes:
            raise ValueError(f"Invalid render_mode '{render_mode}'. Choose from: {valid_modes}")
        
        # Carica frame
        frame_name = self.frame_names[frame_index]
        frame = self.frames_group[frame_name]
        
        positions = frame['positions'][:]
        K_values = frame['contorsione_locale'][:]
        
        # Metadata opzionali
        time = frame.attrs.get('time', 0.0)
        H_total = frame.attrs.get('H_total', 0.0)
        drift_values = frame['drift_matrix'][:] if 'drift_matrix' in frame else None
        
        logger.info("="*80)
        logger.info(f"FIELD GEOMETRY RENDERING: {frame_name}")
        logger.info(f"  Mode: {render_mode}")
        logger.info(f"  Time: {time:.3f} s")
        logger.info(f"  K range: [{K_values.min():.3e}, {K_values.max():.3e}]")
        logger.info(f"  K mean: {K_values.mean():.3e}")
        logger.info("="*80)
        
        # Compute geometry elements
        edges = []
        quiver_origins = np.empty((0, 3))
        quiver_vectors = np.empty((0, 3))
        iso_vertices = np.empty((0, 3))
        iso_faces = np.empty((0, 3))
        
        if render_mode in ['full', 'network', 'network+quivers']:
            logger.info("Computing torsion network...")
            edges = self._compute_torsion_network(positions, K_values)
        
        if render_mode in ['full', 'quivers', 'network+quivers', 'isosurface+quivers']:
            logger.info("Computing torsion quivers...")
            quiver_origins, quiver_vectors = self._compute_torsion_quivers(
                positions, K_values, drift_values
            )
        
        if render_mode in ['full', 'isosurface', 'isosurface+quivers']:
            logger.info("Computing isosurface (Marching Cubes)...")
            iso_vertices, iso_faces = self._compute_isosurface(positions, K_values)
        
        # Setup plot
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Render elements
        rendered_elements = []
        
        # 1. ISOSURFACE (render per primo per z-ordering)
        if len(iso_vertices) > 0:
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            
            # Crea triangoli dalla mesh
            triangles = iso_vertices[iso_faces]
            
            poly = Poly3DCollection(
                triangles,
                alpha=self.config.mesh_alpha,
                facecolors='cyan',
                edgecolors='none',
                shade=True
            )
            ax.add_collection3d(poly)
            rendered_elements.append(f"Isosurface ({len(iso_faces)} faces)")
            logger.info(f"  ✓ Isosurface rendered: {len(iso_vertices)} vertices")
        
        # 2. NETWORK EDGES
        if len(edges) > 0:
            # Prepara segmenti per Line3DCollection
            segments = []
            colors = []
            
            # Normalizza intensità per colormap
            K_intensities = np.array([edge[2] for edge in edges])
            K_norm = (K_intensities - K_intensities.min()) / (K_intensities.max() - K_intensities.min() + 1e-12)
            
            for (i, j, K_avg), k_n in zip(edges, K_norm):
                segments.append([positions[i], positions[j]])
                # Colormap: verde (basso K) → rosso (alto K)
                color = plt.cm.plasma(k_n)
                colors.append(color)
            
            lc = Line3DCollection(
                segments,
                colors=colors,
                linewidths=self.config.edge_linewidth,
                alpha=self.config.edge_alpha
            )
            ax.add_collection3d(lc)
            rendered_elements.append(f"Network ({len(edges)} edges)")
            logger.info(f"  ✓ Network rendered: {len(edges)} edges")
        
        # 3. TORSION QUIVERS
        if len(quiver_origins) > 0:
            # Quiver3D (arrows)
            ax.quiver(
                quiver_origins[:, 0],
                quiver_origins[:, 1],
                quiver_origins[:, 2],
                quiver_vectors[:, 0],
                quiver_vectors[:, 1],
                quiver_vectors[:, 2],
                color='red',
                alpha=self.config.quiver_alpha,
                arrow_length_ratio=0.3,
                linewidth=1.5,
                label=f'Torsion Vectors ({len(quiver_origins)})'
            )
            rendered_elements.append(f"Quivers ({len(quiver_origins)} vectors)")
            logger.info(f"  ✓ Quivers rendered: {len(quiver_origins)} vectors")
        
        # 4. FIELD POINTS (opzionale, solo mode='full')
        if render_mode == 'full':
            # Sub-sample punti per evitare affollamento
            subsample = max(1, len(positions) // 2000)
            pos_sub = positions[::subsample]
            K_sub = K_values[::subsample]
            
            scatter = ax.scatter(
                pos_sub[:, 0],
                pos_sub[:, 1],
                pos_sub[:, 2],
                c=np.abs(K_sub),
                s=5,
                alpha=0.3,
                cmap='viridis',
                label=f'Field ({len(pos_sub)} points)'
            )
            rendered_elements.append(f"Points ({len(pos_sub)})")
            logger.info(f"  ✓ Field points rendered: {len(pos_sub)} (subsampled)")
        
        # Styling
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        
        title = f"Field Geometry - Level {self.metadata.get('target_level', '?')} | t={time:.3f}s\n"
        title += f"Mode: {render_mode.upper()} | " + " + ".join(rendered_elements)
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        if len(quiver_origins) > 0:
            ax.legend(loc='upper right', fontsize=9)
        
        # Equal aspect ratio
        max_range = np.array([
            positions[:, 0].max() - positions[:, 0].min(),
            positions[:, 1].max() - positions[:, 1].min(),
            positions[:, 2].max() - positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (positions[:, 0].max() + positions[:, 0].min()) * 0.5
        mid_y = (positions[:, 1].max() + positions[:, 1].min()) * 0.5
        mid_z = (positions[:, 2].max() + positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        plt.tight_layout()
        
        # Salva
        if save_path is not None:
            save_path = Path(save_path)
            plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight')
            logger.info(f"✓ Field geometry plot saved to {save_path}")
        
        # Mostra
        if show:
            plt.show()
        else:
            plt.close()
        
        logger.info("="*80)
    
    def render_chiral_manifold(
        self,
        mode: str = 'full',
        frame_index: int = -1,
        save_path: Optional[Union[str, Path]] = None,
        show: bool = True
    ) -> None:
        """
        Rendering 3D del manifold con codifica chirale.
        
        [LEGGE FISICA: Distribuzione Spaziale di Materia/Antimateria]
        
        Visualizza la distribuzione tridimensionale del campo χ codificando
        la chiralità con colori:
        - BLU (destrorsa): Regioni di materia ordinaria
        - ROSSO (sinistrorsa): Regioni di antimateria
        - GRIGIO (neutro): Vuoto quantistico / foam structure
        
        Questo rendering permette di identificare:
        1. Clustering spaziale (soliton stars)
        2. Separazione di fase (domain walls)
        3. Simmetria/asimmetria CP globale
        
        Parameters:
        -----------
        mode : str
            Modalità rendering:
            - 'full': Tutti i segmenti con trasparenza differenziata
            - 'chiral_only': Solo segmenti chirali (no neutri)
            - 'matter': Solo destrorsa
            - 'antimatter': Solo sinistrorsa
        
        frame_index : int
            Indice frame da visualizzare (default: -1 = ultimo frame)
        
        save_path : str or Path, optional
            Path file PNG output (se None, non salva)
        
        show : bool
            Mostra plot interattivo (default: True)
        
        Raises:
        -------
        ValueError
            Se mode non valido o HDF5 non caricato
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        valid_modes = ['full', 'chiral_only', 'matter', 'antimatter']
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {valid_modes}")
        
        # Carica frame
        frame_name = self.frame_names[frame_index]
        frame = self.frames_group[frame_name]
        
        positions = frame['positions'][:]  # (N, 3)
        chi_values = frame['chi_values'][:]  # (N,)
        
        # Estrai metadata frame
        time = frame.attrs.get('time', 0.0)
        H_total = frame.attrs.get('H_total', 0.0)
        T_eff = frame.attrs.get('T_eff', 0.0)
        drift = frame.attrs.get('drift', 0.0)
        
        logger.info(f"Rendering frame {frame_index} ({frame_name})")
        logger.info(f"  Time:  {time:.3f} s")
        logger.info(f"  H:     {H_total:.3e} J")
        logger.info(f"  T_eff: {T_eff:.2f} K")
        logger.info(f"  Drift: {drift:.3e}")
        
        # Classifica chiralità
        right_mask, left_mask, neutral_mask = self._classify_chirality(chi_values)
        
        N_right = np.sum(right_mask)
        N_left = np.sum(left_mask)
        N_neutral = np.sum(neutral_mask)
        N_total = len(chi_values)
        
        logger.info(f"  Chirality distribution:")
        logger.info(f"    Right (DX):   {N_right:5d} ({100*N_right/N_total:.1f}%)")
        logger.info(f"    Left (SX):    {N_left:5d} ({100*N_left/N_total:.1f}%)")
        logger.info(f"    Neutral:      {N_neutral:5d} ({100*N_neutral/N_total:.1f}%)")
        
        # Setup plot
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Rendering mode-dependent
        if mode == 'full' or mode == 'chiral_only':
            # Neutri (solo se mode='full')
            if mode == 'full' and N_neutral > 0:
                ax.scatter(
                    positions[neutral_mask, 0],
                    positions[neutral_mask, 1],
                    positions[neutral_mask, 2],
                    c=self.config.color_neutral,
                    s=self.config.marker_size // 2,
                    alpha=self.config.alpha_neutral,
                    label=f'Vacuum ({N_neutral})',
                    depthshade=True
                )
            
            # Destrorsi
            if N_right > 0:
                ax.scatter(
                    positions[right_mask, 0],
                    positions[right_mask, 1],
                    positions[right_mask, 2],
                    c=self.config.color_right,
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    label=f'Right-handed ({N_right})',
                    depthshade=True
                )
            
            # Sinistrorsi
            if N_left > 0:
                ax.scatter(
                    positions[left_mask, 0],
                    positions[left_mask, 1],
                    positions[left_mask, 2],
                    c=self.config.color_left,
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    label=f'Left-handed ({N_left})',
                    depthshade=True
                )
        
        elif mode == 'matter':
            if N_right > 0:
                ax.scatter(
                    positions[right_mask, 0],
                    positions[right_mask, 1],
                    positions[right_mask, 2],
                    c=chi_values[right_mask],
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    cmap='Blues',
                    label=f'Matter ({N_right})',
                    depthshade=True
                )
        
        elif mode == 'antimatter':
            if N_left > 0:
                ax.scatter(
                    positions[left_mask, 0],
                    positions[left_mask, 1],
                    positions[left_mask, 2],
                    c=-chi_values[left_mask],  # Inverti per colormap
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    cmap='Reds',
                    label=f'Antimatter ({N_left})',
                    depthshade=True
                )
        
        # Styling
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        
        title = f"Chiral Manifold - Level {self.metadata.get('target_level', '?')} | t={time:.3f}s\n"
        title += f"Mode: {mode.upper()} | H={H_total:.2e} J | Drift={drift:.2e}"
        ax.set_title(title, fontsize=13, fontweight='bold')
        
        ax.legend(loc='upper right', fontsize=9)
        
        # Equal aspect ratio (importante per interpretazione fisica)
        max_range = np.array([
            positions[:, 0].max() - positions[:, 0].min(),
            positions[:, 1].max() - positions[:, 1].min(),
            positions[:, 2].max() - positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (positions[:, 0].max() + positions[:, 0].min()) * 0.5
        mid_y = (positions[:, 1].max() + positions[:, 1].min()) * 0.5
        mid_z = (positions[:, 2].max() + positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        plt.tight_layout()
        
        # Salva se richiesto
        if save_path is not None:
            save_path = Path(save_path)
            plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight')
            logger.info(f"✓ Plot saved to {save_path}")
        
        # Mostra
        if show:
            plt.show()
        else:
            plt.close()
    
    def render_frame(
        self,
        step_index: int,
        save_path: Optional[Union[str, Path]] = None,
        show: bool = True
    ) -> None:
        """
        Wrapper conveniente per render_chiral_manifold() con index esplicito.
        
        Parameters:
        -----------
        step_index : int
            Indice frame temporale (0 = primo frame)
        
        save_path : str or Path, optional
            Path output PNG
        
        show : bool
            Mostra plot interattivo
        """
        self.render_chiral_manifold(
            mode='full',
            frame_index=step_index,
            save_path=save_path,
            show=show
        )
    
    def render_torsion_field(
        self,
        frame_index: int = -1,
        save_path: Optional[Union[str, Path]] = None,
        show: bool = True
    ) -> None:
        """
        Rendering campo torsione K.
        
        Visualizza la distribuzione spaziale della contorsione locale K,
        proxy per densità di informazione geometrica.
        
        Parameters:
        -----------
        frame_index : int
            Indice frame (default: -1 = ultimo)
        
        save_path : str or Path, optional
            Path output PNG
        
        show : bool
            Mostra plot interattivo
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        # Carica frame
        frame_name = self.frame_names[frame_index]
        frame = self.frames_group[frame_name]
        
        positions = frame['positions'][:]
        K_values = frame['contorsione_locale'][:]
        
        time = frame.attrs.get('time', 0.0)
        
        logger.info(f"Rendering torsion field: {frame_name}")
        logger.info(f"  K range: [{K_values.min():.3e}, {K_values.max():.3e}]")
        logger.info(f"  K mean:  {K_values.mean():.3e}")
        
        # Plot
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        scatter = ax.scatter(
            positions[:, 0],
            positions[:, 1],
            positions[:, 2],
            c=K_values,
            s=self.config.marker_size,
            alpha=0.6,
            cmap='viridis',
            depthshade=True
        )
        
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        ax.set_title(
            f"Torsion Field K | t={time:.3f}s\n"
            f"Mean: {K_values.mean():.2e} | RMS: {np.sqrt(np.mean(K_values**2)):.2e}",
            fontsize=13,
            fontweight='bold'
        )
        
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, aspect=15)
        cbar.set_label('K (contorsione_locale)', rotation=270, labelpad=20, fontsize=10)
        
        plt.tight_layout()
        
        if save_path is not None:
            save_path = Path(save_path)
            plt.savefig(save_path, dpi=self.config.dpi, bbox_inches='tight')
            logger.info(f"✓ Torsion plot saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def animate_manifold(
        self,
        output_path: Union[str, Path] = 'evolution.mp4',
        mode: str = 'full',
        fps: int = 10,
        dpi: int = 100,
        bitrate: int = 1800,
        show_progress: bool = True
    ) -> None:
        """
        [LEGGE FISICA: Evoluzione Temporale del Manifold Chirale]
        
        Genera animazione MP4 della dinamica del manifold, visualizzando
        l'evoluzione temporale della distribuzione di materia/antimateria
        e le transizioni di fase topologiche.
        
        L'animazione usa update incrementale (NO ricreazione plot) per
        massimizzare performance su dataset L3 (13,824+ segmenti).
        
        Physics Observables Visualizzati:
        ----------------------------------
        1. Segregazione spaziale materia/antimateria
        2. Formazione/distruzione solitoni
        3. Propagazione onde di torsione
        4. Separazione di fase (domain walls)
        5. CP symmetry breaking temporale
        
        Parameters:
        -----------
        output_path : str or Path
            Path file MP4 output (default: 'evolution.mp4')
        
        mode : str
            Modalità rendering (come render_chiral_manifold):
            - 'full': Tutti i segmenti
            - 'chiral_only': Solo segmenti chirali
            - 'matter': Solo destrorsi
            - 'antimatter': Solo sinistrorsi
        
        fps : int
            Frame per second della animazione (default: 10)
            Nota: fps != simulation timestep. Controlla velocità playback.
        
        dpi : int
            Risoluzione video (default: 100, usa 150+ per pubblicazioni)
        
        bitrate : int
            Bitrate video in kbps (default: 1800, usa 3600+ per alta qualità)
        
        show_progress : bool
            Stampa progress bar durante rendering (default: True)
        
        Raises:
        -------
        ValueError
            Se HDF5 non caricato o mode non valido
        
        ImportError
            Se matplotlib.animation o ffmpeg non disponibili
        
        Examples:
        ---------
        >>> viz = ManifoldVisualizer()
        >>> viz.load_state('cosmology_L3_equilibrio.h5')
        >>> viz.animate_manifold('L3_evolution.mp4', fps=15, dpi=150)
        
        Notes:
        ------
        Richiede ffmpeg installato nel sistema per encoding MP4.
        Su Windows: scoop install ffmpeg
        Su Linux: apt install ffmpeg
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        valid_modes = ['full', 'chiral_only', 'matter', 'antimatter']
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {valid_modes}")
        
        try:
            from matplotlib.animation import FuncAnimation, FFMpegWriter
        except ImportError as e:
            raise ImportError(
                "matplotlib.animation required for video generation. "
                "Install with: pip install matplotlib[animation]"
            ) from e
        
        output_path = Path(output_path)
        N_frames = len(self.frame_names)
        
        logger.info("="*80)
        logger.info(" MANIFOLD ANIMATION RENDERER")
        logger.info("="*80)
        logger.info(f"  Output:       {output_path}")
        logger.info(f"  Mode:         {mode}")
        logger.info(f"  Frames:       {N_frames}")
        logger.info(f"  FPS:          {fps}")
        logger.info(f"  DPI:          {dpi}")
        logger.info(f"  Bitrate:      {bitrate} kbps")
        logger.info(f"  Duration:     {N_frames/fps:.1f} seconds")
        logger.info("="*80)
        
        # Carica primo frame per setup iniziale
        first_frame = self.frames_group[self.frame_names[0]]
        positions = first_frame['positions'][:]
        chi_values = first_frame['chi_values'][:]
        
        # Classifica chiralità primo frame
        right_mask, left_mask, neutral_mask = self._classify_chirality(chi_values)
        
        # Setup figura e asse
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Inizializza scatter plots (uno per tipo)
        scatter_objects = {}
        
        if mode == 'full':
            # Neutri
            if np.any(neutral_mask):
                scatter_objects['neutral'] = ax.scatter(
                    positions[neutral_mask, 0],
                    positions[neutral_mask, 1],
                    positions[neutral_mask, 2],
                    c=self.config.color_neutral,
                    s=self.config.marker_size // 2,
                    alpha=self.config.alpha_neutral,
                    label='Vacuum',
                    depthshade=True
                )
            
            # Destrorsi
            if np.any(right_mask):
                scatter_objects['right'] = ax.scatter(
                    positions[right_mask, 0],
                    positions[right_mask, 1],
                    positions[right_mask, 2],
                    c=self.config.color_right,
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    label='Right-handed',
                    depthshade=True
                )
            
            # Sinistrorsi
            if np.any(left_mask):
                scatter_objects['left'] = ax.scatter(
                    positions[left_mask, 0],
                    positions[left_mask, 1],
                    positions[left_mask, 2],
                    c=self.config.color_left,
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    label='Left-handed',
                    depthshade=True
                )
        
        elif mode == 'chiral_only':
            # Solo chirali (NO neutri)
            if np.any(right_mask):
                scatter_objects['right'] = ax.scatter(
                    positions[right_mask, 0],
                    positions[right_mask, 1],
                    positions[right_mask, 2],
                    c=self.config.color_right,
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    label='Right-handed',
                    depthshade=True
                )
            
            if np.any(left_mask):
                scatter_objects['left'] = ax.scatter(
                    positions[left_mask, 0],
                    positions[left_mask, 1],
                    positions[left_mask, 2],
                    c=self.config.color_left,
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    label='Left-handed',
                    depthshade=True
                )
        
        elif mode == 'matter':
            if np.any(right_mask):
                scatter_objects['matter'] = ax.scatter(
                    positions[right_mask, 0],
                    positions[right_mask, 1],
                    positions[right_mask, 2],
                    c=chi_values[right_mask],
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    cmap='Blues',
                    label='Matter',
                    depthshade=True
                )
        
        elif mode == 'antimatter':
            if np.any(left_mask):
                scatter_objects['antimatter'] = ax.scatter(
                    positions[left_mask, 0],
                    positions[left_mask, 1],
                    positions[left_mask, 2],
                    c=-chi_values[left_mask],
                    s=self.config.marker_size,
                    alpha=self.config.alpha_chiral,
                    cmap='Reds',
                    label='Antimatter',
                    depthshade=True
                )
        
        # Styling statico
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        ax.legend(loc='upper right', fontsize=9)
        
        # Equal aspect ratio (calcolato su tutti i frame per stabilità)
        all_positions = []
        for fname in self.frame_names[::max(1, N_frames//10)]:  # Sample 10 frames
            all_positions.append(self.frames_group[fname]['positions'][:])
        all_positions = np.vstack(all_positions)
        
        max_range = np.array([
            all_positions[:, 0].max() - all_positions[:, 0].min(),
            all_positions[:, 1].max() - all_positions[:, 1].min(),
            all_positions[:, 2].max() - all_positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (all_positions[:, 0].max() + all_positions[:, 0].min()) * 0.5
        mid_y = (all_positions[:, 1].max() + all_positions[:, 1].min()) * 0.5
        mid_z = (all_positions[:, 2].max() + all_positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Text handle per info temporali (aggiornato ad ogni frame)
        info_text = ax.text2D(0.02, 0.98, '', transform=ax.transAxes,
                              fontsize=10, verticalalignment='top',
                              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Update function (chiamata da FuncAnimation)
        def update(frame_idx: int):
            """
            Aggiorna plot per frame corrente.
            
            PERFORMANCE CRITICAL: Aggiorna solo dati, NON ricrea scatter objects.
            """
            frame_name = self.frame_names[frame_idx]
            frame = self.frames_group[frame_name]
            
            positions = frame['positions'][:]
            chi_values = frame['chi_values'][:]
            
            time = frame.attrs.get('time', 0.0)
            H_total = frame.attrs.get('H_total', 0.0)
            drift = frame.attrs.get('drift', 0.0)
            
            # Riclassifica chiralità
            right_mask, left_mask, neutral_mask = self._classify_chirality(chi_values)
            
            # Aggiorna scatter objects (solo dati, NO ricreazione)
            if mode == 'full':
                if 'neutral' in scatter_objects and np.any(neutral_mask):
                    scatter_objects['neutral']._offsets3d = (
                        positions[neutral_mask, 0],
                        positions[neutral_mask, 1],
                        positions[neutral_mask, 2]
                    )
                
                if 'right' in scatter_objects and np.any(right_mask):
                    scatter_objects['right']._offsets3d = (
                        positions[right_mask, 0],
                        positions[right_mask, 1],
                        positions[right_mask, 2]
                    )
                
                if 'left' in scatter_objects and np.any(left_mask):
                    scatter_objects['left']._offsets3d = (
                        positions[left_mask, 0],
                        positions[left_mask, 1],
                        positions[left_mask, 2]
                    )
            
            elif mode == 'chiral_only':
                if 'right' in scatter_objects and np.any(right_mask):
                    scatter_objects['right']._offsets3d = (
                        positions[right_mask, 0],
                        positions[right_mask, 1],
                        positions[right_mask, 2]
                    )
                
                if 'left' in scatter_objects and np.any(left_mask):
                    scatter_objects['left']._offsets3d = (
                        positions[left_mask, 0],
                        positions[left_mask, 1],
                        positions[left_mask, 2]
                    )
            
            elif mode == 'matter' and 'matter' in scatter_objects:
                if np.any(right_mask):
                    scatter_objects['matter']._offsets3d = (
                        positions[right_mask, 0],
                        positions[right_mask, 1],
                        positions[right_mask, 2]
                    )
                    scatter_objects['matter'].set_array(chi_values[right_mask])
            
            elif mode == 'antimatter' and 'antimatter' in scatter_objects:
                if np.any(left_mask):
                    scatter_objects['antimatter']._offsets3d = (
                        positions[left_mask, 0],
                        positions[left_mask, 1],
                        positions[left_mask, 2]
                    )
                    scatter_objects['antimatter'].set_array(-chi_values[left_mask])
            
            # Aggiorna titolo con info temporali
            title = f"Chiral Manifold Evolution - Level {self.metadata.get('target_level', '?')}\n"
            title += f"Frame {frame_idx+1}/{N_frames} | t={time:.3f}s | H={H_total:.2e} J | Drift={drift:.2e}"
            ax.set_title(title, fontsize=13, fontweight='bold')
            
            # Aggiorna info text
            N_right = np.sum(right_mask)
            N_left = np.sum(left_mask)
            N_neutral = np.sum(neutral_mask)
            N_total = len(chi_values)
            
            info_str = f"DX: {N_right:5d} ({100*N_right/N_total:4.1f}%)\n"
            info_str += f"SX: {N_left:5d} ({100*N_left/N_total:4.1f}%)\n"
            info_str += f"∅:  {N_neutral:5d} ({100*N_neutral/N_total:4.1f}%)"
            info_text.set_text(info_str)
            
            if show_progress and (frame_idx % max(1, N_frames // 20) == 0):
                logger.info(f"  Rendering frame {frame_idx+1}/{N_frames} ({100*(frame_idx+1)/N_frames:.1f}%)")
            
            return list(scatter_objects.values()) + [info_text]
        
        # Crea animazione
        logger.info("Creating animation...")
        anim = FuncAnimation(
            fig,
            update,
            frames=N_frames,
            interval=1000/fps,  # ms per frame
            blit=False,  # blit=True non funziona bene con 3D in matplotlib
            repeat=True
        )
        
        # Setup writer
        writer = FFMpegWriter(
            fps=fps,
            bitrate=bitrate,
            metadata={
                'title': f'WQT Manifold Evolution - Level {self.metadata.get("target_level", "?")}',
                'artist': 'WQT Physics Team',
                'comment': f'Mode: {mode} | Frames: {N_frames}'
            }
        )
        
        # Salva video
        logger.info(f"Encoding video to {output_path}...")
        logger.info("  (This may take several minutes for large datasets)")
        
        try:
            anim.save(output_path, writer=writer, dpi=dpi)
            logger.info("="*80)
            logger.info(f"✓ Animation saved successfully!")
            logger.info(f"  File: {output_path}")
            logger.info(f"  Size: {output_path.stat().st_size / 1024**2:.2f} MB")
            logger.info(f"  Duration: {N_frames/fps:.2f} seconds")
            logger.info("="*80)
        except Exception as e:
            logger.error(f"Failed to save animation: {e}")
            logger.error("Ensure ffmpeg is installed: scoop install ffmpeg (Windows) or apt install ffmpeg (Linux)")
            raise
        finally:
            plt.close(fig)
    
    def animate_field_dynamics(
        self,
        output_path: Union[str, Path] = 'field_evolution.mp4',
        render_mode: str = 'network+quivers',
        fps: int = 10,
        dpi: int = 100,
        bitrate: int = 1800,
        show_progress: bool = True
    ) -> None:
        """
        [LEGGE FISICA: Dinamica del Campo con Deformazione Mesh]
        
        Genera animazione della geometria delle forze, visualizzando la 
        deformazione della mesh del manifold invece dell'aggiornamento dei punti.
        
        Questo mostra l'evoluzione temporale della struttura di forze:
        - Network edges che si formano/distruggono
        - Vettori di torsione che cambiano direzione/intensità
        - Mesh che si deforma seguendo le forze
        
        Parameters:
        -----------
        output_path : str or Path
            Path file MP4 output (default: 'field_evolution.mp4')
        
        render_mode : str
            Modalità rendering (come render_field_geometry):
            - 'network+quivers': Network + vettori (recommended)
            - 'isosurface+quivers': Superficie + vettori
            - 'full': Tutti gli elementi
            - 'network', 'quivers', 'isosurface': Singoli elementi
        
        fps : int
            Frame per second (default: 10)
        
        dpi : int
            Risoluzione video (default: 100)
        
        bitrate : int
            Bitrate video in kbps (default: 1800)
        
        show_progress : bool
            Stampa progress bar durante rendering
        
        Raises:
        -------
        ValueError
            Se HDF5 non caricato
        
        ImportError
            Se matplotlib.animation o ffmpeg non disponibili
        
        Examples:
        ---------
        >>> viz = ManifoldVisualizer()
        >>> viz.load_state('cosmology_L3.h5')
        >>> viz.animate_field_dynamics('field_dynamics.mp4', mode='network+quivers')
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        valid_modes = ['full', 'network', 'quivers', 'isosurface', 
                       'network+quivers', 'isosurface+quivers']
        if render_mode not in valid_modes:
            raise ValueError(f"Invalid render_mode '{render_mode}'. Choose from: {valid_modes}")
        
        try:
            from matplotlib.animation import FuncAnimation, FFMpegWriter
        except ImportError as e:
            raise ImportError(
                "matplotlib.animation required for video generation. "
                "Install with: pip install matplotlib[animation]"
            ) from e
        
        output_path = Path(output_path)
        N_frames = len(self.frame_names)
        
        logger.info("="*80)
        logger.info(" FIELD DYNAMICS ANIMATION RENDERER")
        logger.info("="*80)
        logger.info(f"  Output:       {output_path}")
        logger.info(f"  Mode:         {render_mode}")
        logger.info(f"  Frames:       {N_frames}")
        logger.info(f"  FPS:          {fps}")
        logger.info(f"  DPI:          {dpi}")
        logger.info(f"  Duration:     {N_frames/fps:.1f} seconds")
        logger.info("="*80)
        
        # Setup figura
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Containers per oggetti grafici aggiornabili
        network_collection = None
        quiver_object = None
        mesh_collection = None
        scatter_object = None
        
        # Carica primo frame per bounds
        first_frame = self.frames_group[self.frame_names[0]]
        positions_init = first_frame['positions'][:]
        
        # Calcola bounds globali (su tutti i frame per stabilità)
        all_positions = []
        for fname in self.frame_names[::max(1, N_frames//10)]:
            all_positions.append(self.frames_group[fname]['positions'][:])
        all_positions = np.vstack(all_positions)
        
        max_range = np.array([
            all_positions[:, 0].max() - all_positions[:, 0].min(),
            all_positions[:, 1].max() - all_positions[:, 1].min(),
            all_positions[:, 2].max() - all_positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (all_positions[:, 0].max() + all_positions[:, 0].min()) * 0.5
        mid_y = (all_positions[:, 1].max() + all_positions[:, 1].min()) * 0.5
        mid_z = (all_positions[:, 2].max() + all_positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Styling statico
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        
        # Text handle per info temporali
        info_text = ax.text2D(0.02, 0.98, '', transform=ax.transAxes,
                              fontsize=10, verticalalignment='top',
                              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Update function
        def update(frame_idx: int):
            """
            Aggiorna geometria per frame corrente.
            
            PERFORMANCE CRITICAL: Aggiorna solo geometria, NON ricrea oggetti grafici.
            """
            nonlocal network_collection, quiver_object, mesh_collection, scatter_object
            
            frame_name = self.frame_names[frame_idx]
            frame = self.frames_group[frame_name]
            
            positions = frame['positions'][:]
            K_values = frame['contorsione_locale'][:]
            
            time = frame.attrs.get('time', 0.0)
            H_total = frame.attrs.get('H_total', 0.0)
            drift_values = frame['drift_matrix'][:] if 'drift_matrix' in frame else None
            
            # Rimuovi vecchi oggetti
            if network_collection is not None:
                network_collection.remove()
            if quiver_object is not None:
                quiver_object.remove()
            if mesh_collection is not None:
                mesh_collection.remove()
            if scatter_object is not None:
                scatter_object.remove()
            
            # Ricalcola geometria
            if render_mode in ['full', 'network', 'network+quivers']:
                edges = self._compute_torsion_network(positions, K_values)
                
                if len(edges) > 0:
                    segments = []
                    colors = []
                    K_intensities = np.array([edge[2] for edge in edges])
                    K_norm = (K_intensities - K_intensities.min()) / (K_intensities.max() - K_intensities.min() + 1e-12)
                    
                    for (i, j, K_avg), k_n in zip(edges, K_norm):
                        segments.append([positions[i], positions[j]])
                        colors.append(plt.cm.plasma(k_n))
                    
                    network_collection = Line3DCollection(
                        segments,
                        colors=colors,
                        linewidths=self.config.edge_linewidth,
                        alpha=self.config.edge_alpha
                    )
                    ax.add_collection3d(network_collection)
            
            if render_mode in ['full', 'quivers', 'network+quivers', 'isosurface+quivers']:
                quiver_origins, quiver_vectors = self._compute_torsion_quivers(
                    positions, K_values, drift_values
                )
                
                if len(quiver_origins) > 0:
                    quiver_object = ax.quiver(
                        quiver_origins[:, 0],
                        quiver_origins[:, 1],
                        quiver_origins[:, 2],
                        quiver_vectors[:, 0],
                        quiver_vectors[:, 1],
                        quiver_vectors[:, 2],
                        color='red',
                        alpha=self.config.quiver_alpha,
                        arrow_length_ratio=0.3,
                        linewidth=1.5
                    )
            
            if render_mode in ['full', 'isosurface', 'isosurface+quivers']:
                iso_vertices, iso_faces = self._compute_isosurface(positions, K_values)
                
                if len(iso_vertices) > 0:
                    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                    
                    triangles = iso_vertices[iso_faces]
                    mesh_collection = Poly3DCollection(
                        triangles,
                        alpha=self.config.mesh_alpha,
                        facecolors='cyan',
                        edgecolors='none',
                        shade=True
                    )
                    ax.add_collection3d(mesh_collection)
            
            if render_mode == 'full':
                subsample = max(1, len(positions) // 2000)
                pos_sub = positions[::subsample]
                K_sub = K_values[::subsample]
                
                scatter_object = ax.scatter(
                    pos_sub[:, 0],
                    pos_sub[:, 1],
                    pos_sub[:, 2],
                    c=np.abs(K_sub),
                    s=5,
                    alpha=0.3,
                    cmap='viridis'
                )
            
            # Aggiorna titolo
            title = f"Field Dynamics - Level {self.metadata.get('target_level', '?')}\n"
            title += f"Frame {frame_idx+1}/{N_frames} | t={time:.3f}s | H={H_total:.2e} J"
            ax.set_title(title, fontsize=12, fontweight='bold')
            
            # Info text
            info_str = f"K_mean: {K_values.mean():.2e}\n"
            info_str += f"K_max:  {K_values.max():.2e}\n"
            info_str += f"K_rms:  {np.sqrt(np.mean(K_values**2)):.2e}"
            info_text.set_text(info_str)
            
            if show_progress and (frame_idx % max(1, N_frames // 20) == 0):
                logger.info(f"  Rendering frame {frame_idx+1}/{N_frames} ({100*(frame_idx+1)/N_frames:.1f}%)")
            
            return [info_text]
        
        # Crea animazione
        logger.info("Creating field dynamics animation...")
        anim = FuncAnimation(
            fig,
            update,
            frames=N_frames,
            interval=1000/fps,
            blit=False,
            repeat=True
        )
        
        # Setup writer
        writer = FFMpegWriter(
            fps=fps,
            bitrate=bitrate,
            metadata={
                'title': f'WQT Field Dynamics - Level {self.metadata.get("target_level", "?")}',
                'artist': 'WQT Physics Team',
                'comment': f'Mode: {render_mode} | Frames: {N_frames}'
            }
        )
        
        # Salva video
        logger.info(f"Encoding video to {output_path}...")
        logger.info("  (This may take several minutes)")
        
        try:
            anim.save(output_path, writer=writer, dpi=dpi)
            logger.info("="*80)
            logger.info(f"✓ Field dynamics animation saved successfully!")
            logger.info(f"  File: {output_path}")
            logger.info(f"  Size: {output_path.stat().st_size / 1024**2:.2f} MB")
            logger.info(f"  Duration: {N_frames/fps:.2f} seconds")
            logger.info("="*80)
        except Exception as e:
            logger.error(f"Failed to save animation: {e}")
            logger.error("Ensure ffmpeg is installed: scoop install ffmpeg (Windows) or apt install ffmpeg (Linux)")
            raise
        finally:
            plt.close(fig)
    
    def animate_volumetric_manifold(
        self,
        output_path: Union[str, Path] = 'volumetric_evolution.mp4',
        apply_smoothing: bool = True,
        show_field_lines: bool = True,
        fps: int = 10,
        dpi: int = 120,
        bitrate: int = 2400,
        show_progress: bool = True
    ) -> None:
        """
        [RENDERING VOLUMETRICO DINAMICO: Evoluzione Mesh con Texture Chirale]
        
        Genera animazione MP4 dell'evoluzione del manifold con rendering volumetrico:
        1. Isosuperficie del campo χ con texture chirale dinamica
        2. Smoothing Gaussiano 3D per eliminare rumore Planckiano L0
        3. Linee di campo K (torsion trails) come telaio geometrico
        4. Mesh deformabile (NO scatter points)
        
        La texture chirale (Blu DX, Rosso SX, Bianco neutro) segue le undulazioni
        della mesh e l'opacità varia con ∂χ/∂t (dinamica del campo).
        
        VALIDAZIONE L3:
        ---------------
        Richiede dataset L3 con ≥13,824 segmenti. Non procede se inferiore.
        
        Parameters:
        -----------
        output_path : str or Path
            Path file MP4 output (default: 'volumetric_evolution.mp4')
        
        apply_smoothing : bool
            Applica Gaussian smoothing 3D (elimina rumore L0)
        
        show_field_lines : bool
            Mostra linee di campo K (torsion trails)
        
        fps : int
            Frame per second (default: 10)
        
        dpi : int
            Risoluzione video (default: 120)
        
        bitrate : int
            Bitrate video in kbps (default: 2400)
        
        show_progress : bool
            Stampa progress bar durante rendering
        
        Raises:
        -------
        ValueError
            Se dataset ha meno di 13,824 segmenti (non L3)
        
        ImportError
            Se scikit-image o ffmpeg non disponibili
        
        Examples:
        ---------
        >>> viz = ManifoldVisualizer()
        >>> viz.load_state('cosmology_L3.h5')
        >>> viz.animate_volumetric_manifold(
        ...     output_path='L3_volumetric.mp4',
        ...     apply_smoothing=True,
        ...     show_field_lines=True,
        ...     fps=12
        ... )
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        if not HAS_SKIMAGE:
            raise ImportError(
                "scikit-image required for volumetric rendering. "
                "Install with: pip install scikit-image"
            )
        
        try:
            from matplotlib.animation import FuncAnimation, FFMpegWriter
        except ImportError as e:
            raise ImportError(
                "matplotlib.animation required for video generation. "
                "Install with: pip install matplotlib[animation]"
            ) from e
        
        output_path = Path(output_path)
        N_frames = len(self.frame_names)
        
        # VALIDAZIONE L3: Verifica numero segmenti
        first_frame = self.frames_group[self.frame_names[0]]
        N_segments = len(first_frame['positions'][:])
        
        if N_segments < 13824:
            raise ValueError(
                f"Dataset validation failed: Expected ≥13,824 segments (L3), "
                f"found {N_segments}. Cannot proceed with L3 volumetric rendering."
            )
        
        logger.info("="*80)
        logger.info(" VOLUMETRIC MANIFOLD ANIMATION - L3 FRACTAL LEVEL")
        logger.info("="*80)
        logger.info(f"  Output:       {output_path}")
        logger.info(f"  Segments:     {N_segments} (L3 validated ✓)")
        logger.info(f"  Frames:       {N_frames}")
        logger.info(f"  Smoothing:    {'ON (Gaussian σ=' + str(self.config.smoothing_sigma) + ')' if apply_smoothing else 'OFF'}")
        logger.info(f"  Field lines:  {'ON' if show_field_lines else 'OFF'}")
        logger.info(f"  FPS:          {fps}")
        logger.info(f"  DPI:          {dpi}")
        logger.info(f"  Duration:     {N_frames/fps:.1f} seconds")
        logger.info("="*80)
        
        # Setup figura
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Calcola bounds globali
        all_positions = []
        for fname in self.frame_names[::max(1, N_frames//5)]:
            all_positions.append(self.frames_group[fname]['positions'][:])
        all_positions = np.vstack(all_positions)
        
        max_range = np.array([
            all_positions[:, 0].max() - all_positions[:, 0].min(),
            all_positions[:, 1].max() - all_positions[:, 1].min(),
            all_positions[:, 2].max() - all_positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (all_positions[:, 0].max() + all_positions[:, 0].min()) * 0.5
        mid_y = (all_positions[:, 1].max() + all_positions[:, 1].min()) * 0.5
        mid_z = (all_positions[:, 2].max() + all_positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Styling statico
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        ax.view_init(elev=20, azim=45)
        
        # Text handle per info temporali
        info_text = ax.text2D(0.02, 0.98, '', transform=ax.transAxes,
                              fontsize=10, verticalalignment='top',
                              bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        
        # Containers per oggetti grafici
        mesh_collection = None
        fieldlines_collection = None
        
        # Calcola derivate temporali χ per opacità dinamica (pre-compute)
        chi_derivatives = []
        for i in range(N_frames):
            frame = self.frames_group[self.frame_names[i]]
            chi_t = frame['chi_values'][:]
            
            if i > 0:
                frame_prev = self.frames_group[self.frame_names[i-1]]
                chi_prev = frame_prev['chi_values'][:]
                dt = frame.attrs.get('time', 0.0) - frame_prev.attrs.get('time', 0.0)
                dchi_dt = (chi_t - chi_prev) / (dt + 1e-10)
            else:
                dchi_dt = np.zeros_like(chi_t)
            
            chi_derivatives.append(dchi_dt)
        
        logger.info("Pre-computed temporal derivatives for dynamic opacity")
        
        # Update function
        def update(frame_idx: int):
            """
            Aggiorna geometria volumetrica per frame corrente.
            
            RENDERING VOLUMETRICO:
            - Isosuperficie χ con texture chirale
            - Linee di campo K (torsion trails)
            - Opacità dinamica basata su ∂χ/∂t
            """
            nonlocal mesh_collection, fieldlines_collection
            
            frame_name = self.frame_names[frame_idx]
            frame = self.frames_group[frame_name]
            
            positions = frame['positions'][:]
            chi_values = frame['chi_values'][:]
            K_values = frame['contorsione_locale'][:]
            dchi_dt = chi_derivatives[frame_idx]
            
            time = frame.attrs.get('time', 0.0)
            H_total = frame.attrs.get('H_total', 0.0)
            
            # Rimuovi vecchi oggetti
            if mesh_collection is not None:
                mesh_collection.remove()
            if fieldlines_collection is not None:
                fieldlines_collection.remove()
            
            # COMPUTE GEOMETRIA
            # 1. Linee di campo K (sotto la mesh)
            if show_field_lines:
                k_streamlines = self._compute_K_field_lines(positions, K_values, num_lines=12)
                
                if len(k_streamlines) > 0:
                    from mpl_toolkits.mplot3d.art3d import Line3DCollection
                    
                    segments = []
                    for line in k_streamlines:
                        for i in range(len(line) - 1):
                            segments.append([line[i], line[i+1]])
                    
                    fieldlines_collection = Line3DCollection(
                        segments,
                        colors='gray',
                        linewidths=0.4,
                        alpha=0.5
                    )
                    ax.add_collection3d(fieldlines_collection)
            
            # 2. Isosuperficie con texture chirale dinamica
            iso_vertices, iso_faces, chi_on_vertices = self._compute_chiral_isosurface(
                positions, chi_values, apply_smoothing=apply_smoothing
            )
            
            if len(iso_vertices) > 0:
                from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                
                triangles = iso_vertices[iso_faces]
                
                # TEXTURE CHIRALE DINAMICA
                chi_per_face = chi_on_vertices[iso_faces].mean(axis=1)
                
                # Interpola ∂χ/∂t sui vertici per opacità dinamica
                from scipy.spatial import KDTree
                tree = KDTree(positions)
                _, vert_indices = tree.query(iso_vertices, k=1)
                dchi_dt_on_vertices = dchi_dt[vert_indices]
                dchi_dt_per_face = dchi_dt_on_vertices[iso_faces].mean(axis=1)
                
                # Normalizza |∂χ/∂t| per opacità [0.4, 0.9]
                dchi_abs = np.abs(dchi_dt_per_face)
                if dchi_abs.max() > 1e-10:
                    opacity_norm = (dchi_abs - dchi_abs.min()) / (dchi_abs.max() - dchi_abs.min())
                    opacity = 0.4 + 0.5 * opacity_norm  # Range [0.4, 0.9]
                else:
                    opacity = np.full(len(iso_faces), 0.7)
                
                # Classifica chiralità
                right_mask = chi_per_face > self.config.chi_threshold_positive
                left_mask = chi_per_face < self.config.chi_threshold_negative
                neutral_mask = ~(right_mask | left_mask)
                
                # Crea array colori RGBA con opacità dinamica
                face_colors = np.zeros((len(iso_faces), 4))
                
                face_colors[right_mask] = np.c_[
                    np.full(np.sum(right_mask), 0.2),
                    np.full(np.sum(right_mask), 0.4),
                    np.full(np.sum(right_mask), 0.9),
                    opacity[right_mask]
                ]
                
                face_colors[left_mask] = np.c_[
                    np.full(np.sum(left_mask), 0.9),
                    np.full(np.sum(left_mask), 0.2),
                    np.full(np.sum(left_mask), 0.2),
                    opacity[left_mask]
                ]
                
                face_colors[neutral_mask] = np.c_[
                    np.full(np.sum(neutral_mask), 0.95),
                    np.full(np.sum(neutral_mask), 0.95),
                    np.full(np.sum(neutral_mask), 0.95),
                    opacity[neutral_mask] * 0.6
                ]
                
                mesh_collection = Poly3DCollection(
                    triangles,
                    facecolors=face_colors,
                    linewidths=0,
                    shade=True
                )
                ax.add_collection3d(mesh_collection)
            
            # Aggiorna titolo
            title = f"Volumetric L3 Manifold Evolution\n"
            title += f"Frame {frame_idx+1}/{N_frames} | t={time:.3f}s | "
            if apply_smoothing:
                title += f"σ={self.config.smoothing_sigma:.1f} | "
            title += f"{N_segments} segments"
            
            ax.set_title(title, fontsize=12, fontweight='bold')
            
            # Info text
            if len(iso_vertices) > 0:
                N_right = np.sum(right_mask)
                N_left = np.sum(left_mask)
                N_neutral = np.sum(neutral_mask)
                
                info_str = f"Vertices: {len(iso_vertices)}\n"
                info_str += f"DX: {N_right} | SX: {N_left} | ∅: {N_neutral}\n"
                info_str += f"|∂χ/∂t|: [{dchi_abs.min():.2e}, {dchi_abs.max():.2e}]"
                info_text.set_text(info_str)
            
            if show_progress and (frame_idx % max(1, N_frames // 10) == 0):
                logger.info(f"  Rendering frame {frame_idx+1}/{N_frames} ({100*(frame_idx+1)/N_frames:.1f}%)")
            
            return [info_text]
        
        # Crea animazione
        logger.info("Creating volumetric animation...")
        anim = FuncAnimation(
            fig,
            update,
            frames=N_frames,
            interval=1000/fps,
            blit=False,
            repeat=True
        )
        
        # Setup writer
        writer = FFMpegWriter(
            fps=fps,
            bitrate=bitrate,
            metadata={
                'title': f'WQT Volumetric Manifold L3 - {N_segments} segments',
                'artist': 'WQT Physics Team - Scientific Visualization Engineer',
                'comment': f'Frames: {N_frames} | Smoothing: {apply_smoothing}'
            }
        )
        
        # Salva video
        logger.info(f"Encoding volumetric animation to {output_path}...")
        logger.info("  (This may take several minutes for L3 dataset)")
        
        try:
            anim.save(output_path, writer=writer, dpi=dpi)
            logger.info("="*80)
            logger.info(f"✓ Volumetric animation saved successfully!")
            logger.info(f"  File: {output_path}")
            logger.info(f"  Size: {output_path.stat().st_size / 1024**2:.2f} MB")
            logger.info(f"  Duration: {N_frames/fps:.2f} seconds")
            logger.info(f"  Segments: {N_segments} (L3 fractal level)")
            logger.info("="*80)
        except Exception as e:
            logger.error(f"Failed to save volumetric animation: {e}")
            logger.error("Ensure ffmpeg is installed: scoop install ffmpeg (Windows) or apt install ffmpeg (Linux)")
            raise
        finally:
            plt.close(fig)
    
    def animate_density_network(
        self,
        output_path: Union[str, Path] = 'L3_density_network.mp4',
        k_neighbors: int = 6,
        chi_similarity_threshold: float = 0.05,
        point_size: float = 1.0,
        point_alpha: float = 0.05,
        line_alpha: float = 0.3,
        fps: int = 3,
        dpi: int = 120,
        bitrate: int = 2400,
        show_progress: bool = True
    ) -> None:
        """
        [RENDERING ALTERNATIVO: Density Cloud + k-NN Connectivity Network]
        
        Approccio complementare al volumetric rendering che preserva la natura
        DISCRETA dei segmenti Planckiani invece di forzare una superficie continua.
        
        FILOSOFIA:
        ----------
        - Non impone una "soglia" arbitraria (no Marching Cubes)
        - Mostra la DENSITÀ dei segmenti come "nuvola quantistica"
        - Rivela la CONNETTIVITÀ topologica via k-nearest neighbors
        - Colora i segmenti secondo χ (chiralità)
        - Disegna connessioni solo tra segmenti con Δχ < threshold
        
        RISULTATO VISIVO:
        -----------------
        - Aree dense di segmenti → regioni di campo forte (apparenza solida)
        - Aree rarefatte → vacuum foam (apparenza nebulosa)
        - Linee di connessione → "trama del vuoto" (network topologico)
        - Nessun artefatto da soglia isosurface
        
        Questo metodo è ideale per:
        1. Vedere le FLUTTUAZIONI discrete (non smoothate)
        2. Visualizzare la TOPOLOGIA del manifold (grafo di adiacenza)
        3. Evitare "bolle che appaiono/scompaiono" da soglie fisse
        
        Parameters:
        -----------
        output_path : str or Path
            Path file MP4 output
        
        k_neighbors : int
            Numero di vicini per k-NN connectivity (default: 6)
        
        chi_similarity_threshold : float
            Max differenza χ per disegnare connessione (default: 0.05)
            Solo segmenti con |Δχ| < threshold sono connessi
        
        point_size : float
            Dimensione punti scatter (default: 1.0, molto piccolo)
        
        point_alpha : float
            Trasparenza punti (default: 0.05, effetto nuvola)
        
        line_alpha : float
            Trasparenza linee connessione (default: 0.3)
        
        fps : int
            Frame per second (default: 3)
        
        dpi : int
            Risoluzione video (default: 120)
        
        bitrate : int
            Bitrate video in kbps (default: 2400)
        
        show_progress : bool
            Stampa progress bar durante rendering
        
        Raises:
        -------
        ValueError
            Se dataset ha meno di 13,824 segmenti (non L3)
        
        Examples:
        ---------
        >>> viz = ManifoldVisualizer()
        >>> viz.load_state('cosmology_L3.h5')
        >>> viz.animate_density_network(
        ...     output_path='L3_density_network.mp4',
        ...     k_neighbors=6,
        ...     chi_similarity_threshold=0.05,
        ...     point_alpha=0.05,
        ...     fps=3
        ... )
        
        Notes:
        ------
        Questo rendering è COMPLEMENTARE (non sostitutivo) del volumetric.
        - Volumetric → mostra campi continui (fisica macroscopica)
        - Density+Network → mostra discretizzazione L0 (fisica microscopica)
        """
        if self.hdf5_file is None:
            raise ValueError("No HDF5 state loaded. Call load_state() first.")
        
        try:
            from matplotlib.animation import FuncAnimation, FFMpegWriter
        except ImportError as e:
            raise ImportError(
                "matplotlib.animation required for video generation. "
                "Install with: pip install matplotlib[animation]"
            ) from e
        
        output_path = Path(output_path)
        N_frames = len(self.frame_names)
        
        # VALIDAZIONE L3
        first_frame = self.frames_group[self.frame_names[0]]
        N_segments = len(first_frame['positions'][:])
        
        if N_segments < 13824:
            raise ValueError(
                f"Dataset validation failed: Expected ≥13,824 segments (L3), "
                f"found {N_segments}. Cannot proceed with L3 density rendering."
            )
        
        logger.info("="*80)
        logger.info(" DENSITY + CONNECTIVITY NETWORK ANIMATION - L3 DISCRETE MANIFOLD")
        logger.info("="*80)
        logger.info(f"  Output:           {output_path}")
        logger.info(f"  Segments:         {N_segments} (L3 validated ✓)")
        logger.info(f"  Frames:           {N_frames}")
        logger.info(f"  k-NN neighbors:   {k_neighbors}")
        logger.info(f"  Chi threshold:    {chi_similarity_threshold}")
        logger.info(f"  Point alpha:      {point_alpha} (density cloud)")
        logger.info(f"  Line alpha:       {line_alpha} (network)")
        logger.info(f"  FPS:              {fps}")
        logger.info(f"  Duration:         {N_frames/fps:.1f} seconds")
        logger.info("="*80)
        
        # Setup figura
        fig = plt.figure(figsize=self.config.figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Calcola bounds globali
        all_positions = []
        for fname in self.frame_names[::max(1, N_frames//5)]:
            all_positions.append(self.frames_group[fname]['positions'][:])
        all_positions = np.vstack(all_positions)
        
        max_range = np.array([
            all_positions[:, 0].max() - all_positions[:, 0].min(),
            all_positions[:, 1].max() - all_positions[:, 1].min(),
            all_positions[:, 2].max() - all_positions[:, 2].min()
        ]).max() / 2.0
        
        mid_x = (all_positions[:, 0].max() + all_positions[:, 0].min()) * 0.5
        mid_y = (all_positions[:, 1].max() + all_positions[:, 1].min()) * 0.5
        mid_z = (all_positions[:, 2].max() + all_positions[:, 2].min()) * 0.5
        
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Styling
        ax.set_xlabel('X (m)', fontsize=11)
        ax.set_ylabel('Y (m)', fontsize=11)
        ax.set_zlabel('Z (m)', fontsize=11)
        ax.view_init(elev=20, azim=45)
        ax.set_facecolor('black')  # Sfondo nero per effetto nuvola
        fig.patch.set_facecolor('black')
        
        # Text handle
        info_text = ax.text2D(0.02, 0.98, '', transform=ax.transAxes,
                              fontsize=10, verticalalignment='top', color='white',
                              bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
        
        # Containers
        scatter_object = None
        network_collection = None
        
        # Colormap chirale (divergente)
        cmap = plt.cm.RdBu_r  # Rosso (SX) → Bianco → Blu (DX)
        
        logger.info("Creating density + network animation...")
        
        def update(frame_idx: int):
            """
            Aggiorna density cloud + k-NN network per frame corrente.
            
            RENDERING STRATEGY:
            - Scatter: Tutti i segmenti (nuvola densa)
            - Lines: Solo connessioni tra vicini con |Δχ| < threshold
            """
            nonlocal scatter_object, network_collection
            
            frame_name = self.frame_names[frame_idx]
            frame = self.frames_group[frame_name]
            
            positions = frame['positions'][:]
            chi_values = frame['chi_values'][:]
            
            time = frame.attrs.get('time', 0.0)
            
            # Rimuovi vecchi oggetti
            if scatter_object is not None:
                scatter_object.remove()
            if network_collection is not None:
                network_collection.remove()
            
            # 1. DENSITY CLOUD (tutti i segmenti)
            scatter_object = ax.scatter(
                positions[:, 0],
                positions[:, 1],
                positions[:, 2],
                c=chi_values,
                cmap=cmap,
                s=point_size,
                alpha=point_alpha,
                vmin=-np.abs(chi_values).max(),
                vmax=np.abs(chi_values).max(),
                edgecolors='none'
            )
            
            # 2. k-NN CONNECTIVITY NETWORK
            # Calcola k vicini per ogni segmento
            tree = KDTree(positions)
            distances, indices = tree.query(positions, k=k_neighbors+1)  # +1 perché include sé stesso
            
            # Filtra connessioni per similarità χ
            edges = []
            edge_colors = []
            
            for i in range(N_segments):
                chi_i = chi_values[i]
                
                for j_idx in range(1, k_neighbors+1):  # Salta sé stesso (indice 0)
                    j = indices[i, j_idx]
                    chi_j = chi_values[j]
                    
                    # Connetti solo se |Δχ| < threshold (segmenti simili)
                    if np.abs(chi_i - chi_j) < chi_similarity_threshold:
                        # Evita duplicati (i->j e j->i)
                        if i < j:
                            edges.append([positions[i], positions[j]])
                            
                            # Colore basato su χ medio
                            chi_mean = (chi_i + chi_j) / 2.0
                            # Normalizza [-max, +max] → [0, 1] per colormap
                            chi_norm = (chi_mean + np.abs(chi_values).max()) / (2.0 * np.abs(chi_values).max())
                            edge_colors.append(cmap(chi_norm))
            
            # Disegna network
            if len(edges) > 0:
                from mpl_toolkits.mplot3d.art3d import Line3DCollection
                
                network_collection = Line3DCollection(
                    edges,
                    colors=edge_colors,
                    linewidths=0.2,
                    alpha=line_alpha
                )
                ax.add_collection3d(network_collection)
            
            # Titolo
            title = f"Density + k-NN Network (L3 Discrete Manifold)\n"
            title += f"Frame {frame_idx+1}/{N_frames} | t={time:.3f}s | "
            title += f"{N_segments} segments | {len(edges)} connections"
            
            ax.set_title(title, fontsize=12, fontweight='bold', color='white')
            
            # Info text
            info_str = f"Segments: {N_segments}\n"
            info_str += f"k-NN: {k_neighbors} | Δχ < {chi_similarity_threshold}\n"
            info_str += f"Edges: {len(edges)}\n"
            info_str += f"χ range: [{chi_values.min():.2f}, {chi_values.max():.2f}]"
            info_text.set_text(info_str)
            
            if show_progress and (frame_idx % max(1, N_frames // 10) == 0):
                logger.info(f"  Rendering frame {frame_idx+1}/{N_frames} ({100*(frame_idx+1)/N_frames:.1f}%) - {len(edges)} edges")
            
            return [info_text]
        
        # Crea animazione
        anim = FuncAnimation(
            fig,
            update,
            frames=N_frames,
            interval=1000/fps,
            blit=False,
            repeat=True
        )
        
        # Setup writer
        writer = FFMpegWriter(
            fps=fps,
            bitrate=bitrate,
            metadata={
                'title': f'WQT Density Network L3 - {N_segments} segments',
                'artist': 'WQT Physics Team - Scientific Visualization Engineer',
                'comment': f'k-NN={k_neighbors} | Δχ<{chi_similarity_threshold}'
            }
        )
        
        # Salva video
        logger.info(f"Encoding density+network animation to {output_path}...")
        
        try:
            anim.save(output_path, writer=writer, dpi=dpi)
            logger.info("="*80)
            logger.info(f"✓ Density+Network animation saved successfully!")
            logger.info(f"  File: {output_path}")
            logger.info(f"  Size: {output_path.stat().st_size / 1024**2:.2f} MB")
            logger.info(f"  Duration: {N_frames/fps:.2f} seconds")
            logger.info(f"  Segments: {N_segments} (L3 fractal level)")
            logger.info("="*80)
        except Exception as e:
            logger.error(f"Failed to save density+network animation: {e}")
            logger.error("Ensure ffmpeg is installed: scoop install ffmpeg (Windows) or apt install ffmpeg (Linux)")
            raise
        finally:
            plt.close(fig)
    
    def close(self) -> None:
        """Chiude file HDF5 (cleanup)."""
        if self.hdf5_file is not None:
            self.hdf5_file.close()
            logger.info("HDF5 file closed")
            self.hdf5_file = None
            self.frames_group = None
    
    def __enter__(self):
        """Context manager support."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
    
    def __del__(self):
        """Destructor cleanup."""
        self.close()


if __name__ == '__main__':
    """
    Test utility integrata.
    
    Testa rendering statico e animazione su dataset L1/L2/L3 disponibili.
    
    Usage:
        python -m wqt_oop.visualizer                    # Run all tests
        python -m wqt_oop.visualizer --animate          # Test animation only
        python -m wqt_oop.visualizer --dataset L3       # Test specific level
    """
    import sys
    import argparse
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Test ManifoldVisualizer')
    parser.add_argument('--animate', action='store_true', help='Test animation generation')
    parser.add_argument('--dataset', choices=['L1', 'L2', 'L3'], help='Test specific dataset level')
    args = parser.parse_args()
    
    print("="*80)
    print(" MANIFOLD VISUALIZER - Test Suite")
    print("="*80)
    
    # Cerca dataset disponibili
    test_data_dir = Path(__file__).parent.parent / 'VQT'
    if not test_data_dir.exists():
        test_data_dir = Path.cwd()
    
    datasets = {
        'L1': test_data_dir / 'cosmology_L1.h5',
        'L2': test_data_dir / 'cosmology_L2.h5',
        'L3': test_data_dir / 'cosmology_L3_equilibrio.h5'
    }
    
    # Filter by requested dataset
    if args.dataset:
        datasets = {args.dataset: datasets[args.dataset]}
    
    available = {k: v for k, v in datasets.items() if v.exists()}
    
    if not available:
        print("❌ No test datasets found!")
        print(f"   Searched in: {test_data_dir}")
        print("   Expected files: cosmology_L1.h5, cosmology_L2.h5, cosmology_L3_equilibrio.h5")
        sys.exit(1)
    
    print(f"Found {len(available)} dataset(s):")
    for name, path in available.items():
        print(f"  ✓ {name}: {path}")
    print()
    
    # Test rendering
    for level_name, dataset_path in available.items():
        print("="*80)
        print(f" Testing {level_name} - {dataset_path.name}")
        print("="*80)
        
        viz = ManifoldVisualizer()
        viz.load_state(dataset_path)
        
        # Static rendering tests
        if not args.animate:
            print("\n1. Testing full rendering...")
            viz.render_chiral_manifold(
                mode='full',
                frame_index=-1,
                save_path=f'test_{level_name}_chiral_full.png',
                show=False
            )
            
            print("\n2. Testing chiral-only rendering...")
            viz.render_chiral_manifold(
                mode='chiral_only',
                frame_index=-1,
                save_path=f'test_{level_name}_chiral_only.png',
                show=False
            )
            
            print("\n3. Testing torsion field rendering...")
            viz.render_torsion_field(
                frame_index=-1,
                save_path=f'test_{level_name}_torsion.png',
                show=False
            )
        
        # Animation test (only for L1 or if explicitly requested)
        if args.animate or (level_name == 'L1' and not args.dataset):
            print("\n4. Testing animation generation...")
            viz.animate_manifold(
                output_path=f'test_{level_name}_animation.mp4',
                mode='full',
                fps=10 if level_name == 'L1' else 8,
                dpi=80,  # Low quality for fast testing
                bitrate=1200,
                show_progress=True
            )
        
        viz.close()
        print()
    
    print("="*80)
    print(" ✓ ALL TESTS PASSED")
    print("="*80)
    print("\nGenerated files:")
    for f in Path.cwd().glob('test_*'):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.2f} KB)")
    print()
    repo_dir = Path(__file__).parent.parent
    vqt_dir = repo_dir.parent / 'VQT'
    
    test_files = [
        vqt_dir / 'cosmology_L1.h5',
        vqt_dir / 'cosmology_L2.h5',
        vqt_dir / 'cosmology_L3.h5',
        vqt_dir / 'cosmology_L3_equilibrio.h5',
    ]
    
    available_files = [f for f in test_files if f.exists()]
    
    if len(available_files) == 0:
        print("ERROR: No test HDF5 files found in VQT/ directory")
        print("Expected files:")
        for f in test_files:
            print(f"  - {f}")
        sys.exit(1)
    
    print(f"\nFound {len(available_files)} test files:")
    for i, f in enumerate(available_files):
        print(f"  [{i}] {f.name} ({f.stat().st_size / 1e6:.1f} MB)")
    
    # Test con primo file disponibile
    test_file = available_files[0]
    print(f"\nTesting with: {test_file.name}")
    print("="*80)
    
    # Context manager per cleanup automatico
    with ManifoldVisualizer() as viz:
        # Load
        viz.load_state(test_file)
        
        # Test 1: Full chiral rendering (ultimo frame)
        print("\n[TEST 1] Full chiral manifold rendering...")
        viz.render_chiral_manifold(
            mode='full',
            frame_index=-1,
            save_path=repo_dir / 'test_chiral_full.png',
            show=False
        )
        
        # Test 2: Chiral only (primo frame)
        print("\n[TEST 2] Chiral-only rendering (first frame)...")
        viz.render_chiral_manifold(
            mode='chiral_only',
            frame_index=0,
            save_path=repo_dir / 'test_chiral_only.png',
            show=False
        )
        
        # Test 3: Torsion field
        print("\n[TEST 3] Torsion field rendering...")
        viz.render_torsion_field(
            frame_index=-1,
            save_path=repo_dir / 'test_torsion_field.png',
            show=False
        )
        
        # Metadata
        print("\n[METADATA]")
        meta = viz.get_metadata()
        for key, value in meta.items():
            print(f"  {key}: {value}")
        
        print(f"\nTotal frames: {viz.get_frame_count()}")
    
    print("\n" + "="*80)
    print(" ✓ ALL TESTS PASSED")
    print("="*80)
    print("\nOutput files:")
    print("  - test_chiral_full.png")
    print("  - test_chiral_only.png")
    print("  - test_torsion_field.png")
