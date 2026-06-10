"""
================================================================================
COLLASSO GERARCHICO: la materia si aggrega anche TRA i blocchi (L2)?
================================================================================

Task A (gerarchia chirale). Al task 1 questo STESSO setup inter-blocco dava C piatta
(clumping cinematico): l'advezione M1 agiva solo dentro gli anelli L1 e la torsione a
L2 ricadeva sul gradiente scalare coarse. Ora il motore ha:
  - OPERATORE DI PROIEZIONE CHIRALE bloch_aggregate (L_n -> L_{n+1}): n del blocco =
    media ricorsiva dei Bloch; n_z = <cos theta> = chiralita' netta che RISALE la
    gerarchia, |n|<1 = depolarizzazione;
  - TORSIONE DALLO SPIN A TUTTI I LIVELLI: K2_bloch = chi0^2 sum W |n_i-n_j|^2 sui
    Bloch aggregati (apply_muratore_step L2+);
  - ADVEZIONE GERARCHICA: chi coarse advettato TRA i blocchi da u=-mu*grad(f_coarse),
    f_coarse=1-K2_bloch/rho*, upwind conservativo sul ring dei figli; dchi distribuito
    alle foglie. Stesso mu derivato (rho*/chi0^2=2).

METRICA (la STESSA del task 1, derivata SOLO dal campo): D_b = media(rho_SX) per blocco
L1; C_inter = Var_b(D_b)/media_b(D_b)^2.

CRITERIO (intuizione di Luca): vicino alla scala di Planck c'e' POCA massa (1 parete su
24 voxel = rho_SX~2%: blocchi quasi vuoti) -> la gravita' inter-blocco e' in REGIME DI
CAMPO DEBOLE (segnale piccolo). La firma falsificabile della gravita' non e' "collassa
tanto" ma "IL COLLASSO SCALA CON LA MASSA": piu' pareti nei blocchi densi -> piu'
chiralita' netta -> piu' K2_bloch -> piu' aggregazione. Il null legacy resta piatto a
OGNI massa.

CHECK DI COERENZA: (1) un passo di advezione conserva ESATTAMENTE somma(chi);
(2) K2_bloch a L2 vede il contrasto materia/vuoto (>0 tra blocchi diversi).

ESECUZIONE:  python experiments/collasso_gerarchico/test_collasso_gerarchico.py
================================================================================
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ROOT = os.path.dirname(EXP)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(EXP, "exp3"))
import numpy as np
from test_soglia_formazione import make
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.motore_chirale_spinoriale import (kink_slope, chirality_densities,
                                               spin_torsion_K2_bloch)


def _l1_blocks(root):
    acc = []
    def w(n):
        if n.children and isinstance(n.children[0], SegmentoQuantistico):
            acc.append(n)
        else:
            for c in n.children:
                if isinstance(c, SolitoneComposito):
                    w(c)
    w(root); return acc


def _matter_density(block, chi0):
    chi = np.array([leaf.chi for leaf in block.children], dtype=float)
    theta = 2.0 * np.arctan(np.abs(kink_slope(chi, chi0)))
    rho_sx, _ = chirality_densities(theta)
    return float(rho_sx.mean())


def _conc_inter(blocks, chi0):
    D = np.array([_matter_density(b, chi0) for b in blocks])
    m = D.mean()
    return (float(D.var() / (m * m)) if m > 1e-12 else 0.0), D


def _seed_field(blocks, chi0, n_dense, rng, period=None):
    """n_dense blocchi DENSI sparsi, resto vuoto. period=None -> 1 parete (mezzo su /
    mezzo giu', come al task 1); period=p -> domini alternati ogni p voxel (24/p pareti:
    piu' MASSA per blocco). Il vuoto e' uniforme +chi0."""
    idx = set(int(i) for i in rng.permutation(len(blocks))[:n_dense])
    for j, b in enumerate(blocks):
        for i, leaf in enumerate(b.children):
            if j in idx:
                if period is None:
                    base = chi0 if i < len(b.children) // 2 else -chi0
                else:
                    base = chi0 if (i // period) % 2 == 0 else -chi0
            else:
                base = chi0
            leaf.chi = base + 0.01 * chi0 * rng.standard_normal()
            leaf.vel = 0.0


def _total_chi(blocks):
    return float(sum(leaf.chi for b in blocks for leaf in b.children))


def check_coerenza(seed=7, n_dense=6):
    """(1) conservazione esatta di somma(chi) in un passo di advezione gerarchica;
    (2) la proiezione chirale vede il contrasto materia/vuoto a L2 (K2_bloch>0)."""
    np.random.seed(seed)
    root = make(seed, chi_mean=50, level=2)
    blocks = _l1_blocks(root)
    chi0 = root.physics.chi_stable
    _seed_field(blocks, chi0, n_dense, np.random.default_rng(seed))
    root.set_ec_integrato(1e-3)
    tot0 = _total_chi(blocks)
    root.apply_advezione_gravitazionale_step(0.02)     # SOLO advezione (gerarchica+anello)
    tot1 = _total_chi(blocks)
    err = abs(tot1 - tot0) / (abs(tot0) + 1e-30)
    n = np.array([c.bloch_aggregate() for c in root.children])
    W = root.coupling_matrix
    W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
    K2 = spin_torsion_K2_bloch(n, W, chi0)
    assert err < 1e-12, f"advezione NON conserva chi: err={err:.2e}"
    assert K2.max() > 0.0, "proiezione chirale cieca: K2_bloch=0 con materia/vuoto"
    print(f"  [coerenza] somma(chi) conservata (err={err:.1e});  "
          f"K2_bloch L2 in [{K2.min():.2e}, {K2.max():.2e}] (vede il contrasto);  "
          f"|n| aggregati in [{np.linalg.norm(n, axis=1).min():.3f}, "
          f"{np.linalg.norm(n, axis=1).max():.3f}] (depolarizzazione) -> PASS")


def run(mode, n_dense=6, steps=600, dt=0.02, sample=50, seed=7, period=None):
    """mode='ec' -> motore completo (con gerarchia chirale); 'legacy' -> evolve nudo."""
    np.random.seed(seed)
    root = make(seed, chi_mean=50, level=2)
    blocks = _l1_blocks(root)
    chi0 = root.physics.chi_stable
    _seed_field(blocks, chi0, n_dense, np.random.default_rng(seed), period=period)
    if mode == "ec":
        root.set_ec_integrato(1e-3)
    ts, Cs = [], []
    for s in range(steps + 1):
        if s % sample == 0:
            C, _ = _conc_inter(blocks, chi0)
            ts.append(s * dt); Cs.append(C)
        if s == steps:
            break
        root.compute_hamiltonian()
        root.evolve_with_muratore(dt) if mode == "ec" else root.evolve(dt)
    chi_all = np.array([l.chi for b in blocks for l in b.children])
    assert not np.any(np.isnan(chi_all)), f"{mode}: NaN"
    return np.array(ts), np.array(Cs), float(np.abs(chi_all).max())


def _plot(t, curves, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"  [plot saltato: {e}]")
        return None
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for label, C, style, color in curves:
        ax.plot(t, C / (C[0] + 1e-12), style, color=color, lw=2, label=label)
    ax.axhline(1.0, color="gray", ls=":", lw=1)
    ax.set_xlabel("tempo"); ax.set_ylabel("C_inter(t)/C_inter(0)")
    ax.set_title("Collasso GERARCHICO: concentrazione TRA blocchi (L2)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)
    return out_png


MASSE = [("1 parete (Planck: quasi vuoto)", None),
         ("4 pareti", 6),
         ("8 pareti (denso)", 3)]


def main():
    seeds = list(range(1, 5))
    print("=" * 78)
    print("  COLLASSO GERARCHICO: l'aggregazione TRA blocchi SCALA CON LA MASSA?")
    print("=" * 78)
    check_coerenza()
    print()
    print(f"  C_inter=Var_b(D_b)/media^2 sui 24 blocchi L1; crescita su {len(seeds)} semi")
    print(f"  per TRE masse dei blocchi densi (campo debole -> denso):")
    rows = []
    for label, period in MASSE:
        gl, gm, mxs = [], [], []
        for sd in seeds:
            _, C_lg, _ = run("legacy", seed=sd, period=period)
            _, C_ec, mx = run("ec", seed=sd, period=period)
            gl.append(C_lg[-1] / (C_lg[0] + 1e-12))
            gm.append(C_ec[-1] / (C_ec[0] + 1e-12))
            mxs.append(mx)
        gl, gm = np.array(gl), np.array(gm)
        wins = int(np.sum(gm > gl + 1e-6))
        rows.append((label, float(gl.mean()), float(gm.mean()), float(gm.std()),
                     wins, float(np.mean(mxs))))
        print(f"    {label:32s}: null x{gl.mean():.3f}  EC x{gm.mean():.3f} +/- {gm.std():.3f}"
              f"   EC>null {wins}/{len(seeds)}  |chi|max={np.mean(mxs):.0f}")
    # serie temporale di esempio (massa piena) per la figura
    t, C_lg, _ = run("legacy", seed=2, period=3)
    _, C_ec, _ = run("ec", seed=2, period=3)
    png = _plot(t, [("motore EC (8 pareti)", C_ec, "-", "green"),
                    ("legacy (null)", C_lg, "--", "steelblue")],
                os.path.join(HERE, "collasso_gerarchico.png"))
    if png:
        print(f"  figura: {png}")
    print("-" * 78)
    g_ec = [r[2] for r in rows]; g_nl = [r[1] for r in rows]
    wins_tot = sum(r[4] for r in rows); n_tot = len(MASSE) * len(seeds)
    monotono = all(g_ec[k + 1] > g_ec[k] for k in range(len(g_ec) - 1))
    null_piatto = max(g_nl) < 1.01
    stabile = max(r[5] for r in rows) < 1e4
    if monotono and null_piatto and wins_tot >= int(0.75 * n_tot) and stabile:
        print(f"  VERDETTO: GRAVITA' GERARCHICA CONFERMATA -> il collasso inter-blocco SCALA")
        print(f"            CON LA MASSA ({' -> '.join(f'x{g:.3f}' for g in g_ec)}; null piatto a")
        print(f"            ogni massa; EC>null {wins_tot}/{n_tot}; stabile). A scala ~Planck il")
        print(f"            campo e' DEBOLE (poca massa per blocco) ma la firma c'e': la")
        print(f"            chiralita' risale la gerarchia e la gravita' agisce TRA i blocchi.")
        print(f"            Il task 1 e' riscattato (intuizione di Luca: serviva la massa).")
    elif not monotono:
        print(f"  VERDETTO: NON scala con la massa ({' -> '.join(f'x{g:.3f}' for g in g_ec)}):")
        print(f"            non e' gravita' (o la proiezione satura male). Indagare K2_bloch.")
    else:
        print(f"  VERDETTO: non conclusivo (wins {wins_tot}/{n_tot}, null x{max(g_nl):.3f},")
        print(f"            stabile={stabile}).")


if __name__ == "__main__":
    main()
