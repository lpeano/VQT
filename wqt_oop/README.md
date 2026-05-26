# WQT_OOP - Weyl Quantum Topology Framework

**Object-Oriented Framework per Simulazioni Cosmologiche Multi-Livello**

[![Tests](https://img.shields.io/badge/tests-13%2F13_passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.13-blue)]()
[![Architecture](https://img.shields.io/badge/architecture-production_ready-success)]()

---

## 🎯 Quick Start

```bash
# Test suite completo (13 tests)
python -m wqt_oop.test_suite_completo

# Run simulazione L1 (24 segmenti, 1000 steps)
python -m wqt_oop.run_cosmology --level 1 --steps 1000

# Run simulazione L2 (576 segmenti, monitoring verbose)
python -m wqt_oop.run_cosmology --level 2 --steps 5000 --verbose
```

---

## 📦 Moduli Principali

| Modulo | Descrizione | Status |
|--------|-------------|--------|
| `fermi_dirac_screening.py` | Screening continuo Fermi-Dirac | ✅ PROD |
| `spatial_hash_grid.py` | O(N log N) neighbor search | ✅ PROD |
| `spatial_cache.py` | Mean-field caching | ✅ PROD |
| `energy_drift_observer.py` | Real-time monitoring | ✅ PROD |
| `fractal_universe_factory.py` | Recursive universe generation | ✅ PROD |
| `run_cosmology.py` | CLI entry point | ✅ PROD |
| `solitone_composito.py` | Composite soliton (24+) | ✅ PROD |
| `segmento_quantistico.py` | Quantum segment (L0) | ✅ PROD |
| `physics_context.py` | Immutable physics config | ✅ PROD |

---

## 🏗️ Architettura

### Gerarchia Frattale
```
Level 0 (L0): SegmentoQuantistico      →  1 segment   (2 DOF)
Level 1 (L1): SolitoneComposito        →  24 segments (48 DOF)
Level 2 (L2): MacroSolitone            →  576 segments
Level 3 (L3): GigaSolitone             →  13,824 segments
Level N (Ln): UniverseSolitone         →  24^N segments
```

### Pattern Design
- **Composite:** Struttura ricorsiva solitoni
- **Factory:** Generazione automatica universi
- **Observer:** Monitoring drift energetico
- **Strategy:** Screening intercambiabile (Fermi-Dirac, exponential, ...)

---

## 🔬 Fisica Implementata

### 1. Fermi-Dirac Screening
Sostituzione screening discreto (exp) con distribuzione quantistica continua:

```python
f(χ) = 1 / (exp((χ - μ)/T) + 1)
```

- **μ (mu_fermi):** Potenziale chimico (threshold transizione)
- **T (T_fermi):** Temperatura efficace (larghezza transizione)
- **Cooling:** T(t) = T₀ · exp(-γt)

### 2. Hamiltoniano Composito
```
H_total = H_internal + H_coupling + H_inter

H_internal = Σᵢ [½mᵢvᵢ² + V(χᵢ)]
H_coupling = κ·Σᵢⱼ Wᵢⱼ·(χᵢ - χⱼ)²
H_inter = λ·Σᵢⱼ Wᵢⱼ·tanh(χᵢ/χ₀)·tanh(χⱼ/χ₀)
```

### 3. Conservazione Energia
- **Target:** |dH/dt| < 10⁻³
- **Validato:** drift = 6.5×10⁻⁴ (100 steps, dt=0.005)
- **Emergency stop:** drift > 0.1 → terminazione automatica

---

## ⚡ Performance

### Scaling O(N² → N log N)
Spatial hashing riduce complessità interazioni:

| N Solitons | Naive O(N²) | Spatial Hash O(N log N) | Speedup |
|------------|-------------|-------------------------|---------|
| 100        | 1 ms        | 0.5 ms                  | 2x      |
| 1,000      | 100 ms      | 5 ms                    | 20x     |
| 10,000     | 10 s        | 50 ms                   | 200x    |
| 100,000    | 16 min      | 500 ms                  | 2000x   |

**Benchmark (test_suite_completo):**
- Build 1000 solitons: **9.6 ms**
- Query 30 neighbors: **0.7 ms**

### Memory Scaling
```python
Memory(L) ≈ 20 bytes × 24^L

L1: 0.5 MB
L2: 12 MB
L3: 288 MB
L4: 6.9 GB
L5: 166 GB
```

---

## 🧪 Test Suite

```bash
python -m wqt_oop.test_suite_completo
```

**Coverage:**
1. ✅ Fermi-Dirac distribution (f(μ), f(μ±5T), cooling)
2. ✅ Energy conservation (drift < 0.01)
3. ✅ Spatial hash performance (build, query)
4. ✅ Spatial cache (hit/miss, auto-invalidation)
5. ✅ Observer pattern (alert triggering)
6. ✅ Factory integration (L1 creation, evolution)

**Status:** 13/13 PASSING ✅

---

## 📖 Documentazione

- **[ARCHITETTURA_SCALING_MASSIMO.md](../docs/ARCHITETTURA_SCALING_MASSIVO.md):** Documentazione completa architettura
- **[REFACTORING_FERMI_DIRAC.md](../REFACTORING_FERMI_DIRAC.md):** Dettagli screening Fermi-Dirac
- **[INTEGRAZIONE_COMPLETATA.md](../INTEGRAZIONE_COMPLETATA.md):** Storia integrazione framework
- **[GUIDA_MIGRAZIONE.md](../GUIDA_MIGRAZIONE.md):** Migrazione da discrete → continuous

---

## 🚀 Advanced Usage

### Python API
```python
from wqt_oop.fractal_universe_factory import FractalUniverseFactory, UniverseConfig
from wqt_oop.run_cosmology import CosmologySimulation
from wqt_oop.energy_drift_observer import (
    EnergyDriftMonitor, StatisticsLogger, ProgressTracker
)

# Configuration
config = UniverseConfig(
    target_level=2,
    chi_mean=50.0,
    chi_std=5.0,
    spatial_extent=100.0,
    seed=42,
    enable_fermi_screening=True,
    enable_spatial_cache=True
)

# Create universe
factory = FractalUniverseFactory()
universe = factory.create_universe(config)

# Setup simulation
sim = CosmologySimulation(
    universe=universe,
    dt=0.01,
    enable_spatial_hash=True
)

# Attach observers
sim.attach(EnergyDriftMonitor(warning_threshold=1e-3))
sim.attach(StatisticsLogger(log_interval=100))
sim.attach(ProgressTracker(total_steps=1000))

# Run
sim.run(total_steps=1000)

# Get final state
stats = universe.get_occupazione_stati()
print(f"Polarizzazione: {stats['polarizzazione']:.3f}")
print(f"T_eff: {stats['T_eff']:.3e}")
```

### Custom Physics
```python
from wqt_oop.physics_context import PhysicsContext

# Custom Fermi-Dirac parameters
physics = PhysicsContext(
    level=1,
    length_scale=1.0e-10,
    mu_fermi=100.0,      # Higher chemical potential
    T_fermi=10.0,        # Softer transition
    gamma_cooling=0.05,  # Faster cooling
    alpha_K=0.01,        # Weak coupling
    kappa_coupling=0.01
)
```

---

## 🛠️ CLI Reference

```bash
python -m wqt_oop.run_cosmology [OPTIONS]

OPTIONS:
  --level, -l INT           Target fractal level (0-5) [default: 2]
  --steps, -n INT           Total integration steps [default: 1000]
  --dt FLOAT                Timestep [s] [default: 0.01]
  --chi-mean FLOAT          Mean chi field value [default: 50.0]
  --chi-std FLOAT           Chi standard deviation [default: 5.0]
  --spatial-extent FLOAT    Spatial box size [m] [default: 100.0]
  --enable-spatial-hash     Enable O(N log N) optimization [default: True]
  --log-interval INT        Log every N steps [default: 100]
  --drift-warning FLOAT     WARNING threshold [default: 1e-3]
  --drift-critical FLOAT    CRITICAL threshold [default: 1e-2]
  --output, -o PATH         Output HDF5 file [optional]
  --seed INT                Random seed [default: 42]
  --verbose, -v             Verbose logging
```

### Examples
```bash
# Quick test (L1, 100 steps)
python -m wqt_oop.run_cosmology --level 1 --steps 100

# Production run (L2, 10k steps, monitoring)
python -m wqt_oop.run_cosmology \
  --level 2 \
  --steps 10000 \
  --dt 0.005 \
  --log-interval 500 \
  --verbose

# High precision (small dt, tight drift tolerance)
python -m wqt_oop.run_cosmology \
  --level 1 \
  --steps 5000 \
  --dt 0.001 \
  --drift-warning 1e-4 \
  --drift-critical 1e-3
```

---

## 🔍 Troubleshooting

### ImportError: No module named 'wqt_oop'
```bash
# Run from project root
cd c:\Users\lpeano\plank\VQT
python -m wqt_oop.test_suite_completo
```

### Drift Too High
```python
# Reduce coupling constants
physics = PhysicsContext(
    level=1,
    length_scale=1e-10,
    alpha_K=0.01,      # Was 1.0
    kappa_coupling=0.01 # Was 0.25
)

# Reduce timestep
sim.dt = 0.001  # Was 0.01
```

### Memory Overflow (L4+)
```bash
# Enable spatial hash (REQUIRED for L3+)
python -m wqt_oop.run_cosmology --level 4 --enable-spatial-hash
```

### Slow Performance
```bash
# Check spatial hash is enabled
--enable-spatial-hash

# Increase log interval (reduce I/O)
--log-interval 1000

# Disable verbose logging
# (remove --verbose flag)
```

---

## 📊 Benchmark Results

**Test System:** Windows 11, Python 3.13

| Test | Result | Status |
|------|--------|--------|
| Fermi f(μ) = 0.5 | 0.500000 | ✅ |
| Fermi f(μ-5T) ~ 0.993 | 0.993307 | ✅ |
| Energy drift < 0.01 | 6.527e-04 | ✅ |
| Spatial hash build (1k) | 9.59 ms | ✅ |
| Spatial hash query | 0.681 ms | ✅ |
| Cache hit (age=1) | 100% | ✅ |
| Observer WARNING trigger | YES | ✅ |
| Factory L1 creation | 1 ms | ✅ |

---

## 🤝 Contributing

### Running Tests
```bash
# Full test suite
python -m wqt_oop.test_suite_completo

# Individual modules
python -m wqt_oop.validate_fermi
python -m wqt_oop.spatial_hash_grid
python -m wqt_oop.spatial_cache
python -m wqt_oop.energy_drift_observer
```

### Code Style
- Follow PEP 8
- Type hints obbligatori
- Docstrings stile NumPy
- Test coverage > 90%

---

## 📜 License

[Your License Here]

---

## 📧 Contact

**Development Team:** [Your Team]  
**Issues:** [GitHub Issues URL]  
**Docs:** [Documentation URL]  

---

**Built with ❤️ for Quantum Cosmology**
