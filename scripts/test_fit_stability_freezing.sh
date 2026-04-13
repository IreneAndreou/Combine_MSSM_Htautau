#!/bin/bash
set -euo pipefail

# ============================================================
# Run expected AsymptoticLimits for:
#   1) ggH POI, other POI floating
#   2) ggH POI, freeze r_bbH=0
#   3) bbH POI, other POI floating
#   4) bbH POI, freeze r_ggH=0
#
# Then:
#   - Collect limits to JSON
#   - Make standard expected-band plots
#   - Make overlay plots comparing freeze vs no-freeze
#
# Usage:
#   bash scripts/run_freeze_vs_nofreeze_limits.sh
# ============================================================

MASSES="60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,160,180,200,250,300,350,400,450,500,600,700,800,900,1000,1100,1200,1400,1600,1800,2000,2300,2600,2900,3200,3500"

WS="mssm_output/cmb/ws-gof.root"
OUTDIR="mssm_output/cmb"
PLOTTER="python3 plotMSSMLimits.py"

CMS_SUB="Own Work"
TITLE_RIGHT="109.08 fb^{-1} (13.6 TeV)"

mkdir -p "${OUTDIR}"

if [[ ! -f "${WS}" ]]; then
  echo "[ERROR] Workspace not found: ${WS}"
  exit 1
fi

run_limits () {
  local mode="$1"          # ggH or bbH
  local poi="$2"           # r_ggH or r_bbH
  local freeze="$3"        # yes or no
  local freeze_arg="$4"    # e.g. --freezeParameters r_bbH
  local tag="$5"           # output tag

  echo "============================================================"
  echo "Running ${mode} scenario: ${tag}"
  echo "============================================================"

  combineTool.py \
    -m "${MASSES}" \
    -M AsymptoticLimits \
    --rAbsAcc 0 \
    --rRelAcc 0.0005 \
    --setParameters r_ggH=0,r_bbH=0 \
    --redefineSignalPOIs "${poi}" \
    -d "${WS}" \
    --there \
    -n ".${tag}" \
    --X-rtd MINIMIZER_analytic \
    --cminDefaultMinimizerStrategy 0 \
    --cminDefaultMinimizerTolerance 0.01 \
    --boundlist mssm_boundaries.json \
    -v 1 \
    ${freeze_arg}

  combineTool.py \
    -M CollectLimits "${OUTDIR}"/higgsCombine.${tag}*.root \
    --use-dirs \
    -o "${OUTDIR}/${tag}.json"
}

# ------------------------------------------------------------
# Run 4 scenarios
# ------------------------------------------------------------

run_limits "ggH" "r_ggH" "no"  ""                            "ggH_noFreeze"
run_limits "ggH" "r_ggH" "yes" "--freezeParameters r_bbH"    "ggH_freezebbH"

run_limits "bbH" "r_bbH" "no"  ""                            "bbH_noFreeze"
run_limits "bbH" "r_bbH" "yes" "--freezeParameters r_ggH"    "bbH_freezeggH"

# ------------------------------------------------------------
# Standard expected-band plots
# ------------------------------------------------------------

echo "============================================================"
echo "Making standard band plots"
echo "============================================================"

${PLOTTER} \
  --cms-sub "${CMS_SUB}" \
  --title-right "${TITLE_RIGHT}" \
  --process 'gg#phi' \
  --y-axis-min 0.0001 \
  --y-axis-max 1000.0 \
  --show exp \
  "${OUTDIR}/ggH_noFreeze_cmb.json" \
  --output "${OUTDIR}/mssm_model-independent_ggH_noFreeze" \
  --logx --logy

${PLOTTER} \
  --cms-sub "${CMS_SUB}" \
  --title-right "${TITLE_RIGHT}" \
  --process 'gg#phi' \
  --y-axis-min 0.0001 \
  --y-axis-max 1000.0 \
  --show exp \
  "${OUTDIR}/ggH_freezebbH_cmb.json" \
  --output "${OUTDIR}/mssm_model-independent_ggH_freezebbH" \
  --logx --logy

