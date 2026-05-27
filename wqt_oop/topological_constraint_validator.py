"""
================================================================================
TOPOLOGICAL CONSTRAINT VALIDATOR - Validazione Geometrica del Manifold
================================================================================

Layer addittivo NON-INVASIVO che implementa il passaggio da validazione
energetica a validazione topologica per il manifold discreto VQT.

PARADIGM SHIFT:
--------------
PRIMA (Legacy):
  - Convergenza energetica: |ΔH/H| < threshold
  - La non-convergenza era un errore del sistema

DOPO (Topologico):
  - Validazione geometrica: Σ τᵢ ≡ 4π, ΔK alternato
  - L'espansione energetica è una caratteristica (proprietà emergente)
  - L'energia viene CATALOGATA, non usata come vincolo

VINCOLI FONDAMENTALI IMPLEMENTATI:
-----------------------------------
1. CHIUSURA SPINORIALE 720°: |Σ τᵢ mod 4π| < ε_closure
   - Derivazione: SU(2) covering group (proprietà topologica spinori fermionici)
   - Target: Σ τᵢ ≡ 0 (mod 4π)

2. DETORSIONE CON CHIRALITÀ ALTERNATA ±180°:
   - Pattern K²: K'[i] e K'[i+1] devono avere segno opposto
   - Qualità = frazione coppie adiacenti con alternanza corretta [0,1]

3. DENSITÀ DI VINCOLO ρ_constraint:
   - ρ[i] = 0.5·f_closure(i) + 0.5·f_detorsion(i)
   - Alta ρ → segmento con vincoli topologici forti → clustering materia
   - Mappa spaziale ρ sostituisce il potenziale energetico nel playback

GARANZIE ARCHITETTURALI:
------------------------
  ✓ Zero modifiche a segmento_quantistico.py
  ✓ Zero modifiche a solitone_composito.py
  ✓ Zero modifiche a abstract_soliton.py
  ✓ Zero modifiche a energy_drift_observer.py
  ✓ Proprietà simplettiche di Strang Splitting intatte
  ✓ Backward compatibility totale (sistema legacy continua a funzionare)

UTILIZZO:
---------
  validator = TopologicalConstraintValidator(universe, physics)
  state = validator.compute_constraint_state(step=0, time=0.0)
  print(state.mean_constraint_density)   # Densità vincolo media
  print(state.phase_label)               # "vacuum" / "transition" / "condensed"

================================================================================
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from .abstract_soliton import AbstractSoliton
from .solitone_composito import SolitoneComposito
from .segmento_quantistico import SegmentoQuantistico
from .physics_context import PhysicsContext
from .energy_drift_observer import Observer, SimulationState


logger = logging.getLogger(__name__)


# ============================================================================
# TOPOLOGICAL STATE SNAPSHOT
# ============================================================================

@dataclass
class TopologicalState:
    """
    Snapshot completo dello stato topologico del manifold.

    Contiene sia le metriche di vincolo (parametri di controllo primari)
    sia le energie emergenti (variabili dipendenti, NON vincoli).
    """
    step: int
    time: float

    # === VINCOLI FONDAMENTALI (parametri di controllo) ===
    closure_error_deg: float
    """Distanza dalla chiusura 720°: min(|Σ τᵢ mod 4π|, 4π - |...|) in gradi."""

    closure_error_normalized: float
    """closure_error_deg / 360° (normalizzato su mezzo giro)."""

    closure_satisfied: bool
    """True se closure_error_deg < closure_tolerance_deg."""

    detorsion_pattern_quality: float
    """Qualità pattern chiralità alternata [0,1]. 1=perfetto, 0=caotico."""

    detorsion_satisfied: bool
    """True se detorsion_pattern_quality > 0.5."""

    # === DENSITÀ DI VINCOLO (metrica per clustering materia) ===
    constraint_density: np.ndarray
    """ρ_constraint per segmento, shape (N,), range [0,1]."""

    mean_constraint_density: float
    """Media globale ρ. Indica la fase topologica corrente."""

    constraint_density_std: float
    """Deviazione standard ρ. Alta std → forte clustering (eterogeneità spaziale)."""

    # === GRADI DI LIBERTÀ ===
    N_segments: int
    """Numero totale segmenti atomici nel manifold."""

    N_dof: int
    """DOF totali = 2 * N_segments (χ, v per segmento)."""

    # === ENERGIE EMERGENTI (variabili dipendenti, NON vincoli) ===
    H_total_emergent: float
    """Energia totale: proprietà EMERGENTE dalla geometria, non parametro di controllo."""

    H_torsion_emergent: float
    """Energia di torsione emergente (H_coupling)."""

    # === DIAGNOSTICA TOPOLOGICA ===
    topology_charge: float
    """Carica topologica conservata Σ χᵢ."""

    phase_label: str
    """Fase topologica: 'vacuum', 'transition', o 'condensed'."""

    transition_detected: bool
    """True se rilevata transizione di fase in questa step."""


# ============================================================================
# CORE VALIDATOR
# ============================================================================

class TopologicalConstraintValidator:
    """
    Validatore vincoli topologici per manifold frattale VQT.

    Sostituisce il monitoraggio energetico con validazione geometrica
    basata su vincoli spinoriali (720°) e di detorsione (±180°).

    Questo validator è un LAYER PASSIVO: legge lo stato del manifold
    tramite le interfacce esistenti (get_auxiliary_state, get_position)
    senza mai scrivere su di esso.
    """

    # Soglie di fase topologica
    PHASE_VACUUM = 0.3      # ρ < 0.3: vincoli deboli, espansione
    PHASE_TRANSITION = 0.6  # 0.3 ≤ ρ < 0.6: fase intermedia
    # ρ ≥ 0.6: materia condensata ("condensed")

    def __init__(
        self,
        universe: AbstractSoliton,
        physics: PhysicsContext,
        closure_tolerance_deg: float = 10.0,
        detorsion_tolerance_deg: float = 30.0,
        max_history_length: int = 100
    ):
        """
        Parameters
        ----------
        universe : AbstractSoliton
            Universo frattale da validare (letto passivamente).
        physics : PhysicsContext
            Contesto fisico (usato per parametri di scala).
        closure_tolerance_deg : float
            Tolleranza vincolo chiusura 720° [gradi].
        detorsion_tolerance_deg : float
            Tolleranza pattern detorsione [gradi].
        max_history_length : int
            Lunghezza massima della finestra storia stati.
        """
        self.universe = universe
        self.physics = physics
        self.closure_tolerance_deg = closure_tolerance_deg
        self.detorsion_tolerance_deg = detorsion_tolerance_deg
        self.max_history_length = max_history_length

        self.state_history: List[TopologicalState] = []

        logger.info("TopologicalConstraintValidator initialized")
        logger.info(f"  Closure tolerance:   ±{closure_tolerance_deg:.1f}°")
        logger.info(f"  Detorsion tolerance: ±{detorsion_tolerance_deg:.1f}°")

    # ------------------------------------------------------------------
    # a) DOF in tempo reale
    # ------------------------------------------------------------------

    def compute_dof(self, N_segments: int) -> int:
        """
        Calcola gradi di libertà in tempo reale.

        DOF(N) = 2 · N     (χ, v per ogni voxel)

        Scaling gerarchico:
          Livello 0: DOF = 2 · 24⁰ = 2
          Livello 1: DOF = 2 · 24¹ = 48
          Livello 2: DOF = 2 · 24² = 1152
          Livello N: DOF = 2 · 24ᴺ

        Parameters
        ----------
        N_segments : int
            Numero voxel attivi.

        Returns
        -------
        int
            Gradi di libertà totali.
        """
        return 2 * N_segments

    # ------------------------------------------------------------------
    # b) Vincolo chiusura spinoriale 720°
    # ------------------------------------------------------------------

    def check_closure_constraint(
        self,
        tau_values: np.ndarray
    ) -> Tuple[float, float, bool]:
        """
        Verifica vincolo chiusura spinoriale: Σ τᵢ ≡ 0 (mod 4π).

        Un solitone fermionico è topologicamente stabile se e solo se
        la somma dei tempi propri locali è un multiplo di 4π (720°).

        Derivazione:
          - Spinori SU(2): periodicità 4π (non 2π come i bosoni)
          - Chiusura a 720° = invarianza rispetto a rotazione completa

        Parameters
        ----------
        tau_values : ndarray
            Tempi propri locali τᵢ [rad], shape (N,).

        Returns
        -------
        total_closure_rad : float
            Σ τᵢ totale [rad].
        error_deg : float
            Distanza dalla multipla di 4π più vicina [gradi].
        is_satisfied : bool
            True se vincolo soddisfatto entro tolleranza.
        """
        four_pi = 4.0 * np.pi
        total_rad = float(np.sum(tau_values))

        residual = total_rad % four_pi
        # Prendi distanza minima: min(residual, 4π - residual)
        error_rad = min(residual, four_pi - residual)
        error_deg = float(np.degrees(error_rad))

        is_satisfied = error_deg < self.closure_tolerance_deg
        return total_rad, error_deg, is_satisfied

    # ------------------------------------------------------------------
    # b) Vincolo detorsione ±180°
    # ------------------------------------------------------------------

    def check_detorsion_pattern(
        self,
        K_squared_values: np.ndarray
    ) -> Tuple[float, bool]:
        """
        Verifica pattern detorsione con chiralità alternata ±180°.

        Il pattern ottimale è: K²[0] alto, K²[1] basso, K²[2] alto, ...
        ovvero le differenze prime di K² devono alternare di segno.

        Metrica:
          quality = (# coppie adiacenti con alternanza) / (# coppie totali)

        Returns
        -------
        quality : float
            Qualità pattern [0, 1]. 1 = perfetto.
        is_satisfied : bool
            True se quality > 0.5.
        """
        N = len(K_squared_values)
        if N < 3:
            return 1.0, True

        K_diff = np.diff(K_squared_values)
        if len(K_diff) < 2:
            return 1.0, True

        # Prodotto di differenze consecutive: negativo = alternanza
        products = K_diff[:-1] * K_diff[1:]
        n_alternating = int(np.sum(products < 0))
        quality = float(n_alternating) / float(len(products))

        is_satisfied = quality > 0.5
        return quality, is_satisfied

    # ------------------------------------------------------------------
    # c) Densità di vincolo spaziale
    # ------------------------------------------------------------------

    def compute_constraint_density(
        self,
        positions: np.ndarray,
        tau_values: np.ndarray,
        K_squared_values: np.ndarray,
        neighborhood_radius: Optional[float] = None
    ) -> np.ndarray:
        """
        Calcola densità di vincolo locale per ogni segmento.

        Formula:
          ρ[i] = 0.5 · f_closure(i) + 0.5 · f_detorsion(i)

        dove:
          f_closure[i]   = contributo locale al vincolo 720°
                           (unifomità τ nel vicinato)
          f_detorsion[i] = smoothness locale di K²
                           (qualità pattern ±90° nel vicinato)

        Interpretazione fisica:
          - Alta ρ → segmento con vincoli topologici forti
          - Clustering materia = regioni ad alta densità vincolo
          - Mappa ρ sostituisce il potenziale energetico nel playback

        Parameters
        ----------
        positions : ndarray, shape (N, 3)
        tau_values : ndarray, shape (N,)
        K_squared_values : ndarray, shape (N,)
        neighborhood_radius : float, optional
            Raggio vicinato [stessa unità di positions].
            Se None, stimato da nearest-neighbor medio.

        Returns
        -------
        rho : ndarray, shape (N,), dtype float64, range [0, 1]
        """
        N = len(positions)
        if N == 0:
            return np.array([], dtype=np.float64)
        if N == 1:
            return np.array([1.0], dtype=np.float64)

        # --- Auto-stima neighborhood_radius ---
        if neighborhood_radius is None:
            neighborhood_radius = self._estimate_neighborhood_radius(positions)

        # --- Contributo chiusura (f_closure) ---
        # Uniformità di τ: deviazione normalizzata dalla media
        tau_range = float(np.ptp(tau_values))
        if tau_range < 1e-12:
            f_closure = np.ones(N, dtype=np.float64)
        else:
            tau_mean = float(np.mean(tau_values))
            f_closure = 1.0 - np.clip(
                np.abs(tau_values - tau_mean) / tau_range, 0.0, 1.0
            )

        # --- Contributo detorsione (f_detorsion) ---
        f_detorsion = self._compute_local_detorsion(
            positions, K_squared_values, neighborhood_radius
        )

        rho = 0.5 * f_closure + 0.5 * f_detorsion
        return np.clip(rho, 0.0, 1.0)

    def _estimate_neighborhood_radius(self, positions: np.ndarray) -> float:
        """Stima il raggio di vicinato come 2× distanza nearest-neighbor media."""
        try:
            from scipy.spatial import cKDTree
            tree = cKDTree(positions)
            k = min(2, len(positions))
            dists, _ = tree.query(positions, k=k)
            nn_col = dists[:, 1] if k > 1 else dists[:, 0]
            return float(np.mean(nn_col)) * 2.0
        except Exception:
            return 1.0

    def _compute_local_detorsion(
        self,
        positions: np.ndarray,
        K_squared_values: np.ndarray,
        neighborhood_radius: float
    ) -> np.ndarray:
        """
        Smoothness locale di K² per ogni segmento.

        f_detorsion[i] = 1 / (1 + CV_local)
        dove CV_local = σ(K²_hood) / μ(K²_hood) è il coefficiente di variazione.
        """
        N = len(positions)
        f_detorsion = np.ones(N, dtype=np.float64)

        try:
            from scipy.spatial import cKDTree
            tree = cKDTree(positions)
            neighbors_list = tree.query_ball_tree(tree, neighborhood_radius)

            for i, hood_indices in enumerate(neighbors_list):
                if len(hood_indices) <= 1:
                    continue
                K_local = K_squared_values[list(hood_indices)]
                K_mean = float(np.mean(K_local))
                if K_mean > 1e-12:
                    CV = float(np.std(K_local)) / K_mean
                    f_detorsion[i] = 1.0 / (1.0 + CV)

        except ImportError:
            # Fallback senza scipy: usa indici lineari come proxy di vicinanza
            window = max(1, int(neighborhood_radius))
            for i in range(N):
                hood = list(range(max(0, i - window), min(N, i + window + 1)))
                if len(hood) <= 1:
                    continue
                K_local = K_squared_values[hood]
                K_mean = float(np.mean(K_local))
                if K_mean > 1e-12:
                    CV = float(np.std(K_local)) / K_mean
                    f_detorsion[i] = 1.0 / (1.0 + CV)

        return f_detorsion

    # ------------------------------------------------------------------
    # Classificazione fase
    # ------------------------------------------------------------------

    def classify_phase(self, mean_density: float) -> str:
        """
        Classifica la fase topologica dalla densità vincolo media.

        Returns
        -------
        str
            'vacuum' | 'transition' | 'condensed'
        """
        if mean_density < self.PHASE_VACUUM:
            return "vacuum"
        elif mean_density < self.PHASE_TRANSITION:
            return "transition"
        else:
            return "condensed"

    # ------------------------------------------------------------------
    # Rilevamento transizioni di fase
    # ------------------------------------------------------------------

    def detect_phase_transition(
        self,
        current_state: TopologicalState,
        window_size: int = 10
    ) -> bool:
        """
        Rileva transizioni di fase topologica nella finestra temporale.

        Criteri (OR logico):
          1. Il phase_label è cambiato rispetto all'ultimo stato noto
          2. Salto brusco |Δρ_mean| > 0.15 nella finestra

        Parameters
        ----------
        current_state : TopologicalState
            Stato corrente (NON ancora in state_history).
        window_size : int
            Dimensione finestra analisi.

        Returns
        -------
        bool
            True se transizione rilevata.
        """
        n_hist = len(self.state_history)
        if n_hist < 2:
            return False

        window = self.state_history[-min(window_size, n_hist):]

        # Criterio 1: cambio etichetta fase
        last_phase = window[-1].phase_label
        if current_state.phase_label != last_phase:
            logger.info(
                f"PHASE TRANSITION detected at step {current_state.step}: "
                f"{last_phase} → {current_state.phase_label}"
            )
            return True

        # Criterio 2: salto brusco densità
        prev_densities = [s.mean_constraint_density for s in window]
        delta_rho = abs(
            current_state.mean_constraint_density - float(np.mean(prev_densities))
        )
        if delta_rho > 0.15:
            logger.info(
                f"DENSITY JUMP detected at step {current_state.step}: "
                f"Δρ = {delta_rho:.3f}"
            )
            return True

        return False

    # ------------------------------------------------------------------
    # Snapshot completo
    # ------------------------------------------------------------------

    def compute_constraint_state(self, step: int, time: float) -> TopologicalState:
        """
        Calcola lo snapshot topologico completo del manifold.

        Workflow:
          1. Estrae τᵢ, K²ᵢ, posizioni da interfacce esistenti
          2. Verifica vincoli 720° e ±180°
          3. Calcola densità vincolo ρ per ogni segmento
          4. Classifica fase topologica
          5. Cataloga energie emergenti (NON usate come vincoli)
          6. Rileva transizioni di fase

        Parameters
        ----------
        step : int
            Step simulazione corrente.
        time : float
            Tempo fisico [unità Planck].

        Returns
        -------
        TopologicalState
        """
        # 1. Geometria
        aux = self.universe.get_auxiliary_state()
        tau_values = aux['tau_locale']
        K_squared = aux['contorsione']
        positions = self._extract_all_positions(self.universe)
        N_segments = len(positions)

        # 2. Vincolo chiusura 720°
        _, closure_err_deg, closure_ok = self.check_closure_constraint(tau_values)
        closure_normalized = closure_err_deg / 360.0

        # 3. Vincolo detorsione ±180°
        detorsion_quality, detorsion_ok = self.check_detorsion_pattern(K_squared)

        # 4. Densità vincolo
        rho = self.compute_constraint_density(positions, tau_values, K_squared)
        rho_mean = float(np.mean(rho)) if len(rho) > 0 else 0.0
        rho_std = float(np.std(rho)) if len(rho) > 0 else 0.0

        # 5. DOF
        N_dof = self.compute_dof(N_segments)

        # 6. Energie emergenti (catalogazione, NON vincoli)
        H_total = float(self.universe.energia_totale)
        H_torsion = float(self.universe.compute_hamiltonian_coupling())
        Q_topo = float(self.universe.get_topology_charge())

        # 7. Fase
        phase = self.classify_phase(rho_mean)

        state = TopologicalState(
            step=step,
            time=time,
            closure_error_deg=closure_err_deg,
            closure_error_normalized=closure_normalized,
            closure_satisfied=closure_ok,
            detorsion_pattern_quality=detorsion_quality,
            detorsion_satisfied=detorsion_ok,
            constraint_density=rho,
            mean_constraint_density=rho_mean,
            constraint_density_std=rho_std,
            N_segments=N_segments,
            N_dof=N_dof,
            H_total_emergent=H_total,
            H_torsion_emergent=H_torsion,
            topology_charge=Q_topo,
            phase_label=phase,
            transition_detected=False,  # aggiornato sotto
        )

        # 8. Transizione (richiede storia precedente, quindi dopo aver costruito state)
        state.transition_detected = self.detect_phase_transition(state)

        # Aggiorna storia
        self.state_history.append(state)
        if len(self.state_history) > self.max_history_length:
            self.state_history.pop(0)

        return state

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _extract_all_positions(self, soliton: AbstractSoliton) -> np.ndarray:
        """Estrae posizioni di tutti i segmenti atomici (ricorsivo sul Composite)."""
        if isinstance(soliton, SegmentoQuantistico):
            return soliton.position.reshape(1, 3)
        elif isinstance(soliton, SolitoneComposito):
            parts = [self._extract_all_positions(child) for child in soliton.children]
            return np.vstack(parts)
        else:
            return np.zeros((1, 3), dtype=np.float64)

    def get_summary(self, state: TopologicalState) -> str:
        """Genera riassunto testuale dello stato topologico."""
        c_ok = "OK" if state.closure_satisfied else "VIOLATED"
        d_ok = "OK" if state.detorsion_satisfied else "LOW"
        t_flag = " [TRANSITION DETECTED]" if state.transition_detected else ""

        return (
            f"\n{'='*60}\n"
            f"TOPOLOGICAL STATE  step={state.step}  t={state.time:.3f}\n"
            f"{'='*60}\n"
            f"Phase:              {state.phase_label.upper()}{t_flag}\n"
            f"DOF:                {state.N_dof}  (N={state.N_segments} segments)\n"
            f"Closure 720°:       err={state.closure_error_deg:.2f}°  [{c_ok}]\n"
            f"Detorsion ±180°:    quality={state.detorsion_pattern_quality:.3f}  [{d_ok}]\n"
            f"Constraint ρ:       μ={state.mean_constraint_density:.3f}  "
            f"σ={state.constraint_density_std:.3f}\n"
            f"Emergent H_total:   {state.H_total_emergent:.4e}  (not a control param)\n"
            f"Emergent H_torsion: {state.H_torsion_emergent:.4e}\n"
            f"Topology charge Q:  {state.topology_charge:.4f}\n"
            f"{'='*60}"
        )


# ============================================================================
# OBSERVER: SOSTITUISCE ENERGY LOGGING CON CONSTRAINT-DENSITY LOGGING
# ============================================================================

class TopologicalConstraintObserver(Observer):
    """
    Observer che sostituisce il logging energetico con il logging
    della Densità di Vincolo topologica.

    Si integra nel pattern Observer esistente (energy_drift_observer.py)
    senza modificarlo: implementa la stessa interfaccia Observer.

    Sostituzione:
      PRIMA: log |ΔH/H| (drift energia)
      DOPO:  log ρ_constraint (densità vincolo)
    """

    def __init__(
        self,
        validator: TopologicalConstraintValidator,
        log_interval: int = 10,
        verbose_interval: int = 100
    ):
        """
        Parameters
        ----------
        validator : TopologicalConstraintValidator
        log_interval : int
            Log compatto ogni N steps.
        verbose_interval : int
            Log completo (summary) ogni N steps.
        """
        self.validator = validator
        self.log_interval = log_interval
        self.verbose_interval = verbose_interval
        self.logged_states: List[TopologicalState] = []

    def on_simulation_start(self):
        self.logged_states.clear()
        logger.info("TopologicalConstraintObserver: ACTIVE")
        logger.info("  Energy drift monitoring:   DISABLED (emergent property)")
        logger.info("  Constraint density logging: ENABLED")

    def update(self, state: SimulationState):
        """
        Callback per ogni step simulazione.

        Logga ρ_constraint invece di |ΔH/H|.
        Identifica automaticamente le transizioni di fase.
        """
        if state.step % self.log_interval != 0:
            return

        topo = self.validator.compute_constraint_state(
            step=state.step,
            time=state.time
        )
        self.logged_states.append(topo)

        # Log compatto (sostituisce il log drift energetico)
        logger.info(
            f"Step {state.step:6d} | t={state.time:8.3f} | "
            f"ρ={topo.mean_constraint_density:.3f}±{topo.constraint_density_std:.3f} | "
            f"phase={topo.phase_label:10s} | "
            f"closure_err={topo.closure_error_deg:5.1f}° | "
            f"H_emergent={topo.H_total_emergent:.3e}"
        )

        # Log verbose periodico
        if state.step % self.verbose_interval == 0:
            logger.info(self.validator.get_summary(topo))

        # Alert transizione di fase
        if topo.transition_detected:
            logger.warning(
                f"TOPOLOGICAL PHASE TRANSITION at step {state.step}: "
                f"→ {topo.phase_label.upper()}  "
                f"(ρ={topo.mean_constraint_density:.3f})"
            )

    def on_simulation_end(self):
        n = len(self.logged_states)
        logger.info(f"TopologicalConstraintObserver: {n} states logged")
        if n > 0:
            logger.info(self.validator.get_summary(self.logged_states[-1]))

    def export_to_dict(self) -> Dict:
        """
        Esporta storia completa in formato dizionario (compatibile con HDF5).

        Chiavi restituite:
          step, time,
          closure_error_deg, closure_satisfied,
          detorsion_quality, detorsion_satisfied,
          mean_constraint_density, constraint_density_std,
          N_dof, N_segments,
          H_total_emergent, H_torsion_emergent,
          topology_charge, phase_label, transition_detected
        """
        if not self.logged_states:
            return {}

        return {
            'step': np.array([s.step for s in self.logged_states], dtype=np.int64),
            'time': np.array([s.time for s in self.logged_states], dtype=np.float64),
            'closure_error_deg': np.array(
                [s.closure_error_deg for s in self.logged_states], dtype=np.float64
            ),
            'closure_satisfied': np.array(
                [s.closure_satisfied for s in self.logged_states], dtype=bool
            ),
            'detorsion_quality': np.array(
                [s.detorsion_pattern_quality for s in self.logged_states], dtype=np.float64
            ),
            'detorsion_satisfied': np.array(
                [s.detorsion_satisfied for s in self.logged_states], dtype=bool
            ),
            'mean_constraint_density': np.array(
                [s.mean_constraint_density for s in self.logged_states], dtype=np.float64
            ),
            'constraint_density_std': np.array(
                [s.constraint_density_std for s in self.logged_states], dtype=np.float64
            ),
            'N_dof': np.array([s.N_dof for s in self.logged_states], dtype=np.int64),
            'N_segments': np.array(
                [s.N_segments for s in self.logged_states], dtype=np.int64
            ),
            'H_total_emergent': np.array(
                [s.H_total_emergent for s in self.logged_states], dtype=np.float64
            ),
            'H_torsion_emergent': np.array(
                [s.H_torsion_emergent for s in self.logged_states], dtype=np.float64
            ),
            'topology_charge': np.array(
                [s.topology_charge for s in self.logged_states], dtype=np.float64
            ),
            'phase_label': np.array(
                [s.phase_label for s in self.logged_states], dtype='S16'
            ),
            'transition_detected': np.array(
                [s.transition_detected for s in self.logged_states], dtype=bool
            ),
        }
