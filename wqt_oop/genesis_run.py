"""
================================================================================
GENESIS RUN — Transizione di Fase Ottaedrica -> Icosaedrica
================================================================================

Obiettivo
---------
Osservare la "nascita della materia": il sistema parte in fase Ottaedrica
(chi_mean=5, chi_sat=0.10) e il doppio pozzo V(chi)=beta(chi^2-chi_0^2)^2
guida i segmenti verso chi_stable=50 (fase Icosaedrica, chi_sat=1.0).

Monitoraggio in tempo reale
---------------------------
  PhaseEventLogger : rileva ogni cambio di fase (Ottaedrica/Cubottaedrica/
                     Icosaedrica) e ogni Delta-E_Psi > 5% tra step consecutivi
  eventi_nascita.log : file dedicato agli eventi di transizione
  genesis_log.log    : log completo della run

Output
------
  output_peano/genesis_*.h5   — HDF5 con triade per replay
  eventi_nascita.log          — eventi di transizione e drain
  genesis_log.log             — log completo

================================================================================
"""

import sys
import os
import time
import logging
import warnings
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Sopprimi UserWarning "DRIFT ENERGIA CRITICO" dai segmenti (atteso a chi<<chi_stable)
warnings.filterwarnings("ignore", message=".*DRIFT ENERGIA CRITICO.*")

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.hdf5_logger import HDF5Logger, HDF5LoggerConfig
from wqt_oop.energy_drift_observer import SimulationState
from wqt_oop.energy_metrics import (
    classify_geometric_phase,
    load_h5_and_validate,
)


# ============================================================================
# CONFIGURAZIONE GENESIS
# ============================================================================

CHI_MEAN    = 5.0      # Fase Ottaedrica: chi_sat = 5/50 = 0.10
CHI_SPREAD  = 0.5      # Spread stretto per partenza netta
CHI_STABLE  = 50.0     # Valore di vuoto (doppio pozzo)
N_STEPS     = 2000     # Ampio margine per catturare la transizione
DT          = 0.1      # Timestep
LOG_EVERY   = 10       # Log triade ogni N step
SAVE_EVERY  = 20       # Salva frame HDF5 ogni N step

DPSI_THRESHOLD = 0.05  # Delta-E_Psi relativo soglia (5%)

OUTPUT_DIR      = Path("output_peano")
GENESIS_LOG     = Path("genesis_log.log")
EVENTI_NASCITA  = Path("eventi_nascita.log")


# ============================================================================
# PHASE EVENT LOGGER
# ============================================================================

