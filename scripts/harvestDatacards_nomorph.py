import ROOT; ROOT.PyConfig.IgnoreCommandLineOptions = True
import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombineTools.ch import CombineHarvester, CardWriter, SetStandardBinNames, AutoRebin
from CombineHarvester.TauSF.systematics import AddMSSMRun3Systematics
from argparse import ArgumentParser
from os import environ
import json

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

# Prevent cppyy's check for the PCH
environ['CLING_STANDARD_PCH'] = 'none'

valid_eras = ['Run3_2022', 'Run3_2022EE', 'Run3_2023', 'Run3_2023BPix', 'Run3_2024', 'Run3']
all_masses = [60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 140, 160, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1400, 1600, 1800, 2000, 2300, 2600, 2900, 3200, 3500]

description = "Build non-morphed MSSM Htautau datacards for a single mass point."
parser = ArgumentParser(prog="harvestDatacards_nomorph", description=description, epilog="Success!")
parser.add_argument('-o', '--output_folder', dest='output_folder', type=str, required=True, help="output folder")
parser.add_argument('-e', '--eras', dest='eras', type=str, required=True, help="eras to process")
# removed mass argument
args = parser.parse_args()

output_folder = args.output_folder
era_tag = args.eras

if era_tag == 'Run3':
    eras = ['Run3_2022', 'Run3_2022EE', 'Run3_2023', 'Run3_2023BPix', 'Run3_2024']
else:
    eras = era_tag.split(',')

for e in eras:
    if e not in valid_eras:
        raise Exception(f"ERROR: unsupported era {e}. Available: {','.join(valid_eras)}")

channels = ['tt', 'mt', 'et']
bkg_procs = {
    'tt': ['ggH_SM_htt_M125', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes', 'JetFakesSublead'],
    'et': ['ggH_SM_htt_M125', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes'],
    'mt': ['ggH_SM_htt_M125', 'ZTT', 'ZL', 'VVT', 'TTT', 'JetFakes'],
}
sig_procs = ['bbH_MSSM_htt', 'ggH_MSSM_htt']

cats = {
    'mt': [(1, 'mt_nobtag'), (2, 'mt_btag')],
    'et': [(1, 'et_nobtag'), (2, 'et_btag')],
    'tt': [(1, 'tt_nobtag'), (2, 'tt_btag')],
}

theory_json = "/vols/cms/ia2318/HiggsDNA-powheg/output/LHE_2024_MSSM/Run3_2024/signal_theory_factors_MSSM.json"
with open(theory_json, "r") as f:
    theory_factors = json.load(f)

def _json_key_for_proc_mass(proc, mass):
    m = int(mass)
    if proc == "bbH_MSSM_htt":
        k = f"BBHto2Tau_M_{m}"
        return k if k in theory_factors else None
    if proc == "ggH_MSSM_htt":
        k = f"GluGluHto2Tau_M_{m}_2HDM_II"
        if k in theory_factors:
            return k
        k_alt = "GluGluHto2Tau_M125_amcatnloFXFX"
        return k_alt if (m == 125 and k_alt in theory_factors) else None
    return None

# Loop over all masses
for mass in all_masses:
    print(green(f"Processing mass {mass}"))
    masses = [mass]
    nominal_histograms = {}

    cb = CombineHarvester()

    # Add observations/processes
    for chn in channels:
        for era in eras:
            cb.AddObservations(['*'], ['mssm'], [era], [chn], cats[chn])
            cb.AddProcesses(['*'], ['mssm'], [era], [chn], bkg_procs[chn], cats[chn], False)
            cb.AddProcesses([str(m) for m in masses], ['mssm'], [era], [chn], sig_procs, cats[chn], True)

    cb = AddMSSMRun3Systematics(cb)

    # Extract shapes
    for chn in channels:
        for cat in cats[chn]:
            for era in eras:
                cat_name = cat[1]
                for prefix in ["mt_", "et_", "tt_"]:
                    if cat_name.startswith(prefix):
                        cat_name = cat_name.replace(prefix, "", 1)

                filename = f"shapes/mssm.datacard.mt_tot.{chn}.{era}.{cat_name}.root"
                print(">>>   file " + filename)
                print(">>>   channel " + chn)
                print(">>>   category " + cat_name)
                print(">>>   mass " + str(mass))

                cb.cp().channel([chn]).bin([cat[1]]).process(bkg_procs[chn]).era([era]).ExtractShapes(
                    filename, "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC"
                )
                cb.cp().channel([chn]).bin([cat[1]]).process(sig_procs).era([era]).mass([str(mass)]).ExtractShapes(
                    filename, "$BIN/$PROCESS$MASS", "$BIN/$PROCESS$MASS_$SYSTEMATIC"
                )

    # Apply theory factors only for the selected mass
    for proc in ["ggH_MSSM_htt", "bbH_MSSM_htt"]:
        ren_syst = "QCDscale_ren_signal_ACCEPT"
        fac_syst = "QCDscale_fac_signal_ACCEPT"

        key = _json_key_for_proc_mass(proc, mass)
        if key is None:
            print(f"[WARN] Missing theory factors for proc={proc}, mass={mass}")
            continue

        vals = theory_factors[key]
        ren_up_denom = vals["scale_muR_2p0_factor"]
        ren_dn_denom = vals["scale_muR_0p5_factor"]
        fac_up_denom = vals["scale_muF_2p0_factor"]
        fac_dn_denom = vals["scale_muF_0p5_factor"]

        cb.cp().process([proc]).mass([str(mass)]).syst_name([ren_syst]).ForEachSyst(
            lambda syst, u=ren_up_denom, d=ren_dn_denom: (
                syst.set_value_u(syst.value_u() * (1.0 / u)),
                syst.set_value_d(syst.value_d() * (1.0 / d))
            )
        )
        cb.cp().process([proc]).mass([str(mass)]).syst_name([fac_syst]).ForEachSyst(
            lambda syst, u=fac_up_denom, d=fac_dn_denom: (
                syst.set_value_u(syst.value_u() * (1.0 / u)),
                syst.set_value_d(syst.value_d() * (1.0 / d))
            )
        )

    # Rebin
    rebin = AutoRebin()
    rebin.SetBinThreshold(0.2)
    rebin.SetBinUncertFraction(0.9)
    rebin.SetRebinMode(1)
    rebin.SetPerformRebin(True)
    rebin.SetVerbosity(1)
    rebin.Rebin(cb, cb)

    # Clean up negatives
    print(green("Zeroing NegativeBins"))
    cb.ForEachProc(NegativeBins)

    print(green("Zeroing NegativeYields"))
    cb.ForEachProc(NegativeYields)

    print(green("Caching nominal histograms"))
    cb.ForEachProc(GetNominalHisto)

    print(green(">>> Zeroing negative systematics"))
    cb.ForEachSyst(DetectNegativeSyst)

    SetStandardBinNames(cb)
    cb.SetAutoMCStats(cb, 0., 0, 1)

    print("\n==== Processes just before writing cards ====")
    cb.PrintAll()

    print(green(">>> writing datacards..."))
    datacardtxt = f"{output_folder}/cmb/$BIN_{mass}.txt"
    datacardroot = f"{output_folder}/cmb/common/$BIN_input_{mass}.root"

    writer = CardWriter(datacardtxt, datacardroot)
    writer.SetVerbosity(1)
    writer.SetWildcardMasses([])  # no morphing / no wildcard mass dependence
    writer.WriteCards("cmb", cb)

    print(green(f"Done. Wrote non-morphed cards for mass {mass}."))