"""
================================================================================
SIMULAZIONE DI PRODUZIONE - Motore OOP Conservativo
================================================================================

Obiettivi:
1. Verificare separazione di fase persistente (Var(χ) > 0)
2. Osservare clustering auto-corretto (Materia vs Spazio)
3. Monitorare radiazione di torsione durante fusioni
4. Validare conservazione H su tempi lunghi

Output:
- HDF5 database compatibile con renderer legacy
- Log dettagliato diagnostica fisica
================================================================================
"""

import numpy as np
import h5py
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito

# ============================================================
# CONFIGURAZIONE
# ============================================================

# Parametri simulazione
N_SEGMENTI = 24  # Reticolo Leech
N_STEPS = 1000   # Equivalente a 100s (dt=0.1)
DT = 0.1
SAVE_EVERY = 10  # Salva ogni 10 step (1s)

# Output
OUTPUT_DIR = Path("output_produzione")
OUTPUT_DIR.mkdir(exist_ok=True)
DB_FILE = OUTPUT_DIR / f"produzione_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
LOG_FILE = OUTPUT_DIR / "simulazione.log"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# INIZIALIZZAZIONE SISTEMA
# ============================================================

def initialize_system() -> SolitoneComposito:
    """
    Crea SolitoneComposito(24) con distribuzione bimodale.
    
    Configurazione:
    - 12 segmenti → Materia (χ ≈ +4.5)
    - 12 segmenti → Spazio (χ ≈ -4.5)
    - Velocità casuali
    - Screening dinamico ABILITATO
    
    Returns:
        SolitoneComposito inizializzato
    """
    logger.info("="*70)
    logger.info("INIZIALIZZAZIONE SISTEMA")
    logger.info("="*70)
    
    physics_level0 = PhysicsContext.for_level(0)
    physics_level1 = PhysicsContext.for_level(1)
    
    logger.info(f"Livello 0: L={physics_level0.length_scale:.3e}m, α_K={physics_level0.alpha_K:.3e}")
    logger.info(f"Livello 1: L={physics_level1.length_scale:.3e}m, α_K={physics_level1.alpha_K:.3e}")
    
    # Crea 24 segmenti bimodali
    segments = []
    np.random.seed(42)  # Riproducibilità
    
    for i in range(N_SEGMENTI):
        # Distribuzione bimodale: Materia (+) vs Spazio (-)
        if i < N_SEGMENTI // 2:
            chi = 4.5 + np.random.normal(0, 0.3)  # Materia
        else:
            chi = -4.5 + np.random.normal(0, 0.3)  # Spazio
        
        vel = np.random.uniform(-2.0, 2.0)
        
        # Posizione su circonferenza (topologia compatta)
        theta = 2 * np.pi * i / N_SEGMENTI
        position = np.array([np.cos(theta), np.sin(theta), 0.0])
        
        seg = SegmentoQuantistico(
            chi=chi,
            vel=vel,
            physics=physics_level0,
            position=position
        )
        segments.append(seg)
    
    # Crea composito con screening
    solitone = SolitoneComposito(
        children=segments,
        physics=physics_level1,
        screening_enabled=True  # CRITICO: Screening dinamico
    )
    
    # Diagnostica iniziale
    diag = solitone.get_diagnostics()
    chi_values = np.array([seg.chi for seg in segments])
    
    logger.info(f"\nStato iniziale:")
    logger.info(f"  N_segmenti:    {N_SEGMENTI}")
    logger.info(f"  Screening:     ENABLED")
    logger.info(f"  H_total:       {diag['energia']:.6e} J")
    logger.info(f"  Q_total:       {diag['carica_topologica']:.6f}")
    logger.info(f"  χ_mean:        {np.mean(chi_values):.6f}")
    logger.info(f"  χ_std (Var^½): {np.std(chi_values):.6f}")
    logger.info(f"  τ_std:         {diag['tau_std']:.6f}")
    logger.info("="*70)
    
    return solitone


# ============================================================
# EVOLUZIONE E DIAGNOSTICA
# ============================================================

