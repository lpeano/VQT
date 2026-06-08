"""
================================================================================
P7 — DECOMPOSIZIONE SPETTRALE A DUE CANALI (ampiezza vs fase) sui cluster Z_24
================================================================================

Implementa il test di FORMALIZZAZIONE_MASSA_TOPOLOGICA.md sez. 8. Il parametro
d'ordine del cluster psi_B = m_B * exp(i*phi_B) si separa in:
  - canale RADIALE  (ampiezza m_B = <tanh(chi/chi0)>): la MASSA (Higgs-like, localizz.)
  - canale di FASE  (phi_B dal settore tau spinoriale): la PROPAGAZIONE (Goldstone-like)
La fase si decompone nei 24 modi di Fourier dell'anello Z_24 dei cluster. I periodi
24/gcd(m,24) SONO i divisori di 24 -> struttura della BASE, esatta e field-independent.

ATTENZIONE (gotcha): NON usa l'integratore spettrale (bug deriva 38%). Usa solo la
DFT (np.fft), che su un anello circolante coincide con l'autobase di SpectralBasis
ed e' esatta (roundtrip 1e-15). Qui "ascoltiamo" un campo FERMO, non lo evolviamo.

PARTE A (sempre, istantanea, nessun quench): struttura della base dei modi della
  matrice di accoppiamento Z_24 (autovalori lambda_m, periodi = divisori di 24).
PARTE B (--quench): genera un campo congelato (i campi delle campagne NON sono
  salvati su disco) e ne decompone ampiezza e fase; split di energia + ortogonalita'.

NB ONESTA': un difetto PUNTUALE singolo e' una quasi-delta -> spettro SPALMATO su
tutti i modi (atteso, NON struttura). La concentrazione su modi-divisore richiede un
pattern COLLETTIVO commensurato (plasma/onda coerente).

ESECUZIONE:
  cd VQT_repo
  python experiments/exp3/analyze_spettro_cluster.py --level 2          # solo Parte A
  python experiments/exp3/analyze_spettro_cluster.py --level 2 --quench --chi-mean 72
================================================================================
"""

import sys, os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
from math import gcd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments", "exp3"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGDIR = os.path.join(ROOT, "experiments", "exp3", "figures")
os.makedirs(FIGDIR, exist_ok=True)
CHI_STABLE = 50.0
DIVISORS_24 = [1, 2, 3, 4, 6, 8, 12, 24]


def _dense(W):
    return W.toarray() if hasattr(W, "toarray") else np.asarray(W)


def parte_A_base(root):
    """Struttura della base dei modi della matrice circolante Z_24 (24 cluster)."""
    W = _dense(root.coupling_matrix)
    n = W.shape[0]
    # autovalori del circolante = DFT della prima riga (reale per W simmetrica)
    lam = np.fft.fft(W[0, :]).real
    print("  [A] BASE DEI MODI dell'anello dei cluster (Z_%d)" % n)
    print("      mode m | periodo 24/gcd(m,24) | lambda_m (autovalore coupling)")
    print("      " + "-" * 56)
    # raggruppa per periodo (= divisore)
    by_period = {}
    for m in range(n):
        per = n // gcd(m, n)
        by_period.setdefault(per, []).append((m, lam[m]))
    for per in sorted(by_period):
        modi = by_period[per]
        ms = ",".join(str(m) for m, _ in modi)
        lvals = np.array([l for _, l in modi])
        flag = "  <-- divisore di 24" if (per in DIVISORS_24 and n == 24) else ""
        print(f"      periodo {per:>2}: modi m=[{ms:<22}] lambda~{lvals.mean():+.4f}{flag}")
    print("      -> i periodi sono ESATTAMENTE i divisori di %d: %s" %
          (n, sorted(by_period.keys())))
    print("      (struttura della BASE: esatta, indipendente dal campo)")
    return lam


