#!/bin/bash
set -euo pipefail

# ============================================================
# Expected-limit validation / stability checks for MSSM workspace
#
# What this script does:
#   - Expected AsymptoticLimits with several minimizer variants
#   - Extracts median expected limits from logs
#   - Produces compact CSV summary tables
#   - Flags relative spread across variants
#   - Runs a 1D MultiDimFit scan for the chosen POI
#   - Optional freeze-group expected limit checks
#   - Optional alternate-workspace comparison
#   - Optional toy cross-checks with HybridNew
#
# Thesis-oriented outputs:
#   - asymptotic_summary.csv
#   - scan_summary.csv
#   - toy_summary.csv
#   - freeze_group_summary.csv
#   - per-tag health_report.txt
#   - per-tag toy_interpretation.txt
# ============================================================

# --------------------------
# Defaults
# --------------------------
WS="mssm_output/cmb/ws.root"
OUTBASE="mssm_output/cmb/expected_limit_validation"
MASS=2000
POI="r_ggH"
ALT_WS=""
DO_ALT_COMPARE=0
DO_FREEZE_GROUPS=0
DO_TOY_CROSSCHECK=0
DO_BOTH_POIS=0

REL_SPREAD_WARN=0.05
NTOYS=50
TOY_SEED=123456

BOUNDLIST=""

# Optional mass list if you later want mass-scan style jobs elsewhere
MASSES="60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,160,180,200,250,300,350,400,450,500,600,700,800,900,1000,1100,1200,1400,1600,1800,2000,2300,2600,2900,3200,3500"

# --------------------------
# Parse args
# --------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ws) WS="$2"; shift 2 ;;
    --outbase) OUTBASE="$2"; shift 2 ;;
    --mass) MASS="$2"; shift 2 ;;
    --poi) POI="$2"; shift 2 ;;
    --alt-ws) ALT_WS="$2"; DO_ALT_COMPARE=1; shift 2 ;;
    --freeze-groups) DO_FREEZE_GROUPS=1; shift ;;
    --toy-crosscheck) DO_TOY_CROSSCHECK=1; shift ;;
    --ntoys) NTOYS="$2"; shift 2 ;;
    --toy-seed) TOY_SEED="$2"; shift 2 ;;
    --boundlist) BOUNDLIST="$2"; shift 2 ;;
    --both-pois) DO_BOTH_POIS=1; shift ;;
    --spread-warn) REL_SPREAD_WARN="$2"; shift 2 ;;
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
rm -f "${OUTBASE}/toy_summary.csv"
rm -f "${OUTBASE}/freeze_group_summary.csv"
rm -f "${OUTBASE}/scan_summary.csv"
rm -f "${OUTBASE}/scan_summary_tmp.csv"

if [[ ! -f "${WS}" ]]; then
  echo "[ERROR] Workspace not found: ${WS}"
  exit 1
fi

if [[ "${DO_ALT_COMPARE}" -eq 1 ]]; then
  ALT_WS="$(realpath "${ALT_WS}")"
  if [[ ! -f "${ALT_WS}" ]]; then
    echo "[ERROR] Alternate workspace not found: ${ALT_WS}"
    exit 1
  fi
fi

# --------------------------
# Helpers
# --------------------------
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

common_minimizer_opts() {
  echo \
    --cminDefaultMinimizerStrategy 0 \
    --cminDefaultMinimizerTolerance 0.01 \
    --X-rtd MINIMIZER_analytic
}

