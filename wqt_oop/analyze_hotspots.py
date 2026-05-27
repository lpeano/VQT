"""
═══════════════════════════════════════════════════════════════════════════════
 ANALYZE HOTSPOTS - Post-Mortem Spatial Analysis of Topological Instabilities
═══════════════════════════════════════════════════════════════════════════════

Identifies spatial clustering of energy drift hotspots in WQT simulations.

Usage:
    python -m wqt_oop.analyze_hotspots --input cosmology_L3_equilibrio.h5 --output drift_matrix.json

Outputs:
    1. drift_matrix.json - Structured data of hotspots and correlations
    2. hotspot_spatial_map.png - 3D scatter plot of instability locations
    3. torsion_drift_correlation.png - K vs velocity variance correlation
    4. energy_variance_map.png - Spatial heatmap of energy fluctuations

Physics Questions Addressed:
    - Are instabilities spatially clustered? (Soliton star hypothesis)
    - Does high K correlate with high drift? (Torsion-driven turbulence)
    - Is there a critical density threshold? (Phase transition signature)

Author: WQT Physics Team
Date: 2026-05-26
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import h5py
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.spatial import distance_matrix
from scipy.stats import pearsonr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HotspotAnalyzer:
    """Analyzes spatial distribution and correlations of topological instabilities."""

    def __init__(self, hdf5_path: Path):
        self.hdf5_path = hdf5_path
        self.frames_data = []
        self.hotspot_data = {}

    def load_frames(self) -> None:
        """Load all frames from HDF5 with SWMR compatibility."""
        logger.info(f"Loading frames from {self.hdf5_path}")
        
        with h5py.File(self.hdf5_path, 'r') as f:
            frames_group = f['frames']
            frame_names = sorted([k for k in frames_group.keys() if k.startswith('frame_')])
            
            logger.info(f"Found {len(frame_names)} frames")
            
            for frame_name in frame_names:
                frame = frames_group[frame_name]
                
                frame_data = {
                    'time': frame.attrs['time'],
                    'H_total': frame.attrs['H_total'],
                    'T_eff': frame.attrs['T_eff'],
                    'drift': frame.attrs['drift'],
                    'positions': frame['positions'][:],
                    'chi_values': frame['chi_values'][:],
                    'velocities': frame['velocities'][:],
                    'tau_locale': frame['tau_locale'][:],
                    'contorsione_locale': frame['contorsione_locale'][:],  # K
                }
                
                self.frames_data.append(frame_data)
                
        logger.info(f"Loaded {len(self.frames_data)} frames successfully")

    def compute_velocity_variance(self) -> np.ndarray:
        """
        Compute temporal variance of velocity magnitude for each segment.
        High variance = energy churning (instability marker).
        
        Returns:
            variance (N,): Velocity magnitude variance over time for each segment
        """
        N_segments = len(self.frames_data[0]['velocities'])
        N_frames = len(self.frames_data)
        
        # (N_frames, N_segments) array of velocities (already scalar dχ/dt)
        velocities = np.zeros((N_frames, N_segments))
        
        for i, frame in enumerate(self.frames_data):
            # Velocities are already scalar (dχ/dt), use absolute value
            velocities[i, :] = np.abs(frame['velocities'])
        
        # Variance over time for each segment
        variance = np.var(velocities, axis=0)
        
        logger.info(f"Velocity variance: min={variance.min():.3e}, max={variance.max():.3e}, mean={variance.mean():.3e}")
        
        return variance

    def identify_hotspots(self, velocity_variance: np.ndarray, threshold_percentile: float = 95.0) -> np.ndarray:
        """
        Identify hotspot segments with variance above threshold.
        
        Args:
            velocity_variance: Variance array from compute_velocity_variance()
            threshold_percentile: Percentile cutoff (default 95 = top 5%)
        
        Returns:
            hotspot_indices: Indices of hotspot segments
        """
        threshold = np.percentile(velocity_variance, threshold_percentile)
        hotspot_indices = np.where(velocity_variance >= threshold)[0]
        
        logger.info(f"Identified {len(hotspot_indices)} hotspots (>{threshold_percentile}th percentile)")
        logger.info(f"  Threshold: {threshold:.3e}")
        logger.info(f"  Hotspot fraction: {100.0 * len(hotspot_indices) / len(velocity_variance):.2f}%")
        
        return hotspot_indices

    def compute_spatial_clustering(self, positions: np.ndarray, hotspot_indices: np.ndarray) -> Dict:
        """
        Analyze spatial clustering of hotspots using nearest-neighbor distances.
        
        Args:
            positions: (N, 3) array of segment positions
            hotspot_indices: Indices of hotspot segments
        
        Returns:
            clustering_metrics: Dict with clustering statistics
        """
        if len(hotspot_indices) < 2:
            logger.warning("Too few hotspots for clustering analysis")
            return {}
        
        hotspot_positions = positions[hotspot_indices]
        
        # Compute pairwise distances
        dist_matrix = distance_matrix(hotspot_positions, hotspot_positions)
        
        # Nearest neighbor distances (exclude self)
        np.fill_diagonal(dist_matrix, np.inf)
        nn_distances = np.min(dist_matrix, axis=1)
        
        # Compare to random distribution
        random_indices = np.random.choice(len(positions), len(hotspot_indices), replace=False)
        random_positions = positions[random_indices]
        random_dist_matrix = distance_matrix(random_positions, random_positions)
        np.fill_diagonal(random_dist_matrix, np.inf)
        random_nn_distances = np.min(random_dist_matrix, axis=1)
        
        clustering_ratio = random_nn_distances.mean() / nn_distances.mean()
        
        metrics = {
            'hotspot_count': len(hotspot_indices),
            'mean_nn_distance': float(nn_distances.mean()),
            'std_nn_distance': float(nn_distances.std()),
            'random_mean_nn_distance': float(random_nn_distances.mean()),
            'clustering_ratio': float(clustering_ratio),  # > 1.0 = clustered
            'cluster_significance': 'STRONG' if clustering_ratio > 2.0 else 'MODERATE' if clustering_ratio > 1.5 else 'WEAK'
        }
        
        logger.info(f"Clustering analysis:")
        logger.info(f"  Hotspot NN distance: {metrics['mean_nn_distance']:.2f} ± {metrics['std_nn_distance']:.2f}")
        logger.info(f"  Random NN distance:  {metrics['random_mean_nn_distance']:.2f}")
        logger.info(f"  Clustering ratio:    {metrics['clustering_ratio']:.2f}x ({metrics['cluster_significance']})")
        
        return metrics

    def correlate_torsion_drift(self, velocity_variance: np.ndarray) -> Dict:
        """
        Compute correlation between torsion K and energy drift.
        
        Args:
            velocity_variance: Velocity variance proxy for drift
        
        Returns:
            correlation_metrics: Dict with Pearson r, p-value, etc.
        """
        # Use last frame for K (most evolved state)
        K_values = self.frames_data[-1]['contorsione_locale']
        
        # Pearson correlation
        r, p_value = pearsonr(K_values, velocity_variance)
        
        metrics = {
            'pearson_r': float(r),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.01),
            'interpretation': 'STRONG' if abs(r) > 0.7 else 'MODERATE' if abs(r) > 0.4 else 'WEAK'
        }
        
        logger.info(f"Torsion-Drift correlation:")
        logger.info(f"  Pearson r = {r:.3f} (p={p_value:.3e})")
        logger.info(f"  Strength:   {metrics['interpretation']}")
        
        return metrics

    def plot_spatial_map(self, velocity_variance: np.ndarray, hotspot_indices: np.ndarray, output_path: Path) -> None:
        """Generate 3D scatter plot of segment positions colored by variance."""
        positions = self.frames_data[-1]['positions']
        
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # All segments (gray, small)
        ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2], 
                   c='lightgray', s=1, alpha=0.3, label='Stable')
        
        # Hotspots (colored by variance magnitude)
        hotspot_positions = positions[hotspot_indices]
        hotspot_variance = velocity_variance[hotspot_indices]
        
        scatter = ax.scatter(hotspot_positions[:, 0], hotspot_positions[:, 1], hotspot_positions[:, 2],
                             c=hotspot_variance, s=50, cmap='hot', alpha=0.8, 
                             label=f'Hotspots (n={len(hotspot_indices)})')
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title('Spatial Distribution of Energy Hotspots (L3)', fontsize=14, fontweight='bold')
        ax.legend()
        
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.5, aspect=10)
        cbar.set_label('Velocity Variance', rotation=270, labelpad=20)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        logger.info(f"Saved spatial map to {output_path}")
        plt.close()

    def plot_torsion_correlation(self, velocity_variance: np.ndarray, output_path: Path) -> None:
        """Plot K vs velocity variance scatter with regression line."""
        K_values = self.frames_data[-1]['contorsione_locale']
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Scatter plot
        ax.scatter(K_values, velocity_variance, s=5, alpha=0.5, c='steelblue')
        
        # Regression line
        z = np.polyfit(K_values, velocity_variance, 1)
        p = np.poly1d(z)
        ax.plot(K_values, p(K_values), 'r--', linewidth=2, label=f'Fit: y={z[0]:.3e}x+{z[1]:.3e}')
        
        r, p_value = pearsonr(K_values, velocity_variance)
        
        ax.set_xlabel('Torsion K (contorsione_locale)', fontsize=12)
        ax.set_ylabel('Velocity Variance', fontsize=12)
        ax.set_title(f'Torsion-Drift Correlation (r={r:.3f}, p={p_value:.3e})', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        logger.info(f"Saved torsion correlation plot to {output_path}")
        plt.close()

    def plot_energy_heatmap(self, velocity_variance: np.ndarray, output_path: Path) -> None:
        """2D heatmap projection (XY plane) of energy variance."""
        positions = self.frames_data[-1]['positions']
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        scatter = ax.scatter(positions[:, 0], positions[:, 1], 
                            c=velocity_variance, s=20, cmap='plasma', alpha=0.7)
        
        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        ax.set_title('Energy Variance Map (XY Projection)', fontsize=14, fontweight='bold')
        ax.set_aspect('equal')
        
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label('Velocity Variance', rotation=270, labelpad=20)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        logger.info(f"Saved energy heatmap to {output_path}")
        plt.close()

    def generate_report(self, velocity_variance: np.ndarray, hotspot_indices: np.ndarray, 
                       clustering_metrics: Dict, correlation_metrics: Dict, output_path: Path) -> None:
        """Generate JSON report with all analysis results."""
        
        report = {
            'simulation': {
                'file': str(self.hdf5_path),
                'frames_analyzed': len(self.frames_data),
                'total_segments': len(velocity_variance),
                'final_time': float(self.frames_data[-1]['time']),
                'final_drift': float(self.frames_data[-1]['drift']),
                'final_T_eff': float(self.frames_data[-1]['T_eff']),
            },
            'hotspots': {
                'count': len(hotspot_indices),
                'fraction': float(len(hotspot_indices) / len(velocity_variance)),
                'indices': hotspot_indices.tolist(),
                'velocity_variance_threshold': float(np.percentile(velocity_variance, 95)),
            },
            'clustering': clustering_metrics,
            'torsion_correlation': correlation_metrics,
            'statistics': {
                'velocity_variance': {
                    'min': float(velocity_variance.min()),
                    'max': float(velocity_variance.max()),
                    'mean': float(velocity_variance.mean()),
                    'std': float(velocity_variance.std()),
                    'median': float(np.median(velocity_variance)),
                },
                'torsion_K': {
                    'min': float(self.frames_data[-1]['contorsione_locale'].min()),
                    'max': float(self.frames_data[-1]['contorsione_locale'].max()),
                    'mean': float(self.frames_data[-1]['contorsione_locale'].mean()),
                    'std': float(self.frames_data[-1]['contorsione_locale'].std()),
                },
            },
            'physics_interpretation': {
                'soliton_star_hypothesis': bool(clustering_metrics.get('cluster_significance') == 'STRONG'),
                'torsion_driven_turbulence': bool(correlation_metrics.get('interpretation') in ['STRONG', 'MODERATE']),
                'temperature_regulation_active': bool(abs(self.frames_data[-1]['T_eff'] - self.frames_data[0]['T_eff']) < 10.0),
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Saved analysis report to {output_path}")
        
        # Print executive summary
        logger.info("=" * 80)
        logger.info(" EXECUTIVE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"  Hotspots identified:  {len(hotspot_indices)} / {len(velocity_variance)} ({100*len(hotspot_indices)/len(velocity_variance):.1f}%)")
        logger.info(f"  Spatial clustering:   {clustering_metrics.get('cluster_significance', 'N/A')}")
        logger.info(f"  K-drift correlation:  {correlation_metrics.get('interpretation', 'N/A')} (r={correlation_metrics.get('pearson_r', 0):.3f})")
        logger.info(f"  T_eff regulation:     {'ACTIVE' if report['physics_interpretation']['temperature_regulation_active'] else 'INACTIVE'}")
        logger.info("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Analyze hotspots in WQT simulation')
    parser.add_argument('--input', type=Path, required=True, help='Input HDF5 file')
    parser.add_argument('--output', type=Path, default=Path('drift_matrix.json'), help='Output JSON file')
    parser.add_argument('--threshold', type=float, default=95.0, help='Hotspot percentile threshold (default: 95)')
    
    args = parser.parse_args()
    
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    # Initialize analyzer
    analyzer = HotspotAnalyzer(args.input)
    
    # Load data
    analyzer.load_frames()
    
    # Compute variance (proxy for energy drift)
    velocity_variance = analyzer.compute_velocity_variance()
    
    # Identify hotspots
    hotspot_indices = analyzer.identify_hotspots(velocity_variance, args.threshold)
    
    # Spatial clustering analysis
    positions = analyzer.frames_data[-1]['positions']
    clustering_metrics = analyzer.compute_spatial_clustering(positions, hotspot_indices)
    
    # Torsion-drift correlation
    correlation_metrics = analyzer.correlate_torsion_drift(velocity_variance)
    
    # Generate plots
    output_dir = args.output.parent
    analyzer.plot_spatial_map(velocity_variance, hotspot_indices, output_dir / 'hotspot_spatial_map.png')
    analyzer.plot_torsion_correlation(velocity_variance, output_dir / 'torsion_drift_correlation.png')
    analyzer.plot_energy_heatmap(velocity_variance, output_dir / 'energy_variance_map.png')
    
    # Generate JSON report
    analyzer.generate_report(velocity_variance, hotspot_indices, clustering_metrics, correlation_metrics, args.output)
    
    logger.info("Analysis complete! 🌌")
    
    return 0


if __name__ == '__main__':
    exit(main())
