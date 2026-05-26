"""
Visualizzazione evoluzione 24 campi chirali nel tempo
Mostra chiaramente la separazione di fasi Materia-Spazio
"""
import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import sys

def visualizza_evoluzione(db_path, speed=1, max_frames=None):
    """
    Crea animazione evoluzione χ_i(t) per i 24 campi
    """
    # Leggi dati
    with h5py.File(db_path, 'r') as f:
        tel = f['telemetria_scalare'][:]
        valid = tel['rm'] > 0
        tel_valid = tel[valid]
        
        if max_frames:
            tel_valid = tel_valid[:max_frames]
        
        n_frames = len(tel_valid)
        print(f"Frames totali: {n_frames}")
        
        # Estrai tutti i χ_vettore
        chi_matrix = np.array([frame['chi_vettore'] for frame in tel_valid])  # Shape: (n_frames, 24)
        tempi = np.array([frame['frame_id'] / 24.0 for frame in tel_valid])
    
    # Setup figura
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Evoluzione Separazione Fasi - 24 Campi Chirali (Reticolo di Leech)', 
                 fontsize=14, fontweight='bold')
    
    # Layout: 2 righe, 2 colonne
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # 1. Plot principale: χ_i vs tempo (linee colorate)
    ax1 = fig.add_subplot(gs[0, :])  # Tutta la prima riga
    
    # Colori alternati SX/DX
    colors_sx = plt.cm.Reds(np.linspace(0.4, 0.9, 12))
    colors_dx = plt.cm.Blues(np.linspace(0.4, 0.9, 12))
    
    lines = []
    for i in range(24):
        if i % 2 == 0:  # Segmenti SPAZIO (inizializzati a -4.5)
            color = colors_sx[i//2]
            label = f'χ_{i} (SX)' if i < 2 else None
        else:  # Segmenti MATERIA (inizializzati a +4.5)
            color = colors_dx[i//2]
            label = f'χ_{i} (DX)' if i < 2 else None
        
        line, = ax1.plot([], [], color=color, linewidth=1.5, alpha=0.8, label=label)
        lines.append(line)
    
    ax1.set_xlabel('Tempo (s)', fontsize=12)
    ax1.set_ylabel('χ (potenziale di scala)', fontsize=12)
    ax1.set_title('Evoluzione Temporale dei 24 Campi Locali', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.set_xlim(0, tempi[-1])
    ax1.set_ylim(chi_matrix.min() * 1.1, chi_matrix.max() * 1.1)
    
    # Linea verticale tempo corrente
    vline = ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    # 2. Istogramma distribuzione χ (snapshot corrente)
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.set_xlabel('χ', fontsize=10)
    ax2.set_ylabel('Frequenza', fontsize=10)
    ax2.set_title('Distribuzione χ (frame corrente)', fontsize=11, fontweight='bold')
    hist_bars = ax2.bar([], [], width=0, alpha=0.7, color='purple')
    ax2.set_xlim(chi_matrix.min() * 1.1, chi_matrix.max() * 1.1)
    ax2.set_ylim(0, 5)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. Metriche evoluzione
    ax3 = fig.add_subplot(gs[1, 1])
    
    # Calcola metriche pre-computate
    var_chi = np.var(chi_matrix, axis=1)
    range_chi = np.ptp(chi_matrix, axis=1)
    
    line_var, = ax3.plot([], [], 'b-', linewidth=2, label='Var(χ)')
    line_range, = ax3.plot([], [], 'r-', linewidth=2, label='Range(χ)')
    
    ax3.set_xlabel('Tempo (s)', fontsize=10)
    ax3.set_ylabel('Valore', fontsize=10)
    ax3.set_title('Metriche Separazione Fasi', fontsize=11, fontweight='bold')
    ax3.set_xlim(0, tempi[-1])
    ax3.set_ylim(0, max(var_chi.max(), range_chi.max()) * 1.1)
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    vline_metrics = ax3.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    # Testo informativo
    info_text = ax3.text(0.02, 0.98, '', transform=ax3.transAxes, 
                         verticalalignment='top', fontsize=9,
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Funzione di aggiornamento
    def update(frame_idx):
        # Aggiorna linee temporali (mostra tutto fino a frame_idx)
        for i, line in enumerate(lines):
            line.set_data(tempi[:frame_idx], chi_matrix[:frame_idx, i])
        
        # Aggiorna linea verticale
        current_time = tempi[frame_idx]
        vline.set_xdata([current_time, current_time])
        vline_metrics.set_xdata([current_time, current_time])
        
        # Aggiorna istogramma (solo frame corrente)
        ax2.clear()
        ax2.hist(chi_matrix[frame_idx], bins=15, alpha=0.7, color='purple', edgecolor='black')
        ax2.set_xlabel('χ', fontsize=10)
        ax2.set_ylabel('Frequenza', fontsize=10)
        ax2.set_title(f'Distribuzione χ (t={current_time:.1f}s)', fontsize=11, fontweight='bold')
        ax2.set_xlim(chi_matrix.min() * 1.1, chi_matrix.max() * 1.1)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Metriche SX vs DX
        chi_sx = chi_matrix[frame_idx, ::2]  # Indici pari
        chi_dx = chi_matrix[frame_idx, 1::2]  # Indici dispari
        mean_sx = np.mean(chi_sx)
        mean_dx = np.mean(chi_dx)
        
        # Aggiungi linee verticali per media SX/DX
        ax2.axvline(mean_sx, color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'μ_SX={mean_sx:.1f}')
        ax2.axvline(mean_dx, color='blue', linestyle='--', linewidth=2, alpha=0.7, label=f'μ_DX={mean_dx:.1f}')
        ax2.legend(fontsize=8)
        
        # Aggiorna metriche
        line_var.set_data(tempi[:frame_idx], var_chi[:frame_idx])
        line_range.set_data(tempi[:frame_idx], range_chi[:frame_idx])
        
        # Aggiorna testo info
        n_clusters = 1 + np.sum(np.diff(np.sort(chi_matrix[frame_idx])) > 9.0)
        info_text.set_text(
            f'Frame: {frame_idx}/{n_frames}\n'
            f'Tempo: {current_time:.1f}s\n'
            f'Var(χ): {var_chi[frame_idx]:.2e}\n'
            f'Range: {range_chi[frame_idx]:.1f}\n'
            f'Clusters: {n_clusters}\n'
            f'Δμ(SX-DX): {abs(mean_sx - mean_dx):.1f}'
        )
        
        return lines + [vline, vline_metrics, info_text]
    
    # Crea animazione
    interval = 1000 / (24 * speed)  # ms per frame
    ani = FuncAnimation(fig, update, frames=range(0, n_frames, speed), 
                       interval=interval, blit=False, repeat=True)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python visualizza_evoluzione_24campi.py <database.h5> [speed] [max_frames]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    speed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    max_frames = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    print(f"Database: {db_path}")
    print(f"Velocità: {speed}x")
    if max_frames:
        print(f"Max frames: {max_frames}")
    
    visualizza_evoluzione(db_path, speed, max_frames)
