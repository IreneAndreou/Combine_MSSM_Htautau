# Copy shapes example code command:
# for cat in nobtag btag; do for chn in et mt tt; do cp /vols/cms/ia2318/TIDAL/Draw/production_070525_EarlyRun3SyncMSSM_blind/Run3_2022EE/control/$chn/datacard_mt_tot_${cat}_${chn}_Run3_2022EE.root shapes/mssm.datacard.mt_tot.${chn}.Run3_2022EE.${cat}.root; done; done

# Example command to run this script:
# python3 scripts/harvestDatacards_newQCD_uncerts.py --output_folder mssm_output --eras Run3_2022EE --wp Medium
import ROOT; ROOT.PyConfig.IgnoreCommandLineOptions = True
import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombineTools.ch import CombineHarvester, CardWriter, SetStandardBinNames, AutoRebin
import CombineHarvester.CombinePdfs.morphing as morphing
from CombineHarvester.CombinePdfs.morphing import BuildRooMorphing, BuildCMSHistFuncFactory
from argparse import ArgumentParser
import yaml
#import os

# specify with eras to fit or combine all eras together by specifying "all"
valid_eras = ['Run3_2022', 'Run3_2022EE','Run3_2023','Run3_2023BPix','Run3']

# HI
description = '''This script makes datacards with CombineHarvester for performing the MSSM Htautau Search.'''
parser = ArgumentParser(prog="harvesterDatacards",description=description,epilog="Success!")
# parser.add_argument('-c', '--config', dest='config', type=str, default='config/harvestDatacards.yml', action='store', help="set config file")
parser.add_argument('-o', '--output_folder', dest='output_folder', type=str, default='', help="set output folder name")
parser.add_argument('-e', '--eras', dest='eras', type=str, default='', help="set eras to be processed")
# parser.add_argument('--wp', dest='wp', default='medium', help="The vs jet WP to measure SFs for")
args = parser.parse_args()
# wp=args.wp

# vsele_wp = 'VVLoose'

# with open(args.config, 'r') as file:
#    setup = yaml.safe_load(file)
#
# output_folder = setup["output_folder"]
# era_tag = setup["eras"]

if args.output_folder:
  output_folder = args.output_folder
if args.eras:
  era_tag = args.eras

if era_tag == 'Run3':
  eras = ['Run3_2022', 'Run3_2022EE','Run3_2023','Run3_2023BPix']
else:
  eras = era_tag.split(',')

for e in eras:
  if e not in valid_eras:
    raise Exception("ERROR: one or more of the eras you specified is not supported, available options are: %s" % ",".join(valid_eras))

def green(string,**kwargs):
    '''Displays text in green text inside a black background'''
    return kwargs.get('pre',"")+"\x1b[0;32;40m%s\033[0m"%string

def NegativeBins(p):
  '''Replaces negative bins in hists with 0'''
  print("Checking for negative bins in process: ",p.process())
  hist = p.shape()
  has_negative = False
  for i in range(1,hist.GetNbinsX()+1):
    if hist.GetBinContent(i) < 0:
       has_negative = True
       print("Process: ",p.process()," has negative bins.")
  if (has_negative):
    for i in range(1,hist.GetNbinsX()+1):
       if hist.GetBinContent(i) < 0:
          hist.SetBinContent(i,0)
  p.set_shape(hist,False)


def NegativeYields(p):
  '''If process has negative yield then set to 0'''
  if (p.process() == "QCD"):
     if p.rate()<0:
        hist = p.shape()
        #error = 0.0
        for i in range(1,hist.GetNbinsX()+1):
           bin_i = hist.GetBinContent(i)
           error = hist.GetBinError(i)
           bins = [hist.GetXaxis().GetBinLowEdge(i), hist.GetXaxis().GetBinUpEdge(i)]
           print("Process: ",p.process()," has negative yields.", p.channel(), p.bin(), p.rate(), bins, bin_i, error)
        p.set_rate(0.)


