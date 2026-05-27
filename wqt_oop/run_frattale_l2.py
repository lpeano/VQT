"""
================================================================================
SIMULAZIONE FRATTALE LIVELLO 2: MacroSolitoni
================================================================================

Simulazione di un sistema gerarchico:
- Livello 2: 1 MacroSolitone (24 compositi)
- Livello 1: 24 SolitoneComposito (24 segmenti ciascuno)
- Livello 0: 576 SegmentoQuantistico totali

OBIETTIVO:
Verificare che la conservazione energetica e l'auto-organizzazione
si mantengono attraverso la gerarchia frattale.

FISICA:
- Cold Start: v ∈ [-0.1, 0.1]
- Screening adattivo locale
- Decadimento spaziale: W_ij = exp(-d_ij / L_eff)
- Exchange topologico: lambda_exchange scalato con alpha_K
- Cooling dinamico: gamma = 0.1 -> 0.001

SCALING:
- alpha_K(L2) = alpha_K(L0) · 24^4 = 1.0 · 331,776
- lambda_exchange(L2) = 5.0 · 331,776 = 1,658,880
================================================================================
"""

import sys
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List
from dataclasses import dataclass

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.macro_solitone_factory import MacroSolitoneFactory
from wqt_oop.solitone_composito import SolitoneComposito


@dataclass
class FractalMetrics:
    """Metriche sistema frattale."""
    step: int
    H_total: float
    E_radiated: float
    H_conserved: float
    chi_barycenter: float  # Baricentro campo chi
    n_composites_matter: int  # Compositi con chi_center > 0
    n_composites_space: int   # Compositi con chi_center <= 0


