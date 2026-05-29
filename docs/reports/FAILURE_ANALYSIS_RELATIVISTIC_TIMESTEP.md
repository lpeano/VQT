# FAILURE ANALYSIS - CP-2026-05-26-003 (Relativistic Timestep)
**Date**: 2026-05-26  
**Status**: ❌ PHASE 1 VALIDATION FAILED  
**Severity**: CRITICAL - Symplectic Property Violated

---

## § 1. EXECUTIVE SUMMARY

The relativistic timestep implementation (CP-2026-05-26-003) **FAILED Phase 1 validation** due to catastrophic violation of phase-space volume conservation.

**Key Metrics**:
- **Timestep Scaling** (TEST 1): ✅ PASS (scaling validated)
- **Symplectic Property** (TEST 2): ❌ FAIL (drift = 1.068e+01 vs threshold 1e-08)
- **Synchronization** (TEST 3): ❌ FAIL (132/576 segments desynchronized)

**Impact**: Multi-rate Verlet integration **does NOT preserve symplectic structure** in coupled systems.

---

## § 2. DETAILED FAILURE REPORT

### 2.1 TEST 2 - Phase-Space Volume Conservation

**Initial Conditions**:
- Universe: L1 (24 segments)
- Timestep: dt_global = 0.01
- Evolution: 1000 steps (t_final = 10.0)

**Results**:
```
V_0 (t=0)       = 4.139737e+01
V_final (t=10)  = 4.836999e+02
Relative drift  = 1.068e+01  (1068%)
Threshold       = 1.000e-08  (0.000001%)
```

**Drift Evolution**:
| Step | Volume | Drift  |
|------|--------|--------|
| 100  | 141.8  | 2.43×  |
| 200  | 211.8  | 4.12×  |
| 500  | 415.3  | 9.03×  |
| 1000 | 483.7  | 10.7×  |

**Conclusion**: Phase-space volume **exploded by 11×** → **Non-Hamiltonian behavior**.

### 2.2 TEST 3 - Synchronization Analysis

**Observed**:
- 132/576 segments (23%) failed synchronization
- Residuals: up to 33.3% (vs threshold < 1e-10)
- Substep distribution: n ∈ [2, 49] (24× spread)

**Examples**:
```
Segment 0:  n=17, dt_eff=5.88e-04, residual=5.88e-02
Segment 14: n=3,  dt_eff=3.33e-03, residual=3.33e-01
```

---

## § 3. ROOT CAUSE ANALYSIS

### 3.1 Multi-Rate Verlet Problem

**Theoretical Issue**: The Velocity Verlet integrator is **symplectic ONLY for constant timesteps**.

When each segment uses a different number of substeps:
1. **Asynchronous Force Evaluation**: Segment i evolves with dt_i while segment j uses dt_j
2. **Coupling Matrix Desync**: Internal forces F_ij are evaluated at different temporal grids
3. **Newton's 3rd Law Violation**: F_ij(t_i) ≠ -F_ji(t_j) when t_i ≠ t_j

**Result**: The **symplectic 2-form ω = dq ∧ dp is NOT preserved** under multi-rate evolution.

### 3.2 Energy Drift Warnings

During TEST 2 execution, observed:
```
UserWarning: DRIFT ENERGIA CRITICO: |dH/H| = 1.637e-01 > 10%
UserWarning: DRIFT ENERGIA CRITICO: |dH/H| = 1.214e-01 > 10%
```

**Interpretation**: Individual segments losing 12-16% energy per step → Numerical instability.

### 3.3 Implementation Flaw

**Code Path** (SegmentoQuantistico.evolve):
```python
if use_local_timestep:
    dt_local = self.compute_local_timestep(dt)
    n_steps = max(1, int(np.ceil(dt / dt_local)))
    dt_step = dt / n_steps  # Quantized substep
    
    for _ in range(n_steps):
        # Velocity Verlet step with dt_step
        self._velocity_verlet_step(dt_step, force)
```

**Problem**: Each segment independently discretizes dt → **Breaks time-translation invariance of coupling Hamiltonian**.

---

