#!/usr/bin/env bash
set -euo pipefail

MASSES="60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,160,180,200,250,300,350,400,450,500,600,700,800,900,1000,1100,1200,1400,1600,1800,2000,2300,2600,2900,3200,3500"

BOUNDLIST="mssm_boundaries.json"
LUMI_LABEL="109.08 fb^{-1} (13.6 TeV)"
CMS_SUB="Private Work"

declare -A WS
WS[tt]="mssm_output/cmb/ws_tt.root"
WS[mt]="mssm_output/cmb/ws_mt.root"
WS[et]="mssm_output/cmb/ws_et.root"

declare -A OUTDIR
OUTDIR[tt]="mssm_output/tt"
OUTDIR[mt]="mssm_output/mt"
OUTDIR[et]="mssm_output/et"

CHANNELS=("tt" "mt" "et")

run_limits() {
  local ch="$1"
  local ws="${WS[$ch]}"
  local out="${OUTDIR[$ch]}"

  mkdir -p "${out}"

  echo "============================================================"
  echo "Running channel: ${ch}"
  echo "Workspace: ${ws}"
  echo "Output dir: ${out}"
  echo "============================================================"

  combineTool.py \
    -m "${MASSES}" \
    -M AsymptoticLimits \
    --rAbsAcc 0 \
    --rRelAcc 0.0005 \
    --setParameters r_ggH=0,r_bbH=0 \
    --redefineSignalPOIs r_bbH \
    --freezeParameters r_ggH \
    -d "${ws}" \
    --there \
    -n ".bbH_${ch}" \
    --boundlist "${BOUNDLIST}" \
    --X-rtd MINIMIZER_analytic \
    --cminDefaultMinimizerStrategy 0 \
    --cminDefaultMinimizerTolerance 0.01 \
    -v 1

  combineTool.py \
    -m "${MASSES}" \
    -M AsymptoticLimits \
    --rAbsAcc 0 \
    --rRelAcc 0.0005 \
    --setParameters r_ggH=0,r_bbH=0 \
    --redefineSignalPOIs r_ggH \
    --freezeParameters r_bbH \
    -d "${ws}" \
    --there \
    -n ".ggH_${ch}" \
    --boundlist "${BOUNDLIST}" \
    --X-rtd MINIMIZER_analytic \
    --cminDefaultMinimizerStrategy 0 \
    --cminDefaultMinimizerTolerance 0.01 \
    -v 1

  combineTool.py \
    -M CollectLimits \
    mssm_output/cmb/higgsCombine.bbH_${ch}.AsymptoticLimits.mH*.root \
    -o ${out}/mssm_bbH_${ch}.json

  combineTool.py \
    -M CollectLimits \
    mssm_output/cmb/higgsCombine.ggH_${ch}.AsymptoticLimits.mH*.root \
    -o ${out}/mssm_ggH_${ch}.json

  python3 plotMSSMLimits.py \
    --cms-sub "${CMS_SUB}" \
    --title-right "${LUMI_LABEL}" \
    --process 'gg#phi' \
    --y-axis-min 0.0001 \
    --y-axis-max 1000.0 \
    --show exp \
    "${out}/mssm_ggH_${ch}.json" \
    --output "${out}/mssm_model-independent_ggH_${ch}" \
    --logx --logy

  python3 plotMSSMLimits.py \
    --cms-sub "${CMS_SUB}" \
    --title-right "${LUMI_LABEL}" \
    --process 'bb#phi' \
    --y-axis-min 0.0001 \
    --y-axis-max 1000.0 \
    --show exp \
    "${out}/mssm_bbH_${ch}.json" \
    --output "${out}/mssm_model-independent_bbH_${ch}" \
    --logx --logy
}

cat > overlay_mssm_limits.py << 'PYEOF'
#!/usr/bin/env python3
import json
import argparse
import matplotlib.pyplot as plt

