output_dir=$1
working_pointVsJets=$2
working_pointVsEle=$3
era=$4

if [ "${era}" == "UL" ]; then
 echo ${era}
 pois="rate_tauSF_DM0_pT20to25_2016_preVFP,rate_tauSF_DM0_pT25to30_2016_preVFP,rate_tauSF_DM0_pT30to35_2016_preVFP,rate_tauSF_DM0_pT35to40_2016_preVFP,rate_tauSF_DM0_pT40to50_2016_preVFP,rate_tauSF_DM0_pT50to60_2016_preVFP,rate_tauSF_DM0_pT60to80_2016_preVFP,rate_tauSF_DM0_pT80to100_2016_preVFP,rate_tauSF_DM0_pT100to200_2016_preVFP,rate_tauSF_DM1_pT20to25_2016_preVFP,rate_tauSF_DM1_pT25to30_2016_preVFP,rate_tauSF_DM1_pT30to35_2016_preVFP,rate_tauSF_DM1_pT35to40_2016_preVFP,rate_tauSF_DM1_pT40to50_2016_preVFP,rate_tauSF_DM1_pT50to60_2016_preVFP,rate_tauSF_DM1_pT60to80_2016_preVFP,rate_tauSF_DM1_pT80to100_2016_preVFP,rate_tauSF_DM1_pT100to200_2016_preVFP,rate_tauSF_DM10_pT20to25_2016_preVFP,rate_tauSF_DM10_pT25to30_2016_preVFP,rate_tauSF_DM10_pT30to35_2016_preVFP,rate_tauSF_DM10_pT35to40_2016_preVFP,rate_tauSF_DM10_pT40to50_2016_preVFP,rate_tauSF_DM10_pT50to60_2016_preVFP,rate_tauSF_DM10_pT60to80_2016_preVFP,rate_tauSF_DM10_pT80to100_2016_preVFP,rate_tauSF_DM10_pT100to200_2016_preVFP,rate_tauSF_DM11_pT20to25_2016_preVFP,rate_tauSF_DM11_pT25to30_2016_preVFP,rate_tauSF_DM11_pT30to35_2016_preVFP,rate_tauSF_DM11_pT35to40_2016_preVFP,rate_tauSF_DM11_pT40to50_2016_preVFP,rate_tauSF_DM11_pT50to60_2016_preVFP,rate_tauSF_DM11_pT60to80_2016_preVFP,rate_tauSF_DM11_pT80to100_2016_preVFP,rate_tauSF_DM11_pT100to200_2016_preVFP,rate_tauSF_DM0_pT20to25_2016_postVFP,rate_tauSF_DM0_pT25to30_2016_postVFP,rate_tauSF_DM0_pT30to35_2016_postVFP,rate_tauSF_DM0_pT35to40_2016_postVFP,rate_tauSF_DM0_pT40to50_2016_postVFP,rate_tauSF_DM0_pT50to60_2016_postVFP,rate_tauSF_DM0_pT60to80_2016_postVFP,rate_tauSF_DM0_pT80to100_2016_postVFP,rate_tauSF_DM0_pT100to200_2016_postVFP,rate_tauSF_DM1_pT20to25_2016_postVFP,rate_tauSF_DM1_pT25to30_2016_postVFP,rate_tauSF_DM1_pT30to35_2016_postVFP,rate_tauSF_DM1_pT35to40_2016_postVFP,rate_tauSF_DM1_pT40to50_2016_postVFP,rate_tauSF_DM1_pT50to60_2016_postVFP,rate_tauSF_DM1_pT60to80_2016_postVFP,rate_tauSF_DM1_pT80to100_2016_postVFP,rate_tauSF_DM1_pT100to200_2016_postVFP,rate_tauSF_DM10_pT20to25_2016_postVFP,rate_tauSF_DM10_pT25to30_2016_postVFP,rate_tauSF_DM10_pT30to35_2016_postVFP,rate_tauSF_DM10_pT35to40_2016_postVFP,rate_tauSF_DM10_pT40to50_2016_postVFP,rate_tauSF_DM10_pT50to60_2016_postVFP,rate_tauSF_DM10_pT60to80_2016_postVFP,rate_tauSF_DM10_pT80to100_2016_postVFP,rate_tauSF_DM10_pT100to200_2016_postVFP,rate_tauSF_DM11_pT20to25_2016_postVFP,rate_tauSF_DM11_pT25to30_2016_postVFP,rate_tauSF_DM11_pT30to35_2016_postVFP,rate_tauSF_DM11_pT35to40_2016_postVFP,rate_tauSF_DM11_pT40to50_2016_postVFP,rate_tauSF_DM11_pT50to60_2016_postVFP,rate_tauSF_DM11_pT60to80_2016_postVFP,rate_tauSF_DM11_pT80to100_2016_postVFP,rate_tauSF_DM11_pT100to200_2016_postVFP,rate_tauSF_DM0_pT20to25_2017,rate_tauSF_DM0_pT25to30_2017,rate_tauSF_DM0_pT30to35_2017,rate_tauSF_DM0_pT35to40_2017,rate_tauSF_DM0_pT40to50_2017,rate_tauSF_DM0_pT50to60_2017,rate_tauSF_DM0_pT60to80_2017,rate_tauSF_DM0_pT80to100_2017,rate_tauSF_DM0_pT100to200_2017,rate_tauSF_DM1_pT20to25_2017,rate_tauSF_DM1_pT25to30_2017,rate_tauSF_DM1_pT30to35_2017,rate_tauSF_DM1_pT35to40_2017,rate_tauSF_DM1_pT40to50_2017,rate_tauSF_DM1_pT50to60_2017,rate_tauSF_DM1_pT60to80_2017,rate_tauSF_DM1_pT80to100_2017,rate_tauSF_DM1_pT100to200_2017,rate_tauSF_DM10_pT20to25_2017,rate_tauSF_DM10_pT25to30_2017,rate_tauSF_DM10_pT30to35_2017,rate_tauSF_DM10_pT35to40_2017,rate_tauSF_DM10_pT40to50_2017,rate_tauSF_DM10_pT50to60_2017,rate_tauSF_DM10_pT60to80_2017,rate_tauSF_DM10_pT80to100_2017,rate_tauSF_DM10_pT100to200_2017,rate_tauSF_DM11_pT20to25_2017,rate_tauSF_DM11_pT25to30_2017,rate_tauSF_DM11_pT30to35_2017,rate_tauSF_DM11_pT35to40_2017,rate_tauSF_DM11_pT40to50_2017,rate_tauSF_DM11_pT50to60_2017,rate_tauSF_DM11_pT60to80_2017,rate_tauSF_DM11_pT80to100_2017,rate_tauSF_DM11_pT100to200_2017,rate_tauSF_DM0_pT20to25_2018,rate_tauSF_DM0_pT25to30_2018,rate_tauSF_DM0_pT30to35_2018,rate_tauSF_DM0_pT35to40_2018,rate_tauSF_DM0_pT40to50_2018,rate_tauSF_DM0_pT50to60_2018,rate_tauSF_DM0_pT60to80_2018,rate_tauSF_DM0_pT80to100_2018,rate_tauSF_DM0_pT100to200_2018,rate_tauSF_DM1_pT20to25_2018,rate_tauSF_DM1_pT25to30_2018,rate_tauSF_DM1_pT30to35_2018,rate_tauSF_DM1_pT35to40_2018,rate_tauSF_DM1_pT40to50_2018,rate_tauSF_DM1_pT50to60_2018,rate_tauSF_DM1_pT60to80_2018,rate_tauSF_DM1_pT80to100_2018,rate_tauSF_DM1_pT100to200_2018,rate_tauSF_DM10_pT20to25_2018,rate_tauSF_DM10_pT25to30_2018,rate_tauSF_DM10_pT30to35_2018,rate_tauSF_DM10_pT35to40_2018,rate_tauSF_DM10_pT40to50_2018,rate_tauSF_DM10_pT50to60_2018,rate_tauSF_DM10_pT60to80_2018,rate_tauSF_DM10_pT80to100_2018,rate_tauSF_DM10_pT100to200_2018,rate_tauSF_DM11_pT20to25_2018,rate_tauSF_DM11_pT25to30_2018,rate_tauSF_DM11_pT30to35_2018,rate_tauSF_DM11_pT35to40_2018,rate_tauSF_DM11_pT40to50_2018,rate_tauSF_DM11_pT50to60_2018,rate_tauSF_DM11_pT60to80_2018,rate_tauSF_DM11_pT80to100_2018,rate_tauSF_DM11_pT100to200_2018"