${PLOTTER} \
  --cms-sub "${CMS_SUB}" \
  --title-right "${TITLE_RIGHT}" \
  --process 'bb#phi' \
  --y-axis-min 0.0001 \
  --y-axis-max 1000.0 \
  --show exp \
  "${OUTDIR}/bbH_noFreeze_cmb.json" \
  --output "${OUTDIR}/mssm_model-independent_bbH_noFreeze" \
  --logx --logy

${PLOTTER} \
  --cms-sub "${CMS_SUB}" \
  --title-right "${TITLE_RIGHT}" \
  --process 'bb#phi' \
  --y-axis-min 0.0001 \
  --y-axis-max 1000.0 \
  --show exp \
  "${OUTDIR}/bbH_freezeggH_cmb.json" \
  --output "${OUTDIR}/mssm_model-independent_bbH_freezeggH" \
  --logx --logy

# ------------------------------------------------------------
# Overlay plots: exp0 only
# Your plotting script supports:
#   file.json:exp0:Title="...",LineColor=...,LineStyle=...
# ------------------------------------------------------------

echo "============================================================"
echo "Making overlay plots"
echo "============================================================"

${PLOTTER} \
  "${OUTDIR}/ggH_noFreeze_cmb.json:exp0:Title=\"gg#phi expected (other POI floating)\",LineColor=ROOT.kBlack,LineStyle=1,LineWidth=3" \
  "${OUTDIR}/ggH_freezebbH_cmb.json:exp0:Title=\"gg#phi expected (r_{bb#phi}=0 fixed)\",LineColor=ROOT.kRed,LineStyle=2,LineWidth=3" \
  --cms-sub "${CMS_SUB}" \
  --title-right "${TITLE_RIGHT}" \
  --process 'gg#phi' \
  --show exp \
  --y-axis-min 0.0001 \
  --y-axis-max 1000.0 \
  --output "${OUTDIR}/mssm_model-independent_ggH_overlay_freezebbH" \
  --logx --logy

${PLOTTER} \
  "${OUTDIR}/bbH_noFreeze_cmb.json:exp0:Title=\"bb#phi expected (other POI floating)\",LineColor=ROOT.kBlack,LineStyle=1,LineWidth=3" \
  "${OUTDIR}/bbH_freezeggH_cmb.json:exp0:Title=\"bb#phi expected (r_{gg#phi}=0 fixed)\",LineColor=ROOT.kBlue,LineStyle=2,LineWidth=3" \
  --cms-sub "${CMS_SUB}" \
  --title-right "${TITLE_RIGHT}" \
  --process 'bb#phi' \
  --show exp \
  --y-axis-min 0.0001 \
  --y-axis-max 1000.0 \
  --output "${OUTDIR}/mssm_model-independent_bbH_overlay_freezeggH" \
  --logx --logy

echo "============================================================"
echo "Done."
echo
echo "JSON outputs:"
echo "  ${OUTDIR}/ggH_noFreeze.json"
echo "  ${OUTDIR}/ggH_freezebbH.json"
echo "  ${OUTDIR}/bbH_noFreeze.json"
echo "  ${OUTDIR}/bbH_freezeggH.json"
echo
echo "Band plots:"
echo "  ${OUTDIR}/mssm_model-independent_ggH_noFreeze.pdf"
echo "  ${OUTDIR}/mssm_model-independent_ggH_freezebbH.pdf"
echo "  ${OUTDIR}/mssm_model-independent_bbH_noFreeze.pdf"
echo "  ${OUTDIR}/mssm_model-independent_bbH_freezeggH.pdf"
echo
echo "Overlay plots:"
echo "  ${OUTDIR}/mssm_model-independent_ggH_overlay_freezebbH.pdf"
echo "  ${OUTDIR}/mssm_model-independent_bbH_overlay_freezeggH.pdf"
echo "============================================================"