"""
================================================================================
L4 SELF-ASSEMBLY RUN — Auto-organizzazione di 48 solitoni L1
================================================================================

Modello: EffectiveL1 (coarse-grained mean-field)
  Ogni solitone L1 e' rappresentato da un singolo DOF chi_bar con dinamica
  V(chi) = beta*(chi^2 - chi_0^2)^2 (doppio pozzo identico al L1 completo).
  La scelta di questo modello permette 3000 step con 48 solitoni in ~1s,
  mantenendo la fisica essenziale: doppio pozzo, smorzamento, coupling Yukawa.

Inter-coupling (L2 scale, Yukawa):
  F_i = Sigma_{j in NN(i)} [-kappa * W_ij * (chi_i - chi_j) + F_exchange_ij]
        + F_mean_field_i

StructuralObserver:
  - CN_mean: numero di coordinazione medio (vicini iso-fase entro r_cut_cn)
  - BFS cluster: gruppi connessi (|r_ij| < r_cut_cluster, stessa fase)
  - Stability: cluster stabile per >= STABILITY_WINDOW step -> "Livello consolidato"

Analisi finale:
  a) Cluster formati e dimensioni
  b) E_Psi per livello di scala
  c) Struttura cristallina vs polvere di particelle
================================================================================
"""

import sys
import os
import time
import logging
import warnings
from collections import deque, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scipy.spatial import KDTree
from wqt_oop.energy_metrics import (
    PeanoVQTAnalyzer,
    classify_geometric_phase,
    EnergyTriad,
)


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

N_SOL = 48            # Solitoni L1 (48 = 2 x L2 = 4 x 12)
N_STEPS = 3000
DT = 0.1
LOG_EVERY = 50        # Log completo ogni N step
STABILITY_WINDOW = 100  # Step di stabilita' per "livello consolidato"

# --- Fisica L1 (doppio pozzo) ---
BETA = 0.001          # Costante doppio pozzo V = beta*(chi^2-chi_0^2)^2
CHI_0 = 50.0          # Minimo del doppio pozzo
GAMMA = 0.02          # Smorzamento effettivo L1 (mod. per 3000 step)
MASS = 1.0

# --- Coupling inter-solitonico (scala L2) ---
KAPPA_NN = 2.0        # Coupling vicini espliciti
LAMBDA_NN = 0.4       # Scambio topologico NN
L_EFF_NN = 2.5        # Lunghezza Yukawa
KAPPA_MF = 0.1        # Mean-field long-range
W_MF_DIST = 10.0      # Distanza effettiva long-range

# --- Geometria ---
R_SPHERE = 9.0        # Raggio sfera distribuzione casuale
N_NN = 8              # Vicini espliciti per solitone
R_CUT_CN = 5.5        # Raggio coordinazione (CN=12 per R=9, N=48)
R_CUT_CLUSTER = 4.0   # Raggio cluster (piu' stretto del CN)
CHI_ICO = 0.55 * CHI_0  # Soglia icosaedrica per cluster (|chi| > 27.5)

# --- Peano-VQT sistema ---
DRAIN_THRESHOLD = 0.8
DRAIN_RATE = 0.05

