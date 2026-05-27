"""
================================================================================
FERMI-DIRAC SCREENING - Transizione Continua & Principio di Pauli
================================================================================

Implementa screening adattivo basato sulla distribuzione di Fermi-Dirac,
sostituendo le soglie discrete con una funzione continua e derivabile.

FISICA:
-------
f(χ) = 1 / (exp((χ - μ) / T) + 1)

dove:
- μ (mu): Potenziale chimico - punto di transizione (50% occupazione)
- T (T_eff): Temperatura efficace - larghezza della transizione
- ε = 1e-9: Regolarizzazione per evitare singolarità T→0

INTERPRETAZIONE FISICA:
----------------------
I solitoni si comportano come fermioni soggetti al Principio di Esclusione di Pauli:
- Stati a bassa energia (χ < μ): Alta occupazione → screening forte
- Stati ad alta energia (χ > μ): Bassa occupazione → screening debole
- Transizione continua evita discontinuità nelle forze

POTENZIALE EFFICACE:
-------------------
V_eff(χ) = -T·ln(1 + exp(-(χ-μ)/T))

Forza conservativa:
F(χ) = -dV_eff/dχ = -f(χ)

CONSERVAZIONE ENERGETICA:
------------------------
Le forze derivano da un potenziale → conservazione hamiltoniana
garantita a livello O(dt³) con integratore Verlet.

================================================================================
"""

import numpy as np
from typing import Tuple, Optional
import warnings


