# TauSF
a repository for fitting the tau ID SFs using ZTT events

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
git clone --branch CMSSW_14_X-PnetDM git@github.com:Ksavva1021/TauSF.git TauSF
```

compile:

```bash
cd TauSF/
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
hadd -f shapes/ztt.datacard.pt_2_vs_m_vis.mt.Run3_2022.vsJetVTight.vsEleVVLoose.root /vols/cms/ks1021/TauSF/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/datacards/Run3_2022/sf_calculation/mt/*.root
```

## Converting datacards

If you are starting from 2D histograms in bins of pT vs m_vis these must first be split into
1D histograms in bins of m_vis
Run this script to split the datacards:

```bash
python3 scripts/convertDatacards.py -f shapes/ztt.datacard.pt_2_vs_m_vis.mt.your_datacard_suffixes.root
```