class PhaseEventLogger:
    """
    Monitora in tempo reale i cambi di fase geometrica e i salti di E_Psi.

    Scrive su eventi_nascita.log ogni:
    - Transizione di fase (Ottaedrica->Cubottaedrica->Icosaedrica)
    - Delta-E_Psi > 5% relativo tra due step di log consecutivi
    - Primo evento di drain (E_Psi 0 -> >0)
    """

    def __init__(self, event_path: Path, main_logger: logging.Logger):
        self._path = event_path
        self._log = main_logger
        self._current_phase: str = "START"
        self._E_psi_prev: float = 0.0
        self._events: list = []
        self._first_drain_step: int = -1
        self._first_drain_E_psi: float = 0.0
        self._icosahedral_first_step: int = -1
        self._icosahedral_first_E_psi: float = 0.0

        # Inizializza file eventi
        with open(event_path, "w", encoding="utf-8") as f:
            f.write("# eventi_nascita.log — Genesis Run\n")
            f.write(f"# Avviata: {datetime.now().isoformat()}\n")
            f.write(f"# Config: chi_mean={CHI_MEAN}, N_STEPS={N_STEPS}\n\n")

    def update(self, step: int, chi_sat: float, E_Psi: float) -> str:
        """
        Aggiorna il monitor e registra eventi rilevanti.

        Parameters
        ----------
        step : int
        chi_sat : float
        E_Psi : float  (accumulato fino a questo step)

        Returns
        -------
        phase : str  (fase corrente)
        """
        phase = classify_geometric_phase(chi_sat)

        # --- Transizione di fase ---
        if phase != self._current_phase and self._current_phase != "START":
            msg = (f"[FASE] Step {step:5d}: {self._current_phase:15s} -> {phase}"
                   f"  |  chi_sat={chi_sat:.4f}")
            self._emit(step, msg, level="WARNING")
            if phase == "Icosaedrica" and self._icosahedral_first_step < 0:
                self._icosahedral_first_step = step
                self._icosahedral_first_E_psi = E_Psi
                msg2 = (f"[CRISTALLIZZAZIONE] Step {step}: "
                        f"prima fase Icosaedrica  |  E_Psi={E_Psi:.4e}")
                self._emit(step, msg2, level="WARNING")
        elif self._current_phase == "START":
            msg = (f"[FASE] Step {step:5d}: fase iniziale = {phase}"
                   f"  |  chi_sat={chi_sat:.4f}")
            self._emit(step, msg, level="INFO")
            if phase == "Icosaedrica" and self._icosahedral_first_step < 0:
                self._icosahedral_first_step = step
                self._icosahedral_first_E_psi = E_Psi

        self._current_phase = phase

        # --- Primo drain ---
        if self._first_drain_step < 0 and E_Psi > 0:
            self._first_drain_step = step
            self._first_drain_E_psi = E_Psi
            msg = (f"[DRAIN-PRIMO] Step {step}: "
                   f"E_Psi 0 -> {E_Psi:.4e}  (drain attivato)")
            self._emit(step, msg, level="INFO")

        # --- Delta-E_Psi > soglia ---
        if self._E_psi_prev > 0:
            delta_rel = (E_Psi - self._E_psi_prev) / self._E_psi_prev
            if delta_rel > DPSI_THRESHOLD:
                msg = (f"[DELTA-EPSI] Step {step}: "
                       f"Delta-E_Psi rilevato = {delta_rel*100:.1f}%"
                       f"  |  E_Psi={E_Psi:.4e}")
                self._emit(step, msg, level="INFO")

        self._E_psi_prev = E_Psi
        return phase

    def _emit(self, step: int, msg: str, level: str = "INFO"):
        """Scrive messaggio su log principale e su eventi_nascita.log."""
        if level == "WARNING":
            self._log.warning(msg)
        else:
            self._log.info(msg)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        self._events.append((step, msg))

    # --- Report finale ---
    @property
    def first_icosahedral_step(self) -> int:
        return self._icosahedral_first_step

    @property
    def first_icosahedral_E_psi(self) -> float:
        return self._icosahedral_first_E_psi

    @property
    def first_drain_step(self) -> int:
        return self._first_drain_step

    @property
    def events(self) -> list:
        return list(self._events)


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging() -> logging.Logger:
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%H:%M:%S"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fh = logging.FileHandler(GENESIS_LOG, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)

    return logging.getLogger(__name__)


# ============================================================================
# INIZIALIZZAZIONE SISTEMA
# ============================================================================

