"""
Analizza i risultati della simulazione con porosità topologica.
Verifica se Var(χ) > 0 (separazione di fasi).
"""
import h5py
import numpy as np
import sys

if len(sys.argv) < 2:
    print("Uso: python analisi_porosita.py <file.h5>")
    sys.exit(1)

filename = sys.argv[1]

with h5py.File(filename, 'r') as f:
    tel = f['telemetria_scalare'][:]
    
    # Filtra frame validi
    valid = tel['rm'] > 0
    tel_valid = tel[valid]
    
    print(f"\n{'='*80}")
    print(f"ANALISI POROSITÀ TOPOLOGICA: {filename}")
    print(f"{'='*80}\n")
    
    print(f"Frame totali: {len(tel)}")
    print(f"Frame validi: {len(tel_valid)}")
    
    if len(tel_valid) == 0:
        print("❌ ERRORE: Nessun frame valido!")
        sys.exit(1)
    
    # Campiona 10 frame equidistanti
    n_samples = min(10, len(tel_valid))
    indices = np.linspace(0, len(tel_valid)-1, n_samples, dtype=int)
    
    print(f"\n{'Frame':<10} {'Var(χ)':<12} {'Max|flux|':<12} {'E_coup':<12} {'STATO':<20}")
    print('-' * 80)
    
    for idx in indices:
        frame = tel_valid[idx]
        chi_vec = frame['chi_vettore']
        vel_vec = frame['vel_vettore']
        
        # Calcola varianza χ
        var_chi = np.var(chi_vec)
        
        # Calcola max flusso (proxy: velocità)
        max_flux = np.max(np.abs(vel_vec))
        
        # Energia di accoppiamento (approssimata da varianza contorsione)
        contorsione = frame['contorsione_locale']
        e_coup_proxy = np.var(contorsione) * 0.01  # Scala approssimativa
        
        # Determina stato
        if var_chi > 0.1:
            stato = "✅ SEPARAZIONE!"
        elif var_chi > 0.01:
            stato = "⚠️ Nucleazione..."
        else:
            stato = "❌ Omogeneo"
        
        print(f"{frame['frame_id']:<10} {var_chi:<12.2e} {max_flux:<12.2f} {e_coup_proxy:<12.2f} {stato:<20}")
    
    # Statistiche finali
    print("\n" + "="*80)
    final_frame = tel_valid[-1]
    final_chi = final_frame['chi_vettore']
    final_var = np.var(final_chi)
    
    print(f"\n📊 STATO FINALE (frame {final_frame['frame_id']}):")
    print(f"   Var(χ)     = {final_var:.6e}")
    print(f"   χ_min      = {np.min(final_chi):.4f}")
    print(f"   χ_max      = {np.max(final_chi):.4f}")
    print(f"   Range      = {np.ptp(final_chi):.4f}")
    print(f"   χ_medio    = {np.mean(final_chi):.4f}")
    
    if final_var > 0.1:
        print(f"\n🎉 SUCCESSO! Il lock-in topologico è stato rotto!")
        print(f"   La porosità dinamica ha permesso la separazione di fasi.")
    elif final_var > 0.01:
        print(f"\n⚠️ Nucleazione in corso... Var(χ) sta crescendo.")
    else:
        print(f"\n❌ Sistema ancora omogeneo. Potrebbe servire:")
        print(f"   - Sigma più piccolo (attualmente 3.0)")
        print(f"   - Bias più forte")
        print(f"   - Tempo di simulazione più lungo")
    
    print("\n" + "="*80 + "\n")