append_master_csv_header_if_needed() {
  local file="$1"
  local header="$2"
  mkdir -p "$(dirname "${file}")"
  if [[ ! -f "${file}" ]]; then
    echo "${header}" > "${file}"
  fi
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

extract_hybrid_cls_from_log() {
  local logfile="$1"
  python3 - "$logfile" <<'PY'
import re, sys, json
txt = open(sys.argv[1], "r", encoding="utf-8", errors="ignore").read()

matches = re.findall(r"CLs\s*=\s*([0-9eE+.\-]+)\s*\+/-\s*([0-9eE+.\-]+)", txt)
pb = re.findall(r"1-Pb\s*=\s*([0-9eE+.\-]+)\s*\+/-\s*([0-9eE+.\-]+)", txt)
pmu = re.findall(r"Pmu\s*=\s*([0-9eE+.\-]+)\s*\+/-\s*([0-9eE+.\-]+)", txt)

out = {
    "cls":"NA",
    "cls_err":"NA",
    "one_minus_pb":"NA",
    "one_minus_pb_err":"NA",
    "pmu":"NA",
    "pmu_err":"NA"
}
if matches:
    out["cls"], out["cls_err"] = matches[-1]
if pb:
    out["one_minus_pb"], out["one_minus_pb_err"] = pb[-1]
if pmu:
    out["pmu"], out["pmu_err"] = pmu[-1]

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

dynamic_scan_range_from_exp50() {
  local exp50="$1"
  python3 - "$exp50" <<'PY'
import sys
mu = float(sys.argv[1])

hi = 2.0 * mu
hi = max(hi, 0.005)
hi = min(hi, 10.0)

print(f"0,{hi:.8g}")
PY
}

dynamic_toy_range_from_exp50() {
  local poi="$1"
  local exp50="$2"
  python3 - "$poi" "$exp50" <<'PY'
import sys
poi = sys.argv[1]
mu = float(sys.argv[2])

hi = 3.0 * mu
hi = max(hi, 0.01)
hi = min(hi, 10.0)

if poi == "r_ggH":
    print(f"r_ggH=0,{hi:.8g}:r_bbH=0,{hi:.8g}")
elif poi == "r_bbH":
    print(f"r_bbH=0,{hi:.8g}:r_ggH=0,{hi:.8g}")
else:
    print(f"r_ggH=0,{hi:.8g}:r_bbH=0,{hi:.8g}")
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
  local variant="$5"
  local extra_opts="$6"

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
    -m "${MASS}"
    -n ".${tag}.${variant}"
    -t -1
    --run expected
    --rAbsAcc 0
    --rRelAcc 0.0005
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
  echo "${tag},${poi},${MASS},${variant},${row}" >> "${outbase}/asymptotic_summary.csv"

  popd >/dev/null
}

run_multidim_scan() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local exp50="$5"

  outbase="$(realpath "${outbase}")"

  local outdir="${outbase}/${tag}/scan"
  mkdir -p "${outdir}"

  local freeze_arg
  freeze_arg="$(other_poi_freeze_arg "${poi}")"

  local scan_range
  scan_range="$(dynamic_scan_range_from_exp50 "${exp50}")"

  echo "============================================================"
  echo "[MultiDimFit scan] ${tag}"
  echo "Using dynamic scan range: ${scan_range}"
  echo "============================================================"

  pushd "${outdir}" >/dev/null

  combine -M MultiDimFit "${ws}" \
    -m "${MASS}" \
    -n ".${tag}.scan" \
    -t -1 \
    --algo grid \
    --points 81 \
    --alignEdges 1 \
    --robustFit 1 \
    $(combine_common_args "${poi}" "${freeze_arg}") \
    $(common_minimizer_opts) \
    --setParameterRanges "${poi}=${scan_range}" \
    </dev/null | tee "multidim_${tag}.log"

  local rootfile="higgsCombine.${tag}.scan.MultiDimFit.mH${MASS}.root"
  if [[ -f "${rootfile}" ]]; then
    extract_scan_to_csv "${rootfile}" "scan_points.csv"
    awk -F, -v tag="${tag}" -v poi="${poi}" -v mass="${MASS}" '
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

run_freeze_group_limit_scan() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local group_name="$5"
  local group_freeze="$6"

  local outdir="${outbase}/${tag}/freeze_groups/${group_name}"
  mkdir -p "${outdir}"

  local other
  other="$(other_poi_name "${poi}")"

  local combined_freeze=""
  if [[ -n "${other}" ]]; then
    combined_freeze="${other},${group_freeze}"
  else
    combined_freeze="${group_freeze}"
  fi

  echo "============================================================"
  echo "[FreezeGroup AsymptoticLimits] ${tag} :: ${group_name}"
  echo "============================================================"

  pushd "${outdir}" >/dev/null

  local cmd=(
    combine -M AsymptoticLimits "${ws}"
    -m "${MASS}"
    -n ".${tag}.${group_name}"
    -t -1
    --run expected
    --rAbsAcc 0
    --rRelAcc 0.0005
    -v 1
    --redefineSignalPOIs "${poi}"
    --setParameters r_ggH=0,r_bbH=0
    --freezeParameters "${combined_freeze}"
    $(common_minimizer_opts)
  )

  if [[ -n "${BOUNDLIST}" ]]; then
    cmd+=( --boundlist "${BOUNDLIST}" )
  fi

  "${cmd[@]}" </dev/null | tee "freeze_${group_name}.log" || true

  local json
  json="$(extract_asymptotic_metrics_from_log "freeze_${group_name}.log")"
  echo "${json}" > "freeze_metrics.json"

  append_master_csv_header_if_needed "${outbase}/freeze_group_summary.csv" \
    "tag,poi,mass,group_name,observed,exp2p5,exp16,exp50,exp84,exp97p5"

  local row
  row="$(write_json_value_to_csv_row "${json}" "observed,exp2p5,exp16,exp50,exp84,exp97p5")"
  echo "${tag},${poi},${MASS},${group_name},${row}" >> "${outbase}/freeze_group_summary.csv"

  popd >/dev/null
}

run_toy_crosscheck() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"
  local exp50="$5"

  local outdir="${outbase}/${tag}/toy_crosscheck"
  mkdir -p "${outdir}"

  local freeze_arg
  freeze_arg="$(other_poi_freeze_arg "${poi}")"

  local asym_med="${exp50}"
  local toy_ranges
  toy_ranges="$(dynamic_toy_range_from_exp50 "${poi}" "${asym_med}")"

  echo "============================================================"
  echo "[Toy cross-check] ${tag}"
  echo "Using asymptotic median expected: ${asym_med}"
  echo "Using dynamic toy ranges: ${toy_ranges}"
  echo "============================================================"

  pushd "${outdir}" >/dev/null

  echo "Asymptotic median expected: ${asym_med}" > toy_summary.txt

  if [[ "${asym_med}" == "NA" || -z "${asym_med}" ]]; then
    echo "[ERROR] Could not extract asymptotic median; skipping toys." | tee -a toy_summary.txt
    popd >/dev/null
    return 1
  fi

  python3 - "${asym_med}" > toy_points.txt <<'PY'
import sys
mu = float(sys.argv[1])
for p in [0.5*mu, 0.8*mu, 1.0*mu, 1.2*mu, 1.5*mu]:
    print(f"{p:.8g}")
PY

  echo "[INFO] HybridNew test points:" | tee -a toy_summary.txt
  cat toy_points.txt | tee -a toy_summary.txt

  append_master_csv_header_if_needed "${outbase}/toy_summary.csv" \
    "tag,poi,mass,test_mu,cls,cls_err,one_minus_pb,one_minus_pb_err,pmu,pmu_err"

  while read -r point; do
    local safe_point
    safe_point="${point//./p}"

    echo "[Toy cross-check] singlePoint=${point}"

    combine -M HybridNew "${ws}" \
      -m "${MASS}" \
      -n ".${tag}.hybrid.${safe_point}" \
      -T "${NTOYS}" \
      -i 1 \
      --frequentist \
      --LHCmode LHC-limits \
      --singlePoint "${point}" \
      --saveHybridResult \
      -v 1 \
      -s "${TOY_SEED}" \
      $(combine_common_args "${poi}" "${freeze_arg}") \
      $(common_minimizer_opts) \
      --setParameterRanges "${toy_ranges}" \
      </dev/null | tee "hybrid_${safe_point}.log" || true

    local toy_json
    toy_json="$(extract_hybrid_cls_from_log "hybrid_${safe_point}.log")"
    echo "${toy_json}" > "hybrid_${safe_point}.json"

    local row
    row="$(write_json_value_to_csv_row "${toy_json}" "cls,cls_err,one_minus_pb,one_minus_pb_err,pmu,pmu_err")"
    echo "${tag},${poi},${MASS},${point},${row}" >> "${outbase}/toy_summary.csv"
  done < toy_points.txt

  python3 - "${outbase}/toy_summary.csv" "${tag}" "${poi}" "${MASS}" "${asym_med}" > toy_interpretation.txt <<'PY'
import csv, sys
fname, tag, poi, mass, asym_med = sys.argv[1:]
rows = []
with open(fname) as f:
    r = csv.DictReader(f)
    for row in r:
        if row["tag"] == tag and row["poi"] == poi and row["mass"] == mass:
            try:
                rows.append((float(row["test_mu"]), float(row["cls"]), float(row["cls_err"])))
            except:
                pass

print("Toy cross-check summary")
print("=======================")
print(f"POI = {poi}")
print(f"mass = {mass}")
print(f"Asymptotic median expected = {asym_med}")
print()

if not rows:
    print("No toy rows found.")
    sys.exit(0)

rows.sort()
for mu, cls, err in rows:
    print(f"mu = {mu:.6g}   CLs = {cls:.6g} +/- {err:.6g}")

mono = all(rows[i][1] >= rows[i+1][1] for i in range(len(rows)-1))
closest = min(rows, key=lambda x: abs(x[1]-0.05))

print()
print(f"Monotonic decrease of CLs with mu: {'YES' if mono else 'NO'}")
print(f"Closest point to CLs=0.05: mu = {closest[0]:.6g}, CLs = {closest[1]:.6g} +/- {closest[2]:.6g}")
PY

  cat toy_interpretation.txt >> toy_summary.txt
  popd >/dev/null
}