def _leaves_chi_tau(node):
    """Raccoglie (chi, tau) di tutte le foglie sotto node, ricorsivamente."""
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    chi, tau = [], []
    def walk(n):
        if isinstance(n, SegmentoQuantistico):
            chi.append(float(n.chi))
            tau.append(float(getattr(n, "tau_locale", getattr(n, "tau", 0.0))))
        else:
            for c in n.children:
                walk(c)
    walk(node)
    return np.array(chi), np.array(tau)


def parte_B_campo(root):
    """psi_B per cluster (figli diretti del root) -> DFT ampiezza e fase."""
    children = root.children
    n = len(children)
    m_B, phi_B = np.zeros(n), np.zeros(n)
    for i, c in enumerate(children):
        chi, tau = _leaves_chi_tau(c)
        m_B[i] = np.mean(np.tanh(chi / CHI_STABLE))          # ampiezza (magnetizzazione)
        phi_B[i] = np.mean(tau)                               # fase (settore spinoriale)
    # DFT su Z_n
    A = np.fft.fft(m_B)                                       # canale radiale
    P = np.fft.fft(phi_B - phi_B.mean())                     # canale di fase (no DC)
    pow_amp = np.abs(A) ** 2
    pow_pha = np.abs(P) ** 2

    print("\n  [B] DECOMPOSIZIONE DEL CAMPO CONGELATO (%d cluster)" % n)
    print(f"      m_B (ampiezza): range [{m_B.min():+.3f}, {m_B.max():+.3f}], "
          f"std={m_B.std():.4f}")
    print(f"      phi_B (fase tau): range [{phi_B.min():+.3f}, {phi_B.max():+.3f}], "
          f"std={phi_B.std():.4f}")

    # energia nei due canali (somma delle potenze AC, modi 1..n-1)
    E_amp = float(pow_amp[1:].sum())
    E_pha = float(pow_pha[1:].sum())
    print(f"\n      ENERGIA canale RADIALE (ampiezza/massa) = {E_amp:.4e}")
    print(f"      ENERGIA canale FASE (propagazione)      = {E_pha:.4e}")

    # ortogonalita': cross-correlazione tra i due segnali spaziali
    a = m_B - m_B.mean(); b = phi_B - phi_B.mean()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-30
    xcorr = float(np.dot(a, b) / denom)
    print(f"      CROSS-CORRELAZIONE radiale-fase = {xcorr:+.3f}  "
          f"({'ORTOGONALI (~0)' if abs(xcorr) < 0.2 else 'ACCOPPIATI'})")

    # dove sta la potenza di fase? concentrata o spalmata?
    if E_pha > 1e-30:
        frac = pow_pha[1:] / E_pha
        flat = 1.0 / (n - 1)                                  # spettro piatto = 1/(n-1) per modo
        ipr = float(np.sum(frac ** 2))                        # 1/(n-1)=spalmato, ->1=concentrato
        print(f"      spettro di FASE: IPR={ipr:.3f} (piatto={flat:.3f}); "
              f"{'CONCENTRATO' if ipr > 3*flat else 'SPALMATO (atteso per difetto singolo)'}")
        # i 3 modi di fase piu' forti
        top = np.argsort(pow_pha[1:])[::-1][:3] + 1
        print("      modi di fase dominanti: " +
              ", ".join(f"m={m}(per {n//gcd(m,n)})" for m in top))
    return m_B, phi_B, pow_amp, pow_pha


