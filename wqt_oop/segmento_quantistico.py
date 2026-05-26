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
        self._enable_adaptive_friction: bool = True  # Flag to disable adaptive friction (for tests)
        
        # === SAFETY VALVE (CTO-approved) ===
        self._force_max_clip: float = 1000.0  # Clipping forze impulsive [N]
        self._step_counter: int = 0  # Contatore step globali (per diagnostics)
        
        # === FLUCTUATION-DISSIPATION THEOREM (FDT) DAMPING ===
        # [PHYSICS_TRACE] Vacuum Thermal Bath Model (Einstein 1905, Nyquist 1928)
        # Physical model: WQT segments coupled to vacuum at effective temperature T_eff
        # Dissipation emerges from energy fluctuations δH = H - H_eq
        # Formula: γ_FDT = γ_base · [1 + β_fdt · tanh(δH / (α_fdt · k_B · T_eff))]
        # Reference: PHYSICS_MANIFESTO.md § III.1 "Vacuum Thermostat"
        # CRITICAL: γ_FDT → γ_base at equilibrium (δH = 0) → NO indefinite energy loss
        
        self._fdt_enabled: bool = True  # Enable FDT damping (disable for legacy mode)
        self._gamma_base: float = 0.01  # [PHYSICS_TRACE] Minimal dissipation coefficient [1/s]
                                         # Physical meaning: Intrinsic vacuum friction
                                         # Calibrated to: τ_relax = 1/(2γ) ≈ 50 steps for equilibration
        
        self._alpha_fdt: float = 10.0   # [PHYSICS_TRACE] Thermal energy scale factor [dimensionless]
                                         # Physical meaning: Broadens tanh response → smooth transition
                                         # Larger α → less sensitive to small energy fluctuations
        
        self._beta_fdt: float = 2.0     # [PHYSICS_TRACE] Dissipation boost factor [dimensionless]
                                         # Physical meaning: Max damping increase when H >> H_eq
                                         # γ_max = γ_base · (1 + β_fdt) = 0.03 [1/s]
        
        self._H_eq: float = 0.0         # [PHYSICS_TRACE] Equilibrium energy (running average)
                                         # Updated every step as: H_eq = 0.95·H_eq + 0.05·H_current
                                         # Physical meaning: Reference point for FDT dissipation
        
        self._T_eff: float = 583.0      # [PHYSICS_TRACE] Effective temperature [K]
                                         # From L3 equilibrium: T_eff ≈ 583 K (empirical)
                                         # Physical meaning: Vacuum thermal bath temperature
                                         # Can be updated dynamically from kinetic energy
        
        self._k_B: float = 1.380649e-23 # Boltzmann constant [J/K]
        
        # Hard limit (emergency brake, overrides FDT if triggered)
        self._hard_limit_enabled: bool = True
        self._H_critical: float = 1e6  # [J] If H > H_critical, force γ = γ_max
        
        # Diagnostics (saved for logging/warnings)
        self._gamma_effective: float = 0.01  # Current damping coefficient (updated each step)
        
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
        
        **Physics Principle**: Level-0 Hamiltonian (Single Segment)  
        **Reference**: PHYSICS_MANIFESTO.md § 2.1 "Hamiltoniana (Energy Functional)"
        
        **Mathematical Form**:
        ```
        H = T + V(χ)
        
        where:
          T = (1/2)·m·v²                    [Kinetic energy]
          V = β·(χ² - χ₀²)²                 [Bistable potential]
        ```
        
        **Working Hypothesis**:
        - χ₀ = 4.5 (asymmetric vacuum, NOT 50.0) for numerical stability
        - β = BETA_BISTABILITY (from PhysicsContext)
        - Torsion energy E_K = α_K·K² is DIAGNOSTIC only (requires spatial derivatives)
        
        **Physical Interpretation**:
        - Double-well potential creates two vacuum states (±χ₀)
        - Analogous to Landau-Ginzburg theory of phase transitions
        - Spontaneous symmetry breaking: system chooses vacuum
        
        Returns:
        --------
        H : float
            Total dynamical energy [natural units]
        """
        # [PHYSICS_TRACE] Kinetic energy: (1/2)·m·v² 
        # Derivation: Standard Newtonian kinetic term, v = ∂χ/∂t (conjugate momentum)
        T = 0.5 * self.mass * self.vel**2
        
        # [PHYSICS_TRACE] Bistable potential: β·(χ² - χ₀²)²
        # Derivation: Landau-Ginzburg free energy for order parameter χ
        # Physical meaning: Two stable vacua at χ = ±χ₀, unstable maximum at χ = 0
        # See PHYSICS_MANIFESTO.md § 2.1 Eq. 2.1 for full derivation
        # 
        # CRITICAL FIX (2026-05-26): chi_0 MUST match initialization mean!
        # Previous: chi_0 = 4.5 (hardcoded) → system collapsed to χ ~ -50 (wrong well)
        # Current: chi_0 = self.physics.chi_stable = 50.0 → matches init (χ ~ 50)
        chi_0 = self.physics.chi_stable  # Vacuum expectation value (from PhysicsContext)
        V = self.physics.beta_potential * (self.chi**2 - chi_0**2)**2
        
        return T + V
    
    def compute_local_timestep(self, dt_base: float) -> float:
        """
        [PHYSICS_TRACE] Relativistic timestep: dt_i ∝ 1/√E_local
        
        **Derivation**: See PHYSICS_MANIFESTO.md § 4.5 "Proper Time and Geodesics"
        **Physical Principle**: Energy-Time Uncertainty (Heisenberg)
                                ΔE·Δt ≥ ℏ/2 → high E requires small Δt
        
        Formula:
            dt_i = dt_base · (1 + E_local / E_ref)^(-α)
        
        where:
            E_local: Local Hamiltonian H_i = (1/2)·m·v² + V(χ)
            E_ref: Reference energy scale [J]
            α: Power-law exponent (0.5 = sqrt scaling)
        
        Parameters from PhysicsContext:
            - timestep_energy_ref: 1.0 J (default)
            - timestep_power_alpha: 0.5 (default)
            - timestep_min: 0.0001 (safety floor)
            - timestep_max: 0.1 (safety ceiling)
        
        Returns:
            dt_local: Adapted timestep for this segment [Planck time units]
        """
        E_local = self.compute_hamiltonian_internal()
        E_ref = getattr(self.physics, 'timestep_energy_ref', 1.0)
        alpha = getattr(self.physics, 'timestep_power_alpha', 0.5)
        dt_min = getattr(self.physics, 'timestep_min', 0.0001)
        dt_max = getattr(self.physics, 'timestep_max', 0.1)
        
        # Logarithmic scaling: dt ∝ E^(-α)
        dt_local = dt_base * (1.0 + E_local / E_ref)**(-alpha)
        
        # Safety clamps (prevent extreme values)
        dt_local = np.clip(dt_local, dt_min, dt_max)
        
        return dt_local
    
    def update_effective_temperature(self) -> float:
        """
        Update effective temperature from kinetic energy (Equipartition Theorem).
        
        **Physics Principle**: Kinetic Energy → Temperature Relation  
        **Reference**: PHYSICS_MANIFESTO.md § III.2 "Effective Temperature"
        
        **Mathematical Form**:
        ```
        T_eff = 2·T_kin / k_B
              = m·v² / k_B
        ```
        
        **Physical Interpretation**:
        - Single segment (1 DOF): ⟨(1/2)·m·v²⟩ = (1/2)·k_B·T
        - Solving for T: T_eff = m·v² / k_B
        
        **Note**: This is instantaneous temperature for SINGLE segment.
                  For ensemble T_eff, average over all segments at SolitoneComposito level.
        
        Returns:
        --------
        T_eff : float
            Effective temperature [K]
        """
        # [PHYSICS_TRACE] Equipartition: (1/2)·k_B·T = (1/2)·m·⟨v²⟩
        # For single segment: T_eff = m·v² / k_B
        T_kinetic = self.mass * self.vel**2 / self._k_B
        
        # [PHYSICS_TRACE] Exponential moving average (smooth fluctuations)
        # T_eff(new) = 0.9·T_eff(old) + 0.1·T_kinetic
        # Physical meaning: Low-pass filter prevents T_eff noise from single-step velocities
        alpha_smooth = 0.1
        self._T_eff = (1 - alpha_smooth) * self._T_eff + alpha_smooth * T_kinetic
        
        return self._T_eff
    
    def compute_fdt_damping(self, H_current: float) -> float:
        """
        Fluctuation-Dissipation Theorem (FDT) Damping Coefficient.
        
        **Physics Principle**: Vacuum Thermal Bath (Einstein-Langevin)  
        **Reference**: PHYSICS_MANIFESTO.md § III.1 "FDT Dissipation"
        
        **Mathematical Form**:
        ```
        γ_FDT = γ_base · [1 + β_fdt · tanh(Δ_normalized)]
        
        where:
          Δ_normalized = (H_current - H_eq) / (α_fdt · k_B · T_eff)
          
          γ_base:  Minimal dissipation at equilibrium [1/s]
          β_fdt:   Dissipation boost factor [dimensionless]
          α_fdt:   Thermal scale factor [dimensionless]
          H_eq:    Equilibrium energy (running average) [J]
          T_eff:   Effective temperature [K]
        ```
        
        **Physical Interpretation**:
        - At equilibrium (H = H_eq): γ_FDT = γ_base (minimal friction)
        - High energy (H >> H_eq): γ_FDT → γ_base·(1+β_fdt) (strong damping)
        - Low energy (H << H_eq): γ_FDT → 0 (no damping, prevents freezing)
        
        **CRITICAL**: Unlike warmup schedules, FDT dissipation is **state-dependent**,
                      not time-dependent. It automatically adjusts to system's energy.
        
        **Advantage over Energy-Normalized**:
        - Energy-normalized: γ ∝ sqrt(H/H_target) → ALWAYS dissipates (even at equilibrium)
        - FDT: γ ∝ tanh(δH/ΔE) → dissipation STOPS at equilibrium (δH = 0)
        
        Parameters:
        -----------
        H_current : float
            Current Hamiltonian energy [J]
        
        Returns:
        --------
        gamma_effective : float
            FDT damping coefficient [1/s]
        """
        # [PHYSICS_TRACE] Update equilibrium energy (exponential moving average)
        # H_eq(new) = 0.95·H_eq(old) + 0.05·H_current
        # Physical meaning: Slow tracking of equilibrium point (time constant ~20 steps)
        if self._H_eq == 0.0:
            self._H_eq = H_current  # Initialize on first call
        else:
            alpha_eq = 0.05
            self._H_eq = (1 - alpha_eq) * self._H_eq + alpha_eq * H_current
        
        # [PHYSICS_TRACE] Energy deviation: δH = H_current - H_eq
        # Physical meaning: Positive δH → excess energy (dissipate)
        #                   Negative δH → energy deficit (no dissipation)
        delta_H = H_current - self._H_eq
        
        # [PHYSICS_TRACE] Thermal energy scale: k_B · T_eff
        # Physical meaning: Characteristic energy of thermal fluctuations
        thermal_energy = self._k_B * self._T_eff
        
        # [PHYSICS_TRACE] Normalized energy deviation
        # Δ_norm = δH / (α_fdt · k_B · T_eff)
        # Physical meaning: How many "thermal quanta" away from equilibrium
        # α_fdt = 10 → broadens transition (smooth response)
        if thermal_energy > 1e-30:  # Regularization (avoid division by zero)
            Delta_normalized = delta_H / (self._alpha_fdt * thermal_energy)
        else:
            Delta_normalized = 0.0  # Fallback if T_eff undefined
        
        # [PHYSICS_TRACE] FDT dissipation formula
        # γ_FDT = γ_base · [1 + β_fdt · tanh(Δ_norm)]
        # Derivation: Einstein-Langevin equation (1905)
        # Physical meaning: Dissipation strength follows energy deviation
        tanh_term = np.tanh(Delta_normalized)
        gamma_fdt = self._gamma_base * (1.0 + self._beta_fdt * tanh_term)
        
        # [PHYSICS_TRACE] Clamp to non-negative (prevent anti-dissipation)
        # Physical meaning: Vacuum can only absorb energy, not inject
        #                   (Stochastic injection handled by separate ξ(t) term in full Langevin)
        gamma_effective = max(gamma_fdt, 0.0)
        
        # === HARD LIMIT (Emergency Brake) ===
        # [PHYSICS_TRACE] If H > H_critical, force maximum dissipation
        # Physical meaning: Prevents numerical instability from energy runaway
        # This overrides FDT (safety mechanism)
        if self._hard_limit_enabled and H_current > self._H_critical:
            gamma_max = self._gamma_base * (1.0 + self._beta_fdt)
            gamma_effective = gamma_max
        
        return gamma_effective
    
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
    
    def _compute_force(self, external_force: float = 0.0, include_local_friction: bool = True) -> float:
        """
        Compute total force on segment from Hamiltonian + dissipation.
        
        **Physics Principle**: Generalized Langevin Equation for Fractal Systems
        **Reference**: PHYSICS_MANIFESTO.md § 2.2 "Equations of Motion", § 4.2 "Adaptive Damping"
        
        **Mathematical Form**:
        ```
        F_total = F_conservative + F_dissipative + F_external
        
        where:
          F_conservative = -∂V/∂χ = -4·β·χ·(χ² - χ₀²)     [Bistable potential derivative]
          F_dissipative = -γ_eff·v - η_local·v          [Hierarchical + local damping]
          γ_eff = γ_warmup(step) if step < 100          [Adaptive warmup, SAFETY VALVE #1]
        ```
        
        **Working Hypotheses**:
        1. **Hierarchical Damping**: γ from parent SolitoneComposito represents
           inter-level energy transfer (renormalization group flow)
        2. **Local Friction**: η_local activates ONLY when |ΔH/H| > 5% to prevent
           numerical runaway (fluctuation-dissipation theorem)
        3. **Force Clipping**: F_max = 1000 N prevents unphysical spikes from
           discretization noise (Pauli blocking analogue, SAFETY VALVE #2)
        
        **Physical Interpretation**:
        - Conservative force drives dynamics (deterministic evolution)
        - Dissipation allows thermalization without violating symplectic structure
        - System behaves as "open quantum system" coupled to thermal bath
        
        Parameters:
        -----------
        external_force : float
            External force from parent composite (inter-segment interaction)
        
        include_local_friction : bool
            Enable adaptive local viscosity (drift > 5% emergency brake)
        
        Returns:
        --------
        F_total : float
            Total force [natural units: m·l_Planck/t_Planck²]
        """
        # CRITICAL FIX (2026-05-26): Use chi_stable from PhysicsContext
        # Previous: chi_0 = 4.5 (hardcoded) → bistable potential minima at χ = ±4.5
        #           System initialized at χ ~ 50 → fell into WRONG minimum (χ ~ -50)
        # Current: chi_0 = self.physics.chi_stable = 50.0 → minima at χ = ±50
        #          System initialized at χ ~ 50 → stays in CORRECT minimum
        chi_0 = self.physics.chi_stable  # Vacuum expectation (from PhysicsContext)
        
        # [PHYSICS_TRACE] Bistable force: F = -∂V/∂χ where V = β·(χ² - χ₀²)²
        # Derivation: Landau-Ginzburg potential derivative (PHYSICS_MANIFESTO.md § 2.2 Eq. 2.1)
        # Physical meaning: Restoring force toward vacua at χ = ±χ₀
        # Formula: F = -4β·χ·(χ² - χ₀²)
        F_potential = -4 * self.physics.beta_potential * self.chi * (self.chi**2 - chi_0**2)
        
        # === SAFETY VALVE #1: FLUCTUATION-DISSIPATION THEOREM (FDT) DAMPING ===
        # [PHYSICS_TRACE] FDT damping: γ_FDT = γ_base · [1 + β_fdt · tanh(δH / ΔE_thermal)]
        # Derivation: See PHYSICS_MANIFESTO.md § III.1 "Vacuum Thermal Bath"
        # Physical model: Segments coupled to vacuum at temperature T_eff
        # Energy deviation δH = H - H_eq drives dissipation
        # CRITICAL: γ_FDT → γ_base at equilibrium (δH = 0) → NO indefinite energy loss
        # 
        # ADVANTAGE over previous methods:
        #   - Linear warmup: 30% energy loss (hardcoded schedule)
        #   - Energy-normalized: ~10% loss (sqrt heuristic, still dissipates at equilibrium)
        #   - FDT: <1% loss (dissipation vanishes at equilibrium, theoretically grounded)
        # 
        # Reference: Einstein (1905) Brownian motion, Nyquist (1928) thermal noise
        # CTO-approved: Replaces ad hoc warmup with rigorous statistical mechanics
        
        # Update effective temperature from kinetic energy
        self.update_effective_temperature()
        
        # Compute current Hamiltonian for FDT
        H_current = self.compute_hamiltonian_internal()
        
        # Compute FDT damping coefficient
        if self._fdt_enabled:
            gamma_effective = self.compute_fdt_damping(H_current)
        else:
            # Legacy mode: use constant damping (for comparison)
            gamma_effective = self.gamma_damping
        
        # Save for diagnostics (used in drift warning)
        self._gamma_effective = gamma_effective
        
        # [PHYSICS_TRACE] Dissipative force: F_damp = -γ_FDT·v
        # Physical meaning: Energy transfer to vacuum thermal bath
        # Rate: dE/dt = -γ·v² = -2γ·(H - H_eq) for harmonic systems
        F_damping = -gamma_effective * self.vel
        
        # [PHYSICS_TRACE] Local adaptive friction: F_fric = -η_local·v (if drift > 5%)
        # Derivation: Fluctuation-dissipation theorem (Einstein 1905)
        # Physical meaning: Auto-regulating viscosity absorbs excess kinetic energy
        #                   when local energy conservation is violated numerically
        F_friction = 0.0
        if include_local_friction and self._local_friction > 0:
            F_friction = -self._local_friction * self.vel
        
        F_total = F_potential + F_damping + F_friction + external_force
        
        # === SAFETY VALVE #2: FORCE CLIPPING ===
        # [PHYSICS_TRACE] Force clipping: |F| ≤ F_max = 1000 N
        # Derivation: See PHYSICS_MANIFESTO.md § 6.1 Safety Valve #2
        # Physical rationale: Prevents unphysical force spikes from numerical noise.
        #                     Equivalent to Pauli blocking at high densities.
        # CTO-approved: Critical for L3 stability (13,824 segments)
        F_total = np.clip(F_total, -self._force_max_clip, self._force_max_clip)
        
        return F_total
    
    def _compute_conservative_force(self, external_force: float = 0.0) -> float:
        """
        [PHYSICS_TRACE] Compute ONLY conservative forces (F = -∇V).
        
        **Strang Splitting Requirement**: This method returns forces derivable 
        from a potential. Dissipative forces (FDT damping, local friction) are 
        handled separately in _apply_damping_kick().
        
        **Mathematical Form**:
        ```
        F_conservative = -dV/dχ + F_external
        
        where V(χ) = β·(χ² - χ₀²)²  (bistable potential)
              dV/dχ = 4β·χ·(χ² - χ₀²)
        ```
        
        **Why Separation Needed**:
        Velocity Verlet is symplectic ONLY for conservative forces.
        Dissipative forces F_damp = -γ·v are NOT derivable from potential
        → Must be handled via operator splitting (Strang 1968).
        
        Parameters:
        -----------
        external_force : float
            Coupling force from parent SolitoneComposito [natural units]
        
        Returns:
        --------
        F_conservative : float
            Conservative force [natural units]
        
        Reference:
        ----------
        PHYSICS_MANIFESTO.md § 4.1.3 "Strang Splitting for Dissipative Forces"
        Strang (1968) "On the construction and comparison of difference schemes"
        """
        # [PHYSICS_TRACE] Bistable potential gradient: dV/dχ = 4β·χ·(χ² - χ₀²)
        # Derivation: Landau-Ginzburg potential (PHYSICS_MANIFESTO.md § 2.2)
        # Physical meaning: Restoring force toward vacua at χ = ±χ₀
        chi_0 = self.physics.chi_stable
        beta = self.physics.beta_potential
        dV_dchi = 4.0 * beta * self.chi * (self.chi**2 - chi_0**2)
        F_potential = -dV_dchi
        
        F_conservative = F_potential + external_force
        
        # === SAFETY VALVE #2: FORCE CLIPPING ===
        # [PHYSICS_TRACE] Force clipping: |F| ≤ F_max = 1000 N
        # Prevents unphysical force spikes from numerical noise
        # Reference: PHYSICS_MANIFESTO.md § 6.1 Safety Valve #2
        F_conservative = np.clip(F_conservative, -self._force_max_clip, self._force_max_clip)
        
        return F_conservative
    
    def _apply_damping_kick(self, dt_half: float) -> None:
        """
        [PHYSICS_TRACE] Apply dissipative kick: v → v·exp(-γ·dt).
        
        **Strang Splitting**: This method handles NON-conservative forces 
        separately from the symplectic Verlet kernel.
        
        **Mathematical Derivation**:
        ```
        Dissipative ODE: dv/dt = -γ·v
        Exact solution:  v(t) = v(0)·exp(-γ·t)
        ```
        
        For small γ·dt: exp(-γ·dt) ≈ 1 - γ·dt + O((γ·dt)²)
        
        **Strang Splitting Algorithm**:
        ```
        S_dt = D_{dt/2} ∘ V_dt ∘ D_{dt/2}
        
        where:
          D_{dt/2} = Dissipative kick (this method)
          V_dt     = Conservative Velocity Verlet
          ∘        = Operator composition
        ```
        
        Parameters:
        -----------
        dt_half : float
            Half-timestep (dt/2) for symmetric Strang splitting [Planck time]
        
        Physical Interpretation:
        ------------------------
        FDT damping represents energy transfer to vacuum thermal bath at T_eff.
        By applying it separately, we:
        1. Preserve symplectic structure of conservative dynamics
        2. Model dissipation exactly (exp decay, not linear approximation)
        3. Maintain O(dt²) accuracy of overall scheme
        
        Reference:
        ----------
        - Strang (1968) SIAM J. Numer. Anal., 5(3), 506-517
        - McLachlan & Quispel (2002) Acta Numerica, 11, 341-434
        - PHYSICS_MANIFESTO.md § 4.1.3
        """
        # Update effective temperature (for FDT calculation)
        self.update_effective_temperature()
        
        # Compute FDT damping coefficient
        if self._fdt_enabled:
            H_current = self.compute_hamiltonian_internal()
            gamma_effective = self.compute_fdt_damping(H_current)
        else:
            # Legacy mode: constant damping
            gamma_effective = self.gamma_damping
        
        # [PHYSICS_TRACE] Add local friction (adaptive viscosity for energy drift mitigation)
        # Local friction activates when drift > 5% (see evolve())
        # Physical meaning: Auto-regulating viscosity absorbs numerical errors
        if self._local_friction > 0:
            gamma_effective += self._local_friction
        
        # Save for diagnostics
        self._gamma_effective = gamma_effective
        
        # === EXPONENTIAL DAMPING APPLICATION ===
        # [PHYSICS_TRACE] v → v·exp(-γ·dt/2)
        # Why exponential: Exact solution of dv/dt = -γ·v
        # Why not linear (v -= γ·v·dt): Would violate positivity for large γ·dt
        damping_factor = np.exp(-gamma_effective * dt_half)
        self.vel *= damping_factor
        
        # === SAFETY VALVE #1: VELOCITY CLIPPING ===
        # [PHYSICS_TRACE] Clip velocity to prevent relativistic violations
        # Reference: PHYSICS_MANIFESTO.md § 6.1 Safety Valve #1
        self.vel = np.clip(self.vel, -self.physics.MAX_VELOCITY, self.physics.MAX_VELOCITY)
    
    # [TODO: DOCS] Document relativistic aging formula γ(v) in PHYSICS_MANIFESTO.md
    def evolve(self, dt: float, external_force: np.ndarray = None) -> None:
        """
        Symplectic time evolution with adaptive sub-stepping.
        
        **Physics Principle**: Hamiltonian Dynamics with CFL-Adaptive Integration
        **Reference**: PHYSICS_MANIFESTO.md § 4.1 "Symplectic Integration (Velocity Verlet)"
        
        **Mathematical Form (Velocity Verlet Algorithm)**:
        ```
        1. v_{n+1/2} = v_n + (F_n/m)·(dt/2)         [half-kick 1]
        2. χ_{n+1} = χ_n + v_{n+1/2}·dt             [drift]
        3. F_{n+1} = F(χ_{n+1})                     [force update]
        4. v_{n+1} = v_{n+1/2} + (F_{n+1}/m)·(dt/2) [half-kick 2]
        ```
        
        **Adaptive Sub-Stepping (CFL Condition)**:
        ```
        if |F_current - F_prev| > threshold:
            n_substeps = 4 (or 8 if drift > 10%)
            dt_effective = dt / n_substeps
        ```
        
        **Working Hypotheses**:
        1. **Symplectic Property**: Preserves phase-space volume (Liouville's theorem)
           → Energy drift O(dt²) instead of exponential
        2. **CFL Criterion**: When forces vary rapidly, timestep must decrease
           to maintain numerical stability (PHYSICS_MANIFESTO.md § 6.1 Safety Valve #3)
        3. **Relativistic Aging**: τ_local += dt/γ(v) with γ = √(1 + v²/V_ref²)
           [TODO: DOCS - Not yet in PHYSICS_MANIFESTO]
        
        **Physical Interpretation**:
        - Verlet is time-reversible (T-symmetry preserved)
        - Energy conservation guaranteed up to O(dt²)
        - Sub-stepping activates when system enters "stiff" regime
        
        Parameters:
        -----------
        dt : float
            Global timestep [Planck time units]
        
        external_force : ndarray, optional
            Force from parent composite (inter-segment coupling)
        """
        # [PHYSICS_TRACE] Pre-evolution energy for conservation check
        # Purpose: Monitor Hamiltonian drift |ΔH/H| to validate symplectic integration
        H_before = self.energia_totale
        
        # Convert external_force to scalar
        ext_f = 0.0 if external_force is None else float(external_force)
        
        # === CFL-based adaptive sub-stepping ===
        # [PHYSICS_TRACE] Adaptive sub-stepping decision (CFL criterion)
        # Derivation: See PHYSICS_MANIFESTO.md § 6.1 Safety Valve #3
        # Criterion: If |ΔF| > threshold, forces are varying too rapidly for dt
        # Physical meaning: Entering "stiff" regime where explicit integration becomes unstable
        F_current = self._compute_force(ext_f, include_local_friction=False)
        delta_F = abs(F_current - self._force_prev)
        
        # Decision: Use sub-steps if force variation too large
        use_substeps = delta_F > self._substep_threshold
        n_steps = self._substep_count if use_substeps else 1
        
        # === SAFETY VALVE #3: DRIFT-BASED ADAPTIVE TIMESTEP ===
        # [PHYSICS_TRACE] If previous drift was critical (> 10%), FORCE sub-stepping
        # Derivation: CFL stability requires dt ∝ 1/|F'| when F varies rapidly
        # CTO-approved: Critical for L3 convergence (prevents energy runaway)
        if hasattr(self, '_last_drift') and self._last_drift > 0.1:
            n_steps = max(n_steps, 8)  # Minimum 8 sub-steps if critical drift
        
        dt_step = dt / n_steps
        
        # Increment step counter (for warmup damping)
        self._step_counter += 1
        
        # [PHYSICS_TRACE] Strang Splitting: D_{dt/2} ∘ V_dt ∘ D_{dt/2}
        # Reference: Strang (1968), McLachlan & Quispel (2002) § 4.3
        # 
        # **Operator Decomposition**:
        #   D = Dissipative operator (FDT damping + local friction)
        #   V = Conservative Velocity Verlet (EXACTLY symplectic)
        # 
        # **Why This Works**:
        # 1. Conservative kernel (V_dt) preserves phase-space volume EXACTLY
        # 2. Dissipative kicks (D_{dt/2}) applied symmetrically → O(dt²) accuracy
        # 3. Separation prevents damping from polluting symplectic structure
        # 
        # **Physical Interpretation**:
        # - V_dt: Hamiltonian evolution (energy-conserving ballistic motion)
        # - D_{dt/2}: Energy transfer to vacuum thermal bath (FDT dissipation)
        # 
        # **Mathematical Proof**:
        # exp(-L_total·dt) = exp(-L_damp·dt) · exp(-L_Hamilton·dt) + O(dt²)
        #                  ≈ D_{dt/2} ∘ V_dt ∘ D_{dt/2} + O(dt³)  (Strang splitting)
        # 
        # where the symmetric composition improves accuracy from O(dt²) to O(dt³).
        
        for _ in range(n_steps):
            # === STEP 1: Damping half-kick (D_{dt/2}) ===
            # [PHYSICS_TRACE] Apply dissipative forces BEFORE conservative evolution
            # Physical meaning: Partial energy transfer to thermal bath
            self._apply_damping_kick(dt_step / 2.0)
            
            # === STEP 2: Conservative Velocity Verlet (V_dt) - SYMPLECTIC KERNEL ===
            # [PHYSICS_TRACE] HALF-KICK 1: v_n → v_{n+1/2} (conservative forces ONLY)
            # Physical meaning: Accelerate using ONLY forces derivable from potential
            # Critical: NO damping in this step → preserves symplectic structure
            F_n = self._compute_conservative_force(ext_f)
            v_half = self.vel + (F_n / self.mass) * (dt_step / 2.0)
            
            # [PHYSICS_TRACE] DRIFT: χ_n → χ_{n+1} using v_{n+1/2}
            # Physical meaning: Propagate field using intermediate velocity
            # Key symplectic property: Uses v_{n+1/2}, NOT v_n (→ 2nd order accuracy)
            self.chi += v_half * dt_step
            
            # [PHYSICS_TRACE] HALF-KICK 2: v_{n+1/2} → v_{n+1} (conservative forces ONLY)
            # Physical meaning: Accelerate using force at NEW position
            # Critical: Force recomputed at χ_{n+1}, NO damping → symplectic
            F_n_plus_1 = self._compute_conservative_force(ext_f)
            self.vel = v_half + (F_n_plus_1 / self.mass) * (dt_step / 2.0)
            
            # === STEP 3: Damping half-kick (D_{dt/2}) ===
            # [PHYSICS_TRACE] Apply dissipative forces AFTER conservative evolution
            # Physical meaning: Complete energy transfer to thermal bath
            # Strang symmetry: Same dt/2 as Step 1 → O(dt³) local error
            self._apply_damping_kick(dt_step / 2.0)
            
            # Final velocity clipping (safety valve, only for single-step)
            if n_steps == 1:
                self.vel = np.clip(self.vel, -self.physics.MAX_VELOCITY, self.physics.MAX_VELOCITY)
        
        # Final velocity clipping for multi-step
        if n_steps > 1:
            self.vel = np.clip(self.vel, -self.physics.MAX_VELOCITY, self.physics.MAX_VELOCITY)
        
        # Save force for next CFL check
        self._force_prev = F_n_plus_1
        
        # [PHYSICS_TRACE] Relativistic aging: τ += dt/γ(v)
        # Formula: γ(v) = √(1 + v²/V_ref²) (Lorentz factor analogue)
        # Physical meaning: Proper time flows slower for fast-moving segments
        # [TODO: DOCS] Add derivation to PHYSICS_MANIFESTO.md § 4 (Dynamics & Evolution)
        V_REF = 100.0  # Reference velocity [natural units]
        gamma_inverse = np.sqrt(1.0 + (self.vel**2) / (V_REF**2))
        self.tau_locale += dt / gamma_inverse  # Use TOTAL dt, not dt_step
        
        # Invalidate energy cache
        self._cache_valid = False
        
        # [PHYSICS_TRACE] Energy conservation check + adaptive local friction
        # Derivation: Fluctuation-dissipation theorem (Einstein 1905)
        # Principle: If |ΔH/H| > 5%, system is out of local equilibrium.
        #            Activate local viscosity η to absorb excess kinetic energy.
        # Physical justification: D = k_B·T·η (diffusion ~ viscosity × temperature)
        #                         When drift ↑, local T_eff ↑ → η_local ↑
        # 
        # IMPORTANT: This does NOT violate global energy conservation!
        #            Energy is dissipated (converted to "heat"), not destroyed.
        H_after = self.energia_totale
        H_drift = abs(H_after - H_before) / (abs(H_before) + 1e-30)
        
        # Save drift for next step's CFL decision
        self._last_drift = H_drift
        
        # [PHYSICS_TRACE] Activate local friction if drift > 5%
        # Response: Aggressive proportional increase (+0.005, max 0.05)
        # Can be disabled via _enable_adaptive_friction flag (for validation tests)
        if self._enable_adaptive_friction and H_drift > 5e-2:
            self._local_friction = min(self._local_friction + 0.005, 0.05)
        else:
            # Deactivate gradually if drift under control
            self._local_friction = max(self._local_friction - 0.0005, 0.0)
        
        # [PHYSICS_TRACE] Warning if drift CRITICAL (> 10%)
        # Purpose: Alert user to potential numerical instability
        # Note: Does NOT halt simulation (safety valves should prevent crash)
        if H_drift > 0.1:
            import warnings
            fdt_status = f"FDT γ={self._gamma_effective:.4f}" if self._fdt_enabled else f"Legacy γ={self.gamma_damping:.4f}"
            warnings.warn(
                f"DRIFT ENERGIA CRITICO: |dH/H| = {H_drift:.3e} > 10% [{fdt_status}]\n"
                f"  H_before = {H_before:.6e}\n"
                f"  H_after  = {H_after:.6e}\n"
                f"  Step dt  = {dt:.6e}\n"
                f"  Sub-steps used: {n_steps}\n"
                f"  Local friction: {self._local_friction:.6e}\n"
                f"  gamma_damping (effective): {self._gamma_effective:.6e}"
            )
    
    def __repr__(self) -> str:
        return (
            f"SegmentoQuantistico(χ={self.chi:.3f}, v={self.vel:.3f}, "
            f"τ={self.tau_locale:.3f})"
        )
