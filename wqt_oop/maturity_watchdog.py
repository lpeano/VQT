"""
================================================================================
MATURITY WATCHDOG - Autotuning della Maturità + Spettroscopia del Manifold
================================================================================

Il watchdog opera in due fasi:

  FASE 1 — SPETTROSCOPIA (step 0 … spectral_min_steps):
    Accumula σ(ρ) = constraint_density_std e, al raggiungimento di
    spectral_min_steps campioni, esegue una FFT per estrarre la firma
    dinamica del manifold:
      • f_dom   — frequenza di risonanza dominante [1/Planck]
      • T_dom   — periodo fondamentale [Planck]
      • W_auto  — finestra di maturità auto-sintonizzata = factor × T_dom/dt

    Questo trasforma il generatore in un "analizzatore di spettro in situ":
    le oscillazioni di σ(ρ) non sono rumore da abbattere ma la firma
    topologica del livello. Ogni file HDF5 contiene la carta d'identità
    dinamica del manifold.

  FASE 2 — MATURITÀ [Eq. WD-1] (dopo la spettroscopia):
    Usa W_auto (armonizzato con la fisica) per verificare:
      1. |d/dt σ(ρ)| < ε_norm  per W_auto step consecutivi
      2. std(H_window)/|mean(H)| < H_rel_tol  (H in oscillazione stazionaria)

INVARIANZA DI SCALA:
    ε_norm = ε / √N_dof
    Garantisce sensibilità uniforme tra L1 (N_dof=48) e L6 (N_dof≈382M).

METADATI HDF5:
    Tutti i risultati (spettro + maturità) vengono salvati nel gruppo
    /maturity del file HDF5, consentendo:
      • Correlazione tra teoria (torsore, vincoli) e dinamica osservata
      • Rilevamento di leggi di scala f_dom(L) tra livelli frattali
      • Validazione automatica delle modifiche fisiche

================================================================================
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# MATURITY WATCHDOG
# ============================================================================

class MaturityWatchdog:
    """
    Watchdog di maturità spaziale con spettroscopia integrata per simulazioni VQT.

    Fase 1 — Spettroscopia: analizza FFT di σ(ρ) per estrarre f_dom e T_dom,
    poi auto-sintonizza W = spectral_tune_factor × T_dom / dt.

    Fase 2 — Maturità: verifica |d/dt σ(ρ)| < ε_norm per W consecutivi
    (condizione armonizzata con la fisica del manifold).

    Parameters
    ----------
    window_size : int
        W iniziale (usato se auto_tune_window=False o prima della spettroscopia).
    convergence_threshold : float
        ε — soglia su |d/dt σ(ρ)| [Planck⁻¹]. Normalizzata: ε_norm = ε/√N_dof.
    n_dof : int
        N_dof = 2 × N_segments del livello corrente.
    dt : float
        Passo temporale [unità Planck].
    H_osc_window : int
        Finestra per stazionarietà di H_emergent.
    H_rel_tol : float
        Tolleranza relativa H: std(H)/|mean(H)| < tol.
    auto_tune_window : bool
        Se True, W viene auto-sintonizzato da T_dom dopo la spettroscopia.
    spectral_min_steps : int
        Step minimi di accumulo prima della FFT. Devono coprire almeno
        2 periodi attesi (default 200 = sicuro per T_dom ≲ 1 Planck).
    spectral_tune_factor : float
        W_auto = factor × T_dom / dt. Default 0.75 (< 1 periodo per trovare
        le finestre di quiete senza aspettare un ciclo completo).
    """

    def __init__(
        self,
        window_size: int = 50,
        convergence_threshold: float = 1e-4,
        n_dof: int = 1,
        dt: float = 0.01,
        H_osc_window: int = 20,
        H_rel_tol: float = 0.10,
        auto_tune_window: bool = True,
        spectral_min_steps: int = 200,
        spectral_tune_factor: float = 0.75,
    ):
        self.W = window_size
        self.epsilon_raw = convergence_threshold
        self.n_dof = max(n_dof, 1)
        self.dt = dt
        self.H_rel_tol = H_rel_tol
        self.auto_tune_window = auto_tune_window
        self.spectral_min_steps = spectral_min_steps
        self.spectral_tune_factor = spectral_tune_factor

        # ε normalizzato: scala con 1/√N_dof (TCL — incertezza di σ come stimatore)
        self.epsilon_norm = convergence_threshold / np.sqrt(self.n_dof)

        # Finestre mobili (maturità)
        self._sigma_window: deque = deque(maxlen=window_size + 1)
        self._H_window: deque = deque(maxlen=H_osc_window)

        # Storia completa per FFT (cresce fino a spectral_min_steps, poi si ferma)
        self._sigma_full: list = []

        # Stato watchdog
        self._consecutive: int = 0
        self._is_mature: bool = False
        self.total_steps_fed: int = 0
        self.maturity_step: Optional[int] = None

        # Spettroscopia
        self._spectral_done: bool = False
        self._spectral_result: dict = {}
        self._W_before_tune: int = window_size  # per logging

        logger.info(
            f"MaturityWatchdog  W_init={window_size}  ε={convergence_threshold:.2e}  "
            f"N_dof={n_dof}  ε_norm={self.epsilon_norm:.2e}  "
            f"auto_tune={'ON' if auto_tune_window else 'OFF'}  "
            f"spectral_min={spectral_min_steps}"
        )

    # ------------------------------------------------------------------
    # Aggiornamento principale
    # ------------------------------------------------------------------

    def update(self, topo_state, step_idx: int) -> bool:
        """
        Aggiorna il watchdog con il TopologicalState del passo corrente.

        Workflow:
          1. Accumula σ(ρ) nella storia completa (per FFT).
          2. Al raggiungimento di spectral_min_steps, esegue analyze_spectral_signature()
             e (se auto_tune_window) aggiorna W.
          3. Controlla la condizione di maturità con W corrente.

        Returns True se la maturità è appena dichiarata o già raggiunta.
        """
        sigma = float(topo_state.constraint_density_std)
        H = float(topo_state.H_total_emergent)

        self._sigma_window.append(sigma)
        self._H_window.append(H)
        self.total_steps_fed += 1

        # Accumula storia completa finché non serve per FFT
        if len(self._sigma_full) < self.spectral_min_steps:
            self._sigma_full.append(sigma)

        if self._is_mature:
            return True

        # --- FASE 1: spettroscopia al raggiungimento del minimo di campioni ---
        if (self.auto_tune_window
                and not self._spectral_done
                and self.total_steps_fed >= self.spectral_min_steps):
            self._spectral_result = self._analyze_spectral_signature()
            self._spectral_done = True
            T_dom = self._spectral_result.get("oscillation_period_planck", 0.0)
            if T_dom > 0:
                W_new = max(10, int(self.spectral_tune_factor * T_dom / self.dt))
                self._W_before_tune = self.W
                self.W = W_new
                # Ridimensiona la finestra mantenendo i dati recenti
                recent = list(self._sigma_window)[-(W_new + 1):]
                self._sigma_window = deque(recent, maxlen=W_new + 1)
                logger.info(
                    f"[WATCHDOG SPECTRAL] f_dom={self._spectral_result['dominant_frequency']:.4f} [1/Planck]  "
                    f"T_dom={T_dom:.3f} Planck  "
                    f"W: {self._W_before_tune} → {W_new}  "
                    f"(factor={self.spectral_tune_factor})"
                )
            else:
                self._spectral_done = True
                logger.warning("[WATCHDOG SPECTRAL] Frequenza dominante non determinabile — W invariato.")

        # In fase di accumulo spettrale: non ancora in grado di valutare maturità
        if self.auto_tune_window and not self._spectral_done:
            return False

        # --- FASE 2: verifica maturità ---
        if len(self._sigma_window) < 2:
            return False

        dsigma_dt = abs(self._sigma_window[-1] - self._sigma_window[-2]) / self.dt
        sigma_ok = dsigma_dt < self.epsilon_norm
        H_ok = self._H_stationary()

        if sigma_ok and H_ok:
            self._consecutive += 1
        else:
            self._consecutive = 0

        if self._consecutive >= self.W:
            self._is_mature = True
            self.maturity_step = step_idx
            logger.info(
                f"[WATCHDOG] Maturità dichiarata al step {step_idx + 1}  "
                f"|dσ/dt|={dsigma_dt:.3e} < ε_norm={self.epsilon_norm:.3e}  "
                f"H_stat={H_ok}  streak={self._consecutive}/{self.W}"
            )

        return self._is_mature

    # ------------------------------------------------------------------
    # Spettroscopia FFT
    # ------------------------------------------------------------------

    def _analyze_spectral_signature(self) -> dict:
        """
        FFT di σ(ρ) per estrarre la firma dinamica del manifold.

        Restituisce un dizionario con:
          - dominant_frequency [1/Planck]
          - oscillation_period_planck [Planck]
          - oscillation_period_steps [int]
          - dominant_power_fraction (power del picco / power totale)
          - spectral_entropy (misura di complessità spettrale)
          - W_auto (finestra di maturità auto-sintonizzata)
          - N_samples_analyzed
        """
        sigma_arr = np.asarray(self._sigma_full, dtype=float)
        N = len(sigma_arr)

        if N < 4:
            return {}

        # Rimuovi trend lineare e media (detrend)
        trend = np.polyfit(np.arange(N), sigma_arr, 1)
        sigma_detrended = sigma_arr - np.polyval(trend, np.arange(N))

        # FFT
        fft_vals = np.fft.rfft(sigma_detrended)
        fft_freq = np.fft.rfftfreq(N, d=self.dt)
        power = np.abs(fft_vals) ** 2

        # Escludi componente DC
        power[0] = 0.0
        total_power = float(power.sum())

        # Frequenza dominante
        dom_idx = int(np.argmax(power))
        dom_freq = float(fft_freq[dom_idx])
        dom_period = (1.0 / dom_freq) if dom_freq > 0 else float("inf")
        dom_power_frac = float(power[dom_idx] / (total_power + 1e-30))

        # Entropia spettrale (misura quanti modi contribuiscono)
        p_norm = power / (total_power + 1e-30)
        p_pos = p_norm[p_norm > 1e-15]
        spectral_entropy = float(-np.sum(p_pos * np.log(p_pos)))

        # W auto-sintonizzato
        W_auto = (max(10, int(self.spectral_tune_factor * dom_period / self.dt))
                  if dom_freq > 0 else self.W)

        # Top-3 frequenze per i metadati
        top3_idx = np.argsort(power)[::-1][:3]
        top3_freqs = [float(fft_freq[i]) for i in top3_idx if fft_freq[i] > 0]
        top3_periods = [1.0 / f for f in top3_freqs]

        result = {
            "dominant_frequency":          dom_freq,
            "oscillation_period_planck":   dom_period,
            "oscillation_period_steps":    int(dom_period / self.dt) if dom_freq > 0 else -1,
            "dominant_power_fraction":     dom_power_frac,
            "spectral_entropy":            spectral_entropy,
            "N_samples_analyzed":          N,
            "W_auto_tuned":                W_auto,
            "top3_frequencies":            top3_freqs,
            "top3_periods_planck":         top3_periods,
        }

        logger.info(
            f"[WATCHDOG SPECTRAL] Firma dinamica L (N_dof={self.n_dof}):\n"
            f"  f_dom={dom_freq:.5f} [1/Planck]  T_dom={dom_period:.4f} Planck  "
            f"({int(dom_period/self.dt)} step)\n"
            f"  Potenza dominante: {dom_power_frac*100:.1f}%  "
            f"Entropia spettrale: {spectral_entropy:.3f}\n"
            f"  Top-3 periodi: {[f'{p:.3f}' for p in top3_periods[:3]]} Planck"
        )

        return result

    # ------------------------------------------------------------------
    # Stazionarietà H
    # ------------------------------------------------------------------

    def _H_stationary(self) -> bool:
        if len(self._H_window) < 3:
            return True
        H_arr = np.asarray(self._H_window)
        mean_H = np.mean(np.abs(H_arr))
        if mean_H < 1e-30:
            return True
        return float(np.std(H_arr)) / mean_H < self.H_rel_tol

    # ------------------------------------------------------------------
    # Proprietà di stato
    # ------------------------------------------------------------------

    def is_mature(self) -> bool:
        return self._is_mature

    def is_spectral_done(self) -> bool:
        return self._spectral_done

    def maturity_percentage(self) -> float:
        """Avanzamento verso maturità [0–100%]. Prima della spettroscopia: progresso accumulazione."""
        if self._is_mature:
            return 100.0
        if not self._spectral_done:
            # Mostra avanzamento accumulazione spettrale
            return min(49.9, 50.0 * self.total_steps_fed / self.spectral_min_steps)
        if len(self._sigma_window) < 2:
            return 50.0
        return 50.0 + min(49.9, 50.0 * self._consecutive / self.W)

    def get_sigma_derivative(self) -> float:
        if len(self._sigma_window) < 2:
            return float("inf")
        return abs(self._sigma_window[-1] - self._sigma_window[-2]) / self.dt

    def get_maturity_cost(self) -> int:
        if self.maturity_step is not None:
            return self.maturity_step + 1
        return self.total_steps_fed

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_status_line(self) -> str:
        """Riga di stato compatta per logging console."""
        pct = self.maturity_percentage()
        dsdt = self.get_sigma_derivative()
        H_ok = self._H_stationary()
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)

        if not self._spectral_done:
            phase = f"[SPECTRAL {self.total_steps_fed}/{self.spectral_min_steps}]"
        else:
            f_dom = self._spectral_result.get("dominant_frequency", 0.0)
            T_dom = self._spectral_result.get("oscillation_period_planck", 0.0)
            phase = f"f={f_dom:.3f}Hz T={T_dom:.2f}P"

        return (
            f"Maturity: {pct:5.1f}%  [{bar}]  "
            f"|dσ/dt|={dsdt:.2e}  ε_norm={self.epsilon_norm:.2e}  "
            f"streak={self._consecutive}/{self.W}  "
            f"H={'OK' if H_ok else 'NO'}  {phase}"
        )

    def get_metadata_dict(self) -> dict:
        """
        Dizionario completo per il gruppo /maturity nell'HDF5.

        Contiene parametri watchdog, risultati spettroscopia e costo di maturità.
        Chiavi con prefisso 'spectral_' sono la firma dinamica del manifold.
        """
        base = {
            # Parametri watchdog
            "watchdog_enabled":           True,
            "watchdog_window_size_init":  self._W_before_tune,
            "watchdog_window_size_used":  self.W,
            "watchdog_epsilon_raw":       self.epsilon_raw,
            "watchdog_epsilon_norm":      self.epsilon_norm,
            "watchdog_n_dof":             self.n_dof,
            "watchdog_dt":                self.dt,
            "watchdog_H_rel_tol":         self.H_rel_tol,
            "watchdog_auto_tune":         int(self.auto_tune_window),
            "watchdog_spectral_min_steps": self.spectral_min_steps,
            "watchdog_spectral_tune_factor": self.spectral_tune_factor,
            # Risultati maturità
            "maturity_cost_steps":        self.get_maturity_cost(),
            "maturity_declared":          int(self._is_mature),
            "maturity_step":              self.maturity_step if self.maturity_step is not None else -1,
            "maturity_percentage_final":  self.maturity_percentage(),
        }

        # Firma spettrale (se disponibile)
        if self._spectral_result:
            for k, v in self._spectral_result.items():
                if isinstance(v, list):
                    # Liste → stringa per compatibilità attrs HDF5
                    base[f"spectral_{k}"] = str(v)
                else:
                    base[f"spectral_{k}"] = v

        return base
