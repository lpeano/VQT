"""Verifica conservazione carica topologica nel tempo"""
import h5py
import numpy as np
import sys

with h5py.File(sys.argv[1], 'r') as f:
    tel = f['telemetria_scalare'][:]
    
    valid = tel['rm'] > 0
    tel_valid = tel[valid]
    
    print("CONSERVAZIONE CARICA TOPOLOGICA Σχᵢ")
    print("=" * 60)
    
    # Sample frames
    frames_to_check = [0, len(tel_valid)//4, len(tel_valid)//2, 3*len(tel_valid)//4, len(tel_valid)-1]
    
    for idx in frames_to_check:
        frame = tel_valid[idx]
        chi_vec = frame['chi_vettore']
        
        somma_chi = np.sum(chi_vec)
        var_chi = np.var(chi_vec)
        range_chi = np.ptp(chi_vec)
        
        print(f"\nFrame {frame['frame_id']:3d} (λ={frame['lambda_proper']:.2f}):")
        print(f"  Σχᵢ      = {somma_chi:+10.4f}  ← Deve restare costante!")
        print(f"  Var(χ)   = {var_chi:10.2e}  ← Cresce se si separano")
        print(f"  Range(χ) = {range_chi:10.4f}  ← Distanza max tra bolle")
        
        # Analisi pattern
        n_positivi = np.sum(chi_vec > 0)
        n_negativi = np.sum(chi_vec < 0)
        print(f"  Pattern: {n_positivi} campi DX (+), {n_negativi} campi SX (-)")
    
    # Verifica drift
    print("\n" + "=" * 60)
    somma_iniziale = np.sum(tel_valid[0]['chi_vettore'])
    somma_finale = np.sum(tel_valid[-1]['chi_vettore'])
    drift = abs(somma_finale - somma_iniziale)
    
    print(f"Σχᵢ(t=0)     = {somma_iniziale:+.6f}")
    print(f"Σχᵢ(t=final) = {somma_finale:+.6f}")
    print(f"Drift assoluto = {drift:.6e}")
    
    if drift < 1e-6:
        print("✅ CONSERVAZIONE PERFETTA (drift < 1e-6)")
    elif drift < 1e-3:
        print("✅ CONSERVAZIONE ECCELLENTE (drift < 1e-3)")
    elif drift < 0.1:
        print("⚠️  Conservazione buona (drift < 0.1)")
    else:
        print("❌ DRIFT ECCESSIVO! Possibile bug numerico!")
