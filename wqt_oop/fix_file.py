"""Script per riparare solitone_composito.py rimuovendo sezione duplicata."""

# Leggi file
with open("c:/Users/lpeano/plank/VQT/wqt_oop/solitone_composito.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Trova le linee da rimuovere (linea 486-544)
output_lines = []
skip_mode = False
first_getbudget_found = False

for i, line in enumerate(lines, start=1):
    # Trova prima occorrenza di get_energy_budget
    if "def get_energy_budget" in line and not first_getbudget_found:
        first_getbudget_found = True
        skip_mode = True
        continue
    
    # Trova seconda occorrenza (quella buona)
    if "def get_energy_budget" in line and first_getbudget_found and skip_mode:
        skip_mode = False
        output_lines.append(line)
        continue
    
    # Scrivi linea solo se non in skip_mode
    if not skip_mode:
        output_lines.append(line)

# Scrivi file riparato
with open("c:/Users/lpeano/plank/VQT/wqt_oop/solitone_composito.py", "w", encoding="utf-8") as f:
    f.writelines(output_lines)

print("File riparato: sezione duplicata rimossa")
