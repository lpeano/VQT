"""
SIMULAZIONE DI PRODUZIONE AVANZATA: Osservazione della Separazione di Fase Materia/Spazio

Questo script simula l'evoluzione di un sistema composito di 24 segmenti quantistici
per osservare la nascita spontanea di struttura dall'energia.

METRICHE MONITORATE:
1. Conservazione termodinamica (H_conserved = const)
2. Separazione di fase (conta χ > 0 vs χ < 0)
3. Dinamica del confine (transizioni materia ↔ spazio)
4. Clustering spaziale (formazione di strutture coerenti)
5. Correlazione fusione/radiazione (eventi topologici)

FISICA:
- Einstein-Cartan con torsione quantizzata
- Dissipazione radiativa simplettica (F = -γ·v)
- Accoppiamento Leech 24D con screening
- Fusione inelastica con conservazione topologica
"""

import sys
sys.path.insert(0, r"c:\Users\lpeano\plank\VQT")

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito


@dataclass
class PhaseMetrics:
    """Metriche separazione di fase."""
    n_matter: int  # Segmenti con χ > 0
    n_space: int   # Segmenti con χ < 0
    matter_fraction: float  # Frazione materia
    boundary_flux: int  # Transizioni materia↔spazio dall'ultimo step
    
    
@dataclass
class ClusterMetrics:
    """Metriche clustering spaziale."""
    matter_cluster_size: float  # Raggio medio cluster materia
    space_cluster_size: float   # Raggio medio cluster spazio
    separation_index: float     # Indice separazione (0=misto, 1=separato)
    

@dataclass
class RadiationEvent:
    """Evento di radiazione significativo."""
    step: int
    E_radiated_delta: float  # Energia radiata in questo step
    Var_tau: float  # Disomogeneità temporale
    eta_eff: float  # Efficienza radiativa
    n_matter: int   # Configurazione materia/spazio


