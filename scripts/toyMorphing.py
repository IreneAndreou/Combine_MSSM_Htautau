#!/usr/bin/env python3
import os, sys
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

from CombineHarvester.CombineTools.ch import CombineHarvester, CardWriter, SetStandardBinNames, AutoRebin
import CombineHarvester.CombinePdfs.morphing as morphing
from CombineHarvester.CombinePdfs.morphing import BuildCMSHistFuncFactory
from ROOT import RooWorkspace, RooRealVar

# ─── 0) CONFIG ───────────────────────────────────────────
analysis    = "MyDummy"
era         = "2022"
channel     = "mt"
category    = (1, "mt")
bkg_procs   = ["ZTT", "W", "QCD"]
sig_procs   = ["ggH"]
masses      = ["120", "125", "130"]
shapes_file = "shapes.root"    # must contain mt/data_obs, mt/ZTT*, mt/W*, mt/QCD*, mt/ggH<MASS>*

# ─── 1) HARVEST everything (bkg + sig + data) ─────────────
harv = CombineHarvester()
harv.AddObservations(['*'], [analysis], [era], [channel], [category])
harv.AddProcesses(['*'], [analysis], [era], [channel], bkg_procs,  [category], False)
harv.AddProcesses(masses, [analysis], [era], [channel], sig_procs, [category], True)

# Optional rebin
if True:
    arb = AutoRebin()
    arb.SetBinThreshold(0)
    arb.SetBinUncertFraction(1.0)
    arb.SetPerformRebin(True)
    arb.Rebin(harv, harv)

# Standardize bin naming
SetStandardBinNames(harv)

# ─── 2) EXTRACT SHAPES ───────────────────────────────────
harv.cp().process(bkg_procs).ExtractShapes(
    shapes_file,
    f"{channel}/$PROCESS",
    f"{channel}/$PROCESS_$SYSTEMATIC"
)
harv.cp().process(sig_procs).mass(masses).ExtractShapes(
    shapes_file,
    f"{channel}/$PROCESS$MASS",
    f"{channel}/$PROCESS$MASS_$SYSTEMATIC"
)

# ─── 3) MORPHING ──────────────────────────────────────────
workspace = RooWorkspace(analysis, analysis)
# Morphing variable over the mass grid
m_min, m_max = float(masses[0]), float(masses[-1])
MH = RooRealVar("MH", "Mass of H in GeV", m_min, m_max)
MH.setConstant(True)

print("Building CMSHistFunc morphing...")
BuildCMSHistFuncFactory(workspace, harv, MH, sig_procs[0])

# Save temporary workspace file
workspace.writeToFile("workspace_py.root")

# ─── 4) ADD WORKSPACE & EXTRACT MORPHED PDF/DATA ─────────
harv.AddWorkspace(workspace, False)
harv.ExtractPdfs(harv, analysis, "$BIN_$PROCESS_morph", "")
harv.ExtractData(analysis, "$BIN_data_obs")

# ─── 5) WRITE DATACARDS ───────────────────────────────────
output_dir = "/vols/cms/ia2318/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/output_cards"
os.makedirs(output_dir, exist_ok=True)

writer = CardWriter(
    os.path.join(output_dir, "$BIN/$BIN.txt"),
    os.path.join(output_dir, "$BIN/common/$BIN_input_%s.root" % era)
)
writer.SetWildcardMasses(masses)
writer.WriteCards("cmb", harv)