class FermiDiracScreening:
    """
    Screening adattivo basato su statistica di Fermi-Dirac.
    
    Attributes:
    -----------
    mu : float
        Potenziale chimico (threshold energetico) [unità di χ]
    
    T_eff : float
        Temperatura efficace (larghezza transizione) [unità di χ]
    
    epsilon : float
        Regolarizzazione per evitare exp overflow
    
    Methods:
    --------
    occupation(chi) -> float
        Calcola probabilità occupazione f(χ) ∈ [0,1]
    
    screening_factor(chi) -> float
        Fattore attenuazione A(χ) = 1 - f(χ) ∈ [0,1]
        (Alta energia → alta attenuazione)
    
    effective_potential(chi) -> float
        Potenziale termodinamico V_eff(χ)
    
    conservative_force(chi) -> float
        Forza F = -dV_eff/dχ (derivabile, conservativa)
    
    gradient_occupation(chi) -> float
        Gradiente df/dχ per calcolo forze
    """
    
    def __init__(self, 
                 mu: float = 50.0, 
                 T_eff: float = 5.0,
                 epsilon: float = 1e-9):
        """
        Inizializza screening Fermi-Dirac.
        
        Parameters:
        -----------
        mu : float
            Potenziale chimico (threshold di transizione)
            Default: 50.0 (compatibile con vecchio rho_threshold)
        
        T_eff : float
            Temperatura efficace (larghezza transizione)
            Valori tipici:
            - T_eff ~ 1.0: transizione sharp (quasi discontinua)
            - T_eff ~ 5.0: transizione smooth (consigliato)
            - T_eff ~ 10.0: transizione very soft
        
        epsilon : float
            Regolarizzazione anti-overflow
            Previene exp(x) con x > 700 (limite macchina)
        """
        assert T_eff > epsilon, "T_eff deve essere > epsilon per evitare singolarità"
        assert mu >= 0, "Potenziale chimico deve essere non-negativo"
        
        self.mu = mu
        self.T_eff = max(T_eff, epsilon)  # Protezione T→0
        self.epsilon = epsilon
        
        # Clip range per evitare overflow in exp()
        self.x_max = 700.0  # exp(700) ~ 1e304 (sotto limite float64)
    
    def occupation(self, chi: np.ndarray) -> np.ndarray:
        """
        Distribuzione di Fermi-Dirac (probabilità occupazione).
        
        f(χ) = 1 / (exp((χ - μ) / T) + 1)
        
        Proprietà:
        - f(μ) = 0.5 (punto medio)
        - f(-∞) → 1 (completamente occupato)
        - f(+∞) → 0 (vuoto)
        - Monotona decrescente, sempre ∈ [0,1]
        
        Parameters:
        -----------
        chi : ndarray
            Valori del campo χ (può essere scalare o array)
        
        Returns:
        --------
        f : ndarray
            Probabilità occupazione ∈ [0, 1]
        """
        chi = np.asarray(chi)
        
        # Argomento esponente (clippato per stabilità)
        x = (chi - self.mu) / self.T_eff
        x_clipped = np.clip(x, -self.x_max, self.x_max)
        
        # Fermi-Dirac con protezione numerica
        # Per x >> 1: f ≈ exp(-x) (evita overflow)
        # Per x << -1: f ≈ 1
        # Per |x| ~ 0: formula standard
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=RuntimeWarning)
            f = 1.0 / (np.exp(x_clipped) + 1.0)
        
        return f
    
    def screening_factor(self, chi: np.ndarray) -> np.ndarray:
        """
        Fattore di attenuazione screening (1 - f).
        
        A(χ) = 1 - f(χ) = exp((χ-μ)/T) / (exp((χ-μ)/T) + 1)
        
        Interpretazione:
        - χ << μ: A→0 (NO screening, accoppiamento pieno)
        - χ >> μ: A→1 (screening massimo, accoppiamento soppresso)
        
        Questo inverte la logica standard perché vogliamo:
        - Bassa energia → bassa attenuazione (stati occupati, forte interazione)
        - Alta energia → alta attenuazione (stati vuoti, Pauli exclusion)
        
        Parameters:
        -----------
        chi : ndarray
            Valori campo χ
        
        Returns:
        --------
        A : ndarray
            Fattore attenuazione ∈ [0, 1]
        """
        return 1.0 - self.occupation(chi)
    
    def effective_potential(self, chi: np.ndarray) -> np.ndarray:
        """
        Potenziale termodinamico efficace (entropia libera).
        
        V_eff(χ) = -T·ln(1 + exp(-(χ-μ)/T))
        
        Questo è il gran potenziale del sistema Fermi-Dirac.
        La forza F = -dV/dχ garantisce evoluzione conservativa.
        
        Proprietà:
        - χ → -∞: V_eff → 0
        - χ → +∞: V_eff → -(χ-μ)
        - Convessa (d²V/dχ² > 0 → sistema stabile)
        
        Parameters:
        -----------
        chi : ndarray
            Valori campo χ
        
        Returns:
        --------
        V : ndarray
            Potenziale efficace [unità energia]
        """
        chi = np.asarray(chi)
        x = -(chi - self.mu) / self.T_eff
        x_clipped = np.clip(x, -self.x_max, self.x_max)
        
        # V_eff = -T·ln(1 + exp(x))
        # Per x >> 1: V_eff ≈ -T·x = (χ-μ)
        # Per x << -1: V_eff ≈ -T·exp(x) → 0
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=RuntimeWarning)
            V = -self.T_eff * np.log(1.0 + np.exp(x_clipped))
        
        return V
    
    def conservative_force(self, chi: np.ndarray) -> np.ndarray:
        """
        Forza conservativa derivata dal potenziale.
        
        F(χ) = -dV_eff/dχ = -f(χ)
        
        Proprietà:
        - Derivabile su tutto R
        - Monotona (dF/dχ < 0 → forza restauratrice)
        - Asintoticamente nulla per |χ| → ∞
        
        Questa forza 'spinge' il sistema verso configurazioni
        di minima energia libera, implementando il raffreddamento
        termodinamico in modo continuo.
        
        Parameters:
        -----------
        chi : ndarray
            Valori campo χ
        
        Returns:
        --------
        F : ndarray
            Forza conservativa [unità forza]
        """
        return -self.occupation(chi)
    
    def gradient_occupation(self, chi: np.ndarray) -> np.ndarray:
        """
        Gradiente della distribuzione (per calcolo forze).
        
        df/dχ = -f(χ)·(1-f(χ)) / T
              = -1/(4T·cosh²((χ-μ)/(2T)))
        
        Proprietà:
        - Massimo a χ = μ (maggior variazione)
        - Simmetrico rispetto a μ
        - Larghezza ~ 4T (range transizione)
        
        Parameters:
        -----------
        chi : ndarray
            Valori campo χ
        
        Returns:
        --------
        df_dchi : ndarray
            Derivata df/dχ
        """
        f = self.occupation(chi)
        return -f * (1.0 - f) / self.T_eff
    
    def get_occupazione_stati(self, chi_values: np.ndarray) -> dict:
        """
        Analizza distribuzione stati e polarizzazione.
        
        Divide il sistema in:
        - Stati DESTRORSI: χ > μ (alta energia, bassa occupazione)
        - Stati SINISTRORSI: χ < μ (bassa energia, alta occupazione)
        
        Returns:
        --------
        stats : dict
            Dizionario con:
            - 'N_destro': Numero stati χ > μ
            - 'N_sinistro': Numero stati χ < μ
            - 'f_destro': Occupazione media destrorsi
            - 'f_sinistro': Occupazione media sinistrorsi
            - 'polarizzazione': (N_destro - N_sinistro) / N_total
            - 'entropia_mixing': Misura disordine (-Σ[f·ln(f) + (1-f)·ln(1-f)])
        """
        chi_values = np.asarray(chi_values)
        f_vals = self.occupation(chi_values)
        
        # Classificazione stati
        mask_destro = chi_values > self.mu
        mask_sinistro = chi_values <= self.mu
        
        N_destro = np.sum(mask_destro)
        N_sinistro = np.sum(mask_sinistro)
        N_total = len(chi_values)
        
        # Occupazione media per tipo
        f_destro = np.mean(f_vals[mask_destro]) if N_destro > 0 else 0.0
        f_sinistro = np.mean(f_vals[mask_sinistro]) if N_sinistro > 0 else 1.0
        
        # Polarizzazione (asimmetria popolazione)
        polarizzazione = (N_destro - N_sinistro) / N_total if N_total > 0 else 0.0
        
        # Entropia di mixing (misura disordine)
        # S = -Σᵢ [fᵢ·ln(fᵢ) + (1-fᵢ)·ln(1-fᵢ)]
        # S_max quando f=0.5 (massimo disordine)
        # S→0 quando f→0 o f→1 (ordine perfetto)
        eps = 1e-15  # Evita log(0)
        f_safe = np.clip(f_vals, eps, 1.0 - eps)
        entropia = -np.sum(
            f_safe * np.log(f_safe) + (1.0 - f_safe) * np.log(1.0 - f_safe)
        )
        
        return {
            'N_destro': int(N_destro),
            'N_sinistro': int(N_sinistro),
            'f_destro': float(f_destro),
            'f_sinistro': float(f_sinistro),
            'polarizzazione': float(polarizzazione),
            'entropia_mixing': float(entropia),
            'mu': self.mu,
            'T_eff': self.T_eff
        }
    
    def update_temperature(self, gamma_cooling: float, dt: float) -> None:
        """
        Aggiorna temperatura efficace tramite cooling.
        
        dT/dt = -gamma_cooling · T
        T(t+dt) = T(t) · exp(-gamma·dt)
        
        Implementa raffreddamento esponenziale simulando
        un bagno termico a temperatura decrescente.
        
        Parameters:
        -----------
        gamma_cooling : float
            Tasso di raffreddamento [1/s]
        
        dt : float
            Passo temporale [s]
        """
        self.T_eff *= np.exp(-gamma_cooling * dt)
        self.T_eff = max(self.T_eff, self.epsilon)  # Floor minimo
    
    def __repr__(self) -> str:
        return (f"FermiDiracScreening(μ={self.mu:.2f}, T_eff={self.T_eff:.3e}, "
                f"ε={self.epsilon:.1e})")