def initialize_genesis_system(log: logging.Logger) -> SolitoneComposito:
    """
    Sistema L1 (24 segmenti) con distribuzione bimodale a chi_mean=5.

    Fase iniziale: Ottaedrica (chi_sat = 5/50 = 0.10).
    Il doppio pozzo V(chi)=beta*(chi^2-chi_0^2)^2 guida i segmenti
    verso chi_stable=+-50 (fase Icosaedrica).
    """
    rng = np.random.default_rng(2026)
    physics_L0 = PhysicsContext.for_level(0)
    physics_L1 = PhysicsContext.for_level(1)

    log.info("=" * 70)
    log.info("GENESIS RUN — INIZIALIZZAZIONE")
    log.info("=" * 70)
    log.info(f"  N_SEGMENTI  = 24 (Reticolo Leech)")
    log.info(f"  chi_mean    = {CHI_MEAN}  (chi_sat_0 = {CHI_MEAN/CHI_STABLE:.2f} -> Ottaedrica)")
    log.info(f"  chi_stable  = {CHI_STABLE}")
    log.info(f"  N_STEPS     = {N_STEPS}, DT = {DT}")
    log.info(f"  Attesa: V(chi) guidera' chi da {CHI_MEAN} -> +-{CHI_STABLE}")
    log.info(f"  Transizione attesa: Ottaedrica -> Cubottaedrica -> Icosaedrica")

    segments = []
    for i in range(24):
        sign = 1.0 if i < 12 else -1.0
        chi = sign * (CHI_MEAN + rng.uniform(-CHI_SPREAD, CHI_SPREAD))
        vel = rng.uniform(-0.1, 0.1)  # Velocita' piccola: partenza quasi-ferma
        theta = 2 * np.pi * i / 24
        pos = np.array([np.cos(theta), np.sin(theta), 0.0])
        segments.append(SegmentoQuantistico(chi=chi, vel=vel,
                                            physics=physics_L0, position=pos))

    soliton = SolitoneComposito(segments, physics_L1, screening_enabled=True)

    H0 = soliton.energia_totale
    chi_vals = np.array([s.chi for s in segments])
    chi_sat0 = float(np.mean(np.abs(chi_vals))) / CHI_STABLE
    phase0 = classify_geometric_phase(chi_sat0)

    log.info(f"  H_iniziale  = {H0:.6e}")
    log.info(f"  chi_sat_0   = {chi_sat0:.4f}  (fase: {phase0})")
    log.info("=" * 70)

    return soliton


# ============================================================================
# LOOP PRINCIPALE
# ============================================================================

def run_genesis() -> dict:
    log = setup_logging()
    soliton = initialize_genesis_system(log)

    # --- HDF5 Logger ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    h5_path = OUTPUT_DIR / f"genesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
    hdf5_cfg = HDF5LoggerConfig(
        filepath=h5_path,
        save_interval=SAVE_EVERY,
        enable_swmr=False,
        buffer_size=50,
        compression="gzip",
    )
    hdf5_log = HDF5Logger(
        config=hdf5_cfg,
        universe=soliton,
        metadata={
            "chi_mean": CHI_MEAN,
            "chi_stable": CHI_STABLE,
            "N_steps": N_STEPS,
            "dt": DT,
            "genesis_run": True,
        },
    )

    # --- Phase Event Logger ---
    phase_log = PhaseEventLogger(EVENTI_NASCITA, log)

    H_initial = soliton.energia_totale
    t_start = time.time()

    log.info("")
    log.info("INIZIO EVOLUZIONE")
    log.info(
        f"{'Step':>6}  {'Fase':16}  {'chi_sat':>8}  "
        f"{'E_chi':>12}  {'E_RX':>12}  {'E_Psi':>12}  {'H_drift':>10}"
    )
    log.info("-" * 82)

    for step in range(1, N_STEPS + 1):
        soliton.evolve(DT)

        if step % LOG_EVERY == 0 or step == 1:
            triad = soliton.get_energy_triad()
            chi_vals = np.array([soliton._get_child_chi(c) for c in soliton.children])
            chi_sat = float(np.mean(np.abs(chi_vals))) / CHI_STABLE
            H_now = soliton.energia_totale
            drift = abs(H_now - H_initial) / max(abs(H_initial), 1e-30)

            E_chi = triad.E_chi if triad else float("nan")
            E_RX  = triad.E_RX  if triad else float("nan")
            E_Psi = triad.E_Psi if triad else float("nan")

            # Aggiorna phase logger (rileva transizioni + Delta-E_Psi)
            phase = phase_log.update(step, chi_sat, E_Psi)

            log.info(
                f"{step:6d}  {phase:16s}  {chi_sat:8.4f}  "
                f"{E_chi:12.4e}  {E_RX:12.4e}  {E_Psi:12.4e}  {drift:10.3e}"
            )

        # Salva frame HDF5
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

    # --- Riepilogo ---
    H_final = soliton.energia_totale
    triad_fin = soliton.get_energy_triad()
    E_psi_fin = triad_fin.E_Psi if triad_fin else 0.0

    log.info("")
    log.info("=" * 70)
    log.info("RIEPILOGO GENESIS")
    log.info("=" * 70)
    log.info(f"  H_iniziale:           {H_initial:.6e}")
    log.info(f"  H_finale:             {H_final:.6e}")
    log.info(f"  E_Psi finale:         {E_psi_fin:.6e}")
    log.info(f"  Tempo simulazione:    {elapsed:.1f}s")

    if phase_log.first_icosahedral_step > 0:
        log.info(f"  Prima cristallizzazione icosaedrica: step {phase_log.first_icosahedral_step}")
        log.info(f"  E_Psi al momento:     {phase_log.first_icosahedral_E_psi:.6e}")
    else:
        log.info("  ATTENZIONE: fase Icosaedrica non raggiunta in questa run")

    if phase_log.first_drain_step > 0:
        log.info(f"  Primo drain:          step {phase_log.first_drain_step}")

    log.info(f"  N. eventi registrati: {len(phase_log.events)}")
    log.info(f"  File HDF5:            {h5_path}")
    log.info(f"  Log eventi:           {EVENTI_NASCITA}")
    log.info("=" * 70)

    # --- Validazione HDF5 ---
    log.info("")
    log.info("VALIDAZIONE HDF5")
    report = load_h5_and_validate(h5_path, chi_stable=CHI_STABLE, verbose=True)

    # --- Aggiorna checkpoint ---
    _update_checkpoint(report, phase_log, h5_path, elapsed)
    log.info("Checkpoint aggiornato: docs/MIGRAZIONE_CHECKPOINT.md")

    return {
        "report": report,
        "first_icosahedral_step": phase_log.first_icosahedral_step,
        "first_icosahedral_E_psi": phase_log.first_icosahedral_E_psi,
        "first_drain_step": phase_log.first_drain_step,
        "events": phase_log.events,
        "elapsed": elapsed,
    }