summarise_variant_results() {
  local outbase="$1"
  local tag="$2"
  local poi="$3"

  local summary="${outbase}/${tag}/summary_table.csv"
  mkdir -p "${outbase}/${tag}"

  if [[ ! -f "${outbase}/asymptotic_summary.csv" ]]; then
    cat > "${summary}" <<EOF
tag,poi,mass,variant,observed,exp2p5,exp16,exp50,exp84,exp97p5
EOF
    cat > "${outbase}/${tag}/health_report.txt" <<EOF
Expected-limit health report
===========================
POI = ${poi}
mass = ${MASS}

Status: UNDECIDED
Reason: missing asymptotic_summary.csv.
EOF
    return 0
  fi

  python3 - "${outbase}/asymptotic_summary.csv" "${tag}" "${poi}" "${MASS}" "${summary}" "${REL_SPREAD_WARN}" "${outbase}/${tag}/health_report.txt" <<'PY'
import csv, sys
source, tag, poi, mass, outcsv, warnthr, report = sys.argv[1:]
warnthr = float(warnthr)

rows = []
with open(source) as f:
    r = csv.DictReader(f)
    for row in r:
        if row["tag"] == tag and row["poi"] == poi and row["mass"] == mass:
            rows.append(row)

with open(outcsv, "w", newline="") as f:
    if rows:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    else:
        f.write("tag,poi,mass,variant,observed,exp2p5,exp16,exp50,exp84,exp97p5\n")

vals = {}
for row in rows:
    try:
        vals[row["variant"]] = float(row["exp50"])
    except:
        vals[row["variant"]] = None

baseline = vals.get("baseline")
valid = [v for v in vals.values() if v is not None]

with open(report, "w") as out:
    out.write("Expected-limit health report\n")
    out.write("===========================\n")
    out.write(f"POI = {poi}\n")
    out.write(f"mass = {mass}\n\n")
    for k in ["baseline","strategy1","tol0p1","noanalytic"]:
        out.write(f"{k:10s}: {vals.get(k)}\n")

    if baseline is None or baseline == 0 or not valid:
        out.write("\nStatus: UNDECIDED\n")
        out.write("Reason: missing asymptotic expected entries.\n")
        sys.exit(0)

    vmin = min(valid)
    vmax = max(valid)
    spread = (vmax - vmin) / abs(baseline)

    out.write(f"\nBaseline median expected = {baseline}\n")
    out.write(f"Min median expected      = {vmin}\n")
    out.write(f"Max median expected      = {vmax}\n")
    out.write(f"Relative spread          = {spread:.6f}\n")

    if spread > warnthr:
        out.write("\nStatus: WARNING\n")
        out.write(f"Relative spread exceeds threshold {warnthr:.3f}\n")
    else:
        out.write("\nStatus: OK\n")
        out.write(f"Relative spread within threshold {warnthr:.3f}\n")
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

run_one_workspace_one_poi() {
  local ws="$1"
  local outbase="$2"
  local tag="$3"
  local poi="$4"

  mkdir -p "${outbase}/${tag}"

  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "baseline"  "$(common_minimizer_opts)"
  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "strategy1" "--cminDefaultMinimizerStrategy 1 --cminDefaultMinimizerTolerance 0.01 --X-rtd MINIMIZER_analytic"
  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "tol0p1"   "--cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --X-rtd MINIMIZER_analytic"
  run_asymptotic_variant "${ws}" "${outbase}" "${tag}" "${poi}" "noanalytic" "--cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.01"

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
    echo "[ERROR] Check ${outbase}/${tag}/asymptotic/baseline/asymptotic_${tag}_baseline.log"
    return 1
  fi

  echo "[INFO] ${tag}: baseline expected median = ${baseline_exp50}"

  run_multidim_scan "${ws}" "${outbase}" "${tag}" "${poi}" "${baseline_exp50}"

  if [[ "${DO_FREEZE_GROUPS}" -eq 1 ]]; then
    run_freeze_group_limit_scan "${ws}" "${outbase}" "${tag}" "${poi}" "bbb"      "rgx{prop_bin.*}"
    run_freeze_group_limit_scan "${ws}" "${outbase}" "${tag}" "${poi}" "fake"     "rgx{CMS_MSSM_fake_t_.*}"
    run_freeze_group_limit_scan "${ws}" "${outbase}" "${tag}" "${poi}" "trig"     "rgx{CMS_MSSM_trig_.*}"
    run_freeze_group_limit_scan "${ws}" "${outbase}" "${tag}" "${poi}" "taueff"   "rgx{CMS_MSSM_eff_t_.*}"
    run_freeze_group_limit_scan "${ws}" "${outbase}" "${tag}" "${poi}" "tauscale" "rgx{CMS_MSSM_scale_t_.*}"
  fi

  if [[ "${DO_TOY_CROSSCHECK}" -eq 1 ]]; then
    run_toy_crosscheck "${ws}" "${outbase}" "${tag}" "${poi}" "${baseline_exp50}"
  fi

  summarise_variant_results "${outbase}" "${tag}" "${poi}"
}

# --------------------------
# Main
# --------------------------
if [[ "${DO_BOTH_POIS}" -eq 1 ]]; then
  run_one_workspace_one_poi "${WS}" "${OUTBASE}" "ggH_main" "r_ggH"
  run_one_workspace_one_poi "${WS}" "${OUTBASE}" "bbH_main" "r_bbH"
else
  run_one_workspace_one_poi "${WS}" "${OUTBASE}" "${POI#r_}_main" "${POI}"
fi

if [[ "${DO_ALT_COMPARE}" -eq 1 ]]; then
  if [[ "${DO_BOTH_POIS}" -eq 1 ]]; then
    run_one_workspace_one_poi "${ALT_WS}" "${OUTBASE}/alt_workspace" "ggH_alt" "r_ggH"
    run_one_workspace_one_poi "${ALT_WS}" "${OUTBASE}/alt_workspace" "bbH_alt" "r_bbH"
  else
    run_one_workspace_one_poi "${ALT_WS}" "${OUTBASE}/alt_workspace" "${POI#r_}_alt" "${POI}"
  fi
fi

finalize_master_tables

cat > "${OUTBASE}/README_thesis_outputs.txt" <<EOF
Files produced for thesis validation
===================================

1) asymptotic_summary.csv
   One row per minimizer variant with observed and expected asymptotic limits.

