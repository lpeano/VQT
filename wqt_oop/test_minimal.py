"""Test minimale per diagnosticare bug conservazione carica topologica."""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wqt_oop.physics_context import PhysicsContext
from wqt_oop.segmento_quantistico import SegmentoQuantistico

# Test singolo segmento
print("=== TEST SINGOLO SEGMENTO ===\n")

physics = PhysicsContext.for_level(0)
seg = SegmentoQuantistico(chi=4.5, vel=1.0, physics=physics)

print(f"Stato iniziale:")
print(f"  chi = {seg.chi:.6f}")
print(f"  vel = {seg.vel:.6f}")
print(f"  H   = {seg.energia_totale:.6e}")
print(f"  Q   = {seg.get_topology_charge():.6f}")
print(f"  [DEBUG] Q dovrebbe essere uguale a chi: {seg.chi:.6f}")
print(f"  [DEBUG] Differenza Q-chi: {abs(seg.get_topology_charge() - seg.chi):.6e}")

# Evoluzione 10 passi CON DIAGNOSTICA
dt = 0.1
for step in range(10):
    seg.evolve(dt)
    if step % 2 == 0:
        print(f"\nStep {step}:")
        print(f"  chi = {seg.chi:.6f}")
        print(f"  vel = {seg.vel:.6f}")
        print(f"  H   = {seg.energia_totale:.6e}")
        print(f"  Q   = {seg.get_topology_charge():.6f}")

print(f"\n{'='*50}")
print("DIAGNOSI: Q = chi cambia durante evoluzione")
print("Questo è CORRETTO se chi è il campo dinamico.")
print("La carica topologica conservata è Σχᵢ,")
print("non i χᵢ individuali!")
print(f"{'='*50}")