fi

if [ "${era}" == "2022" ]; then
 echo ${era}
 pois="rate_tauSF_DM0_pT20to25_2022_preEE,rate_tauSF_DM0_pT25to30_2022_preEE,rate_tauSF_DM0_pT30to35_2022_preEE,rate_tauSF_DM0_pT35to40_2022_preEE,rate_tauSF_DM0_pT40to50_2022_preEE,rate_tauSF_DM0_pT50to60_2022_preEE,rate_tauSF_DM0_pT60to80_2022_preEE,rate_tauSF_DM0_pT80to100_2022_preEE,rate_tauSF_DM0_pT100to200_2022_preEE,rate_tauSF_DM1_pT20to25_2022_preEE,rate_tauSF_DM1_pT25to30_2022_preEE,rate_tauSF_DM1_pT30to35_2022_preEE,rate_tauSF_DM1_pT35to40_2022_preEE,rate_tauSF_DM1_pT40to50_2022_preEE,rate_tauSF_DM1_pT50to60_2022_preEE,rate_tauSF_DM1_pT60to80_2022_preEE,rate_tauSF_DM1_pT80to100_2022_preEE,rate_tauSF_DM1_pT100to200_2022_preEE,rate_tauSF_DM10_pT20to25_2022_preEE,rate_tauSF_DM10_pT25to30_2022_preEE,rate_tauSF_DM10_pT30to35_2022_preEE,rate_tauSF_DM10_pT35to40_2022_preEE,rate_tauSF_DM10_pT40to50_2022_preEE,rate_tauSF_DM10_pT50to60_2022_preEE,rate_tauSF_DM10_pT60to80_2022_preEE,rate_tauSF_DM10_pT80to100_2022_preEE,rate_tauSF_DM10_pT100to200_2022_preEE,rate_tauSF_DM11_pT20to25_2022_preEE,rate_tauSF_DM11_pT25to30_2022_preEE,rate_tauSF_DM11_pT30to35_2022_preEE,rate_tauSF_DM11_pT35to40_2022_preEE,rate_tauSF_DM11_pT40to50_2022_preEE,rate_tauSF_DM11_pT50to60_2022_preEE,rate_tauSF_DM11_pT60to80_2022_preEE,rate_tauSF_DM11_pT80to100_2022_preEE,rate_tauSF_DM11_pT100to200_2022_preEE,rate_tauSF_DM0_pT20to25_2022_postEE,rate_tauSF_DM0_pT25to30_2022_postEE,rate_tauSF_DM0_pT30to35_2022_postEE,rate_tauSF_DM0_pT35to40_2022_postEE,rate_tauSF_DM0_pT40to50_2022_postEE,rate_tauSF_DM0_pT50to60_2022_postEE,rate_tauSF_DM0_pT60to80_2022_postEE,rate_tauSF_DM0_pT80to100_2022_postEE,rate_tauSF_DM0_pT100to200_2022_postEE,rate_tauSF_DM1_pT20to25_2022_postEE,rate_tauSF_DM1_pT25to30_2022_postEE,rate_tauSF_DM1_pT30to35_2022_postEE,rate_tauSF_DM1_pT35to40_2022_postEE,rate_tauSF_DM1_pT40to50_2022_postEE,rate_tauSF_DM1_pT50to60_2022_postEE,rate_tauSF_DM1_pT60to80_2022_postEE,rate_tauSF_DM1_pT80to100_2022_postEE,rate_tauSF_DM1_pT100to200_2022_postEE,rate_tauSF_DM10_pT20to25_2022_postEE,rate_tauSF_DM10_pT25to30_2022_postEE,rate_tauSF_DM10_pT30to35_2022_postEE,rate_tauSF_DM10_pT35to40_2022_postEE,rate_tauSF_DM10_pT40to50_2022_postEE,rate_tauSF_DM10_pT50to60_2022_postEE,rate_tauSF_DM10_pT60to80_2022_postEE,rate_tauSF_DM10_pT80to100_2022_postEE,rate_tauSF_DM10_pT100to200_2022_postEE,rate_tauSF_DM11_pT20to25_2022_postEE,rate_tauSF_DM11_pT25to30_2022_postEE,rate_tauSF_DM11_pT30to35_2022_postEE,rate_tauSF_DM11_pT35to40_2022_postEE,rate_tauSF_DM11_pT40to50_2022_postEE,rate_tauSF_DM11_pT50to60_2022_postEE,rate_tauSF_DM11_pT60to80_2022_postEE,rate_tauSF_DM11_pT80to100_2022_postEE,rate_tauSF_DM11_pT100to200_2022_postEE"
