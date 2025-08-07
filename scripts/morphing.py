import ROOT
import numpy as np

def auto_rebin(hist, min_bin_content=1e-3):
    """Merge bins so that no bin is zero or below min_bin_content."""
    nbins = hist.GetNbinsX()
    edges = [hist.GetXaxis().GetBinLowEdge(1)]
    acc = 0
    for i in range(1, nbins+1):
        acc += hist.GetBinContent(i)
        # If accumulated content is enough or last bin, set new edge
        if acc >= min_bin_content or i == nbins:
            edges.append(hist.GetXaxis().GetBinUpEdge(i))
            acc = 0
    # Rebin
    arr = np.array(edges, dtype='float64')
    rebinned = hist.Rebin(len(arr)-1, hist.GetName()+"_rebin", arr)
    return rebinned

# Setup
mt_tot = ROOT.RooRealVar("mt_tot", "m_{T}^{tot}", 0, 1000, "GeV")
MH = ROOT.RooRealVar("MH", "Higgs mass", 125.0, 60, 3500)

mass_points = [60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 160, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1400, 1600, 1800, 2000, 2300, 2600, 2900, 3200, 3500]

# Open input
f = ROOT.TFile.Open("shapes/mssm.datacard.mt_tot.mt.Run3_2022EE.nobtag.root")

# PDFs list
pdfs = ROOT.RooArgList()
pdf_refs = []
dh_refs = []  # <-- NEW: keep DataHists alive too!

ref_binning = None
for m in mass_points:
    path = f"mt_nobtag/ggH_MSSM_htt{m}"
    hist = f.Get(path)
    if not hist or hist.IsZombie():
        raise RuntimeError(f"Missing histogram: {path}")
    
    # --- REBINNING STEP ---
    hist = auto_rebin(hist, min_bin_content=1)
    # ----------------------
    # if ref_binning is None:
    #     ref_binning = (hist.GetNbinsX(), hist.GetXaxis().GetXmin(), hist.GetXaxis().GetXmax())
    # else:
    #     this_binning = (hist.GetNbinsX(), hist.GetXaxis().GetXmin(), hist.GetXaxis().GetXmax())
    #     if this_binning != ref_binning:
    #         print(f"⚠️ Skipping {path}: binning {this_binning} does not match reference {ref_binning}")
    #         import sys
    #         sys.exit()
    total = hist.Integral()
    print(f"  Histogram {path} integral: {total}")
    if total <= 0:
        print(f"⚠️ Histogram {path} is empty or negative!")
        import sys
        sys.exit()
    print(f"Loaded: {path}")

    dh = ROOT.RooDataHist(f"dh_{m}", "", ROOT.RooArgList(mt_tot), hist)
    pdf = ROOT.RooHistPdf(f"pdf_{m}", "", ROOT.RooArgSet(mt_tot), dh)

    pdfs.add(pdf)
    pdf_refs.append(pdf)
    dh_refs.append(dh)  # <-- ✅ keep alive!

    print(f"  --> Added {pdf.GetName()} to pdfs. Current size: {pdfs.getSize()}")

# Debug print
print("PDFs in list:")
for i in range(pdfs.getSize()):
    obj = pdfs.at(i)
    print(f"  {i}: {obj.GetName()} ({obj.ClassName()})")

# Grid
grid = ROOT.TVectorT('double')(len(mass_points))
for i, m in enumerate(mass_points):
    grid[i] = m

# Morph
morph = ROOT.RooMomentMorph(
    "mymorph", "Morphed signal",
    MH,                      # the morphing parameter
    ROOT.RooArgList(mt_tot), # the *observable* for integration
    pdfs,
    grid
)

# Save
w = ROOT.RooWorkspace("w")
getattr(w, "import")(morph)
w.writeToFile("workspace_morphing.root")
print("✅ All done!")


f = ROOT.TFile.Open("workspace_morphing.root")
w = f.Get("w")

mt_tot = w.var("mt_tot")
MH = w.var("MH")
mymorph = w.pdf("mymorph")

c = ROOT.TCanvas("c", "Morphing Example", 800, 600)
# Plot multiple interpolation points
# Open your workspace
f = ROOT.TFile.Open("workspace_morphing.root")
w = f.Get("w")

# Get observable, morphing parameter, and PDF
mt_tot = w.var("mt_tot")
MH = w.var("MH")
mymorph = w.pdf("mymorph")

# Mass points to test
test_masses = [62, 73, 87, 94, 114, 236, 387, 431, 125] ## does not work for high masses for some reason

# Create canvas, frame, and legend
c = ROOT.TCanvas("c", "Morphing with Legend", 800, 600)
frame = mt_tot.frame()
legend = ROOT.TLegend(0.65, 0.55, 0.88, 0.88)
legend.SetBorderSize(0)
legend.SetFillStyle(0)
legend.SetTextFont(42)
legend.SetTextSize(0.03)

# Pick some colors
colors = [
    ROOT.kRed, ROOT.kBlue, ROOT.kGreen+2, ROOT.kMagenta, ROOT.kOrange+7,
    ROOT.kCyan+2, ROOT.kBlack, ROOT.kViolet, ROOT.kAzure+1, ROOT.kPink+7,
    ROOT.kTeal+3, ROOT.kGray+2
]

# Loop over test masses and plot
for i, mass in enumerate(test_masses):
    MH.setVal(mass)
    MH.setConstant(True)

    color = colors[i % len(colors)]

    # Give each curve a name to grab later
    curve_name = f"curve_{mass}"
    mymorph.plotOn(
        frame,
        ROOT.RooFit.LineColor(color),
        ROOT.RooFit.Name(curve_name)
    )

    # Find plotted curve and add to legend
    curve_obj = frame.findObject(curve_name)
    if curve_obj:
        legend.AddEntry(curve_obj, f"mH = {mass} GeV", "l")
    else:
        print(f"⚠️ Warning: Could not find curve {curve_name} for legend!")

# Axis labels
frame.GetXaxis().SetTitle("m_{T}^{tot} [GeV]")
frame.GetYaxis().SetTitle("Morphing PDF")

# Draw and save
frame.Draw()
legend.Draw()

c.SaveAs("morphing_plot_with_legend.pdf")
print("✅ Saved: morphing_plot_with_legend.pdf")