# Copy shapes example code command:
# for cat in nobtag btag; do for chn in et mt tt; do cp /vols/cms/ia2318/TIDAL/Draw/production_070525_EarlyRun3SyncMSSM_blind/Run3_2022EE/control/$chn/datacard_mt_tot_${cat}_${chn}_Run3_2022EE.root shapes/mssm.datacard.mt_tot.${chn}.Run3_2022EE.${cat}.root; done; done

# Example command to run this script:
# python3 scripts/harvestDatacards_newQCD_uncerts.py --output_folder mssm_output --eras Run3_2022EE --wp Medium
import ROOT; ROOT.PyConfig.IgnoreCommandLineOptions = True
import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombineTools.ch import CombineHarvester, CardWriter, SetStandardBinNames, AutoRebin
import CombineHarvester.CombinePdfs.morphing as morphing
from CombineHarvester.CombinePdfs.morphing import BuildRooMorphing, BuildCMSHistFuncFactory, BuildCMSHistFuncFactoryCombined
from CombineHarvester.TauSF.systematics import AddMSSMRun3Systematics
from argparse import ArgumentParser
import yaml
from os import environ
# Prevent cppyy's check for the PCH
environ['CLING_STANDARD_PCH'] = 'none'
import cppyy
import json

# specify with eras to fit or combine all eras together by specifying "all"
valid_eras = ['Run3_2022', 'Run3_2022EE','Run3_2023','Run3_2023BPix', 'Run3_2024', 'Run3']

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
  eras = ['Run3_2022', 'Run3_2022EE','Run3_2023','Run3_2023BPix', 'Run3_2024']
else:
  eras = era_tag.split(',')

for e in eras:
  if e not in valid_eras:
    raise Exception("ERROR: one or more of the eras you specified is not supported, available options are: %s" % ",".join(valid_eras))

nominal_histograms = {} # store nominal histos in this dictionary (for zeroing systs)

def green(string,**kwargs):
    '''Displays text in green text inside a black background'''
    return kwargs.get('pre',"")+"\x1b[0;32;40m%s\033[0m"%string

def NegativeBins(p):
    '''Replaces negative bins in hists with 0'''
    hist = p.shape().Clone()
    for i in range(1,hist.GetNbinsX()+1):
        if hist.GetBinContent(i) < 0:
            print("(Process, Channel, Bin) = (%s, %s, %s) has negative bins." % (p.process(), p.channel(), p.bin()))
            hist.SetBinContent(i,0)
    p.set_shape(hist,False)


def GetNominalHisto(p):
    print(f"Retrieving nominal histogram for process: {p.process()} and category: {p.bin()}")
    nom_hist = p.shape().Clone()
    nominal_histograms[p.process()+'_'+p.bin()] = nom_hist


def ZeroNegativeBins(hist, name, type='up/down'):
    '''Sets negative bins in a histogram to zero'''
    integral_before = hist.Integral()
    negative_bins = False
    for i in range(1, hist.GetNbinsX() + 1):
        if hist.GetBinContent(i) < 0:
            negative_bins = True
            hist.SetBinContent(i, 0)
    # update integral
    integral_after = hist.Integral()
    if integral_after > 0:
        hist.Scale(integral_before/integral_after)
    return negative_bins, hist

def DetectNegativeSyst(s):
    '''Replaces negative bins in hists with 0'''
    is_shape = s.type() == 'shape'
    if is_shape:
        up_histo = s.shape_u().Clone()
        down_histo = s.shape_d().Clone()
        is_neg_up, new_up_histo = ZeroNegativeBins(up_histo, s.name(), 'up')
        is_neg_down, new_down_histo = ZeroNegativeBins(down_histo, s.name(), 'down')
        if is_neg_up or is_neg_down:
            print(f">>>>> Negative bins found for systematic: {s.name()} for process: {s.process()} and category: {s.bin()}")
            nominal_hist = nominal_histograms[s.process()+'_'+s.bin()].Clone()
            s.set_shapes(new_up_histo, new_down_histo, nominal_hist)

