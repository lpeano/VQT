# tools/run_all_validation.py
import subprocess
import os
import sys

def run(cmd):
    print(f"\n--- Lancio: {cmd} ---")
    subprocess.run(cmd, shell=True, check=True)

# 1. Lancio catena simulazione (Ramo B)
run("python experiments/genesis_run.py")
run("python experiments/l2_aggregation_run.py")
run("python experiments/l4_self_assembly_run.py")

# 2. Generazione statistiche grafiche (La "Firma del Vuoto")
run("python experiments/render_zero_point_stats.py")

# 3. Consolidamento log
print("\n=== VERIFICA LOG CONSOLIDATI ===")
for log in ["logs/l4_self_assembly.log", "logs/cluster_analysis.log"]:
    if os.path.exists(log):
        print(f"\nUltimi dati {log}:")
        # Legge le ultime 5 righe del log
        with open(log, 'r') as f:
            print("".join(f.readlines()[-5:]))

print("\n[OK] Validazione completata. Grafico salvato in: assets/zero_point_validation.png")