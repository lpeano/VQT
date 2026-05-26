"""Analisi evoluzione temporale della separazione di fasi"""
import h5py
import numpy as np
import sys

def analizza_evoluzione(db_path, n_campioni=10):
    """
    Campiona uniformemente n_campioni frames dal database
    e mostra l'evoluzione di Var(χ), Range, clustering
    """
    with h5py.File(db_path, 'r') as f:
        tel = f['telemetria_scalare'][:]
        
        # Filtra frame validi
        valid = tel['rm'] > 0
        tel_valid = tel[valid]
        
        n_frames = len(tel_valid)
        print(f"\n{'='*80}")
        print(f"DATABASE: {db_path}")
        print(f"Frames totali: {n_frames}")
        print(f"{'='*80}\n")
        
        # Indici campionati uniformemente
        indices = np.linspace(0, n_frames-1, n_campioni, dtype=int)
        
        print(f"{'Frame':<8} {'Tempo':<8} {'Var(χ)':<12} {'Range':<10} {'χ_min':<10} {'χ_max':<10} {'N_clusters':<12}")
        print("-" * 80)
        
        var_list = []
        time_list = []
        
        for idx in indices:
            frame = tel_valid[idx]
            chi_vec = frame['chi_vettore']
            
            # Metriche
            var_chi = np.var(chi_vec)
            range_chi = np.ptp(chi_vec)
            chi_min = np.min(chi_vec)
            chi_max = np.max(chi_vec)
            
            # Clustering: numero di salti > 3σ_base
            chi_sorted = np.sort(chi_vec)
            salti = np.diff(chi_sorted)
            n_clusters = 1 + np.sum(salti > 9.0)  # 3 * SIGMA_BASE = 9
            
            # Tempo stimato (frame / 24 fps)
            tempo = frame['frame_id'] / 24.0
            
            var_list.append(var_chi)
            time_list.append(tempo)
            
            # Stato clustering
            if var_chi > 1000:
                stato = "✅ SEPARATO"
            elif var_chi > 10:
                stato = "⚠️ Nucleazione"
            else:
                stato = "❌ Omogeneo"
            
            print(f"{frame['frame_id']:<8} {tempo:<8.1f} {var_chi:<12.2e} {range_chi:<10.2f} "
                  f"{chi_min:<10.2f} {chi_max:<10.2f} {n_clusters:<12} {stato}")
        
        print("\n" + "="*80)
        print("ANALISI TENDENZE")
        print("="*80)
        
        # Fit lineare/esponenziale
        if len(var_list) > 2:
            # Crescita media Var(χ) per secondo
            delta_var = var_list[-1] - var_list[0]
            delta_time = time_list[-1] - time_list[0]
            crescita_media = delta_var / delta_time if delta_time > 0 else 0
            
            print(f"\nCrescita Var(χ): {var_list[0]:.2e} → {var_list[-1]:.2e}")
            print(f"Fattore moltiplicativo: {var_list[-1]/var_list[0]:.2f}×")
            print(f"Tasso di crescita medio: {crescita_media:.2e} per secondo")
            
            # Estrapolazione a 100s
            if delta_time < 100:
                var_estrapolata = var_list[0] + crescita_media * 100
                print(f"\n🔮 ESTRAPOLAZIONE A 100s:")
                print(f"   Var(χ) stimata ≈ {var_estrapolata:.2e}")
                print(f"   (assumendo crescita lineare)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analisi_evoluzione_temporale.py <database.h5> [n_campioni]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    n_campioni = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    
    analizza_evoluzione(db_path, n_campioni)