fi

if [ "${working_pointVsEle}" == True ]; then
 python scripts/harvestDatacards_newQCD_uncerts.py --dm-bins -o "outputs/${output_dir}" --wp "${working_pointVsJets}" --tightVsEle --useCRs

else
 python scripts/harvestDatacards_newQCD_uncerts.py --dm-bins -o "outputs/${output_dir}" --wp "${working_pointVsJets}"  --useCRs
fi

#fix combine memory issues
ulimit -s unlimited

combineTool.py -M T2W -i outputs/${output_dir}/cmb/ -o ws.root --X-allow-no-signal

echo "Running first fit"

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -n ".ztt.bestfit.singles" -d outputs/${output_dir}/cmb/ws.root --freezeNuisanceGroups TES

echo "Running snapshot fit"

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -d outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.MultiDimFit.mH125.root -n ".ztt.bestfit.singles.postfit" --snapshotName MultiDimFit --freezeNuisanceGroups TES

echo "Running TES up fit"

tes_up='--setParameters CMS_scale_t_1prong_2016_preVFP=1,CMS_scale_t_1prong_2016_postVFP=1,CMS_scale_t_1prong_2017=1,CMS_scale_t_1prong_2018=1,CMS_scale_t_1prong1pizero_2016_preVFP=1,CMS_scale_t_1prong1pizero_2016_postVFP=1,CMS_scale_t_1prong1pizero_2017=1,CMS_scale_t_1prong1pizero_2018=1,CMS_scale_t_3prong_2016_preVFP=1,CMS_scale_t_3prong_2016_postVFP=1,CMS_scale_t_3prong_2017=1,CMS_scale_t_3prong_2018=1,CMS_scale_t_3prong1pizero_2016_preVFP=1,CMS_scale_t_3prong1pizero_2016_postVFP=1,CMS_scale_t_3prong1pizero_2017=1,CMS_scale_t_3prong1pizero_2018=1'

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -d outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.MultiDimFit.mH125.root -n ".ztt.bestfit.singles.postfit.TESUp" --snapshotName MultiDimFit --freezeNuisanceGroups TES ${tes_up}

