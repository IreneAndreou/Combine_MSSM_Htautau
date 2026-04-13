#!/bin/bash

set -euo pipefail

ERA=$1
CHANNEL=$2
CATEGORY=$3
DIR=$4
MODE=${5:-local}
MASS=${6:-125}
NUM_TOYS_PER_SEED=${7:-50}

# Two-POI background-only hypothesis
POI_VALUES="r_ggH=0,r_bbH=0"
POI_FREEZE="r_ggH,r_bbH"

if [[ "$MODE" != "local" && "$MODE" != "submit" ]]; then
    echo "[ERROR] Given mode '$MODE' not known. Use: local or submit"
    exit 1
fi

if [[ "${ERA}" == "combined" ]]; then
    ID=${ERA}
elif [[ "${CHANNEL}" == "cmb" ]]; then
    ID=${ERA}
elif [[ "${CATEGORY}" == "all" ]]; then
    ID=${ERA}-${CHANNEL}
else
    ID=${ERA}-${CHANNEL}-${CATEGORY}
fi

pushd "$DIR" >/dev/null || exit 1

if [[ -f utils/setup_cmssw.sh ]]; then
    source /cvmfs/cms.cern.ch/cmsset_default.sh
else
    echo "[WARN] /cvmfs/cms.cern.ch/cmsset_default.sh not found, assuming CMSSW is already set up"
fi

ulimit -s unlimited


# Select workspace/datacard and output directory based on channel/category
if [[ "${CHANNEL}" == "cmb" && "${CATEGORY}" == "all" ]]; then
    DATACARD="${PWD}/mssm_output_no_morph/cmb/ws_${MASS}.root"
elif [[ "${CATEGORY}" == "all" ]]; then
    DATACARD="${PWD}/mssm_output_no_morph/cmb/${CHANNEL}_ws_${MASS}.root"
elif [[ "${CHANNEL}" != "cmb" && "${CATEGORY}" != "all" ]]; then
    DATACARD="${PWD}/mssm_output_no_morph/cmb/${CHANNEL}_${CATEGORY}_ws_${MASS}.root"
else
    # fallback to combined if ambiguous
    DATACARD="${PWD}/mssm_output_no_morph/cmb/ws_${MASS}.root"
fi

WORKDIR=$(dirname "${DATACARD}")
OUTDIR="${WORKDIR}/gof_observed/${ID}/m${MASS}"
mkdir -p "${OUTDIR}"

pushd "${WORKDIR}" >/dev/null || exit 1

# Optional titles
TITLE="${ERA}, ${CHANNEL}, ${CATEGORY}"
TITLE_LEFT="CMS"

for ALGO in saturated
do
    echo "============================================================"
    echo "Observed GoF for ${ID}, m=${MASS}, algo=${ALGO}, background-only"
    echo "Workspace: ${DATACARD}"
    echo "============================================================"

    # Clean stale outputs for this configuration
    rm -f "higgsCombineTest.${ID}.${ALGO}.obs.GoodnessOfFit.mH${MASS}.root"
    rm -f higgsCombineTest."${ID}"."${ALGO}".toys.GoodnessOfFit.mH"${MASS}".*.root

    # Observed GoF on data
    combine -M GoodnessOfFit \
        -n "Test.${ID}.${ALGO}.obs" \
        --algo="${ALGO}" \
        -m "${MASS}" \
        -d "${DATACARD}" \
        -v 1 \
        --fixedSignalStrength 0 \
        --setParameters "${POI_VALUES}" \
        --freezeParameters "${POI_FREEZE}" \

    TOYSOPT="--toysFreq"

    case "$MODE" in
        local)
            combineTool.py -M GoodnessOfFit \
                -n "Test.${ID}.${ALGO}.toys" \
                --algo="${ALGO}" \
                -m "${MASS}" \
                -d "${DATACARD}" \
                -s 1230:1239:1 \
                -t "${NUM_TOYS_PER_SEED}" \
                ${TOYSOPT} \
                --fixedSignalStrength 0 \
                --setParameters "${POI_VALUES}" \
                --freezeParameters "${POI_FREEZE}" \
                --parallel 10 \
            ;;
        submit)
            combineTool.py -M GoodnessOfFit \
                -n "Test.${ID}.${ALGO}.toys" \
                --algo="${ALGO}" \
                -m "${MASS}" \
                -d "${DATACARD}" \
                -s 1230:1239:1 \
                -t "${NUM_TOYS_PER_SEED}" \
                ${TOYSOPT} \
                --fixedSignalStrength 0 \
                --job-mode condor \
                --task-name "gof-${ID}-${ALGO}-m${MASS}" \
                --sub-opts='+MaxRuntime=10800' \
            ;;
    esac

    OBS_FILE="higgsCombineTest.${ID}.${ALGO}.obs.GoodnessOfFit.mH${MASS}.root"

    if [[ ! -f "${OBS_FILE}" ]]; then
        echo "[ERROR] Observed GoF output ${OBS_FILE} not found"
        exit 1
    fi

    INPUTS=()
    for SEED in {1230..1239}; do
        TOY_FILE="higgsCombineTest.${ID}.${ALGO}.toys.GoodnessOfFit.mH${MASS}.${SEED}.root"
        if [[ -f "${TOY_FILE}" ]]; then
            INPUTS+=("${TOY_FILE}")
        else
            echo "[WARN] Missing toy file: ${TOY_FILE}"
        fi
    done

    if [[ ${#INPUTS[@]} -eq 0 ]]; then
        echo "[ERROR] No toy files found for collection"
        exit 1
    fi

    combineTool.py -M CollectGoodnessOfFit \
        --input "${OBS_FILE}" "${INPUTS[@]}" \
        --output "${OUTDIR}/gof.json"

    plotGof.py \
        --statistic "${ALGO}" \
        --mass "${MASS}.0" \
        --output gof \
        "${OUTDIR}/gof.json" \
        --title-right="${TITLE}" \
        --title-left="${TITLE_LEFT}, obs., background-only"

    mv gof.pdf "${OUTDIR}/" 2>/dev/null || true
    mv gof.png "${OUTDIR}/" 2>/dev/null || true
done

popd >/dev/null || exit 1
popd >/dev/null || exit 1