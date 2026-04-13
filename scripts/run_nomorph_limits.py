import os
import subprocess

MASSES = [
    60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 140,
    160, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000,
    1100, 1200, 1400, 1600, 1800, 2000, 2300, 2600, 2900, 3200, 3500
]

ERAS = "Run3_2024"
HARVEST_SCRIPT = "scripts/harvestDatacards_nomorph.py"
BOUNDLIST = "mssm_boundaries.json"

GGH_MAP = 'map=^.*/ggH_MSSM_htt$:r_ggH[0,0,200]'
BBH_MAP = 'map=^.*/bbH_MSSM_htt$:r_bbH[0,0,200]'

OUTDIR = "mssm_output_no_morph"

def run(cmd):
    print("\n>>>", cmd)
    subprocess.run(cmd, shell=True, check=True)

bbH_files = []
ggH_files = []

for mass in MASSES:
    print("\n======================================")
    print(f" Running mass {mass}")
    print("======================================")

    cmb_dir = f"{OUTDIR}/cmb"
    combined_card = f"{cmb_dir}/combined_{mass}.txt"
    ws_file = f"{cmb_dir}/ws_{mass}.root"

    # 1. Harvest
    # Uncomment if you want the script to rebuild cards each time
    run(f"""
    python3 {HARVEST_SCRIPT} \
        --output_folder {OUTDIR} \
        --eras {ERAS} \
        --mass {mass}
    """)


    # 2. Combine the per-category cards into one combined card for this mass (combined)
    combined_card = f"{cmb_dir}/combined_{mass}.txt"
    run(f"""
    cd {cmb_dir}
    combineCards.py \
        et1=mssm_et_1_Run3_2024_{mass}.txt \
        et2=mssm_et_2_Run3_2024_{mass}.txt \
        mt1=mssm_mt_1_Run3_2024_{mass}.txt \
        mt2=mssm_mt_2_Run3_2024_{mass}.txt \
        tt1=mssm_tt_1_Run3_2024_{mass}.txt \
        tt2=mssm_tt_2_Run3_2024_{mass}.txt \
        > combined_{mass}.txt
    """)

    # 2b. Per-channel combined cards and workspaces
    for chn in ["et", "mt", "tt"]:
        chn_dir = f"{OUTDIR}/cmb"
        chn_card = f"{chn_dir}/combined_{chn}_{mass}.txt"
        run(f"""
        cd {chn_dir}
        combineCards.py \
            mssm_{chn}_1_Run3_2024_{mass}.txt \
            mssm_{chn}_2_Run3_2024_{mass}.txt \
            > combined_{chn}_{mass}.txt
        """)
        chn_ws = f"{chn_dir}/{chn}_ws_{mass}.root"
        run(f"""
        text2workspace.py {chn_card} \
            -o {chn_ws} \
            -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel \
            --PO '{GGH_MAP}' \
            --PO '{BBH_MAP}' \
            -m {mass}
        """)

    # 2c. Per-category cards and workspaces
    for chn in ["et", "mt", "tt"]:
        chn_dir = f"{OUTDIR}/cmb"
        for cat in [1, 2]:
            cat_card = f"{chn_dir}/mssm_{chn}_{cat}_Run3_2024_{mass}.txt"
            cat_ws = f"{chn_dir}/{chn}_{cat}_ws_{mass}.root"
            run(f"""
            text2workspace.py {cat_card} \
                -o {cat_ws} \
                -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel \
                --PO '{GGH_MAP}' \
                --PO '{BBH_MAP}' \
                -m {mass}
            """)

    # 3. Build ONE workspace for this mass from the combined card (as before)
    run(f"""
    text2workspace.py {combined_card} \
        -o {ws_file} \
        -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel \
        --PO '{GGH_MAP}' \
        --PO '{BBH_MAP}' \
        -m {mass}
    """)

    # 4. bbH limit
    run(f"""
    combineTool.py -m {mass} -M AsymptoticLimits \
        --rAbsAcc 0 --rRelAcc 0.0005 \
        --setParameters r_ggH=0,r_bbH=0 \
        --redefineSignalPOIs r_bbH \
        --freezeParameters r_ggH \
        -d {ws_file} \
        --there -n .bbH \
        --boundlist {BOUNDLIST} \
        --X-rtd MINIMIZER_analytic \
        --cminDefaultMinimizerStrategy 0 \
        --cminDefaultMinimizerTolerance 0.01 -v 1
    """)

    # 5. ggH limit
    run(f"""
    combineTool.py -m {mass} -M AsymptoticLimits \
        --rAbsAcc 0 --rRelAcc 0.0005 \
        --setParameters r_ggH=0,r_bbH=0 \
        --redefineSignalPOIs r_ggH \
        --freezeParameters r_bbH \
        -d {ws_file} \
        --there -n .ggH \
        --boundlist {BOUNDLIST} \
        --X-rtd MINIMIZER_analytic \
        --cminDefaultMinimizerStrategy 0 \
        --cminDefaultMinimizerTolerance 0.01 -v 1
    """)

    bbH_files.append(f"{cmb_dir}/higgsCombine.bbH.AsymptoticLimits.mH{mass}.root")
    ggH_files.append(f"{cmb_dir}/higgsCombine.ggH.AsymptoticLimits.mH{mass}.root")

# 6. Collect
run(f"""
combineTool.py -M CollectLimits {' '.join(bbH_files)} \
    -o {OUTDIR}/cmb/mssm_nomorph_bbH.json
""")

run(f"""
combineTool.py -M CollectLimits {' '.join(ggH_files)} \
    -o {OUTDIR}/cmb/mssm_nomorph_ggH.json
""")

# 7. Plot
run(f"""
python3 plotMSSMLimits.py \
    --cms-sub "Private Work" \
    --title-right "109.08 fb^{{-1}} (13.6 TeV)" \
    --process 'gg#phi' \
    --y-axis-min 0.0001 \
    --y-axis-max 1000.0 \
    --show exp \
    {OUTDIR}/cmb/mssm_nomorph_ggH.json \
    --output mssm_nomorph_ggH \
    --logx --logy
""")

run(f"""
python3 plotMSSMLimits.py \
    --cms-sub "Private Work" \
    --title-right "109.08 fb^{{-1}} (13.6 TeV)" \
    --process 'bb#phi' \
    --y-axis-min 0.0001 \
    --y-axis-max 1000.0 \
    --show exp \
    {OUTDIR}/cmb/mssm_nomorph_bbH.json \
    --output mssm_nomorph_bbH \
    --logx --logy
""")

print("\nDone.")