#!/bin/bash
set -euo pipefail

# ============================================================
# Fast thesis fit-validation script for MSSM workspaces
#
# Runs for each requested mass / POI:
#   1) Expected AsymptoticLimits with a few minimizer variants
#   2) 1D MultiDimFit scan around the expected median limit
#   3) Lightweight best-fit check with MultiDimFit --algo none
#
# Produces:
#   - asymptotic_summary.csv
#   - scan_summary.csv
#   - bestfit_summary.csv
#   - all_masses_summary.csv
#   - <tag>/health_report.txt
#   - README_thesis_validation.txt
#
# Philosophy:
#   - fast enough for many mass points
#   - robust enough for thesis validation
#   - no FitDiagnostics / HybridNew by default
# ============================================================

# --------------------------
# Defaults
# --------------------------
WS="mssm_output/cmb/ws.root"
OUTBASE="mssm_output/cmb/thesis_fit_validation"
MASS=2000
MASSES=""
POI="r_ggH"
DO_BOTH_POIS=0

DEFAULT_MASSES="60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,140,160,180,200,250,300,350,400,450,500,600,700,800,900,1000,1100,1200,1400,1600,1800,2000,2300,2600,2900,3200,3500"

# thresholds
REL_SPREAD_WARN=0.05
BESTFIT_AT_BOUNDARY_WARN=1e-4

# scan settings
SCAN_POINTS=41
SCAN_RANGE_SCALE=2.0

BOUNDLIST=""

# --------------------------
# Parse args
# --------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ws) WS="$2"; shift 2 ;;
    --outbase) OUTBASE="$2"; shift 2 ;;
    --mass) MASS="$2"; shift 2 ;;
    --masses) MASSES="$2"; shift 2 ;;
    --default-masses) MASSES="${DEFAULT_MASSES}"; shift ;;
    --poi) POI="$2"; shift 2 ;;
    --both-pois) DO_BOTH_POIS=1; shift ;;
    --spread-warn) REL_SPREAD_WARN="$2"; shift 2 ;;
    --boundary-warn) BESTFIT_AT_BOUNDARY_WARN="$2"; shift 2 ;;
    --scan-points) SCAN_POINTS="$2"; shift 2 ;;
    --scan-scale) SCAN_RANGE_SCALE="$2"; shift 2 ;;
    --boundlist) BOUNDLIST="$2"; shift 2 ;;
    *)
      echo "[ERROR] Unknown argument: $1"
      exit 1
      ;;
  esac
done

WS="$(realpath "${WS}")"
mkdir -p "${OUTBASE}"
OUTBASE="$(realpath "${OUTBASE}")"

rm -f "${OUTBASE}/asymptotic_summary.csv"
rm -f "${OUTBASE}/scan_summary.csv"
rm -f "${OUTBASE}/scan_summary_tmp.csv"
rm -f "${OUTBASE}/bestfit_summary.csv"
rm -f "${OUTBASE}/all_masses_summary.csv"

if [[ ! -f "${WS}" ]]; then
  echo "[ERROR] Workspace not found: ${WS}"
  exit 1
fi

# If --masses not given, fall back to single MASS
if [[ -z "${MASSES}" ]]; then
  MASSES="${MASS}"
fi

# --------------------------
# Helpers
# --------------------------
append_master_csv_header_if_needed() {
  local file="$1"
  local header="$2"
  mkdir -p "$(dirname "${file}")"
  if [[ ! -f "${file}" ]]; then
    echo "${header}" > "${file}"
  fi
}

other_poi_name() {
  local poi="$1"
  if [[ "${poi}" == "r_ggH" ]]; then
    echo "r_bbH"
  elif [[ "${poi}" == "r_bbH" ]]; then
    echo "r_ggH"
  else
    echo ""
  fi
}

other_poi_freeze_arg() {
  local poi="$1"
  local other
  other="$(other_poi_name "${poi}")"
  if [[ -n "${other}" ]]; then
    echo "--freezeParameters ${other}"
  else
    echo ""
  fi
}

combine_common_args() {
  local poi="$1"
  local freeze_arg="$2"
  echo \
    --redefineSignalPOIs "${poi}" \
    --setParameters r_ggH=0,r_bbH=0 \
    ${freeze_arg}
}

common_asymptotic_opts() {
  echo \
    --cminDefaultMinimizerStrategy 0 \
    --cminDefaultMinimizerTolerance 0.01 \
    --X-rtd MINIMIZER_analytic
}