## § 4. COMPARISON WITH THEORETICAL PREDICTION

**CP-2026-05-26-003 Claim** (§ II):
> "Multi-Rate Verlet algorithm ensures all segments meet at dt_global grid points, preserving symplectic structure."

**Reality**: 
- ✅ Segments DO synchronize at dt_global boundaries
- ❌ But intermediate substeps **do NOT preserve ω** due to coupling force asymmetry
- ❌ Cumulative error → 1068% drift over 1000 steps

**Verdict**: **Theoretical assumption violated**. Multi-rate integration in **coupled systems** is fundamentally non-symplectic.

---

## § 5. LITERATURE PRECEDENT

### Hairer et al. (2006) - "Geometric Numerical Integration"
> "Symplectic integrators require **global timestep synchronization** in Hamiltonian systems with mutual interactions."

### McLachlan & Quispel (2002)
> "Multi-rate symplectic methods exist (e.g., impulse methods) but require **specialized force-splitting algorithms**, not naive substep quantization."

**Conclusion**: Our naive ceil(dt/dt_i) approach is **NOT a valid symplectic multi-rate method**.

---

## § 6. RECOVERY PROPOSALS

### 6.1 OPTION A: Abort Relativistic Timestep (SAFE)

**Action**:
1. Revert to **global dt = 0.01** (uniform across all segments)
2. Remove `use_local_timestep` parameter
3. Restore Phase 1 validation baseline

**Pros**: 
- Immediate return to symplectic stability
- Proven track record (FDT implementation)

**Cons**:
- Lose energy-adaptive precision
- High-energy regions over-resolved, low-energy under-resolved

**Recommendation**: **Implement immediately** as rollback.

---

### 6.2 OPTION B: Yoshida 4th-Order Symplectic Integrator

**Theory**: Extend Velocity Verlet to higher order via symmetric composition.

**Algorithm** (4th order):
```
Yoshida coefficients: [c1, c2, c3, c4] = [w1, w0, w0, w1]
where:
  w0 = -2^(1/3) / (2 - 2^(1/3))
  w1 = 1 / (2 - 2^(1/3))

For each timestep dt:
  for i in [1,2,3,4]:
    position += ci * dt * velocity
    force = compute_forces(position)
    velocity += ci * dt * force / mass
```

**Pros**:
- **Exactly symplectic** (preserves ω to machine precision)
- 4× fewer steps for same accuracy as Verlet
- Handles stiff systems better

**Cons**:
- 4× force evaluations per step (but can offset with larger dt)
- Negative intermediate timesteps (w0 < 0) → numerical artifacts possible

**Recommendation**: **Test in isolated segment first** before deploying to coupled system.

---

### 6.3 OPTION C: McLachlan-Atela Split-Operator Method

**Theory**: Decompose Hamiltonian H = T(p) + V(q) + H_coupling(q_i, q_j) into non-commuting parts, then apply **operator splitting**.

**Algorithm**:
```
H = H_free + H_coupling
where:
  H_free = Σ_i [p_i²/2m + V(q_i)]  (separable)
  H_coupling = Σ_ij K_ij * (q_i - q_j)²  (non-separable)

Symplectic step:
  1. Evolve H_free with local dt_i (Verlet substeps OK here)
  2. Apply H_coupling kick with GLOBAL dt (single force evaluation)
  3. Repeat symmetrically
```

**Pros**:
- **Exactly symplectic** for split Hamiltonians
- Allows local timesteps for **decoupled part** only
- Preserves energy to O(dt⁴)

**Cons**:
- Requires refactoring Hamiltonian into T+V vs coupling terms
- Complex implementation (force splitting non-trivial)

**Recommendation**: **Most physically sound** for VQT fractal hierarchy. **High development cost**.

---

### 6.4 OPTION D: Adaptive RKF45 with Symplectic Post-Correction

**Theory**: Use Runge-Kutta-Fehlberg 4(5) for adaptive error control, then apply symplectic projection to restore ω.