channels = ['mt']#, 'tt', 'et']
bkg_procs = {}
# procs for the tauh+tauh channel ## TODO: check QCD / JetFakes with Danny
bkg_procs['tt'] = ['ZTT', 'ZL', 'ZJ', 'W', 'VVT', 'VVJ', 'TTT', 'TTJ', 'JetFakes', 'JetFakesSublead']

# procs for the mu+tauh channel
bkg_procs['et'] = ['ZTT', 'ZL', 'ZJ', 'W', 'VVT', 'VVJ', 'TTT', 'TTJ', 'QCD']

# procs for the e+tauh channel
bkg_procs['mt'] = ['ZTT', 'ZL', 'ZJ', 'W', 'VVT', 'VVJ', 'TTT', 'TTJ', 'QCD']

# signal processes are defined as any with genuine hadronic taus in the mt channel
masses = [60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 160, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1400, 1600, 1800, 2000, 2300, 2600, 2900, 3200, 3500]
sig_procs = ['ggH_MSSM_htt']
#sig_procs.append('bbH_MSSM_htt')
#sig_procs.append('ggH_MSSM_htt')


cats = {}

cats['mt'] = [
               (1, 'mt_nobtag'),
               #(2, 'mt_btag'),
]

# cats['et'] = [
#                 (1, 'et_nobtag'),
#                 (2, 'et_btag'),
# ]

# cats['tt'] = [
#                 (1, 'tt_nobtag'),
#                 (2, 'tt_btag'),
# ]

# Create an empty CombineHarvester instance
cb = CombineHarvester()

# Add processes and observations
for chn in channels:
    for era in eras:
        # Adding Data,Signal Processes and Background processes to the harvester instance
        cb.AddObservations(['*'], ['mssm'], [era], [chn], cats[chn])
        cb.AddProcesses(['*'], ['mssm'], [era], [chn], bkg_procs[chn], cats[chn], False)
        cb.AddProcesses([str(m) for m in masses], ['mssm'], [era], [chn], sig_procs, cats[chn], True)  # TODO: signal


# TODO: Add systematics; need to run them first -- and change them from scale factors
# === Example: Lumi uncertainty for all backgrounds ===
# SystMap('era')(['Run3_2022'], 1.02)(['Run3_2023'], 1.03) to vary by era.
# for chn in channels:
#     for era in eras:
#         cb.cp().process(bkg_procs[chn]).era([era]).AddSyst(cb, f"lumi_{era}", "lnN",ch.SystMap()(1.025))

# # === Example: tau ID uncertainty, correlated across channels ===
# for chn in channels:
#     for era in eras:
#         cb.cp().process(bkg_procs[chn]).era([era]).AddSyst(cb,  f"tauID_{era}", "lnN", ch.SystMap()(1.05))


# Populating Observation, Process and Systematic entries in the harvester instance
for chn in channels:
    for cat in cats[chn]:
        for era in eras:
            cat_name = cat[1]
            # Remove only the channel prefix if present (e.g. "mt_", "et_", "tt_")
            for prefix in ["mt_", "et_", "tt_"]:
                if cat_name.startswith(prefix):
                    cat_name = cat_name.replace(prefix, "", 1)
            filename = 'shapes/mssm.datacard.mt_tot.%s.%s.%s.root' % (chn, era, cat_name)
            print(">>>   file " + filename)
            print(">>>   channel " + chn)
            print(">>>   category " + cat_name)
            cb.cp().channel([chn]).bin([cat[1]]).process(bkg_procs[chn]).era([era]).ExtractShapes(filename, "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC")
            # TODO: Setup signal processes --
            cb.cp().channel([chn]).bin([cat[1]]).process(sig_procs).era([era]).ExtractShapes(filename, "$BIN/$PROCESS$MASS", "$BIN/$PROCESS$MASS_$SYSTEMATIC")

rebin = AutoRebin()
#rebin.SetBinThreshold(100)
rebin.SetBinUncertFraction(0.2)
rebin.SetRebinMode(1)
rebin.SetPerformRebin(True)
rebin.SetVerbosity(1)
rebin.Rebin(cb,cb)

