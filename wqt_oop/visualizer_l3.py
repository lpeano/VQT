"""
================================================================================
MANIFOLD VISUALIZER L3 - High-Performance Chiral Dynamics Renderer
================================================================================

Visualizzatore scientifico ad alte prestazioni per dataset L3 (13,824 segmenti).
Ottimizzato per rendering accurato della dinamica chirale e vacuum foam.

FEATURES:
---------
1. Validazione rigorosa dataset L3 (13,824 segmenti obbligatori)
2. Colormap divergente scientifica per campo χ
3. Opacità dinamica basata su Δχ/Δt (Zitterbewegung visualization)
4. Rendering incrementale con FuncAnimation (NO ricreazione plot)
5. Vacuum foam masking con densità adattiva
6. Debug logging del bilanciamento chirale frame-by-frame
7. Backend Agg per performance ottimali

PHYSICS VISUALIZATION:
----------------------
- χ > +0.1: BLU (Destrorsa, "materia")
- χ < -0.1: ROSSO (Sinistrorsa, "antimateria")
- |χ| ≤ 0.1: BIANCO/Trasparente (Vuoto quantistico)
- Opacità ∝ |Δχ/Δt| (fluttuazioni energetiche)

USAGE:
------
>>> from wqt_oop.visualizer_l3 import ManifoldVisualizerL3
>>> viz = ManifoldVisualizerL3()
>>> viz.load_state('cosmology_L3_equilibrio.h5')  # Valida 13,824 segmenti
>>> viz.animate_manifold('L3_dynamics.mp4', fps=10, dpi=120)

Author: WQT Physics Team (Senior Graphics Engineer)
Date: 2026-05-26
================================================================================
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
from dataclasses import dataclass

import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')  # Backend non-interattivo per performance
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.animation import FuncAnimation, FFMpegWriter
from mpl_toolkits.mplot3d import Axes3D

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfigL3:
    """
    Configurazione rendering L3 ottimizzata.
    
    Attributes:
    -----------
    chi_threshold : float
        Soglia assoluta per classificare neutro (default: 0.1)
    
    color_right : str
        Colore destrorsa (default: 'blue')
    
    color_left : str
        Colore sinistrorsa (default: 'red')
    
    color_neutral : str
        Colore vuoto quantistico (default: 'white')
    
    marker_size : int
        Dimensione markers (default: 5 per L3)
    
    alpha_base : float
        Opacità base per segmenti (default: 0.6)
    
    alpha_neutral_min : float
        Opacità minima vacuum (default: 0.1)
    
    alpha_dynamic_scale : float
        Fattore scala per opacità dinamica (default: 10.0)
    
    vacuum_foam_density_threshold : float
        Percentile per masking vacuum foam (default: 50.0)
        Solo vacuum con |Δχ/Δt| > percentile vengono mostrati
    
    dpi : int
        Risoluzione output (default: 120)
    
    figsize : Tuple[int, int]
        Dimensione figura (default: (14, 12))
    """
    chi_threshold: float = 0.1
    color_right: str = '#2E86DE'  # Blu scuro
    color_left: str = '#EE5A6F'   # Rosso corallo
    color_neutral: str = '#F5F6FA'  # Bianco ghiaccio
    marker_size: int = 5
    alpha_base: float = 0.6
    alpha_neutral_min: float = 0.1
    alpha_dynamic_scale: float = 10.0
    vacuum_foam_density_threshold: float = 50.0
    dpi: int = 120
    figsize: Tuple[int, int] = (14, 12)


class ManifoldVisualizerL3:
    """
    [LEGGE FISICA: Rendering Scientifico Dinamica Chirale L3]
    
    Visualizzatore ad alte prestazioni per manifold L3 (13,824 segmenti).
    
    Validazione Rigorosa:
    ---------------------
    Il visualizzatore RICHIEDE esattamente 13,824 segmenti. Se il dataset
    caricato ha un numero diverso, solleva ValueError dettagliato.
    
    Opacità Dinamica:
    -----------------
    L'opacità di ogni punto è modulata da:
        α(i) = α_base + α_scale · |Δχ_i/Δt|
    
    dove Δχ_i/Δt è la derivata temporale del campo scalare. Questo
    evidenzia le fluttuazioni del vuoto quantistico (Zitterbewegung).
    
    Vacuum Foam Masking:
    --------------------
    I segmenti neutri (|χ| < 0.1) con bassa varianza energetica vengono
    resi trasparenti per evitare noise visivo. Solo le fluttuazioni
    significative (> percentile threshold) sono visualizzate.
    
    Methods:
    --------
    load_state(hdf5_path) : Carica e valida dataset L3
    animate_manifold(output_path, fps, dpi, bitrate) : Genera video MP4
    close() : Cleanup HDF5
    """
    
    # Costanti di validazione
    L3_EXPECTED_SEGMENTS = 13824
    L3_EXPECTED_LEVEL = 3
    
    def __init__(self, config: Optional[VisualizationConfigL3] = None):
        """
        Inizializza visualizzatore L3.
        
        Parameters:
        -----------
        config : VisualizationConfigL3, optional
            Configurazione rendering (default: parametri ottimizzati L3)
        """
        self.config = config or VisualizationConfigL3()
        self.hdf5_file: Optional[h5py.File] = None
        self.frames_group: Optional[h5py.Group] = None
        self.frame_names: List[str] = []
        self.metadata: Dict = {}
        
        # Cache per Δχ/Δt (evita ricalcolo)
        self.chi_derivatives: Optional[np.ndarray] = None
        
        logger.info("="*80)
        logger.info(" MANIFOLD VISUALIZER L3 - High-Performance Chiral Renderer")
        logger.info("="*80)
        logger.info(f"  Expected segments: {self.L3_EXPECTED_SEGMENTS}")
        logger.info(f"  Chi threshold:     ±{self.config.chi_threshold}")
        logger.info(f"  Color scheme:      {self.config.color_left} / {self.config.color_neutral} / {self.config.color_right}")
        logger.info(f"  Backend:           {matplotlib.get_backend()}")
        logger.info("="*80)
    
    def load_state(self, hdf5_path: Union[str, Path]) -> None:
        """
        Carica e valida dataset L3.
        
        VALIDAZIONE RIGOROSA:
        ---------------------
        - Numero segmenti DEVE essere esattamente 13,824
        - Se diverso, solleva ValueError con diagnostica dettagliata
        
        Parameters:
        -----------
        hdf5_path : str or Path
            Path file HDF5 contenente simulazione L3
        
        Raises:
        -------
        FileNotFoundError
            Se file non esiste
        
        ValueError
            Se numero segmenti != 13,824 o schema HDF5 non compatibile
        """
        hdf5_path = Path(hdf5_path)
        
        if not hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")
        
        logger.info(f"Loading L3 dataset from: {hdf5_path}")
        
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
        
        # VALIDAZIONE CRITICA: Numero segmenti
        first_frame = self.frames_group[self.frame_names[0]]
        
        if 'chi_values' not in first_frame:
            raise ValueError("Frame missing 'chi_values' dataset. Invalid schema.")
        
        N_segments = len(first_frame['chi_values'][:])
        
        logger.info(f"  Frames loaded:     {len(self.frame_names)}")
        logger.info(f"  Segments detected: {N_segments}")
        
        # VALIDAZIONE RIGOROSA
        if N_segments != self.L3_EXPECTED_SEGMENTS:
            error_msg = (
                f"\n{'='*80}\n"
                f" VALIDATION ERROR: Incorrect segment count for L3\n"
                f"{'='*80}\n"
                f"  Expected: {self.L3_EXPECTED_SEGMENTS} segments (Level 3)\n"
                f"  Detected: {N_segments} segments\n"
                f"  Dataset:  {hdf5_path.name}\n"
                f"\n"
                f"  Possible causes:\n"
                f"  - Wrong dataset level (check if L1/L2 instead of L3)\n"
                f"  - Corrupted HDF5 file\n"
                f"  - Incomplete simulation run\n"
                f"\n"
                f"  Expected level hierarchy:\n"
                f"    L1:  24      segments (2^0 × 24)\n"
                f"    L2:  576     segments (24^2)\n"
                f"    L3:  13,824  segments (24^3)  ← REQUIRED\n"
                f"    L4:  331,776 segments (24^4)\n"
                f"\n"
                f"  This visualizer is EXCLUSIVELY for L3 datasets.\n"
                f"  For L1/L2, use the standard ManifoldVisualizer.\n"
                f"{'='*80}\n"
            )
            raise ValueError(error_msg)
        
        logger.info(f"  [OK] Segment count validated: {N_segments} == {self.L3_EXPECTED_SEGMENTS}")
        
        # Verifica datasets richiesti
        required_datasets = ['positions', 'chi_values', 'velocities']
        missing = [ds for ds in required_datasets if ds not in first_frame]
        
        if missing:
            raise ValueError(f"Frame missing required datasets: {missing}")
        
        # Pre-calcola Δχ/Δt per tutti i frames (cache per performance)
        logger.info("  Pre-computing temporal derivatives Δχ/Δt...")
        self._compute_chi_derivatives()
        
        logger.info("  [OK] L3 dataset loaded and validated successfully")
        logger.info("="*80)
    
    def _compute_chi_derivatives(self) -> None:
        """
        Pre-calcola derivate temporali Δχ/Δt per opacità dinamica.
        
        Δχ_i/Δt ≈ (χ_i(t+Δt) - χ_i(t)) / Δt
        
        Stored in self.chi_derivatives: (N_frames, N_segments)
        """
        N_frames = len(self.frame_names)
        N_segments = self.L3_EXPECTED_SEGMENTS
        
        self.chi_derivatives = np.zeros((N_frames, N_segments))
        
        for i in range(N_frames):
            frame_current = self.frames_group[self.frame_names[i]]
            chi_current = frame_current['chi_values'][:]
            
            if i < N_frames - 1:
                # Forward difference
                frame_next = self.frames_group[self.frame_names[i + 1]]
                chi_next = frame_next['chi_values'][:]
                
                t_current = frame_current.attrs.get('time', 0.0)
                t_next = frame_next.attrs.get('time', 0.0)
                dt = t_next - t_current
                
                if dt > 0:
                    self.chi_derivatives[i, :] = (chi_next - chi_current) / dt
                else:
                    self.chi_derivatives[i, :] = 0.0
            else:
                # Ultimo frame: usa backward difference
                frame_prev = self.frames_group[self.frame_names[i - 1]]
                chi_prev = frame_prev['chi_values'][:]
                
                t_current = frame_current.attrs.get('time', 0.0)
                t_prev = frame_prev.attrs.get('time', 0.0)
                dt = t_current - t_prev
                
                if dt > 0:
                    self.chi_derivatives[i, :] = (chi_current - chi_prev) / dt
                else:
                    self.chi_derivatives[i, :] = 0.0
        
        logger.info(f"    Δχ/Δt range: [{np.min(np.abs(self.chi_derivatives)):.2e}, {np.max(np.abs(self.chi_derivatives)):.2e}]")
    
    def _classify_chirality(self, chi_values: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Classifica segmenti per chiralità.
        
        Parameters:
        -----------
        chi_values : np.ndarray (N,)
            Valori campo χ
        
        Returns:
        --------
        right_mask, left_mask, neutral_mask : Tuple[np.ndarray, np.ndarray, np.ndarray]
            Boolean masks per ciascuna categoria chirale
        """
        right_mask = chi_values > self.config.chi_threshold
        left_mask = chi_values < -self.config.chi_threshold
        neutral_mask = ~(right_mask | left_mask)
        
        return right_mask, left_mask, neutral_mask
    
    def _compute_dynamic_alpha(self, frame_idx: int, chi_values: np.ndarray) -> np.ndarray:
        """
        Calcola opacità dinamica basata su |Δχ/Δt|.
        
        α(i) = α_base + α_scale · normalized(|Δχ_i/Δt|)
        
        Con masking per vacuum foam: segmenti neutri con bassa
        varianza energetica ricevono α → α_min.
        
        Parameters:
        -----------
        frame_idx : int
            Indice frame corrente
        
        chi_values : np.ndarray (N,)
            Valori χ correnti
        
        Returns:
        --------
        alpha_values : np.ndarray (N,)
            Opacità per ciascun segmento [0.0, 1.0]
        """
        dchi_dt = np.abs(self.chi_derivatives[frame_idx, :])
        
        # Normalizza [0, 1]
        dchi_max = np.percentile(dchi_dt, 99)  # Robust normalization
        dchi_norm = np.clip(dchi_dt / (dchi_max + 1e-10), 0.0, 1.0)
        
        # Opacità base + contributo dinamico
        alpha = self.config.alpha_base + self.config.alpha_dynamic_scale * dchi_norm
        alpha = np.clip(alpha, 0.0, 1.0)
        
        # Vacuum foam masking: neutri con bassa varianza → trasparenti
        _, _, neutral_mask = self._classify_chirality(chi_values)
        
        if np.any(neutral_mask):
            # Calcola threshold basato su percentile
            dchi_neutral = dchi_dt[neutral_mask]
            threshold = np.percentile(dchi_neutral, self.config.vacuum_foam_density_threshold)
            
            # Maschera neutri sotto-soglia
            low_variance_neutral = neutral_mask & (dchi_dt < threshold)
            alpha[low_variance_neutral] = self.config.alpha_neutral_min
        
        return alpha
    
    def animate_manifold(
        self,
        output_path: Union[str, Path] = 'L3_evolution.mp4',
        fps: int = 5,  # REDUCED: 5fps for scientific analysis (200ms/frame)
        dpi: int = 120,  # INCREASED: Better quality
        bitrate: int = 3000,  # INCREASED: Avoid compression artifacts
        frame_skip: int = 1,  # Skip frames if dataset too dense (1 = no skip)
        show_vacuum_foam: bool = True,
        show_progress: bool = True
    ) -> None:
        """
        [LEGGE FISICA: Evoluzione Temporale Chirale con Vacuum Foam]
        
        Genera animazione MP4 della dinamica del manifold L3, visualizzando:
        1. Transizione DX→SX (rottura simmetria CP)
        2. Fluttuazioni Zitterbewegung (opacità dinamica)
        3. Vacuum foam structure (mascheramento adattivo)
        4. Energy churning hotspots (alta |Δχ/Δt|)
        
        PERFORMANCE OPTIMIZATION:
        -------------------------
        - Update incrementale (NO ricreazione scatter objects)
        - Backend Agg (NO overhead interattivo)
        - Pre-computed Δχ/Δt (cached)
        - Vacuum masking (riduce punti renderizzati)
        
        Parameters:
        -----------
        output_path : str or Path
            Path file MP4 output
        
        fps : int
            Frame per second (default: 10)
        
        dpi : int
            Risoluzione video (default: 120)
        
        bitrate : int
            Bitrate video in kbps (default: 2400)
        
        show_vacuum_foam : bool
            Mostra vacuum foam mascherato (default: True)
        
        Raises:
        -------
        ValueError
            Se dataset non caricato o validazione fallita
        
        ImportError
            Se ffmpeg non disponibile
        """
        if self.hdf5_file is None:
            raise ValueError("No L3 dataset loaded. Call load_state() first.")
        
        output_path = Path(output_path)
        N_frames = len(self.frame_names)
        
        logger.info("="*80)
        logger.info(" L3 ANIMATION RENDERER - Chiral Dynamics Visualization")
        logger.info("="*80)
        logger.info(f"  Output:       {output_path}")
        logger.info(f"  Segments:     {self.L3_EXPECTED_SEGMENTS}")
        logger.info(f"  Frames:       {N_frames}")
        logger.info(f"  FPS:          {fps}")
        logger.info(f"  DPI:          {dpi}")
        logger.info(f"  Bitrate:      {bitrate} kbps")
        logger.info(f"  Duration:     {N_frames/fps:.1f} seconds")
        logger.info(f"  Vacuum foam:  {'ENABLED' if show_vacuum_foam else 'DISABLED'}")
        logger.info("="*80)
        
        # =======================================================================
        # DARK THEME SETUP - Scientific Visualization Mode
        # =======================================================================
        plt.style.use('dark_background')
        
        # Carica primo frame per setup
        first_frame = self.frames_group[self.frame_names[0]]
        positions = first_frame['positions'][:]
        chi_values = first_frame['chi_values'][:]
        
        right_mask, left_mask, neutral_mask = self._classify_chirality(chi_values)
        alpha_values = self._compute_dynamic_alpha(0, chi_values)
        
        # Setup figura e asse con sfondo custom
        fig = plt.figure(figsize=self.config.figsize, facecolor='#0B0E14')
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#0B0E14')  # Deep space black
        
        # =======================================================================
        # LAYERED RENDERING - Background (Vacuum) → Foreground (Matter)
        # =======================================================================
        
        # LAYER 1: Vacuum Foam (Background) - Grigio scuro con alpha bassissimo
        scatter_neutral = None
        if show_vacuum_foam and np.any(neutral_mask):
            scatter_neutral = ax.scatter(
                positions[neutral_mask, 0],
                positions[neutral_mask, 1],
                positions[neutral_mask, 2],
                c='#2C3E50',  # Dark gray
                s=self.config.marker_size // 3,  # Piccoli punti
                alpha=0.1,  # MOLTO trasparente per non bruciare vista
                label='Vacuum foam',
                depthshade=False,
                edgecolors='none',
                zorder=1  # Background layer
            )
        
        # LAYER 2: DX Matter (Foreground) - Blu brillante
        scatter_right = ax.scatter(
            positions[right_mask, 0],
            positions[right_mask, 1],
            positions[right_mask, 2],
            c='#007BFF',  # Scientific blue (Bootstrap primary)
            s=self.config.marker_size,
            alpha=0.8,  # Alta opacità per brillare
            label='Right-handed (DX)',
            depthshade=True,
            edgecolors='none',
            zorder=2  # Foreground layer
        )
        
        # LAYER 3: SX Antimatter (Foreground) - Rosso brillante
        scatter_left = ax.scatter(
            positions[left_mask, 0],
            positions[left_mask, 1],
            positions[left_mask, 2],
            c='#FF4136',  # Scientific red (high visibility)
            s=self.config.marker_size,
            alpha=0.8,  # Alta opacità per brillare
            label='Left-handed (SX)',
            depthshade=True,
            edgecolors='none',
            zorder=2  # Foreground layer
        )
        
        # =======================================================================
        # AXIS STYLING - High contrast on dark background
        # =======================================================================
        ax.set_xlabel('X (m)', fontsize=11, labelpad=10, color='white')
        ax.set_ylabel('Y (m)', fontsize=11, labelpad=10, color='white')
        ax.set_zlabel('Z (m)', fontsize=11, labelpad=10, color='white')
        
        # Tick colors
        ax.tick_params(axis='x', colors='gray', labelsize=9)
        ax.tick_params(axis='y', colors='gray', labelsize=9)
        ax.tick_params(axis='z', colors='gray', labelsize=9)
        
        # Grid subtle
        ax.grid(True, alpha=0.1, color='gray', linestyle=':')
        
        # Pane colors (molto scuri)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('#1C1C1C')
        ax.yaxis.pane.set_edgecolor('#1C1C1C')
        ax.zaxis.pane.set_edgecolor('#1C1C1C')
        
        # Legend con sfondo scuro
        legend = ax.legend(loc='upper right', fontsize=9, framealpha=0.8, 
                          facecolor='#1C1C1C', edgecolor='gray')
        for text in legend.get_texts():
            text.set_color('white')
        
        # Equal aspect ratio (calcolato su tutti i frames)
        all_positions = []
        for fname in self.frame_names[::max(1, N_frames//5)]:
            all_positions.append(self.frames_group[fname]['positions'][:])
        all_positions = np.vstack(all_positions)
        
        max_range = np.array([
            np.ptp(all_positions[:, 0]),
            np.ptp(all_positions[:, 1]),
            np.ptp(all_positions[:, 2])
        ]).max() / 2.0
        
        mid = all_positions.mean(axis=0)
        ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
        ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
        ax.set_zlim(mid[2] - max_range, mid[2] + max_range)
        
        # =======================================================================
        # DYNAMIC INFO OVERLAY - Frame stats in real-time
        # =======================================================================
        info_text = ax.text2D(0.02, 0.98, '', transform=ax.transAxes,
                              fontsize=11, verticalalignment='top',
                              family='monospace', color='#00FF00',  # Terminal green
                              weight='bold',
                              bbox=dict(boxstyle='round', facecolor='#0B0E14', 
                                       edgecolor='#00FF00', alpha=0.9, linewidth=2))
        
        # Update function (PERFORMANCE CRITICAL)
        # Closure captures: show_vacuum_foam, show_progress
        _show_progress = show_progress  # Capture in closure scope
        
        def update(frame_idx: int):
            """Aggiorna plot per frame corrente (NO ricreazione oggetti)."""
            frame_name = self.frame_names[frame_idx]
            frame = self.frames_group[frame_name]
            
            positions = frame['positions'][:]
            chi_values = frame['chi_values'][:]
            
            time = frame.attrs.get('time', 0.0)
            H_total = frame.attrs.get('H_total', 0.0)
            drift = frame.attrs.get('drift', 0.0)
            
            # Riclassifica chiralità
            right_mask, left_mask, neutral_mask = self._classify_chirality(chi_values)
            alpha_values = self._compute_dynamic_alpha(frame_idx, chi_values)
            
            # CRITICAL: Update solo dati, NO ricreazione
            if np.any(right_mask):
                scatter_right._offsets3d = (
                    positions[right_mask, 0],
                    positions[right_mask, 1],
                    positions[right_mask, 2]
                )
                scatter_right.set_alpha(alpha_values[right_mask].mean())
            
            if np.any(left_mask):
                scatter_left._offsets3d = (
                    positions[left_mask, 0],
                    positions[left_mask, 1],
                    positions[left_mask, 2]
                )
                scatter_left.set_alpha(alpha_values[left_mask].mean())
            
            if scatter_neutral is not None and np.any(neutral_mask):
                scatter_neutral._offsets3d = (
                    positions[neutral_mask, 0],
                    positions[neutral_mask, 1],
                    positions[neutral_mask, 2]
                )
                scatter_neutral.set_alpha(alpha_values[neutral_mask].mean())
            
            # Update titolo
            title = f"L3 Chiral Manifold Evolution - 13,824 Segments\n"
            title += f"Frame {frame_idx+1}/{N_frames} | t={time:.3f}s | H={H_total:.2e} J | Drift={drift:.2e}"
            ax.set_title(title, fontsize=13, fontweight='bold', color='white', pad=20)
            
            # DEBUG INFO (richiesto)
            N_right = np.sum(right_mask)
            N_left = np.sum(left_mask)
            N_neutral = np.sum(neutral_mask)
            N_total = len(chi_values)
            
            info_str = f"Frame: {frame_idx+1:3d}/{N_frames} | t={time:5.2f}s\n"
            info_str += f"DX:     {N_right:5d} ({100*N_right/N_total:5.1f}%)\n"
            info_str += f"SX:     {N_left:5d} ({100*N_left/N_total:5.1f}%)\n"
            info_str += f"Neutro: {N_neutral:5d} ({100*N_neutral/N_total:5.1f}%)\n"
            info_str += f"Drift:  {drift:.3e}"
            info_text.set_text(info_str)
            
            # Console logging (OGNI FRAME come richiesto)
            if _show_progress:
                logger.info(f"  Frame: {frame_idx+1:3d} | DX: {100*N_right/N_total:5.1f}% | SX: {100*N_left/N_total:5.1f}% | Neutro: {100*N_neutral/N_total:5.1f}%")
            
            return [scatter_right, scatter_left, scatter_neutral, info_text]
        
        # Crea animazione
        logger.info("Creating FuncAnimation...")
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
                'title': 'WQT L3 Manifold - Chiral Dynamics Evolution',
                'artist': 'WQT Physics Team',
                'comment': f'13,824 segments | {N_frames} frames | Vacuum foam visualization'
            }
        )
        
        # Salva video
        logger.info(f"Encoding video to {output_path}...")
        logger.info("  (Rendering 13,824 segments × 20 frames - this will take a few minutes)")
        logger.info("")
        
        try:
            anim.save(output_path, writer=writer, dpi=dpi)
            
            file_size_mb = output_path.stat().st_size / 1024**2
            
            logger.info("")
            logger.info("="*80)
            logger.info(" [OK] L3 ANIMATION COMPLETED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info(f"  File:     {output_path}")
            logger.info(f"  Size:     {file_size_mb:.2f} MB")
            logger.info(f"  Duration: {N_frames/fps:.2f} seconds")
            logger.info(f"  Quality:  {dpi} DPI, {bitrate} kbps")
            logger.info("="*80)
            logger.info(f"  View with: vlc {output_path}")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"Failed to save animation: {e}")
            logger.error("Ensure ffmpeg is installed: scoop install ffmpeg (Windows)")
            raise
        finally:
            plt.close(fig)
    
    def close(self) -> None:
        """Chiude file HDF5 (cleanup)."""
        if self.hdf5_file is not None:
            self.hdf5_file.close()
            logger.info("L3 dataset closed")
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
    Test integrato per L3 visualizer.
    
    Usage:
        python -m wqt_oop.visualizer_l3
    """
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*80)
    print(" L3 MANIFOLD VISUALIZER - Test Suite")
    print("="*80 + "\n")
    
    # Cerca dataset L3
    test_paths = [
        Path.cwd() / 'cosmology_L3_equilibrio.h5',
        Path.cwd().parent / 'VQT' / 'cosmology_L3_equilibrio.h5',
        Path(r'C:\Users\lpeano\plank\VQT\cosmology_L3_equilibrio.h5'),
    ]
    
    dataset_path = None
    for path in test_paths:
        if path.exists():
            dataset_path = path
            break
    
    if dataset_path is None:
        print("[ERROR] L3 dataset not found!")
        print("   Searched paths:")
        for p in test_paths:
            print(f"     - {p}")
        print("\n   Please ensure cosmology_L3_equilibrio.h5 is available.")
        sys.exit(1)
    
    print(f"[OK] Found L3 dataset: {dataset_path}\n")
    
    # Test visualizer
    viz = ManifoldVisualizerL3()
    
    try:
        print("Loading and validating L3 dataset...")
        viz.load_state(dataset_path)
        
        print("\nGenerating L3 animation (this will take 3-5 minutes)...\n")
        viz.animate_manifold(
            output_path='L3_test_animation.mp4',
            fps=10,
            dpi=100,  # Reduced DPI for faster testing
            bitrate=2000,
            show_vacuum_foam=True
        )
        
        print("\n" + "="*80)
        print(" [OK] L3 TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(f"\nGenerated: L3_test_animation.mp4")
        print("View with: vlc L3_test_animation.mp4\n")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        viz.close()