class ProductionSimulation:
    """Simulazione di produzione con monitoraggio avanzato."""
    
    def __init__(self, N_segments: int = 24, seed: int = 42):
        """
        Inizializza simulazione.
        
        Parameters:
        -----------
        N_segments : int
            Numero segmenti (deve essere multiplo di 24)
        seed : int
            Seed per riproducibilità
        """
        assert N_segments % 24 == 0, "N deve essere multiplo di 24"
        
        self.N_segments = N_segments
        self.seed = seed
        np.random.seed(seed)
        
        # Physics contexts con lambda_exchange forte per aggregazione
        base_ctx = PhysicsContext(
            level=0,
            length_scale=1.616255e-35,
            alpha_K=1.0,
            beta_potential=0.001,
            kappa_coupling=0.25,
            lambda_exchange=5.0,  # 100x default per vincere energia cinetica
            sigma_chi=3.0,
            sigma_velocity=2.0,
            sigma_torsion=2.0 * np.pi,
            sigma_tau=5.0
        )
        self.ctx_0 = base_ctx
        self.ctx_1 = PhysicsContext.for_level(1, base_context=base_ctx)
        
        # Crea segmenti con separazione di fase iniziale
        self.segments = self._initialize_segments()
        
        # Crea solitone composito (screening ADATTIVO sempre abilitato)
        self.soliton = SolitoneComposito(
            self.segments, 
            self.ctx_1, 
            screening_enabled=True  # Sempre ON ma adattivo localmente
        )
        
        # Storia
        self.history: Dict[str, List] = {
            'steps': [],
            'H_total': [],
            'E_radiated': [],
            'H_conserved': [],
            'n_matter': [],
            'n_space': [],
            'boundary_flux': [],
            'cluster_size': [],
            'separation_index': [],
            'gamma': []
        }
        
        # Eventi radiazione
        self.radiation_events: List[RadiationEvent] = []
        
        # Stato precedente per boundary flux
        self._prev_phase_labels = None
    
    def _initialize_segments(self) -> List[SegmentoQuantistico]:
        """
        Crea segmenti con separazione di fase iniziale.
        
        Configurazione:
        - 9 segmenti "materia" (χ ~ +4.5, v piccola)
        - 15 segmenti "spazio" (χ ~ -4.5, v piccola)
        
        Returns:
        --------
        segments : List[SegmentoQuantistico]
        """
        segments = []
        
        # Primi 9: materia (COLD START: v ridotta 20x)
        for i in range(9):
            chi_init = np.random.uniform(3.5, 5.5)  # Intorno a +4.5
            v_init = np.random.uniform(-0.1, 0.1)  # COLD: era [-2,2], ora [-0.1,0.1]
            seg = SegmentoQuantistico(chi_init, v_init, self.ctx_0)
            segments.append(seg)
        
        # Rimanenti 15: spazio (COLD START: v ridotta 20x)
        for i in range(15):
            chi_init = np.random.uniform(-5.5, -3.5)  # Intorno a -4.5
            v_init = np.random.uniform(-0.1, 0.1)  # COLD: era [-2,2], ora [-0.1,0.1]
            seg = SegmentoQuantistico(chi_init, v_init, self.ctx_0)
            segments.append(seg)
        
        # Mischia ordine (non vogliamo clustering artificiale)
        np.random.shuffle(segments)
        
        return segments
    
    def _compute_phase_metrics(self) -> PhaseMetrics:
        """Calcola metriche separazione di fase."""
        state = self.soliton.get_state_vector()
        chi_vals = state[::2]  # Estrai χ (posizioni pari)
        
        # Etichette fase
        phase_labels = (chi_vals > 0).astype(int)  # 1=materia, 0=spazio
        n_matter = np.sum(phase_labels)
        n_space = self.N_segments - n_matter
        
        # Boundary flux (quante transizioni dall'ultimo step)
        if self._prev_phase_labels is not None:
            boundary_flux = np.sum(phase_labels != self._prev_phase_labels)
        else:
            boundary_flux = 0
        
        self._prev_phase_labels = phase_labels.copy()
        
        return PhaseMetrics(
            n_matter=n_matter,
            n_space=n_space,
            matter_fraction=n_matter / self.N_segments,
            boundary_flux=boundary_flux
        )
    
    def _compute_cluster_metrics(self) -> ClusterMetrics:
        """
        Calcola metriche clustering spaziale.
        
        NOTA: Usa indici come "posizioni" (reticolo 1D circolare).
        Per un sistema 3D, si userebbero coordinate spaziali reali.
        """
        state = self.soliton.get_state_vector()
        chi_vals = state[::2]
        
        # Indici materia/spazio
        matter_idx = np.where(chi_vals > 0)[0]
        space_idx = np.where(chi_vals <= 0)[0]
        
        # Calcola "raggio" medio cluster (distanza media tra nodi stessa fase)
        def cluster_radius(indices):
            if len(indices) < 2:
                return 0.0
            distances = []
            for i in range(len(indices)):
                for j in range(i+1, len(indices)):
                    # Distanza circolare
                    d = min(abs(indices[i] - indices[j]), 
                           self.N_segments - abs(indices[i] - indices[j]))
                    distances.append(d)
            return np.mean(distances) if distances else 0.0
        
        matter_cluster = cluster_radius(matter_idx)
        space_cluster = cluster_radius(space_idx)
        
        # Indice separazione (0=casuale, 1=perfettamente separato)
        # Se materia/spazio formano cluster contigui, matter_cluster è piccolo
        max_separation = self.N_segments / 4  # Normalizzazione
        separation = 1.0 - min(matter_cluster, max_separation) / max_separation
        
        return ClusterMetrics(
            matter_cluster_size=matter_cluster,
            space_cluster_size=space_cluster,
            separation_index=separation
        )
    
    def _detect_radiation_event(self, step: int, E_rad_delta: float) -> None:
        """
        Rileva eventi di radiazione significativi.
        
        Soglia: E_rad_delta > 10% di H_total
        """
        budget = self.soliton.get_energy_budget()
        H_total = budget['H_total']
        
        if H_total > 1e-6 and abs(E_rad_delta) / H_total > 0.10:
            # Calcola Var(tau) e eta_eff
            aux = self.soliton.get_auxiliary_state()
            tau_vals = aux['tau_locale']
            Var_tau = np.var(tau_vals)
            eta_eff = self.ctx_1.compute_radiation_efficiency(Var_tau)
            
            # Conta materia
            state = self.soliton.get_state_vector()
            chi_vals = state[::2]
            n_matter = np.sum(chi_vals > 0)
            
            event = RadiationEvent(
                step=step,
                E_radiated_delta=E_rad_delta,
                Var_tau=Var_tau,
                eta_eff=eta_eff,
                n_matter=n_matter
            )
            self.radiation_events.append(event)
    
    def run(self, N_steps: int = 1000, dt: float = 0.1, log_interval: int = 50) -> None:
        """
        Esegue simulazione di produzione.
        
        Parameters:
        -----------
        N_steps : int
            Numero di steps temporali
        dt : float
            Timestep
        log_interval : int
            Intervallo logging
        """
        print("=" * 80)
        print(" COLD UNIVERSE: Screening Adattivo + Decadimento Spaziale")
        print("=" * 80)
        print(f"N_segments      = {self.N_segments}")
        print(f"lambda_exchange = {self.ctx_1.lambda_exchange} (100x default)")
        print(f"v_init          = [-0.1, 0.1] (COLD START)")
        print(f"Cooling:        gamma=0.1 (step<200), gamma=0.001 (step>=200)")
        print(f"Screening:      ADATTIVO (cluster=forte, vuoto=debole)")
        print(f"rho_threshold   = {self.soliton.rho_threshold}")
        print(f"Accoppiamento:  W_ij = exp(-d_ij/{self.soliton.L_eff}) (decadimento spaziale)")
        print(f"N_steps         = {N_steps}")
        print(f"dt              = {dt}")
        print()
        
        # Bilancio iniziale
        budget_init = self.soliton.get_energy_budget()
        phase_init = self._compute_phase_metrics()
        
        print("CONFIGURAZIONE INIZIALE:")
        print(f"  H_total         = {budget_init['H_total']:.6e}")
        print(f"  Materia (chi>0) = {phase_init.n_matter} / {self.N_segments}")
        print(f"  Spazio (chi<=0) = {phase_init.n_space} / {self.N_segments}")
        print(f"  Frazione matter = {phase_init.matter_fraction:.2%}")
        print()
        
        # Log header
        print(f"{'Step':>6}  {'H_total':>12}  {'E_rad':>12}  {'H_cons':>12}  "
              f"{'M/S':>6}  {'Flux':>5}  {'Sep':>6}  {'gamma':>10}")
        print("-" * 80)
        
        # Tracking energia radiata precedente
        E_rad_prev = 0.0
        
        # Evoluzione con COOLING DINAMICO (screening sempre adattivo)
        for step in range(1, N_steps + 1):
            # === COOLING DINAMICO ===
            # Step < 200: gamma alto (dissipazione rapida)
            # Step >= 200: gamma basso (conservazione)
            if step < 200:
                gamma_target = 0.1  # Cooling forte
            else:
                gamma_target = 0.001  # Conservazione
            
            # Applica gamma a tutti i segmenti
            for seg in self.segments:
                seg.gamma_damping = gamma_target
            
            # Evolvi sistema (screening ADATTIVO automatico)
            self.soliton.evolve(dt)
            
            # Raccogli metriche
            budget = self.soliton.get_energy_budget()
            phase = self._compute_phase_metrics()
            cluster = self._compute_cluster_metrics()
            
            # Gamma corrente (da primo segmento)
            gamma_current = self.segments[0].gamma_damping
            
            # Rileva eventi radiazione
            E_rad_delta = budget['E_radiated'] - E_rad_prev
            if E_rad_delta != 0:  # Solo se c'e' variazione
                self._detect_radiation_event(step, E_rad_delta)
            E_rad_prev = budget['E_radiated']
            
            # Salva storia
            self.history['steps'].append(step)
            self.history['H_total'].append(budget['H_total'])
            self.history['E_radiated'].append(budget['E_radiated'])
            self.history['H_conserved'].append(budget['H_conserved'])
            self.history['n_matter'].append(phase.n_matter)
            self.history['n_space'].append(phase.n_space)
            self.history['boundary_flux'].append(phase.boundary_flux)
            self.history['cluster_size'].append(cluster.matter_cluster_size)
            self.history['separation_index'].append(cluster.separation_index)
            self.history['gamma'].append(gamma_current)
            
            # Log
            if step % log_interval == 0 or step == N_steps:
                print(f"{step:6d}  {budget['H_total']:12.4e}  "
                      f"{budget['E_radiated']:12.4e}  "
                      f"{budget['H_conserved']:12.4e}  "
                      f"{phase.n_matter:2d}/{phase.n_space:2d}  "
                      f"{phase.boundary_flux:5d}  "
                      f"{cluster.separation_index:6.3f}  "
                      f"{gamma_current:10.6f}")
        
        print()
        self._print_results(budget_init)
    
    def _print_results(self, budget_init: Dict[str, float]) -> None:
        """Stampa risultati finali."""
        budget_final = self.soliton.get_energy_budget()
        
        # Drift H_conserved
        H_cons_init = budget_init['H_conserved']
        H_cons_final = budget_final['H_conserved']
        drift = abs((H_cons_final - H_cons_init) / H_cons_init) * 100
        
        # Statistiche fase
        n_matter_mean = np.mean(self.history['n_matter'])
        n_matter_std = np.std(self.history['n_matter'])
        
        # Statistiche clustering
        sep_mean = np.mean(self.history['separation_index'])
        sep_max = np.max(self.history['separation_index'])
        
        # Boundary flux totale
        flux_total = np.sum(self.history['boundary_flux'])
        
        print("=" * 80)
        print(" RISULTATI SIMULAZIONE")
        print("=" * 80)
        print()
        print("CONSERVAZIONE TERMODINAMICA:")
        print(f"  H_conserved_init  = {H_cons_init:.6e}")
        print(f"  H_conserved_final = {H_cons_final:.6e}")
        print(f"  Drift             = {drift:.6f}%")
        print(f"  Stato: {'CONSERVATO' if drift < 1.0 else 'DRIFT ECCESSIVO'}")
        print()
        
        print("SEPARAZIONE DI FASE:")
        print(f"  Materia media     = {n_matter_mean:.1f} +/- {n_matter_std:.1f}")
        print(f"  Configurazione    = {self.history['n_matter'][-1]}/24 materia")
        print(f"  Transizioni tot   = {flux_total} (materia<->spazio)")
        print(f"  Stabilita confine = {'STABILE' if flux_total < 100 else 'INSTABILE'}")
        print()
        
        print("CLUSTERING SPAZIALE:")
        print(f"  Separation index  = {sep_mean:.3f} (media)")
        print(f"  Separation max    = {sep_max:.3f}")
        print(f"  Cluster size      = {self.history['cluster_size'][-1]:.2f} (finale)")
        print(f"  Auto-organizzaz.  = {'PRESENTE' if sep_mean > 0.3 else 'CASUALE'}")
        print()
        
        print("EVENTI DI RADIAZIONE:")
        print(f"  Eventi rilevati   = {len(self.radiation_events)}")
        if self.radiation_events:
            # Top 3 eventi più energetici
            top_events = sorted(self.radiation_events, 
                              key=lambda e: abs(e.E_radiated_delta), 
                              reverse=True)[:3]
            print(f"  Top 3 eventi energetici:")
            for i, event in enumerate(top_events, 1):
                print(f"    {i}. Step {event.step:4d}: "
                      f"dE={event.E_radiated_delta:+.2e}, "
                      f"eta={event.eta_eff:.4f}, "
                      f"Materia={event.n_matter}/24")
        print()
        
        print("=" * 80)
        
        # Salva storia su file
        self._save_history()
    
    def _save_history(self, filename: str = "produzione_history.npz") -> None:
        """Salva storia simulazione su file."""
        np.savez(
            filename,
            steps=self.history['steps'],
            H_total=self.history['H_total'],
            E_radiated=self.history['E_radiated'],
            H_conserved=self.history['H_conserved'],
            n_matter=self.history['n_matter'],
            n_space=self.history['n_space'],
            boundary_flux=self.history['boundary_flux'],
            cluster_size=self.history['cluster_size'],
            separation_index=self.history['separation_index'],
            gamma=self.history['gamma']
        )
        print(f"Storia salvata in: {filename}")


if __name__ == "__main__":
    # Crea simulazione
    sim = ProductionSimulation(N_segments=24, seed=42)
    
    # Esegui 1000 steps con dt ridotto (forze E_torsion ~ 576x più forti)
    sim.run(N_steps=1000, dt=0.001, log_interval=50)
