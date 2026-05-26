"""
================================================================================
SEGMENTO QUANTISTICO - Livello 0 (Atomo della Gerarchia)
================================================================================

Implementazione concreta di AbstractSoliton per il livello base.
Rappresenta un singolo segmento quantistico con 2 DOF: (χ, v)

FISICA:
- Hamiltoniana: H = (1/2)mv² + β(χ²-χ₀²)² + αₖK²
- Evoluzione: integratore simplettico Verlet
- Torsione: K² quantizzata secondo soglia di Planck
================================================================================
"""

import numpy as np
from typing import Dict, Optional
from .abstract_soliton import AbstractSoliton
from .physics_context import PhysicsContext


class SegmentoQuantistico(AbstractSoliton):
    """
    Segmento quantistico singolo (livello 0).
    
    Rappresenta l'unità atomica del manifold frattale.
    
    Degrees of Freedom (DOF): 2
    - χ (chi): Campo scalare (potenziale topologico)
    - v: Velocità coniugata (∂χ/∂t)
    
    Variabili Ausiliarie:
    - τ (tau_locale): Tempo proprio locale
    - Ω (chiusura): Errore chiusura spinoriale
    
    Nota: K² (torsione) è una proprietà GEOMETRICA che emerge
    solo nell'interazione tra segmenti (SolitoneComposito).
    
    Attributes:
    -----------
    chi : float
        Campo scalare χ
    
    vel : float
        Velocità ∂χ/∂t
    
    tau_locale : float
        Tempo proprio accumulato
    
    chiusura : float
        Errore chiusura spinore
    
    position : ndarray, shape (3,)
        Posizione spaziale del segmento
    """
    
    def __init__(self, 
                 chi: float, 
                 vel: float, 
                 physics: PhysicsContext,
                 position: Optional[np.ndarray] = None):
        """
        Inizializza segmento quantistico.
        
        Parameters:
        -----------
        chi : float
            Valore iniziale campo χ
        
        vel : float
            Velocità iniziale
        
        physics : PhysicsContext
            Contesto fisico (livello 0)
        
        position : ndarray, optional
            Posizione spaziale 3D
        """
        super().__init__(physics)
        
        assert physics.level == 0, "SegmentoQuantistico richiede livello=0"
        
        # Stato dinamico
        self.chi: float = chi
        self.vel: float = vel
        
        # Variabili ausiliarie
        self.tau_locale: float = 0.0
        self.chiusura: float = 0.0
        
        # Dissipazione (mutabile, aggiornato da SolitoneComposito)
        self.gamma_damping: float = 0.0  # Coefficiente smorzamento [1/s]
        
        # Sub-stepping adattivo (stabilità locale)
        self._force_prev: float = 0.0  # Forza step precedente (tracking)
        self._local_friction: float = 0.0  # Viscosità locale adattiva
        self._substep_threshold: float = 100.0  # Soglia variazione forza per sub-stepping
        self._substep_count: int = 4  # Numero micro-step
        
        # Posizione spaziale
        self.position: np.ndarray = position if position is not None else np.zeros(3)
        
        # Massa effettiva (unità naturali)
        self.mass: float = 1.0
    
    def get_state_vector(self) -> np.ndarray:
        """Stato: [χ, v]"""
        return np.array([self.chi, self.vel])
    
    def set_state_vector(self, state: np.ndarray) -> None:
        """Imposta [χ, v]."""
        super().set_state_vector(state)
        self.chi = state[0]
        self.vel = state[1]
    
    def get_auxiliary_state(self) -> Dict[str, np.ndarray]:
        """Restituisce τ, Ω come array (singolo elemento)."""
        return {
            'tau_locale': np.array([self.tau_locale]),
            'contorsione': np.array([0.0]),  # Placeholder per compatibilità
            'chiusura_spinore': np.array([self.chiusura])
        }
    
    def compute_hamiltonian_internal(self) -> float:
        """
        Hamiltoniana dinamica (conservata dall'integratore).
        
        H_dyn = T + V
        
        T = (1/2) m v²
        V = β (χ² - χ₀²)²
        
        NOTA: E_tors = α_K·K² è energia diagnostica, NON parte
        dell'Hamiltoniana dinamica (K² richiede derivate spaziali).
        """
        # Energia cinetica
        T = 0.5 * self.mass * self.vel**2
        
        # Potenziale doppio pozzo (Mexican hat)
        chi_0 = 4.5  # Minimo asimmetrico
        V = self.physics.beta_potential * (self.chi**2 - chi_0**2)**2
        
        return T + V
    
    def compute_hamiltonian_coupling(self) -> float:
        """
        Per segmento singolo, accoppiamento = 0.
        (Viene calcolato a livello SolitoneComposito)
        """
        return 0.0
    
    def get_position(self) -> np.ndarray:
        """Posizione centroide = posizione segmento."""
        return self.position.copy()
    
    def get_topology_charge(self) -> float:
        """
        Carica topologica = χ (singolo segmento).
        
        Nota: Per un segmento isolato, Q=χ è la coordinata del campo.
        L'invariante globale Σχᵢ emerge solo nel SolitoneComposito.
        
        Returns:
        --------
        Q : float
            Carica topologica (campo χ)
        """
        return self.chi
    
    def get_spinor_closure(self) -> float:
        """Chiusura = τ (mod 4π)."""
        return self.tau_locale % (4 * np.pi)
    
    # =========================================================================
    # [LEGGE FISICA: Forza Totale Hamiltoniana + Dissipazione]
    # Principio: La forza su un segmento è la somma di contributi conservativi
    #            (Hamiltoniana) e dissipativi (damping gerarchico + viscosità locale).
    # 
    # Derivazione: Equazione di Langevin generalizzata per sistemi frattali:
    #              m·a = F_conservative + F_damping + F_friction + F_external
    #              dove F_damping = -γ_h·v (gerarchico, da SolitoneComposito)
    #              e F_friction = -η_local·v (locale, auto-regolante).
    # 
    # Validazione: TODO_VALIDATION → test_l3_stability (test_universal_scaling.py)
    # =========================================================================
    def _compute_force(self, external_force: float = 0.0, include_local_friction: bool = True) -> float:
        """
        Forza totale dall'Hamiltoniana dinamica + dissipazione.
        
        H_dynamical = T + V(χ)
        F_potential = -∂V/∂χ
        F_damping = -γ·v  (smorzamento viscoso gerarchico)
        F_friction = -η_local·v  (viscosità locale adattiva, solo se drift > 5%)
        
        NOTA: La forza di smorzamento permette al sistema di radiare energia
        in modo simplettico-compatibile (nessun drift numerica).
        
        Parameters:
        -----------
        external_force : float
            Forza da accoppiamento esterno
        
        include_local_friction : bool
            Se True, include viscosità locale adattiva
        
        Returns:
        --------
        F_total : float
            Forza totale
        """
        chi_0 = 4.5
        
        # Derivata potenziale doppio pozzo
        F_potential = -4 * self.physics.beta_potential * self.chi * (self.chi**2 - chi_0**2)
        
        # Forza di smorzamento gerarchico (da SolitoneComposito)
        F_damping = -self.gamma_damping * self.vel
        
        # Viscosità locale adattiva (attivata solo se drift > 5%)
        F_friction = 0.0
        if include_local_friction and self._local_friction > 0:
            F_friction = -self._local_friction * self.vel
        
        return F_potential + F_damping + F_friction + external_force
    
    # =========================================================================
    # [LEGGE FISICA: Integratore Simplettico con Sub-Stepping Adattivo]
    # Principio: Quando forze variano rapidamente (|ΔF| > threshold), la
    #            stabilità numerica richiede riduzione locale del timestep.
    # 
    # Derivazione: Condizione di Courant-Friedrichs-Lewy (CFL) per stabilità:
    #              dt_max = C · dx / |v_max|, dove C < 1.
    #              Con forze variabili, CFL viene violata → sub-stepping.
    # 
    # Algoritmo: Velocity Verlet (simplettico, conservativo O(dt³)):
    #            1. v_{n+1/2} = v_n + (F_n/m)·(dt/2)   [half-kick]
    #            2. χ_{n+1} = χ_n + v_{n+1/2}·dt      [drift]
    #            3. F_{n+1} = F(χ_{n+1})              [ricalcola]
    #            4. v_{n+1} = v_{n+1/2} + (F_{n+1}/m)·(dt/2)  [half-kick]
    # 
    # Validazione: TODO_VALIDATION → drift < 10% su L3 (cosmology_L3.h5)
    # =========================================================================
    def evolve(self, dt: float, external_force: np.ndarray = None) -> None:
        """
        Evoluzione simplettica con sub-stepping adattivo.
        
        ALGORITMO ADATTIVO:
        1. Calcola variazione forza |F_t - F_{t-1}|
        2. Se |ΔF| > threshold → esegui 4 micro-step con dt/4
        3. Altrimenti → singolo step standard
        4. Se drift locale > 5% → attiva viscosità locale
        
        ALGORITMO SIMPLETTICO (Velocity Verlet):
        1. v_{n+1/2} = v_n + (F_n/m)·(dt/2)     [half-kick]
        2. χ_{n+1} = χ_n + v_{n+1/2}·dt         [drift]
        3. F_{n+1} = F(χ_{n+1})                 [ricalcola forza]
        4. v_{n+1} = v_{n+1/2} + (F_{n+1}/m)·(dt/2)  [half-kick]
        
        Parameters:
        -----------
        dt : float
            Passo temporale
        
        external_force : ndarray, optional
            Forza esterna (scalare o array 1D)
        """
        # Energia pre-evoluzione (per controllo conservazione)
        H_before = self.energia_totale
        
        # Converti external_force
        ext_f = 0.0 if external_force is None else float(external_force)
        
        # --- DECISIONE SUB-STEPPING ---
        # [LEGGE FISICA: Criterio CFL Adattivo]
        # Se |ΔF| > threshold → forze variabili richiedono dt ridotto
        F_current = self._compute_force(ext_f, include_local_friction=False)
        delta_F = abs(F_current - self._force_prev)
        
        # Se forza varia troppo rapidamente, usa sub-stepping
        use_substeps = delta_F > self._substep_threshold
        n_steps = self._substep_count if use_substeps else 1
        dt_step = dt / n_steps
        
        # --- EVOLUZIONE (singolo o multi-step) ---
        for _ in range(n_steps):
            # HALF-KICK 1 (v_n → v_{n+1/2})
            F_n = self._compute_force(ext_f)
            v_half = self.vel + (F_n / self.mass) * (dt_step / 2.0)
            
            # DRIFT (χ_n → χ_{n+1} usando v_{n+1/2})
            self.chi += v_half * dt_step
            
            # HALF-KICK 2 (v_{n+1/2} → v_{n+1})
            F_n_plus_1 = self._compute_force(ext_f)  # Forza NUOVA
            self.vel = v_half + (F_n_plus_1 / self.mass) * (dt_step / 2.0)
            
            # Clipping velocità (solo se singolo step, altrimenti alla fine)
            if n_steps == 1:
                self.vel = np.clip(self.vel, -self.physics.MAX_VELOCITY, self.physics.MAX_VELOCITY)
        
        # Clipping finale per multi-step
        if n_steps > 1:
            self.vel = np.clip(self.vel, -self.physics.MAX_VELOCITY, self.physics.MAX_VELOCITY)
        
        # Salva forza per prossimo step
        self._force_prev = F_n_plus_1
        
        # --- AGING RELATIVISTICO ---
        # γ(v) = sqrt(1 + v²/V_REF²)
        V_REF = 100.0  # Velocità riferimento relativistica
        gamma_inverse = np.sqrt(1.0 + (self.vel**2) / (V_REF**2))
        self.tau_locale += dt / gamma_inverse  # dt TOTALE (non dt_step)
        
        # Invalida cache
        self._cache_valid = False
        
        # --- CONTROLLO CONSERVAZIONE ENERGIA + VISCOSITÀ ADATTIVA ---
        # [LEGGE FISICA: Auto-Regolazione Viscosa per Conservazione Locale]
        # Principio: Se drift > 5%, il sistema è fuori equilibrio locale.
        #            Viscosità locale assorbe eccesso cinetico senza violare
        #            conservazione globale (energia → calore, non persa).
        # 
        # Derivazione: Teorema di fluttuazione-dissipazione (Einstein 1905):
        #              D = k_B·T·η (diffusione ~ viscosità × temperatura).
        #              Quando drift ↑, temperatura locale ↑ → η_local ↑.
        H_after = self.energia_totale
        H_drift = abs(H_after - H_before) / (abs(H_before) + 1e-30)
        
        # ATTIVAZIONE VISCOSITÀ LOCALE se drift > 5%
        if H_drift > 5e-2:
            # Incrementa viscosità locale (risposta proporzionale)
            self._local_friction = min(self._local_friction + 0.001, 0.01)  # Max 0.01
        else:
            # Disattiva gradualmente se drift sotto controllo
            self._local_friction = max(self._local_friction - 0.0005, 0.0)
        
        # WARNING solo se drift MOLTO alto e viscosità già al massimo
        if H_drift > 0.1 and self._local_friction >= 0.01:
            import warnings
            warnings.warn(
                f"DRIFT ENERGIA CRITICO: |dH/H| = {H_drift:.3e} > 10%\n"
                f"  H_before = {H_before:.6e}\n"
                f"  H_after  = {H_after:.6e}\n"
                f"  Step dt  = {dt:.6e}\n"
                f"  Sub-steps used: {n_steps}\n"
                f"  Local friction: {self._local_friction:.6e}\n"
                f"  gamma_damping: {self.gamma_damping:.6e}"
            )
    
    def __repr__(self) -> str:
        return (
            f"SegmentoQuantistico(χ={self.chi:.3f}, v={self.vel:.3f}, "
            f"τ={self.tau_locale:.3f})"
        )
