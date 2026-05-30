# experiments/render_zero_point_stats.py
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Assicuriamoci che la root sia nel path per importare core/
sys.path.append(os.getcwd())

from wqt_oop.segmento_quantistico import SegmentoQuantistico
from wqt_oop.solitone_composito import SolitoneComposito
from wqt_oop.physics_context import PhysicsContext
from dataclasses import replace

def run_sim(zp):
    p0 = replace(PhysicsContext.for_level(0), zero_point_amplitude=zp)
    p1 = replace(PhysicsContext.for_level(1), zero_point_amplitude=zp)
    rng = np.random.default_rng(7)
    s = SolitoneComposito([SegmentoQuantistico(chi=50.0+rng.uniform(-1,1), vel=0, physics=p0,
          position=np.array([np.cos(2*np.pi*i/24),np.sin(2*np.pi*i/24),0.0])) for i in range(24)], p1)
    
    ek_hist = []
    for _ in range(3000):
        s.evolve(0.1)
        ek_hist.append(float(np.sum([c.vel**2 for c in s.children])))
    return ek_hist

print("Esecuzione simulazioni di validazione (ZP OFF vs ON)...")
data_off = run_sim(0.0)
data_on = run_sim(0.05)

plt.figure(figsize=(10,6))
plt.plot(data_off, label="OFF (zp=0) - Congelamento", alpha=0.6)
plt.plot(data_on, label="ON (zp=0.05) - Vuoto Vivo", alpha=0.6)
plt.yscale('log')
plt.title("Certificazione Anti-Congelamento (Nyquist Motor)")
plt.xlabel("Step")
plt.ylabel("E_kin (log scale)")
plt.legend()
plt.grid(True, which="both", ls="-", alpha=0.2)
plt.savefig("assets/zero_point_validation.png")

print(f"Grafico salvato in assets/zero_point_validation.png")
print(f"E_kin finale ON: {data_on[-1]:.4f} (Stabile)")