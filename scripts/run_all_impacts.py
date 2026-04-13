import os
import subprocess

ERA = "Run3_2024"
DIR = os.getcwd()
MASS = 125

WORKSPACE_DIR = os.path.join(DIR, "mssm_output_no_morph", "cmb")
IMPACTS_BASE = os.path.join(WORKSPACE_DIR, "gof_observed")

CHANNELS = ["et", "mt", "tt"]
CATEGORIES = [1, 2]

PARALLEL = 8
POI = "r_ggH"
FROZEN_POIS = "r_bbH"


def run(cmd, cwd=None):
    print(f"\n[INFO] Running: {cmd}\n")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)


def impacts_name():
    return f".ggH_m{MASS}.Impacts"


def common_options(ws_file):
    return (
        f"-m {MASS} "
        f"-d {ws_file} "
        f"--setParameters r_ggH=0,r_bbH=0 "
        f"--redefineSignalPOIs {POI} "
        f"--freezeParameters {FROZEN_POIS} "
        f"-n {impacts_name()} "
    )


def do_impacts(id_str, ws_file, impacts_dir):
    os.makedirs(impacts_dir, exist_ok=True)

    common = common_options(ws_file)

    # 1. Initial fit
    run(
        f"combineTool.py -M Impacts {common} "
        f"--doInitialFit "
        f"--robustFit 1 "
        f"--cminDefaultMinimizerStrategy 0 "
        f"--cminDefaultMinimizerTolerance 0.1",
        cwd=impacts_dir,
    )

    # 2. Per-nuisance fits
    run(
        f"combineTool.py -M Impacts {common} "
        f"--doFits "
        f"--robustFit 1 "
        f"--parallel {PARALLEL} "
        f"--cminDefaultMinimizerStrategy 0 "
        f"--cminDefaultMinimizerTolerance 0.1",
        cwd=impacts_dir,
    )

    # 3. Collect output json
    run(
        f"combineTool.py -M Impacts {common} "
        f"-o impacts_bkgonly.json",
        cwd=impacts_dir,
    )

    # 4. Plot impacts
    run(
        "plotImpacts.py -i impacts_bkgonly.json -o impacts_bkgonly --blind",
        cwd=impacts_dir,
    )


def build_workspace_list():
    combos = []

    # Full combination
    combos.append((ERA, os.path.join(WORKSPACE_DIR, f"ws_{MASS}.root")))

    # Per channel
    for chn in CHANNELS:
        combos.append((f"{ERA}-{chn}", os.path.join(WORKSPACE_DIR, f"{chn}_ws_{MASS}.root")))

    # Per category
    for chn in CHANNELS:
        for cat in CATEGORIES:
            combos.append((f"{ERA}-{chn}-{cat}", os.path.join(WORKSPACE_DIR, f"{chn}_{cat}_ws_{MASS}.root")))

    return combos


def main():
    combos = build_workspace_list()

    for id_str, ws_file in combos:
        impacts_dir = os.path.join(IMPACTS_BASE, id_str, f"m{MASS}")

        if not os.path.isfile(ws_file):
            print(f"[WARN] Workspace not found: {ws_file}, skipping {id_str}")
            continue

        print(f"\n[INFO] Running impacts for {id_str}")
        print(f"[INFO] Workspace: {ws_file}")
        print(f"[INFO] Output dir: {impacts_dir}")

        do_impacts(id_str, ws_file, impacts_dir)

    print("\n[INFO] All impacts done.")


if __name__ == "__main__":
    main()