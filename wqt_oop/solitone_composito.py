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
        # Soglia Jitterbug: chi_max/chi_stable = sqrt(2) e' la costante geometrica
        # della transizione Ottaedro->Cubottaedro di Fuller, calibrata sperimentalmente
        # su file L2/L3/L4 (5/8 file entro 5% da sqrt(2)).
        self._peano_analyzer = PeanoVQTAnalyzer(
            chi_saturation_threshold=np.sqrt(2),
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

        # === EINSTEIN-CARTAN (additivo, opt-in; legacy evolve() INTATTO) ===
        # Dinamica EC: torsione a chiralita' alternata (180 deg) + chiusura spinoriale
        # 720 deg + saturazione (pressione di degenerazione di spin = bounce).
        # Recupera la fisica persa nel refactoring (commit a5b417e). Vedi
        # wqt_oop/einstein_cartan.py e docs/peano/DIAGNOSI_SATURAZIONE_EC.md.
        self.ec_dynamics_enabled: bool = False   # DEFAULT OFF -> comportamento legacy
        # Coefficienti EC (tarabili). NON sono i coupling postulati scala-dipendenti:
        # sono ancorati a scale fisiche/topologiche. beta_sat = forza della
        # saturazione; kappa_closure = rigidita' della chiusura 720; k2_ref dalla
        # scala del campo (sqrt(2)*chi0 Jitterbug), non un fit.
        # beta_sat = l'analogo di G (accoppiamento gravitazionale del muratore EC).
        # NON e' un knob libero: e' DERIVATO dalla rigidezza geometrica (gravita'
        # indotta, Sakharov/Verlinde) -> beta_sat = Theta / R_geo, con
        #   R_geo = 4 N/(N-1) = 4*24/23 = 4.174  (topologico, dal 24 di Leech)
        #   Theta = scala intrinseca del voxel (da chi0, beta_pot), NON tarata.
        # Vedi wqt_oop/rigidezza_geometrica.py e docs/peano/EDIFICIO_EINSTEIN_CARTAN.md.
        # Il valore qui e' il placeholder in unita' di codice (Theta=1); per usare la
        # G emergente: beta_sat <- rigidezza_geometrica.block_rigidity(...)[1].
        self.ec_beta_sat: float = 1e-8
        self.ec_kappa_closure: float = 1e-2
        from .einstein_cartan import default_k2_ref_chi
        self.ec_k2_ref_chi: float = default_k2_ref_chi(self.physics.chi_stable)

        # === MURATORE DI PLANCK (additivo, opt-in; lato ESPANSIONE dell'EC) ===
        # La stessa pressione di spin che satura (bounce) spinge lo spazio a crescere:
        # fattore di scala a per blocco, guidato dall'eccesso di torsione fisica
        # (K2/a^2 - rho*)+, AUTO-REGOLANTE (H->0 a equilibrio). ZERO parametri nuovi:
        # riusa ec_beta_sat e ec_k2_ref_chi. Vedi wqt_oop/muratore_planck.py.
        self.muratore_enabled: bool = False      # DEFAULT OFF -> nessuna espansione
        self.scale_factor_a: float = 1.0         # metrica del blocco (a=1: nessuna)
        self.muratore_d_f: float = 3.0           # dim. effettiva per il conteggio voxel
        self.muratore_H_last: float = 0.0        # ultimo H = a'/a (diagnostico)

        # === DRIVE DI FONDO (gravita': la FEBBRE e' il motore di espansione) ===
        # L'espansione di fondo e' sorgentata dall'agitazione termica LOCALE (la febbre
        # = KE/nodo), modulata dalla rigidezza (i kink la sopprimono):
        #   H_fondo = h_fondo_coeff * T_local / (1 + K2/rho*)
        # -> i VUOTI (T>0, K2 basso) espandono; la MATERIA (K2 alto) e' soppressa ->
        #    la materia si addensa (CLUMPING = gravita' attrattiva, controparte della
        #    spinta espansiva). Cosi' la febbre/termostato DIVENTA il motore (non un
        #    bagno separato). coeff=0 (default) -> nessun drive (GATE bit-identico).
        self.muratore_h_fondo_coeff: float = 0.0

        # === G EMERGENTE ATTIVA (additivo, opt-in): beta_sat <- rigidezza FISICA ===
        # La rigidezza fisica e' R_phys = R_geo/a^2 (diluita dall'espansione), quindi
        # beta = Theta/R_phys = beta_baseline * a^2 per blocco: dove lo spazio si e'
        # espanso, G e' MAGGIORE (gravita' indotta). Feedback espansione->G->espansione,
        # regolato dalla diluizione della torsione (~1/a^2). Flag OFF -> beta costante
        # (GATE bit-identico). Vedi wqt_oop/rigidezza_geometrica.py.
        self.g_emergent_active: bool = False

        # === KINK-STIFFENING (additivo, opt-in): la MATERIA irrigidisce lo spaziotempo ===
        # In VQT i kink SONO complessita' dello spaziotempo (la materia nasce dalla
        # torsione). Quindi i kink aumentano la rigidezza locale:
        #   R_local = R_geo * (1 + K2/rho*)   (knob-free: usa il rho* derivato)
        #   beta_local = Theta/R_local = beta_geom / (1 + K2/rho*)
        # -> dove c'e' materia (K2 alto) beta cala -> espansione SOPPRESSA li'; i VUOTI
        #    (soffici) espandono -> la materia si addensa (grumi). La spinta espansiva
        #    (frame spaziotempo) E' attrazione (frame materia): UNA sola forza.
        self.kink_stiffening_active: bool = False

        # === MOTORE CHIRALE SPINORIALE (additivo, opt-in) ===
        # Da' ai voxel lo spinore (theta, dphi): beta/alpha = pendenza del kink, twist 180
        # alternato + chiusura 720. Le densita' chirali SX/DX derivano dallo spinore.
        # Vive ACCANTO a (chi,v); default OFF -> bit-identico. Vedi motore_chirale_spinoriale.py.
        self.spinore_enabled: bool = False

        # === EINSTEIN-CARTAN COMPLETO: la TORSIONE e' sorgentata dallo SPIN ===
        # Quando attivo: la torsione K2 usata in saturazione/espansione/gravita' viene dal
        # vettore di Bloch dello spinore (K2_spin = chi0^2 * sum W |n_i-n_j|^2), NON dal
        # gradiente scalare di chi. Lo spin genera la torsione (EC vero). Richiede lo spinore.
        self.ec_torsion_from_spin: bool = False

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
        Concatena variabili ausiliarie di tutti i figli (flat iterativo).
        
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
        
        stack = [self]
        from .segmento_quantistico import SegmentoQuantistico
        
        while stack:
            curr = stack.pop()
            if isinstance(curr, SegmentoQuantistico):
                tau_list.append(curr.tau_locale)
                K_list.append(0.0)  # Placeholder per compatibilità
                closure_list.append(curr.chiusura)
            else:
                stack.extend(reversed(curr.children))
                
        return {
            'tau_locale': np.array(tau_list, dtype=np.float64),
            'contorsione': np.array(K_list, dtype=np.float64),
            'chiusura_spinore': np.array(closure_list, dtype=np.float64)
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
        # Saturazione topologica: max(|χ|)/χ_stable (nessun cap a 1.0).
        # Il segnale fisico e' chi_MAX: e' la singolarita' locale del campo che
        # innesca la transizione Jitterbug, non la media (artefatto statistico).
        # Dalla calibrazione su L2/L3/L4: chi_max/chi_stable raggiunge sqrt(2)
        # esattamente al picco di saturazione (5/8 file, errore < 5%).
        chi_saturation = float(np.max(np.abs(chi_values)) / max(chi_0, 1e-30))

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
        Restituisce la triade Peano-VQT con E_Psi aggregata da TUTTI i livelli.

        E_Psi nel triad = somma ricorsiva su tutta la gerarchia (L1..LN).
        Il drain scatta a L1 dove i chi individuali possono superare sqrt(2)*chi_stable,
        ma il root non vede quei valori (usa medie dei figli diretti).
        Aggregare E_Psi da tutti i livelli e' necessario per osservarlo nell'HDF5.

        Returns None se compute_hamiltonian_coupling() non e' ancora stato chiamato.
        """
        if self._last_triad is None:
            return None
        return EnergyTriad(
            E_chi=self._last_triad.E_chi,
            E_RX=self._last_triad.E_RX,
            E_Psi=self.get_total_E_psi(),
        )

    def get_total_E_psi(self) -> float:
        """
        Somma E_Psi di questo livello + tutti i livelli figli (ricorsiva).

        Complessita' O(N_composites) = O(24^L) — trascurabile rispetto al coupling.
        Necessario perche' il drain Jitterbug scatta a L1 (chi individuali > sqrt(2)*chi0)
        ma il root non vede quei valori: usa solo le medie dei figli diretti (~50 a L3/L4).
        """
        total = self._peano_analyzer.E_psi_total
        for child in self.children:
            if isinstance(child, SolitoneComposito):
                total += child.get_total_E_psi()
        return total
    
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

    # =======================================================================
    # EINSTEIN-CARTAN (additivo, opt-in). NON modifica evolve() legacy.
    # =======================================================================
    def apply_ec_kick(self, dt: float) -> None:
        """Applica il kick di Einstein-Cartan a OGNI blocco L1 dell'albero.

        Su un blocco L1 (figli = SegmentoQuantistico, anello Z_24) calcola le forze EC
        (saturazione settore chi + chiusura 720 settore tau) e le applica come kick
        additivo: vel += F_chi*dt (settore campo), tau_locale += F_tau*dt (settore
        spinoriale). Ricorre nei sotto-compositi per i livelli L>=2.

        Conservativo (le forze sono gradienti di einstein_cartan.ec_energy) e stabile
        (forze limitate). Attivo solo se ec_dynamics_enabled.
        """
        from .segmento_quantistico import SegmentoQuantistico
        from .einstein_cartan import ec_forces, torsion_density_K2
        # EC completo: se la torsione e' sorgentata dallo SPIN, la saturazione/bounce e'
        # gia' applicata sullo spinore (relax_step) -> NON applicare il settore scalare su
        # chi (evita doppio conteggio). La torsione e' tutta dello spin.
        if self.ec_torsion_from_spin:
            for c in self.children:
                if isinstance(c, SolitoneComposito):
                    c.apply_ec_kick(dt)
            return
        if self.children and isinstance(self.children[0], SegmentoQuantistico):
            # blocco L1: i 24 figli sono segmenti
            chi = np.array([c.chi for c in self.children], dtype=float)
            tau = np.array([c.tau_locale for c in self.children], dtype=float)
            W = self.coupling_matrix
            W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            # Muratore ON: la soglia di saturazione si dilata con lo spazio
            # (K2 vs rho**a^2  <=>  K2_fisica vs rho*) -> l'espansione ALLEVIA il
            # bounce. OFF (o a=1): soglia invariata -> EC identico (GATE).
            k2_ref_eff = self.ec_k2_ref_chi
            if self.muratore_enabled:
                k2_ref_eff = self.ec_k2_ref_chi * (self.scale_factor_a ** 2)
            k2_mean = float(np.mean(torsion_density_K2(chi, W)))   # per kink-stiffening
            F_chi, F_tau = ec_forces(chi, tau, W, self.physics.chi_stable,
                                     self._beta_eff(k2_mean), self.ec_kappa_closure,
                                     k2_ref_eff)
            for i, c in enumerate(self.children):
                c.vel += float(F_chi[i]) * dt          # forza EC sul campo
                c.tau_locale += float(F_tau[i]) * dt   # chiusura spinoriale 720
            self._cache_valid = False
        else:
            for c in self.children:
                if isinstance(c, SolitoneComposito):
                    c.apply_ec_kick(dt)

    def evolve_with_ec(self, dt: float, external_force: np.ndarray = None) -> None:
        """Evoluzione con dinamica Einstein-Cartan ADDITIVA (opt-in).

        Strang splitting conservativo: half-kick EC, passo simplettico legacy,
        half-kick EC. NON modifica evolve(): se ec_dynamics_enabled=False e' identico
        a evolve() (path legacy verificato). Propaga il flag ai sotto-compositi.
        """
        if not self.ec_dynamics_enabled:
            self.evolve(dt, external_force)            # legacy puro
            return
        self.apply_ec_kick(0.5 * dt)
        self.evolve(dt, external_force)
        self.apply_ec_kick(0.5 * dt)

    def set_ec_dynamics(self, enabled: bool, beta_sat: float = None,
                        kappa_closure: float = None) -> None:
        """Attiva/disattiva la dinamica EC su TUTTO l'albero (ricorsivo)."""
        from .segmento_quantistico import SegmentoQuantistico
        self.ec_dynamics_enabled = enabled
        if beta_sat is not None:
            self.ec_beta_sat = beta_sat
        if kappa_closure is not None:
            self.ec_kappa_closure = kappa_closure
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.set_ec_dynamics(enabled, beta_sat, kappa_closure)

    def apply_muratore_step(self, dt: float) -> None:
        """Un tick di Planck del MURATORE: OGNI blocco (a ogni livello) espande il
        proprio fattore di scala a in proporzione all'ECCESSO di torsione fisica
        COARSE del suo livello sopra rho*. Auto-regolante (knob-free): riusa
        ec_beta_sat e ec_k2_ref_chi. Attivo solo se muratore_enabled.

        La torsione e' calcolata sulla chi COARSE-GRAINED dei figli (foglia -> chi;
        composito -> chi medio via _get_child_chi): cosi' l'espansione puo' nascere a
        QUALSIASI scala dove la materia si concentra (gradiente coarse tra i figli),
        non solo a L1. -> G(scala) puo' diventare non-monotono dalla dinamica stessa.
        Poi ricorre nei sotto-compositi (che espandono il loro a)."""
        from .segmento_quantistico import SegmentoQuantistico
        from .muratore_planck import hubble_rate, expand
        from .einstein_cartan import torsion_density_K2
        # chi coarse del livello = rappresentativo di ciascun figlio
        chi = np.array([self._get_child_chi(c) for c in self.children], dtype=float)
        W = self.coupling_matrix
        W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
        # TORSIONE: in EC completo viene sorgentata dallo SPIN (vettore di Bloch dello
        # spinore), altrimenti dal gradiente scalare di chi (legacy).
        if (self.ec_torsion_from_spin and self.children
                and isinstance(self.children[0], SegmentoQuantistico)):
            from .motore_chirale_spinoriale import spin_torsion_K2
            theta = np.array([c.theta_spin for c in self.children], dtype=float)
            dphi = np.array([c.dphi_spin for c in self.children], dtype=float)
            K2 = spin_torsion_K2(theta, dphi, W, self.physics.chi_stable)
        else:
            K2 = torsion_density_K2(chi, W)
        k2_mean = float(np.mean(K2))                             # per kink-stiffening
        # (1) BOUNCE locale: relief della torsione in eccesso (K2-rho*)+
        H = hubble_rate(chi, W, self.scale_factor_a,
                        self.ec_k2_ref_chi, self._beta_eff(k2_mean), K2=K2)
        # (2) DRIVE DI FONDO (febbre = motore): emissione di Planck UNIFORME (ogni voxel
        # emette uguale = il bagno/febbre globale, NON la KE locale che traccia la materia),
        # modulata dalla rigidezza: H_fondo = coeff / (1 + K2/rho*). I vuoti (K2 basso)
        # espandono PIENO; la materia (K2 alto) e' soppressa -> i vuoti spingono, la materia
        # si addensa (CLUMPING = gravita'). coeff = tasso di emissione di fondo (~T_eff).
        if self.muratore_h_fondo_coeff > 0.0:
            H += self.muratore_h_fondo_coeff / (1.0 + k2_mean / self.ec_k2_ref_chi)
        self.muratore_H_last = float(H)
        self.scale_factor_a = float(expand(self.scale_factor_a, H, dt))
        # ricorre: anche i sotto-compositi espandono il loro a
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.apply_muratore_step(dt)

    def evolve_with_muratore(self, dt: float, external_force: np.ndarray = None) -> None:
        """Evoluzione con EC + MURATORE (espansione) ADDITIVI (opt-in).

        Se muratore_enabled=False -> evolve_with_ec(dt) (che a sua volta e' legacy se
        EC off): NESSUN effetto. Se ON: prima espande (a cresce dall'eccesso di
        torsione), poi passo EC (la cui soglia di saturazione e' ora dilatata da a:
        l'espansione allevia il bounce). Il muratore richiede l'EC come sorgente."""
        if self.spinore_enabled:
            self.apply_spinore_step(dt)            # rilassa lo spinore (additivo, accanto a chi,v)
        if not self.muratore_enabled:
            self.evolve_with_ec(dt, external_force)
            return
        self.apply_muratore_step(dt)
        self.evolve_with_ec(dt, external_force)

    def set_muratore(self, enabled: bool) -> None:
        """Attiva/disattiva il muratore su TUTTO l'albero (ricorsivo). Abilita anche
        l'EC (la torsione e' la sorgente dell'espansione)."""
        self.muratore_enabled = enabled
        if enabled and not self.ec_dynamics_enabled:
            self.set_ec_dynamics(True)
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.set_muratore(enabled)

    def _beta_eff(self, k2_mean: float = 0.0) -> float:
        """beta_sat EFFETTIVO del blocco (G emergente + kink-stiffening).
        - g_emergent_active: beta = beta_baseline * a^2 = Theta/R_phys (R_phys=R_geo/a^2):
          dove a>1 (espanso) G maggiore.
        - kink_stiffening_active: beta /= (1 + K2/rho*): dove c'e' materia (K2 alto) la
          rigidezza sale e beta cala -> espansione soppressa (i vuoti espandono, la materia
          si addensa = gravita'). Knob-free (usa rho*).
        Flag OFF (o a=1, K2=0) -> beta_baseline (GATE bit-identico)."""
        b = self.ec_beta_sat
        if self.g_emergent_active:
            b = b * (self.scale_factor_a ** 2)
            if self.kink_stiffening_active:
                b = b / (1.0 + k2_mean / self.ec_k2_ref_chi)
        return b

    def set_g_emergent(self, enabled: bool) -> None:
        """Attiva/disattiva la G emergente attiva (beta<-rigidezza fisica) su tutto
        l'albero. Richiede il muratore (a varia)."""
        self.g_emergent_active = enabled
        if enabled and not self.muratore_enabled:
            self.set_muratore(True)
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.set_g_emergent(enabled)

    def set_kink_stiffening(self, enabled: bool) -> None:
        """Attiva/disattiva il kink-stiffening (la materia irrigidisce lo spaziotempo:
        beta /= 1+K2/rho*) su tutto l'albero. Richiede la G emergente (modifica beta)."""
        self.kink_stiffening_active = enabled
        if enabled and not self.g_emergent_active:
            self.set_g_emergent(True)
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.set_kink_stiffening(enabled)

    def set_drive_fondo(self, coeff: float) -> None:
        """Imposta il drive di fondo (febbre = motore di espansione) su tutto l'albero:
        H_fondo = coeff * T_local / (1+K2/rho*). Abilita muratore + kink-stiffening
        (la rigidezza modula il drive -> clumping). coeff=0 -> spento (bit-identico)."""
        self.muratore_h_fondo_coeff = coeff
        if coeff > 0.0:
            if not self.muratore_enabled:
                self.set_muratore(True)
            self.kink_stiffening_active = True
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.set_drive_fondo(coeff)

    def apply_spinore_step(self, dt: float) -> None:
        """Un passo del MOTORE CHIRALE SPINORIALE su ogni blocco L1 (anello di 24): rilassa
        lo spinore (theta = pendenza kink via beta/alpha; dphi = twist 180 + chiusura 720)
        usando il campo chi dei figli. Additivo (non tocca chi,v). Ricorre per L>=2."""
        from .segmento_quantistico import SegmentoQuantistico
        from .motore_chirale_spinoriale import relax_step
        if self.children and isinstance(self.children[0], SegmentoQuantistico):
            chi = np.array([c.chi for c in self.children], dtype=float)
            theta = np.array([c.theta_spin for c in self.children], dtype=float)
            dphi = np.array([c.dphi_spin for c in self.children], dtype=float)
            W = self.coupling_matrix
            W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
            # scale fisiche dal physics (NON hardcoded): chi0, rho*, beta_sat.
            # La saturazione EC sullo spin si attiva con ec_torsion_from_spin (bounce).
            ec = self.ec_torsion_from_spin
            theta, dphi, _ = relax_step(
                theta, dphi, chi, dt, W=(W if ec else None),
                chi0=self.physics.chi_stable, beta_sat=self.ec_beta_sat,
                rho_star=(self.ec_k2_ref_chi if ec else None))
            for i, c in enumerate(self.children):
                c.theta_spin = float(theta[i]); c.dphi_spin = float(dphi[i])
        else:
            for c in self.children:
                if isinstance(c, SolitoneComposito):
                    c.apply_spinore_step(dt)

    def set_spinore(self, enabled: bool) -> None:
        """Attiva/disattiva il motore chirale spinoriale su tutto l'albero. Inizializza
        lo spinore dal campo (theta da |pendenza kink|) quando lo accende."""
        from .segmento_quantistico import SegmentoQuantistico
        from .motore_chirale_spinoriale import init_from_field
        self.spinore_enabled = enabled
        if enabled and self.children and isinstance(self.children[0], SegmentoQuantistico):
            chi = np.array([c.chi for c in self.children], dtype=float)
            theta, dphi = init_from_field(chi, self.physics.chi_stable)
            for i, c in enumerate(self.children):
                c.theta_spin = float(theta[i]); c.dphi_spin = float(dphi[i])
        for c in self.children:
            if isinstance(c, SolitoneComposito):
                c.set_spinore(enabled)

    def set_ec_integrato(self, h_fondo_coeff: float) -> None:
        """EINSTEIN-CARTAN COMPLETAMENTE INTEGRATO: accende lo spinore (spin),
        rende la TORSIONE sorgentata dallo spin (ec_torsion_from_spin), e accende
        l'espansione/gravita' (drive di fondo). Un solo EC: lo spin genera la torsione
        che satura (bounce sullo spin), espande e fa gravita'. Ricorsivo. h_fondo_coeff =
        tasso di emissione di fondo (l'unica scala; le altre sono derivate da chi0)."""
        self.set_spinore(True)
        self.set_drive_fondo(h_fondo_coeff)
        # torsione dallo spin su TUTTO l'albero (ricorsivo)
        def _flag(node):
            node.ec_torsion_from_spin = True
            for c in node.children:
                if isinstance(c, SolitoneComposito):
                    _flag(c)
        _flag(self)

    def get_spinore_state(self) -> dict:
        """Diagnostico spinoriale: winding (->4pi=720), errore beta/alpha vs pendenza kink,
        densita' chirali medie SX (materia)/DX (spazio), norma."""
        from .segmento_quantistico import SegmentoQuantistico
        from .motore_chirale_spinoriale import (spinor_components, chirality_densities,
                                                kink_slope, CLOSURE_4PI)
        windings, slope_errs, sx, dx, norms = [], [], [], [], []
        def walk(n):
            if n.children and isinstance(n.children[0], SegmentoQuantistico):
                chi = np.array([c.chi for c in n.children], dtype=float)
                theta = np.array([c.theta_spin for c in n.children], dtype=float)
                dphi = np.array([c.dphi_spin for c in n.children], dtype=float)
                a, b = spinor_components(theta, dphi)
                rsx, rdx = chirality_densities(theta)
                ratio = np.abs(b) / (np.abs(a) + 1e-12)
                windings.append(float(np.sum(dphi)))
                slope_errs.append(float(np.mean(np.abs(ratio - np.abs(kink_slope(chi, n.physics.chi_stable))))))
                sx.append(float(rsx.mean())); dx.append(float(rdx.mean()))
                norms.append(float(np.max(np.abs(np.abs(a)**2 + np.abs(b)**2 - 1.0))))
            else:
                for c in n.children:
                    if isinstance(c, SolitoneComposito):
                        walk(c)
        walk(self)
        n = max(len(windings), 1)
        return {"winding_mean": float(np.mean(windings)) if windings else 0.0,
                "closure_err_mean": float(np.mean(windings) - CLOSURE_4PI) if windings else 0.0,
                "slope_err_mean": float(np.mean(slope_errs)) if slope_errs else 0.0,
                "rho_sx_mean": float(np.mean(sx)) if sx else 0.0,
                "rho_dx_mean": float(np.mean(dx)) if dx else 0.0,
                "norm_err_max": float(np.max(norms)) if norms else 0.0,
                "n_blocks": len(windings)}

    def get_expansion_state(self) -> dict:
        """Diagnostico dell'espansione PER LIVELLO (a vive a ogni livello). Ritorna
        aggregati globali + per_level[L] = {a_mean, a_max, H_mean, beta} con
        beta(L)=Theta/(R_geo/<a^2>) = (Theta/R_geo)*<a^2> (G emergente, Theta=1).
        Cosi' si vede se G(L) e' monotono o no (task 1). a=1 ovunque -> nessuna espansione."""
        from .segmento_quantistico import SegmentoQuantistico
        from .muratore_planck import voxel_count
        from .rigidezza_geometrica import geometric_rigidity
        W = self.coupling_matrix
        W = (W.toarray() if hasattr(W, "toarray") else np.asarray(W))
        R_geo = geometric_rigidity(W)

        per_lev = {}   # depth -> lists
        vox = [0.0]

        def depth(node):
            if not node.children or isinstance(node.children[0], SegmentoQuantistico):
                return 1
            return 1 + depth(node.children[0])

        def walk(node):
            # registra OGNI composito al suo livello (L1 incluso: depth=1)
            L = depth(node)
            d = per_lev.setdefault(L, {"a": [], "H": []})
            d["a"].append(node.scale_factor_a)
            d["H"].append(node.muratore_H_last)
            vox[0] += voxel_count(node.scale_factor_a, node.muratore_d_f)
            for c in node.children:
                if isinstance(c, SolitoneComposito):
                    walk(c)
        walk(self)

        per_level = {}
        all_a, all_H = [], []
        for L, d in per_lev.items():
            a = np.array(d["a"]); all_a.extend(d["a"]); all_H.extend(d["H"])
            a2m = float((a ** 2).mean())
            per_level[L] = {"a_mean": float(a.mean()), "a_max": float(a.max()),
                            "H_mean": float(np.mean(d["H"])),
                            "beta": a2m / R_geo, "n_blocks": len(d["a"])}
        return {
            "a_mean": float(np.mean(all_a)) if all_a else 1.0,
            "a_max": float(np.max(all_a)) if all_a else 1.0,
            "H_mean": float(np.mean(all_H)) if all_H else 0.0,
            "voxel_total": float(vox[0]),
            "R_geo": R_geo,
            "per_level": per_level,
        }

    def evolve_fast(self, dt: float, external_force: np.ndarray = None) -> None:
        """
        Evoluzione ACCELERATA gerarchica (additiva, NON sostituisce evolve()).

        Struttura IDENTICA a evolve() ma con due differenze sull'integrazione:
          - Foglie L1 (figli = SegmentoQuantistico): un'unica chiamata vettoriale
            FastEvolver (Forest-Ruth) sui 24 segmenti, invece di 24 child.evolve().
          - Livelli L2+ (figli = SolitoneComposito): ricorsione child.evolve_fast().

        Tutto il resto (damping gerarchico, coupling inter-figli, cooling
        Fermi-Dirac, heat transfer, zero-point, drain Peano-VQT via guard,
        cache) e' replicato verbatim da evolve() per equivalenza fisica.

        Verificato dal GATE test_evolve_fast_equivalence.py (evolve vs evolve_fast
        su L2, osservabili collettivi entro 1%). Attivato da un flag a livello
        chiamante: evolve() resta il default invariato.

        Speedup: elimina il loop Python sui segmenti foglia (vero bottleneck L4).
        """
        from .fast_evolver import FastEvolver

        # --- CALCOLO COEFFICIENTE SMORZAMENTO DINAMICO (come evolve) ---
        gamma = self._compute_damping_coefficient()
        self._last_gamma = gamma  # letto da FastEvolver per il damping
        self._cache_valid = False

        # Energia PRIMA evoluzione (triggera drain con guard _triad_step)
        H_before = self.compute_hamiltonian()

        # Aggiorna gamma nei figli (come evolve)
        for child in self.children:
            if isinstance(child, SegmentoQuantistico):
                child.gamma_damping = gamma
            else:
                child._set_damping_recursive(gamma)

        # Forze di accoppiamento inter-figli (riusa la logica esistente)
        internal_forces = self._compute_coupling_forces()

        # Normalizza external_force (come evolve)
        if external_force is None:
            ext_forces_array = np.zeros(self.N_children)
        elif isinstance(external_force, (int, float, np.number)):
            ext_forces_array = np.full(self.N_children, float(external_force))
        else:
            ext_forces_array = np.asarray(external_force)

        children_are_segments = all(
            isinstance(c, SegmentoQuantistico) for c in self.children
        )

        if children_are_segments:
            # --- L1: integrazione vettoriale dei 24 segmenti via FastEvolver ---
            # enable_drain=False: il drain e' gestito qui sopra da compute_hamiltonian
            # (come in evolve), NON da FastEvolver. advance_step_counter=False: il
            # contatore lo incrementa evolve_fast alla fine (evita doppio conteggio).
            fe = getattr(self, "_fast_evolver_cache", None)
            if fe is None:
                fe = FastEvolver(self, dt=dt, method="forest_ruth",
                                 use_spectral_linear=False, enable_drain=False)
                self._fast_evolver_cache = fe
            fe._dt = dt
            total_ext = internal_forces + ext_forces_array
            fe.step(external_force=total_ext, advance_step_counter=False)
        else:
            # --- L2+: ricorsione sui compositi figli ---
            for i, child in enumerate(self.children):
                child.evolve_fast(dt, internal_forces[i] + ext_forces_array[i])

        # --- COOLING TEMPERATURA FERMI-DIRAC (verbatim da evolve) ---
        if self.screening_enabled:
            self.fermi_screener.update_temperature(
                gamma_cooling=self.physics.gamma_cooling, dt=dt
            )

        # --- MISURA ENERGIA RADIATA EFFETTIVA (verbatim da evolve) ---
        self._cache_valid = False
        H_after = self.compute_hamiltonian()
        E_rad_step = H_before - H_after
        self.E_radiated_total += E_rad_step

        # --- TRASFERIMENTO ENERGETICO GERARCHICO (verbatim da evolve) ---
        if E_rad_step > 0 and self.hierarchical_heat_fraction > 0:
            E_transfer = E_rad_step * self.hierarchical_heat_fraction
            self._transfer_heat_to_children(E_transfer, dt)
            self.E_transferred_to_children += E_transfer

        # --- AGGIORNA SPATIAL CACHE (verbatim da evolve) ---
        positions = np.array([child.get_position() for child in self.children])
        chi_values = np.array([self._get_child_chi(child) for child in self.children])
        position_mean = np.mean(positions, axis=0)
        chi_mean = float(np.mean(chi_values))
        chi_std = float(np.std(chi_values))

        self._current_simulation_step += 1
        self.spatial_cache.update(
            position_mean=position_mean, chi_mean=chi_mean,
            chi_std=chi_std, H_total=H_after,
            current_step=self._current_simulation_step
        )
        self._cache_valid = False
        self._centroid = None

        # --- MOTORE ZERO-POINT (verbatim da evolve) ---
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
            self._cache_valid = False

    def _compute_coupling_forces(self) -> np.ndarray:
        """
        Calcola forze di accoppiamento tra figli (vettorizzato).

        F_i = -∂H_coupling/∂χᵢ
            = -∂(kappa·E_coupling + E_exchange)/∂χᵢ
            = -kappa·Σⱼ W_ij·2(χᵢ-χⱼ)
              + λ·α_K·Σⱼ W_ij·sech²(χᵢ/χ₀)·tanh(χⱼ/χ₀)/χ₀
        
        Returns:
        --------
        forces : ndarray, shape (N_children,)
        """
        chi_values = np.array([self._get_child_chi(child) for child in self.children])
        chi_0 = self.physics.chi_stable
        
        chi_diff = chi_values[:, None] - chi_values[None, :]
        tanh_v = np.tanh(chi_values / chi_0)
        sech2_v = 1.0 - tanh_v**2
        exchange_term = sech2_v[:, None] * tanh_v[None, :] / chi_0
        
        W_dense = (self.coupling_matrix.toarray() 
                   if issparse(self.coupling_matrix) 
                   else self.coupling_matrix)

        if not self.screening_enabled:
            # Vettorizzazione forze senza screening
            F_coupling_mat = W_dense * 2 * chi_diff
            F_exchange_mat = -W_dense * exchange_term
            
            F_coupling = np.sum(F_coupling_mat, axis=1)
            F_exchange = np.sum(F_exchange_mat, axis=1)
            
            forces = (-self.physics.kappa_coupling * F_coupling 
                    + self.physics.lambda_exchange * self.physics.alpha_K * F_exchange)
            return np.clip(forces, -1e6, 1e6)
        
        # --- CON SCREENING ADATTIVO (vettorizzato) ---
        rho_local = matvec(np.abs(W_dense), np.abs(chi_values))
        
        agg = self.get_child_aggregates()
        velocities = agg['vel']
        K_squared = agg['k2_mean']
        tau_locale = agg['tau_mean']
        
        delta_v = velocities[:, None] - velocities[None, :]
        delta_K2 = K_squared[:, None] - K_squared[None, :]
        delta_tau = tau_locale[:, None] - tau_locale[None, :]
        
        A_chi = np.exp(-np.abs(chi_diff) / self.physics.sigma_chi)
        A_v = np.exp(-np.abs(delta_v) / self.physics.sigma_velocity)
        A_K = np.exp(-np.abs(delta_K2) / self.physics.sigma_torsion)
        A_tau = np.exp(-np.abs(delta_tau) / self.physics.sigma_tau)
        
        A_density_v = self.fermi_screener.screening_factor(rho_local)
        A_density_mat = (A_density_v[:, None] + A_density_v[None, :]) / 2.0
        
        attenuation_total = A_chi * A_v * A_K * A_tau * A_density_mat
        W_eff = W_dense * attenuation_total
        
        F_coupling_mat = W_eff * 2 * chi_diff
        F_exchange_mat = -W_eff * exchange_term
        
        F_coupling = np.sum(F_coupling_mat, axis=1)
        F_exchange = np.sum(F_exchange_mat, axis=1)
        
        forces = (-self.physics.kappa_coupling * F_coupling 
                + self.physics.lambda_exchange * self.physics.alpha_K * F_exchange)
        return np.clip(forces, -1e6, 1e6)
    
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
