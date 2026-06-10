"""
================================================================================
COLLASSO DINAMICO: la materia MIGRA e si AGGREGA, o c'e' solo espansione differenziale?
================================================================================

Domanda di Luca (la prova FORTE della gravita'): sul motore completo (Einstein-Cartan
integrato, torsione dallo spin), su un run lungo, la MATERIA si CONCENTRA (la densita' di
difetti cresce nei grumi, i kink si addensano) oppure vediamo SOLO espansione differenziale
(a_vuoto > a_denso) senza vera migrazione?

METRICA (identica per i due motori, derivata dal CAMPO -> confronto apples-to-apples):
  per ogni voxel  slope = (chi_{i+1}-chi_{i-1})/(2 chi0);  theta = 2 atan|slope|;
                  rho_SX = sin^2(theta/2)              (DENSITA' DI MATERIA chirale).
  per ogni blocco L1:  D_b = media(rho_SX nel blocco)   ("massa"/difetto del blocco).
  CONCENTRAZIONE:      C = Var_b(D_b) / media_b(D_b)^2   (varianza relativa, adimensionale).
                       (cresce se la materia si addensa in pochi blocchi; piatta se diffusa).

CRITERIO FALSIFICABILE:
  - COLLASSO/GRAVITA' VERA:   C(t) CRESCE nel tempo (la materia si aggrega).
  - SOLO ESPANSIONE DIFF.:    C(t) piatta/in calo mentre a_vuoto/a_denso diverge.
NULL/CONTROLLO: stesso campo iniziale, motore LEGACY (EC OFF, evolve nudo). La gravita' EC
  e' reale solo se C_EC cresce PIU' di C_legacy (oltre la dinamica di campo nuda).

Nessun valore hardcoded: chi0 da physics.chi_stable, rho*=2chi0^2 derivato, 180/720 topologici.

ESECUZIONE:  python experiments/collasso_dinamico/test_collasso_dinamico.py
================================================================================
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))               # experiments/collasso_dinamico
EXP = os.path.dirname(HERE)                                     # experiments
ROOT = os.path.dirname(EXP)                                     # repo root
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(EXP, "exp3"))                  # test_soglia_formazione.make
import numpy as np
from test_soglia_formazione import make
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.motore_chirale_spinoriale import kink_slope, chirality_densities


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
    """D_b = densita' di materia chirale del blocco, derivata SOLO dal campo chi
    (vale identica per motore EC e legacy)."""
    chi = np.array([leaf.chi for leaf in block.children], dtype=float)
    slope = kink_slope(chi, chi0)                  # pendenza del kink (centered diff /2chi0)
    theta = 2.0 * np.arctan(np.abs(slope))
    rho_sx, _ = chirality_densities(theta)         # sin^2(theta/2) = materia
    return float(rho_sx.mean())


def _concentration(blocks, chi0):
    """C = Var_b(D_b)/media_b(D_b)^2 + vettore D_b (per ispezione)."""
    D = np.array([_matter_density(b, chi0) for b in blocks])
    m = D.mean()
    C = float(D.var() / (m * m)) if m > 1e-12 else 0.0
    return C, D


def _seed_field(root, blocks, chi0, n_dense, rng):
    """Campo iniziale IDENTICO per i due run: n_dense blocchi = parete di dominio (kink,
    materia) sparsi, gli altri = vuoto quasi-uniforme. Piccolo rumore per rompere la
    simmetria (semina di instabilita')."""
    idx = rng.permutation(len(blocks))[:n_dense]           # blocchi densi a caso
    dense = set(int(i) for i in idx)
    for j, b in enumerate(blocks):
        for i, leaf in enumerate(b.children):
            if j in dense:
                leaf.chi = (chi0 if i < len(b.children) // 2 else -chi0)
            else:
                leaf.chi = chi0
            leaf.chi += 0.01 * chi0 * rng.standard_normal()    # rumore di semina
            leaf.vel = 0.0


def run(mode, n_dense=6, steps=600, dt=0.02, sample=20, h_fondo=1e-3, seed=7):
    """Un run. mode='ec' -> motore completo; mode='legacy' -> evolve nudo (EC OFF).
    Ritorna (t[], C[], a_dense[], a_void[], D_final, sp)."""
    np.random.seed(seed)
    root = make(1, chi_mean=50, level=2)
    blocks = _l1_blocks(root)
    chi0 = root.physics.chi_stable
    _seed_field(root, blocks, chi0, n_dense, np.random.default_rng(seed))
    dense_mask = np.array([float(np.std([l.chi for l in b.children])) for b in blocks]) > 0.3 * chi0

    if mode == "ec":
        root.set_ec_integrato(h_fondo)             # motore completo: spin->torsione->sat+esp+grav

    ts, Cs, a_d, a_v = [], [], [], []
    for s in range(steps + 1):
        if s % sample == 0:
            C, _ = _concentration(blocks, chi0)
            a = np.array([b.scale_factor_a for b in blocks])
            ts.append(s * dt); Cs.append(C)
            a_d.append(float(a[dense_mask].mean()) if dense_mask.any() else 1.0)
            a_v.append(float(a[~dense_mask].mean()) if (~dense_mask).any() else 1.0)
        if s == steps:
            break
        root.compute_hamiltonian()
        if mode == "ec":
            root.evolve_with_muratore(dt)
        else:
            root.evolve(dt)                        # LEGACY nudo (controllo)

    _, D_final = _concentration(blocks, chi0)
    sp = root.get_spinore_state() if mode == "ec" else None
    chi_all = np.array([l.chi for b in blocks for l in b.children])
    assert not np.any(np.isnan(chi_all)), f"{mode}: NaN nel campo"
    return (np.array(ts), np.array(Cs), np.array(a_d), np.array(a_v), D_final, sp,
            float(np.abs(chi_all).max()))


def _plot(ec, lg, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"  [plot saltato: {e}]")
        return None
    t_ec, C_ec, ad_ec, av_ec = ec[0], ec[1], ec[2], ec[3]
    t_lg, C_lg = lg[0], lg[1]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].plot(t_ec, C_ec / (C_ec[0] + 1e-12), "-", color="crimson", lw=2,
               label="motore EC completo")
    ax[0].plot(t_lg, C_lg / (C_lg[0] + 1e-12), "--", color="steelblue", lw=2,
               label="legacy (EC off)")
    ax[0].axhline(1.0, color="gray", ls=":", lw=1)
    ax[0].set_xlabel("tempo"); ax[0].set_ylabel("C(t)/C(0)  (concentrazione materia)")
    ax[0].set_title("Collasso: la materia si concentra?"); ax[0].legend(); ax[0].grid(alpha=0.3)
    ax[1].plot(t_ec, ad_ec, "-", color="darkred", lw=2, label="a denso (materia)")
    ax[1].plot(t_ec, av_ec, "-", color="navy", lw=2, label="a vuoto")
    ax[1].set_xlabel("tempo"); ax[1].set_ylabel("fattore di scala a")
    ax[1].set_title("Espansione differenziale (controllo)"); ax[1].legend(); ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)
    return out_png


