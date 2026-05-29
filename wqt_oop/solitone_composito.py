"""
================================================================================
SOLITONE COMPOSITO - Livello N≥1 (Struttura Frattale)
================================================================================

Implementa Pattern Composite: un solitone composto da 24 (o più) sotto-solitoni.

GERARCHIA FRATTALE:
- Livello 0: 1 SegmentoQuantistico (2 DOF)
- Livello 1: 24 Segmenti → SolitoneComposito (48 DOF)
- Livello 2: 24 Solitoni(24) → MacroSolitone (1152 DOF)
- Livello N: 24^N segmenti atomici

FISICA:
- H_total = H_internal + H_coupling + H_inter
- Accoppiamento: Matrice Leech + screening dinamico
- Fusione: 24 solitoni → 1 solitone livello+1
================================================================================
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from scipy.sparse import issparse
from .abstract_soliton import AbstractSoliton
from .segmento_quantistico import SegmentoQuantistico
from .physics_context import PhysicsContext
from .fermi_dirac_screening import FermiDiracScreening, screening_density_based
from .spatial_cache import SpatialCache
from .sparse_coupling import (
    build_sparse_decay_coupling,
    build_dense_decay_coupling,
    weighted_sum_sq,
    weighted_outer_sum,
    matvec,
)
from .energy_metrics import PeanoVQTAnalyzer, EnergyTriad
from .zero_point_motor import enforce_nyquist_zero_point, E_zp_from_amplitude


class SolitoneComposito(AbstractSoliton):
    """
    Solitone composto da N sotto-solitoni (tipicamente N=24).
    
    Implementa composizione frattale: ogni livello contiene 24 unità
    del livello inferiore.
    
    Attributes:
    -----------
    children : List[AbstractSoliton]
        Lista solitoni costituenti (24 o multipli)
    
    N_children : int
        Numero di sotto-solitoni
    
    coupling_matrix : ndarray, shape (N, N)
        Matrice accoppiamento Leech (simmetria E8×E8)
    
    screening_enabled : bool
        Se True, applica screening dinamico multi-scala
    
    E_radiated_total : float
        Energia totale radiata (accumulata durante evoluzione)
    """
    
    def __init__(self,
                 children: List[AbstractSoliton],
                 physics: PhysicsContext,
                 coupling_matrix: Optional[np.ndarray] = None,
                 screening_enabled: bool = True):
        """
        Inizializza solitone composito.
        
        Parameters:
        -----------
        children : List[AbstractSoliton]
            Sotto-solitoni (deve essere multiplo di 24)
        
        physics : PhysicsContext
            Contesto fisico (livello ≥ 1)
        
        coupling_matrix : ndarray, optional
            Matrice accoppiamento W_ij (se None, usa Leech standard)
        
        screening_enabled : bool
            Abilita attenuazione multi-scala
        """
        super().__init__(physics)
        
        assert len(children) % 24 == 0, "N solitoni deve essere multiplo di 24"
        assert physics.level >= 1, "SolitoneComposito richiede livello≥1"
        
        self.children: List[AbstractSoliton] = children
        self.N_children: int = len(children)
        self.screening_enabled: bool = screening_enabled
        
        # FERMI-DIRAC SCREENING (Nuovo: sostituisce soglie discrete)
        self.fermi_screener = FermiDiracScreening(
            mu=physics.mu_fermi,
            T_eff=physics.T_fermi,
            epsilon=physics.fermi_epsilon
        )
        
        # SPATIAL CACHE (Multi-livello: evita ricalcoli ricorsivi)
        self.spatial_cache = SpatialCache(
            invalidation_threshold=1e-4 * (1.5 ** physics.level),  # Scaling per livello
            max_age_steps=10
        )
        self._current_simulation_step = 0  # Tracker step per cache
        
        # Backward compatibility (deprecato: usato solo per diagnostica)
        self.rho_threshold: float = physics.mu_fermi  # DEPRECATO: ora derivato da μ
        
        # Accoppiamento a distanza variabile
        self.L_eff: float = 3.0  # Lunghezza caratteristica interazione (in unità di spaziatura reticolo)
        
        # Bilancio energetico (termodinamica aperta)
        self.E_radiated_total: float = 0.0  # Energia radiata cumulativa
        self.E_transferred_to_children: float = 0.0  # Energia trasferita ai figli (heat sink)
        self.hierarchical_heat_fraction: float = 0.9  # Frazione energia dissipata → riscaldamento figli (AUMENTATA per L3)
        self.E_zero_point_injected: float = 0.0  # Energia cumulativa dal vuoto (motore zero-point Nyquist)

        # PEANO-VQT ENERGY TRIAD
        self._peano_analyzer = PeanoVQTAnalyzer(
            chi_saturation_threshold=0.8,
            drain_rate=0.1,
        )
        self._last_triad: Optional[EnergyTriad] = None
        self._triad_step: int = -1  # guard: drain applicato solo una volta per step

        # Matrice accoppiamento CON DECADIMENTO SPAZIALE
        # Usa CSR sparse per N > 48; densa per N <= 48 (overhead sparse > beneficio)
        if coupling_matrix is None:
            if self.N_children > 48:
                self.coupling_matrix = build_sparse_decay_coupling(
                    self.N_children, self.L_eff
                )
            else:
                self.coupling_matrix = build_dense_decay_coupling(
                    self.N_children, self.L_eff
                )
        else:
            assert coupling_matrix.shape == (self.N_children, self.N_children)
            self.coupling_matrix = coupling_matrix
        
        # Posizione centroide (media posizioni figli)
        self._centroid: Optional[np.ndarray] = None
    
    @staticmethod
    def _build_leech_coupling(N: int) -> np.ndarray:
        """
        Costruisce matrice accoppiamento simmetria Leech.
        
        Per N=24: usa cubottaedro (12 vicini)
        Per N>24: estende pattern ricorsivamente
        
        Parameters:
        -----------
        N : int
            Numero nodi
        
        Returns:
        --------
        W : ndarray, shape (N, N)
            Matrice simmetrica normalizzata
        """
        W = np.zeros((N, N))
        
        # Pattern base 24×24 (cubottaedro)
        if N == 24:
            # Ogni nodo connesso a 12 vicini (simmetria ottaedro+cubo)
            for i in range(24):
                # Connessioni ciclica
                neighbors = [
                    (i + 1) % 24,  # Vicino destro
                    (i - 1) % 24,  # Vicino sinistro
                    (i + 6) % 24,  # Opposizione esagonale
                    (i - 6) % 24,
                    (i + 12) % 24, # Antipodale
                ]
                
                # Connessioni cubottaedro complete (12 vicini)
                for offset in [1, 5, 7, 11, 13, 17, 19, 23]:
                    neighbors.append((i + offset) % 24)
                
                # Rimuovi duplicati e self-connection
                neighbors = list(set(neighbors))
                if i in neighbors:
                    neighbors.remove(i)
                
                # Peso uniforme normalizzato
                for j in neighbors[:12]:  # Limita a 12 vicini
                    W[i, j] = 1.0 / 12.0
        else:
            # Per N > 24: pattern ricorsivo (ogni blocco 24 interno + inter-blocco)
            num_blocks = N // 24
            
            for block_idx in range(num_blocks):
                start = block_idx * 24
                end = start + 24
                
                # Accoppiamento intra-blocco
                W[start:end, start:end] = SolitoneComposito._build_leech_coupling(24)
                
                # Accoppiamento inter-blocco (più debole)
                for other_block in range(num_blocks):
                    if other_block != block_idx:
                        other_start = other_block * 24
                        other_end = other_start + 24
                        
                        # Connessione ridotta (1/24 dell'intensità)
                        W[start:end, other_start:other_end] = 1.0 / (24 * 12)
        
        return W
    
    @staticmethod
    def _build_spatial_decay_coupling(N: int, L_eff: float = 3.0) -> np.ndarray:
        """
        Costruisce matrice accoppiamento con DECADIMENTO SPAZIALE ESPONENZIALE.
        
        W_ij = exp(-d_ij / L_eff) / Z_i
        
        dove:
        - d_ij è la distanza geometrica nel reticolo circolare
        - L_eff è la lunghezza caratteristica di interazione
        - Z_i = Σⱼ exp(-d_ij / L_eff) è la normalizzazione
        
        FISICA:
        - L_eff piccolo (1-2): solo primi vicini, clustering locale forte
        - L_eff medio (3-5): include 2°/3° vicini, clustering moderato
        - L_eff grande (>8): interazioni a lungo raggio, democrazia Leech
        
        Parameters:
        -----------
        N : int
            Numero nodi (deve essere multiplo di 24)
        L_eff : float
            Lunghezza caratteristica interazione [unità di spaziatura]
        
        Returns:
        --------
        W : ndarray, shape (N, N)
            Matrice simmetrica normalizzata con decadimento esponenziale
        """
        W = np.zeros((N, N))
        
        for i in range(N):
            for j in range(N):
                if i == j:
                    W[i, j] = 0.0  # No self-interaction
                else:
                    # Distanza circolare: min(|i-j|, N-|i-j|)
                    d_ij = min(abs(i - j), N - abs(i - j))
                    
                    # Decadimento esponenziale
                    W[i, j] = np.exp(-d_ij / L_eff)
            
            # Normalizzazione: ogni riga somma a 1
            row_sum = np.sum(W[i, :])
            if row_sum > 0:
                W[i, :] /= row_sum
        
        return W
    
    def get_state_vector(self) -> np.ndarray:
        """
        Concatena stati di tutti i figli.
        
        Returns:
        --------
        state : ndarray
            [child_0_state, child_1_state, ..., child_N_state]
        """
        return np.concatenate([child.get_state_vector() for child in self.children])
    
    def set_state_vector(self, state: np.ndarray) -> None:
        """Distribuisce stato ai figli."""
        super().set_state_vector(state)
        
        offset = 0
        for child in self.children:
            n_dof = child.get_num_dof()
            child.set_state_vector(state[offset:offset + n_dof])
            offset += n_dof
    
    def get_auxiliary_state(self) -> Dict[str, np.ndarray]:
        """
        Concatena variabili ausiliarie di tutti i figli.
        
        Returns:
        --------
        aux : dict
            {
                'tau_locale': ndarray(N_children,),
                'contorsione': ndarray(N_children,),
                'chiusura_spinore': ndarray(N_children,)
            }
        """
        tau_list = []
        K_list = []
        closure_list = []
        
        for child in self.children:
            aux = child.get_auxiliary_state()
            tau_list.append(aux['tau_locale'])
            K_list.append(aux['contorsione'])
            closure_list.append(aux['chiusura_spinore'])
        
        return {
            'tau_locale': np.concatenate(tau_list),
            'contorsione': np.concatenate(K_list),
            'chiusura_spinore': np.concatenate(closure_list)
        }

    def get_child_aggregates(self) -> Dict[str, np.ndarray]:
        """
        Ritorna un valore SCALARE per FIGLIO diretto (non per foglia).

        A differenza di get_auxiliary_state() — che attraversa tutti i
        segmenti foglia e alloca array O(N_foglie) — questo metodo
        interroga solo i self.N_children figli diretti, restituendo
        array di lunghezza N_children in O(N_children).

        Usato da compute_hamiltonian_coupling() al posto di
        get_auxiliary_state() per evitare:
        - Allocazione esplosiva a L4 (331 776 foglie per traversal)
        - Bug latente: l'indice [i] accedeva la foglia i, non il figlio i

        Returns
        -------
        dict con chiavi 'chi', 'vel', 'k2_mean', 'tau_mean' —
        arrays di shape (N_children,)
        """
        chi_arr  = np.empty(self.N_children)
        vel_arr  = np.empty(self.N_children)
        k2_arr   = np.empty(self.N_children)
        tau_arr  = np.empty(self.N_children)

        for i, child in enumerate(self.children):
            chi_arr[i] = self._get_child_chi(child)
            vel_arr[i] = self._get_child_velocity(child)
            # k2_mean: per SegmentoQuantistico usa contorsione diretta;
            #          per SolitoneComposito usa la media dei figli cacheata
            if isinstance(child, SegmentoQuantistico):
                aux = child.get_auxiliary_state()
                k2_arr[i]  = float(aux['contorsione'])
                tau_arr[i] = float(aux['tau_locale'])
            else:
                # Usa cached mean-field se disponibile
                cached = child.get_cached_mean_state()
                if cached is not None:
                    k2_arr[i]  = cached.get('k2_mean', 0.0)
                    tau_arr[i] = cached.get('tau_mean', child.physics.level * 0.05)
                else:
                    # Fallback: media sui figli diretti del composito (1 livello)
                    sub_k2  = []
                    sub_tau = []
                    for sub in child.children:
                        a = sub.get_auxiliary_state()
                        sub_k2.append(float(a['contorsione'])
                                      if np.isscalar(a['contorsione'])
                                      else float(np.mean(a['contorsione'])))
                        sub_tau.append(float(a['tau_locale'])
                                       if np.isscalar(a['tau_locale'])
                                       else float(np.mean(a['tau_locale'])))
                    k2_arr[i]  = float(np.mean(sub_k2))
                    tau_arr[i] = float(np.mean(sub_tau))

        return {'chi': chi_arr, 'vel': vel_arr,
                'k2_mean': k2_arr, 'tau_mean': tau_arr}

    def compute_hamiltonian_internal(self) -> float:
        """
        Somma energie interne dei figli.
        
        H_internal = Σᵢ H_child[i]
        """
        return sum(child.energia_totale for child in self.children)
    
    def compute_hamiltonian_coupling(self) -> float:
        """
        Energia accoppiamento tra figli + torsione geometrica.

        H_coupling = (1/2) Σᵢⱼ W_ij · A(Δχ,Δv,ΔK²,Δτ) · (χᵢ-χⱼ)²
                   + E_torsion + E_exchange

        Come effetto collaterale aggiorna self._last_triad (EnergyTriad Peano-VQT)
        con il drain χ→Ψ applicato al massimo una volta per step di simulazione
        (guard self._triad_step vs self._current_simulation_step).

        Il valore restituito è il float invariato dell'Hamiltoniana classica;
        la triade è accessibile tramite get_energy_triad() o get_energy_budget().
        """
        if self.N_children == 1:
            return 0.0  # Singolo figlio: no coupling, no torsion

        # Estrai campi χ dai figli (media se compositi)
        chi_values = np.array([self._get_child_chi(child) for child in self.children])

        # Matrice differenze
        chi_diff = chi_values[:, None] - chi_values[None, :]

        # --- TERMINE DI TORSIONE GEOMETRICA ---
        E_torsion = 0.5 * self.physics.alpha_K * np.sum(self.coupling_matrix * chi_diff**2)

        # --- INTERAZIONE DI SCAMBIO TOPOLOGICO (SMOOTH) ---
        # CRITICAL FIX (2026-05-26): Use chi_stable from PhysicsContext
        chi_0 = self.physics.chi_stable
        tanh_matrix = np.tanh(chi_values[:, None] / chi_0) * np.tanh(chi_values[None, :] / chi_0)
        E_exchange_unscreened = -self.physics.lambda_exchange * self.physics.alpha_K * np.sum(
            self.coupling_matrix * tanh_matrix
        )

        if not self.screening_enabled:
            E_coupling = 0.5 * weighted_sum_sq(self.coupling_matrix, chi_diff)
            E_chi_raw = self.physics.kappa_coupling * E_coupling
            E_exchange_val = E_exchange_unscreened
        else:
            # --- SCREENING ADATTIVO LOCALE (vettorizzato) ---
            agg = self.get_child_aggregates()
            chi_values_v = agg['chi']
            velocities   = agg['vel']
            K_squared    = agg['k2_mean']
            tau_locale   = agg['tau_mean']

            rho_local = matvec(
                np.abs(self.coupling_matrix)
                if not issparse(self.coupling_matrix)
                else self.coupling_matrix.copy(),
                np.abs(chi_values_v),
            )
            A_density = self.fermi_screener.screening_factor(rho_local)

            dchi = chi_values_v[:, None] - chi_values_v[None, :]
            dvel = velocities[:, None]   - velocities[None, :]
            dk2  = K_squared[:, None]    - K_squared[None, :]
            dtau = tau_locale[:, None]   - tau_locale[None, :]

            A_chi  = np.exp(-np.abs(dchi) / self.physics.sigma_chi)
            A_vel  = np.exp(-np.abs(dvel) / self.physics.sigma_velocity)
            A_K    = np.exp(-np.abs(dk2)  / self.physics.sigma_torsion)
            A_tau  = np.exp(-np.abs(dtau) / self.physics.sigma_tau)
            A_dens_mat = (A_density[:, None] + A_density[None, :]) / 2.0
            attenuation = A_chi * A_vel * A_K * A_tau * A_dens_mat

            W_dense = (self.coupling_matrix.toarray()
                       if issparse(self.coupling_matrix)
                       else self.coupling_matrix)
            W_eff = W_dense * attenuation

            E_coupling = 0.5 * float(np.sum(W_eff * dchi ** 2))
            E_chi_raw = self.physics.kappa_coupling * E_coupling

            tanh_v = np.tanh(chi_values_v / chi_0)
            tanh_mat = tanh_v[:, None] * tanh_v[None, :]
            E_exchange_screened = -float(np.sum(W_eff * tanh_mat))
            E_exchange_val = self.physics.lambda_exchange * self.physics.alpha_K * E_exchange_screened

            # Libera temporanei (benefico a L4 con >14k chiamate/step)
            del dchi, dvel, dk2, dtau, A_chi, A_vel, A_K, A_tau, A_dens_mat
            del attenuation, W_eff, tanh_mat

        # --- PEANO-VQT TRIAD (side-effect, guard per-step) ---
        # Saturazione χ: mean(|χ|)/χ_stable ∈ [0,1]
        chi_saturation = float(min(np.mean(np.abs(chi_values)) / max(chi_0, 1e-30), 1.0))

        if self._triad_step != self._current_simulation_step:
            # Prima chiamata di questo step: applica drain
            triad = self._peano_analyzer.compute_triad(E_chi_raw, E_torsion, E_exchange_val)
            self._last_triad = self._peano_analyzer.apply_drain(triad, chi_saturation)
            self._triad_step = self._current_simulation_step
        else:
            # Chiamata successiva nello stesso step (es. H_after in evolve):
            # aggiorna i componenti fisici senza applicare ulteriore drain
            self._last_triad = EnergyTriad(
                E_chi=E_chi_raw,
                E_RX=E_torsion + E_exchange_val,
                E_Psi=self._peano_analyzer.E_psi_total,
            )

        return E_chi_raw + E_torsion + E_exchange_val

    def get_energy_triad(self) -> Optional[EnergyTriad]:
        """
        Restituisce l'ultima triade Peano-VQT calcolata.

        Returns None se compute_hamiltonian_coupling() non è ancora stato chiamato.
        """
        return self._last_triad
    
    @staticmethod
    def _get_child_chi(child: AbstractSoliton) -> float:
        """Estrae χ medio da figlio (gestisce sia Segmento che Composito)."""
        if isinstance(child, SegmentoQuantistico):
            return child.chi
        else:
            # Composito: media ricorsiva
            state = child.get_state_vector()
            chi_vals = state[::2]  # Estrai χ (posizioni pari)
            return np.mean(chi_vals)
    
    @staticmethod
    def _get_child_velocity(child: AbstractSoliton) -> float:
        """Estrae velocità media da figlio."""
        if isinstance(child, SegmentoQuantistico):
            return child.vel
        else:
            state = child.get_state_vector()
            vel_vals = state[1::2]  # Estrai v (posizioni dispari)
            return np.mean(vel_vals)
    
    def get_position(self) -> np.ndarray:
        """
        Posizione = centroide figli (baricentro).
        
        Usa spatial cache per evitare ricalcoli frequenti.
        
        Per Livello 1: media delle posizioni dei 24 segmenti atomici
        Per Livello 2+: media ricorsiva dei baricentri dei compositi figli
        
        Returns:
        --------
        position : ndarray
            Baricentro geometrico [dimensione dipende da implementazione]
        """
        # Prova cache PRIMA
        cached_state = self.spatial_cache.get(self._current_simulation_step)
        if cached_state is not None:
            return cached_state.position_mean
        
        # Cache miss: calcola posizione
        if self._centroid is None:
            positions = np.array([child.get_position() for child in self.children])
            self._centroid = np.mean(positions, axis=0)
        return self._centroid
    
    def compute_barycenter(self) -> float:
        """
        Calcola baricentro nel campo χ (centro di massa topologico).
        
        Per solitoni compositi gerarchici, questo permette di trattare
        un MacroSolitone come un "punto pesante" nelle interazioni
        a livello superiore.
        
        Returns:
        --------
        chi_center : float
            Campo χ medio ponderato (baricentro topologico)
        """
        # Per compositi, calcola media ricorsiva
        chi_values = np.array([self._get_child_chi(child) for child in self.children])
        return np.mean(chi_values)
    
    def get_topology_charge(self) -> float:
        """
        Carica topologica globale = somma winding numbers.
        
        Q_total = Σᵢ (τᵢ / 4π)
        
        Questo è l'invariante topologico conservato durante evoluzione.
        """
        return sum(child.get_topology_charge() for child in self.children)
    
    def get_spinor_closure(self) -> float:
        """Chiusura = somma τ figli (mod 4π)."""
        total_tau = sum(child.get_spinor_closure() for child in self.children)
        return total_tau % (4 * np.pi)
    
    def get_occupazione_stati(self) -> Dict[str, float]:
        """
        NUOVO: Analizza distribuzione stati Fermi-Dirac e polarizzazione.
        
        Divide il sistema in:
        - Stati DESTRORSI: χ > μ (alta energia, bassa occupazione)
        - Stati SINISTRORSI: χ ≤ μ (bassa energia, alta occupazione)
        
        Returns:
        --------
        stats : dict
            Dizionario con:
            - 'N_destro': Numero stati χ > μ
            - 'N_sinistro': Numero stati χ ≤ μ
            - 'f_destro': Occupazione media destrorsi
            - 'f_sinistro': Occupazione media sinistrorsi
            - 'polarizzazione': (N_destro - N_sinistro) / N_total
            - 'entropia_mixing': Misura disordine termodinamico
            - 'mu': Potenziale chimico attuale
            - 'T_eff': Temperatura efficace attuale
            - 'rho_media': Densità locale media
        
        Esempio uso:
        ------------
        >>> stats = soliton.get_occupazione_stati()
        >>> print(f"Polarizzazione: {stats['polarizzazione']:.3f}")
        >>> print(f"Entropia: {stats['entropia_mixing']:.3f}")
        >>> print(f"T_eff: {stats['T_eff']:.3e}")
        """
        # Estrai valori χ dai figli
        chi_values = np.array([self._get_child_chi(child) for child in self.children])
        
        # Usa il metodo del FermiDiracScreening
        stats = self.fermi_screener.get_occupazione_stati(chi_values)
        
        # Aggiungi densità locale media (diagnostica aggiuntiva)
        rho_local = np.abs(self.coupling_matrix) @ np.abs(chi_values)
        stats['rho_media'] = float(np.mean(rho_local))
        stats['rho_max'] = float(np.max(rho_local))
        stats['rho_min'] = float(np.min(rho_local))
        
        return stats
    
    def get_cached_mean_state(self) -> Optional[Dict[str, float]]:
        """
        Recupera stato medio cachato (mean-field approximation).
        
        PERFORMANCE: Usato da livelli superiori per evitare discese ricorsive
        profonde nella gerarchia. Se cache valida, restituisce:
        - chi_mean: Valor medio campo χ
        - chi_std: Deviazione standard
        - H_total: Energia totale
        
        Se cache invalida, restituisce None (caller deve ricalcolare).
        
        Returns:
        --------
        state : dict or None
            Stato cachato (None se invalido)
        
        Esempio uso (livello L3 che interroga L2):
        ------------------------------------------
        >>> cached = level2_soliton.get_cached_mean_state()
        >>> if cached is not None:
        >>>     chi_approx = cached['chi_mean']  # Evita ricorsione profonda
        >>> else:
        >>>     chi_approx = level2_soliton.compute_barycenter()  # Fallback
        """
        cached_state = self.spatial_cache.get(self._current_simulation_step)
        
        if cached_state is None:
            return None
        
        return {
            'chi_mean': cached_state.chi_mean,
            'chi_std': cached_state.chi_std,
            'H_total': cached_state.H_total,
            'position_mean': cached_state.position_mean,
            'cache_age_steps': self._current_simulation_step - cached_state.step
        }
    
    def evolve(self, dt: float, external_force: np.ndarray = None) -> None:
        """
        Evolve tutti i figli con forze interne + esterne + dissipazione radiativa.
        
        Parameters:
        -----------
        dt : float
            Timestep globale [Planck time]
        external_force : ndarray or float, optional
            Forza esterna (scalare o array per ogni child)
        
        Process:
        --------
        1. Calcola coefficiente smorzamento gamma(Var(tau))
        2. Aggiorna gamma_damping nei figli
        3. Calcola forze inter-child (accoppiamento)
        4. Distribuisci forze ai figli
        5. Evolvi ogni figlio (con dissipazione integrata)
        6. Misura energia radiata effettiva
        7. Invalida cache
        """
        # --- CALCOLO COEFFICIENTE SMORZAMENTO DINAMICO ---
        gamma = self._compute_damping_coefficient()
        
        # Invalida cache PRIMA della misurazione
        self._cache_valid = False
        
        # Energia PRIMA evoluzione (per bilancio)
        H_before = self.compute_hamiltonian()
        
        # Aggiorna gamma nei figli (MUTABILE)
        for child in self.children:
            if isinstance(child, SegmentoQuantistico):
                child.gamma_damping = gamma
            else:
                # Ricorsivo per compositi
                child._set_damping_recursive(gamma)
        
        # Calcola forze di accoppiamento
        internal_forces = self._compute_coupling_forces()
        
        # Gestione external_force (può essere None, scalare o array)
        if external_force is None:
            ext_forces_array = np.zeros(self.N_children)
        elif isinstance(external_force, (int, float, np.number)):
            # Scalare: applica uniformemente a tutti i figli
            ext_forces_array = np.full(self.N_children, float(external_force))
        else:
            # Array: usa direttamente
            ext_forces_array = np.asarray(external_force)
        
        # Evolvi ogni figlio
        for i, child in enumerate(self.children):
            # Forza totale = interna + esterna
            total_force = internal_forces[i] + ext_forces_array[i]
            
            # Evoluzione figlio (con smorzamento integrato)
            child.evolve(dt, total_force)
        
        # --- COOLING TEMPERATURA FERMI-DIRAC ---
        # Aggiorna temperatura efficace: T(t+dt) = T(t)·exp(-gamma_cooling·dt)
        if self.screening_enabled:
            self.fermi_screener.update_temperature(
                gamma_cooling=self.physics.gamma_cooling,
                dt=dt
            )
        
        # --- MISURA ENERGIA RADIATA EFFETTIVA ---
        # Invalida cache PRIMA della misurazione finale
        self._cache_valid = False
        H_after = self.compute_hamiltonian()
        E_rad_step = H_before - H_after
        
        # Accumula variazione (positiva = dissipazione, negativa = assorbimento)
        self.E_radiated_total += E_rad_step
        
        # =====================================================================
        # [LEGGE FISICA: Trasferimento Energetico Gerarchico - Serbatoio]
        # Principio: L'energia dissipata da livello n non si annulla, ma
        #            trasferisce al livello n-1 come calore residuo (70%),
        #            preservando conservazione globale H_conserved.
        # 
        # Derivazione: Dalla termodinamica dei sistemi aperti (Prigogine),
        #              energia dissipata = ∫ T·dS = Q_emesso + W_trasferito.
        #              Con efficienza ε=0.7, Q_trasferito = 0.7·E_rad.
        # 
        # Validazione: TODO_VALIDATION → test_energy_transfer (test_universal_scaling.py)
        # =====================================================================
        if E_rad_step > 0 and self.hierarchical_heat_fraction > 0:
            E_transfer = E_rad_step * self.hierarchical_heat_fraction
            self._transfer_heat_to_children(E_transfer, dt)
            self.E_transferred_to_children += E_transfer
        
        # --- AGGIORNA SPATIAL CACHE ---
        # Ricalcola stato medio figli
        positions = np.array([child.get_position() for child in self.children])
        chi_values = np.array([self._get_child_chi(child) for child in self.children])
        
        position_mean = np.mean(positions, axis=0)
        chi_mean = float(np.mean(chi_values))
        chi_std = float(np.std(chi_values))
        
        # Update cache
        self._current_simulation_step += 1
        self.spatial_cache.update(
            position_mean=position_mean,
            chi_mean=chi_mean,
            chi_std=chi_std,
            H_total=H_after,
            current_step=self._current_simulation_step
        )
        
        # Invalida cache e centroide (backward compatibility)
        self._cache_valid = False
        self._centroid = None

        # =====================================================================
        # [MOTORE ZERO-POINT: modo di Nyquist lambda=2 l_P]
        # Il modo staggered (-1)^i non puo' mai congelarsi: floor di punto-zero
        # T-indipendente. Applicato SOLO a figli atomici (SegmentoQuantistico).
        # Gated da physics.zero_point_amplitude (0 = off, backward-compatible).
        # =====================================================================
        zp_amp = getattr(self.physics, 'zero_point_amplitude', 0.0)
        if zp_amp > 0.0 and self.N_children >= 2 and all(
            isinstance(c, SegmentoQuantistico) for c in self.children
        ):
            E_zp = E_zp_from_amplitude(zp_amp, self.N_children)
            vels = np.array([c.vel for c in self.children], dtype=float)
            v_new, E_inj = enforce_nyquist_zero_point(vels, E_zp)
            for c, vv in zip(self.children, v_new):
                c.vel = float(vv)
            self.E_zero_point_injected += E_inj
            self._cache_valid = False  # le velocita' sono cambiate

    def _compute_coupling_forces(self) -> np.ndarray:
        """
        Calcola forze di accoppiamento tra figli.
        
        F_i = -∂H_coupling/∂χᵢ
            = -∂(kappa·E_coupling + E_exchange)/∂χᵢ
            = -kappa·Σⱼ W_ij·2(χᵢ-χⱼ)
              + λ·α_K·Σⱼ W_ij·sech²(χᵢ/χ₀)·tanh(χⱼ/χ₀)/χ₀
        
        NOTA: E_torsion è un observable geometrico (K² della connessione),
        non genera forze dinamiche. È emergente, non primario.
        
        Returns:
        --------
        forces : ndarray, shape (N_children,)
            Forza su ogni figlio
        """
        chi_values = np.array([self._get_child_chi(child) for child in self.children])
        forces = np.zeros(self.N_children)
        # CRITICAL FIX (2026-05-26): Use chi_stable from PhysicsContext
        chi_0 = self.physics.chi_stable  # Scala caratteristica del campo
        
        if not self.screening_enabled:
            # Forze senza screening
            for i in range(self.N_children):
                F_coupling = 0.0
                F_exchange = 0.0
                
                for j in range(self.N_children):
                    if i != j:
                        W_ij = self.coupling_matrix[i, j]
                        
                        # Contributo E_coupling: (χᵢ-χⱼ)²
                        delta_chi = chi_values[i] - chi_values[j]
                        F_coupling += W_ij * 2 * delta_chi
                        
                        # Contributo E_exchange: -λ·α_K·Σ W·tanh(χᵢ/χ₀)·tanh(χⱼ/χ₀)
                        # ∂/∂χᵢ = -λ·α_K·W·sech²(χᵢ/χ₀)·tanh(χⱼ/χ₀)/χ₀
                        tanh_i = np.tanh(chi_values[i] / chi_0)
                        tanh_j = np.tanh(chi_values[j] / chi_0)
                        sech2_i = 1.0 - tanh_i**2  # sech²(x) = 1 - tanh²(x)
                        F_exchange += -W_ij * sech2_i * tanh_j / chi_0
                
                # Forza totale (NO F_torsion: è geometrico, non dinamico)
                forces[i] = (-self.physics.kappa_coupling * F_coupling 
                           + self.physics.lambda_exchange * self.physics.alpha_K * F_exchange)
            
            # CLIP forze per evitare singolarità numeriche
            # (protezione contro esplosioni in regioni chi~0)
            F_max = 1e6  # Forza massima ammissibile
            forces = np.clip(forces, -F_max, F_max)
            
            return forces
        
        # --- CON SCREENING ADATTIVO ---
        # Densità locale campo
        rho_local = np.abs(self.coupling_matrix) @ np.abs(chi_values)
        
        aux = self.get_auxiliary_state()
        velocities = np.array([self._get_child_velocity(child) for child in self.children])
        K_squared = aux['contorsione']
        tau_locale = aux['tau_locale']
        
        for i in range(self.N_children):
            F_coupling = 0.0
            F_exchange = 0.0
            
            for j in range(self.N_children):
                if i == j:
                    continue
                
                # Differenze
                delta_chi = abs(chi_values[i] - chi_values[j])
                delta_v = abs(velocities[i] - velocities[j])
                delta_K2 = abs(K_squared[i] - K_squared[j])
                delta_tau = abs(tau_locale[i] - tau_locale[j])
                
                # Attenuazione
                A_chi = np.exp(-delta_chi / self.physics.sigma_chi)
                A_v = np.exp(-delta_v / self.physics.sigma_velocity)
                A_K = np.exp(-delta_K2 / self.physics.sigma_torsion)
                A_tau = np.exp(-delta_tau / self.physics.sigma_tau)
                
                attenuation = A_chi * A_v * A_K * A_tau
                
                # Screening adattivo densità (Fermi-Dirac)
                A_density_i = self.fermi_screener.screening_factor(np.array([rho_local[i]]))[0]
                A_density_j = self.fermi_screener.screening_factor(np.array([rho_local[j]]))[0]
                A_density = (A_density_i + A_density_j) / 2.0
                
                attenuation_total = attenuation * A_density
                w_eff = self.coupling_matrix[i, j] * attenuation_total
                
                # Contributo da (χᵢ-χⱼ)²
                delta_chi_signed = chi_values[i] - chi_values[j]
                F_coupling += w_eff * 2 * delta_chi_signed
                
                # Contributo E_exchange (smooth)
                tanh_i = np.tanh(chi_values[i] / chi_0)
                tanh_j = np.tanh(chi_values[j] / chi_0)
                sech2_i = 1.0 - tanh_i**2
                F_exchange += -w_eff * sech2_i * tanh_j / chi_0
            
            # Forza totale (NO F_torsion)
            forces[i] = (-self.physics.kappa_coupling * F_coupling 
                       + self.physics.lambda_exchange * self.physics.alpha_K * F_exchange)
        
        # CLIP forze per stabilità numerica
        F_max = 1e6  # Forza massima ammissibile
        forces = np.clip(forces, -F_max, F_max)
        
        return forces
    
    def _compute_damping_coefficient(self) -> float:
        """
        Calcola coefficiente smorzamento adattivo universale.
        
        MODELLO TERMODINAMICO FRATTALE:
        gamma_adaptive = gamma_base(level) · f_thermal(T_eff) · g_disomogeneity(Var(tau))
        
        DELEGA A PhysicsContext.get_adaptive_damping() che implementa:
        - Legge di scala frattale: γ_base(n) = γ_0 · (24^n)^k
        - Feedback termodinamico: modulazione per T_eff
        - Modulazione disomogeneità: dipendenza da Var(τ)
        
        Returns:
        --------
        gamma : float
            Coefficiente smorzamento adattivo [1/s]
        """
        if self.N_children == 0:
            return 0.0
        
        # Calcola disomogeneità temporale
        aux = self.get_auxiliary_state()
        tau_vals = aux['tau_locale']
        tau_variance = np.var(tau_vals)
        
        # Temperatura efficace del sistema
        T_eff = self.fermi_screener.T_eff if self.screening_enabled else self.physics.T_fermi
        
        # USA MODELLO UNIVERSALE (legge di scala + feedback termico)
        gamma_adaptive = self.physics.get_adaptive_damping(
            T_eff=T_eff,
            tau_variance=tau_variance,
            level=self.physics.level
        )
        
        return gamma_adaptive
    
    def _set_damping_recursive(self, gamma: float) -> None:
        """Propaga coefficiente smorzamento ricorsivamente."""
        for child in self.children:
            if isinstance(child, SegmentoQuantistico):
                child.gamma_damping = gamma
            else:
                child._set_damping_recursive(gamma)
    
    # =========================================================================
    # [LEGGE FISICA: Distribuzione Energetica Gerarchica via Equipartizione]
    # Principio: Energia termica si distribuisce uniformemente tra DOF figli,
    #            aumentando energia cinetica (segmenti) o temperatura (compositi).
    # 
    # Derivazione: Teorema di equipartizione (Boltzmann): E = (1/2)k_B·T per DOF.
    #              Con N_children DOF, E_per_child = E_total/N_children.
    # 
    # Meccanismo: - SegmentoQuantistico: ΔE → Δv = sqrt(2ΔE/m)
    #             - SolitoneComposito: ΔE → ΔT_eff = E/(N·k_B)
    # 
    # Validazione: TODO_VALIDATION → transfer_fraction = 70% (test_energy_transfer)
    # =========================================================================
    def _transfer_heat_to_children(self, E_heat: float, dt: float) -> None:
        """
        Trasferisce energia dissipata ai figli come riscaldamento (serbatoio energetico).
        
        TEORIA DEL SERBATOIO:
        ---------------------
        L'energia dissipata dal livello n (via damping) non viene 'persa',
        ma trasferita al livello n-1 (children) come calore residuo.
        
        - Se child è SolitoneComposito: aumenta T_eff locale (riscaldamento termico)
        - Se child è SegmentoQuantistico: aumenta velocità (energia cinetica)
        
        Questo assicura che H_conserved = H_total + E_radiated rimanga costante
        su scala cosmologica.
        
        Args:
            E_heat: Energia da trasferire [J]
            dt: Timestep corrente [s]
        """
        if self.N_children == 0 or E_heat <= 0:
            return
        
        # Energia per figlio (distribuzione uniforme)
        E_per_child = E_heat / self.N_children
        
        for child in self.children:
            if isinstance(child, SegmentoQuantistico):
                # SEGMENTO: Energia cinetica
                # ΔE_kin = (1/2)mΔv² ⇒ Δv = sqrt(2ΔE/m)
                # NOTA: Fattore 0.5 per evitare boost eccessivi che causano instabilità numerica
                delta_v = 0.5 * np.sqrt(2.0 * E_per_child / child.mass)
                
                # Aggiungi velocità (random direction per isotropia)
                direction = 1.0 if np.random.rand() > 0.5 else -1.0
                child.vel += direction * delta_v
                
                # Clamp per stabilità
                child.vel = np.clip(child.vel, -self.physics.MAX_VELOCITY, self.physics.MAX_VELOCITY)
            
            else:
                # COMPOSITO: Riscaldamento termico (aumenta T_eff)
                # ΔT = E_heat / (N_DOF · k_B) dove k_B ~ 1 (unità naturali)
                # Approssimazione: ΔT ∝ E_heat / N_children
                if child.screening_enabled and hasattr(child, 'fermi_screener'):
                    # Aumenta temperatura efficace del child
                    delta_T = E_per_child / child.N_children  # Scaling per DOF
                    new_T_eff = child.fermi_screener.T_eff + delta_T
                    
                    # Clamp per stabilità (non superare 10x temperatura base)
                    T_max = child.physics.T_fermi * 10.0
                    new_T_eff = np.clip(new_T_eff, child.physics.T_fermi * 0.1, T_max)
                    
                    # Aggiorna temperatura (MUTAZIONE: fermi_screener non è frozen)
                    child.fermi_screener.T_eff = new_T_eff
    
    def get_energy_budget(self) -> Dict[str, float]:
        """
        Restituisce bilancio energetico completo CON trasferimento gerarchico.
        
        Returns:
        --------
        budget : dict
            {
                'H_internal': Energia figli,
                'H_coupling': Energia accoppiamento,
                'H_total': Energia totale,
                'E_radiated': Energia radiata cumulativa,
                'E_transferred': Energia trasferita ai figli (heat sink),
                'E_net_dissipated': E_radiated - E_transferred (vera perdita),
                'H_conserved': H_total + E_net_dissipated (deve essere costante)
            }
        """
        H_int = self.compute_hamiltonian_internal()
        H_coup = self.compute_hamiltonian_coupling()
        H_tot = H_int + H_coup
        
        # Energia netta dissipata = radiata - trasferita ai figli
        E_net_dissipated = self.E_radiated_total - self.E_transferred_to_children
        
        budget = {
            'H_internal': H_int,
            'H_coupling': H_coup,
            'H_total': H_tot,
            'E_radiated': self.E_radiated_total,
            'E_transferred': self.E_transferred_to_children,
            'E_net_dissipated': E_net_dissipated,
            'H_conserved': H_tot + E_net_dissipated,
            'E_zero_point': self.E_zero_point_injected,
        }

        # Peano-VQT triad (disponibile dopo la prima chiamata a compute_hamiltonian_coupling)
        if self._last_triad is not None:
            budget['E_chi'] = self._last_triad.E_chi
            budget['E_RX']  = self._last_triad.E_RX
            budget['E_Psi'] = self._last_triad.E_Psi

        return budget
    
    def __repr__(self) -> str:
        return (
            f"SolitoneComposito(livello={self.physics.level}, "
            f"N_children={self.N_children}, "
            f"DOF={self.get_num_dof()}, "
            f"H={self.energia_totale:.3e})"
        )