class FractalSimulation:
    """Simulazione MacroSolitone Livello 2."""
    
    def __init__(
        self,
        lambda_exchange_base: float = 5.0,
        v_range: tuple = (-0.1, 0.1),
        seed: int = 42
    ):
        """
        Inizializza sistema frattale Livello 2.
        
        Parameters:
        -----------
        lambda_exchange_base : float
            Intensità scambio topologico base
        v_range : tuple
            Range velocità cold start
        seed : int
            Seed riproducibilità
        """
        self.seed = seed
        self.v_range = v_range
        
        print("=" * 80)
        print(" COSTRUZIONE SISTEMA FRATTALE LIVELLO 2")
        print("=" * 80)
        
        # Crea contesto fisico base con scaling corretto
        base_ctx = PhysicsContext(
            level=0,
            length_scale=1.616255e-35,
            alpha_K=1.0,
            beta_potential=0.001,
            kappa_coupling=0.25,
            lambda_exchange=lambda_exchange_base,
            sigma_chi=3.0,
            sigma_velocity=2.0,
            sigma_torsion=2.0 * np.pi,
            sigma_tau=5.0
        )
        
        # Contesti gerarchici
        self.ctx_0 = PhysicsContext.for_level(0, base_context=base_ctx)
        self.ctx_1 = PhysicsContext.for_level(1, base_context=base_ctx)
        self.ctx_2 = PhysicsContext.for_level(2, base_context=base_ctx)
        
        print(f"\nSCALING FISICO:")
        print(f"  Livello 0: alpha_K = {self.ctx_0.alpha_K:.1f}, lambda_ex = {self.ctx_0.lambda_exchange:.1f}")
        print(f"  Livello 1: alpha_K = {self.ctx_1.alpha_K:.1f}, lambda_ex = {self.ctx_1.lambda_exchange:.1f}")
        print(f"  Livello 2: alpha_K = {self.ctx_2.alpha_K:.1f}, lambda_ex = {self.ctx_2.lambda_exchange:.1f}")
        print(f"  Rapporto lambda/alpha_K = {self.ctx_2.lambda_exchange / self.ctx_2.alpha_K:.6f} (costante)")
        
        # Costruisci MacroSolitone
        print(f"\nCOSTRUZIONE GERARCHIA...")
        self.macro = MacroSolitoneFactory.build_level_2_macro(
            self.ctx_2,
            n_composites=24,
            matter_fraction=0.375,  # ~9/24 per composito
            v_range=v_range,
            seed=seed
        )
        
        print(f"  [OK] MacroSolitone creato")
        print(f"    N_compositi (L1) = {self.macro.N_children}")
        print(f"    N_segmenti (L0)  = {self.macro.N_children * 24}")
        print(f"    N_DOF totali     = {self.macro.get_num_dof()}")
        print(f"    H_total_init     = {self.macro.energia_totale:.6e}")
        
        # Storia metriche
        self.history: List[FractalMetrics] = []
    
    def _compute_fractal_metrics(self, step: int) -> FractalMetrics:
        """Calcola metriche sistema frattale."""
        budget = self.macro.get_energy_budget()
        
        # Baricentro campo χ
        chi_center = self.macro.compute_barycenter()
        
        # Conta compositi per fase
        n_matter = 0
        n_space = 0
        for composite in self.macro.children:
            chi_comp = composite.compute_barycenter()
            if chi_comp > 0:
                n_matter += 1
            else:
                n_space += 1
        
        return FractalMetrics(
            step=step,
            H_total=budget['H_total'],
            E_radiated=budget['E_radiated'],
            H_conserved=budget['H_conserved'],
            chi_barycenter=chi_center,
            n_composites_matter=n_matter,
            n_composites_space=n_space
        )
    
    def run(
        self,
        N_steps: int = 1000,
        dt: float = 0.001,
        cooling_steps: int = 200,
        gamma_cool: float = 0.1,
        gamma_conserve: float = 0.001,
        log_interval: int = 50
    ) -> None:
        """
        Esegue simulazione frattale.
        
        Parameters:
        -----------
        N_steps : int
            Numero step temporali
        dt : float
            Timestep (ridotto per stabilita con alpha_K grande)
        cooling_steps : int
            Step con cooling alto
        gamma_cool, gamma_conserve : float
            Coefficienti smorzamento
        log_interval : int
            Intervallo logging
        """
        print("\n" + "=" * 80)
        print(" SIMULAZIONE FRATTALE: Auto-Organizzazione Gerarchica")
        print("=" * 80)
        print(f"N_steps       = {N_steps}")
        print(f"dt            = {dt}")
        print(f"Cooling:      gamma = {gamma_cool} (step < {cooling_steps}), {gamma_conserve} (step >= {cooling_steps})")
        print(f"Screening:    ADATTIVO (rho_threshold = {self.macro.rho_threshold})")
        print(f"Accoppiamento: exp(-d_ij / {self.macro.L_eff})")
        print()
        
        # Metriche iniziali
        metrics_init = self._compute_fractal_metrics(0)
        self.history.append(metrics_init)
        
        print(f"STATO INIZIALE:")
        print(f"  H_total      = {metrics_init.H_total:.6e}")
        print(f"  chi_barycenter = {metrics_init.chi_barycenter:.3f}")
        print(f"  Compositi M/S = {metrics_init.n_composites_matter}/{metrics_init.n_composites_space}")
        print()
        
        # Header log
        print(f"{'Step':>6}  {'H_total':>12}  {'E_rad':>12}  {'H_cons':>12}  "
              f"{'chi_bar':>8}  {'M/S':>6}  {'gamma':>10}")
        print("-" * 80)
        
        # Evoluzione
        for step in range(1, N_steps + 1):
            # Cooling dinamico
            gamma = gamma_cool if step < cooling_steps else gamma_conserve
            
            # Applica gamma a TUTTI i segmenti atomici (ricorsivamente)
            self._set_gamma_recursive(self.macro, gamma)
            
            # Evolvi MacroSolitone (ricorsione automatica)
            self.macro.evolve(dt)
            
            # Metriche
            metrics = self._compute_fractal_metrics(step)
            self.history.append(metrics)
            
            # Log
            if step % log_interval == 0 or step == N_steps:
                print(f"{step:6d}  {metrics.H_total:12.4e}  "
                      f"{metrics.E_radiated:12.4e}  "
                      f"{metrics.H_conserved:12.4e}  "
                      f"{metrics.chi_barycenter:8.3f}  "
                      f"{metrics.n_composites_matter:2d}/{metrics.n_composites_space:2d}  "
                      f"{gamma:10.6f}")
        
        print()
        self._print_results(metrics_init)
    
    def _set_gamma_recursive(self, soliton, gamma: float) -> None:
        """Imposta gamma ricorsivamente su tutti i segmenti atomici."""
        from wqt_oop.segmento_quantistico import SegmentoQuantistico
        
        if isinstance(soliton, SegmentoQuantistico):
            soliton.gamma_damping = gamma
        elif isinstance(soliton, SolitoneComposito):
            for child in soliton.children:
                self._set_gamma_recursive(child, gamma)
    
    def _print_results(self, metrics_init: FractalMetrics) -> None:
        """Stampa risultati finali."""
        metrics_final = self.history[-1]
        
        # Drift
        H_init = metrics_init.H_conserved
        H_final = metrics_final.H_conserved
        drift = abs((H_final - H_init) / H_init) * 100
        
        print("=" * 80)
        print(" RISULTATI SIMULAZIONE FRATTALE")
        print("=" * 80)
        print()
        
        print("CONSERVAZIONE TERMODINAMICA:")
        print(f"  H_conserved_init  = {H_init:.6e}")
        print(f"  H_conserved_final = {H_final:.6e}")
        print(f"  Drift             = {drift:.6f}%")
        if drift < 0.01:
            print(f"  Stato: CONSERVATO PERFETTAMENTE")
        elif drift < 1.0:
            print(f"  Stato: CONSERVATO")
        else:
            print(f"  Stato: DRIFT ECCESSIVO")
        print()
        
        print("AUTO-ORGANIZZAZIONE GERARCHICA:")
        print(f"  Compositi M/S iniziali = {metrics_init.n_composites_matter}/{metrics_init.n_composites_space}")
        print(f"  Compositi M/S finali   = {metrics_final.n_composites_matter}/{metrics_final.n_composites_space}")
        print(f"  chi_barycenter iniziale  = {metrics_init.chi_barycenter:.3f}")
        print(f"  chi_barycenter finale    = {metrics_final.chi_barycenter:.3f}")
        
        # Stabilità configurazione
        last_100 = [m.n_composites_matter for m in self.history[-100:]]
        std_last = np.std(last_100)
        print(f"  Stabilita ultimi 100 step: sigma = {std_last:.3f}")
        if std_last < 0.5:
            print(f"  Stato: CONFIGURAZIONE STABILE")
        else:
            print(f"  Stato: Oscillante")
        print()
        
        # Salva storia
        self._save_history()
        
        print("=" * 80)
    
    def _save_history(self, filename: str = "fractal_l2_history.npz") -> None:
        """Salva storia su file."""
        steps = np.array([m.step for m in self.history])
        H_total = np.array([m.H_total for m in self.history])
        E_radiated = np.array([m.E_radiated for m in self.history])
        H_conserved = np.array([m.H_conserved for m in self.history])
        chi_barycenter = np.array([m.chi_barycenter for m in self.history])
        n_matter = np.array([m.n_composites_matter for m in self.history])
        n_space = np.array([m.n_composites_space for m in self.history])
        
        np.savez(
            filename,
            steps=steps,
            H_total=H_total,
            E_radiated=E_radiated,
            H_conserved=H_conserved,
            chi_barycenter=chi_barycenter,
            n_composites_matter=n_matter,
            n_composites_space=n_space
        )
        print(f"Storia salvata in: {filename}")


if __name__ == "__main__":
    # Crea simulazione con COLD START ESTREMO per Livello 2
    sim = FractalSimulation(
        lambda_exchange_base=5.0,
        v_range=(-0.01, 0.01),  # Cold Start ULTRA-FREDDO (10x più freddo di L1)
        seed=42
    )
    
    # Esegui simulazione (TEST RAPIDO: 200 step)
    # NOTA: dt ridotto a 0.0001 per gestire alpha_K ~ 331k
    sim.run(
        N_steps=200,  # Ridotto per test (prod: 1000+)
        dt=0.0001,  # 10x più piccolo per stabilità Livello 2
        cooling_steps=100,  # Cooling esteso (come richiesto: t<200)
        gamma_cool=0.1,  # Dissipazione forte iniziale
        gamma_conserve=0.001,  # Conservazione dopo cooling
        log_interval=20  # Log più frequente
    )
