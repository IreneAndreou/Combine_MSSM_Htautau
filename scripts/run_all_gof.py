import subprocess
import os

ERA = "Run3_2024"
DIR = os.getcwd()
MASS = 60
MODE = "local"
NUM_TOYS = 50

script = os.path.join("scripts", "run_gof.sh")
# chmod +x the script to ensure it can be run
subprocess.run(["chmod", "+x", script], check=True)
def run_gof(channel, category):
    cmd = [
        script,
        ERA,
        channel,
        str(category),
        DIR,
        MODE,
        str(MASS),
        str(NUM_TOYS)
    ]
    print(f"\n[INFO] Running: {' '.join(cmd)}\n")
    subprocess.run(cmd, check=True)

# Full combination (all channels, all categories)
run_gof("cmb", "all")
print("\n[INFO] Finished full combination. Now running per channel...\n")

# Per channel (all categories)
for chn in ["et", "mt", "tt"]:
    run_gof(chn, "all")
    print(f"[INFO] Finished channel {chn} (all categories)")

print("\n[INFO] Finished per channel. Now running per category...\n")

# Per category in each channel
for chn in ["et", "mt", "tt"]:
    for cat in [1, 2]:
        run_gof(chn, str(cat))
        print(f"[INFO] Finished channel {chn}, category {cat}")

print(f"\n[INFO] All GoF tests for m{MASS} completed.")
