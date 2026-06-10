"""
================================================================================
COLLASSO DINAMICO: la materia MIGRA e si AGGREGA (collasso gravitazionale)?
================================================================================

Domanda di Luca (la prova FORTE della gravita'): la materia si CONCENTRA nel tempo
(i difetti si fondono in meno grumi, piu' densi), o resta dove e' stata seminata?

Due esiti registrati in questo folder:
  1) MOTORE EC SENZA ADVEZIONE (NOTE.md, prima versione): il clumping e' CINEMATICO.
     Il fattore di scala 'a' espande i vuoti piu' della materia, ma 'a' NON trasporta
     chi tra i voxel -> la concentrazione C resta PIATTA. Niente migrazione.
  2) MOTORE EC + ADVEZIONE M1 (questo test): la metrica retroagisce sul campo. chi e'
     advettato da  u = -mu * grad(f),  f = 1 - K2_spin/rho*  per-voxel (= potenziale
     gravitazionale: lo STESSO f che dilata il tempo TRASCINA la materia). Al kink K2 e'
     alta -> f ha un minimo (al cuore f<0: tempo invertito) -> chi confluisce -> i difetti
     si FONDONO = COLLASSO. Forma conservativa upwind sull'anello: somma(chi) invariata.

METRICA (derivata SOLO dal campo chi -> confronto apples-to-apples EC/legacy):
  per ogni voxel  slope=(chi_{i+1}-chi_{i-1})/(2 chi0); theta=2 atan|slope|;
                  rho_SX = sin^2(theta/2)              (DENSITA' DI MATERIA chirale).
  CONCENTRAZIONE  C = Var_i(rho_SX_i) / media_i(rho_SX_i)^2   (sui voxel dell'anello).
                  cresce se i difetti si fondono in pochi grumi densi; piatta se diffusi.

CRITERIO FALSIFICABILE:
  - COLLASSO/GRAVITA' VERA:  C(t) CRESCE col motore EC+M1, e PIU' del null legacy (mu=0).
  - SOLO dinamica di campo:  C(t) = al null legacy.
La finestra di mobilita': mu troppo piccolo -> la diffusione numerica vince (no collasso);
mu troppo grande -> over-driving (l'anello si destabilizza, C cala). C'e' un mu ottimale.

Nessun valore hardcoded di fisica: chi0 da physics.chi_stable, rho*=2chi0^2 derivato,
180/720 topologici. mu = UNA mobilita' di trasporto (non e' una legge di scala 24^L).

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
from wqt_oop.motore_chirale_spinoriale import kink_slope, chirality_densities

MU_DEFAULT = 2.0          # sweet spot dello sweep (miglior media, |chi|max piu' basso)


def _matter_vox(root, chi0):
    """Densita' di materia chirale PER VOXEL (rho_SX), derivata SOLO dal campo chi."""
    chi = np.array([c.chi for c in root.children], dtype=float)
    slope = kink_slope(chi, chi0)
    theta = 2.0 * np.arctan(np.abs(slope))
    rho_sx, _ = chirality_densities(theta)
    return rho_sx


def _conc(rho_sx):
    """C = Var_i(rho_SX)/media_i(rho_SX)^2 sui voxel (concentrazione della materia)."""
    m = rho_sx.mean()
    return float(rho_sx.var() / (m * m)) if m > 1e-12 else 0.0


def _seed_ring(root, chi0, rng):
    """Campo iniziale IDENTICO per i due run: 4 domini sparsi (8 pareti = materia diffusa
    su molti kink) + piccolo rumore. La gravita' deve FONDERLI in pochi grumi."""
    patt = np.ones(len(root.children))
    for a, b in [(2, 5), (9, 11), (15, 16), (20, 22)]:
        patt[a:b] = -1.0
    for i, c in enumerate(root.children):
        c.chi = chi0 * patt[i] + 0.02 * chi0 * rng.standard_normal()
        c.vel = 0.0


