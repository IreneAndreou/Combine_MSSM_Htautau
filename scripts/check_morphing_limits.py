# Script to check the two jsons with and without morphing for ggH and bbH limits
import json
import os

# Paths to the JSON files (update if needed)
file_with_morph = os.path.join(os.path.dirname(__file__), '../mssm_output/cmb/mssm_bbH_combined_cmb.json')
file_no_morph = os.path.join(os.path.dirname(__file__), '../mssm_output_no_morph/cmb/mssm_nomorph_bbH.json')

def load_json(path):
	with open(path, 'r') as f:
		return json.load(f)

def compare_limits(limits1, limits2):
	print(f"{'Mass':>8} | {'exp0 (morph)':>14} | {'exp0 (no morph)':>17} | {'Δexp0':>10}")
	print('-'*90)
	all_masses = sorted(set(limits1.keys()) | set(limits2.keys()), key=lambda x: float(x))
	for mass in all_masses:
		l1 = limits1.get(mass, {})
		l2 = limits2.get(mass, {})
		exp0_1 = l1.get('exp0', float('nan'))
		exp0_2 = l2.get('exp0', float('nan'))
		delta_exp0 = exp0_1 - exp0_2 if not (is_nan(exp0_1) or is_nan(exp0_2)) else float('nan')
		print(f"{mass:>8} | {exp0_1:14.6g} | {exp0_2:17.6g} | {delta_exp0:10.3g}")

def is_nan(x):
	try:
		return x != x
	except:
		return True

if __name__ == "__main__":
	limits_morph = load_json(file_with_morph)
	limits_nomorph = load_json(file_no_morph)
	print("Comparison of bbH limits (with morphing vs no morphing):\n")
	compare_limits(limits_morph, limits_nomorph)