# ============================================================================
# CHECKPOINT UPDATE
# ============================================================================

def _update_checkpoint(
    report: dict, phase_log: PhaseEventLogger, h5_path: Path, elapsed: float
) -> None:
    ck_path = Path(__file__).parent.parent / "docs" / "MIGRAZIONE_CHECKPOINT.md"
    if not ck_path.exists():
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    ico_step = phase_log.first_icosahedral_step
    ico_epsi = phase_log.first_icosahedral_E_psi

    block = (
        f"\n---\n"
        f"## GENESIS RUN — {now}\n\n"
        f"**Config**: chi_mean={CHI_MEAN}, N_STEPS={N_STEPS}, dt={DT}\n\n"
        f"**Domanda a) Prima cristallizzazione icosaedrica**: "
        f"{'step ' + str(ico_step) if ico_step > 0 else 'NON RAGGIUNTA'}\n\n"
        f"**Domanda b) Salto E_Psi al momento della cristallizzazione**: "
        f"{ico_epsi:.4e}\n\n"
        f"**Primo drain attivato**: step {phase_log.first_drain_step}\n\n"
        f"**Validazione HDF5**:\n"
        f"- Frames: {report['total_frames']}\n"
        f"- E_Psi finale: {report['E_psi_final']:.4e}\n"
        f"- E_Psi monotona: {'SI' if report['E_psi_monotonic'] else 'NO'}\n"
        f"- Drain frames: {report['drain_frames']}\n"
        f"- Fasi: {report['geometric_phase_counts']}\n"
        f"- Condensazione confermata: "
        f"{'SI (frame ' + str(report['condensation_frame']) + ')' if report['icosahedral_reached'] else 'NO'}\n\n"
        f"**N. eventi registrati**: {len(phase_log.events)}\n"
        f"**Tempo simulazione**: {elapsed:.1f}s\n"
        f"**File**: {h5_path.name}\n"
    )

    with open(ck_path, "a", encoding="utf-8") as f:
        f.write(block)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    results = run_genesis()
    sys.exit(0 if results["report"]["E_psi_monotonic"] else 1)