2) scan_summary.csv
   1D profile-likelihood scan points extracted from MultiDimFit.
   Plot: deltaNLL vs POI.

3) toy_summary.csv
   Toy-based CLs values at points around the asymptotic median expected limit.
   Plot: CLs vs tested signal strength, with a horizontal line at CLs=0.05.

4) freeze_group_summary.csv
   Expected limits with specific nuisance groups frozen.
   Plot: expected median limit vs frozen group.

5) <tag>/health_report.txt
   Plain-text verdict on minimizer stability for the expected median limit.

6) <tag>/toy_crosscheck/toy_interpretation.txt
   Plain-text summary of toy-based validation near the asymptotic crossing.

Suggested thesis statements
===========================
- The expected asymptotic limit is stable under reasonable minimizer variations.
- The 1D profile-likelihood scan is smooth in the vicinity of the expected limit.
- Toy-based CLs values decrease with increasing tested signal strength and are consistent with the asymptotic expected limit scale.
- Freezing nuisance groups provides a controlled cross-check of sensitivity to dominant systematic sectors.
EOF

echo "============================================================"
echo "Done."
echo
echo "Main workspace:"
echo "  ${WS}"
if [[ "${DO_ALT_COMPARE}" -eq 1 ]]; then
  echo "Alternate workspace:"
  echo "  ${ALT_WS}"
fi
echo
echo "Outputs under:"
echo "  ${OUTBASE}/"
echo "Key files:"
echo "  ${OUTBASE}/asymptotic_summary.csv"
echo "  ${OUTBASE}/scan_summary.csv"
echo "  ${OUTBASE}/toy_summary.csv"
echo "  ${OUTBASE}/freeze_group_summary.csv   (if enabled)"
echo "  ${OUTBASE}/README_thesis_outputs.txt"
echo "============================================================"