SELF_LOG = Path("l4_self_assembly.log")
CLUSTER_LOG = Path("cluster_analysis.log")


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging() -> logging.Logger:
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    fh = logging.FileHandler(SELF_LOG, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    root.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    root.addHandler(ch)
    return logging.getLogger(__name__)


def log_cluster(msg: str) -> None:
    with open(CLUSTER_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ============================================================================
# GEOMETRIA
# ============================================================================

def random_sphere_positions(n: int, r: float, rng: np.random.Generator) -> np.ndarray:
    """n punti uniformi in sfera di raggio r (metodo radice cubica)."""
    theta = rng.uniform(0, 2 * np.pi, n)
    phi = np.arccos(rng.uniform(-1, 1, n))
    rad = r * rng.uniform(0, 1, n) ** (1.0 / 3.0)
    x = rad * np.sin(phi) * np.cos(theta)
    y = rad * np.sin(phi) * np.sin(theta)
    z = rad * np.cos(phi)
    return np.column_stack([x, y, z])


def build_nn_graph(positions: np.ndarray, n_nn: int) -> tuple:
    """
    KDTree NN graph. Ritorna (pairs_i, pairs_j, W_pairs) vettorizzati.
    pairs_i[k], pairs_j[k] = indici coppia k; W_pairs[k] = peso Yukawa.
    """
    tree = KDTree(positions)
    dists, idx = tree.query(positions, k=n_nn + 1)

    seen: set = set()
    pi, pj, pw = [], [], []
    for i in range(len(positions)):
        for k in range(1, n_nn + 1):
            j = int(idx[i, k])
            pair = (min(i, j), max(i, j))
            if pair not in seen:
                seen.add(pair)
                pi.append(pair[0])
                pj.append(pair[1])
                pw.append(float(np.exp(-dists[i, k] / L_EFF_NN)))

    return np.array(pi), np.array(pj), np.array(pw)


# ============================================================================
# DINAMICA EFFETTIVA L1
# ============================================================================

def compute_forces_vec(chi: np.ndarray, pi, pj, pw) -> np.ndarray:
    """
    Forze inter-solitoniche vettorizzate (coupling Yukawa + mean-field).
    """
    chi_0 = CHI_0
    forces = np.zeros(len(chi))

    chi_a, chi_b = chi[pi], chi[pj]
    W = pw

    dchi = chi_a - chi_b
    ta = np.tanh(chi_a / chi_0)
    tb = np.tanh(chi_b / chi_0)
    s2a = 1.0 - ta * ta
    s2b = 1.0 - tb * tb

    Fc = -KAPPA_NN * W * dchi
    Fxa = LAMBDA_NN * W * s2a * tb / chi_0
    Fxb = LAMBDA_NN * W * ta * s2b / chi_0

    np.add.at(forces, pi, Fc + Fxa)
    np.add.at(forces, pj, -Fc + Fxb)

    # Mean-field (long-range)
    W_mf = float(np.exp(-W_MF_DIST / L_EFF_NN))
    chi_mf = float(np.mean(chi))
    forces += -KAPPA_MF * W_mf * (chi - chi_mf)

    return forces


def evolve_step(chi: np.ndarray, vel: np.ndarray, forces: np.ndarray, dt: float):
    """Verlet simplettico vettorizzato per N solitoni coarse-grained."""
    chi_0 = CHI_0
    F_dw = -4.0 * BETA * (chi**2 - chi_0**2) * chi
    F_damp = -GAMMA * MASS * vel
    F_total = F_dw + F_damp + forces
    vel_new = np.clip(vel + F_total * dt / MASS, -500.0, 500.0)
    chi_new = np.clip(chi + vel_new * dt, -250.0, 250.0)
    return chi_new, vel_new


def hamiltonian_total(chi: np.ndarray, vel: np.ndarray, pi, pj, pw) -> float:
    chi_0 = CHI_0
    E_kin = 0.5 * MASS * np.sum(vel**2)
    E_pot = BETA * np.sum((chi**2 - chi_0**2)**2)
    chi_a, chi_b = chi[pi], chi[pj]
    W = pw
    E_coup = 0.5 * KAPPA_NN * float(np.sum(W * (chi_a - chi_b)**2))
    ta = np.tanh(chi_a / chi_0); tb = np.tanh(chi_b / chi_0)
    E_exch = -LAMBDA_NN * float(np.sum(W * ta * tb))
    return float(E_kin + E_pot + E_coup + E_exch)


def coupling_energies(chi: np.ndarray, pi, pj, pw) -> tuple:
    chi_0 = CHI_0
    chi_a, chi_b = chi[pi], chi[pj]
    W = pw
    dchi = chi_a - chi_b
    E_chi_raw = 0.5 * KAPPA_NN * float(np.sum(W * dchi**2))
    ta = np.tanh(chi_a / chi_0); tb = np.tanh(chi_b / chi_0)
    E_exch = -LAMBDA_NN * float(np.sum(W * ta * tb))
    # E_torsion approssimata come alpha_K * E_coupling
    alpha_K_L2 = 1.0 / (24 ** 2)
    E_torsion = alpha_K_L2 * E_chi_raw
    return E_chi_raw, E_torsion, E_exch


# ============================================================================
# STRUCTURAL OBSERVER
# ============================================================================

class StructuralObserver:
    """
    Calcola in tempo reale:
    - CN_mean: coordinazione media iso-fase entro r_cut_cn
    - Cluster (BFS iso-fase, spaziale entro r_cut_cluster)
    - Stabilita' cluster: livello "consolidato" se stabile STABILITY_WINDOW step
    """

    def __init__(self, positions: np.ndarray):
        N = len(positions)
        # Pre-calcola matrice distanze (fissa, posizioni immutabili)
        diff = positions[:, None, :] - positions[None, :, :]
        self.dist = np.sqrt(np.sum(diff**2, axis=2))  # (N, N)
        self.N = N

        # Maschere spaziali pre-calcolate
        self.mask_cn  = (self.dist < R_CUT_CN)  & (~np.eye(N, dtype=bool))
        self.mask_cl  = (self.dist < R_CUT_CLUSTER) & (~np.eye(N, dtype=bool))

        # Stabilita'
        self._largest_hist: deque = deque(maxlen=STABILITY_WINDOW)
        self._consolidation: dict = {}  # level -> (step, E_Psi)
        self._prev_E_psi: dict = {}

    # ------------------------------------------------------------------
    def coordination_number(self, chi: np.ndarray) -> float:
        """CN medio: vicini iso-fase entro r_cut_cn con |chi| > CHI_ICO."""
        phase = np.sign(chi)
        ico = np.abs(chi) > CHI_ICO

        # Per ogni solitone i, conta j con stessa fase, |chi_j|>ICO, dist<r_cut
        CN = np.zeros(self.N)
        for i in range(self.N):
            if not ico[i]:
                continue
            mask = self.mask_cn[i] & ico & (phase == phase[i])
            CN[i] = mask.sum()

        n_ico = ico.sum()
        return float(CN[ico].mean()) if n_ico > 0 else 0.0

    # ------------------------------------------------------------------
    def find_clusters(self, chi: np.ndarray) -> list:
        """
        BFS: cluster connessi iso-fase con |chi| > CHI_ICO e dist < r_cut_cluster.
        Ritorna lista di dimensioni ordinata desc.
        """
        ico = np.abs(chi) > CHI_ICO
        phase = np.where(chi > CHI_ICO, 1, np.where(chi < -CHI_ICO, -1, 0))
        visited = np.zeros(self.N, dtype=bool)
        clusters = []

        for start in range(self.N):
            if visited[start] or phase[start] == 0:
                continue
            size = 0
            q = deque([start])
            visited[start] = True
            p = phase[start]
            while q:
                node = q.popleft()
                size += 1
                neighbors = np.where(
                    self.mask_cl[node] & ~visited & (phase == p)
                )[0]
                for nb in neighbors:
                    visited[nb] = True
                    q.append(nb)
            clusters.append(size)

        return sorted(clusters, reverse=True)

    # ------------------------------------------------------------------
    def check_stability(
        self, step: int, clusters: list, E_Psi: float, log: logging.Logger
    ) -> None:
        """
        Monitora stabilita' cluster. Se il cluster piu' grande
        rimane stabile (variazione <= 2) per STABILITY_WINDOW step
        e la sua dimensione e' >= 12: dichiara "livello consolidato".
        """
        largest = clusters[0] if clusters else 0
        self._largest_hist.append(largest)

        if len(self._largest_hist) < STABILITY_WINDOW:
            return

        arr = np.array(self._largest_hist)
        if arr.max() - arr.min() > 2 or arr.mean() < 12:
            return

        # Cluster stabile!
        stable_size = int(round(arr.mean()))
        level = max(1, stable_size // 12)
        key = f"L{level}"

        if key not in self._consolidation:
            self._consolidation[key] = (step, E_Psi, stable_size)
            delta_E = E_Psi - self._prev_E_psi.get(f"L{level-1}", 0.0)
            msg = (
                f"[LIVELLO {key} CONSOLIDATO] step {step}: "
                f"cluster stabile di {stable_size} solitoni | "
                f"E_Psi={E_Psi:.4e} | delta_E_Psi={delta_E:.4e}"
            )
            log.warning(msg)
            log_cluster(msg)
            self._prev_E_psi[key] = E_Psi

    # ------------------------------------------------------------------
    @property
    def consolidations(self) -> dict:
        return dict(self._consolidation)


# ============================================================================
# ANALISI FINALE
# ============================================================================

def analyze_cluster_sizes(clusters: list) -> dict:
    """
    Verifica se le dimensioni dei cluster sono multipli di 12.
    """
    if not clusters:
        return {"clusters": [], "multiples_of_12": [], "disorder": True}

    multiples = []
    for size in clusters:
        nearest = round(size / 12) * 12
        deviation = abs(size - nearest) / 12.0
        is_mult = nearest >= 12 and deviation <= 0.3
        multiples.append({
            "size": size,
            "nearest_multiple_12": nearest,
            "deviation": deviation,
            "is_multiple": is_mult,
        })

    n_mult = sum(1 for m in multiples if m["is_multiple"])
    disorder = n_mult == 0 or (clusters[0] < 6)

    return {
        "clusters": clusters,
        "details": multiples,
        "n_clusters_multiple_12": n_mult,
        "disorder": disorder,
    }


def determine_final_outcome(clusters: list, M: float, sat: float) -> str:
    if not clusters:
        return "POLVERE DI PARTICELLE"
    largest = clusters[0]
    if largest >= 40 and abs(M) > 0.6:
        return "STRUTTURA CRISTALLINA (singolo super-solitone)"
    if largest >= 20 and abs(M) > 0.4:
        return "STRUTTURA CRISTALLINA (dominio maggioritario)"
    if len(clusters) >= 3 and max(clusters) >= 10:
        return "STRUTTURA POLICRISTALLINA (multi-dominio)"
    if sat > 0.6:
        return "FASE ICOSAEDRICA DISORDINATA"
    return "POLVERE DI PARTICELLE"


# ============================================================================
# MAIN
# ============================================================================

def run_self_assembly() -> dict:
    log = setup_logging()
    with open(CLUSTER_LOG, "w", encoding="utf-8") as f:
        f.write(f"# cluster_analysis.log — {datetime.now().isoformat()}\n\n")

    log.info("=" * 72)
    log.info("L4 SELF-ASSEMBLY RUN — 48 solitoni L1 (EffectiveL1 coarse-grained)")
    log.info("=" * 72)
    log.info(f"  N_SOL={N_SOL}, N_STEPS={N_STEPS}, DT={DT}")
    log.info(f"  V(chi)=beta*(chi^2-chi_0^2)^2  beta={BETA}, chi_0={CHI_0}")
    log.info(f"  gamma={GAMMA}, kappa_NN={KAPPA_NN}, lambda_NN={LAMBDA_NN}")
    log.info(f"  L_eff={L_EFF_NN}, R_sphere={R_SPHERE}, N_NN={N_NN}")
    log.info(f"  r_cut_CN={R_CUT_CN} (CN=12 target), r_cut_cluster={R_CUT_CLUSTER}")

    # --- Inizializza posizioni e solitoni ---
    rng = np.random.default_rng(2026)
    positions = random_sphere_positions(N_SOL, R_SPHERE, rng)
    pi, pj, pw = build_nn_graph(positions, N_NN)
    log.info(f"  Coppie NN: {len(pi)}, W_NN: [{pw.min():.3f}, {pw.max():.3f}]")

    # Tutti partono da chi=+10 (Ottaedrica) con piccolo rumore
    chi = 10.0 + rng.normal(0, 0.5, N_SOL)
    vel = rng.normal(0, 0.5, N_SOL)

    # --- Observer e Peano ---
    observer = StructuralObserver(positions)
    peano = PeanoVQTAnalyzer(chi_saturation_threshold=DRAIN_THRESHOLD, drain_rate=DRAIN_RATE)

    H0 = hamiltonian_total(chi, vel, pi, pj, pw)
    sat0 = float(np.mean(np.abs(chi)) / CHI_0)
    log.info(f"  H_0 = {H0:.4e}, chi_sat_0 = {sat0:.4f}")
    log.info("")

    # --- Header tabella ---
    log.info(
        f"{'Step':>6}  {'chi_sat':>8}  {'M':>7}  {'CN_mean':>8}  "
        f"{'E_Psi':>12}  {'Cluster_max':>12}  {'N_cluster':>10}  {'H_tot':>12}"
    )
    log.info("-" * 94)

    # Serie temporali
    ts = {"steps": [], "sat": [], "M": [], "CN": [], "epsi": [], "H": [],
          "cl_max": [], "n_cl": []}
    phase_prev = "Ottaedrica"
    t0 = time.time()
    last_clusters = []

    for step in range(1, N_STEPS + 1):
        forces = compute_forces_vec(chi, pi, pj, pw)
        chi, vel = evolve_step(chi, vel, forces, DT)

        # Log e analisi ogni LOG_EVERY step
        if step % LOG_EVERY == 0 or step == 1:
            sat = float(np.mean(np.abs(chi)) / CHI_0)
            M = float(np.mean(np.clip(chi / CHI_0, -1.0, 1.0)))
            CN = observer.coordination_number(chi)
            H_tot = hamiltonian_total(chi, vel, pi, pj, pw)
            clusters = observer.find_clusters(chi)
            cl_max = clusters[0] if clusters else 0
            n_cl = len(clusters)

            # Peano-VQT sistema
            E_chi_r, E_tor, E_exch = coupling_energies(chi, pi, pj, pw)
            triad = peano.compute_triad(E_chi_r, E_tor, E_exch)
            triad = peano.apply_drain(triad, min(sat, 1.0))
            E_psi = peano.E_psi_total

            log.info(
                f"{step:6d}  {sat:8.4f}  {M:7.4f}  {CN:8.2f}  "
                f"{E_psi:12.4e}  {cl_max:12d}  {n_cl:10d}  {H_tot:12.4e}"
            )

            # Fase collettiva
            phase = classify_geometric_phase(sat)
            if phase != phase_prev:
                log.warning(
                    f"  [FASE-COLLETTIVA] step {step}: {phase_prev} -> {phase} "
                    f"| chi_sat={sat:.4f} M={M:.4f}"
                )
                phase_prev = phase

            # CN vicino a 12?
            if 10 <= CN <= 14:
                log.warning(
                    f"  [CN~12] step {step}: coordinazione CN={CN:.1f} "
                    f"~ fase icosaedrica!"
                )

            # Stabilita' livello
            observer.check_stability(step, clusters, E_psi, log)

            ts["steps"].append(step); ts["sat"].append(sat)
            ts["M"].append(M); ts["CN"].append(CN)
            ts["epsi"].append(E_psi); ts["H"].append(H_tot)
            ts["cl_max"].append(cl_max); ts["n_cl"].append(n_cl)
            last_clusters = clusters

        # Stability check ogni step (solo dimensione cluster max)
        else:
            # Lightweight: solo update hist stabilita'
            observer._largest_hist.append(
                observer._largest_hist[-1] if observer._largest_hist else 0
            )

    elapsed = time.time() - t0

    # ---------------------------------------------------------------
    # ANALISI FINALE
    # ---------------------------------------------------------------
    clusters_final = observer.find_clusters(chi)
    sat_f = float(np.mean(np.abs(chi)) / CHI_0)
    M_f = float(np.mean(np.clip(chi / CHI_0, -1.0, 1.0)))
    CN_f = observer.coordination_number(chi)
    H_f = hamiltonian_total(chi, vel, pi, pj, pw)
    E_psi_f = peano.E_psi_total

    cluster_analysis = analyze_cluster_sizes(clusters_final)
    outcome = determine_final_outcome(clusters_final, M_f, sat_f)

    log.info("")
    log.info("=" * 72)
    log.info("ANALISI FINALE")
    log.info("=" * 72)
    log.info(f"  Esito:            {outcome}")
    log.info(f"  chi_sat:          {sat0:.4f} -> {sat_f:.4f}")
    log.info(f"  M (ordine):       {M_f:.4f}")
    log.info(f"  CN_mean:          {CN_f:.2f}  (target: 12.0)")
    log.info(f"  H_tot:            {H0:.4e} -> {H_f:.4e}  ({(H_f-H0)/H0*100:.1f}%)")
    log.info(f"  E_Psi sistema:    {E_psi_f:.4e}")
    log.info(f"  Tempo:            {elapsed:.2f}s")

    log.info("")
    log.info("  DISTRIBUZIONE CLUSTER FINALI:")
    if clusters_final:
        for info in cluster_analysis["details"]:
            mult_str = f"(~{info['nearest_multiple_12']}, mult.12)" if info["is_multiple"] else ""
            log.info(f"    Cluster size={info['size']:3d}  {mult_str}")
    else:
        log.info("    Nessun cluster rilevato (sistema disordinato)")

    n_mult = cluster_analysis["n_clusters_multiple_12"]
    if n_mult > 0:
        log.info(f"  ** {n_mult} cluster sono multipli di 12 — segnatura icosaedrica!")
    else:
        log.info("  Nessun cluster di dimensione multipla di 12.")

    log.info("")
    log.info("  LIVELLI CONSOLIDATI:")
    if observer.consolidations:
        for lvl, (step_c, epsi_c, size_c) in sorted(observer.consolidations.items()):
            log.info(f"    {lvl}: step {step_c}, size={size_c}, E_Psi={epsi_c:.4e}")
    else:
        log.info("    Nessun livello consolidato rilevato (100 step stabilita').")

    log.info("")
    log.info("  RISPOSTA ALLE DOMANDE:")
    sizes_str = str(clusters_final[:8]) if clusters_final else "[]"
    log.info(f"  a) Cluster formati: {len(clusters_final)}, dimensioni: {sizes_str}")
    log.info(f"  b) E_Psi collettiva: {E_psi_f:.4e}")
    if observer.consolidations:
        for lvl, (sc, ep, sz) in sorted(observer.consolidations.items()):
            prev_ep = list(observer._prev_E_psi.values())
            log.info(f"     E_Psi a {lvl}: {ep:.4e}")
    if n_mult > 0:
        log.info(f"  c) Il sistema ha scelto strutture basate su multipli di 12: SI")
        log.info(f"     -> {outcome}")
    else:
        log.info(f"  c) Strutture disordinate: il sistema NON ha scelto multipli di 12.")
        log.info(f"     -> {outcome}")

    log.info("=" * 72)

    result = {
        "outcome": outcome,
        "sat_f": sat_f,
        "M_f": M_f,
        "CN_f": CN_f,
        "H0": H0, "Hf": H_f,
        "E_psi_f": E_psi_f,
        "clusters_final": clusters_final,
        "cluster_analysis": cluster_analysis,
        "consolidations": observer.consolidations,
        "elapsed": elapsed,
        "ts": ts,
    }

    _update_checkpoint(result)
    log.info("  Checkpoint aggiornato.")
    return result


# ============================================================================
# CHECKPOINT
# ============================================================================

def _update_checkpoint(r: dict) -> None:
    ck = Path(__file__).parent.parent / "docs" / "MIGRAZIONE_CHECKPOINT.md"
    if not ck.exists():
        return

    clusters = r["clusters_final"]
    ca = r["cluster_analysis"]
    n_mult = ca["n_clusters_multiple_12"]

    sizes_str = ", ".join(str(s) for s in clusters[:8]) if clusters else "nessuno"
    consolidations_str = (
        " | ".join(f"{k}: step {v[0]} size={v[2]}" for k, v in sorted(r["consolidations"].items()))
        if r["consolidations"] else "nessuno"
    )

    block = (
        f"\n---\n"
        f"## L4 Self-Assembly — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Config**: {N_SOL} L1 (EffectiveL1), {N_STEPS} step, "
        f"kappa_NN={KAPPA_NN}, R={R_SPHERE}\n\n"
        f"**a) Cluster formati**: {len(clusters)} cluster | "
        f"dimensioni: [{sizes_str}]\n\n"
        f"**b) E_Psi collettiva**: {r['E_psi_f']:.4e}\n\n"
        f"**c) Esito**: **{r['outcome']}**\n"
        f"- Multipli di 12: {'SI (' + str(n_mult) + ' cluster)' if n_mult else 'NO'}\n"
        f"- CN_mean finale: {r['CN_f']:.2f} (target: 12.0)\n"
        f"- M (ordine): {r['M_f']:.4f}\n"
        f"- chi_sat: {r['sat_f']:.4f}\n"
        f"- H_tot: {r['H0']:.4e} -> {r['Hf']:.4e} "
        f"({(r['Hf']-r['H0'])/r['H0']*100:.1f}%)\n\n"
        f"**Livelli consolidati**: {consolidations_str}\n"
        f"**Tempo run**: {r['elapsed']:.2f}s\n"
    )

    with open(ck, "a", encoding="utf-8") as f:
        f.write(block)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_self_assembly()
    sys.exit(0)
