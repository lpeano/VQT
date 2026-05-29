"""
================================================================================
VALIDAZIONE PEANO-VQT — Simulazione di Produzione Monitorata
================================================================================

Obiettivo
---------
Osservare il comportamento del motore VQT durante la saturazione del campo chi
e verificare che:
  1. La triade energetica (E_chi, E_RX, E_Psi) evolva correttamente
  2. Il drain chi -> Psi si attivi quando chi_saturation > 0.8
  3. La fase geometrica Icosaedrica corrisponda all'evento di "nascita materia"
  4. Il file HDF5 registri correttamente la triade per replay offline

Configurazione
--------------
  chi_mean = 45.0  ->  chi_saturation = 45/50 = 0.90 >> soglia (0.8)
  Il drain e' attivo fin dal primo step.

Output
------
  osservazioni_simulazione.log  — log fisico per step
  output_peano/peano_sim_*.h5   — HDF5 con triade per replay
================================================================================
"""

import sys
import os
import time
import logging
import numpy as np
from pathlib import Path
from datetime import datetime

# Path setup per esecuzione diretta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.hdf5_logger import HDF5Logger, HDF5LoggerConfig
from wqt_oop.energy_drift_observer import SimulationState
from wqt_oop.energy_metrics import classify_geometric_phase, load_h5_and_validate


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

N_SEGMENTI  = 24       # Reticolo Leech (24-cell)
N_STEPS     = 300      # Step totali di evoluzione
DT          = 0.1      # Timestep [unita' Planck]
LOG_EVERY   = 10       # Log triade ogni N step
SAVE_EVERY  = 5        # Salva frame HDF5 ogni N step

CHI_MEAN    = 45.0     # chi_saturation = 45/50 = 0.90 (drain attivo)
CHI_SPREAD  = 3.0      # Spread iniziale
CHI_STABLE  = 50.0     # Valore di vuoto (coincide con PhysicsContext default)

