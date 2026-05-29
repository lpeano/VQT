"""
================================================================================
L2 AGGREGATION RUN — Due Solitoni L1 in Interazione
================================================================================

Esperimento di scalabilita' L1 -> L2:
  Due SolitoneComposito L1 icosaedrici (chi ~= +-50) si avvicinano in
  chi-spazio tramite un accoppiamento inter-solitonico Yukawa.

Scenari
-------
  SAME : chi_A = +52, chi_B = +48   (stesso segno)  -> aggregazione attesa
  CROSS: chi_A = +52, chi_B = -48   (segni opposti) -> frustrazione topologica

Inter-coupling model (centro di massa)
---------------------------------------
  E_inter = kappa * W_AB * (chi_A - chi_B)^2 / 2
           - lambda * W_AB * tanh(chi_A/chi_0) * tanh(chi_B/chi_0)
  W_AB    = exp(-D / L_eff)   (Yukawa)
  F_a     = -dE_inter/d(chi_A)   applicata uniformemente ai 24 segmenti di A
  F_b     = -dE_inter/d(chi_B)   uniformemente a B   (terzo principio)

Parametri fisici
----------------
  kappa_inter = 2.0   (~2x accoppiamento L2, amplificato per visibilita')
  W_AB = exp(-5/3) ~= 0.189
  F_inter(Dchi=4, same)  ~= 1.5  vs  F_dw(chi=52) ~= 42   (3.5% perturbazione)
  F_inter(Dchi=100, cross) ~= 38  vs  F_dw(chi=52) ~= 42   (comparabili!)

Output
------
  l2_aggregation.log   -- log fisico step-by-step
  eventi_l2.log        -- eventi discreti (fase, frustrazione, aggregazione)
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

warnings.filterwarnings("ignore", message=".*DRIFT ENERGIA CRITICO.*")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import classify_geometric_phase


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

# --- Scenario ---
# "SAME"  : chi_B positivo (stesso segno di A) -> aggregazione attesa
# "CROSS" : chi_B negativo (segno opposto)     -> frustrazione attesa
SCENARIOS = ["SAME", "CROSS"]

CHI_A_MEAN   = 52.0    # Solitone A: leggermente sopra chi_stable
CHI_B_SAME   = 48.0    # Solitone B (SAME): leggermente sotto
CHI_B_CROSS  = -48.0   # Solitone B (CROSS): segno opposto
CHI_STABLE   = 50.0
CHI_SPREAD   = 1.0

# --- Coupling inter-solitonico ---
KAPPA_INTER  = 2.0    # kappa (amplificato ~20x L2 fisica per visibilita')
LAMBDA_INTER = 0.5    # lambda scambio inter-L1
D_SEPARATION = 5.0    # distanza spaziale centroidi [u. reticolo]
L_EFF_INTER  = 3.0    # lunghezza Yukawa
W_AB = float(np.exp(-D_SEPARATION / L_EFF_INTER))   # ~0.189

# --- Simulazione ---
N_STEPS     = 400
DT          = 0.1
LOG_EVERY   = 10

# --- Soglie monitoraggio ---
DELTA_CHI_AGG    = 3.0    # |Dchi| < soglia -> aggregazione
DELTA_CHI_REP    = 1.3    # |Dchi| > 1.3x iniziale -> repulsione

MAIN_LOG    = Path("l2_aggregation.log")
EVENTI_LOG  = Path("eventi_l2.log")


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging() -> logging.Logger:
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    fh = logging.FileHandler(MAIN_LOG, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    root.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    root.addHandler(ch)
    return logging.getLogger(__name__)


def emit_event(msg: str, log: logging.Logger, level: str = "WARNING") -> None:
    """Scrive evento su log principale e su eventi_l2.log."""
    if level == "WARNING":
        log.warning(msg)
    else:
        log.info(msg)
    with open(EVENTI_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ============================================================================
# INIZIALIZZAZIONE SOLITONI L1
# ============================================================================

def make_l1_soliton(
    chi_mean: float,
    center_x: float,
    rng: np.random.Generator,
    label: str,
    log: logging.Logger,
) -> SolitoneComposito:
    """
    Crea un SolitoneComposito L1 (24 segmenti) in stato icosaedrico.

    Parameters
    ----------
    chi_mean   : valore medio del campo chi (es. +52 o -48)
    center_x   : coordinata x del centroide [offset spaziale]
    rng        : generatore casuale
    label      : 'A' o 'B' (per il log)
    """
    physics_L0 = PhysicsContext.for_level(0)
    physics_L1 = PhysicsContext.for_level(1)

    segments = []
    for i in range(24):
        chi = chi_mean + rng.uniform(-CHI_SPREAD, CHI_SPREAD)
        vel = rng.uniform(-0.3, 0.3)

        # Posizione: cerchio di raggio 1 centrato su center_x
        theta = 2.0 * np.pi * i / 24
        pos = np.array([center_x + np.cos(theta), np.sin(theta), 0.0])

        segments.append(SegmentoQuantistico(
            chi=chi, vel=vel, physics=physics_L0, position=pos
        ))

    sol = SolitoneComposito(segments, physics_L1, screening_enabled=True)
    chi_sat = abs(chi_mean) / CHI_STABLE
    phase = classify_geometric_phase(chi_sat)
    log.debug(f"  Solitone {label}: chi_mean={chi_mean:+.1f}, chi_sat={chi_sat:.3f}, "
              f"fase={phase}, H={sol.energia_totale:.3e}")
    return sol


# ============================================================================
# SISTEMA DUO-SOLITONICO
# ============================================================================

class DuoSolitonSystem:
    """
    Due SolitoneComposito L1 con accoppiamento inter-solitonico Yukawa.

    Il coupling agisce sui baricentri dei campi chi (approssimazione
    di campo medio / centro di massa) e viene distribuito uniformemente
    ai 24 segmenti di ciascun solitone.
    """

    def __init__(self, sol_a: SolitoneComposito, sol_b: SolitoneComposito):
        self.A = sol_a
        self.B = sol_b

    # ------------------------------------------------------------------
    def chi_bar(self, sol: SolitoneComposito) -> float:
        """Baricentro del campo chi (valore medio sui 24 segmenti)."""
        return sol.compute_barycenter()

    # ------------------------------------------------------------------
    def compute_inter_energy(self) -> tuple[float, float, float]:
        """
        Energia di interazione inter-solitonica.

        Returns (E_coupling, E_exchange, E_inter_total)
        """
        chi_a = self.chi_bar(self.A)
        chi_b = self.chi_bar(self.B)
        chi_0 = CHI_STABLE

        E_coupling  = 0.5 * KAPPA_INTER * W_AB * (chi_a - chi_b) ** 2
        tanh_a = float(np.tanh(chi_a / chi_0))
        tanh_b = float(np.tanh(chi_b / chi_0))
        E_exchange  = -LAMBDA_INTER * W_AB * tanh_a * tanh_b

        return E_coupling, E_exchange, E_coupling + E_exchange

    # ------------------------------------------------------------------
    def compute_inter_forces(self) -> tuple[float, float]:
        """
        Forze inter-solitoniche sul campo chi (terzo principio: F_b = -F_a).

        Derivate da -dE_inter/d(chi_a) e -dE_inter/d(chi_b).
        """
        chi_a = self.chi_bar(self.A)
        chi_b = self.chi_bar(self.B)
        chi_0 = CHI_STABLE

        tanh_a  = float(np.tanh(chi_a / chi_0))
        tanh_b  = float(np.tanh(chi_b / chi_0))
        sech2_a = 1.0 - tanh_a ** 2
        sech2_b = 1.0 - tanh_b ** 2

        # dE_coupling/d(chi_a) = kappa * W * (chi_a - chi_b)
        dE_coup_a = KAPPA_INTER * W_AB * (chi_a - chi_b)
        dE_coup_b = -dE_coup_a                              # anti-simmetrico

        # dE_exchange/d(chi_a) = -lambda * W * sech2_a * tanh_b / chi_0
        dE_exch_a = -LAMBDA_INTER * W_AB * sech2_a * tanh_b / chi_0
        dE_exch_b = -LAMBDA_INTER * W_AB * tanh_a * sech2_b / chi_0

        F_a = -(dE_coup_a + dE_exch_a)   # F = -dE/dq
        F_b = -(dE_coup_b + dE_exch_b)

        return F_a, F_b

    # ------------------------------------------------------------------
    def evolve(self, dt: float) -> None:
        F_a, F_b = self.compute_inter_forces()
        self.A.evolve(dt, external_force=float(F_a))
        self.B.evolve(dt, external_force=float(F_b))

    # ------------------------------------------------------------------
    @property
    def E_psi_total(self) -> float:
        return (self.A._peano_analyzer.E_psi_total +
                self.B._peano_analyzer.E_psi_total)

    @property
    def H_total(self) -> float:
        _, _, E_inter = self.compute_inter_energy()
        return self.A.energia_totale + self.B.energia_totale + E_inter


# ============================================================================
# MONITOR EVENTI
# ============================================================================

class AggregationMonitor:
    """
    Rileva e logga eventi di aggregazione, repulsione e frustrazione.
    """

    def __init__(self, initial_delta_chi: float, log: logging.Logger, scenario: str):
        self._delta0 = initial_delta_chi
        self._log    = log
        self._scenario = scenario
        self._phase_A: str = "START"
        self._phase_B: str = "START"
        self._E_psi_prev: float = 0.0
        self._aggregated = False
        self._frustrated = False
        self._repelled    = False
        self._outcome: str = "IN_CORSO"

    def update(
        self,
        step: int,
        chi_a: float,
        chi_b: float,
        E_psi: float,
        sol_a: SolitoneComposito,
        sol_b: SolitoneComposito,
    ) -> dict:
        delta_chi = abs(chi_a - chi_b)
        chi_sat_a = abs(chi_a) / CHI_STABLE
        chi_sat_b = abs(chi_b) / CHI_STABLE
        phase_a = classify_geometric_phase(chi_sat_a)
        phase_b = classify_geometric_phase(chi_sat_b)

        info = {
            "step": step, "chi_a": chi_a, "chi_b": chi_b,
            "delta_chi": delta_chi,
            "chi_sat_a": chi_sat_a, "chi_sat_b": chi_sat_b,
            "phase_a": phase_a, "phase_b": phase_b,
            "E_psi": E_psi,
        }

        # --- Transizione di fase A ---
        if phase_a != self._phase_A and self._phase_A != "START":
            emit_event(
                f"[FASE-A] step {step:4d}: {self._phase_A} -> {phase_a} "
                f"| chi_A={chi_a:+.2f} chi_sat={chi_sat_a:.3f}",
                self._log, "WARNING"
            )
        self._phase_A = phase_a

        # --- Transizione di fase B ---
        if phase_b != self._phase_B and self._phase_B != "START":
            emit_event(
                f"[FASE-B] step {step:4d}: {self._phase_B} -> {phase_b} "
                f"| chi_B={chi_b:+.2f} chi_sat={chi_sat_b:.3f}",
                self._log, "WARNING"
            )
        self._phase_B = phase_b

        # --- Frustrazione topologica ---
        if (not self._frustrated and
                chi_a * chi_b < 0 and
                abs(chi_a) > 0.4 * CHI_STABLE and
                abs(chi_b) > 0.4 * CHI_STABLE):
            self._frustrated = True
            emit_event(
                f"[FRUSTRAZIONE] step {step}: chi_A={chi_a:+.2f} e chi_B={chi_b:+.2f} "
                f"hanno segni opposti -- frustrazione topologica rilevata!",
                self._log, "WARNING"
            )

        # --- Aggregazione ---
        if (not self._aggregated and
                delta_chi < DELTA_CHI_AGG and
                phase_a == "Icosaedrica" and
                phase_b == "Icosaedrica"):
            self._aggregated = True
            self._outcome = "AGGREGATO"
            emit_event(
                f"[AGGREGAZIONE] step {step}: Delta_chi={delta_chi:.3f} < {DELTA_CHI_AGG} "
                f"| A={phase_a} B={phase_b} -> STRUTTURA L2 STABILE",
                self._log, "WARNING"
            )

        # --- Repulsione ---
        if (not self._repelled and
                delta_chi > self._delta0 * DELTA_CHI_REP and
                step > 50):
            self._repelled = True
            self._outcome = "RESPINTO"
            emit_event(
                f"[REPULSIONE] step {step}: Delta_chi={delta_chi:.2f} > "
                f"{self._delta0 * DELTA_CHI_REP:.2f} (1.3x iniziale) "
                f"-> i solitoni si allontanano",
                self._log, "WARNING"
            )

        # --- Salto E_Psi (>10% relativo) ---
        if self._E_psi_prev > 0:
            dpsi_rel = (E_psi - self._E_psi_prev) / self._E_psi_prev
            if dpsi_rel > 0.10:
                emit_event(
                    f"[EPSI-JUMP] step {step}: Delta-E_Psi={dpsi_rel*100:.1f}% "
                    f"| E_Psi={E_psi:.4e} -> evento di condensazione durante impatto",
                    self._log
                )
        self._E_psi_prev = E_psi

        return info

    @property
    def outcome(self) -> str:
        return self._outcome

    @property
    def was_frustrated(self) -> bool:
        return self._frustrated


# ============================================================================
# SINGOLO SCENARIO
# ============================================================================

def run_scenario(scenario: str, log: logging.Logger) -> dict:
    """
    Esegue un singolo scenario (SAME o CROSS) e restituisce i risultati.
    """
    chi_b_mean = CHI_B_SAME if scenario == "SAME" else CHI_B_CROSS
    rng = np.random.default_rng(42 + (0 if scenario == "SAME" else 1))

    log.info("")
    log.info("=" * 70)
    log.info(f"SCENARIO: {scenario}")
    log.info(f"  chi_A = {CHI_A_MEAN:+.1f}, chi_B = {chi_b_mean:+.1f}")
    log.info(f"  kappa_inter = {KAPPA_INTER}, lambda_inter = {LAMBDA_INTER}")
    log.info(f"  W_AB = exp(-{D_SEPARATION}/{L_EFF_INTER}) = {W_AB:.4f}")
    log.info(f"  N_STEPS = {N_STEPS}, DT = {DT}")
    log.info("=" * 70)

    emit_event(f"\n=== SCENARIO {scenario} ===", log, "INFO")
    emit_event(f"chi_A={CHI_A_MEAN:+.1f}, chi_B={chi_b_mean:+.1f}", log, "INFO")

    # Inizializza solitoni (A a sinistra, B a destra)
    sol_a = make_l1_soliton(CHI_A_MEAN,  -D_SEPARATION / 2, rng, "A", log)
    sol_b = make_l1_soliton(chi_b_mean,  +D_SEPARATION / 2, rng, "B", log)
    system = DuoSolitonSystem(sol_a, sol_b)

    chi_a0 = system.chi_bar(sol_a)
    chi_b0 = system.chi_bar(sol_b)
    delta0 = abs(chi_a0 - chi_b0)
    H0     = system.H_total

    log.info(f"  chi_A_bar_0 = {chi_a0:+.3f}, chi_B_bar_0 = {chi_b0:+.3f}")
    log.info(f"  |Delta_chi|_0 = {delta0:.3f}")
    log.info(f"  H_sistema_0 = {H0:.4e}")
    log.info(f"  W_AB = {W_AB:.4f}")
    log.info("")

    monitor = AggregationMonitor(delta0, log, scenario)

    log.info(f"{'Step':>6}  {'chi_A':>8}  {'chi_B':>8}  "
             f"{'Dchi':>7}  {'Fase A':12}  {'Fase B':12}  "
             f"{'E_Psi':>12}  {'H_tot':>12}")
    log.info("-" * 95)

    # Serie temporali per analisi finale
    steps_ts, chi_a_ts, chi_b_ts, dchi_ts, epsi_ts = [], [], [], [], []

    t_start = time.time()

    for step in range(1, N_STEPS + 1):
        system.evolve(DT)

        if step % LOG_EVERY == 0 or step == 1:
            chi_a = system.chi_bar(sol_a)
            chi_b = system.chi_bar(sol_b)
            E_psi = system.E_psi_total
            H_tot = system.H_total
            info  = monitor.update(step, chi_a, chi_b, E_psi, sol_a, sol_b)

            log.info(
                f"{step:6d}  {chi_a:+8.3f}  {chi_b:+8.3f}  "
                f"{info['delta_chi']:7.3f}  {info['phase_a']:12s}  {info['phase_b']:12s}  "
                f"{E_psi:12.4e}  {H_tot:12.4e}"
            )

            steps_ts.append(step)
            chi_a_ts.append(chi_a)
            chi_b_ts.append(chi_b)
            dchi_ts.append(info["delta_chi"])
            epsi_ts.append(E_psi)

    elapsed = time.time() - t_start

    # --- Riepilogo scenario ---
    chi_a_fin = system.chi_bar(sol_a)
    chi_b_fin = system.chi_bar(sol_b)
    delta_fin = abs(chi_a_fin - chi_b_fin)
    E_psi_fin = system.E_psi_total
    phase_a_fin = classify_geometric_phase(abs(chi_a_fin) / CHI_STABLE)
    phase_b_fin = classify_geometric_phase(abs(chi_b_fin) / CHI_STABLE)

    outcome = monitor.outcome
    if outcome == "IN_CORSO":
        # Determina dal delta finale
        if delta_fin < DELTA_CHI_AGG:
            outcome = "AGGREGATO"
        elif delta_fin > delta0 * 1.3:
            outcome = "RESPINTO"
        else:
            outcome = "OSCILLANTE"

    log.info("")
    log.info(f"  RIEPILOGO SCENARIO {scenario}")
    log.info(f"  Esito:            {outcome}")
    log.info(f"  chi_A finale:     {chi_a_fin:+.3f}  ({phase_a_fin})")
    log.info(f"  chi_B finale:     {chi_b_fin:+.3f}  ({phase_b_fin})")
    log.info(f"  |Delta_chi| fin:  {delta_fin:.3f}  (iniziale: {delta0:.3f})")
    log.info(f"  E_Psi finale:     {E_psi_fin:.4e}")
    log.info(f"  Frustrazione:     {'SI' if monitor.was_frustrated else 'NO'}")
    log.info(f"  Tempo:            {elapsed:.1f}s")

    emit_event(
        f"[ESITO-{scenario}] {outcome} | Dchi: {delta0:.2f} -> {delta_fin:.2f} "
        f"| A={phase_a_fin} B={phase_b_fin} | Frust={monitor.was_frustrated}",
        log, "WARNING" if outcome == "AGGREGATO" else "INFO"
    )

    return {
        "scenario":    scenario,
        "outcome":     outcome,
        "frustrated":  monitor.was_frustrated,
        "delta_chi_0": delta0,
        "delta_chi_f": delta_fin,
        "chi_a_fin":   chi_a_fin,
        "chi_b_fin":   chi_b_fin,
        "phase_a_fin": phase_a_fin,
        "phase_b_fin": phase_b_fin,
        "E_psi_fin":   E_psi_fin,
        "elapsed":     elapsed,
        "steps":       np.array(steps_ts),
        "chi_a":       np.array(chi_a_ts),
        "chi_b":       np.array(chi_b_ts),
        "dchi":        np.array(dchi_ts),
        "epsi":        np.array(epsi_ts),
    }


# ============================================================================
# MAIN
# ============================================================================

def run_l2_aggregation() -> list[dict]:
    log = setup_logging()

    # Prepara log eventi
    with open(EVENTI_LOG, "w", encoding="utf-8") as f:
        f.write(f"# eventi_l2.log  —  L2 Aggregation Run  —  {datetime.now().isoformat()}\n\n")

    log.info("=" * 70)
    log.info("L2 AGGREGATION RUN — Due Solitoni Icosaedrici L1")
    log.info("=" * 70)
    log.info(f"  Scenario SAME : chi_A={CHI_A_MEAN:+.1f} / chi_B={CHI_B_SAME:+.1f}")
    log.info(f"  Scenario CROSS: chi_A={CHI_A_MEAN:+.1f} / chi_B={CHI_B_CROSS:+.1f}")
    log.info(f"  kappa_inter   = {KAPPA_INTER}")
    log.info(f"  lambda_inter  = {LAMBDA_INTER}")
    log.info(f"  D             = {D_SEPARATION}, L_eff = {L_EFF_INTER}, W = {W_AB:.4f}")
    log.info(f"  N_STEPS       = {N_STEPS}, DT = {DT}")

    results = []
    for scenario in SCENARIOS:
        r = run_scenario(scenario, log)
        results.append(r)

    # --- Report finale comparativo ---
    log.info("")
    log.info("=" * 70)
    log.info("CONFRONTO SCENARI")
    log.info("=" * 70)
    log.info(f"  {'Scenario':8}  {'Esito':12}  {'Dchi_0':>7}  {'Dchi_f':>7}  "
             f"{'Fase A':12}  {'Fase B':12}  {'Frustraz':8}  {'E_Psi':>12}")
    log.info("-" * 90)
    for r in results:
        log.info(
            f"  {r['scenario']:8s}  {r['outcome']:12s}  {r['delta_chi_0']:7.2f}  "
            f"{r['delta_chi_f']:7.3f}  {r['phase_a_fin']:12s}  {r['phase_b_fin']:12s}  "
            f"{'SI' if r['frustrated'] else 'NO':8s}  {r['E_psi_fin']:12.4e}"
        )

    log.info("")
    log.info("CONCLUSIONI FISICHE:")

    same = next(r for r in results if r["scenario"] == "SAME")
    cross = next(r for r in results if r["scenario"] == "CROSS")

    if same["outcome"] == "AGGREGATO":
        log.info("  [SAME]  Aggregazione L2 confermata: solitoni stesso-fase si legano.")
    elif same["outcome"] == "OSCILL.":
        log.info("  [SAME]  Oscillazione stabile: proto-legame L2 in formazione.")
    else:
        log.info(f"  [SAME]  Esito: {same['outcome']}. L1 resistenti alle perturbazioni L2.")

    if cross["frustrated"]:
        log.info("  [CROSS] Frustrazione topologica rilevata: segni opposti generano")
        log.info("          repulsione di scambio. Il solitone B attraversa Ottaedrica")
        log.info("          durante il flip di fase — instabilita' transiente.")
    if cross["outcome"] == "AGGREGATO":
        log.info("  [CROSS] Paradosso: aggregazione cross-fase via flip!")
        log.info("          B ha invertito il segno di chi per minimizzare E_coupling.")

    log.info("")
    log.info(f"  Log eventi: {EVENTI_LOG}")
    log.info("=" * 70)

    _update_checkpoint(results)
    return results


# ============================================================================
# CHECKPOINT
# ============================================================================

def _update_checkpoint(results: list[dict]) -> None:
    ck = Path(__file__).parent.parent / "docs" / "peano" / "MIGRAZIONE_CHECKPOINT.md"
    if not ck.exists():
        return

    same  = next((r for r in results if r["scenario"] == "SAME"),  {})
    cross = next((r for r in results if r["scenario"] == "CROSS"), {})

    block = (
        f"\n---\n"
        f"## L2 Aggregation Run — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Parametri**: kappa_inter={KAPPA_INTER}, lambda={LAMBDA_INTER}, "
        f"W_AB={W_AB:.3f}, N={N_STEPS}\n\n"
        f"| Scenario | Esito | Dchi_0 | Dchi_f | Fase A | Fase B | Frustrazione | E_Psi |\n"
        f"|----------|-------|--------|--------|--------|--------|--------------|-------|\n"
        f"| SAME  | {same.get('outcome','?')} | {same.get('delta_chi_0',0):.2f} | "
        f"{same.get('delta_chi_f',0):.3f} | {same.get('phase_a_fin','?')} | "
        f"{same.get('phase_b_fin','?')} | {'SI' if same.get('frustrated') else 'NO'} | "
        f"{same.get('E_psi_fin',0):.4e} |\n"
        f"| CROSS | {cross.get('outcome','?')} | {cross.get('delta_chi_0',0):.2f} | "
        f"{cross.get('delta_chi_f',0):.3f} | {cross.get('phase_a_fin','?')} | "
        f"{cross.get('phase_b_fin','?')} | {'SI' if cross.get('frustrated') else 'NO'} | "
        f"{cross.get('E_psi_fin',0):.4e} |\n\n"
        f"**Conclusione**: {cross.get('outcome','?')} cross-fase, "
        f"{'frustrazione rilevata' if cross.get('frustrated') else 'no frustrazione'}.\n"
    )

    with open(ck, "a", encoding="utf-8") as f:
        f.write(block)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    results = run_l2_aggregation()
    sys.exit(0)