# # Zero negetive bins
# print(green("Zeroing NegativeBins"))
# cb.ForEachProc(NegativeBins)

# print(green("Zeroing NegativeYields"))
# cb.ForEachProc(NegativeYields)


# Create workspace
ws = ROOT.RooWorkspace("mssm_workspace", "mssm_workspace")

# Define the morphing variable
MH = ROOT.RooRealVar("MH", "Higgs mass", float(masses[0]), float(masses[-1]))
MH.setConstant(True)

# Build the map of all signal processes -> "norm" variables
norm_map = {"ggH_MSSM_htt": "norm"}

print(green(">>> morphing..."))
for proc in sig_procs:
    BuildCMSHistFuncFactory(ws, cb, MH, proc, process_norm_map={proc: norm_map[proc]})

# Add the workspace to CB
cb.AddWorkspace(ws, True)
cb.cp().signals().ExtractPdfs(cb, "mssm_workspace", "$BIN_$PROCESS_morph")
cb.cp().backgrounds().ExtractPdfs(cb, "mssm_workspace", "$BIN_$PROCESS_morph")


# Extract PDFs for both signal processes
# cb.ExtractPdfs(cb, "mssm_workspace", "$BIN_$PROCESS_morph", "_norm")
cb.ExtractData("mssm_workspace", "$BIN_data_obs")


# # Optionally save workspace separately
ws.writeToFile(f"{output_folder}/mssm_workspace.root")
print(green("Morphing workspace built and extracted!"))

#filter procs with 0 or negative yields
#cb.FilterProcs(lambda p : p.rate() <=0.)

SetStandardBinNames(cb)
# Add bbb uncerts using autoMC stats
cb.SetAutoMCStats(cb, 0., 1, 1)

print("\n==== Processes just before writing cards ====")
cb.PrintAll()

# define groups - this will help determine correlated uncertainties later on
# add a group for systematics that are correlated by bins and by eras


# Write datacards
print(green(">>> writing datacards..."))
datacardtxt  = "%s/cmb/$BIN.txt"%(output_folder)
datacardroot = "%s/cmb/common/$BIN_input.root"%(output_folder)

# ## CHECKS
# ## -----------------------------------------------------------------
# import uproot

# print("\n==== Checking expected shapes in input ROOT files ====")

# # First query the unique bins, eras, processes and masses you’ve added to cb
# bins     = cb.cp().bin_set()
# eras     = cb.cp().era_set()
# procs    = cb.cp().process_set()
# masses   = cb.cp().mass_set()    # this will be empty for backgrounds

# for era in eras:
#   for bin_ in bins:
#     for proc in procs:
#       # decide if this is a signal point or background
#       sig = proc in cb.cp().signals().process_set()
#       if sig:
#         # for each mass point
#         for m in masses:
#           shape_name = f"{bin_}/{proc}{m}"
#           fname = f"shapes/mssm.datacard.mt_tot.mt.Run3_2022EE.nobtag.root"
#           try:
#             f = uproot.open(fname)
#             status = "FOUND" if shape_name in f else "MISSING"
#             print(f"{status}: {fname} -> {shape_name}")
#           except Exception as e:
#             print(f"ERROR opening {fname}: {e}")
#       else:
#         # background
#         shape_name = f"{bin_}/{proc}"
#         fname = f"shapes/mssm.datacard.mt_tot.mt.Run3_2022EE.nobtag.root"
#         try:
#           f = uproot.open(fname)
#           status = "FOUND" if shape_name in f else "MISSING"
#           print(f"{status}: {fname} -> {shape_name}")
#         except Exception as e:
#           print(f"ERROR opening {fname}: {e}")

# import sys
# sys.exit()
# ## -----------------------------------------------------------------
writer = CardWriter(datacardtxt,datacardroot)
writer.SetVerbosity(1)
# Add the masses
writer.SetWildcardMasses([str(m) for m in masses])
writer.WriteCards("cmb", cb)