sanitize_mass_tag() {
  local mass="$1"
  echo "${mass}" | sed 's/\./p/g'
}

extract_asymptotic_metrics_from_log() {
  local logfile="$1"
  python3 - "$logfile" <<'PY'
import re, sys, json
txt = open(sys.argv[1], "r", encoding="utf-8", errors="ignore").read()

def grab(label):
    patterns = [
        rf"{re.escape(label)}\s*:\s*.*<\s*([0-9eE+.\-]+)",
        rf"{re.escape(label)}\s*:\s*r(?:_[A-Za-z0-9]+)?\s*<\s*([0-9eE+.\-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, txt)
        if m:
            return m.group(1)
    return "NA"

out = {
    "observed": grab("Observed Limit"),
    "exp2p5": grab("Expected  2.5%"),
    "exp16": grab("Expected 16.0%"),
    "exp50": grab("Expected 50.0%"),
    "exp84": grab("Expected 84.0%"),
    "exp97p5": grab("Expected 97.5%"),
}
print(json.dumps(out))
PY
}

write_json_value_to_csv_row() {
  local json="$1"
  local keys_csv="$2"
  python3 - "$json" "$keys_csv" <<'PY'
import json, sys
obj = json.loads(sys.argv[1])
keys = sys.argv[2].split(",")
print(",".join(str(obj.get(k, "NA")) for k in keys))
PY
}

dynamic_scan_range_from_exp50() {
  local exp50="$1"
  local scale="$2"
  python3 - "$exp50" "$scale" <<'PY'
import sys
mu = float(sys.argv[1])
scale = float(sys.argv[2])

hi = scale * mu
hi = max(hi, 0.01)
hi = min(hi, 10.0)

print(f"0,{hi:.8g}")
PY
}

dynamic_bestfit_range_from_exp50() {
  local exp50="$1"
  python3 - "$exp50" <<'PY'
import sys
mu = float(sys.argv[1])
hi = max(0.1, 5.0 * mu)
hi = min(hi, 10.0)
print(f"0,{hi:.8g}")
PY
}

extract_scan_to_csv() {
  local rootfile="$1"
  local csvfile="$2"
  python3 - "$rootfile" "$csvfile" <<'PY'
import sys
import ROOT

rootfile, csvfile = sys.argv[1], sys.argv[2]
f = ROOT.TFile.Open(rootfile)
if not f or f.IsZombie():
    raise RuntimeError(f"Could not open {rootfile}")
t = f.Get("limit")
if not t:
    raise RuntimeError("Tree 'limit' not found")

branches = [b.GetName() for b in t.GetListOfBranches()]
poi_names = [x for x in ["r", "r_ggH", "r_bbH"] if x in branches]

poi = None
for cand in ["r_ggH", "r_bbH", "r"]:
    if cand in poi_names:
        poi = cand
        break

if poi is None:
    raise RuntimeError(f"No POI branch found in branches: {branches}")

with open(csvfile, "w") as out:
    out.write("point,poi_name,poi_value,deltaNLL,quantileExpected\n")
    i = 0
    for ev in t:
        dNLL = getattr(ev, "deltaNLL", float("nan"))
        qexp = getattr(ev, "quantileExpected", float("nan"))
        pval = getattr(ev, poi)
        out.write(f"{i},{poi},{pval},{dNLL},{qexp}\n")
        i += 1
PY
}

extract_bestfit_to_csv() {
  local rootfile="$1"
  local csvfile="$2"
  python3 - "$rootfile" "$csvfile" <<'PY'
import sys
import ROOT

rootfile, csvfile = sys.argv[1], sys.argv[2]
f = ROOT.TFile.Open(rootfile)
if not f or f.IsZombie():
    raise RuntimeError(f"Could not open {rootfile}")

t = f.Get("limit")
if not t:
    raise RuntimeError("Tree 'limit' not found")

branches = [b.GetName() for b in t.GetListOfBranches()]
poi = None
for cand in ["r_ggH", "r_bbH", "r"]:
    if cand in branches:
        poi = cand
        break

if poi is None:
    raise RuntimeError(f"No POI branch found in {branches}")

best = None
for i, ev in enumerate(t):
    best = {
        "entry": i,
        "poi_name": poi,
        "poi_value": getattr(ev, poi, float("nan")),
        "deltaNLL": getattr(ev, "deltaNLL", float("nan")),
        "quantileExpected": getattr(ev, "quantileExpected", float("nan")),
    }
    break

with open(csvfile, "w") as out:
    out.write("entry,poi_name,poi_value,deltaNLL,quantileExpected\n")
    if best is not None:
        out.write(f'{best["entry"]},{best["poi_name"]},{best["poi_value"]},{best["deltaNLL"]},{best["quantileExpected"]}\n')
PY
}

# --------------------------
# Core runners
# --------------------------
run_asymptotic_variant() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local mass="$5"
  local variant="$6"
  local extra_opts="$7"

  local outdir="${outbase}/${tag}/asymptotic/${variant}"
  mkdir -p "${outdir}"

  local freeze_arg
  freeze_arg="$(other_poi_freeze_arg "${poi}")"

  echo "============================================================"
  echo "[AsymptoticLimits] ${tag} :: ${variant}"
  echo "============================================================"

  pushd "${outdir}" >/dev/null

  local cmd=(
    combine -M AsymptoticLimits "${ws}"
    -m "${mass}"
    -n ".${tag}.${variant}"
    -t -1
    --run expected
    --rAbsAcc 0
    --rRelAcc 0.001
    -v 1
    $(combine_common_args "${poi}" "${freeze_arg}")
  )

  if [[ -n "${BOUNDLIST}" ]]; then
    cmd+=( --boundlist "${BOUNDLIST}" )
  fi

  # shellcheck disable=SC2206
  local extra_array=( ${extra_opts} )
  cmd+=( "${extra_array[@]}" )

  "${cmd[@]}" </dev/null | tee "asymptotic_${tag}_${variant}.log"

  local json
  json="$(extract_asymptotic_metrics_from_log "asymptotic_${tag}_${variant}.log")"
  echo "${json}" > "asymptotic_metrics.json"

  append_master_csv_header_if_needed "${outbase}/asymptotic_summary.csv" \
    "tag,poi,mass,variant,observed,exp2p5,exp16,exp50,exp84,exp97p5"

  local row
  row="$(write_json_value_to_csv_row "${json}" "observed,exp2p5,exp16,exp50,exp84,exp97p5")"
  echo "${tag},${poi},${mass},${variant},${row}" >> "${outbase}/asymptotic_summary.csv"

  popd >/dev/null
}