class DiagnosticTracker:
    """Traccia metriche fisiche durante simulazione."""
    
    def __init__(self):
        self.time = []
        self.H_total = []
        self.Q_total = []
        self.chi_mean = []
        self.chi_std = []
        self.tau_std = []
        self.E_torsion = []
        self.E_coupling = []
        
    def record(self, step: int, solitone: SolitoneComposito):
        """Registra snapshot diagnostico."""
        diag = solitone.get_diagnostics()
        chi_values = np.array([seg.chi for seg in solitone.children])
        
        self.time.append(step * DT)
        self.H_total.append(diag['energia'])
        self.Q_total.append(diag['carica_topologica'])
        self.chi_mean.append(np.mean(chi_values))
        self.chi_std.append(np.std(chi_values))
        self.tau_std.append(diag['tau_std'])
        
        # Calcola componenti energetiche
        H_internal = solitone.compute_hamiltonian_internal()
        H_coupling = solitone.compute_hamiltonian_coupling()
        
        # Estima E_torsion (dalla differenza con coupling puro)
        # H_coupling include sia accoppiamento che torsione
        self.E_coupling.append(H_coupling)
        
    def log_summary(self, step: int):
        """Stampa summary periodico."""
        if len(self.time) == 0:
            return
        
        idx = -1
        logger.info(
            f"Step {step:4d}: t={self.time[idx]:6.1f}s | "
            f"H={self.H_total[idx]:.3e} | "
            f"Var(χ)^½={self.chi_std[idx]:.4f} | "
            f"σ(τ)={self.tau_std[idx]:.4f}"
        )
        
        # Alert se separazione collassa
        if self.chi_std[idx] < 0.5:
            logger.warning(f"  ⚠️  SEPARAZIONE DEBOLE: Var(χ)^½ = {self.chi_std[idx]:.4f} < 0.5")
        
        # Alert se drift energia
        if len(self.H_total) > 1:
            H_drift = abs(self.H_total[idx] - self.H_total[0]) / abs(self.H_total[0])
            if H_drift > 1e-2:
                logger.warning(f"  ⚠️  DRIFT ENERGIA: |ΔH/H| = {H_drift:.3e} > 1%")


def save_to_hdf5(db_file: Path, solitone: SolitoneComposito, tracker: DiagnosticTracker):
    """
    Salva risultati in formato HDF5.
    
    Struttura compatibile con renderer legacy WQT_manifold.py:
    - /frames/NNNN/chi
    - /frames/NNNN/vel
    - /frames/NNNN/tau_locale
    - /diagnostics/time, H_total, chi_std, etc.
    """
    logger.info(f"\n💾 Salvando database: {db_file}")
    
    with h5py.File(db_file, 'w') as f:
        # Metadati
        f.attrs['N_segmenti'] = N_SEGMENTI
        f.attrs['N_steps'] = N_STEPS
        f.attrs['dt'] = DT
        f.attrs['timestamp'] = datetime.now().isoformat()
        f.attrs['screening_enabled'] = True
        
        # Diagnostica globale
        diag_group = f.create_group('diagnostics')
        diag_group.create_dataset('time', data=tracker.time)
        diag_group.create_dataset('H_total', data=tracker.H_total)
        diag_group.create_dataset('Q_total', data=tracker.Q_total)
        diag_group.create_dataset('chi_mean', data=tracker.chi_mean)
        diag_group.create_dataset('chi_std', data=tracker.chi_std)
        diag_group.create_dataset('tau_std', data=tracker.tau_std)
        diag_group.create_dataset('E_coupling', data=tracker.E_coupling)
        
        # Stato finale (per ripresa)
        final_group = f.create_group('final_state')
        state_vector = solitone.get_state_vector()
        final_group.create_dataset('state', data=state_vector)
        
        # Frame singoli (salvati ogni SAVE_EVERY steps)
        frames_group = f.create_group('frames')
        for i, seg in enumerate(solitone.children):
            frame = frames_group.create_group(f"seg_{i:02d}")
            frame.create_dataset('chi', data=seg.chi)
            frame.create_dataset('vel', data=seg.vel)
            frame.create_dataset('tau_locale', data=seg.tau_locale)
            frame.create_dataset('position', data=seg.position)
    
    logger.info(f"✅ Database salvato: {db_file.stat().st_size / 1024:.1f} KB")