def _find_defect_block(root, chi0):
    """Trova il blocco L1 (figli = segmenti) che contiene la foglia piu' deviata dal
    pozzo dominante. Probe LOCALE: il difetto e' 1 su 24, NON diluito come nel top-ring.
    Ritorna (block, dev_max)."""
    from wqt_oop.segmento_quantistico import SegmentoQuantistico
    allchi = []
    def gather(n):
        if isinstance(n, SegmentoQuantistico):
            allchi.append(n.chi)
        else:
            for c in n.children:
                gather(c)
    gather(root)
    pozzo = chi0 * (1.0 if np.mean(allchi) >= 0 else -1.0)
    best, best_dev = None, -1.0
    def scan(n):
        nonlocal best, best_dev
        if n.children and isinstance(n.children[0], SegmentoQuantistico):
            dev = max(abs(c.chi - pozzo) for c in n.children)
            if dev > best_dev:
                best_dev, best = dev, n
        else:
            for c in n.children:
                if not isinstance(c, SegmentoQuantistico):
                    scan(c)
    scan(root)
    return best, best_dev


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P7 - spettro a due canali sui cluster Z_24")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--chi-mean", type=float, default=72.0)
    ap.add_argument("--quench", action="store_true",
                    help="genera un campo congelato e fa la Parte B (altrimenti solo A)")
    ap.add_argument("--local", action="store_true",
                    help="analizza il RING LOCALE (24 segmenti del blocco L1 che contiene "
                         "il difetto) invece del top-ring globale: probe non diluito")
    ap.add_argument("--pre", type=int, default=40)
    ap.add_argument("--quench-steps", type=int, default=500)
    args = ap.parse_args()

    np.random.seed(args.seed + 100003 * int(round(args.chi_mean)))
    from test_soglia_formazione import make
    print("=" * 70)
    print(f"  P7 - SPETTRO CLUSTER  L{args.level}  (chi_mean={args.chi_mean:.0f})")
    print("=" * 70)

    sol = make(args.seed, chi_mean=args.chi_mean, level=args.level)
    lam = parte_A_base(sol)

    if args.quench:
        from wqt_oop.energy_metrics import (freeze_and_measure_mass,
                                            compute_hierarchical_mass)
        dt = 0.01
        for _ in range(args.pre):
            sol.compute_hamiltonian(); sol.evolve(dt)
        r = freeze_and_measure_mass(sol, max_steps=args.quench_steps, dt=dt,
                                    return_frozen=True)
        frozen = r["frozen"]
        M_tot = compute_hierarchical_mass(frozen)["M_tot"]
        print(f"\n  Campo congelato: M_tot = {M_tot:.3e} "
              f"({'KINK (difetto presente)' if M_tot > 1 else 'vuoto'})")
        if args.local:
            chi0 = getattr(frozen.physics, "chi_stable", CHI_STABLE)
            target, dev = _find_defect_block(frozen, chi0)
            print(f"  PROBE LOCALE: ring L1 del difetto (deviazione max {dev:.1f} dal "
                  f"pozzo). I 24 SEGMENTI di quel blocco, non i cluster globali.")
        else:
            target = frozen
            print(f"  PROBE GLOBALE: top-ring (24 cluster diretti del root). "
                  f"NB a L>=3 il difetto e' diluito qui (usa --local).")
        m_B, phi_B, pow_amp, pow_pha = parte_B_campo(target)

        # grafico
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        n = len(m_B)
        axes[0, 0].stem(range(n), m_B); axes[0, 0].set_title("m_B (ampiezza / massa) per cluster")
        axes[0, 1].stem(range(n), phi_B); axes[0, 1].set_title("phi_B (fase / tau) per cluster")
        axes[1, 0].stem(range(1, n), pow_amp[1:]); axes[1, 0].set_title("spettro RADIALE |DFT(m_B)|^2")
        axes[1, 0].set_xlabel("modo m")
        axes[1, 1].stem(range(1, n), pow_pha[1:]); axes[1, 1].set_title("spettro FASE |DFT(phi_B)|^2")
        axes[1, 1].set_xlabel("modo m")
        for m in DIVISORS_24:
            mm = n // m
            if 1 <= mm < n:
                axes[1, 1].axvline(mm, color="red", ls=":", alpha=0.3)
        fig.suptitle(f"Spettro a due canali L{args.level} chi_mean={args.chi_mean:.0f} "
                     f"(M_tot={M_tot:.1e})", fontweight="bold")
        fig.tight_layout()
        tag = "local" if args.local else "global"
        out = os.path.join(FIGDIR,
                           f"spettro_cluster_L{args.level}_cm{args.chi_mean:.0f}_{tag}.png")
        fig.savefig(out, dpi=120); plt.close(fig)
        print(f"\n  Grafico salvato: {out}")
    else:
        print("\n  (Parte B saltata: aggiungi --quench per generare e analizzare un campo.)")


if __name__ == "__main__":
    main()