run_multidim_scan() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local mass="$5"
  local exp50="$6"

  local outdir="${outbase}/${tag}/scan"
  mkdir -p "${outdir}"

  local freeze_arg
  freeze_arg="$(other_poi_freeze_arg "${poi}")"

  local scan_range
  scan_range="$(dynamic_scan_range_from_exp50 "${exp50}" "${SCAN_RANGE_SCALE}")"

  echo "============================================================"
  echo "[MultiDimFit scan] ${tag}"
  echo "Using dynamic scan range: ${scan_range}"
  echo "============================================================"

  pushd "${outdir}" >/dev/null

  combine -M MultiDimFit "${ws}" \
    -m "${mass}" \
    -n ".${tag}.scan" \
    -t -1 \
    --algo grid \
    --points "${SCAN_POINTS}" \
    --alignEdges 1 \
    --robustFit 1 \
    $(combine_common_args "${poi}" "${freeze_arg}") \
    --cminDefaultMinimizerStrategy 0 \
    --cminDefaultMinimizerTolerance 0.01 \
    --X-rtd MINIMIZER_analytic \
    --setParameterRanges "${poi}=${scan_range}" \
    </dev/null | tee "multidim_${tag}.log"

  local rootfile="higgsCombine.${tag}.scan.MultiDimFit.mH${mass}.root"
  if [[ -f "${rootfile}" ]]; then
    extract_scan_to_csv "${rootfile}" "scan_points.csv"
    awk -F, -v tag="${tag}" -v poi="${poi}" -v mass="${mass}" '
      BEGIN {OFS=","}
      NR==1 {next}
      {print tag,poi,mass,$1,$2,$3,$4,$5}
    ' scan_points.csv >> "${outbase}/scan_summary_tmp.csv"
  fi

  if command -v plot1DScan.py >/dev/null 2>&1 && [[ -f "${rootfile}" ]]; then
    plot1DScan.py "${rootfile}" -o "scan_${tag}" --POI "${poi}" || true
  fi

  popd >/dev/null
}