echo "Running TES down fit"

tes_down='--setParameters CMS_scale_t_1prong_2016_preVFP=-1,CMS_scale_t_1prong_2016_postVFP=-1,CMS_scale_t_1prong_2017=-1,CMS_scale_t_1prong_2018=-1,CMS_scale_t_1prong1pizero_2016_preVFP=-1,CMS_scale_t_1prong1pizero_2016_postVFP=-1,CMS_scale_t_1prong1pizero_2017=-1,CMS_scale_t_1prong1pizero_2018=-1,CMS_scale_t_3prong_2016_preVFP=-1,CMS_scale_t_3prong_2016_postVFP=-1,CMS_scale_t_3prong_2017=-1,CMS_scale_t_3prong_2018=-1,CMS_scale_t_3prong1pizero_2016_preVFP=-1,CMS_scale_t_3prong1pizero_2016_postVFP=-1,CMS_scale_t_3prong1pizero_2017=-1,CMS_scale_t_3prong1pizero_2018=-1'

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -d outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.MultiDimFit.mH125.root -n ".ztt.bestfit.singles.postfit.TESDown" --snapshotName MultiDimFit --freezeNuisanceGroups TES ${tes_down}

echo "Running snapshot fit with byErasAndBins frozen"

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -d outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.MultiDimFit.mH125.root -n ".ztt.bestfit.singles.postfit.freeze_byErasAndBins" --snapshotName MultiDimFit  --freezeNuisanceGroups TES,byErasAndBins

