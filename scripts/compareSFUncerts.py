import ROOT

graph_name = 'DMinclusive_2018'

f1 = ROOT.TFile('outputs/tauSF_Feb16_DMinclusive_mTLt30/cmb/higgsCombine.ztt.bestfit.singles.postfit.MultiDimFit.mH125.TGraphAsymmErrors.root')
f2 = ROOT.TFile('outputs/tauSF_Feb16_DMinclusive_mTLt30/cmb/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins.MultiDimFit.mH125.TGraphAsymmErrors.root')
f3 = ROOT.TFile('outputs/tauSF_Feb16_DMinclusive_mTLt30/cmb/higgsCombine.ztt.bestfit.singles.postfit.freeze_byErasAndBins_byBins.MultiDimFit.mH125.TGraphAsymmErrors.root')

g1 = f1.Get(graph_name)
g2 = f2.Get(graph_name)
g3 = f3.Get(graph_name)

c1 = ROOT.TCanvas()

gout1=ROOT.TGraph()
gout2=ROOT.TGraph()
gout3=ROOT.TGraph()
gout4=ROOT.TGraph()

for i in range(0,g1.GetN()):
  up_total=g1.GetErrorYhigh(i)
  down_total=g1.GetErrorYlow(i)

  up_nobyera=g2.GetErrorYhigh(i)
  down_nobyera=g2.GetErrorYlow(i)

  up_nobybin=g3.GetErrorYhigh(i)
  down_nobybin=g3.GetErrorYlow(i)

  up_byera = (up_total**2-up_nobyera**2)**.5
  down_byera = (down_total**2-down_nobyera**2)**.5

  up_bybin = (up_total**2-up_nobybin**2 - up_byera**2)**.5
  down_bybin = (down_total**2-down_nobybin**2 - down_byera**2)**.5

  up_bybin = (up_total**2-up_nobybin**2-up_byera**2)**.5
  down_bybin = (down_total**2-down_nobybin**2-down_byera**2)**.5

  x=ROOT.Double()
  y=ROOT.Double()
  g1.GetPoint(i,x,y)

#  print x,y, up_total, up_nobyera, up_nobybin
  print up_total, up_nobybin, up_byera, up_bybin 

  ave_total = (up_total+down_total)/2 /y
  ave_stat = (up_nobybin+down_nobybin)/2 /y
  ave_systbyera = (up_byera+down_byera)/2 /y
  ave_systbybin = (up_bybin+down_bybin)/2 /y


  gout1.SetPoint(i, x, ave_total)
  gout2.SetPoint(i, x, ave_stat)
  gout3.SetPoint(i, x, ave_systbyera)
  gout4.SetPoint(i, x, ave_systbybin)
  

gout1.SetMinimum(0.)

gout1.SetMarkerStyle(8)
gout2.SetMarkerStyle(8)
gout3.SetMarkerStyle(8)
gout4.SetMarkerStyle(8)

gout1.GetXaxis().SetTitle('p_{T} (GeV)')
gout1.GetYaxis().SetTitle('relative uncertainty')
gout1.Draw('ap')

gout2.SetMarkerColor(ROOT.kRed)
gout3.SetMarkerColor(ROOT.kBlue)
gout4.SetMarkerColor(ROOT.kGreen-2)

gout2.Draw('p')
gout3.Draw('p')
gout4.Draw('p')

leg = ROOT.TLegend(0.15,0.92,0.9,0.96)
leg.SetNColumns(4) 
leg.AddEntry(gout1,'Total','p')
leg.AddEntry(gout2,'Stat.','p')
leg.AddEntry(gout3,'Syst. (by Era)','p')
leg.AddEntry(gout4,'Other Systs','p')
leg.SetBorderSize(0)
leg.Draw()

c1.Print('graph_uncert_comps_%s.pdf' % graph_name)

 