def load_limit_json(path):
    with open(path) as f:
        data = json.load(f)

    masses = []
    expected = []

    for mass_key in sorted(data.keys(), key=lambda x: float(x)):
        entry = data[mass_key]
        if "exp0" not in entry:
            continue
        masses.append(float(mass_key))
        expected.append(float(entry["exp0"]))

    return masses, expected

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ggh", required=True)
    ap.add_argument("--bbh", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--channel", required=True)
    ap.add_argument("--title-right", default="109.08 fb^{-1} (13.6 TeV)")
    ap.add_argument("--cms-sub", default="Private Work")
    ap.add_argument("--ymin", type=float, default=1e-4)
    ap.add_argument("--ymax", type=float, default=1e3)
    args = ap.parse_args()

    mg, yg = load_limit_json(args.ggh)
    mb, yb = load_limit_json(args.bbh)

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.plot(mg, yg, marker="o", label=r"Expected gg$\phi$")
    ax.plot(mb, yb, marker="s", label=r"Expected bb$\phi$")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(min(min(mg), min(mb)), max(max(mg), max(mb)))
    ax.set_ylim(args.ymin, args.ymax)
    ax.set_xlabel(r"$m_{\phi}$ (GeV)")
    ax.set_ylabel(r"95% CL upper limit on $\sigma \times B(\phi \rightarrow \tau\tau)$ (pb)")
    ax.legend(frameon=False)
    ax.grid(True, which="both", alpha=0.3)

    ax.text(0.02, 0.98, f"CMS {args.cms_sub}", transform=ax.transAxes,
            ha="left", va="top", fontsize=13, fontweight="bold")
    ax.text(0.98, 0.98, args.title_right, transform=ax.transAxes,
            ha="right", va="top", fontsize=11)
    ax.text(0.02, 0.92, f"Channel: {args.channel}", transform=ax.transAxes,
            ha="left", va="top", fontsize=11)

    plt.tight_layout()
    fig.savefig(args.output + ".png", dpi=200)
    fig.savefig(args.output + ".pdf")

if __name__ == "__main__":
    main()
PYEOF

chmod +x overlay_mssm_limits.py

cat > overlay_channels_mssm_limits.py << 'PYEOF'
#!/usr/bin/env python3
import json
import argparse
import matplotlib.pyplot as plt

def load_limit_json(path):
    with open(path) as f:
        data = json.load(f)

    masses = []
    expected = []

    for mass_key in sorted(data.keys(), key=lambda x: float(x)):
        entry = data[mass_key]
        if "exp0" not in entry:
            continue
        masses.append(float(mass_key))
        expected.append(float(entry["exp0"]))

    return masses, expected

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tt", required=True, help="tt json")
    ap.add_argument("--mt", required=True, help="mt json")
    ap.add_argument("--et", required=True, help="et json")
    ap.add_argument("--output", required=True, help="output basename")
    ap.add_argument("--process", required=True, help="ggH or bbH")
    ap.add_argument("--title-right", default="109.08 fb^{-1} (13.6 TeV)")
    ap.add_argument("--cms-sub", default="Private Work")
    ap.add_argument("--ymin", type=float, default=1e-4)
    ap.add_argument("--ymax", type=float, default=1e3)
    args = ap.parse_args()

    m_tt, y_tt = load_limit_json(args.tt)
    m_mt, y_mt = load_limit_json(args.mt)
    m_et, y_et = load_limit_json(args.et)

    fig, ax = plt.subplots(figsize=(8, 7))

    ax.plot(m_tt, y_tt, marker="o", label="tt expected")
    ax.plot(m_mt, y_mt, marker="s", label="mt expected")
    ax.plot(m_et, y_et, marker="^", label="et expected")

    all_masses = m_tt + m_mt + m_et
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(min(all_masses), max(all_masses))
    ax.set_ylim(args.ymin, args.ymax)

    ax.set_xlabel(r"$m_{\phi}$ (GeV)")
    ax.set_ylabel(r"95% CL upper limit on $\sigma \times B(\phi \rightarrow \tau\tau)$ (pb)")

    process_label = args.process
    ax.legend(frameon=False, title=process_label)
    ax.grid(True, which="both", alpha=0.3)

    ax.text(0.02, 0.98, f"CMS {args.cms_sub}", transform=ax.transAxes,
            ha="left", va="top", fontsize=13, fontweight="bold")
    ax.text(0.98, 0.98, args.title_right, transform=ax.transAxes,
            ha="right", va="top", fontsize=11)
    ax.text(0.02, 0.92, f"Process: {args.process}", transform=ax.transAxes,
            ha="left", va="top", fontsize=11)

    plt.tight_layout()
    fig.savefig(args.output + ".png", dpi=200)
    fig.savefig(args.output + ".pdf")
    print(f"Saved {args.output}.png and {args.output}.pdf")

if __name__ == "__main__":
    main()
PYEOF

chmod +x overlay_channels_mssm_limits.py

for ch in "${CHANNELS[@]}"; do
  run_limits "${ch}"

  python3 overlay_mssm_limits.py \
    --ggh "${OUTDIR[$ch]}/mssm_ggH_${ch}.json" \
    --bbh "${OUTDIR[$ch]}/mssm_bbH_${ch}.json" \
    --output "${OUTDIR[$ch]}/mssm_model-independent_overlay_${ch}" \
    --channel "${ch}" \
    --title-right "${LUMI_LABEL}" \
    --cms-sub "${CMS_SUB}" \
    --ymin 0.0001 \
    --ymax 1000.0
done

# Overlay channels for ggH
python3 overlay_channels_mssm_limits.py \
  --tt "mssm_output/tt/mssm_ggH_tt.json" \
  --mt "mssm_output/mt/mssm_ggH_mt.json" \
  --et "mssm_output/et/mssm_ggH_et.json" \
  --output "mssm_output/mssm_model-independent_ggH_channels_overlay" \
  --process "ggH" \
  --title-right "${LUMI_LABEL}" \
  --cms-sub "${CMS_SUB}" \
  --ymin 0.0001 \
  --ymax 1000.0

# Overlay channels for bbH
python3 overlay_channels_mssm_limits.py \
  --tt "mssm_output/tt/mssm_bbH_tt.json" \
  --mt "mssm_output/mt/mssm_bbH_mt.json" \
  --et "mssm_output/et/mssm_bbH_et.json" \
  --output "mssm_output/mssm_model-independent_bbH_channels_overlay" \
  --process "bbH" \
  --title-right "${LUMI_LABEL}" \
  --cms-sub "${CMS_SUB}" \
  --ymin 0.0001 \
  --ymax 1000.0

echo "All done."