def NegativeYields(p):
    '''If process has negative yield then set to 0'''
    if p.rate()<0:
        print("(Process, Channel, Bin) = (%s, %s, %s) has a negative yield" % (p.process(), p.channel(), p.bin()))
        p.set_rate(0.)

def get_hist_summary(hist):
    """Return a small summary dict for a TH1."""
    nbins = hist.GetNbinsX()
    integral = hist.Integral(0, nbins + 1)  # include under/overflow
    neg_bins = []
    zero_bins = 0
    for i in range(1, nbins + 1):
        c = hist.GetBinContent(i)
        if c < 0:
            neg_bins.append(i)
        if c == 0:
            zero_bins += 1
    return {
        "nbins": nbins,
        "integral": integral,
        "entries": hist.GetEntries(),
        "xmin": hist.GetXaxis().GetXmin(),
        "xmax": hist.GetXaxis().GetXmax(),
        "neg_bins": neg_bins,
        "n_zero_bins": zero_bins,
    }


def print_cb_proc_shape_and_rate(p, label=""):
    """Print yield/shape info from the CombineHarvester process object."""
    try:
        hist = p.shape()
        s = get_hist_summary(hist)
        print(
            f"[{label}] era={p.era():12s} ch={p.channel():2s} bin={p.bin():15s} "
            f"proc={p.process():20s} mass={p.mass():>5s} "
            f"rate={p.rate():12.5f} integral={s['integral']:12.5f} "
            f"nbins={s['nbins']:4d} xrange=({s['xmin']:.1f},{s['xmax']:.1f}) "
            f"neg_bins={len(s['neg_bins'])}"
        )
        if len(s["neg_bins"]) > 0:
            print(f"    -> negative bins: {s['neg_bins']}")
    except Exception as e:
        print(
            f"[{label}] era={p.era():12s} ch={p.channel():2s} bin={p.bin():15s} "
            f"proc={p.process():20s} mass={p.mass():>5s} "
            f"rate={p.rate():12.5f}  SHAPE ACCESS FAILED: {e}"
        )


def check_cb_shapes_and_rates(cb, label=""):
    """Loop over all processes in CB and print yield/shape summary."""
    print(f"\n==== Yield and shape check {label} ====")
    cb.ForEachProc(lambda p: print_cb_proc_shape_and_rate(p, label))


def check_input_root_files(eras, channels, cats, bkg_procs, sig_procs, masses):
    """Directly inspect the original ROOT input files before morphing."""
    print("\n==== Direct ROOT input check BEFORE morphing ====")
    for chn in channels:
        for era in eras:
            for cat in cats[chn]:
                cat_name = cat[1]
                for prefix in ["mt_", "et_", "tt_"]:
                    if cat_name.startswith(prefix):
                        cat_name = cat_name.replace(prefix, "", 1)
                filename = f"shapes/mssm.datacard.mt_tot.{chn}.{era}.{cat_name}.root"
                tf = ROOT.TFile.Open(filename)
                if not tf or tf.IsZombie():
                    print(f"[BEFORE][MISSING FILE] {filename}")
                    continue

                print(f"\n[BEFORE] file={filename}")
                full_dir = cat[1]
                d = tf.Get(full_dir)
                if not d:
                    print(f"  -> missing directory {full_dir}")
                    tf.Close()
                    continue

                # backgrounds
                for proc in bkg_procs[chn]:
                    objname = f"{full_dir}/{proc}"
                    h = tf.Get(objname)
                    if not h:
                        print(f"  [MISSING BKG] {objname}")
                        continue
                    s = get_hist_summary(h)
                    print(
                        f"  [BKG] ch={chn:2s} era={era:12s} bin={full_dir:15s} proc={proc:20s} "
                        f"integral={s['integral']:12.5f} nbins={s['nbins']:4d} neg_bins={len(s['neg_bins'])}"
                    )

                # signals
                for proc in sig_procs:
                    for m in masses:
                        objname = f"{full_dir}/{proc}{m}"
                        h = tf.Get(objname)
                        if not h:
                            print(f"  [MISSING SIG] {objname}")
                            continue
                        s = get_hist_summary(h)
                        print(
                            f"  [SIG] ch={chn:2s} era={era:12s} bin={full_dir:15s} proc={proc:20s} "
                            f"mass={m:4d} integral={s['integral']:12.5f} nbins={s['nbins']:4d} "
                            f"neg_bins={len(s['neg_bins'])}"
                        )
                tf.Close()


