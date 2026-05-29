"""
================================================================================
PHYSICS CONTEXT - Dependency Injection per Parametri Scala-Dipendenti
================================================================================

Ogni livello gerarchico opera con costanti fisiche scale-dependent.
La dipendenza esplicita permette testing di leggi fisiche variabili.

SCALING LAW:
    α_K^(n+1) = α_K^(n) · (L_n+1 / L_n)^2
    σ_χ^(n+1) = σ_χ^(n) · sqrt(24)
    
ESEMPI:
    - Livello 0 (Planck): L ~ 10^-35 m, α_K ~ 1.0
    - Livello 1 (Nucleare): L ~ 10^-15 m, α_K ~ 24^2 = 576
    - Livello 2 (Atomico): L ~ 10^-10 m, α_K ~ 24^4 = 331776
================================================================================
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PhysicsContext:
    """
    Contesto fisico immutabile per un dato livello gerarchico.
    
    PARAMETRI SCALE-DEPENDENT:
    --------------------------
    level: int
        Livello gerarchico (0=segmenti, 1=solitone base, 2=macro, ...)
    
    length_scale: float
        Scala di lunghezza caratteristica [m]
        L_n+1 = L_n · sqrt(24) (scaling frattale)
    
    alpha_K: float
        Costante accoppiamento torsione
        α_K^(n+1) = α_K^(n) · 24^d_f
    
    beta_potential: float
        Profondità potenziale doppio pozzo
        
    sigma_chi, sigma_velocity, sigma_torsion, sigma_tau: float
        Parametri screening multi-scala
    
    mu_fermi: float
        Potenziale chimico per Fermi-Dirac (threshold transizione)
    
    T_fermi: float
        Temperatura efficace (larghezza transizione Fermi-Dirac)
    
    gamma_cooling: float
        Tasso raffreddamento temperatura efficace
    
    fermi_epsilon: float
        Regolarizzazione numerica per evitare singolarità
        
    E_fusion_threshold: float
        Soglia energia per fusione → livello superiore
        
    lambda_coherence: float
        Raggio coerenza spaziale per fusione
        
    eps_topology: float
        Tolleranza chiusura topologica ∮τds = 4π
    """
    
    # Identificatori
    level: int
    length_scale: float
    
    # Costanti dinamiche
    alpha_K: float = 1.0  # Accoppiamento torsione
    beta_potential: float = 0.001  # Doppio pozzo
    chi_stable: float = 50.0  # Vacuum expectation value (VEV) for chi field [CRITICAL: Must match initialization!]
    kappa_coupling: float = 0.25  # Accoppiamento inter-segmenti
    lambda_exchange: float = 0.05  # Interazione di scambio topologico (same-phase attraction)
    
    # Screening multi-scala
    sigma_chi: float = 3.0
    sigma_velocity: float = 2.0
    sigma_torsion: float = 2.0 * np.pi
    sigma_tau: float = 5.0
    
    # FERMI-DIRAC SCREENING (Nuovo: soft-constraints continui)
    mu_fermi: float = 50.0  # Potenziale chimico (threshold transizione) [unità di χ o ρ]
    T_fermi: float = 5.0  # Temperatura efficace (larghezza transizione) [unità di χ o ρ]
    gamma_cooling: float = 0.01  # Tasso raffreddamento temperatura [1/s]
    fermi_epsilon: float = 1e-9  # Regolarizzazione anti-singolarità

    # ZERO-POINT MOTOR (modo di Nyquist lambda=2 l_P, anti-congelamento intrinseco)
    # Ampiezza di velocita' staggered per-segmento del punto-zero geometrico.
    # DEFAULT-ON a 0.05: il modo (-1)^i non puo' mai congelarsi -> "vuoto vivo"
    # come fatto STRUTTURALE (non termico). Soglia validata: minima per stato VIVO
    # robusto con perturbazione del vuoto trascurabile (chi_sat +0.001).
    # RIPRODUCIBILITA': per replicare i dati storici Ramo A (run pre-2026-05-29)
    # impostare esplicitamente zero_point_amplitude=0.0.
    zero_point_amplitude: float = 0.05
    
    # === RELATIVISTIC TIMESTEP PARAMETERS (CP-2026-05-26-003) ===
    # [PHYSICS_TRACE] Energy-dependent timestep scaling
    # Reference: PHYSICS_MANIFESTO.md § 4.5 "Proper Time and Geodesics"
    timestep_energy_ref: float = 1.0       # [J] Reference energy scale
    timestep_power_alpha: float = 0.5      # Power-law exponent (0.5 = sqrt)
    timestep_min: float = 0.0001           # [Planck time] Safety floor
    timestep_max: float = 0.1              # [Planck time] Safety ceiling
    
    # Vincoli fusione
    E_fusion_threshold: float = 1e8  # [J] Soglia energia
    lambda_coherence: float = 1e-10  # [m] Raggio coerenza
    eps_topology: float = 1e-6  # Tolleranza 4π
    
    # FUSIONE E RADIAZIONE (Termodinamica Solitoni)
    eta_radiation_base: float = 0.02  # Efficienza radiativa base (2%)
    tau_coherence: float = 10.0  # Scala temporale coerenza fusione
    epsilon_local_absorption: float = 0.30  # Frazione radiazione → espansione metrica (30%)
    # Frazione restante (70%) → onde torsionali libere
    
    # DISSIPAZIONE FRATTALE UNIVERSALE (Legge di Scala)
    gamma_damping_base: float = 0.0005  # γ_0: Coefficiente base (livello 0) - RIDOTTO per stabilità L3
    damping_scaling_exponent: float = 0.2  # k: Esponente legge di scala γ_n = γ_0·(24^n)^k (scaling molto conservativo)
    thermal_feedback_strength: float = 0.05  # Modulazione termica del damping (ridotta a 5%)
    # gamma_effective viene calcolato dinamicamente: γ_eff = γ(level) · f(T_eff) · g(Var(tau))
    
    # RG FLOW COSTANTI DI ACCOPPIAMENTO (Topological Screening)
    alpha_K_rg_exponent: float = 1.0  # k_α: Screening α_K ~ 1/(24^n)^k_α (densità energetica costante)
    kappa_rg_exponent: float = 0.5  # k_κ: Screening κ ~ 1/(24^n)^k_κ (coupling weakening)
    
    # Vincoli fisici
    MAX_VELOCITY: float = 10000.0  # [m/s] Velocità massima
    E_PLANCK_THRESHOLD: float = 10000.0  # Soglia quantizzazione (aumentata da 1000)
    HUBBLE_DAMPING: float = 0.999  # Dissipazione Hubble
    
    # Parametri simulazione
    dt: float = 0.1  # [s] Timestep integratore
    
    @classmethod
    def for_level(cls, level: int, base_context: Optional['PhysicsContext'] = None) -> 'PhysicsContext':
        """
        Factory method: crea contesto per livello gerarchico.
        
        SCALING FRATTALE:
            L_n+1 = L_n · sqrt(24)
            α_K^(n+1) = α_K^(n) · 24^2  (dimensione frattale d_f=2)
            σ_χ^(n+1) = σ_χ^(n) · sqrt(24)
        
        Args:
            level: Livello gerarchico target
            base_context: Contesto livello 0 (default: Planck scale)
        
        Returns:
            PhysicsContext con parametri scalati
        """
        if base_context is None:
            # Contesto base: scala di Planck
            base_context = cls(
                level=0,
                length_scale=1.616255e-35,  # Lunghezza di Planck [m]
                alpha_K=1.0,
                beta_potential=0.001,
                kappa_coupling=0.25,
                lambda_exchange=0.05,
                sigma_chi=3.0,
                sigma_velocity=2.0,
                sigma_torsion=2.0 * np.pi,
                sigma_tau=5.0,
                mu_fermi=50.0,  # Potenziale chimico base
                T_fermi=5.0,  # Temperatura efficace base
                gamma_cooling=0.01,  # Tasso raffreddamento
                fermi_epsilon=1e-9,  # Regolarizzazione
                E_fusion_threshold=1e8,
                lambda_coherence=1e-35,
                eps_topology=1e-6
            )
        
        if level == 0:
            return base_context
        
        # Scaling esponenziale
        scale_factor = np.sqrt(24) ** level
        energy_scale = 24 ** (2 * level)  # d_f = 2 (LEGACY, usato solo per lambda)
        
        # =========================================================================
        # [LEGGE FISICA: Renormalization Group Flow - Topological Screening]
        # Principio: La densità di informazione geometrica (torsione K) diminuisce
        #            con il volume frattale per evitare singolarità topologiche.
        # 
        # Derivazione: Dalla misura empirica K_L2/K_L1 = 0.185 ~ (24^(-0.53)),
        #              deduciamo K_n ~ K_0/(24^n)^β con β≈0.5.
        #              Per densità energetica ρ = (α_K·K²)/V_fractal = const,
        #              con V ~ 24^n, otteniamo α_K ~ 1/(24^n).
        # 
        # Analogia: QCD asymptotic freedom - coupling diminuisce ad alte scale.
        # 
        # Validazione: TODO_VALIDATION → RG_FLOW_ANALYSIS (RG_FLOW_TOPOLOGICAL_SCREENING.md)
        # =========================================================================
        alpha_K_screening = 1.0 / (24 ** level) ** base_context.alpha_K_rg_exponent
        kappa_screening = 1.0 / (24 ** level) ** base_context.kappa_rg_exponent
        
        # LAMBDA mantiene scaling old per backward compatibility
        lambda_scaled = base_context.lambda_exchange * energy_scale
        
        return cls(
            level=level,
            length_scale=base_context.length_scale * scale_factor,
            alpha_K=base_context.alpha_K * alpha_K_screening,  # RG FLOW: screening!
            beta_potential=base_context.beta_potential,
            kappa_coupling=base_context.kappa_coupling * kappa_screening,  # RG FLOW
            lambda_exchange=lambda_scaled,
            sigma_chi=base_context.sigma_chi * scale_factor,
            sigma_velocity=base_context.sigma_velocity,
            sigma_torsion=base_context.sigma_torsion * scale_factor,
            sigma_tau=base_context.sigma_tau,
            mu_fermi=base_context.mu_fermi * scale_factor,  # Scala come sigma_chi
            T_fermi=base_context.T_fermi * scale_factor,  # Scala come sigma_chi
            gamma_cooling=base_context.gamma_cooling,  # Invariante (tasso temporale)
            fermi_epsilon=base_context.fermi_epsilon,  # Invariante (numerica)
            zero_point_amplitude=base_context.zero_point_amplitude,  # Invariante (zero-point intrinseco)
            # SCALING GAMMA DAMPING FRATTALE: γ_n = γ_0 · (24^n)^k
            gamma_damping_base=base_context.gamma_damping_base * (24 ** level) ** base_context.damping_scaling_exponent,
            damping_scaling_exponent=base_context.damping_scaling_exponent,  # Invariante
            thermal_feedback_strength=base_context.thermal_feedback_strength,  # Invariante
            E_fusion_threshold=base_context.E_fusion_threshold * energy_scale,
            lambda_coherence=base_context.lambda_coherence * scale_factor,
            eps_topology=base_context.eps_topology,
            MAX_VELOCITY=base_context.MAX_VELOCITY,
            E_PLANCK_THRESHOLD=base_context.E_PLANCK_THRESHOLD * energy_scale,
            HUBBLE_DAMPING=base_context.HUBBLE_DAMPING,
            dt=base_context.dt
        )
    
    def compute_screening_attenuation(
        self,
        delta_chi: float,
        delta_vel: float,
        delta_K2: float,
        delta_tau: float
    ) -> float:
        """
        Calcola fattore di attenuazione multi-scala.
        
        A(Δχ, Δv, ΔK², Δτ) = exp(-|Δχ|/σχ) · exp(-|Δv|/σv) 
                               · exp(-|ΔK²|/σK) · exp(-|Δτ|/στ)
        
        Args:
            delta_chi: Differenza campo χ
            delta_vel: Differenza velocità
            delta_K2: Differenza curvatura K²
            delta_tau: Differenza tempo locale τ
        
        Returns:
            Fattore di attenuazione ∈ [0, 1]
        """
        A_chi = np.exp(-abs(delta_chi) / self.sigma_chi)
        A_vel = np.exp(-abs(delta_vel) / self.sigma_velocity)
        A_K2 = np.exp(-abs(delta_K2) / self.sigma_torsion)
        A_tau = np.exp(-abs(delta_tau) / self.sigma_tau)
        
        return A_chi * A_vel * A_K2 * A_tau
    
    # =========================================================================
    # [LEGGE FISICA: Efficienza Radiativa per Disomogeneità Temporale]
    # Principio: Sistemi con tempi propri disomogenei radiano energia per
    #            tendere verso sincronizzazione termodinamica (2° principio).
    # 
    # Derivazione: Dalla teoria dei sistemi fuori equilibrio, il rate di
    #              produzione di entropia σ = ∂S/∂t ~ Var(τ)/τ²_coh.
    #              L'efficienza radiativa η segue la disuguaglianza di Clausius.
    # 
    # Validazione: TODO_VALIDATION → test_energy_transfer (test_universal_scaling.py)
    # =========================================================================
    def compute_radiation_efficiency(self, tau_variance: float) -> float:
        """
        Calcola efficienza radiativa basata su disomogeneità temporale.
        
        η_eff = η_base * (1 + Var(τ)/τ_coherence²)
        
        Limitata a [1%, 5%] per stabilità fisica.
        
        Args:
            tau_variance: Varianza dei tempi locali τ nel cluster
        
        Returns:
            Efficienza ∈ [0.01, 0.05]
        """
        eta_eff = self.eta_radiation_base * (1 + tau_variance / self.tau_coherence**2)
        return np.clip(eta_eff, 0.01, 0.05)
    
    # =========================================================================
    # [LEGGE FISICA: Legge di Smorzamento Dinamico Universale]
    # Principio: L'energia dissipata scala con la complessità frattale del sistema,
    #            modulata dalla temperatura termodinamica e dall'entropia temporale.
    # 
    # Derivazione: Dalla teoria dei sistemi dissipativi frattali (Prigogine 1977),
    #              la viscosità efficace scala come η_eff ~ L^(d_f-2) · T · S(τ).
    #              Con d_f=2 (dimensione frattale), otteniamo γ ~ (24^n)^k · T · Var(τ).
    # 
    # Validazione: TODO_VALIDATION → test_thermal_modulation (test_universal_scaling.py)
    # =========================================================================
    def get_adaptive_damping(
        self, 
        T_eff: float, 
        tau_variance: float,
        level: Optional[int] = None
    ) -> float:
        """
        Calcola coefficiente di smorzamento adattivo universale.
        
        MODELLO TERMODINAMICO FRATTALE:
        --------------------------------
        γ_adaptive = γ_base(level) · f_thermal(T_eff) · g_disomogeneity(Var(τ))
        
        dove:
        - γ_base(n) = γ_0 · (24^n)^k  (legge di scala frattale)
        - f_thermal = 1 + β·(T_eff/T_ref - 1)  (feedback termodinamico)
        - g_disomogeneity = 1 + Var(τ)/τ_coherence²  (disomogeneità temporale)
        
        FISICA:
        - Quando T_eff ↑ (sistema 'caldo'), damping ↑ per smorzare fluttuazioni
        - Quando T_eff ↓ (sistema 'freddo'), damping ↓ per preservare coerenza
        - Quando Var(τ) ↑ (disomogeneo), damping ↑ per radiare energia excess
        
        Args:
            T_eff: Temperatura efficace del sistema [K o unità χ]
            tau_variance: Varianza dei tempi locali τ
            level: Livello gerarchico (opzionale, default: self.level)
        
        Returns:
            γ_adaptive [1/s]: Coefficiente smorzamento adattivo
        """
        if level is None:
            level = self.level
        
        # 1. SCALA BASE FRATTALE: γ_base(n) = γ_0 · (24^n)^k
        gamma_base = self.gamma_damping_base * (24 ** level) ** self.damping_scaling_exponent
        
        # 2. MODULAZIONE TERMICA: f(T_eff) = 1 + β·(T_eff/T_ref - 1)
        # T_ref = T_fermi del livello (temperatura caratteristica)
        T_ref = self.T_fermi if self.T_fermi > 0 else 1.0
        thermal_ratio = T_eff / T_ref
        f_thermal = 1.0 + self.thermal_feedback_strength * (thermal_ratio - 1.0)
        # Clamp per stabilità: [0.5, 2.0]
        f_thermal = np.clip(f_thermal, 0.5, 2.0)
        
        # 3. MODULAZIONE DISOMOGENEITÀ: g(Var(τ)) = 1 + Var(τ)/τ_coherence²
        g_disomogeneity = 1.0 + tau_variance / (self.tau_coherence ** 2)
        # Clamp per stabilità: [1.0, 3.0]
        g_disomogeneity = np.clip(g_disomogeneity, 1.0, 3.0)
        
        # 4. COMBINAZIONE
        gamma_adaptive = gamma_base * f_thermal * g_disomogeneity
        
        return gamma_adaptive
    
    def compute_quantization_factor(self, K_squared: float) -> float:
        """
        Calcola fattore di quantizzazione per torsione.
        
        Quando K² supera soglia di Planck, transizione a regime discreto.
        
        q(K²) = 1 / (1 + K²/E_Planck)  (saturazione)
        
        Args:
            K_squared: Torsione geometrica
        
        Returns:
            Fattore ∈ (0, 1]
        """
        return 1.0 / (1.0 + K_squared / self.E_PLANCK_THRESHOLD)
    
    def __str__(self) -> str:
        return (
            f"PhysicsContext(level={self.level}, "
            f"L={self.length_scale:.3e}m, "
            f"α_K={self.alpha_K:.3e}, "
            f"E_fus={self.E_fusion_threshold:.3e}J)"
        )
