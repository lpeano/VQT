#!/usr/bin/env python3
"""
================================================================================
GENERATE TOPOLOGICAL DATASET - Produzione Dati VQT con Validazione Topologica
================================================================================

Script di produzione dati per il manifold frattale VQT.
Genera file HDF5 con ENTRAMBI i dataset:

  /frames/<frame_N>/          -> stato legacy (chi, v, tau, K², screening, H)
  /topological_validation/    -> metriche topologiche (ρ_constraint, fase, DOF,
                                 chiusura 720°, detorsione ±180°, H emergente)

PARADIGMA:
  Energia = proprietà EMERGENTE (catalogata, non vincolo)
  ρ_constraint = metrica primaria (indica clustering materia)

USO:
  # L1 veloce (48 DOF, ~30s)
  python generate_topological_dataset.py --level 1 --steps 300 --output cosmo_L1_topo.h5

  # L2 produzione (1152 DOF)
  python generate_topological_dataset.py --level 2 --steps 500 --output cosmo_L2_topo.h5

  # Stop automatico dopo 2 transizioni di fase
  python generate_topological_dataset.py --level 2 --max-transitions 2 --output cosmo_L2_topo.h5

  # Riproduzione esatta (seed fisso)
  python generate_topological_dataset.py --level 2 --seed 1234 --output cosmo_L2_seed1234.h5

EARLY STOPPING:
  --max-transitions N  -> ferma dopo N transizioni di fase topologica rilevate.
                         Utile per catturare esattamente il cambio vacuum->condensed.
                         Se omesso, gira per --steps completi.

================================================================================
"""

import sys
import gc
import argparse
import logging
import time
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import h5py

# Framework VQT
from wqt_oop.fractal_universe_factory import FractalUniverseFactory, UniverseConfig
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.hdf5_logger import HDF5Logger, HDF5LoggerConfig
from wqt_oop.energy_drift_observer import (
    Observable, StatisticsLogger, ProgressTracker, SimulationState
)
from wqt_oop.topological_integration import (
    TopologicalEvolutionWrapper,
    integrate_topological_validation_to_hdf5,
)
from wqt_oop.variational_topological_force import TopologicalForceConfig
from wqt_oop.maturity_watchdog import MaturityWatchdog


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("gen_topo")

# Sopprimi warning energetici del sistema legacy (sono feature, non bug)
warnings.filterwarnings("ignore", category=UserWarning,
                        message="DRIFT ENERGIA CRITICO.*")


# ============================================================================
# CLI
# ============================================================================