def main():
    print("=" * 78)
    print("  COLLASSO DINAMICO: migrazione/aggregazione della materia vs espansione diff.")
    print("=" * 78)
    ec = run("ec")
    lg = run("legacy")
    C_ec, C_lg = ec[1], lg[1]
    g_ec = C_ec[-1] / (C_ec[0] + 1e-12)
    g_lg = C_lg[-1] / (C_lg[0] + 1e-12)
    sp = ec[5]
    print(f"  CONCENTRAZIONE C(t)=Var_b(D_b)/media^2  (D_b=densita' materia per blocco L1)")
    print(f"    MOTORE EC : C(0)={C_ec[0]:.4e}  C(fine)={C_ec[-1]:.4e}  crescita x{g_ec:.3f}")
    print(f"    LEGACY    : C(0)={C_lg[0]:.4e}  C(fine)={C_lg[-1]:.4e}  crescita x{g_lg:.3f}")
    print(f"    rapporto crescita EC/legacy = {g_ec / (g_lg + 1e-12):.3f}")
    print(f"  ESPANSIONE (EC): a_denso(fine)={ec[2][-1]:.5f}  a_vuoto(fine)={ec[3][-1]:.5f}  "
          f"a_vuoto/a_denso={ec[3][-1] / (ec[2][-1] + 1e-12):.4f}")
    if sp:
        print(f"  spinore: winding={sp['winding_mean']:.2f}  beta/alpha=pendenza err="
              f"{sp['slope_err_mean']:.1e}  norma_err={sp['norm_err_max']:.0e}  "
              f"rho_SX={sp['rho_sx_mean']:.3f}")
    print(f"  |chi|max: EC={ec[6]:.1f}  legacy={lg[6]:.1f}  (stabilita')")
    png = _plot(ec, lg, os.path.join(HERE, "collasso_dinamico.png"))
    if png:
        print(f"  figura: {png}")
    print("-" * 78)
    # VERDETTO
    collapse_ec = g_ec > 1.05
    beats_legacy = g_ec > 1.05 * g_lg
    if collapse_ec and beats_legacy:
        print("  VERDETTO: COLLASSO -> la materia si AGGREGA col motore EC piu' che nel legacy")
        print("            (la parola 'gravita'' e' guadagnata: migrazione, non solo espansione).")
    elif collapse_ec:
        print("  VERDETTO: la concentrazione cresce ma NON oltre il legacy -> e' la dinamica di")
        print("            campo nuda, non un effetto gravitazionale EC. (onesto: non basta).")
    else:
        print("  VERDETTO: SOLO espansione differenziale (a_vuoto>a_denso), NESSUNA migrazione")
        print("            -> il clumping resta cinematico, non c'e' ancora collasso vero.")


if __name__ == "__main__":
    main()
