import ROOT

# Create output file
fout = ROOT.TFile("shapes.root", "RECREATE")

cats = ["mt"]
sig_masses = ["120", "125", "130"]
bkg_procs = ["ZTT", "W", "QCD"]
sig_procs = ["ggH", "bbH"]

def make_hist(name, val=10):
    hist = ROOT.TH1F(name, name, 10, 0, 100)
    for i in range(1, hist.GetNbinsX()+1):
        hist.SetBinContent(i, val + i)
    return hist

for cat in cats:
    fout.mkdir(cat)
    fout.cd(cat)
    
    # Backgrounds
    for proc in bkg_procs:
        h = make_hist(proc)
        h.Write()

    # Signals
    for mass in sig_masses:
        for proc in sig_procs:
            h = make_hist(proc + mass)
            h.Write()

    # Data_obs = sum of backgrounds (or any dummy)
    data_obs = ROOT.TH1F("data_obs", "data_obs", 10, 0, 100)
    for i in range(1, data_obs.GetNbinsX()+1):
        val = sum([10 + i for _ in bkg_procs])
        data_obs.SetBinContent(i, val)
    data_obs.Write()

fout.Close()
print("✅ Created toy shapes.root with data_obs")
