"""Analisi ordine di grandezza dei termini di pressione"""
import numpy as np

# Valori tipici dalla simulazione
chi = -60000
contorsione_k = 2.211e-3
COEFFICIENTE_ACCOPPIAMENTO = 24 / 2400
ACCORCIAMENTO_ANGOLARE = 4 * np.pi / 24
segmenti_frattali = 24
LUNGHEZZA_PLANCK_METRI = 1.616255e-35

# Ricostruisco i calcoli dalla funzione
log_r_dx = 150.0 * np.tanh(chi / 150.0)  # Saturazione
r_conforme = float(segmenti_frattali) * ACCORCIAMENTO_ANGOLARE * np.exp(log_r_dx * COEFFICIENTE_ACCOPPIAMENTO)
r_conforme = np.maximum(r_conforme, 1.0 * LUNGHEZZA_PLANCK_METRI)
accoppiamento_topologico = 1.0 / (r_conforme**2 + 1e-6)

# Termini di pressione
KAPPA_SPIN = 2.0
pressione_repulsione_spin = KAPPA_SPIN * contorsione_k**2 * accoppiamento_topologico
correzione_curvatura_contorsione = contorsione_k**2 * accoppiamento_topologico
densita_energia_contorsione = correzione_curvatura_contorsione

# Stima altri termini (assumendo densità tipiche)
mu_dx_tipico = 1e3  # Ordine di grandezza stimato
mu_sx_tipico = 1e3
tensione_taglio_tipico = 1e4
energia_torsionale_tipico = 1e2
scatolamento = 2.0

densita_materia = (mu_sx_tipico - mu_dx_tipico) * scatolamento
tensione_newtoniana = tensione_taglio_tipico * accoppiamento_topologico
densita_torsione_quadratica = (tensione_taglio_tipico**2 + energia_torsionale_tipico**2) * accoppiamento_topologico

print("=" * 80)
print("ANALISI ORDINE DI GRANDEZZA - TERMINI DI PRESSIONE")
print("=" * 80)
print(f"\nPARAMETRI GEOMETRICI:")
print(f"  χ = {chi:.1f}")
print(f"  K (contorsione) = {contorsione_k:.3e}")
print(f"  r_conforme = {r_conforme:.3e} m")
print(f"  accoppiamento_topologico (1/r²) = {accoppiamento_topologico:.3e}")

print(f"\n{'TERMINE':<40} {'VALORE':<15} {'SEGNO':<10}")
print("-" * 80)

# Termini attrattivi (negativi nella pressione)
print(f"{'densita_materia':<40} {abs(densita_materia):<15.3e} {'NEUTRO':<10}")
print(f"{'tensione_newtoniana':<40} {abs(tensione_newtoniana):<15.3e} {'ATTRATTIVO':<10}")
print(f"{'densita_torsione_quadratica':<40} {abs(densita_torsione_quadratica):<15.3e} {'ATTRATTIVO':<10}")
print(f"{'densita_energia_contorsione':<40} {abs(densita_energia_contorsione):<15.3e} {'ATTRATTIVO':<10}")

print("-" * 80)
# Termine repulsivo (positivo nella pressione)
print(f"{'pressione_repulsione_spin (★ NUOVO)':<40} {abs(pressione_repulsione_spin):<15.3e} {'REPULSIVO':<10}")
print("=" * 80)

# Rapporto critico
rapporto_repulsione_attrattivo = pressione_repulsione_spin / densita_torsione_quadratica
print(f"\nRAPPORTO CRITICO:")
print(f"  Repulsione / Attrazione = {rapporto_repulsione_attrattivo:.3e}")
print(f"\n⚠️  PROBLEMA IDENTIFICATO:")

if abs(rapporto_repulsione_attrattivo) < 0.01:
    print(f"  La repulsione è {1/abs(rapporto_repulsione_attrattivo):.0f}x PIÙ DEBOLE dell'attrazione!")
    print(f"  Il termine è COMPLETAMENTE TRASCURABILE.")
    
    # Calcolo KAPPA_SPIN necessario
    kappa_necessario = KAPPA_SPIN * (1.0 / abs(rapporto_repulsione_attrattivo))
    print(f"\n💡 SOLUZIONE:")
    print(f"  Per bilanciare l'attrazione, serve:")
    print(f"  KAPPA_SPIN ≈ {kappa_necessario:.1e} (attualmente: {KAPPA_SPIN})")
    
print("\n" + "=" * 80)
print("CONCLUSIONE FISICA:")
print("=" * 80)
print("""
La pressione di repulsione spin-spin ESISTE ma è sommersa da termini di densità
di energia molto più grandi (tensione_taglio², energia_torsionale²).

In Einstein-Cartan, questi termini quadratici NON dovrebbero essere nella pressione,
ma nella densità di energia del tensore stress-energia.

Il problema è che stiamo trattando tutti i termini K² allo stesso modo, quando in
realtà:
  - K² nella CURVATURA → contributo all'energia (attrattivo)
  - K² nella PRESSIONE → repulsione spin-spin (repulsivo)

Questi sono FISICAMENTE DISTINTI ma numericamente identici come ordine di grandezza,
quindi si cancellano quasi completamente!

SOLUZIONE: Amplificare KAPPA_SPIN di fattore 10^6 - 10^8 per rendere la repulsione
dominante a scale di Planck.
""")
