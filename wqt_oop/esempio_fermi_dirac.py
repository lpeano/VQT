"""
ESEMPIO PRATICO: Uso del Sistema Fermi-Dirac
================================================

Questo esempio mostra come utilizzare il nuovo screening
Fermi-Dirac per simulare un sistema di solitoni con
separazione di fase dinamica.
"""

import numpy as np
import matplotlib.pyplot as plt
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


def esempio_separazione_fasi():
    """
    Simula separazione di fase: sistema parte misto,
    cooling induce clustering destrorsi/sinistrorsi.
    """
    print("="*70)
    print("ESEMPIO: Separazione di Fase con Cooling Fermi-Dirac")
    print("="*70 + "\n")
    
    # Setup fisica
    ctx_0 = PhysicsContext.for_level(0)
    ctx_1_base = PhysicsContext.for_level(1)
    
    # Context con cooling attivo
    ctx_1 = PhysicsContext(
        level=1,
        length_scale=ctx_1_base.length_scale,
        alpha_K=0.1,
        beta_potential=0.001,
        kappa_coupling=0.1,
        mu_fermi=50.0,       # Soglia separazione
        T_fermi=10.0,        # T iniziale alta
        gamma_cooling=0.05   # Cooling moderato
    )
    
    # Crea 24 segmenti: distribuzione MISTA iniziale
    np.random.seed(42)
    segments = []
    
    for i in range(24):
        # 50% destrorsi, 50% sinistrorsi (random)
        if np.random.rand() < 0.5:
            chi = np.random.uniform(55, 70)  # Destrorso
        else:
            chi = np.random.uniform(30, 45)  # Sinistrorso
        
        vel = np.random.uniform(-1, 1)
        pos = np.random.uniform(-10, 10, 3)
        segments.append(SegmentoQuantistico(chi, vel, ctx_0, position=pos))
    
    soliton = SolitoneComposito(segments, ctx_1, screening_enabled=True)
    
    # Evoluzione con monitoraggio
    dt = 0.1
    N_steps = 500
    
    # Storage
    history = {
        't': [],
        'T_eff': [],
        'polarizzazione': [],
        'N_destro': [],
        'N_sinistro': [],
        'entropia': []
    }
    
    print("Evoluzione sistema con cooling:")
    print("-"*70)
    print("  t[s]   T_eff    N_destro  N_sinistro  Polariz   Entropia")
    print("-"*70)
    
    for step in range(N_steps):
        t = step * dt
        
        # Misura stato
        stats = soliton.get_occupazione_stati()
        
        history['t'].append(t)
        history['T_eff'].append(stats['T_eff'])
        history['polarizzazione'].append(stats['polarizzazione'])
        history['N_destro'].append(stats['N_destro'])
        history['N_sinistro'].append(stats['N_sinistro'])
        history['entropia'].append(stats['entropia_mixing'])
        
        if step % 50 == 0:
            print(f" {t:5.1f}  {stats['T_eff']:.2e}     {stats['N_destro']:2d}"
                  f"         {stats['N_sinistro']:2d}        {stats['polarizzazione']:+.3f}"
                  f"     {stats['entropia_mixing']:.2f}")
        
        # Evolvi
        soliton.evolve(dt)
    
    print("-"*70)
    print(f"\nStato finale (t={N_steps*dt:.1f}s):")
    stats_final = soliton.get_occupazione_stati()
    print(f"  T_eff finale: {stats_final['T_eff']:.3e}")
    print(f"  Destrorsi: {stats_final['N_destro']}")
    print(f"  Sinistrorsi: {stats_final['N_sinistro']}")
    print(f"  Polarizzazione: {stats_final['polarizzazione']:+.3f}")
    
    # Plot evoluzione
    fig, axes = plt.subplots(3, 1, figsize=(10, 10))
    
    # Temperatura
    axes[0].plot(history['t'], history['T_eff'], 'purple', linewidth=2)
    axes[0].set_ylabel('T_eff')
    axes[0].set_title('Cooling Dynamics')
    axes[0].set_yscale('log')
    axes[0].grid(True, alpha=0.3)
    
    # Popolazione
    axes[1].plot(history['t'], history['N_destro'], 'r-', label='Destrorsi')
    axes[1].plot(history['t'], history['N_sinistro'], 'b-', label='Sinistrorsi')
    axes[1].set_ylabel('Numero Stati')
    axes[1].set_title('Separazione di Fase')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # Polarizzazione & Entropia
    ax2 = axes[2]
    ax2.plot(history['t'], history['polarizzazione'], 'k-', linewidth=2, label='Polarizzazione')
    ax2.axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Tempo [s]')
    ax2.set_ylabel('Polarizzazione')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    ax2b = ax2.twinx()
    ax2b.plot(history['t'], history['entropia'], 'orange', linewidth=2, label='Entropia')
    ax2b.set_ylabel('Entropia', color='orange')
    ax2b.tick_params(axis='y', labelcolor='orange')
    ax2b.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig('esempio_separazione_fasi_fermi.png', dpi=150)
    print(f"\n[OK] Plot salvato: esempio_separazione_fasi_fermi.png")
    print("="*70 + "\n")


def esempio_controllo_temperatura():
    """
    Mostra come la temperatura T_eff controlla la
    "sharpness" della transizione.
    """
    print("="*70)
    print("ESEMPIO: Controllo Temperatura Transizione")
    print("="*70 + "\n")
    
    from wqt_oop.fermi_dirac_screening import FermiDiracScreening
    
    rho = np.linspace(0, 100, 500)
    
    # Tre temperature diverse
    T_values = [1.0, 5.0, 15.0]
    
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    
    for T in T_values:
        screener = FermiDiracScreening(mu=50.0, T_eff=T)
        
        A = screener.screening_factor(rho)
        dA_drho = np.gradient(A, rho[1]-rho[0])
        
        # Plot screening factor
        axes[0].plot(rho, A, linewidth=2, label=f'T={T:.1f}')
        
        # Plot derivata
        axes[1].plot(rho, dA_drho, linewidth=2, label=f'T={T:.1f}')
    
    axes[0].axvline(50, color='k', linestyle=':', label='mu=50')
    axes[0].set_ylabel('A(rho) - Screening Factor')
    axes[0].set_title('Effetto Temperatura su Screening')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].axvline(50, color='k', linestyle=':')
    axes[1].set_xlabel('Densita locale rho')
    axes[1].set_ylabel('dA/drho - Forza')
    axes[1].set_title('Gradiente (Forza)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('esempio_temperatura_screening.png', dpi=150)
    print("[OK] Plot salvato: esempio_temperatura_screening.png")
    print("\nOsservazione:")
    print("  - T bassa (1.0): Transizione SHARP (quasi discontinua)")
    print("  - T media (5.0): Transizione SMOOTH (bilanciata)")
    print("  - T alta (15.0): Transizione SOFT (graduale)")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print(" ESEMPI PRATICI: Sistema Fermi-Dirac")
    print("="*70 + "\n")
    
    # Esempio 1: Separazione fasi
    esempio_separazione_fasi()
    
    # Esempio 2: Controllo temperatura
    esempio_controllo_temperatura()
    
    print("="*70)
    print("ESEMPI COMPLETATI")
    print("Plot generati:")
    print("  - esempio_separazione_fasi_fermi.png")
    print("  - esempio_temperatura_screening.png")
    print("="*70 + "\n")
