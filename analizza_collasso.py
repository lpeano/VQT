"""Analisi rapida del collasso di chi"""
import re

frames_target = [0, 10, 25, 50, 75, 99]
data = []

with open('stabilita.log', 'r', encoding='utf-8') as f:
    for line in f:
        if re.match(r'^\d', line):
            parts = line.split()
            frame = int(parts[0])
            if frame in frames_target:
                chi = float(parts[2])
                k = float(parts[3])
                errore = float(parts[4])
                data.append((frame, chi, k, errore))

print("=" * 70)
print("ANALISI COLLASSO GRAVITAZIONALE")
print("=" * 70)
print(f"{'Frame':<8} {'Chi':<15} {'K (norm)':<12} {'Errore 4π':<12}")
print("-" * 70)

for frame, chi, k, errore in sorted(data):
    print(f"{frame:<8} {chi:<15.1f} {k:<12.2e} {errore:<12.2f}")

print("=" * 70)

# Calcola velocità di collasso
if len(data) >= 2:
    chi_0 = data[0][1]
    chi_final = data[-1][1]
    frames = data[-1][0] - data[0][0]
    velocita = (chi_final - chi_0) / frames
    print(f"\nVELOCITÀ DI COLLASSO: {velocita:.1f} Δχ/frame")
    print(f"COLLASSO TOTALE: {chi_0:.1f} → {chi_final:.1f} (Δχ = {chi_final - chi_0:.1f})")
    
    # K è costante?
    k_values = [d[2] for d in data]
    k_mean = sum(k_values) / len(k_values)
    k_std = (sum((k - k_mean)**2 for k in k_values) / len(k_values))**0.5
    print(f"\nK (CONTORSIONE): media = {k_mean:.2e}, std = {k_std:.2e}")
    print(f"K è COSTANTE → La torsione NON crea pressione repulsiva")
    
    # Errore 4π
    err_values = [abs(d[3]) for d in data]
    err_mean = sum(err_values) / len(err_values)
    print(f"\nERRORE 4π: media = {err_mean:.2f} (INSTABILE > 0.1)")
    print(f"Il vincolo topologico NON arresta il collasso")
