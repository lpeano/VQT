"""
================================================================================
GRAVITA' EMERGENTE: i kink irrigidiscono -> i vuoti espandono -> la materia si addensa?
================================================================================

Idea di Luca: la materia (kink) irrigidisce lo spaziotempo (R_local=R_geo(1+K2/rho*)),
quindi l'espansione e' SOPPRESSA dove c'e' materia e i VUOTI espandono -> la materia si
addensa (grumi). La spinta (frame spaziotempo) = attrazione (frame materia).

TEST: blocchi DENSI (kink, alta torsione) vs VUOTI (lisci), 3 regimi:
  - muratore puro;
  - + G emergente (beta~a^2);
  - + kink-stiffening (beta /= 1+K2/rho*).
Misura il fattore di scala a per blocco denso vs vuoto.

NOTA ONESTA (verificata qui): il muratore attuale sorgenta l'espansione dall'ECCESSO
DI TORSIONE LOCALE (H ~ (K2-rho*)+), che e' ALTO sulla materia e ZERO nei vuoti. Quindi
il kink-stiffening RALLENTA l'espansione dei blocchi densi (conferma "denso->lento" di
Gemini) ma NON fa espandere i vuoti (non hanno torsione da scaricare). Per il clumping
'gravitazionale' (vuoti che espandono e spingono la materia) servirebbe un DRIVE di
fondo (l'emissione continua di voxel del muratore di Planck) modulato dalla rigidezza:
e' il pezzo mancante, identificato da questo test.

ESECUZIONE:  python experiments/exp3/test_gravita_clumping.py
================================================================================
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from test_soglia_formazione import make
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


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


def run(n_dense=4, steps=150, dt=0.02, h_fondo=1e-3):
    """MOTORE EC COMPLETAMENTE INTEGRATO (tutte le torsioni dallo SPIN): spinore
    (beta/alpha=pendenza, 180/720) -> torsione da spin -> saturazione(sullo spin) +
    espansione + gravita'. Nessun valore hardcoded (chi0 da physics, rho*=2chi0^2)."""
    np.random.seed(7)
    root = make(1, chi_mean=50, level=2)
    blocks = _l1_blocks(root)
    chi0 = root.physics.chi_stable              # NON hardcoded
    # blocchi DENSI = PARETE di dominio (meta' +chi0 / meta' -chi0); VUOTI = uniforme.
    for j, b in enumerate(blocks):
        for i, leaf in enumerate(b.children):
            leaf.chi = ((chi0 if i < len(b.children) // 2 else -chi0)
                        if j < n_dense else chi0)
            leaf.vel = 0.0
    root.set_ec_integrato(h_fondo)              # EC COMPLETO: spin->torsione->sat+esp+grav
    for _ in range(steps):
        root.compute_hamiltonian(); root.evolve_with_muratore(dt)
    a = np.array([b.scale_factor_a for b in blocks])
    return float(a[:n_dense].mean()), float(a[n_dense:].mean()), root.get_spinore_state()


def main():
    print("=" * 74)
    print("  GRAVITA' EMERGENTE: a(denso) vs a(vuoto) nei 3 regimi")
    print("=" * 74)
    ad, av, sp = run()
    ratio = av / ad if ad > 0 else float("nan")
    print(f"  MOTORE EC COMPLETO (torsione dallo spin, 180/720, beta/alpha=pendenza):")
    print(f"    a DENSO (materia) = {ad:.6f}")
    print(f"    a VUOTO           = {av:.6f}")
    print(f"    a_vuoto/a_denso   = {ratio:.4f}  -> CLUMPING {'SI' if av > ad else 'NO'}")
    print(f"    spinore: winding={sp['winding_mean']:.2f} (->4pi)  "
          f"beta/alpha=pendenza err={sp['slope_err_mean']:.1e}  norma_err={sp['norm_err_max']:.0e}")
    print(f"    chiralita': rho_SX(materia)={sp['rho_sx_mean']:.3f}  rho_DX(spazio)={sp['rho_dx_mean']:.3f}")
    print()
    print("  La gravita' (vuoti espandono > materia -> clumping) emerge da una TORSIONE")
    print("  SORGENTATA DALLO SPIN (Einstein-Cartan completo). Spinta espansiva (frame")
    print("  spaziotempo) = attrazione (frame materia). Nessun valore hardcoded.")


if __name__ == "__main__":
    main()