def find_norm_object(ws, name):
    """Try to find the normalisation object in the workspace."""
    obj = ws.function(name)
    if obj:
        return obj
    obj = ws.var(name)
    if obj:
        return obj
    return None


def first_observable_from_pdf(pdf, ws):
    """Try to get the observable used by the morph pdf/histfunc."""
    try:
        obs = pdf.getObservables(ws.allVars())
        if obs and obs.getSize() > 0:
            return obs.first()
    except Exception:
        pass

    # fallback guesses commonly used in CH workspaces
    for guess in ["CMS_th1x", "x", "m_sv", "mt_tot"]:
        v = ws.var(guess)
        if v:
            return v
    return None


def check_workspace_morphs(ws, cb, masses_to_check=None):
    """
    Inspect objects created in the workspace after morphing.
    For signals, optionally evaluate at selected masses.
    """
    print("\n==== Yield and shape check AFTER morphing (workspace) ====")

    bins = sorted(list(cb.bin_set()))
    sigs = sorted(list(cb.cp().signals().process_set()))
    bkgs = sorted(list(cb.cp().backgrounds().process_set()))

    if masses_to_check is None:
        # a few representative masses
        masses_to_check = [str(masses[0]), "125", "500", str(masses[-1])]
    print("\n==== Signal yields after morphing (from workspace) ====")
    MH_var = ws.var("MH")
    for b in ['mt_btag', 'mt_nobtag', 'tt_btag', 'tt_nobtag']:
        for proc in ['bbH_MSSM_htt', 'ggH_MSSM_htt', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes', 'JetFakesSublead']:
            pdf_name = f"{b}_{proc}_morph"
            pdf = ws.function(pdf_name)
            if not pdf:
                print(f"  [MISSING SIG PDF] {pdf_name}")
                continue
            obs = ws.var(f"CMS_x_{b}")
            if not obs:
                print(f"  [NO OBSERVABLE] for {pdf_name}")
                continue
            for m in [60, 125, 500, 1000, 2000, 3500]:  # or use your full mass list
                MH_var.setVal(float(m))
                try:
                    integral = pdf.createIntegral(ROOT.RooArgSet(obs)).getVal()
                    print(f"Yield: bin={b:15s} proc={proc:20s} mass={m:5d} yield={integral:.6g}")
                except Exception as e:
                    print(f"  [ERROR] {pdf_name} mass={m}: {e}")


channels = ['tt', 'mt', 'et']
bkg_procs = {}
# procs for the tauh+tauh channel ## TODO: check QCD / JetFakes with Danny
bkg_procs['tt'] = ['ggH_SM_htt_M125', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes', 'JetFakesSublead']

# procs for the mu+tauh channel
bkg_procs['et'] = ['ggH_SM_htt_M125', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes']

# procs for the e+tauh channel
bkg_procs['mt'] = ['ggH_SM_htt_M125', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes']

# signal processes are defined as any with genuine hadronic taus in the mt channel
masses = [60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 140, 160, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1400, 1600, 1800, 2000, 2300, 2600, 2900, 3200, 3500]
sig_procs = []
sig_procs.append('bbH_MSSM_htt')
sig_procs.append('ggH_MSSM_htt')


cats = {}

cats['mt'] = [
               (1, 'mt_nobtag'),
               (2, 'mt_btag'),
]

cats['et'] = [
                (1, 'et_nobtag'),
                (2, 'et_btag'),
]

cats['tt'] = [
                (1, 'tt_nobtag'),
                (2, 'tt_btag'),
]

# Create an empty CombineHarvester instance
cb = CombineHarvester()

# Add processes and observations
for chn in channels:
    for era in eras:
        # Adding Data,Signal Processes and Background processes to the harvester instance
        cb.AddObservations(['*'], ['mssm'], [era], [chn], cats[chn])
        cb.AddProcesses(['*'], ['mssm'], [era], [chn], bkg_procs[chn], cats[chn], False)
        cb.AddProcesses([str(m) for m in masses], ['mssm'], [era], [chn], sig_procs, cats[chn], True)  # TODO: signal


cb = AddMSSMRun3Systematics(cb)
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
            cb.cp().channel([chn]).bin([cat[1]]).process(sig_procs).era([era]).ExtractShapes(filename, "$BIN/$PROCESS$MASS", "$BIN/$PROCESS$MASS_$SYSTEMATIC")

# checks before morphing
# check_input_root_files(eras, channels, cats, bkg_procs, sig_procs, masses)
# check_cb_shapes_and_rates(cb, label="BEFORE morphing / after ExtractShapes")

# for QCD scale uncertainties we need to scale the yields to factor out any differences in XS

# Read theory factors from JSON and apply per mass point
theory_json = "/vols/cms/ia2318/HiggsDNA-powheg/output/LHE_2024_MSSM/Run3_2024/signal_theory_factors_MSSM.json"
with open(theory_json, "r") as f:
    theory_factors = json.load(f)

def _json_key_for_proc_mass(proc, mass):
    m = int(mass)
    if proc == "bbH_MSSM_htt":
        k = f"BBHto2Tau_M_{m}"
        return k if k in theory_factors else None
    if proc == "ggH_MSSM_htt":
        # preferred key
        k = f"GluGluHto2Tau_M_{m}_2HDM_II"
        if k in theory_factors:
            return k
        # fallback for 125 sample naming
        k_alt = "GluGluHto2Tau_M125_amcatnloFXFX"
        return k_alt if (m == 125 and k_alt in theory_factors) else None
    return None

for proc in ["ggH_MSSM_htt", "bbH_MSSM_htt"]:
    ren_syst = "QCDscale_ren_signal_ACCEPT"
    fac_syst = "QCDscale_fac_signal_ACCEPT"

    for m in masses:
        key = _json_key_for_proc_mass(proc, m)
        if key is None:
            print(f"[WARN] Missing theory factors for proc={proc}, mass={m}")
            continue

        vals = theory_factors[key]

        # Convention used here:
        #   Up   <- scale_*_2p0_factor
        #   Down <- scale_*_0p5_factor
        # (matches previous behavior where Up denominator was often <1 and Down >1 for muR)
        ren_up_denom = vals["scale_muR_2p0_factor"]
        ren_dn_denom = vals["scale_muR_0p5_factor"]
        fac_up_denom = vals["scale_muF_2p0_factor"]
        fac_dn_denom = vals["scale_muF_0p5_factor"]

        cb.cp().process([proc]).mass([str(m)]).syst_name([ren_syst]).ForEachSyst(
            lambda syst, u=ren_up_denom, d=ren_dn_denom: (
                syst.set_value_u(syst.value_u() * (1.0 / u)),
                syst.set_value_d(syst.value_d() * (1.0 / d))
            )
        )
        cb.cp().process([proc]).mass([str(m)]).syst_name([fac_syst]).ForEachSyst(
            lambda syst, u=fac_up_denom, d=fac_dn_denom: (
                syst.set_value_u(syst.value_u() * (1.0 / u)),
                syst.set_value_d(syst.value_d() * (1.0 / d))
            )
        )

rebin = AutoRebin() # As HIG-21-001
rebin.SetBinThreshold(0.2)
rebin.SetBinUncertFraction(0.9)
rebin.SetRebinMode(1)
rebin.SetPerformRebin(True)
rebin.SetVerbosity(1)
rebin.Rebin(cb,cb)

# Zero negetive bins
print(green("Zeroing NegativeBins"))
cb.ForEachProc(NegativeBins)

print(green("Zeroing NegativeYields"))
cb.ForEachProc(NegativeYields)

# Get nominal histograms for all processes (needed when setting systematics)
cb.ForEachProc(GetNominalHisto)
# raise RuntimeError("Stopping here for debugging purposes")
print(green(">>> Zeroing negative systematics"))
cb.ForEachSyst(DetectNegativeSyst)

# Create workspace
ws = ROOT.RooWorkspace("mssm_workspace", "mssm_workspace")

# Define the morphing variable
MH = ROOT.RooRealVar("MH", "Higgs mass", float(masses[0]), float(masses[-1]))
MH.setConstant(True)
MH_2 = ROOT.RooRealVar("MH_2", "Higgs mass", float(masses[0]), float(masses[-1]))
MH_2.setConstant(True)

# Build the map of all signal processes -> "norm" variables
norm_map = {"ggH_MSSM_htt": "norm", "bbH_MSSM_htt": "norm"}
mass_map = cppyy.gbl.map['std::string','RooAbsReal*']()

for proc in norm_map.keys():
    mass_map[proc] = MH

print(green(">>> morphing..."))
BuildCMSHistFuncFactoryCombined(ws, cb, mass_map, process_norm_map=norm_map)

# Add the workspace to CB
cb.AddWorkspace(ws, True)
cb.cp().signals().ExtractPdfs(cb, "mssm_workspace", "$BIN_$PROCESS_morph")
cb.cp().backgrounds().ExtractPdfs(cb, "mssm_workspace", "$BIN_$PROCESS_morph")


# Extract PDFs for both signal processes
cb.ExtractPdfs(cb, "mssm_workspace", "$BIN_$PROCESS_morph", "_norm")
cb.ExtractData("mssm_workspace", "$BIN_data_obs")
check_workspace_morphs(ws, cb, masses_to_check=masses)


# # Optionally save workspace separately
ws.writeToFile(f"{output_folder}/mssm_workspace.root")
print(green("Morphing workspace built and extracted!"))

#filter procs with 0 or negative yields
# cb.FilterProcs(lambda p : p.rate() <=0.)

SetStandardBinNames(cb)
# Add bbb uncerts using autoMC stats
cb.SetAutoMCStats(cb, 0., 0, 1)

print("\n==== Processes just before writing cards ====")
cb.PrintAll()

# define groups - this will help determine correlated uncertainties later on
# add a group for systematics that are correlated by bins and by eras


# Write datacards
print(green(">>> writing datacards..."))
datacardtxt  = "%s/cmb/$BIN.txt"%(output_folder)
datacardroot = "%s/cmb/common/$BIN_input.root"%(output_folder)

## CHECKS
## -----------------------------------------------------------------
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
#           shape_name = f"mt_nobtag/{proc}{m}"
#           fname = f"shapes/mssm.datacard.mt_tot.mt.Run3_2024.nobtag.root"
#           try:
#             f = uproot.open(fname)
#             status = "FOUND" if shape_name in f else "MISSING"
#             print(f"{status}: {fname} -> {shape_name}")
#           except Exception as e:
#             print(f"ERROR opening {fname}: {e}")
#       else:
#         # background
#         shape_name = f"mt_nobtag/{proc}"
#         fname = f"shapes/mssm.datacard.mt_tot.mt.Run3_2024.nobtag.root"
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
# # ...existing code...

# print("\n==== Yield and shape check BEFORE morphing ====")
# print("\n==== Yield and shape check AFTER morphing ====")