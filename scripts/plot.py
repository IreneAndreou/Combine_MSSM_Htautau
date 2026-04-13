import ROOT

# Open the ROOT file and load the workspace
f = ROOT.TFile.Open("/vols/cms/ia2318/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/mssm_output/cmb/ws.root")
w = f.Get("w")

# Get the necessary variables and function
MH = w.var("MH")
x = w.var("CMS_x_mt_nobtag")
hist_func = w.function("shapeSig_ggH_MSSM_htt_mssm_mt_1_Run3_2022EE")
interp_rate = w.function("interp_rate_mt_nobtag_ggH_MSSM_htt")
proc_norm = w.function("n_exp_binmssm_mt_1_Run3_2022EE_proc_ggH_MSSM_htt")


if not MH or not x or not hist_func:
    print("Error: Could not find MH, x, or hist function in the workspace.")
    exit()

# Prepare a canvas
c = ROOT.TCanvas("c", "", 800, 600)

# Loop over MH values and plot the resulting histograms
colors = [ROOT.kRed, ROOT.kBlue, ROOT.kGreen+2, ROOT.kOrange+7, ROOT.kViolet, ROOT.kTeal+3]
first = True
legend = ROOT.TLegend(0.6, 0.6, 0.88, 0.88)

#for idx, mh_val in enumerate(range(300, 501, 100)):
for idx, mh_val in enumerate([300,400,500,600]):
    MH.setVal(mh_val)
    h = hist_func.createHistogram(f"h_{mh_val}", x)
    h.SetLineColor(colors[idx % len(colors)])
    h.SetLineWidth(2)
    h.SetTitle("shapeSig_ggH_MSSM_htt_mssm_mt_1_Run3_2022EE")

    interp_rate.getVariables().Print("v")
    interp_val = interp_rate.getVal()
    proc_norm_val = proc_norm.getVal()

    print(f"MH = {mh_val} GeV, Integral={h.Integral()}, interp_val={interp_val}, proc_norm_val={proc_norm_val}")

    legend.AddEntry(h, f"MH = {mh_val} GeV", "l")

    if first:
        h.Draw("HIST")
        first = False
    else:
        h.Draw("HIST SAME")

legend.Draw()
c.Update()
c.Print('morphed_masses.pdf')