def parse_args():
    p = argparse.ArgumentParser(
        description="Genera dataset HDF5 con validazione topologica VQT",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Universo
    p.add_argument("--level", "-l", type=int, default=2,
                   help="Livello frattale target (1=L1/48DOF, 2=L2/1152DOF)")
    p.add_argument("--chi-mean", type=float, default=50.0,
                   help="Valore medio campo χ iniziale")
    p.add_argument("--chi-std",  type=float, default=5.0,
                   help="Deviazione standard χ")
    p.add_argument("--vel-std",  type=float, default=0.5,
                   help="Deviazione standard velocità iniziale")
    p.add_argument("--spatial-extent", type=float, default=50.0,
                   help="Dimensione box spaziale [unità Planck]")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed per riproducibilità")

    # Simulazione
    p.add_argument("--steps", "-n", type=int, default=500,
                   help="Numero massimo di step evolutivi")
    p.add_argument("--dt", type=float, default=0.01,
                   help="Passo temporale [unità Planck]")
    p.add_argument("--max-transitions", type=int, default=0,
                   help="Ferma dopo N transizioni di fase (0=disabilitato)")

    # Topologia
    p.add_argument("--topo-log-interval", type=int, default=1,
                   help="Campiona stato topologico ogni N step")
    p.add_argument("--closure-tol", type=float, default=15.0,
                   help="Tolleranza chiusura 720° [gradi]")
    p.add_argument("--detorsion-tol", type=float, default=30.0,
                   help="Tolleranza detorsione ±180° [gradi]")

    # Output
    p.add_argument("--output", "-o", type=str, default="cosmo_topo.h5",
                   help="File HDF5 di output")
    p.add_argument("--save-interval", type=int, default=1,
                   help="Salva frame legacy ogni N step")
    p.add_argument("--log-interval", type=int, default=50,
                   help="Log console ogni N step")

    # Fisica (coupling ridotto per stabilità)
    p.add_argument("--alpha-K",     type=float, default=0.01)
    p.add_argument("--kappa",       type=float, default=0.01)
    p.add_argument("--lambda-exch", type=float, default=0.001)
    p.add_argument("--mu-fermi",    type=float, default=50.0)
    p.add_argument("--T-fermi",     type=float, default=5.0)

    # Forza variazionale [Eq. S-1, INT-1] — opt-in
    p.add_argument("--enable-variational-force", action="store_true",
                   help="Attiva forza dal potenziale topologico S [Eq. S-1] "
                        "con Strang Splitting: U_tot = T_{dt/2} o U_phys o T_{dt/2}")
    p.add_argument("--lambda-homeo", type=float, default=0.1,
                   help="Coefficiente omeostatico lambda [Eq. FH-1]")
    p.add_argument("--gamma-chiral", type=float, default=0.01,
                   help="Coefficiente chirale gamma [Eq. FCH-1]")
    p.add_argument("--rho-0", type=float, default=0.90,
                   help="Set-point omeostatico rho_0 base (asintoto L->∞ se auto-scale attivo)")
    p.add_argument("--auto-scale-rho-0", action="store_true",
                   help="Auto-scala rho_0 con Legge FA [Eq. FA-2]: "
                        "rho_0_eff(L) = rho_0 + delta_rho_fractal / 24^(L/2). "
                        "Il sistema diventa auto-simile: nessun rho_0 manuale per livello.")
    p.add_argument("--delta-rho-fractal", type=float, default=0.05,
                   help="Coefficiente scaling Legge FA [Eq. FA-2]. "
                        "Con rho_0=0.85: L1->0.860, L2->0.852 (pressione espansiva costante)")

    p.add_argument("--verbose", "-v", action="store_true",
                   help="Logging verbose (DEBUG)")

    # Resume
    p.add_argument("--resume-from", type=str, default=None,
                   help="Riprendi da ultimo frame di un file HDF5 esistente. "
                        "La struttura universo (livello, seed, parametri fisici) "
                        "deve essere identica. --steps indica step AGGIUNTIVI.")

    # Inherit — pipeline gerarchica L_n-1 -> L_n
    p.add_argument("--inherit", type=str, default=None, metavar="CHECKPOINT_H5",
                   help="Eredita i nodi solitonici attivi (contorsione > percentile) "
                        "da un checkpoint HDF5 del livello precedente (es. L3 -> L4). "
                        "I segmenti L_n corrispondenti vengono inizializzati con i valori "
                        "chi del checkpoint, riducendo la convergenza del MaturityWatchdog. "
                        "Esempio: --inherit cosmo_L3_ext3.h5 --level 4")
    p.add_argument("--inherit-percentile", type=float, default=75.0,
                   help="Percentile contorsione per selezionare i nodi solitonici "
                        "da ereditare (default 75 = top 25%% più attivi)")
    p.add_argument("--inherit-noise", type=float, default=0.1,
                   help="Rumore additivo (frazione di chi_std) applicato ai valori "
                        "ereditati per evitare degenerazione (default 0.1)")

    # Memory management
    p.add_argument("--gc-interval", type=int, default=10,
                   help="Chiama gc.collect() ogni N step per liberare tensori "
                        "temporanei. Riduce il picco di memoria a L4 (default 10).")
    p.add_argument("--buffer-size", type=int, default=None,
                   help="Override buffer HDF5Logger (frame in RAM prima del flush). "
                        "Default auto: 20 per L<=2, 5 per L3, 2 per L>=4.")

    # Watchdog — autotuning maturità spaziale
    p.add_argument("--watchdog", action="store_true",
                   help="Attiva MaturityWatchdog: auto-terminazione basata su σ(ρ) plateau. "
                        "In questo modo --steps diventa un limite di sicurezza (max_steps).")
    p.add_argument("--watchdog-window", type=int, default=50,
                   help="W — step consecutivi sotto soglia per dichiarare maturità [Eq. WD-1]")
    p.add_argument("--watchdog-epsilon", type=float, default=1e-4,
                   help="ε — soglia su |d/dt σ(ρ)| [Planck⁻¹]. "
                        "Normalizzata internamente per invarianza di scala: ε_norm = ε/√N_dof")
    p.add_argument("--watchdog-H-rel-tol", type=float, default=0.10,
                   help="Tolleranza relativa per stazionarietà H_emergent: std(H)/|mean(H)| < tol")
    p.add_argument("--watchdog-no-autotune", action="store_true",
                   help="Disabilita auto-tune di W dalla spettroscopia (usa --watchdog-window fisso)")
    p.add_argument("--watchdog-spectral-steps", type=int, default=200,
                   help="Step minimi di accumulo prima della FFT spettrale")
    p.add_argument("--watchdog-tune-factor", type=float, default=0.75,
                   help="W_auto = factor × T_dom / dt  (default 0.75 = 3/4 del periodo dominante)")

    # Dry-run: diagnostica senza simulazione
    p.add_argument("--dry-run", action="store_true",
                   help="Stampa report diagnostico completo (memoria, inherit mapping, "
                        "configurazione buffer) ed esce senza eseguire la simulazione. "
                        "Usare prima di lanciare run lunghi per verificare la configurazione.")

    return p.parse_args()


# ============================================================================
# RESUME HELPERS
# ============================================================================

def _collect_all_segments(soliton):
    """Raccolta ricorsiva segmenti atomici (speculare a HDF5Logger._collect_all_segments)."""
    if isinstance(soliton, SegmentoQuantistico):
        return [soliton]
    elif isinstance(soliton, SolitoneComposito):
        segs = []
        for child in soliton.children:
            segs.extend(_collect_all_segments(child))
        return segs
    return []


def load_resume_state(hdf5_path: Path) -> dict:
    """Carica stato dell'ultimo frame da file HDF5 per il resume."""
    with h5py.File(hdf5_path, 'r') as hf:
        frame_names = sorted(hf['frames'].keys())
        if not frame_names:
            raise ValueError(f"Nessun frame trovato in {hdf5_path}")
        last = hf['frames'][frame_names[-1]]
        return {
            'frame_name': frame_names[-1],
            'step':       int(last.attrs['step']),
            'time':       float(last.attrs['time']),
            'chi_values': last['chi_values'][:],
            'velocities': last['velocities'][:],
            'tau_locale': last['tau_locale'][:],
        }


def inject_state_into_universe(universe, resume_state: dict) -> int:
    """Inietta stato HDF5 nel grafo universo. Ritorna N_segments iniettati."""
    segs = _collect_all_segments(universe)
    chi = resume_state['chi_values']
    vel = resume_state['velocities']
    tau = resume_state['tau_locale']
    if len(segs) != len(chi):
        raise ValueError(
            f"Mismatch struttura: {len(segs)} segmenti vs {len(chi)} valori stato. "
            "Il file di resume deve usare la stessa configurazione universo (livello, seed, parametri)."
        )
    for i, seg in enumerate(segs):
        seg.chi        = float(chi[i])
        seg.vel        = float(vel[i])
        seg.tau_locale = float(tau[i])
    return len(segs)


# ============================================================================
# INHERIT — pipeline gerarchica L_{n-1} -> L_n
# ============================================================================

def load_inherit_state(hdf5_path: Path, percentile: float = 75.0) -> dict:
    """
    Carica i nodi solitonici attivi dall'ultimo frame di un checkpoint L_{n-1}.

    Seleziona solo i nodi con contorsione_locale >= percentile (default p75),
    isolando le strutture solitoniche che definiscono la fase condensed.

    Returns
    -------
    dict con:
      'chi_all'       : (N_prev,)  — tutti i chi dell'ultimo frame
      'cont_all'      : (N_prev,)  — contorsione di tutti i nodi
      'soliton_mask'  : (N_prev,)  bool — maschera nodi solitonici
      'chi_solitons'  : (N_sol,)   — chi dei soli nodi solitonici
      'cont_threshold': float      — soglia usata
      'n_solitons'    : int
      'chi_mean'      : float      — media globale (per noise scaling)
      'chi_std'       : float
    """
    with h5py.File(hdf5_path, 'r') as hf:
        frame_names = sorted(hf['frames'].keys())
        if not frame_names:
            raise ValueError(f"Nessun frame in {hdf5_path}")
        last = hf['frames'][frame_names[-1]]
        chi_all  = last['chi_values'][:]
        cont_all = last['contorsione_locale'][:]

    threshold = float(np.percentile(cont_all, percentile))
    mask = cont_all >= threshold

    logger.info(
        f"[inherit] Caricato {hdf5_path.name}: "
        f"{len(chi_all)} nodi, soglia p{percentile:.0f}={threshold:.2f} deg, "
        f"solitoni={mask.sum()} ({100*mask.mean():.1f}%)"
    )

    return {
        'chi_all':        chi_all,
        'cont_all':       cont_all,
        'soliton_mask':   mask,
        'chi_solitons':   chi_all[mask],
        'cont_threshold': threshold,
        'n_solitons':     int(mask.sum()),
        'chi_mean':       float(chi_all.mean()),
        'chi_std':        float(chi_all.std()),
    }


def apply_inherit_to_universe(universe,
                               inherit_state: dict,
                               noise_fraction: float = 0.1,
                               rng: Optional[np.random.Generator] = None) -> int:
    """
    Inizializza i segmenti di L_n con i valori chi ereditati da L_{n-1}.

    Mappatura gerarchica: ogni segmento L_{n-1} corrisponde a 24 segmenti L_n
    (un livello di espansione frattale). I 24 figli ereditano il chi del padre
    con un piccolo rumore per rompere la simmetria.

    Solo i nodi solitonici (soliton_mask=True) vengono modificati;
    gli altri mantengono l'inizializzazione casuale standard.

    Parameters
    ----------
    universe       : radice del grafo universo L_n (già creato dalla factory)
    inherit_state  : output di load_inherit_state()
    noise_fraction : rumore additivo = noise_fraction × chi_std
    rng            : generatore random (default: numpy global)

    Returns
    -------
    n_seeded : int — numero di segmenti modificati
    """
    if rng is None:
        rng = np.random.default_rng()

    segs_Ln = _collect_all_segments(universe)
    N_Ln    = len(segs_Ln)

    chi_prev   = inherit_state['chi_all']         # (N_{n-1},)
    mask_prev  = inherit_state['soliton_mask']    # (N_{n-1},) bool
    chi_std    = inherit_state['chi_std']
    N_prev     = len(chi_prev)

    # Verifica coerenza frattale: N_Ln deve essere N_prev × 24
    expansion = N_Ln // N_prev
    if expansion == 0 or N_Ln % N_prev != 0:
        logger.warning(
            f"[inherit] Mismatch frattale: N_Ln={N_Ln}, N_prev={N_prev}, "
            f"rapporto={N_Ln/N_prev:.2f} (atteso 24). "
            f"Applico mappatura per vicinanza spaziale."
        )
        expansion = None

    noise_sigma = noise_fraction * max(chi_std, 1.0)
    n_seeded = 0

    if expansion is not None:
        # Mappatura diretta: segmento prev[i] -> segs_Ln[i*expansion : (i+1)*expansion]
        for i in range(N_prev):
            if not mask_prev[i]:
                continue
            chi_parent = float(chi_prev[i])
            for k in range(expansion):
                idx = i * expansion + k
                if idx < N_Ln:
                    noise = float(rng.normal(0.0, noise_sigma))
                    segs_Ln[idx].chi = chi_parent + noise
                    n_seeded += 1
    else:
        # Fallback: assegna ai primi N_prev segmenti (con soliton_mask=True)
        soliton_indices = np.where(mask_prev)[0]
        for ii, i in enumerate(soliton_indices):
            if i < N_Ln:
                segs_Ln[i].chi = float(chi_prev[i]) + float(rng.normal(0.0, noise_sigma))
                n_seeded += 1

    logger.info(
        f"[inherit] {n_seeded} segmenti L{universe.physics.level} "
        f"inizializzati dai {inherit_state['n_solitons']} solitoni L{universe.physics.level - 1}"
    )
    return n_seeded


# ============================================================================
# DRY-RUN REPORT
# ============================================================================

def dry_run_report(args, universe, inherit_state: Optional[dict] = None) -> None:
    """
    Stampa un report diagnostico completo ed esce senza avviare la simulazione.

    Sezioni:
      [1] Configurazione universo  — DOF, livello, seed
      [2] Stima memoria RAM        — oggetti, coupling, buffer HDF5, frame size
      [3] Inherit mapping          — solo se --inherit specificato
      [4] Configurazione I/O       — buffer, chunk, output path
      [5] Watchdog                 — parametri se attivo
      [6] Checklist go/no-go       — avvisi automatici se RAM stimata > 80%
    """
    from wqt_oop.sparse_coupling import coupling_memory_bytes

    # Forza UTF-8 su stdout per caratteri non-ASCII (console Windows cp1252)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    W = "=" * 66
    w = "-" * 66

    N_seg    = 24 ** args.level
    N_dof    = 2 * N_seg
    # Compositi a ogni livello: 1 + 24 + 24^2 + ... + 24^(level-1)
    n_compositi = sum(24 ** k for k in range(args.level))

    # --- Stima memoria statica ---
    seg_obj_bytes   = N_seg * 400          # ~400 B per SegmentoQuantistico
    comp_obj_bytes  = n_compositi * 8_000  # ~8 KB per SolitoneComposito (coupling+cache)
    coupling_bytes  = n_compositi * coupling_memory_bytes(
        24, sparse=(24 > 48), L_eff=3.0)
    spatial_cache_b = n_compositi * 5_000  # SpatialCache ~5 KB

    static_mb = (seg_obj_bytes + comp_obj_bytes + coupling_bytes + spatial_cache_b) / 1e6

    # Dimensione frame HDF5: positions(N,3)+chi(N)+cont(N)+screen(N)+tau(N)+vel(N)
    frame_bytes = N_seg * (3 + 1 + 1 + 1 + 1 + 1) * 8  # 8 dataset float64
    if args.buffer_size is not None:
        buf = args.buffer_size
    else:
        buf = max(2, 20 // (4 ** max(0, args.level - 2)))

    buffer_mb = buf * frame_bytes / 1e6

    # Temporanei per step (broadcasting N_children × N_children)
    # get_child_aggregates: N_children scalari = trascurabile
    # Matrici di attenuazione: n_compositi × (24×24×8 byte) × 6 matrici
    temp_per_step_mb = n_compositi * 24 * 24 * 8 * 6 / 1e6

    total_est_mb = static_mb + buffer_mb + temp_per_step_mb + 500  # +500 MB Python overhead

    # HDF5 output size stimata: frame_bytes × steps
    hdf5_est_gb = frame_bytes * args.steps / 1e9

    # --- Stampa report ---
    lines = [
        "",
        W,
        "  VQT DRY-RUN REPORT",
        W,
        "",
        "[1] CONFIGURAZIONE UNIVERSO",
        w,
        f"  Livello target  : L{args.level}",
        f"  N segmenti      : {N_seg:,}  (24^{args.level})",
        f"  DOF             : {N_dof:,}",
        f"  N compositi     : {n_compositi:,}  (livelli L0..L{args.level-1})",
        f"  Seed            : {args.seed}",
        f"  Steps           : {args.steps}  (dt={args.dt})  "
        f"->  t_max = {args.steps * args.dt:.2f} P",
        "",
        "[2] STIMA MEMORIA RAM",
        w,
        f"  Oggetti Python  : {static_mb:,.0f} MB",
        f"    SegmentoQ     :   {seg_obj_bytes/1e6:,.0f} MB  ({N_seg:,} × ~400 B)",
        f"    SolitoneComp  :   {comp_obj_bytes/1e6:,.0f} MB  ({n_compositi:,} × ~8 KB)",
        f"    CouplingMatrix:   {coupling_bytes/1e6:,.0f} MB  (24x24 dense, {n_compositi:,} istanze)",
        f"    SpatialCache  :   {spatial_cache_b/1e6:,.0f} MB",
        f"  Buffer HDF5     : {buffer_mb:,.0f} MB  ({buf} frame × {frame_bytes/1e6:.1f} MB/frame)",
        f"  Temporanei/step : {temp_per_step_mb:,.0f} MB  (broadcasting NxN vettorizzato)",
        f"  Overhead Python : ~500 MB",
        w,
        f"  TOTALE STIMATO  : {total_est_mb:,.0f} MB  ({total_est_mb/1024:.1f} GB)",
        "",
        f"  HDF5 output     : ~{hdf5_est_gb:.1f} GB  ({args.steps} frame × {frame_bytes/1e6:.1f} MB)",
        "",
    ]

    # [3] Inherit mapping
    if inherit_state is not None:
        expansion = N_seg // inherit_state['n_solitons'] if inherit_state['n_solitons'] > 0 else 0
        seeded_pct = 100.0 * (inherit_state['n_solitons'] * max(expansion, 1)) / N_seg
        lines += [
            "[3] INHERIT MAPPING",
            w,
            f"  Checkpoint      : {args.inherit}",
            f"  N nodi L{args.level-1}      : {len(inherit_state['chi_all']):,}",
            f"  Soglia          : p{args.inherit_percentile:.0f} = {inherit_state['cont_threshold']:.2f} deg",
            f"  Solitoni attivi : {inherit_state['n_solitons']:,}  "
            f"({100*inherit_state['soliton_mask'].mean():.1f}% del L{args.level-1})",
            f"  Espansione      : 1:{expansion}  (ogni nodo L{args.level-1} -> {expansion} L{args.level})",
            f"  Segmenti seeded : ~{min(inherit_state['n_solitons']*max(expansion,1), N_seg):,}  "
            f"({seeded_pct:.1f}% di L{args.level})",
            f"  chi_mean inh.   : {inherit_state['chi_mean']:.2f}  "
            f"(±{inherit_state['chi_std']:.2f})  noise={args.inherit_noise*100:.0f}% sigma",
            "",
        ]
    else:
        lines += [
            "[3] INHERIT",
            w,
            "  Non specificato — universo L4 inizializzato casualmente.",
            "  Suggerimento: --inherit cosmo_L3_ext3.h5  per ridurre convergenza.",
            "",
        ]

    # [4] I/O
    lines += [
        "[4] CONFIGURAZIONE I/O",
        w,
        f"  Output path     : {args.output}",
        f"  HDF5 buffer     : {buf} frame  (auto-calc per L{args.level})",
        f"  Save interval   : {args.save_interval} step",
        f"  gc.collect ogni : {args.gc_interval} step",
        "",
    ]

    # [5] Watchdog
    if args.watchdog:
        eps_norm = args.watchdog_epsilon / (N_dof ** 0.5)
        lines += [
            "[5] MATURITY WATCHDOG",
            w,
            f"  W_init          : {args.watchdog_window} step",
            f"  epsilon         : {args.watchdog_epsilon:.2e}  "
            f"(norm: {eps_norm:.2e}  = e / sqrt(DOF))",
            f"  H_rel_tol       : {args.watchdog_H_rel_tol:.2f}",
            f"  Auto-tune       : {'OFF' if args.watchdog_no_autotune else 'ON'}",
            "",
        ]

    # [6] Checklist go / no-go
    RAM_AVAIL_MB = 32 * 1024  # 32 GB
    lines += ["[6] CHECKLIST GO/NO-GO", w]

    checks = [
        ("RAM stimata < 80% disponibile",
         total_est_mb < RAM_AVAIL_MB * 0.8,
         f"{total_est_mb:,.0f} MB / {RAM_AVAIL_MB:,} MB ({100*total_est_mb/RAM_AVAIL_MB:.0f}%)"),
        ("Buffer HDF5 < 5% RAM",
         buffer_mb < RAM_AVAIL_MB * 0.05,
         f"{buffer_mb:,.0f} MB / max {RAM_AVAIL_MB*0.05:,.0f} MB"),
        ("Output HDF5 ragionevole (< 50 GB)",
         hdf5_est_gb < 50,
         f"~{hdf5_est_gb:.1f} GB"),
        ("Inherit specificato",
         inherit_state is not None,
         "SI" if inherit_state is not None else "NO (convergenza piu' lenta)"),
        ("Watchdog attivo",
         args.watchdog,
         "SI" if args.watchdog else "NO (stop manuale --steps)"),
    ]

    all_ok = True
    for label, ok, detail in checks:
        icon = "OK " if ok else "!! "
        if not ok:
            all_ok = False
        lines.append(f"  [{icon}] {label}")
        lines.append(f"          {detail}")

    lines += [
        w,
        "  VERDETTO: " + ("CONFIGURAZIONE PRONTA — puoi lanciare il run." if all_ok
                          else "ATTENZIONE — verifica i punti marcati !! prima di procedere."),
        W,
        "",
    ]

    print("\n".join(lines))


# ============================================================================
# INCREMENTAL TOPOLOGICAL HDF5 WRITER
# Scrive topological_validation per step nell'HDF5 aperto da HDF5Logger.
# Robusto a kill SIGTERM: i dati sono su disco dopo ogni flush.
# ============================================================================

_TOPO_SCHEMA = {
    'step':                    np.int64,
    'time':                    np.float64,
    'mean_constraint_density': np.float64,
    'constraint_density_std':  np.float64,
    'closure_error_deg':       np.float64,
    'closure_satisfied':       np.bool_,
    'detorsion_quality':       np.float64,
    'detorsion_satisfied':     np.bool_,
    'H_total_emergent':        np.float64,
    'H_torsion_emergent':      np.float64,
    'topology_charge':         np.float64,
    'N_segments':              np.int64,
    'N_dof':                   np.int64,
    'transition_detected':     np.bool_,
}
_CHUNK = 64


def _init_topo_group(h5file: h5py.File) -> "h5py.Group":
    """Crea il gruppo topological_validation con dataset estendibili."""
    if 'topological_validation' in h5file:
        del h5file['topological_validation']
    grp = h5file.create_group('topological_validation')
    for name, dtype in _TOPO_SCHEMA.items():
        grp.create_dataset(name, shape=(0,), maxshape=(None,),
                           dtype=dtype, chunks=(_CHUNK,), compression='gzip')
    grp.create_dataset('phase_label', shape=(0,), maxshape=(None,),
                       dtype='S16', chunks=(_CHUNK,), compression='gzip')
    grp.attrs['incremental'] = True
    return grp


def _append_topo_entry(grp: "h5py.Group", topo_state) -> None:
    """Aggiunge un TopologicalState ai dataset estendibili."""
    N = grp['step'].shape[0]
    values = {
        'step':                    topo_state.step,
        'time':                    topo_state.time,
        'mean_constraint_density': topo_state.mean_constraint_density,
        'constraint_density_std':  topo_state.constraint_density_std,
        'closure_error_deg':       topo_state.closure_error_deg,
        'closure_satisfied':       topo_state.closure_satisfied,
        'detorsion_quality':       topo_state.detorsion_pattern_quality,
        'detorsion_satisfied':     topo_state.detorsion_satisfied,
        'H_total_emergent':        topo_state.H_total_emergent,
        'H_torsion_emergent':      topo_state.H_torsion_emergent,
        'topology_charge':         topo_state.topology_charge,
        'N_segments':              topo_state.N_segments,
        'N_dof':                   topo_state.N_dof,
        'transition_detected':     topo_state.transition_detected,
    }
    for name, val in values.items():
        ds = grp[name]
        ds.resize(N + 1, axis=0)
        ds[N] = val
    pl = grp['phase_label']
    pl.resize(N + 1, axis=0)
    pl[N] = topo_state.phase_label.encode('ascii')[:16]


# ============================================================================
# SIMULATION LOOP
# ============================================================================

def run_simulation(args) -> int:
    """
    Loop di simulazione principale.

    Returns
    -------
    int
        Exit code (0 = successo, 1 = errore).
    """
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_path = Path(args.output)

    # ------------------------------------------------------------------
    # FASE 1: Creazione universo
    # ------------------------------------------------------------------
    logger.info("=" * 70)
    logger.info("  GENERATE TOPOLOGICAL DATASET - VQT")
    logger.info("=" * 70)
    logger.info(f"\nParametri:")
    logger.info(f"  Livello:       L{args.level}  "
                f"(DOF = 2×24^{args.level} = {2 * 24**args.level})")
    logger.info(f"  Steps:         {args.steps}  (dt={args.dt})"
                + ("  [MAX — watchdog attivo]" if args.watchdog else ""))
    logger.info(f"  Early stop:    {'dopo ' + str(args.max_transitions) + ' transizioni' if args.max_transitions else 'disabilitato'}")
    if args.watchdog:
        n_dof_preview = 2 * (24 ** args.level)
        eps_norm_preview = args.watchdog_epsilon / (n_dof_preview ** 0.5)
        autotune_str = (f"auto-tune ON (spectral_steps={args.watchdog_spectral_steps} "
                        f"factor={args.watchdog_tune_factor})"
                        if not args.watchdog_no_autotune else "auto-tune OFF")
        logger.info(
            f"  Watchdog:      ON  W_init={args.watchdog_window}  "
            f"ε={args.watchdog_epsilon:.2e}  ε_norm={eps_norm_preview:.2e}  "
            f"H_rel_tol={args.watchdog_H_rel_tol:.2f}  {autotune_str}"
        )
    logger.info(f"  Output:        {output_path}")
    logger.info(f"  Seed:          {args.seed}")

    base_physics = PhysicsContext(
        level=0,
        length_scale=1.0e-10,
        alpha_K=args.alpha_K,
        kappa_coupling=args.kappa,
        lambda_exchange=args.lambda_exch,
        mu_fermi=args.mu_fermi,
        T_fermi=args.T_fermi,
        gamma_cooling=0.01,
        chi_stable=args.chi_mean,
    )

    config = UniverseConfig(
        target_level=args.level,
        chi_mean=args.chi_mean,
        chi_std=args.chi_std,
        vel_std=args.vel_std,
        spatial_extent=args.spatial_extent,
        seed=args.seed,
        enable_fermi_screening=True,
        enable_spatial_cache=True,
    )

    logger.info("\nGenerazione universo...")
    t0 = time.time()
    factory = FractalUniverseFactory(base_physics=base_physics)
    universe = factory.create_universe(config)
    t_create = time.time() - t0

    N_segments = 24 ** args.level
    logger.info(f"Universo creato in {t_create:.2f}s  "
                f"(N={N_segments} segmenti, DOF={2*N_segments})")

    # Physics del livello radice (per il wrapper)
    root_physics = factory.get_physics_for_level(args.level)

    # ------------------------------------------------------------------
    # FASE 1b: Resume da stato precedente (se --resume-from specificato)
    # ------------------------------------------------------------------
    step_offset = 0
    time_offset = 0.0

    if args.resume_from is not None:
        resume_path = Path(args.resume_from)
        if not resume_path.exists():
            logger.error(f"File resume non trovato: {resume_path}")
            return 1

        logger.info(f"\nResume da: {resume_path}")
        try:
            resume_state = load_resume_state(resume_path)
        except Exception as exc:
            logger.error(f"Impossibile caricare stato resume: {exc}")
            return 1

        try:
            n_injected = inject_state_into_universe(universe, resume_state)
        except ValueError as exc:
            logger.error(str(exc))
            return 1

        step_offset = resume_state['step']
        time_offset = resume_state['time']
        logger.info(
            f"  Stato iniettato: {n_injected} segmenti  "
            f"(ultimo frame: {resume_state['frame_name']}  "
            f"step={step_offset}  t={time_offset:.4f} Planck)"
        )
        logger.info(
            f"  Continua per {args.steps} step aggiuntivi  "
            f"(step {step_offset + 1} -> {step_offset + args.steps})"
        )

    # ------------------------------------------------------------------
    # FASE 1c: Inherit — pipeline gerarchica L_{n-1} -> L_n
    # ------------------------------------------------------------------
    _inherit_state_for_dryrun: Optional[dict] = None

    if args.inherit is not None:
        inherit_path = Path(args.inherit)
        if not inherit_path.exists():
            logger.error(f"[inherit] File non trovato: {inherit_path}")
            return 1

        logger.info(f"\n[inherit] Caricamento solitoni da: {inherit_path}")
        try:
            _inherit_state_for_dryrun = load_inherit_state(
                inherit_path, args.inherit_percentile
            )
        except Exception as exc:
            logger.error(f"[inherit] Errore caricamento: {exc}")
            return 1

        if not args.dry_run:
            n_seeded = apply_inherit_to_universe(
                universe, _inherit_state_for_dryrun,
                noise_fraction=args.inherit_noise,
                rng=np.random.default_rng(args.seed + 9999),
            )
            logger.info(
                f"[inherit] Seeding completato: {n_seeded} segmenti L{args.level} "
                f"pre-riscaldati a chi condensed"
            )

    # ------------------------------------------------------------------
    # FASE 1d: Dry-run — stampa report ed esci prima di toccare il disco
    # ------------------------------------------------------------------
    if args.dry_run:
        dry_run_report(args, universe, _inherit_state_for_dryrun)
        gc.collect()
        return 0

    # Libera inherit_state dopo seeding (non più necessaria)
    if _inherit_state_for_dryrun is not None:
        del _inherit_state_for_dryrun
        gc.collect()

    # ------------------------------------------------------------------
    # FASE 2: Setup observer legacy (HDF5Logger, StatisticsLogger)
    # ------------------------------------------------------------------
    logger.info("\nSetup observer...")

    observable = Observable()

    # HDF5Logger per i frame legacy
    # SWMR disabilitato: dopo la simulazione riapriremo il file per aggiungere
    # il gruppo topologico.
    # Buffer adattivo: a L4 ogni frame è ~13 MB -> buffer piccolo per evitare
    # accumulo in RAM. Formula: 20 per L<=2, 5 per L3, 2 per L>=4.
    if args.buffer_size is not None:
        _buf = args.buffer_size
    else:
        _buf = max(2, 20 // (4 ** max(0, args.level - 2)))
    logger.info(f"  HDF5 buffer_size: {_buf} frame (livello L{args.level})")

    hdf5_config = HDF5LoggerConfig(
        filepath=output_path,
        save_interval=args.save_interval,
        enable_swmr=False,   # OFF -> possiamo riaprire in append dopo
        buffer_size=_buf,
        compression="gzip",
    )
    hdf5_metadata = {
        "target_level":   args.level,
        "N_segments":     N_segments,
        "total_steps":    args.steps,
        "dt":             args.dt,
        "chi_mean":       args.chi_mean,
        "chi_std":        args.chi_std,
        "spatial_extent": args.spatial_extent,
        "seed":           args.seed,
        "paradigm":       "topological_v1",
        "step_offset":    step_offset,
        "time_offset":    time_offset,
        "resumed_from":   str(args.resume_from) if args.resume_from else "",
    }
    hdf5_logger = HDF5Logger(
        config=hdf5_config,
        universe=universe,
        metadata=hdf5_metadata,
    )

    stats_logger   = StatisticsLogger(log_interval=args.log_interval)
    progress_tracker = ProgressTracker(total_steps=args.steps)

    observable.attach(hdf5_logger)
    observable.attach(stats_logger)
    observable.attach(progress_tracker)

    # ------------------------------------------------------------------
    # FASE 3: TopologicalEvolutionWrapper (livello topologico)
    # ------------------------------------------------------------------
    force_cfg = None
    if args.enable_variational_force:
        force_cfg = TopologicalForceConfig(
            lambda_homeo=args.lambda_homeo,
            gamma_chiral=args.gamma_chiral,
            rho_0=args.rho_0,
            conserve_topology_charge=True,
            auto_scale_rho_0=args.auto_scale_rho_0,
            delta_rho_fractal=args.delta_rho_fractal,
        )
        rho_0_eff = force_cfg.get_rho_0(args.level)
        logger.info(
            f"\nForza variazionale ATTIVA [Eq. S-1]:  "
            f"lambda={args.lambda_homeo}  gamma={args.gamma_chiral}  "
            f"rho_0_base={args.rho_0}  "
            f"auto_scale={'ON' if args.auto_scale_rho_0 else 'OFF'}  "
            f"rho_0_eff(L{args.level})={rho_0_eff:.4f}"
        )

    wrapper = TopologicalEvolutionWrapper(
        universe=universe,
        physics=root_physics,
        enable_validation=True,
        enable_legacy_energy_logging=False,
        closure_tolerance_deg=args.closure_tol,
        detorsion_tolerance_deg=args.detorsion_tol,
        log_interval=max(1, args.topo_log_interval),
        verbose_interval=max(args.log_interval, args.topo_log_interval * 10),
        force_config=force_cfg,
    )

    # Watchdog maturità spaziale (opt-in)
    watchdog: Optional[MaturityWatchdog] = None
    if args.watchdog:
        watchdog = MaturityWatchdog(
            window_size=args.watchdog_window,
            convergence_threshold=args.watchdog_epsilon,
            n_dof=2 * N_segments,
            dt=args.dt,
            H_rel_tol=args.watchdog_H_rel_tol,
            auto_tune_window=not args.watchdog_no_autotune,
            spectral_min_steps=args.watchdog_spectral_steps,
            spectral_tune_factor=args.watchdog_tune_factor,
        )

    # ------------------------------------------------------------------
    # FASE 4: Loop simulazione
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 70)
    logger.info("  INIZIO SIMULAZIONE")
    logger.info("=" * 70)

    observable.notify_start()

    # Crea il gruppo topological_validation con dataset estendibili nel file HDF5.
    # I dati vengono scritti per ogni step -> robusto a kill SIGTERM.
    topo_grp = _init_topo_group(hdf5_logger.h5file)
    _topo_flush_counter = 0

    H_initial = float(universe.energia_totale)
    T_eff     = (universe.fermi_screener.T_eff
                 if isinstance(universe, SolitoneComposito) else 0.0)
    N_solitons = (universe.N_children
                  if isinstance(universe, SolitoneComposito) else 1)

    transitions_count = 0
    phase_log = []         # Traccia evoluzione fasi per analisi finale
    rho_history = []       # Traccia ρ_mean per ogni step topologico
    stop_reason = "max_steps"

    t_sim_start = time.time()

    step_idx = 0
    try:
        while step_idx < args.steps:

            # --- 1. Evoluzione + validazione topologica ---
            topo_state = wrapper.evolve_step(args.dt)

            # --- 2. Snapshot legacy per observer ---
            H_now = float(universe.energia_totale)
            drift = abs(H_now - H_initial) / (abs(H_initial) + 1e-30)
            if isinstance(universe, SolitoneComposito):
                T_eff = universe.fermi_screener.T_eff

            sim_state = SimulationState(
                step=step_offset + step_idx + 1,
                time=time_offset + (step_idx + 1) * args.dt,
                H_total=H_now,
                drift=drift,      # Segnalato agli observer legacy (non più vincolo)
                N_solitons=N_solitons,
                T_eff=T_eff,
                wall_time=time.time(),
            )
            observable.notify(sim_state)

            # --- 3. Traccia fase topologica + scrittura incrementale HDF5 ---
            if topo_state is not None and step_idx % args.topo_log_interval == 0:
                phase_log.append(topo_state.phase_label)
                rho_history.append(topo_state.mean_constraint_density)
                _append_topo_entry(topo_grp, topo_state)
                _topo_flush_counter += 1
                if _topo_flush_counter % 10 == 0:
                    hdf5_logger.h5file.flush()

            # --- 3b. Memory management: gc.collect() ogni gc_interval step ---
            # Libera tensori temporanei accumulati nel loop (specialmente a L4
            # dove ogni step alloca ~20 MB di array intermedi non raccolti subito)
            if (step_idx + 1) % args.gc_interval == 0:
                del sim_state
                if topo_state is not None:
                    del topo_state
                    topo_state = None
                gc.collect()

            # --- 4. Early stopping su transizioni di fase ---
            if (args.max_transitions > 0
                    and topo_state is not None
                    and topo_state.transition_detected):
                transitions_count += 1
                logger.warning(
                    f"[TRANSITION #{transitions_count}]  "
                    f"step={step_idx+1}  "
                    f"fase={topo_state.phase_label.upper()}  "
                    f"ρ={topo_state.mean_constraint_density:.3f}"
                )
                if transitions_count >= args.max_transitions:
                    logger.info(
                        f"Early stop: {transitions_count} transizioni rilevate "
                        f"(target={args.max_transitions})."
                    )
                    stop_reason = "max_transitions"
                    step_idx += 1
                    break

            # --- 5. Watchdog maturità spaziale [Eq. WD-1] ---
            if watchdog is not None and topo_state is not None:
                mature = watchdog.update(topo_state, step_idx)

                # Log maturity status ogni log_interval step
                if (step_idx + 1) % args.log_interval == 0:
                    logger.info(f"  {watchdog.get_status_line()}")

                if mature:
                    logger.info(
                        f"\n{'=' * 60}\n"
                        f"  [WATCHDOG] MATURITÀ SPAZIALE RAGGIUNTA\n"
                        f"  Step: {step_idx + 1}  |  "
                        f"Costo maturità: {watchdog.get_maturity_cost()} iterazioni\n"
                        f"  ε_norm={watchdog.epsilon_norm:.3e}  "
                        f"W={watchdog.W}  N_dof={watchdog.n_dof}\n"
                        f"{'=' * 60}"
                    )
                    stop_reason = "watchdog_maturity"
                    step_idx += 1
                    break

            step_idx += 1

    except KeyboardInterrupt:
        logger.warning("Simulazione interrotta dall'utente (Ctrl+C).")
        stop_reason = "keyboard_interrupt"

    except Exception as exc:
        logger.error(f"Errore al step {step_idx+1}: {exc}")
        raise

    finally:
        # Chiudi HDF5Logger (flush + close)
        observable.notify_end()
        # Il file viene chiuso da hdf5_logger via notify_end -> on_simulation_end
        # e poi dal hook atexit. Forziamo la chiusura esplicita.
        hdf5_logger.close()

    t_sim = time.time() - t_sim_start
    wrapper.finalize()

    # ------------------------------------------------------------------
    # FASE 5: Finalizzazione HDF5 — variational_force, watchdog, topo fallback
    # topological_validation è già scritto incrementalmente nel loop.
    # Qui scriviamo i gruppi secondari (non inclusi nella scrittura incrementale).
    # ------------------------------------------------------------------
    logger.info("\nFinalizzazione HDF5...")

    topo_data = wrapper.export_topological_history()

    try:
        with h5py.File(output_path, "a") as hf:

            # topological_validation: scrivi solo se la scrittura incrementale
            # non è avvenuta (fallback per compatibilità con vecchie esecuzioni)
            if _topo_flush_counter == 0:
                if topo_data:
                    integrate_topological_validation_to_hdf5(hf, topo_data)
                    logger.info(
                        f"  /topological_validation scritto in bulk "
                        f"({len(topo_data['step'])} entry) [fallback]"
                    )
                else:
                    logger.warning("Nessun dato topologico da esportare.")
            else:
                # Flush finale del gruppo già aperto e chiuso con hdf5_logger
                logger.info(
                    f"  /topological_validation già scritto incrementalmente "
                    f"({_topo_flush_counter} entry)"
                )

            # Aggiungi storia forza variazionale se attiva
            force_hist = wrapper.export_variational_force_history()
            if force_hist:
                if "variational_force" in hf:
                    del hf["variational_force"]
                vgrp = hf.create_group("variational_force")
                for k, v in force_hist.items():
                    vgrp.create_dataset(k, data=v, compression="gzip")
                vgrp.attrs["description"] = (
                    "Variational topological force history [Eq. S-1, INT-1]. "
                    "force_rms: |F_top|_RMS per kick. "
                    "potential_S: S[chi,tau] = lambda*sum(rho-rho0)^2 + gamma*sum(Omega)."
                )
                logger.info(f"  /variational_force aggiunto ({len(force_hist['force_rms'])} kick)")

            # Aggiungi metadati watchdog
            if watchdog is not None:
                if "maturity" in hf:
                    del hf["maturity"]
                mg = hf.create_group("maturity")
                for k, v in watchdog.get_metadata_dict().items():
                    mg.attrs[k] = v
                mg.attrs["stop_reason"] = stop_reason
                hf.attrs["maturity_cost_steps"] = watchdog.get_maturity_cost()
                hf.attrs["maturity_declared"] = int(watchdog.is_mature())
                hf.attrs["stop_reason"] = stop_reason
                logger.info(
                    f"  /maturity aggiunto  "
                    f"(costo={watchdog.get_maturity_cost()} step  "
                    f"maturity={'OK' if watchdog.is_mature() else 'NON raggiunta'})"
                )
            else:
                hf.attrs["stop_reason"] = stop_reason
                hf.attrs["maturity_cost_steps"] = step_idx

    except Exception as exc:
        logger.error(f"Errore finalizzazione HDF5: {exc}")

    # ------------------------------------------------------------------
    # FASE 6: Summary finale
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 70)
    logger.info("  RISULTATI")
    logger.info("=" * 70)

    final_state = wrapper.get_current_topological_state()

    if final_state:
        logger.info(wrapper.validator.get_summary(final_state))

    # Statistiche temporali
    actual_steps = wrapper.current_step
    logger.info(f"\nStatistiche simulazione:")
    logger.info(f"  Step eseguiti:       {actual_steps} / {args.steps}")
    logger.info(f"  Motivo stop:         {stop_reason}")
    logger.info(f"  Tempo totale:        {t_sim:.2f}s")
    logger.info(f"  Throughput:          {actual_steps/t_sim:.1f} step/s")
    logger.info(f"  Tempo fisico:        {actual_steps * args.dt:.3f} [Planck]")
    logger.info(f"  Transizioni rilevate: {transitions_count}")

    if watchdog is not None:
        logger.info(f"\nMaturity Watchdog:")
        logger.info(f"  Maturità dichiarata: {'SI' if watchdog.is_mature() else 'NO (max_steps raggiunto)'}")
        logger.info(f"  Costo maturità:      {watchdog.get_maturity_cost()} step")
        logger.info(f"  ε_norm:              {watchdog.epsilon_norm:.3e}")
        logger.info(f"  |dσ/dt| finale:      {watchdog.get_sigma_derivative():.3e}")
        logger.info(f"  Risparmio:           {args.steps - watchdog.get_maturity_cost()} step evitati "
                    f"({100*(args.steps - watchdog.get_maturity_cost())/args.steps:.1f}%)"
                    if watchdog.is_mature() else "  Risparmio:           nessuno (max_steps esaurito)")

    # Distribuzione fasi
    if phase_log:
        from collections import Counter
        phase_counts = Counter(phase_log)
        total_ph = len(phase_log)
        logger.info(f"\nDistribuzione fasi topologiche ({total_ph} campioni):")
        for phase, cnt in sorted(phase_counts.items()):
            pct = 100 * cnt / total_ph
            bar = "█" * int(pct / 3)
            logger.info(f"  {phase:12s}: {cnt:5d} ({pct:5.1f}%)  {bar}")

    # Evoluzione ρ
    if rho_history:
        rho_arr = np.array(rho_history)
        logger.info(f"\nDensità vincolo ρ_constraint:")
        logger.info(f"  Iniziale:  {rho_arr[0]:.4f}")
        logger.info(f"  Finale:    {rho_arr[-1]:.4f}")
        logger.info(f"  Min/Max:   {rho_arr.min():.4f} / {rho_arr.max():.4f}")
        logger.info(f"  Media:     {rho_arr.mean():.4f}")
        logger.info(f"  Std:       {rho_arr.std():.4f}")
        # Trend lineare
        if len(rho_arr) > 2:
            slope = np.polyfit(range(len(rho_arr)), rho_arr, 1)[0]
            logger.info(f"  Trend:     {'↑ crescente' if slope > 1e-5 else '↓ decrescente' if slope < -1e-5 else '-> stabile'} "
                        f"({slope:+.6f}/step)")

    logger.info(f"\nOutput: {output_path.resolve()}")
    logger.info("=" * 70 + "\n")

    return 0


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    args = parse_args()
    sys.exit(run_simulation(args))
