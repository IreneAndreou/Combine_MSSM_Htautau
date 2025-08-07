import ROOT
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-e', '--eras', dest='eras', type=str, default='UL', help="Eras; can be either UL or 2022")
args = parser.parse_args()
ROOT.gROOT.SetBatch(1)

colourlist=[ROOT.kBlue,ROOT.kRed,ROOT.kGreen+3,ROOT.kBlack,ROOT.kYellow+2,ROOT.kOrange,ROOT.kCyan+3,ROOT.kMagenta+2,ROOT.kViolet-5,ROOT.kGray]

if args.eras == "UL":
   eras = ['2016_preVFP', '2016_postVFP', '2017', '2018']
if args.eras == "2022":
   eras = ['2022_preEE', '2022_postEE']

wps=['loose','medium','tight','vtight']
#wps=['vvvloose','vvloose','vloose','loose','medium','tight','vtight','vvtight']

def PlotGraphs(graphs, leg_titles, plot_name):

  mg = ROOT.TMultiGraph("mg","")
  graph_count=0
  legend_graphs=[]
  hs = ROOT.THStack("hs","")
  for graph_count, graph in enumerate(graphs):
      g = graph.Clone()
      g.SetFillColor(0)
      g.SetLineWidth(3)
      g.SetLineColor(colourlist[graph_count])
      g.SetMarkerSize(0)
      mg.Add(g)
      hs.Add(g.GetHistogram())
      legend_graphs.append(g.Clone())

  c1 = ROOT.TCanvas()
  c1.cd()

  mg.Draw('ape')
  mg.GetYaxis().SetTitle('SF')
  mg.GetXaxis().SetTitle('p_{T} (GeV)')

  leg = ROOT.TLegend(0.15,0.92,0.9,0.96)
  leg.SetNColumns(5)
  leg.SetBorderSize(0)
  for i in range(len(graphs)): leg.AddEntry(legend_graphs[i],leg_titles[i],'pe')
  leg.Draw()

  c1.Print(plot_name+'.pdf')

def PlotFuncs(funcs, leg_titles, plot_name):

  c2 = ROOT.TCanvas()
  c2.cd()

  miny=2
  maxy=0

  for func in funcs:
      f=func
      maxy=max([maxy,f.Eval(20.),f.Eval(200.)])
      miny=min([miny,f.Eval(20.),f.Eval(200.)])

  for count, func in enumerate(funcs):
      f=func
      f.SetTitle('')
      f.SetLineWidth(3)
      f.SetLineColor(colourlist[count])
      #f.SetMarkerSize(0)
      f.SetMinimum(miny-0.05)
      f.SetMaximum(maxy+0.05)
      f.GetYaxis().SetTitle('SF')
      f.GetXaxis().SetTitle('p_{T} (GeV)')
      print count, f
      if count==0: f.Draw()
      else: f.Draw('same')
      
  

  leg = ROOT.TLegend(0.15,0.92,0.9,0.96)
  leg.SetNColumns(4)
  leg.SetBorderSize(0)
  for i in range(len(graphs)): leg.AddEntry(funcs[i],leg_titles[i],'l')
  leg.Draw()

  c2.Print(plot_name+'.pdf')



for era in eras:

  graph_name = 'DMinclusive_%(era)s' % vars()
  graphs = []
  leg_titles = []

  for wp in wps:

    f1 = ROOT.TFile('outputs/tauSF_Mar07_PFMet_DMinclusive_%(wp)s/split_uncertainties.root' % vars())
    graphs.append(f1.Get(graph_name).Clone())
    leg_titles.append(wp)

  PlotGraphs(graphs, leg_titles, 'compare_WPs_DMinclusive_%(era)s' % vars())


  # now make dm-binned version 

  for dm in [0,1,10,11]:
    graphs=[]
    leg_titles=[]
    for wp in wps:
      graph_name = 'DM%(dm)s_%(era)s_fit' % vars()
      f2 = ROOT.TFile('outputs/tauSF_Mar07_PFMet_DMbinned_%(wp)s/split_uncertainties_dmbins.root' % vars())
      func=f2.Get(graph_name).Clone()
      func.SetName(func.GetName()+'_%(wp)s_dm%(dm)s_%(era)s' % vars())
      graphs.append(func)
      leg_titles.append(wp) 
    PlotFuncs(graphs, leg_titles, 'compare_WPs_DM%(dm)s_%(era)s' % vars())