echo "Running snapshot fit with byErasAndBins and byBins frozen"

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -d outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.MultiDimFit.mH125.root -n ".ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins" --snapshotName MultiDimFit  --freezeNuisanceGroups TES,byErasAndBins,byBins

echo "Running snapshot fit with byErasAndBins, byBins, and byDM frozen"

combineTool.py -m 125 -M MultiDimFit --redefineSignalPOIs "${pois}" --saveWorkspace --X-rtd MINIMIZER_analytic --expectSignal 0 --cminDefaultMinimizerStrategy 0 --cminDefaultMinimizerTolerance 0.1 --algo singles --cl=0.68 --there -d outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.MultiDimFit.mH125.root -n ".ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins_byDM" --snapshotName MultiDimFit   --freezeNuisanceGroups TES,byErasAndBins,byBins,byDM0,byDM1,byDM10,byDM11


echo "Making graphs with SFs"

if [ "${working_pointVsEle}" == True ]; then
  for x in .freeze_byErasAndBins .freeze_byErasAndBins_byBins .freeze_byErasAndBins_byBins_byDM .TESUp .TESDown ""; do python scripts/makeSFGraphs.py  -f outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.postfit${x}.MultiDimFit.mH125.root --dm-bins --saveJson --wp="${working_pointVsJets}vsjet_tightvsele"; done
else
  for x in .freeze_byErasAndBins .freeze_byErasAndBins_byBins .freeze_byErasAndBins_byBins_byDM .TESUp .TESDown ""; do python scripts/makeSFGraphs.py  -f outputs/${output_dir}/cmb/higgsCombine.ztt.bestfit.singles.postfit${x}.MultiDimFit.mH125.root --dm-bins --saveJson --wp="${working_pointVsJets}vsjet_vvloosevsele"; done
fi

echo "Making graphs with decomposed uncertainties"

if [ "${working_pointVsEle}" == True ]; then
  json_out="--saveJson --wp=${working_pointVsJets}vsjet_tightvsele"
else
  json_out="--saveJson --wp=${working_pointVsJets}vsjet_vvloosevsele"
fi

dir=outputs/${output_dir}/cmb/

python scripts/decoupleUncerts.py -f1 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.MultiDimFit.mH125.TGraphAsymmErrors.root -f2 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins.MultiDimFit.mH125.TGraphAsymmErrors.root -f3 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins.MultiDimFit.mH125.TGraphAsymmErrors.root  -f4 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins_byDM.MultiDimFit.mH125.TGraphAsymmErrors.root -f5 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.TESUp.MultiDimFit.mH125.TGraphAsymmErrors.root -f6 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.TESDown.MultiDimFit.mH125.TGraphAsymmErrors.root --dm-bins -o "outputs/${output_dir}/cmb/" ${json_out}

python scripts/decoupleUncerts.py -f1 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.MultiDimFit.mH125.TGraphAsymmErrors.root -f2 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins.MultiDimFit.mH125.TGraphAsymmErrors.root -f3 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins.MultiDimFit.mH125.TGraphAsymmErrors.root  -f4 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins_byDM.MultiDimFit.mH125.TGraphAsymmErrors.root -f5 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.TESUp.MultiDimFit.mH125.TGraphAsymmErrors.root -f6 ${dir}/higgsCombine.ztt.bestfit.singles.postfit.TESDown.MultiDimFit.mH125.TGraphAsymmErrors.root --dm-bins -o "outputs/${output_dir}/cmb/" --split-fit ${json_out}