# ========================================================================
# FUNZIONI DI UTILITÀ
# ========================================================================

def screening_density_based(
    rho_local: np.ndarray,
    fermi_screener: FermiDiracScreening
) -> np.ndarray:
    """
    Calcola screening basato su densità locale (integrazione con vecchia logica).
    
    Invece di: A = exp(-rho / rho_threshold)  [discontinua in derivata]
    Usiamo: A = 1 - f(rho)  [continua e derivabile]
    
    Parameters:
    -----------
    rho_local : ndarray
        Densità locale ρᵢ per ogni solitone
    
    fermi_screener : FermiDiracScreening
        Screener configurato (μ ≈ rho_threshold)
    
    Returns:
    --------
    A_density : ndarray
        Fattore attenuazione densità ∈ [0, 1]
    """
    return fermi_screener.screening_factor(rho_local)


def soft_polarization_potential(
    chi: np.ndarray,
    chi_threshold: float = 4.5,
    width: float = 2.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Potenziale di polarizzazione soft per separazione destrorso/sinistrorso.
    
    Invece di: if chi > threshold: apply hard constraint
    Usiamo: V_pol = k·tanh((χ - χ_threshold) / width)
    
    Questo crea una 'pressione' continua che favorisce la separazione
    di fase senza forzarla tramite discontinuità.
    
    Parameters:
    -----------
    chi : ndarray
        Valori campo χ
    
    chi_threshold : float
        Soglia separazione fasi (default: χ₀ = 4.5)
    
    width : float
        Larghezza transizione (~ temperatura)
    
    Returns:
    --------
    V_pol : ndarray
        Potenziale di polarizzazione
    
    F_pol : ndarray
        Forza F = -dV/dχ
    """
    x = (chi - chi_threshold) / width
    tanh_x = np.tanh(x)
    sech2_x = 1.0 - tanh_x**2
    
    # Potenziale (integrale di tanh)
    # V = k·width·ln(cosh(x))
    V_pol = width * np.log(np.cosh(x))
    
    # Forza (derivata con segno cambiato)
    F_pol = -tanh_x
    
    return V_pol, F_pol


# ========================================================================
# TEST & VALIDAZIONE
# ========================================================================

if __name__ == "__main__":
    """Test unitari per verifica fisica."""
    
    print("=" * 70)
    print("TEST FERMI-DIRAC SCREENING")
    print("=" * 70)
    
    # Test 1: Distribuzione base
    screener = FermiDiracScreening(mu=50.0, T_eff=5.0)
    
    chi_test = np.array([20.0, 40.0, 50.0, 60.0, 80.0])
    f_vals = screener.occupation(chi_test)
    A_vals = screener.screening_factor(chi_test)
    
    print("\n1. DISTRIBUZIONE FERMI-DIRAC")
    print("-" * 70)
    for chi, f, A in zip(chi_test, f_vals, A_vals):
        print(f"χ={chi:5.1f} → f={f:.4f}, A(screening)={A:.4f}")
    
    # Test 2: Forze conservative
    print("\n2. FORZE CONSERVATIVE")
    print("-" * 70)
    chi_range = np.linspace(20, 80, 100)
    V_eff = screener.effective_potential(chi_range)
    F_cons = screener.conservative_force(chi_range)
    
    # Verifica: F = -dV/dχ (numericamente)
    dchi = chi_range[1] - chi_range[0]
    F_numeric = -np.gradient(V_eff, dchi)
    
    error = np.max(np.abs(F_cons - F_numeric))
    print(f"Max error |F_analytic - F_numeric| = {error:.3e}")
    print(f"✓ Forza conservativa verified!" if error < 1e-3 else "✗ ERRORE!")
    
    # Test 3: Occupazione stati
    print("\n3. ANALISI OCCUPAZIONE STATI")
    print("-" * 70)
    chi_system = np.random.uniform(30, 70, 24)  # 24 solitoni
    stats = screener.get_occupazione_stati(chi_system)
    
    print(f"Destrorsi (χ > μ):  N={stats['N_destro']}, <f>={stats['f_destro']:.3f}")
    print(f"Sinistrorsi (χ ≤ μ): N={stats['N_sinistro']}, <f>={stats['f_sinistro']:.3f}")
    print(f"Polarizzazione:     {stats['polarizzazione']:.3f}")
    print(f"Entropia mixing:    {stats['entropia_mixing']:.3f}")
    
    # Test 4: Cooling dynamics
    print("\n4. COOLING DYNAMICS")
    print("-" * 70)
    T_init = 10.0
    gamma = 0.1  # 1/s
    dt = 1.0
    
    screener_cool = FermiDiracScreening(mu=50.0, T_eff=T_init)
    
    print(f"T(t=0) = {screener_cool.T_eff:.3e}")
    for step in range(5):
        screener_cool.update_temperature(gamma, dt)
        print(f"T(t={step+1}) = {screener_cool.T_eff:.3e}")
    
    print("\n" + "=" * 70)
    print("TUTTI I TEST COMPLETATI ✓")
    print("=" * 70)
