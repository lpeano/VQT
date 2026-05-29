"""
================================================================================
L2 LEECH RUN — Test del Reticolo di Leech: 24 Solitoni L1 su Sfera
================================================================================

24 SolitoneComposito L1 disposti su geometria sferica (Fibonacci lattice).
Inter-coupling a due regimi:
  1. Nearest-neighbor esplicito (Yukawa, k=6 vicini)
  2. Mean-field per le restanti interazioni a lungo raggio

Monitoraggio collettivo:
  - chi_sat globale: media(|chi_bar_i|)/chi_stable -> attractor icosaedrico?
  - M (magnetizzazione): mean(chi_i/chi_stable) -> ordine ferromagnetico
  - Frustrazione: Sigma W_ij * sign(chi_i * chi_j) normalizzata in [-1,+1]
  - Cluster connesso piu' grande (BFS su vicini iso-fase)

Scenari:
  ALL_POSITIVE : 24 solitoni partono da chi=+10 (Ottaedrica) -> cristallo atteso
  HALF_HALF    : 12 a +10, 12 a -10, mischiati -> vetro di spin o domini?

Output: l2_leech.log, eventi_leech.log, MIGRAZIONE_CHECKPOINT.md
================================================================================
"""

import sys
import os
import time
import logging
import warnings
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore", message=".*DRIFT ENERGIA CRITICO.*")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scipy.spatial import KDTree

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.energy_metrics import classify_geometric_phase


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

N_SOL = 24
CHI_STABLE = 50.0
CHI_MEAN_POS = 10.0   # avvio Ottaedrico (chi_sat=0.20)
CHI_SPREAD = 0.5
SPHERE_RADIUS = 6.0
SEG_RADIUS = 0.4      # raggio cerchio interno al L1

N_NN = 6              # vicini espliciti (Yukawa)
KAPPA_NN = 1.5        # intensita' coupling NN
LAMBDA_NN = 0.3       # scambio NN
L_EFF_NN = 2.5        # lunghezza Yukawa
KAPPA_MF = 0.2        # mean-field (long-range, ~10x piu' debole)
W_MF_DIST = 9.0       # distanza effettiva long-range -> W = exp(-9/2.5) ~ 0.027

N_STEPS = 100
DT = 0.1
LOG_EVERY = 10

# Soglia icosaedrica per cluster BFS
ICO_THRESH = 0.7 * CHI_STABLE   # |chi_bar| > 35

MODES = ["ALL_POSITIVE", "HALF_HALF"]

LEECH_LOG  = Path("l2_leech.log")
EVENTS_LOG = Path("eventi_leech.log")


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging() -> logging.Logger:
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    fh = logging.FileHandler(LEECH_LOG, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    root.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, "%H:%M:%S"))
    root.addHandler(ch)
    return logging.getLogger(__name__)