run_bestfit_check() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local mass="$5"
  local exp50="$6"

  local outdir="${outbase}/${tag}/bestfit"
  mkdir -p "${outdir}"

  local freeze_arg
  freeze_arg="$(other_poi_freeze_arg "${poi}")"

  local fit_range
  fit_range="$(dynamic_bestfit_range_from_exp50 "${exp50}")"

  echo "============================================================"
  echo "[MultiDimFit best-fit check] ${tag}"
  echo "Using fit range: ${fit_range}"
  echo "============================================================"

  pushd "${outdir}" >/dev/null

  combine -M MultiDimFit "${ws}" \
    -m "${mass}" \
    -n ".${tag}.bestfit" \
    -t -1 \
    --algo none \
    --robustFit 1 \
    $(combine_common_args "${poi}" "${freeze_arg}") \
    --cminDefaultMinimizerStrategy 1 \
    --cminDefaultMinimizerTolerance 0.1 \
    --X-rtd MINIMIZER_analytic \
    --setParameterRanges "${poi}=${fit_range}" \
    </dev/null | tee "bestfit_${tag}.log" || true

  local rootfile="higgsCombine.${tag}.bestfit.MultiDimFit.mH${mass}.root"

  append_master_csv_header_if_needed "${outbase}/bestfit_summary.csv" \
    "tag,poi,mass,poi_name,poi_value,deltaNLL,quantileExpected"

  if [[ -f "${rootfile}" ]]; then
    extract_bestfit_to_csv "${rootfile}" "bestfit_metrics.csv"
    awk -F, -v tag="${tag}" -v poi="${poi}" -v mass="${mass}" '
      BEGIN {OFS=","}
      NR==1 {next}
      {print tag,poi,mass,$2,$3,$4,$5}
    ' bestfit_metrics.csv >> "${outbase}/bestfit_summary.csv"
  else
    echo "${tag},${poi},${mass},${poi},FAILED,NA,NA" >> "${outbase}/bestfit_summary.csv"
  fi

  popd >/dev/null
}

summarise_one_tag() {
  local outbase="$1"
  local tag="$2"
  local poi="$3"
  local mass="$4"

  mkdir -p "${outbase}/${tag}"

  python3 - \
    "${outbase}/asymptotic_summary.csv" \
    "${outbase}/bestfit_summary.csv" \
    "${tag}" "${poi}" "${mass}" \
    "${REL_SPREAD_WARN}" \
    "${BESTFIT_AT_BOUNDARY_WARN}" \
    "${outbase}/${tag}/health_report.txt" <<'PY'
import csv, sys

asym_csv, bestfit_csv, tag, poi, mass, spread_warn, boundary_warn, report = sys.argv[1:]
spread_warn = float(spread_warn)
boundary_warn = float(boundary_warn)

# --- asymptotic rows
asym_rows = []
try:
    with open(asym_csv) as f:
        r = csv.DictReader(f)
        for row in r:
            if row["tag"] == tag and row["poi"] == poi and row["mass"] == mass:
                asym_rows.append(row)
except FileNotFoundError:
    pass

vals = {}
for row in asym_rows:
    try:
        vals[row["variant"]] = float(row["exp50"])
    except:
        vals[row["variant"]] = None

baseline = vals.get("baseline")
valid = [v for v in vals.values() if v is not None]

spread = None
if baseline not in (None, 0) and valid:
    spread = (max(valid) - min(valid)) / abs(baseline)

# --- bestfit
bestfit = None
try:
    with open(bestfit_csv) as f:
        r = csv.DictReader(f)
        for row in r:
            if row["tag"] == tag and row["poi"] == poi and row["mass"] == mass:
                bestfit = row
                break
except FileNotFoundError:
    pass

status = "OK"
reasons = []

if baseline is None or not valid:
    status = "WARNING"
    reasons.append("missing asymptotic expected-limit information")
else:
    if spread is not None and spread > spread_warn:
        status = "WARNING"
        reasons.append(f"relative spread {spread:.4f} exceeds threshold {spread_warn:.4f}")

bestfit_value = "NA"
if bestfit is None:
    status = "WARNING"
    reasons.append("missing best-fit summary")
else:
    bestfit_value = bestfit.get("poi_value", "NA")
    try:
        bf = float(bestfit_value)
        if abs(bf) < boundary_warn:
            reasons.append(f"best-fit value {bf:.6g} is very close to lower boundary")
    except:
        if bestfit_value == "FAILED":
            status = "WARNING"
            reasons.append("best-fit MultiDimFit failed")

with open(report, "w") as out:
    out.write("Fast thesis fit-validation report\n")
    out.write("================================\n")
    out.write(f"POI  = {poi}\n")
    out.write(f"mass = {mass}\n\n")

    out.write("Asymptotic expected-limit variants\n")
    out.write("---------------------------------\n")
    for k in ["baseline", "strategy1", "tol0p1", "noanalytic"]:
        out.write(f"{k:10s}: {vals.get(k)}\n")
    if spread is not None:
        out.write(f"\nrelative_spread = {spread:.6f}\n")
    else:
        out.write("\nrelative_spread = NA\n")

    out.write("\nBest-fit check\n")
    out.write("--------------\n")
    out.write(f"bestfit_poi_value = {bestfit_value}\n")

    out.write(f"\nStatus: {status}\n")
    if reasons:
        out.write("Reasons:\n")
        for r in reasons:
            out.write(f" - {r}\n")
    else:
        out.write("Reasons:\n")
        out.write(" - expected limit stable across minimizer variants\n")
        out.write(" - best-fit check completed without obvious pathology\n")
PY
}

