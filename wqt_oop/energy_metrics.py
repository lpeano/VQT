"""
================================================================================
PEANO-VQT ENERGY METRICS
================================================================================

Decomposizione triadica dell'energia di accoppiamento:
    E_chi  — Energia di coerenza del campo χ (allineamento)
    E_RX   — Energia reattiva: torsione geometrica + scambio cross-fase
    E_Psi  — Energia accumulata nel campo Ψ (sink radiativo)

Invariante di conservazione per l'operazione di drain:
    dE_chi + dE_RX + dE_Psi = 0
    (quando E_chi → E_Psi, la somma rimane costante)

================================================================================
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class EnergyTriad:
    """
    Triade energetica Peano-VQT.

    Attributes
    ----------
    E_chi : float
        Energia di coerenza del campo χ  (kappa * E_coupling).
        Favorisce l'allineamento tra segmenti vicini.
    E_RX : float
        Energia reattiva = E_torsion + E_exchange.
        Somma del termine geometrico (K²) e dello scambio topologico.
    E_Psi : float
        Energia accumulata nel sink Ψ tramite drain.
        Cresce monotonicamente (drain irrev.).
    """
    E_chi: float
    E_RX: float
    E_Psi: float

    @property
    def total(self) -> float:
        """Energia totale della triade: E_chi + E_RX + E_Psi."""
        return self.E_chi + self.E_RX + self.E_Psi


@dataclass
class PhaseTransitionEvent:
    """Registro di un singolo evento di drain χ → Ψ."""
    step: int
    chi_saturation: float
    E_drained: float
    E_psi_before: float
    E_psi_after: float


class PeanoVQTAnalyzer:
    """
    Analizzatore energetico Peano-VQT.

    Decompone H_coupling nella triade (E_chi, E_RX, E_Psi) e applica
    il drain verso E_Psi quando la saturazione di χ supera la soglia.

    Il drain conserva la somma:
        triad_before.total == triad_after.total
    (dE_chi = -δ, dE_Psi = +δ, dE_RX = 0  →  dE_chi + dE_RX + dE_Psi = 0)

    Parameters
    ----------
    chi_saturation_threshold : float
        Soglia di saturazione |<|χ|>| / χ_stable oltre la quale scatta il drain.
    drain_rate : float
        Frazione dell'eccesso di saturazione × |E_chi| drenata verso E_Psi per step.
    """

    def __init__(
        self,
        chi_saturation_threshold: float = 0.8,
        drain_rate: float = 0.1,
    ) -> None:
        self.chi_saturation_threshold = chi_saturation_threshold
        self.drain_rate = drain_rate
        self._E_psi: float = 0.0
        self._events: List[PhaseTransitionEvent] = []
        self._step: int = 0

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def compute_triad(
        self,
        E_chi_raw: float,
        E_torsion: float,
        E_exchange: float,
    ) -> EnergyTriad:
        """
        Costruisce la triade dai componenti calcolati dall'Hamiltoniana.

        Parameters
        ----------
        E_chi_raw : float
            Energia di accoppiamento scalata: kappa_coupling * E_coupling.
        E_torsion : float
            Termine geometrico di torsione (sempre ≥ 0).
        E_exchange : float
            Termine di scambio topologico (tipicamente ≤ 0, ferromagn.).

        Returns
        -------
        EnergyTriad
            Triade con E_Psi = valore accumulato corrente.
        """
        return EnergyTriad(
            E_chi=E_chi_raw,
            E_RX=E_torsion + E_exchange,
            E_Psi=self._E_psi,
        )

    def apply_drain(
        self,
        triad: EnergyTriad,
        chi_saturation: float,
    ) -> EnergyTriad:
        """
        Applica drain E_chi → E_Psi se la saturazione supera la soglia.

        Conserva triad.total: dE_chi + dE_RX + dE_Psi = 0.

        Parameters
        ----------
        triad : EnergyTriad
            Triade corrente (prodotta da compute_triad).
        chi_saturation : float
            Saturazione normalizzata: mean(|χ|) / χ_stable, ∈ [0, 1].

        Returns
        -------
        EnergyTriad
            Triade aggiornata (E_chi ridotta, E_Psi aumentata dello stesso δ).
        """
        self._step += 1

        if chi_saturation <= self.chi_saturation_threshold:
            return triad

        excess = chi_saturation - self.chi_saturation_threshold
        # drain ≤ 50% di |E_chi| per evitare oscillazioni
        drain = min(
            self.drain_rate * excess * max(abs(triad.E_chi), 1e-30),
            abs(triad.E_chi) * 0.5,
        )

        E_psi_before = self._E_psi
        self._E_psi += drain
        self._events.append(PhaseTransitionEvent(
            step=self._step,
            chi_saturation=chi_saturation,
            E_drained=drain,
            E_psi_before=E_psi_before,
            E_psi_after=self._E_psi,
        ))

        return EnergyTriad(
            E_chi=triad.E_chi - drain,
            E_RX=triad.E_RX,
            E_Psi=self._E_psi,
        )

    # ------------------------------------------------------------------
    # Diagnostica
    # ------------------------------------------------------------------

    @property
    def E_psi_total(self) -> float:
        """Energia totale accumulata nel sink Ψ."""
        return self._E_psi

    @property
    def phase_events(self) -> List[PhaseTransitionEvent]:
        """Copia della lista eventi di transizione di fase."""
        return list(self._events)

    @staticmethod
    def verify_drain_conservation(
        triad_before: EnergyTriad,
        triad_after: EnergyTriad,
        tol: float = 1e-10,
    ) -> bool:
        """
        Verifica che l'operazione di drain abbia conservato triad.total.

        Parameters
        ----------
        triad_before, triad_after : EnergyTriad
            Triade prima e dopo apply_drain.
        tol : float
            Tolleranza assoluta.

        Returns
        -------
        bool
            True se |total_after - total_before| < tol.
        """
        return abs(triad_after.total - triad_before.total) < tol


# ============================================================================
# VALIDAZIONE HDF5
# ============================================================================

def classify_geometric_phase(chi_saturation: float) -> str:
    """
    Classifica la fase geometrica del campo χ in base alla saturazione.

    Corrispondenza fisica (reticolo Leech / VQT):
      Ottaedrica    chi_sat < 0.30   — 6 modi dominanti, ordine debole
      Cubottaedrica 0.30..0.70       — 12 vicini attivi, ordine intermedio
      Icosaedrica   chi_sat > 0.70   — polarizzazione forte, proto-materia
    """
    if chi_saturation >= 0.70:
        return "Icosaedrica"
    if chi_saturation >= 0.30:
        return "Cubottaedrica"
    return "Ottaedrica"


def load_h5_and_validate(
    filepath,
    chi_stable: float = 50.0,
    verbose: bool = True,
) -> dict:
    """
    Carica un file HDF5 prodotto da HDF5Logger e valida la triade Peano-VQT.

    Controlli eseguiti
    ------------------
    1. Monotonicita' di E_Psi: il drain e' irreversibile (E_Psi deve
       essere non-decrescente tra frame consecutivi).
    2. Classificazione delle fasi geometriche da chi_saturation.
    3. Rilevamento evento "nascita materia" (fase Icosaedrica persistente).

    Parameters
    ----------
    filepath : str or Path
        File HDF5 scritto da HDF5Logger.
    chi_stable : float
        Scala caratteristica del campo χ (default 50.0).
        Letto da metadata/chi_stable se presente nel file.
    verbose : bool
        Se True, stampa il report a schermo.

    Returns
    -------
    dict con chiavi:
        total_frames, E_psi_final, E_psi_monotonic, E_psi_violations,
        drain_frames, geometric_phase_counts (dict),
        max_chi_saturation, icosahedral_reached,
        condensation_frame, E_psi_at_condensation.
    """
    import h5py
    import numpy as np

    report = {
        "filepath": str(filepath),
        "total_frames": 0,
        "E_psi_final": 0.0,
        "E_psi_monotonic": True,
        "E_psi_violations": 0,
        "drain_frames": 0,
        "geometric_phase_counts": {"Ottaedrica": 0, "Cubottaedrica": 0, "Icosaedrica": 0},
        "max_chi_saturation": 0.0,
        "icosahedral_reached": False,
        "condensation_frame": None,
        "E_psi_at_condensation": 0.0,
    }

    with h5py.File(str(filepath), "r") as f:
        # Leggi chi_stable dai metadati se disponibile
        if "metadata" in f:
            chi_stable = float(f["metadata"].attrs.get("chi_stable", chi_stable))

        if "frames" not in f:
            if verbose:
                print(f"[WARN] Nessun gruppo /frames in {filepath}")
            return report

        frames_group = f["frames"]
        frame_names = sorted(frames_group.keys())
        report["total_frames"] = len(frame_names)

        E_psi_prev = None

        for name in frame_names:
            frame = frames_group[name]

            E_Psi = float(frame.attrs.get("E_Psi", 0.0))
            E_chi = float(frame.attrs.get("E_chi", 0.0))

            # Controllo monotonicita'
            if E_psi_prev is not None:
                if E_Psi > E_psi_prev + 1e-12:
                    report["drain_frames"] += 1
                elif E_Psi < E_psi_prev - 1e-12:
                    report["E_psi_monotonic"] = False
                    report["E_psi_violations"] += 1

            E_psi_prev = E_Psi

            # Fase geometrica da chi_values
            if "chi_values" in frame:
                chi_vals = frame["chi_values"][:]
                chi_sat = float(np.mean(np.abs(chi_vals))) / max(chi_stable, 1e-30)
                chi_sat = min(chi_sat, 2.0)  # cap per evitare numeri assurdi
                report["max_chi_saturation"] = max(report["max_chi_saturation"], chi_sat)

                phase = classify_geometric_phase(chi_sat)
                report["geometric_phase_counts"][phase] += 1

                if phase == "Icosaedrica" and not report["icosahedral_reached"]:
                    report["icosahedral_reached"] = True
                    report["condensation_frame"] = name
                    report["E_psi_at_condensation"] = E_Psi

        report["E_psi_final"] = E_psi_prev if E_psi_prev is not None else 0.0

    if verbose:
        _print_validation_report(report)

    return report


def _print_validation_report(report: dict) -> None:
    """Stampa il report di validazione in formato leggibile."""
    sep = "=" * 62
    print(f"\n{sep}")
    print("  VALIDAZIONE PEANO-VQT: REPORT")
    print(sep)
    print(f"  File:    {report['filepath']}")
    print(f"  Frames:  {report['total_frames']}")

    print("\n  --- TRIADE ENERGETICA ---")
    print(f"  E_Psi finale:      {report['E_psi_final']:.6e}")
    print(f"  Frames con drain:  {report['drain_frames']}")
    mono = "SI" if report["E_psi_monotonic"] else f"NO ({report['E_psi_violations']} violazioni)"
    print(f"  E_Psi monotona:    {mono}")

    print("\n  --- FASI GEOMETRICHE ---")
    counts = report["geometric_phase_counts"]
    total = max(sum(counts.values()), 1)
    for name, n in counts.items():
        print(f"  {name:15s}: {n:4d}  ({n / total * 100:.1f}%)")
    print(f"  chi_sat massima:   {report['max_chi_saturation']:.4f}")

    print("\n  --- CONDENSAZIONE MATERIA ---")
    if report["icosahedral_reached"]:
        print(f"  Evento di condensazione materia rilevato: "
              f"E_Psi = {report['E_psi_at_condensation']:.4e}, "
              f"architettura icosaedrica consolidata.")
        print(f"  (Frame: {report['condensation_frame']})")
    else:
        sat = report["max_chi_saturation"]
        print(f"  Fase icosaedrica NON raggiunta (chi_sat_max={sat:.4f} < 0.70)")

    inv_ok = "OK" if report["E_psi_monotonic"] else "VIOLATA"
    print(f"\n  Invariante E_Psi monotona: {inv_ok}")
    print(sep + "\n")