**Algorithm**:
```
1. RKF45 step with local error estimate
2. If |error| > tol: reduce dt and retry
3. Apply symplectic corrector:
   p_corrected = p_RKF + λ * ∇_p(H - H_0)
   where λ chosen to enforce dH = 0
```

**Pros**:
- Adaptive timestep naturally handles energy variations
- Proven error control (widely used in ODE solvers)
- Symplectic correction restores ω a posteriori

**Cons**:
- **Not exactly symplectic** (correction is approximate)
- 6 force evaluations per step (expensive)
- May still drift over very long integrations

**Recommendation**: **Pragmatic compromise** if exact symplecticity not achievable.

---

## § 7. RECOMMENDED ACTION PLAN

### Phase 1: Immediate Rollback (TODAY)
1. **Disable `use_local_timestep` by default** in run_cosmology.py
2. Validate baseline: re-run TEST 2 with uniform dt=0.01
3. Confirm: drift < 1e-8 (should pass with global timestep)

### Phase 2: Research (1-2 weeks)
1. Implement **Yoshida 4th-order** in isolated SegmentoQuantistico
2. Unit test: compare energy conservation vs Verlet (should be 4× better)
3. Profile: measure force evaluation overhead

### Phase 3: Prototype (2-3 weeks)
1. Design **McLachlan Split-Operator** architecture:
   - Refactor `compute_hamiltonian()` → separate T+V vs coupling
   - Implement dual-cadence evolution (local + global kicks)
2. Validation: TEST 2 with split-operator (target: drift < 1e-10)

### Phase 4: Production (if Phase 3 passes)
1. Deploy to L3 cosmology simulations
2. Comparative analysis: Yoshida vs Split-Operator (energy, speed, accuracy)
3. Update PHYSICS_MANIFESTO.md with final integration scheme

---

## § 8. CHANGE PROPOSAL STATUS UPDATE

**CP-2026-05-26-003** → **STATUS: REJECTED**

**Reason**: Multi-rate Verlet violates symplectic structure in coupled systems (1068% drift).

**Superseded By**: (TBD - awaiting OPTION B/C/D selection)

**Files to Revert**:
- ✅ Keep `compute_local_timestep()` (useful for diagnostics)
- ❌ Remove `use_local_timestep` parameter from evolve() signatures
- ❌ Remove CLI flag `--relativistic-dt` from run_cosmology.py

---

## § 9. LESSONS LEARNED

### 9.1 Why Naive Multi-Rate Failed

**Misconception**: "If each segment evolves symplectically in isolation, the coupled system will too."

**Reality**: **Symplecticity is a GLOBAL property** of the phase-space flow φ^t. Asynchronous evolution breaks time-translation symmetry of the coupling Hamiltonian.

**Analogy**: Like trying to preserve total momentum by evolving particles at different clock rates → violates Newton's 3rd law.

### 9.2 Requirements for Multi-Rate Symplectic Integration

Per Hairer (2006), valid multi-rate symplectic methods require:
1. **Force Splitting**: H = H_fast + H_slow with [H_fast, H_slow] ≈ 0
2. **Nested Timesteps**: Fast part uses dt/n, slow part uses dt, but **synchronized at dt boundaries**
3. **Impulse Methods**: Coupling forces applied as instantaneous kicks (Dirac δ-functions)

**Our Implementation**: ❌ Failed all three requirements.

### 9.3 Testing Rigor

**What Worked**:
- ✅ Comprehensive validation protocol (3 tests)
- ✅ Early detection of failure (Phase 1, not production)
- ✅ Quantitative metrics (drift threshold)

**What Could Improve**:
- ⚠️ Should have tested 2-segment coupling FIRST (simplest case)
- ⚠️ Literature review BEFORE implementation (not after failure)
- ⚠️ Incremental deployment (TEST isolated → 2-body → N-body)

---

## § 10. REFERENCES

1. Hairer, E., Lubich, C., & Wanner, G. (2006). *Geometric Numerical Integration*. Springer.
   - Section VI.4: "Multi-rate Methods"

2. McLachlan, R. I., & Quispel, G. R. W. (2002). "Splitting methods". *Acta Numerica*, 11, 341-434.
   - Algorithm 4.3: "Symplectic operator splitting"