# ============================================================
# MAIN SIMULATION LOOP
# ============================================================

def run_simulation():
    """Loop principale simulazione."""
    
    logger.info("\n" + "🌌 "*35)
    logger.info("SIMULAZIONE DI PRODUZIONE - Motore OOP Conservativo")
    logger.info("🌌 "*35 + "\n")
    
    # Inizializza sistema
    solitone = initialize_system()
    tracker = DiagnosticTracker()
    
    # Record stato iniziale
    tracker.record(0, solitone)
    
    # Evoluzione
    logger.info(f"\n{'='*70}")
    logger.info("EVOLUZIONE TEMPORALE")
    logger.info(f"{'='*70}")
    logger.info(f"Passi totali: {N_STEPS}")
    logger.info(f"Timestep dt:  {DT}s")
    logger.info(f"Tempo totale: {N_STEPS * DT}s")
    logger.info(f"{'='*70}\n")
    
    H_initial = solitone.energia_totale
    
    for step in range(1, N_STEPS + 1):
        # Evolvi sistema
        solitone.evolve(DT)
        
        # Record diagnostica ogni SAVE_EVERY
        if step % SAVE_EVERY == 0:
            tracker.record(step, solitone)
            tracker.log_summary(step)
    
    # Diagnostica finale
    logger.info(f"\n{'='*70}")
    logger.info("RISULTATI FINALI")
    logger.info(f"{'='*70}")
    
    H_final = solitone.energia_totale
    H_drift = abs(H_final - H_initial) / abs(H_initial)
    
    chi_values = np.array([seg.chi for seg in solitone.children])
    chi_std_final = np.std(chi_values)
    
    logger.info(f"Conservazione energia:")
    logger.info(f"  H_initial:     {H_initial:.6e}")
    logger.info(f"  H_final:       {H_final:.6e}")
    logger.info(f"  |ΔH/H|:        {H_drift:.6e} ({H_drift*100:.4f}%)")
    
    logger.info(f"\nSeparazione di fase:")
    logger.info(f"  χ_std iniziale: {tracker.chi_std[0]:.6f}")
    logger.info(f"  χ_std finale:   {chi_std_final:.6f}")
    
    if chi_std_final > 1.0:
        logger.info(f"  ✅ SEPARAZIONE PERSISTENTE: Var(χ)^½ > 1.0")
    else:
        logger.warning(f"  ⚠️  SEPARAZIONE DEBOLE: Var(χ)^½ = {chi_std_final:.4f}")
    
    logger.info(f"\nStabilità temporale:")
    logger.info(f"  σ(τ) iniziale: {tracker.tau_std[0]:.6f}")
    logger.info(f"  σ(τ) finale:   {tracker.tau_std[-1]:.6f}")
    
    # Analisi clustering
    n_materia = np.sum(chi_values > 0)
    n_spazio = np.sum(chi_values < 0)
    logger.info(f"\nClustering topologico:")
    logger.info(f"  Materia (χ>0): {n_materia}/{N_SEGMENTI} nodi")
    logger.info(f"  Spazio  (χ<0): {n_spazio}/{N_SEGMENTI} nodi")
    
    # Salva risultati
    logger.info(f"\n{'='*70}")
    save_to_hdf5(DB_FILE, solitone, tracker)
    logger.info(f"{'='*70}")
    
    # Verdetto finale
    success = H_drift < 1e-2 and chi_std_final > 0.5
    
    if success:
        logger.info("\n🎉 SIMULAZIONE COMPLETATA CON SUCCESSO!")
        logger.info("   - Energia conservata (drift < 1%)")
        logger.info("   - Separazione di fase persistente")
        logger.info("\n✨ L'universo respira! ✨\n")
    else:
        logger.warning("\n⚠️  SIMULAZIONE COMPLETATA CON ANOMALIE")
        if H_drift >= 1e-2:
            logger.warning(f"   - Drift energia eccessivo: {H_drift*100:.4f}%")
        if chi_std_final <= 0.5:
            logger.warning(f"   - Separazione di fase debole: {chi_std_final:.4f}")
    
    return success


if __name__ == "__main__":
    try:
        success = run_simulation()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception("ERRORE FATALE:")
        sys.exit(1)
