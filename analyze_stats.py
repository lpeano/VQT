import statistics

# Parse stabilita.log
with open('stabilita.log', encoding='utf-8') as f:
    lines = f.readlines()

chi_vals = []
k_vals = []
sigma_chi_vals = []

for line in lines:
    if line.strip() and not any(line.startswith(x) for x in ['=', 'Frame', 'Fine', 'LOG', '---']):
        parts = line.split()
        if len(parts) >= 4:
            try:
                chi_vals.append(float(parts[2]))
                k_vals.append(float(parts[3]))
            except:
                pass

print(f'Analyzed {len(chi_vals)} frames')
print(f'\nχ field stats:')
print(f'  Min: {min(chi_vals):.1f}')
print(f'  Max: {max(chi_vals):.1f}')
print(f'  Range: {max(chi_vals)-min(chi_vals):.1f}')
print(f'  Mean: {statistics.mean(chi_vals):.2f}')
print(f'  StdDev: {statistics.stdev(chi_vals):.2f}')
print(f'  Last 100 mean: {statistics.mean(chi_vals[-100:]):.2f}')

print(f'\nK_medio (norm) stats:')
print(f'  Min: {min(k_vals):.3e}')
print(f'  Max: {max(k_vals):.3e}')
print(f'  Mean: {statistics.mean(k_vals):.3e}')
print(f'  StdDev: {statistics.stdev(k_vals):.3e}')
print(f'  Last 100 mean: {statistics.mean(k_vals[-100:]):.3e}')

# Parse flussi_24campi.log for Max|Flux|
with open('flussi_24campi.log', encoding='utf-8') as f:
    data = f.read()

import re
flux_matches = re.findall(r'Max\|flux\|=([0-9.e+-]+)', data)
flux_vals = [float(m) for m in flux_matches]

print(f'\nMax|Flux| stats over {len(flux_vals)} frames:')
print(f'  Min: {min(flux_vals):.3f}')
print(f'  Max: {max(flux_vals):.3f}')
print(f'  Mean: {statistics.mean(flux_vals):.3f}')
print(f'  StdDev: {statistics.stdev(flux_vals):.3f}')
print(f'  Last 100 mean: {statistics.mean(flux_vals[-100:]):.3f}')