def run_ring(mu, steps=600, dt=0.02, sample=20, seed=3):
    """Un anello (24 voxel). mu>0 -> motore EC completo + advezione M1; mu=0 -> evolve nudo
    (LEGACY null). Stesso campo iniziale. Ritorna (t[], C[], chimax[], C0, Cfin, chimax_fin)."""
    np.random.seed(seed)               # determinismo (il collasso e' sensibile alle IC)
    root = make(seed, chi_mean=50, level=1)
    chi0 = root.physics.chi_stable
    _seed_ring(root, chi0, np.random.default_rng(seed))
    if mu > 0:
        root.set_ec_integrato(1e-3)        # motore completo (spin->torsione->sat+esp+grav)
        root.set_advezione(mu)             # M1: advezione di chi da -grad(f)
    ts, Cs, mxs = [], [], []
    for s in range(steps + 1):
        if s % sample == 0:
            ts.append(s * dt)
            Cs.append(_conc(_matter_vox(root, chi0)))
            mxs.append(float(np.abs([c.chi for c in root.children]).max()))
        if s == steps:
            break
        root.compute_hamiltonian()
        root.evolve_with_muratore(dt) if mu > 0 else root.evolve(dt)
    chi = np.array([c.chi for c in root.children])
    assert not np.any(np.isnan(chi)), f"mu={mu}: NaN nel campo"
    return (np.array(ts), np.array(Cs), np.array(mxs), Cs[0], Cs[-1], mxs[-1])


def _growth_ensemble(mu, seeds, steps=600, dt=0.02):
    """Crescita media di C su un ENSEMBLE di semi (il collasso e' sensibile alle IC ->
    si misura la media). Ritorna (media, std, |chi|max medio)."""
    gr, mx = [], []
    for sd in seeds:
        _, _, _, C0, Cf, mxf = run_ring(mu, steps, dt, sample=steps, seed=sd)
        gr.append(Cf / (C0 + 1e-12)); mx.append(mxf)
    return float(np.mean(gr)), float(np.std(gr)), float(np.mean(mx))


def mu_sweep(mus=(0.0, 1.0, 2.0, 4.0, 8.0, 16.0), seeds=range(1, 9), steps=600, dt=0.02):
    """La finestra di collasso: crescita MEDIA di C (ensemble) vs mobilita' mu."""
    return [(mu, *_growth_ensemble(mu, list(seeds), steps, dt)) for mu in mus]


def _plot(t_lg, C_lg, t_m1, C_m1, sweep, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"  [plot saltato: {e}]")
        return None
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].plot(t_m1, C_m1 / (C_m1[0] + 1e-12), "-", color="green", lw=2.5,
               label=f"EC + M1 (advezione -grad f)")
    ax[0].plot(t_lg, C_lg / (C_lg[0] + 1e-12), "--", color="steelblue", lw=2,
               label="legacy (EC off, null)")
    ax[0].axhline(1.0, color="gray", ls=":", lw=1)
    ax[0].set_xlabel("tempo"); ax[0].set_ylabel("C(t)/C(0)  (concentrazione materia)")
    ax[0].set_title("Collasso gravitazionale: la materia si fonde?")
    ax[0].legend(); ax[0].grid(alpha=0.3)
    mus = [s[0] for s in sweep]; gr = [s[1] for s in sweep]
    ax[1].plot(mus, gr, "-o", color="crimson", lw=2)
    ax[1].axhline(1.0, color="gray", ls=":", lw=1)
    ax[1].set_xlabel("mobilita' mu"); ax[1].set_ylabel("crescita C(fine)/C(0)")
    ax[1].set_title("Finestra di collasso (mu ottimale)"); ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_png, dpi=110); plt.close(fig)
    return out_png