def log_event(msg: str, log: logging.Logger, level: str = "info") -> None:
    getattr(log, level)(msg)
    with open(EVENTS_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ============================================================================
# GEOMETRIA SFERICA
# ============================================================================

def fibonacci_sphere(n: int, radius: float) -> np.ndarray:
    """n punti uniformemente distribuiti su sfera di raggio radius."""
    pos = np.zeros((n, 3))
    phi = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (i / float(n - 1)) * 2.0
        r = np.sqrt(max(1.0 - y * y, 0.0))
        theta = phi * i
        pos[i] = [np.cos(theta) * r, y, np.sin(theta) * r]
    return pos * radius


def build_nn_graph(centers: np.ndarray, n_nn: int) -> tuple:
    """
    Costruisce grafo dei vicini piu' prossimi con KDTree.

    Returns
    -------
    pairs   : list of (i, j) — coppie uniche
    W_pairs : list of float  — pesi Yukawa per ogni coppia
    """
    tree = KDTree(centers)
    dists, idx = tree.query(centers, k=n_nn + 1)

    pair_dist: dict = {}
    for i in range(len(centers)):
        for k in range(1, n_nn + 1):
            j = int(idx[i, k])
            pair = tuple(sorted([i, j]))
            if pair not in pair_dist:
                pair_dist[pair] = float(dists[i, k])

    pairs = list(pair_dist.keys())
    W_pairs = [float(np.exp(-pair_dist[p] / L_EFF_NN)) for p in pairs]
    return pairs, W_pairs


# ============================================================================
# SOLITONI L1
# ============================================================================

def make_l1_soliton(
    chi_mean: float,
    center: np.ndarray,
    rng: np.random.Generator,
) -> SolitoneComposito:
    """24 segmenti L0 su cerchio locale, screening disabilitato per velocita'."""
    p0 = PhysicsContext.for_level(0)
    p1 = PhysicsContext.for_level(1)
    segs = []
    for i in range(24):
        theta = 2.0 * np.pi * i / 24
        pos = center + SEG_RADIUS * np.array([np.cos(theta), np.sin(theta), 0.0])
        chi = chi_mean + rng.uniform(-CHI_SPREAD, CHI_SPREAD)
        vel = rng.uniform(-0.15, 0.15)
        segs.append(SegmentoQuantistico(chi=chi, vel=vel, physics=p0, position=pos))
    return SolitoneComposito(segs, p1, screening_enabled=False)


def get_chi_bars(solitons: list) -> np.ndarray:
    """Array (N_SOL,) dei baricentri del campo chi."""
    return np.array([s.compute_barycenter() for s in solitons])


# ============================================================================
# FISICA COLLETTIVA
# ============================================================================

def compute_collective_forces(chi_bars: np.ndarray, pairs: list, W_pairs: list) -> np.ndarray:
    """
    Forze inter-solitoniche: nearest-neighbor esplicito + mean-field.

    F_i = Sigma_{j in NN(i)} [-kappa * W_ij * (chi_i - chi_j) + F_exchange_ij]
          + F_mean_field_i

    Returns array (N_SOL,) di forze scalari sul campo chi.
    """
    N = len(chi_bars)
    forces = np.zeros(N)
    chi_0 = CHI_STABLE

    # --- Coupling nearest-neighbor ---
    for (i, j), W in zip(pairs, W_pairs):
        ci, cj = chi_bars[i], chi_bars[j]
        dchi = ci - cj

        ti, tj = float(np.tanh(ci / chi_0)), float(np.tanh(cj / chi_0))
        s2i, s2j = 1.0 - ti * ti, 1.0 - tj * tj

        # Coupling (gradiente chi)
        F_ci = -KAPPA_NN * W * dchi
        F_cj = +KAPPA_NN * W * dchi
        # Scambio topologico
        F_xi = LAMBDA_NN * W * s2i * tj / chi_0
        F_xj = LAMBDA_NN * W * ti * s2j / chi_0

        forces[i] += F_ci + F_xi
        forces[j] += F_cj + F_xj

    # --- Mean-field (long-range, debole) ---
    W_mf = float(np.exp(-W_MF_DIST / L_EFF_NN))
    chi_mf = float(np.mean(chi_bars))
    for i in range(N):
        forces[i] += -KAPPA_MF * W_mf * (chi_bars[i] - chi_mf)

    return forces


def compute_frustration(chi_bars: np.ndarray, pairs: list, W_pairs: list) -> float:
    """
    Frustrazione normalizzata in [-1, +1].
    -1: ordinato (tutti stesso segno, ferromagnetico)
    +1: frustrato (tutti segni opposti, antiferromagnetico)
    """
    if not pairs:
        return 0.0
    total = W_total = 0.0
    for (i, j), W in zip(pairs, W_pairs):
        s = float(np.sign(chi_bars[i] * chi_bars[j]))
        total += W * (-s)   # same-phase: -W (favorevole); cross: +W
        W_total += W
    return total / W_total if W_total > 0 else 0.0


def magnetization(chi_bars: np.ndarray) -> float:
    """Parametro d'ordine M in [-1,+1]. |M|->1: cristallo."""
    return float(np.mean(np.clip(chi_bars / CHI_STABLE, -1.0, 1.0)))


def global_chi_sat(chi_bars: np.ndarray) -> float:
    return float(np.mean(np.abs(chi_bars)) / CHI_STABLE)


def total_E_psi(solitons: list) -> float:
    return sum(s._peano_analyzer.E_psi_total for s in solitons)


def largest_cluster(chi_bars: np.ndarray, pairs: list) -> int:
    """
    BFS: dimensione del cluster connesso piu' grande
    tra solitoni con |chi_bar| > ICO_THRESH e stesso segno.
    """
    N = len(chi_bars)
    phase = np.where(chi_bars > ICO_THRESH, 1,
             np.where(chi_bars < -ICO_THRESH, -1, 0))

    adj: dict = {i: [] for i in range(N)}
    for (i, j) in pairs:
        if phase[i] != 0 and phase[i] == phase[j]:
            adj[i].append(j)
            adj[j].append(i)

    visited = [False] * N
    best = 0
    for start in range(N):
        if visited[start] or phase[start] == 0:
            continue
        size = 0
        q = deque([start])
        visited[start] = True
        while q:
            node = q.popleft()
            size += 1
            for nb in adj[node]:
                if not visited[nb]:
                    visited[nb] = True
                    q.append(nb)
        best = max(best, size)
    return best


# ============================================================================
# SINGOLO MODO
# ============================================================================

def run_mode(
    mode: str,
    centers: np.ndarray,
    pairs: list,
    W_pairs: list,
    log: logging.Logger,
) -> dict:

    log.info("")
    log.info("=" * 72)
    log.info(f"MODO: {mode}")
    log_event(f"\n=== LEECH {mode} ===", log, "info")

    rng = np.random.default_rng(2026 + (0 if mode == "ALL_POSITIVE" else 7))

    # Chi iniziali
    if mode == "ALL_POSITIVE":
        chi_means = [+CHI_MEAN_POS] * N_SOL
        log.info(f"  Tutti +{CHI_MEAN_POS}: partenza Ottaedrica uniforme")
    else:
        half = N_SOL // 2
        raw = [+CHI_MEAN_POS] * half + [-CHI_MEAN_POS] * (N_SOL - half)
        rng2 = np.random.default_rng(999)
        rng2.shuffle(raw)
        chi_means = list(raw)
        n_pos = sum(1 for c in chi_means if c > 0)
        log.info(f"  {n_pos} a +{CHI_MEAN_POS}, {N_SOL-n_pos} a -{CHI_MEAN_POS}, mischiati")

    # Costruisci 24 L1 solitoni
    solitons = [make_l1_soliton(chi_means[k], centers[k], rng)
                for k in range(N_SOL)]
    log.info(f"  {N_SOL} solitoni L1 pronti. Coppie NN: {len(pairs)}")

    cb0 = get_chi_bars(solitons)
    sat0 = global_chi_sat(cb0)
    M0 = magnetization(cb0)
    frus0 = compute_frustration(cb0, pairs, W_pairs)
    log.info(f"  Stato iniziale: chi_sat={sat0:.4f}, M={M0:.4f}, Frustr={frus0:.4f}")
    log.info("")

    log.info(
        f"{'Step':>5}  {'chi_sat':>8}  {'M':>7}  {'Frustr':>8}  "
        f"{'E_Psi':>12}  {'Cluster':>10}  {'H_tot':>12}"
    )
    log.info("-" * 78)

    phase_prev = classify_geometric_phase(sat0)
    ts = {"steps": [], "sat": [], "M": [], "frus": [], "epsi": []}
    t0 = time.time()
    ice_first = -1   # primo step con CRISTALLO completo

    for step in range(1, N_STEPS + 1):
        cb = get_chi_bars(solitons)
        forces = compute_collective_forces(cb, pairs, W_pairs)
        for k, sol in enumerate(solitons):
            sol.evolve(DT, external_force=float(forces[k]))

        if step % LOG_EVERY == 0 or step == 1:
            cb = get_chi_bars(solitons)
            sat = global_chi_sat(cb)
            M = magnetization(cb)
            frus = compute_frustration(cb, pairs, W_pairs)
            E_psi = total_E_psi(solitons)
            H_tot = sum(s.energia_totale for s in solitons)
            cl = largest_cluster(cb, pairs)
            phase = classify_geometric_phase(sat)

            log.info(
                f"{step:5d}  {sat:8.4f}  {M:7.4f}  {frus:8.4f}  "
                f"{E_psi:12.4e}  {cl:4d}/{N_SOL:2d}      {H_tot:12.4e}"
            )
            ts["steps"].append(step); ts["sat"].append(sat)
            ts["M"].append(M); ts["frus"].append(frus); ts["epsi"].append(E_psi)

            # Cambio fase collettiva
            if phase != phase_prev:
                log_event(
                    f"[FASE] step {step}: {phase_prev} -> {phase} "
                    f"| chi_sat={sat:.4f} M={M:.4f}",
                    log, "warning"
                )
                phase_prev = phase

            # Cristallo completo
            if cl == N_SOL and ice_first < 0:
                ice_first = step
                log_event(
                    f"[CRISTALLO-COMPLETO] step {step}: tutti {N_SOL} solitoni "
                    f"aggregati! M={M:.4f} chi_sat={sat:.4f}",
                    log, "warning"
                )

            # Frustrazione significativa
            if frus > 0.4:
                log_event(
                    f"[FRUSTRAZIONE] step {step}: frustr={frus:.3f} > 0.4 "
                    f"— vetro di spin in formazione?",
                    log, "warning"
                )

    elapsed = time.time() - t0

    # --- Analisi finale ---
    cb_f = get_chi_bars(solitons)
    sat_f = global_chi_sat(cb_f)
    M_f = magnetization(cb_f)
    frus_f = compute_frustration(cb_f, pairs, W_pairs)
    E_psi_f = total_E_psi(solitons)
    cl_f = largest_cluster(cb_f, pairs)
    n_pos = int(np.sum(cb_f > ICO_THRESH))
    n_neg = int(np.sum(cb_f < -ICO_THRESH))
    n_dis = N_SOL - n_pos - n_neg

    # Classificazione esito
    if cl_f >= N_SOL * 0.8 and abs(M_f) > 0.7:
        outcome = "STRUTTURA CRISTALLINA"
    elif abs(M_f) < 0.25 and frus_f > 0.15:
        outcome = "VETRO DI SPIN"
    elif cl_f >= N_SOL * 0.5:
        outcome = "DOMINIO PARZIALE"
    else:
        outcome = "POLVERE DI PARTICELLE"

    log.info("")
    log.info(f"  RIEPILOGO {mode}")
    log.info(f"  Esito:           {outcome}")
    log.info(f"  chi_sat:         {sat0:.4f} -> {sat_f:.4f}")
    log.info(f"  M:               {M0:.4f} -> {M_f:.4f}")
    log.info(f"  Frustrazione:    {frus0:.4f} -> {frus_f:.4f}")
    log.info(f"  Cluster max:     {cl_f}/{N_SOL}")
    log.info(f"  +50 / -50 / dis: {n_pos} / {n_neg} / {n_dis}")
    log.info(f"  E_Psi coll.:     {E_psi_f:.4e}")
    if ice_first > 0:
        log.info(f"  Primo cristallo: step {ice_first}")
    log.info(f"  Tempo:           {elapsed:.1f}s")

    log_event(
        f"[ESITO-{mode}] {outcome} | Cluster {cl_f}/{N_SOL} | "
        f"M={M_f:.4f} | Frustr={frus_f:.4f} | E_Psi={E_psi_f:.4e}",
        log, "warning"
    )

    return {
        "mode": mode, "outcome": outcome,
        "sat_f": sat_f, "M_f": M_f, "frus_f": frus_f,
        "E_psi_f": E_psi_f, "cl_f": cl_f,
        "n_pos": n_pos, "n_neg": n_neg, "n_dis": n_dis,
        "ice_first": ice_first,
        "elapsed": elapsed,
        "ts": ts,
    }


# ============================================================================
# MAIN
# ============================================================================

def run_leech() -> list:
    log = setup_logging()

    with open(EVENTS_LOG, "w", encoding="utf-8") as f:
        f.write(f"# eventi_leech.log — {datetime.now().isoformat()}\n\n")

    log.info("=" * 72)
    log.info("L2 LEECH RUN — 24 Solitoni L1 su Geometria Sferica")
    log.info("=" * 72)
    log.info(f"  N_SOL={N_SOL}, N_NN={N_NN}, kappa_NN={KAPPA_NN}, lambda_NN={LAMBDA_NN}")
    log.info(f"  L_eff={L_EFF_NN}, kappa_MF={KAPPA_MF}, R_sfera={SPHERE_RADIUS}")
    log.info(f"  N_STEPS={N_STEPS}, DT={DT}")

    centers = fibonacci_sphere(N_SOL, SPHERE_RADIUS)
    pairs, W_pairs = build_nn_graph(centers, N_NN)
    W_arr = np.array(W_pairs)
    log.info(f"  Coppie NN: {len(pairs)}, W_NN: [{W_arr.min():.3f}, {W_arr.max():.3f}]")

    results = []
    for mode in MODES:
        r = run_mode(mode, centers, pairs, W_pairs, log)
        results.append(r)

    # --- Report comparativo ---
    log.info("")
    log.info("=" * 72)
    log.info("CONFRONTO FINALE")
    log.info("=" * 72)
    log.info(
        f"  {'Modo':14}  {'Esito':22}  {'chi_sat':>8}  {'M':>6}  "
        f"{'Frustr':>7}  {'Cluster':>9}  {'E_Psi':>12}"
    )
    log.info("-" * 92)
    for r in results:
        log.info(
            f"  {r['mode']:14}  {r['outcome']:22}  {r['sat_f']:8.4f}  "
            f"{r['M_f']:6.4f}  {r['frus_f']:7.4f}  "
            f"{r['cl_f']:4d}/{N_SOL}  {r['E_psi_f']:12.4e}"
        )

    log.info("")
    log.info("CONCLUSIONI FISICHE:")
    ap = next((r for r in results if r["mode"] == "ALL_POSITIVE"), {})
    hh = next((r for r in results if r["mode"] == "HALF_HALF"), {})

    if "CRISTAL" in ap.get("outcome", ""):
        log.info("  [ALL_POS] Cristallizzazione collettiva L2: tutti i solitoni")
        log.info("            convergono allo stesso attrattore icosaedrico (+50).")
    else:
        log.info(f"  [ALL_POS] {ap.get('outcome')}: aggregazione parziale.")

    if "VETRO" in hh.get("outcome", ""):
        log.info("  [HALF_HALF] Vetro di spin confermato: la frustrazione")
        log.info("              geometrica impedisce la cristallizzazione globale.")
    elif "CRISTAL" in hh.get("outcome", ""):
        log.info("  [HALF_HALF] Cristallo emergente cross-fase: il coupling")
        log.info("              ferromagnetico ha vinto sulla frustrazione iniziale.")
    else:
        log.info(f"  [HALF_HALF] {hh.get('outcome')}: fase intermedia.")

    log.info(f"  E_Psi ALL_POS:   {ap.get('E_psi_f', 0):.4e} (indicatore legame)")
    log.info(f"  E_Psi HALF_HALF: {hh.get('E_psi_f', 0):.4e} (indicatore frustrazione)")
    log.info("")

    _update_checkpoint(results)
    log.info("  Checkpoint aggiornato.")
    log.info("=" * 72)
    return results


# ============================================================================
# CHECKPOINT
# ============================================================================

def _update_checkpoint(results: list) -> None:
    ck = Path(__file__).parent.parent / "docs" / "peano" / "MIGRAZIONE_CHECKPOINT.md"
    if not ck.exists():
        return

    ap = next((r for r in results if r["mode"] == "ALL_POSITIVE"), {})
    hh = next((r for r in results if r["mode"] == "HALF_HALF"), {})

    block = (
        f"\n---\n"
        f"## L2 Leech Run — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Config**: {N_SOL} L1 solitoni, kappa_NN={KAPPA_NN}, "
        f"N_NN={N_NN}, N_STEPS={N_STEPS}\n\n"
        f"**a) Solitoni nel cluster principale**:\n"
        f"- ALL_POSITIVE: **{ap.get('cl_f','?')}/{N_SOL}** ({ap.get('outcome','?')})\n"
        f"- HALF_HALF: **{hh.get('cl_f','?')}/{N_SOL}** ({hh.get('outcome','?')})\n\n"
        f"**b) E_Psi collettiva (indicatore legame)**:\n"
        f"- ALL_POSITIVE: {ap.get('E_psi_f',0):.4e}\n"
        f"- HALF_HALF: {hh.get('E_psi_f',0):.4e}\n\n"
        f"**c) Esito**:\n"
        f"- ALL_POSITIVE: **{ap.get('outcome','?')}**\n"
        f"- HALF_HALF: **{hh.get('outcome','?')}**\n\n"
        f"| Modo | chi_sat | M | Frustr | Cluster | E_Psi |\n"
        f"|------|---------|---|--------|---------|-------|\n"
        f"| ALL_POS | {ap.get('sat_f',0):.4f} | {ap.get('M_f',0):.4f} | "
        f"{ap.get('frus_f',0):.4f} | {ap.get('cl_f',0)}/{N_SOL} | "
        f"{ap.get('E_psi_f',0):.4e} |\n"
        f"| HALF_HALF | {hh.get('sat_f',0):.4f} | {hh.get('M_f',0):.4f} | "
        f"{hh.get('frus_f',0):.4f} | {hh.get('cl_f',0)}/{N_SOL} | "
        f"{hh.get('E_psi_f',0):.4e} |\n"
    )

    with open(ck, "a", encoding="utf-8") as f:
        f.write(block)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_leech()
    sys.exit(0)