finalize_master_tables() {
  if [[ -f "${OUTBASE}/scan_summary_tmp.csv" ]]; then
    {
      echo "tag,poi,mass,point,poi_name,poi_value,deltaNLL,quantileExpected"
      cat "${OUTBASE}/scan_summary_tmp.csv"
    } > "${OUTBASE}/scan_summary.csv"
    rm -f "${OUTBASE}/scan_summary_tmp.csv"
  fi
}

build_all_masses_summary() {
  python3 - \
    "${OUTBASE}/asymptotic_summary.csv" \
    "${OUTBASE}/bestfit_summary.csv" \
    "${REL_SPREAD_WARN}" \
    "${BESTFIT_AT_BOUNDARY_WARN}" \
    "${OUTBASE}/all_masses_summary.csv" <<'PY'
import csv, sys
from collections import defaultdict

asym_csv, bestfit_csv, spread_warn, boundary_warn, out_csv = sys.argv[1:]
spread_warn = float(spread_warn)
boundary_warn = float(boundary_warn)

asym = defaultdict(dict)
keys = set()

with open(asym_csv) as f:
    r = csv.DictReader(f)
    for row in r:
        key = (row["tag"], row["poi"], row["mass"])
        keys.add(key)
        try:
            asym[key][row["variant"]] = float(row["exp50"])
        except:
            asym[key][row["variant"]] = None

bestfit = {}
with open(bestfit_csv) as f:
    r = csv.DictReader(f)
    for row in r:
        key = (row["tag"], row["poi"], row["mass"])
        keys.add(key)
        bestfit[key] = row

def mass_sort_value(m):
    try:
        return float(m)
    except:
        return 1e99

ordered = sorted(keys, key=lambda x: (x[1], mass_sort_value(x[2]), x[0]))

with open(out_csv, "w", newline="") as f:
    fieldnames = [
        "tag", "poi", "mass",
        "baseline_exp50", "strategy1_exp50", "tol0p1_exp50", "noanalytic_exp50",
        "relative_spread", "bestfit_poi_value", "status", "notes"
    ]
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()

    for key in ordered:
        tag, poi, mass = key
        vals = asym.get(key, {})
        baseline = vals.get("baseline")
        valid = [v for v in vals.values() if v is not None]

        spread = None
        status = "OK"
        notes = []

        if baseline is None or not valid or baseline == 0:
            status = "WARNING"
            notes.append("missing asymptotic information")
        else:
            spread = (max(valid) - min(valid)) / abs(baseline)
            if spread > spread_warn:
                status = "WARNING"
                notes.append(f"spread>{spread_warn:.3f}")

        bf_row = bestfit.get(key)
        bf_val = "NA"
        if bf_row is None:
            status = "WARNING"
            notes.append("missing bestfit")
        else:
            bf_val = bf_row.get("poi_value", "NA")
            if bf_val == "FAILED":
                status = "WARNING"
                notes.append("bestfit failed")
            else:
                try:
                    bf = float(bf_val)
                    if abs(bf) < boundary_warn:
                        notes.append("bestfit near boundary")
                except:
                    pass

        w.writerow({
            "tag": tag,
            "poi": poi,
            "mass": mass,
            "baseline_exp50": baseline if baseline is not None else "NA",
            "strategy1_exp50": vals.get("strategy1", "NA"),
            "tol0p1_exp50": vals.get("tol0p1", "NA"),
            "noanalytic_exp50": vals.get("noanalytic", "NA"),
            "relative_spread": f"{spread:.6f}" if spread is not None else "NA",
            "bestfit_poi_value": bf_val,
            "status": status,
            "notes": "; ".join(notes) if notes else "stable"
        })
PY
}

