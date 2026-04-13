# Combine_MSSM_Htautau
A repository for creating the datacards and employing the fitting procedure using CombineHarvester for the MSMM Htautau analysis in Run3

## Setup

setup CMSSW:

```bash
cmsrel CMSSW_14_1_0_pre4
cd CMSSW_14_1_0_pre4/src
cmsenv
```

### Clone combine and combine harvester:

```bash
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
# IMPORTANT: Checkout the recommended tag on the link above
git clone https://github.com/cms-analysis/CombineHarvester.git CombineHarvester
cd CombineHarvester
git checkout v3.0.0
scram b
```

### Clone tauSF repository:

```bash
git clone --branch main git@github.com:IreneAndreou/Combine_MSSM_Htautau.git Combine_MSSM_Htautau
```

compile:

```bash
cd Combine_MSSM_Htautau/
scram b clean
scram b -j8
```

### Copy datacards to datacards directory

Add instructions to retrieve these from a repository
```bash
mkdir datacards
cp -r directory_with_datacards/ datacards/
```

### Copy mm datacards over to shapes directory

```bash
mkdir shapes
cp -r datacards/your_mm_path/year/datacard_name.root shapes/ztt.datacard.m_vis.mm.year.root
```

### hadd mt datacards placing them in shapes directory (vsEle is set to VVLoose in this case)

```bash
hadd -f shapes/ztt.datacard.pt_2_vs_m_vis.mt.Run3_2022.vsJetMedium.vsEleVVLoose.root /vols/cms/ia2318/Combine_MSSM_Htautau/CMSSW_14_1_0_pre4/src/CombineHarvester/Combine_MSSM_Htautau/datacards/Run3_2022/sf_calculation/mt/*.root
```

## Converting datacards

If you are starting from 2D histograms in bins of pT vs m_vis these must first be split into
1D histograms in bins of m_vis
Run this script to split the datacards:

```bash
python3 scripts/convertDatacards.py -f shapes/ztt.datacard.pt_2_vs_m_vis.mt.your_datacard_suffixes.root
```

## Updates: April 2024

To run limits from  shapes in `/vols/cms/ia2318/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/shapes` run:

```bash
python3 scripts/run_nomorph_limits.py
```

Example commands for prefit plots:
```bash
python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=500,r_bbH=1,r_ggH=1 --plot_dir thesis_plots_prefit
mv shapes_output.root shapes_output_prefit.root
python3 scripts/plot_mssm_shapes.py -i shapes_output_prefit.root -b all --blind --dir mssm_output/final_plots_prefit --logy (--combine-all-bins)
```

Run fit for postfit plots
```bash
combineTool.py -m 125 -M MultiDimFit --setParameters r_ggH=0,r_bbH=0 --freezeParameters r_ggH,r_bbH -d mssm_output/cmb/ws.root -n .BestFit --algo none --saveFitResult --there --robustHesse=1
```


Example commands for postfit plots:
```bash
python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=500,r_bbH=1,r_ggH=1 --plot_dir thesis_plots_postfit --fitresult mssm_output/cmb/multidimfit.BestFit.root:fit_mdf --postfit
mv shapes_output.root shapes_output_postfit.root
python3 scripts/plot_mssm_shapes.py -i shapes_output_postfit.root -b all --blind --dir mssm_output/final_plots_postfit --logy (--combine-all-bins)
```

To run GOF tests:
```bash
bash scripts/run_gof.sh Run3_2024 cmb all . local
```

per channel and category:
```bash
python3 scripts/run_all_gof_M125.py
```

To run (full) Impacts:
```bash
python3 scripts/run_all_impacts.py
```