def main():
    mu = MU_DEFAULT
    seeds = list(range(1, 9))          # ensemble di 8 semi (collasso sensibile alle IC)
    print("=" * 78)
    print("  COLLASSO DINAMICO (anello): la materia si aggrega sotto -grad(f) = gravita'?")
    print("=" * 78)
    # serie temporale di esempio (un seme) per la figura
    lg = run_ring(0.0, seed=3)
    m1 = run_ring(mu, seed=3)
    t_lg, C_lg = lg[0], lg[1]
    t_m1, C_m1 = m1[0], m1[1]
    # confronto APPAIATO per-seme (potente: il null e' ~1.000 sempre, M1 e' a una coda >=1)
    gl = np.array([run_ring(0.0, seed=sd)[4] / (run_ring(0.0, seed=sd)[3] + 1e-12) for sd in seeds])
    gm, mxm = [], []
    for sd in seeds:
        r = run_ring(mu, seed=sd); gm.append(r[4] / (r[3] + 1e-12)); mxm.append(r[5])
    gm = np.array(gm); mxm = np.array(mxm)
    g_lg, s_lg = float(gl.mean()), float(gl.std())
    g_m1, s_m1, mx_m1 = float(gm.mean()), float(gm.std()), float(mxm.mean())
    wins = int(np.sum(gm > gl + 1e-6))                 # semi in cui M1 batte il null
    print(f"  CONCENTRAZIONE C=Var_i(rho_SX)/media^2 sui 24 voxel (materia chirale).")
    print(f"  Crescita C(fine)/C(0) su {len(seeds)} semi (ensemble; collasso e' caotico):")
    print(f"    LEGACY (null) : media x{g_lg:.3f} +/- {s_lg:.3f}  (range [{gl.min():.3f}, {gl.max():.3f}])")
    print(f"    EC + M1 mu={mu} : media x{g_m1:.3f} +/- {s_m1:.3f}  (range [{gm.min():.3f}, {gm.max():.3f}])")
    print(f"    confronto APPAIATO: M1 > null in {wins}/{len(seeds)} semi  |chi|max medio={mx_m1:.1f} (<1e4)")
    print()
    print(f"  FINESTRA DI COLLASSO (crescita C media su {len(seeds)} semi vs mobilita' mu):")
    sweep = mu_sweep(seeds=seeds)
    for mu_i, gr_i, sd_i, mx_i in sweep:
        flag = "<- collasso" if gr_i > 1.05 + sd_i else ("<- null" if mu_i == 0 else "")
        print(f"    mu={mu_i:5.1f} : C x{gr_i:.3f} +/- {sd_i:.3f}   |chi|max={mx_i:5.1f}   {flag}")
    png = _plot(t_lg, C_lg, t_m1, C_m1, sweep, os.path.join(HERE, "collasso_dinamico.png"))
    if png:
        print(f"\n  figura: {png}")
    print("-" * 78)
    stabile = mx_m1 < 1e4 and not np.isnan(mx_m1)
    collapse = g_m1 > 1.05
    # criterio appaiato (a una coda): M1 batte il null nella grande maggioranza dei semi
    beats_null = wins >= int(0.75 * len(seeds)) and g_lg < 1.01
    if collapse and beats_null and stabile:
        print(f"  VERDETTO: COLLASSO -> con l'advezione da -grad(f) la materia si AGGREGA")
        print(f"            (C x{g_m1:.2f} in media, M1>null in {wins}/{len(seeds)} semi) mentre il null")
        print(f"            legacy resta PIATTO (x{g_lg:.3f}), stabile. La parola 'gravita'' e' GUADAGNATA:")
        print(f"            lo stesso f che dilata il tempo trascina la materia e fonde i difetti.")
    elif collapse and not beats_null:
        print(f"  VERDETTO: C cresce (x{g_m1:.2f}) ma non batte il null in modo robusto -> non conclusivo.")
    elif collapse and not stabile:
        print(f"  VERDETTO: concentra (x{g_m1:.2f}) ma INSTABILE (|chi|max={mx_m1:.1e}): mu troppo alto.")
    else:
        print(f"  VERDETTO: a mu={mu} la materia NON collassa in media (C x{g_m1:.2f}); vedi sweep.")


if __name__ == "__main__":
    main()