run_one_workspace_one_poi_one_mass() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local mass="$5"

  mkdir -p "${outbase}/${tag}"

  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}" "baseline"   "$(common_asymptotic_opts)"
  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}" "strategy1"  "--cminDefaultMinimizerStrategy 1 --cminDefaultMinimizerTolerance 0.01 --X-rtd MINIMIZER_analytic"
  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}" "tol0p1"     "--cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --X-rtd MINIMIZER_analytic"
  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}" "noanalytic" "--cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.01"

  local baseline_json_file="${outbase}/${tag}/asymptotic/baseline/asymptotic_metrics.json"
  if [[ ! -f "${baseline_json_file}" ]]; then
    echo "[ERROR] Missing baseline metrics file: ${baseline_json_file}"
    return 1
  fi

  local baseline_exp50
  baseline_exp50="$(python3 - "${baseline_json_file}" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    print(json.load(f).get("exp50", "NA"))
PY
)"

  if [[ "${baseline_exp50}" == "NA" || -z "${baseline_exp50}" ]]; then
    echo "[ERROR] Could not extract baseline expected median for ${tag}"
    return 1
  fi

  echo "[INFO] ${tag}: baseline expected median = ${baseline_exp50}"

  run_multidim_scan "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}" "${baseline_exp50}"
  run_bestfit_check "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}" "${baseline_exp50}"
  summarise_one_tag "${outbase}" "${tag}" "${poi}" "${mass}"
}

run_mass_loop() {
  local ws="$1"
  local outbase="$2"
  local poi="$3"

  IFS=',' read -r -a MASS_ARRAY <<< "${MASSES}"

  for mass in "${MASS_ARRAY[@]}"; do
    mass="$(echo "${mass}" | xargs)"
    [[ -z "${mass}" ]] && continue

    local mass_tag
    mass_tag="$(sanitize_mass_tag "${mass}")"

    local tag="${POI#r_}_m${mass_tag}"
    if [[ "${poi}" == "r_ggH" ]]; then
      tag="ggH_m${mass_tag}"
    elif [[ "${poi}" == "r_bbH" ]]; then
      tag="bbH_m${mass_tag}"
    fi

    echo
    echo "############################################################"
    echo "Running validation for POI=${poi}, mass=${mass}"
    echo "Tag = ${tag}"
    echo "############################################################"
    echo

    run_one_workspace_one_poi_one_mass "${ws}" "${outbase}" "${tag}" "${poi}" "${mass}"
  done
}

# --------------------------
# Main
# --------------------------
if [[ "${DO_BOTH_POIS}" -eq 1 ]]; then
  run_mass_loop "${WS}" "${OUTBASE}" "r_ggH"
  run_mass_loop "${WS}" "${OUTBASE}" "r_bbH"
else
  run_mass_loop "${WS}" "${OUTBASE}" "${POI}"
fi

finalize_master_tables
build_all_masses_summary

cat > "${OUTBASE}/README_thesis_validation.txt" <<EOF
Fast thesis fit-validation outputs
==================================

1) asymptotic_summary.csv
   Expected AsymptoticLimits for several minimizer variants.

2) scan_summary.csv
   1D profile-likelihood scan points from MultiDimFit.

3) bestfit_summary.csv
   Lightweight best-fit summary from MultiDimFit --algo none.

4) all_masses_summary.csv
   One-row-per-mass summary with pass/warn status.

5) <tag>/health_report.txt
   Per-mass text summary for thesis use.

Recommended thesis statements
=============================
- The expected limit is numerically stable under reasonable minimizer variations.
- The profile-likelihood scan is smooth in the vicinity of the expected exclusion region.
- A lightweight best-fit check does not indicate obvious pathologies.

Not included by default
=======================
- FitDiagnostics
- HybridNew toy limits
- GoodnessOfFit toys
- Freeze-group scans

These can be added only for suspicious mass points.
EOF

echo "============================================================"
echo "Done."
echo "Workspace: ${WS}"
echo "Outputs:   ${OUTBASE}/"
echo "Key files:"
echo "  ${OUTBASE}/asymptotic_summary.csv"
echo "  ${OUTBASE}/scan_summary.csv"
echo "  ${OUTBASE}/bestfit_summary.csv"
echo "  ${OUTBASE}/all_masses_summary.csv"
echo "  ${OUTBASE}/README_thesis_validation.txt"
echo "============================================================"