OUTPUT_DIR  = Path("output_peano")
LOG_FILE    = Path("osservazioni_simulazione.log")


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configura logging su console + file."""
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)

    return logging.getLogger(__name__)


# ============================================================================
# INIZIALIZZAZIONE
# ============================================================================

def initialize_high_saturation_system(logger: logging.Logger) -> SolitoneComposito:
    """
    Crea SolitoneComposito(24) con chi vicino a chi_stable.

    Con chi_mean=45 e chi_stable=50 la saturazione iniziale e' 0.90,
    superiore alla soglia di drain (0.80): il meccanismo Peano-VQT e'
    attivo fin dal primo step.
    """
    rng = np.random.default_rng(2026)
    physics_L0 = PhysicsContext.for_level(0)
    physics_L1 = PhysicsContext.for_level(1)

    logger.info("=" * 70)
    logger.info("INIZIALIZZAZIONE SISTEMA AD ALTA SATURAZIONE")
    logger.info("=" * 70)
    logger.info(f"  N_SEGMENTI  = {N_SEGMENTI}")
    logger.info(f"  chi_mean    = {CHI_MEAN}  (chi_sat = {CHI_MEAN/CHI_STABLE:.2f})")
    logger.info(f"  chi_spread  = {CHI_SPREAD}")
    logger.info(f"  soglia_drain= 0.80")
    logger.info(f"  N_STEPS     = {N_STEPS}, DT = {DT}")

    # Distribuzione bimodale: meta' + meta' - (|chi| uguale per entrambi)
    segments = []
    for i in range(N_SEGMENTI):
        sign = 1.0 if i < N_SEGMENTI // 2 else -1.0
        chi  = sign * (CHI_MEAN + rng.uniform(-CHI_SPREAD, CHI_SPREAD))
        vel  = rng.uniform(-1.0, 1.0)

        theta = 2 * np.pi * i / N_SEGMENTI
        pos   = np.array([np.cos(theta), np.sin(theta), 0.0])

        segments.append(SegmentoQuantistico(chi=chi, vel=vel,
                                            physics=physics_L0, position=pos))

    soliton = SolitoneComposito(segments, physics_L1, screening_enabled=True)

    H0 = soliton.energia_totale
    chi_vals = np.array([s.chi for s in segments])
    chi_sat0 = float(np.mean(np.abs(chi_vals))) / CHI_STABLE

    logger.info(f"  H_iniziale  = {H0:.6e}")
    logger.info(f"  chi_sat_0   = {chi_sat0:.4f}  "
                f"(fase: {classify_geometric_phase(chi_sat0)})")
    logger.info("=" * 70)

    return soliton


# ============================================================================
# LOOP PRINCIPALE
# ============================================================================

def run_validation() -> dict:
    """
    Esegue la simulazione monitorata e valida il file HDF5 al termine.

    Returns il report di validazione (output di load_h5_and_validate).
    """
    log = setup_logging()
    soliton = initialize_high_saturation_system(log)

    # --- HDF5 Logger ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    h5_path = OUTPUT_DIR / f"peano_sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
    hdf5_cfg = HDF5LoggerConfig(
        filepath=h5_path,
        save_interval=SAVE_EVERY,
        enable_swmr=False,   # SWMR off per compatibilita' Windows
        buffer_size=20,
        compression="gzip",
    )
    hdf5_log = HDF5Logger(
        config=hdf5_cfg,
        universe=soliton,
        metadata={
            "N_segmenti": N_SEGMENTI,
            "N_steps": N_STEPS,
            "dt": DT,
            "chi_mean": CHI_MEAN,
            "chi_stable": CHI_STABLE,
            "drain_threshold": 0.8,
        },
    )

    H_initial = soliton.energia_totale
    t_start   = time.time()

    log.info("")
    log.info("INIZIO EVOLUZIONE TEMPORALE")
    log.info(f"{'Step':>6}  {'Fase':16}  {'chi_sat':>8}  "
             f"{'E_chi':>12}  {'E_RX':>12}  {'E_Psi':>12}  {'H_drift':>10}")
    log.info("-" * 82)

    condensation_logged = False
    phase_counts = {"Ottaedrica": 0, "Cubottaedrica": 0, "Icosaedrica": 0}

    for step in range(1, N_STEPS + 1):
        soliton.evolve(DT)

        # --- Log triade ---
        if step % LOG_EVERY == 0 or step == 1:
            triad    = soliton.get_energy_triad()
            chi_vals = np.array([soliton._get_child_chi(c) for c in soliton.children])
            chi_sat  = float(np.mean(np.abs(chi_vals))) / CHI_STABLE
            phase    = classify_geometric_phase(chi_sat)
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

            H_now   = soliton.energia_totale
            drift   = abs(H_now - H_initial) / max(abs(H_initial), 1e-30)

            E_chi = triad.E_chi if triad else float("nan")
            E_RX  = triad.E_RX  if triad else float("nan")
            E_Psi = triad.E_Psi if triad else float("nan")

            log.info(f"{step:6d}  {phase:16s}  {chi_sat:8.4f}  "
                     f"{E_chi:12.4e}  {E_RX:12.4e}  {E_Psi:12.4e}  {drift:10.3e}")

            # Evento condensazione materia
            if phase == "Icosaedrica" and not condensation_logged:
                condensation_logged = True
                log.warning(
                    f"Evento di condensazione materia rilevato: "
                    f"E_Psi = {E_Psi:.4e}, architettura icosaedrica consolidata."
                )

            # Alert su violazione numerica (E_Psi non deve decrementare)
            if triad and triad.E_Psi < 0:
                log.error(
                    f"DIVERGENZA NUMERICA al step {step}: "
                    f"E_Psi={E_Psi:.4e} < 0. Stato triade: {triad}"
                )

        # --- Salva frame HDF5 ---
        if step % SAVE_EVERY == 0:
            state = SimulationState(
                step=step,
                time=step * DT,
                H_total=soliton.energia_totale,
                drift=abs(soliton.energia_totale - H_initial) / max(abs(H_initial), 1e-30),
                N_solitons=1,
                T_eff=(soliton.fermi_screener.T_eff
                       if soliton.screening_enabled else soliton.physics.T_fermi),
                wall_time=time.time(),
            )
            hdf5_log.update(state)

    hdf5_log.close()
    elapsed = time.time() - t_start

    # --- Riepilogo run ---
    log.info("")
    log.info("=" * 70)
    log.info("RIEPILOGO SIMULAZIONE")
    log.info("=" * 70)
    H_final = soliton.energia_totale
    total_drift = abs(H_final - H_initial) / max(abs(H_initial), 1e-30)
    log.info(f"  H_iniziale:       {H_initial:.6e}")
    log.info(f"  H_finale:         {H_final:.6e}")
    log.info(f"  Drift totale:     {total_drift:.3e}  ({total_drift*100:.4f}%)")
    log.info(f"  E_Psi finale:     {soliton._peano_analyzer.E_psi_total:.6e}")
    log.info(f"  Fasi registrate:  {phase_counts}")
    log.info(f"  Tempo simulazione:{elapsed:.1f}s")
    log.info(f"  File HDF5:        {h5_path}")
    log.info("=" * 70)

    # --- Validazione HDF5 ---
    log.info("")
    log.info("VALIDAZIONE HDF5 (load_h5_and_validate)")
    report = load_h5_and_validate(h5_path, chi_stable=CHI_STABLE, verbose=True)

    if not report["E_psi_monotonic"]:
        log.error(
            f"INVARIANTE VIOLATA: E_Psi non monotona "
            f"({report['E_psi_violations']} violazioni nel file HDF5)"
        )
    else:
        log.info("Invariante E_Psi monotona: OK")

    if report["icosahedral_reached"]:
        log.info(
            f"Condensazione materia confermata al frame "
            f"{report['condensation_frame']}: "
            f"E_Psi = {report['E_psi_at_condensation']:.4e}"
        )

    # Aggiorna checkpoint
    _update_checkpoint(report, h5_path, elapsed)

    return report


# ============================================================================
# CHECKPOINT UPDATE
# ============================================================================

def _update_checkpoint(report: dict, h5_path: Path, elapsed: float) -> None:
    """Aggiorna docs/MIGRAZIONE_CHECKPOINT.md con i risultati della run."""
    ck_path = Path(__file__).parent.parent / "docs" / "MIGRAZIONE_CHECKPOINT.md"
    if not ck_path.exists():
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    result_block = (
        f"\n---\n"
        f"## Run di Validazione — {now}\n\n"
        f"- File HDF5: `{h5_path.name}`\n"
        f"- Frames: {report['total_frames']}\n"
        f"- E_Psi finale: {report['E_psi_final']:.4e}\n"
        f"- Drain frames: {report['drain_frames']}\n"
        f"- E_Psi monotona: {'SI' if report['E_psi_monotonic'] else 'NO'}\n"
        f"- Fasi: {report['geometric_phase_counts']}\n"
        f"- Condensazione (icosaedrica): "
        f"{'SI (frame ' + str(report['condensation_frame']) + ')' if report['icosahedral_reached'] else 'NO'}\n"
        f"- Tempo simulazione: {elapsed:.1f}s\n"
    )

    with open(ck_path, "a", encoding="utf-8") as f:
        f.write(result_block)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    report = run_validation()
    sys.exit(0 if report["E_psi_monotonic"] else 1)
