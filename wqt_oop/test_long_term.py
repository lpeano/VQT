"""Test stabilità a lungo termine del bilancio termodinamico."""

import sys
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

import numpy as np
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito

def test_long_term_conservation():
    """Test conservazione H_conserved su 1000 steps."""
    
    # Parametri
    dt = 0.1
    N_steps = 1000
    N_samples = 20  # Log ogni 50 steps
    
    # Physics contexts
    ctx_0 = PhysicsContext.for_level(0)
    ctx_1 = PhysicsContext.for_level(1)
    
    # Crea 24 segmenti casuali
    np.random.seed(12345)
    segments = []
    for i in range(24):
        chi_init = np.random.uniform(3.0, 6.0)
        v_init = np.random.uniform(-10.0, 10.0)
        seg = SegmentoQuantistico(chi_init, v_init, ctx_0)
        segments.append(seg)
    
    # Crea composito CON screening
    soliton = SolitoneComposito(segments, ctx_1, screening_enabled=True)
    
    print("=" * 70)
    print(" TEST STABILITA' LONG-TERM (1000 steps, dt=0.1)")
    print("=" * 70)
    print(f"N_segments      = {len(segments)}")
    print(f"Screening       = ENABLED")
    print(f"eta_radiation   = {ctx_1.eta_radiation_base}")
    print(f"tau_coherence   = {ctx_1.tau_coherence}")
    print()
    
    # Bilancio iniziale
    budget_init = soliton.get_energy_budget()
    H_cons_init = budget_init['H_conserved']
    
    print("Bilancio iniziale:")
    print(f"  H_total      = {budget_init['H_total']:.6e}")
    print(f"  H_conserved  = {H_cons_init:.6e}")
    print()
    
    # Log dati
    log_interval = N_steps // N_samples
    H_cons_history = [H_cons_init]
    H_tot_history = [budget_init['H_total']]
    E_rad_history = [0.0]
    steps_logged = [0]
    
    print(f"Evoluzione ({N_steps} steps, dt={dt}):")
    print(f"{'Step':>6}  {'H_total':>12}  {'E_radiated':>12}  {'H_conserved':>12}  {'Drift %':>10}")
    print("-" * 70)
    
    # Evoluzione
    for step in range(1, N_steps + 1):
        soliton.evolve(dt)
        
        if step % log_interval == 0 or step == N_steps:
            budget = soliton.get_energy_budget()
            H_cons = budget['H_conserved']
            drift = abs((H_cons - H_cons_init) / H_cons_init) * 100
            
            print(f"{step:6d}  {budget['H_total']:12.4e}  {budget['E_radiated']:12.4e}  "
                  f"{H_cons:12.4e}  {drift:10.6f}")
            
            H_cons_history.append(H_cons)
            H_tot_history.append(budget['H_total'])
            E_rad_history.append(budget['E_radiated'])
            steps_logged.append(step)
    
    # Analisi finale
    budget_final = soliton.get_energy_budget()
    H_cons_final = budget_final['H_conserved']
    
    drift_final = abs((H_cons_final - H_cons_init) / H_cons_init) * 100
    drift_max = max(abs((h - H_cons_init) / H_cons_init) * 100 for h in H_cons_history)
    
    print()
    print("=" * 70)
    print(" RISULTATI")
    print("=" * 70)
    print(f"H_conserved_init  = {H_cons_init:.6e}")
    print(f"H_conserved_final = {H_cons_final:.6e}")
    print(f"Drift finale      = {drift_final:.4f}%")
    print(f"Drift massimo     = {drift_max:.4f}%")
    print()
    
    # Frazione energia radiata
    frac_rad = budget_final['E_radiated'] / budget_init['H_total'] * 100
    print(f"Frazione radiata  = {frac_rad:.2f}%")
    print()
    
    # Verifica
    if drift_max < 1.0:
        print(" SUCCESSO: Conservazione termodinamica verificata!")
        print(f" H_conserved stabile entro {drift_max:.4f}% su {N_steps} steps")
    else:
        print(f" ERRORE: Drift {drift_max:.4f}% > 1%")
    
    print("=" * 70)

if __name__ == "__main__":
    test_long_term_conservation()