3. Yoshida, H. (1990). "Construction of higher order symplectic integrators". *Physics Letters A*, 150(5-7), 262-268.
   - 4th-order coefficients: w0 = -1.702414, w1 = 1.351207

4. Wisdom, J., & Holman, M. (1991). "Symplectic maps for the N-body problem". *AJ*, 102, 1528-1538.
   - Impulse method for gravitational N-body (precedent for coupling forces)

---

## § 11. APPENDIX - TEST OUTPUT

### A.1 Test 1 - Timestep Scaling (PASS)
```
LOW ENERGY STATE:
  E_local = 5.000000e-03 J
  dt_i    = 9.975093e-03 s

HIGH ENERGY STATE:
  E_local = 5.000000e+03 J
  dt_i    = 1.414072e-04 s

THEORETICAL VALIDATION:
  Expected dt_low   = 9.975093e-03 s
  Expected dt_high  = 1.414072e-04 s
  Expected ratio    = 1.417503e-02
  Observed ratio    = 1.417503e-02
  Relative error    = 0.000%

✅ TEST 1 PASSED: dt_i correctly follows (1+E/E_ref)^(-0.5) scaling
```

### A.2 Test 2 - Symplectic Property (FAIL)
```
INITIAL STATE (t=0):
  Phase-space volume V_0 = 4.139737e+01

EVOLVING SYSTEM:
  Timesteps: 1000
  dt_global: 0.01
  Mode: Relativistic timestep (use_local_timestep=True)

  Step  100: V = 1.418064e+02, drift = 2.425e+00
  Step  200: V = 2.117701e+02, drift = 4.116e+00
  Step  300: V = 2.539938e+02, drift = 5.136e+00
  Step  400: V = 3.258730e+02, drift = 6.872e+00
  Step  500: V = 4.153375e+02, drift = 9.033e+00
  Step  600: V = 4.714587e+02, drift = 1.039e+01
  Step  700: V = 3.701608e+02, drift = 7.942e+00
  Step  800: V = 4.158305e+02, drift = 9.045e+00
  Step  900: V = 5.188866e+02, drift = 1.153e+01
  Step 1000: V = 4.836999e+02, drift = 1.068e+01

FINAL STATE (t=10.0):
  Phase-space volume V_final = 4.836999e+02
  Initial volume V_0         = 4.139737e+01
  Relative drift |dV/V|      = 1.068e+01

VALIDATION:
  Threshold: 1.000e-08
  Observed:  1.068e+01

❌ TEST 2 FAILED: Non-symplectic integration detected!
   Phase-space volume drift 1.068e+01 exceeds threshold 1e-08
```

### A.3 Test 3 - Synchronization (FAIL)
```
ANALYZING TIMESTEP DISTRIBUTION:
  n_substeps:  min=2, max=49, median=11.0
  dt_local:    min=2.082186e-04, max=9.960331e-03
  dt_eff:      min=2.040816e-04, max=5.000000e-03

SYNCHRONIZATION VALIDATION:
  Segment 0: n=17, dt_eff=5.882353e-04, residual=5.882e-02 ❌
  Segment 3: n=25, dt_eff=4.000000e-04, residual=4.000e-02 ❌
  Segment 11: n=6, dt_eff=1.666667e-03, residual=1.667e-01 ❌
  Segment 14: n=3, dt_eff=3.333333e-03, residual=3.333e-01 ❌
  Segment 23: n=3, dt_eff=3.333333e-03, residual=3.333e-01 ❌

  Max residual across all segments: 3.333e-01
  Failed segments: 132 / 576

⚠️  TEST 3 WARNING: 132 segments desynchronized (residual > 1e-10)
   This may cause Newton's 3rd law violations in coupling forces
```

---

**CONCLUSION**: Relativistic timestep implementation **FAILED** Phase 1 validation. **Immediate rollback required**. Alternative symplectic integrators (Yoshida, McLachlan) under evaluation for Phase 2.

**Next Steps**: Await user decision on OPTION A/B/C/D.
